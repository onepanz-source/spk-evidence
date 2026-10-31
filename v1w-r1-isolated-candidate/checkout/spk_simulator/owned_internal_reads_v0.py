"""SPK S3.7d/3b2b2k/4: service-gated real P/S reads + witnessed Core prepare.

An owner tick advances the existing storage controller, obtains actual consumed
batches, reads immutable program and current versioned neuronal state, and
confirms only fulfilled PROGRAM_REFERENCE and STATE_LOAD requests. It never
commits state, admits Core candidate emissions, or verifies the trace-derived
routing manifest independently. Only the directly verified P/S reads are
promoted to service confirmations. Not a full architectural runtime.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.access_v0 import MemoryDomainV0 as Domain
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0, ServiceConfirmedV0
from spk_simulator.computed_emission_binding_v0 import ComputedEmissionBindingV0, bind_computed_emission_v0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.owned_service_tick_v0 import OwnedServiceTickStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, PreparedCoreTransitionV0, CoreStateCommitReceiptV0,
    prepare_core_transition_v0, initialize_neuron_image_v0, commit_core_transition_v0,
)
from spk_simulator.witnessed_core_input_v0 import (
    WitnessedCoreInputBatchV0, WitnessedCoreInputTickV0,
    advance_witnessed_core_input_tick_v0,
)


@dataclass(frozen=True, slots=True)
class InternalReadEvidenceV0:
    request_id: int
    kind: Kind
    node_id: str
    event_time: int
    epoch_id: str
    pe_id: str
    service_boundary: int
    state_version: int | None
    raw: int | None
    last_timestamp: int | None
    # For a program reference, the actual immutable P image is read, not
    # a caller-supplied value or a hash of a previous functional trace.
    config: object | None
    program: object | None


@dataclass(frozen=True, slots=True)
class BoundCorePreparationV0:
    consume_request_id: int
    program_read_request_id: int
    state_read_request_id: int
    transition: PreparedCoreTransitionV0


@dataclass(frozen=True, slots=True)
class OwnedInternalCommitEvidenceV0:
    commit_request_id: int
    preparation: BoundCorePreparationV0
    receipt: CoreStateCommitReceiptV0
    confirmation_boundary: int
    emission_binding: ComputedEmissionBindingV0 | None = None


@dataclass(frozen=True, slots=True)
class OwnedInternalReadStateV0:
    owned: OwnedServiceTickStateV0
    image: VersionedNeuronImageV0
    pending_batches: tuple[WitnessedCoreInputBatchV0, ...] = ()
    reads: tuple[InternalReadEvidenceV0, ...] = ()
    prepared: tuple[BoundCorePreparationV0, ...] = ()
    commits: tuple[OwnedInternalCommitEvidenceV0, ...] = ()


@dataclass(frozen=True, slots=True)
class OwnedInternalReadStepV0:
    witnessed_tick: WitnessedCoreInputTickV0
    new_reads: tuple[InternalReadEvidenceV0, ...]
    new_preparations: tuple[BoundCorePreparationV0, ...]
    state: OwnedInternalReadStateV0


def _canonical_unique(entries, key, description):
    ids = tuple(key(entry) for entry in entries)
    if ids != tuple(sorted(set(ids))):
        raise ValueError(f'noncanonical {description}')


def _read_binding(req, consume, nodes, epoch):
    if req.kind not in (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD):
        raise ValueError('unsupported internal read kind')
    name = ('program' if req.kind is Kind.PROGRAM_REFERENCE else 'state')
    node_id = req.target_id[len(name) + 1:] if req.target_id.startswith(name + ':') else ''
    if (not node_id or node_id not in nodes
            or req.target_id != f'{name}:{node_id}'
            or req.domain is not (Domain.PROGRAM if name == 'program' else Domain.STATE)
            or req.epoch_id != epoch or req.quantity != 1
            or req.event_time is None or type(req.event_time) is not int
            or req.target_pe_id != consume.target_pe_id
            or req.event_time != consume.event_time
            or consume.target_id != f'events:{node_id}'
            or consume.epoch_id != epoch):
        raise ValueError('internal read/batch target, epoch, PE or EVENT_TIME mismatch')
    return node_id


def audit_committed_internal_history_v0(network, state, requests, graph, *,
                                        architecture=None, manifest=None, admission=None):
    """Replay authenticated local Core commits and rebuild historical S snapshots.

    This audits the complete locally retained state history; it is not a
    cryptographic anti-tamper proof. Emitting commits require full OUTPUT context.
    """
    if type(state) is not OwnedInternalReadStateV0:
        raise TypeError('invalid internal owner state')
    from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
    if any(r.kind is Kind.STATE_COMMIT for r in requests):
        serialized = serialize_internal_access_graph_v0(requests, graph)
        bindings = {item.state_commit_request_id: item for item in serialized.batches}
    else:
        if state.commits:
            raise ValueError('commits without STATE_COMMIT requests')
        bindings = {}
    confirmed = {x.request_id: x for x in state.owned.boundary.service.confirmed}
    commit_ids = {r.request_id for r in requests if r.kind is Kind.STATE_COMMIT}
    entries = state.commits
    if (type(entries) is not tuple or
        any(type(item) is not OwnedInternalCommitEvidenceV0 for item in entries) or
        tuple((x.confirmation_boundary, x.commit_request_id) for x in entries) !=
        tuple(sorted(set((x.confirmation_boundary, x.commit_request_id) for x in entries))) or
        {x.commit_request_id for x in entries} != set(confirmed) & commit_ids):
        raise ValueError('invalid or missing authenticated commit history')
    by_read = {x.request_id: x for x in state.reads}
    witnesses = {x.consume_request_id: x for x in state.pending_batches}
    image = initialize_neuron_image_v0(network, epoch_id=state.image.epoch_id)
    snapshots = {(x.node_id, x.version): x for x in image.neurons}
    last_commit_boundary = {}
    for item in entries:
        batch = bindings.get(item.commit_request_id)
        prep = item.preparation
        trans = prep.transition
        if (batch is None or type(prep) is not BoundCorePreparationV0 or
            prep.consume_request_id != batch.consume_request_id or
            prep.program_read_request_id != batch.program_request_id or
            prep.state_read_request_id != batch.state_load_request_id or
            trans.node_id != batch.node_id or trans.event_time != batch.event_time or
            trans.epoch_id != batch.epoch_id or
            item.confirmation_boundary != confirmed[item.commit_request_id].confirmation_boundary or
            type(item.confirmation_boundary) is not int or
            item.confirmation_boundary > state.owned.boundary.service.next_service_tick):
            raise ValueError('invalid historical commit binding')
        witnessed = witnesses.get(prep.consume_request_id)
        p, sr = by_read.get(prep.program_read_request_id), by_read.get(prep.state_read_request_id)
        if (witnessed is None or p is None or sr is None or
            (trans.channels, trans.node_id, trans.event_time) !=
            (witnessed.channels, witnessed.node_id, witnessed.event_time) or
            p.service_boundary > item.confirmation_boundary or
            sr.service_boundary > item.confirmation_boundary or
            sr.service_boundary < last_commit_boundary.get(trans.node_id, 0) or
            witnessed.service_boundary > item.confirmation_boundary):
            raise ValueError('commit without witnessed input and P/S service')
        current = next(x for x in image.neurons if x.node_id == trans.node_id)
        if (sr.state_version != current.version or sr.raw != current.raw or
            sr.last_timestamp != current.last_timestamp or
            sr.kind is not Kind.STATE_LOAD or p.kind is not Kind.PROGRAM_REFERENCE):
            raise ValueError('historical STATE_LOAD does not match committed base version')
        if trans.candidate_outputs:
            if architecture is None or manifest is None or admission is None:
                raise ValueError('emitting history requires architectural OUTPUT context')
            published = item.emission_binding
            if type(published) is not ComputedEmissionBindingV0:
                raise ValueError('emitting history missing authenticated OUTPUT binding')
            expected = bind_computed_emission_v0(
                architecture, network, image, trans, manifest, admission, requests,
                emission_request_id=published.emission_request_id,
            )
            if published != expected:
                raise ValueError('historical OUTPUT binding mismatch')
            if not expected.route_request_ids:
                raise ValueError('terminal-only emission unsupported by atomic owner v0')
            driver = state.owned.boundary.driver
            completed_output = set(state.owned.output.completed_emission_ids)
            confirmed_emission = confirmed.get(expected.emission_request_id)
            storage = driver.boundary.storage
            observed_ids = (
                {x.event_id for x in storage.pending_output + storage.admitted_events}
                | set(storage.consumed_ids)
            )
            if (expected.emission_request_id not in completed_output
                    or expected.emission_request_id not in driver.admitted_emission_ids
                    or confirmed_emission is None
                    or confirmed_emission.confirmation_boundary > item.confirmation_boundary
                    or not set(expected.route_request_ids) <= observed_ids):
                raise ValueError('historical STATE commit lacks authenticated OUTPUT publication')
        elif item.emission_binding is not None:
            raise ValueError('output-free historical commit has spurious OUTPUT binding')
        committed = commit_core_transition_v0(network, image, trans)
        if committed.receipt != item.receipt:
            raise ValueError('historical Core commit receipt mismatch')
        image = committed.state
        last_commit_boundary[trans.node_id] = item.confirmation_boundary
        for x in image.neurons:
            snapshots[(x.node_id, x.version)] = x
    if image != state.image:
        raise ValueError('current neuron image does not match audited commit history')
    return snapshots


def advance_owned_internal_reads_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedInternalReadStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> OwnedInternalReadStepV0:
    """Advance one SERVICE_TIME tick and authenticate finished P/S reads.

    Never accepts caller-claimed read effects or service confirmation IDs.
    A real P/S read happens *after* its service quantum is exhausted, at the
    new boundary. Prepared Core transitions are NOT committed or published.
    """
    if type(state) is not OwnedInternalReadStateV0:
        raise TypeError('invalid internal read owner state')
    if type(network) is not NetworkV0 or type(state.image) is not VersionedNeuronImageV0:
        raise TypeError('invalid network or versioned image')
    if state.image.network != network or state.image.epoch_id != manifest.epoch_id:
        raise ValueError('network/image/epoch mismatch')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    ids = [r.request_id for r in requests]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate request')
    by_id = {r.request_id: r for r in requests}
    consumes = [r for r in requests if r.kind is Kind.BATCH_CONSUME]
    nodes = {n.node_id: n for n in network.nodes}
    _canonical_unique(state.pending_batches, lambda x: x.consume_request_id, 'pending batch IDs')
    _canonical_unique(state.reads, lambda x: x.request_id, 'internal read IDs')
    _canonical_unique(state.prepared, lambda x: x.consume_request_id, 'prepared batch IDs')

    # Enforce a unique, time-specific pair of read requests for every declared
    # neuronal batch; other internal effects remain outside this owner.
    read_by_batch = {}
    for consume in consumes:
        if not consume.target_id.startswith('events:'):
            raise ValueError('batch target must belong to a neuron')
        node_id = consume.target_id[len('events:'):]
        if (node_id not in nodes or consume.epoch_id != state.image.epoch_id
                or type(consume.event_time) is not int):
            raise ValueError('invalid batch identity')
        pair = {}
        for req in requests:
            if req.kind not in (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD):
                continue
            if req.event_time == consume.event_time and req.target_id in (
                    f'program:{node_id}', f'state:{node_id}'):
                _read_binding(req, consume, nodes, state.image.epoch_id)
                if req.kind in pair:
                    raise ValueError('duplicate P/S read for batch')
                pair[req.kind] = req
        if set(pair) != {Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD}:
            raise ValueError('batch lacks P/S read pair')
        read_by_batch[consume.request_id] = pair
    bound_reads = {r.request_id for pair in read_by_batch.values() for r in pair.values()}
    if bound_reads != {r.request_id for r in requests
                       if r.kind in (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD)}:
        raise ValueError('orphan or ambiguously bound P/S read')
    if len(bound_reads) != 2 * len(consumes):
        raise ValueError('P/S read reused across batches')

    svc_before = state.owned.boundary.service
    done_before = {item.request_id for item in svc_before.confirmed}
    awaiting_before = {item.request_id for item in svc_before.awaiting_confirmation}
    saved_read_ids = {item.request_id for item in state.reads}
    if saved_read_ids != done_before & bound_reads:
        raise ValueError('prior internal read confirmation lacks matching owner evidence')
    if saved_read_ids & awaiting_before:
        raise ValueError('internal read simultaneously confirmed and awaiting')
    snapshots = audit_committed_internal_history_v0(
        network, state, requests, graph, architecture=architecture,
        manifest=manifest, admission=admission,
    )
    committed_state_reads = {e.preparation.state_read_request_id for e in state.commits}
    for receipt in state.reads:
        r = by_id.get(receipt.request_id)
        if r is None or r.kind is not receipt.kind or r.target_id != f'{"program" if r.kind is Kind.PROGRAM_REFERENCE else "state"}:{receipt.node_id}':
            raise ValueError('read history/request mismatch')
        if (receipt.epoch_id != r.epoch_id or receipt.event_time != r.event_time
                or receipt.pe_id != r.target_pe_id
                or type(receipt.service_boundary) is not int
                or receipt.service_boundary > svc_before.next_service_tick):
            raise ValueError('invalid saved read identity or boundary')
        node = nodes[receipt.node_id]
        current = snapshots.get((receipt.node_id, receipt.state_version))
        if r.kind is Kind.PROGRAM_REFERENCE:
            if (receipt.config != node.config or receipt.program != node.program
                    or any(v is not None for v in
                           (receipt.raw, receipt.state_version, receipt.last_timestamp))):
                raise ValueError('saved program read does not match current P image')
        elif (current is None or receipt.raw != current.raw
              or receipt.last_timestamp != current.last_timestamp
              or receipt.program is not None or receipt.config is not None
              or (receipt.state_version != next(n.version for n in state.image.neurons
                                                if n.node_id == receipt.node_id)
                  and receipt.request_id not in committed_state_reads)):
            raise ValueError('saved state read is stale or altered')
    # Audit previous EVENT witnesses against the consumed identities still
    # retained by the authoritative storage ledgers. Never trust a history
    # tuple merely because it is a frozen dataclass.
    storage = state.owned.boundary.driver.boundary.storage
    event_ledger = state.owned.boundary.driver.boundary.ledger
    route_by_id = {r.route_request_id: r for r in manifest.routes}
    arrival_by_id = {a.input_index: a for a in event_ledger.ingress.arrivals}
    if len(route_by_id) != len(manifest.routes) or len(arrival_by_id) != len(event_ledger.ingress.arrivals):
        raise ValueError('nonunique historical EVENT provenance identities')
    for batch in state.pending_batches:
        req = by_id.get(batch.consume_request_id)
        if (req is None or req.kind is not Kind.BATCH_CONSUME
                or batch.node_id not in nodes
                or batch.epoch_id != state.image.epoch_id
                or batch.event_time != req.event_time
                or batch.target_pe_id != req.target_pe_id
                or req.target_id != f'events:{batch.node_id}'
                or batch.route_request_ids != tuple(sorted(set(batch.route_request_ids)))
                or batch.external_input_indices != tuple(sorted(set(batch.external_input_indices)))
                or not (batch.route_request_ids or batch.external_input_indices)
                or batch.service_boundary >= svc_before.next_service_tick):
            raise ValueError('invalid historical consumed batch identity')
        if (set(batch.route_request_ids) - set(storage.consumed_ids)
                or set(batch.external_input_indices) - set(event_ledger.external_consumed)):
            raise ValueError('historical batch lacks retained EVENT consumption')
        occurrences = []
        for rid in batch.route_request_ids:
            route = route_by_id.get(rid)
            if route is None or route.consume_request_id != batch.consume_request_id:
                raise ValueError('historical route not bound to batch')
            x = route.occurrence
            occurrences.append((x.target_node_id, x.target_pe_id, x.delivery_event_time, x.target_channel))
        for idx in batch.external_input_indices:
            arrival = arrival_by_id.get(idx)
            if arrival is None or arrival.consume_request_id != batch.consume_request_id:
                raise ValueError('historical external input not bound to batch')
            occurrences.append((arrival.node_id, arrival.target_pe_id, arrival.event_time, arrival.channel))
        if (any((n, pe, t) != (batch.node_id, batch.target_pe_id, batch.event_time)
                for n, pe, t, _ in occurrences)
                or batch.channels != tuple(sorted(ch for _, _, _, ch in occurrences))
                or len(batch.channels) != req.quantity):
            raise ValueError('historical consumed channels disagree with EVENT bindings')
    for prepared in state.prepared:
        batch = next((b for b in state.pending_batches
                      if b.consume_request_id == prepared.consume_request_id), None)
        if batch is None:
            raise ValueError('prepared transition without witnessed batch')
        pair = read_by_batch.get(batch.consume_request_id)
        if (pair is None or prepared.program_read_request_id != pair[Kind.PROGRAM_REFERENCE].request_id
                or prepared.state_read_request_id != pair[Kind.STATE_LOAD].request_id
                or prepared.transition != prepare_core_transition_v0(
                    network, state.image, node_id=batch.node_id,
                    timestamp=batch.event_time, channels=batch.channels)):
            raise ValueError('prepared transition disagrees with immutable Core image')
    if len({p.transition.node_id for p in state.prepared}) != len(state.prepared):
        raise ValueError('multiple outstanding preparations for same neuron')
    # Only the existing controller can supply newly consumed EVENT batches.
    # STATE_COMMIT requests own publication and may remain awaiting while
    # their paired emission accumulates service. Do not publish them early.
    commits_to_emit = {(r.target_id.split(':', 1)[1], r.event_time)
                       for r in requests if r.kind is Kind.STATE_COMMIT
                       and r.target_id.startswith('state:')}
    deferred = tuple(sorted(group.emission_request_id for group in admission.groups
                            if (group.source_node_id, group.emission_event_time)
                            in commits_to_emit))
    witnessed = advance_witnessed_core_input_tick_v0(
        architecture, network, manifest, admission, requests, graph,
        state.owned, ingress=ingress,
        allow_owned_internal_awaiting=True, deferred_emission_ids=deferred,
    )
    owned_after = witnessed.owned_tick.result.state
    quantum = owned_after.boundary.service
    awaiting = {item.request_id: item for item in quantum.awaiting_confirmation}
    confirmed = {item.request_id for item in quantum.confirmed}
    new_reads = []
    for rid in sorted(bound_reads & set(awaiting)):
        req = by_id[rid]
        # Require a finished service period, never an in-progress request.
        if awaiting[rid].finish_boundary > quantum.next_service_tick:
            raise ValueError('internal read service not finished')
        node_id = req.target_id.split(':', 1)[1]
        current = next(n for n in state.image.neurons if n.node_id == node_id)
        node = nodes[node_id]
        if req.kind is Kind.PROGRAM_REFERENCE:
            evidence = InternalReadEvidenceV0(rid, req.kind, node_id, req.event_time,
                req.epoch_id, req.target_pe_id, quantum.next_service_tick,
                None, None, None, node.config, node.program)
        else:
            evidence = InternalReadEvidenceV0(rid, req.kind, node_id, req.event_time,
                req.epoch_id, req.target_pe_id, quantum.next_service_tick,
                current.version, current.raw, current.last_timestamp, None, None)
        new_reads.append(evidence)
    # Promote exclusively reads just performed on the owned immutable image.
    updated_svc = ServiceQuantumStateV0(
        next_service_tick=quantum.next_service_tick,
        partial=quantum.partial,
        awaiting_confirmation=tuple(item for item in quantum.awaiting_confirmation
                                    if item.request_id not in {e.request_id for e in new_reads}),
        confirmed=tuple(sorted(quantum.confirmed + tuple(
            ServiceConfirmedV0(e.request_id, quantum.next_service_tick) for e in new_reads),
            key=lambda item: item.request_id)),
    )
    updated_owned = replace(owned_after, boundary=replace(
        owned_after.boundary, service=updated_svc))
    pending = tuple(sorted(state.pending_batches + witnessed.consumed_batches,
                           key=lambda x: x.consume_request_id))
    _canonical_unique(pending, lambda x: x.consume_request_id, 'accumulated witnessed batch IDs')
    reads = tuple(sorted(state.reads + tuple(new_reads), key=lambda x: x.request_id))
    read_map = {r.request_id: r for r in reads}
    prepared = list(state.prepared)
    prepared_ids = {p.consume_request_id for p in prepared}
    new_preparations = []
    busy_nodes = {p.transition.node_id for p in prepared}
    committed_consumes = {c.preparation.consume_request_id for c in state.commits}
    for batch in pending:
        if batch.consume_request_id in committed_consumes:
            continue
        if batch.consume_request_id in prepared_ids or batch.node_id in busy_nodes:
            continue
        pair = read_by_batch.get(batch.consume_request_id)
        if pair is None:
            raise ValueError('witnessed consume ID has no read pair')
        p = read_map.get(pair[Kind.PROGRAM_REFERENCE].request_id)
        s = read_map.get(pair[Kind.STATE_LOAD].request_id)
        if p is None or s is None:
            continue
        if (batch.epoch_id != state.image.epoch_id or p.node_id != batch.node_id
                or s.node_id != batch.node_id or p.event_time != batch.event_time
                or s.event_time != batch.event_time
                or p.pe_id != batch.target_pe_id or s.pe_id != batch.target_pe_id):
            raise ValueError('P/S read and consumed batch mismatch')
        current = next(n for n in state.image.neurons if n.node_id == batch.node_id)
        node = nodes[batch.node_id]
        if (p.config != node.config or p.program != node.program
                or s.state_version != current.version or s.raw != current.raw
                or s.last_timestamp != current.last_timestamp):
            raise ValueError('stale P/S read or changed neuronal image')
        transition = prepare_core_transition_v0(
            network, state.image, node_id=batch.node_id,
            timestamp=batch.event_time, channels=batch.channels,
        )
        record = BoundCorePreparationV0(batch.consume_request_id,
            p.request_id, s.request_id, transition)
        prepared.append(record)
        new_preparations.append(record)
        busy_nodes.add(batch.node_id)
    _canonical_unique(tuple(sorted(prepared, key=lambda x: x.consume_request_id)),
                      lambda x: x.consume_request_id, 'prepared result IDs')
    return OwnedInternalReadStepV0(
        witnessed, tuple(new_reads), tuple(new_preparations),
        OwnedInternalReadStateV0(updated_owned, state.image, pending, reads,
            tuple(sorted(prepared, key=lambda x: x.consume_request_id)), state.commits),
    )
