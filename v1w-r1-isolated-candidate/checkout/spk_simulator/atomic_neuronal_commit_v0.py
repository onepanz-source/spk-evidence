"""SPK S3.7d/3b2b2k/8: immutable STATE/OUTPUT atomic owner for routed emissions.

No precalculated Network result is consumed. The routing *manifest* and admission
remain upstream constraints, not autonomous topology discovery. The only success
path publishes through the bounded controller and commits a recomputed Core
transition in one returned successor state. No intermediate state is exported.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.bounded_backpressure_driver_v0 import BackpressureServiceFrameV0
from spk_simulator.causal_service_quantum_v0 import ServiceConfirmedV0, ServiceQuantumStateV0
from spk_simulator.computed_emission_binding_v0 import (
    ComputedEmissionBindingV0, bind_computed_emission_v0,
)
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.owned_internal_reads_v0 import (
    OwnedInternalReadStateV0, OwnedInternalCommitEvidenceV0,
    audit_committed_internal_history_v0,
)
from spk_simulator.owned_service_tick_v0 import (
    OwnedServiceTickResultV0, advance_owned_service_tick_v0,
)
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import commit_core_transition_v0


@dataclass(frozen=True, slots=True)
class AtomicNeuronalCommitStepV0:
    commit_request_id: int
    emission_request_id: int
    publication: ComputedEmissionBindingV0
    owner_tick: OwnedServiceTickResultV0
    evidence: OwnedInternalCommitEvidenceV0
    state: OwnedInternalReadStateV0


def commit_atomic_neuronal_output_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedInternalReadStateV0,
    *,
    commit_request_id: int,
    emission_request_id: int,
    ingress: ExternalIngressBindingV0 | None = None,
) -> AtomicNeuronalCommitStepV0:
    """Atomically return both STATE commit and verified routed OUTPUT publication.

    Require a finished service quantum for BOTH requests and an existing
    reservation for the complete output bundle. Any error raises before a
    successor snapshot is returned. Never silently converts SERVICE_TIME to
    EVENT_TIME. Terminal-only outputs are unsupported in this v0 subset.
    """
    if (type(architecture) is not ArchitectureProfileV0 or type(network) is not NetworkV0
            or type(manifest) is not RoutedBindingManifestV0
            or type(admission) is not AtomicEmissionAdmissionV0
            or type(graph) is not AccessDependencyGraphV0
            or type(state) is not OwnedInternalReadStateV0):
        raise TypeError('invalid atomic neuronal owner input')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    if (type(commit_request_id) is not int or commit_request_id < 0
            or type(emission_request_id) is not int or emission_request_id < 0):
        raise ValueError('invalid atomic request identities')
    if (state.image.network != network or state.image.epoch_id != manifest.epoch_id
            or admission.epoch_id != manifest.epoch_id
            or architecture.profile_id != manifest.profile_id):
        raise ValueError('atomic network/profile/epoch mismatch')
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate service identities')
    serialized = serialize_internal_access_graph_v0(requests, graph)
    if serialized.graph != graph:
        raise ValueError('atomic STATE_COMMIT requires serialized causal graph')
    batch = {b.state_commit_request_id: b for b in serialized.batches}.get(commit_request_id)
    commit_req = by_id.get(commit_request_id)
    emit_req = by_id.get(emission_request_id)
    if batch is None or commit_req is None or emit_req is None:
        raise ValueError('missing atomic STATE/OUTPUT service request')
    if (commit_req.kind is not Kind.STATE_COMMIT or commit_req.domain is not Domain.STATE
            or commit_req.target_id != f'state:{batch.node_id}'
            or commit_req.event_time != batch.event_time
            or commit_req.target_pe_id != batch.target_pe_id
            or commit_req.epoch_id != state.image.epoch_id or commit_req.quantity != 1
            or emit_req.kind is not Kind.EMISSION_RECORD
            or emit_req.target_id != f'outputs:{batch.node_id}'
            or emit_req.event_time != batch.event_time
            or emit_req.target_pe_id != batch.target_pe_id
            or emit_req.epoch_id != state.image.epoch_id):
        raise ValueError('STATE/OUTPUT batch target or EVENT_TIME mismatch')
    svc = state.owned.boundary.service
    awaiting = {x.request_id: x.finish_boundary for x in svc.awaiting_confirmation}
    confirmed = {x.request_id for x in svc.confirmed}
    boundary = svc.next_service_tick
    if (commit_request_id not in awaiting or awaiting[commit_request_id] > boundary
            or emission_request_id not in awaiting or awaiting[emission_request_id] > boundary):
        raise ValueError('STATE/OUTPUT service has not finished')
    if commit_request_id in confirmed or emission_request_id in confirmed:
        raise ValueError('atomic STATE/OUTPUT request already confirmed')
    predecessor = next(x for x in graph.dependencies if x.request_id == commit_request_id)
    pred = predecessor.predecessor_ids if hasattr(predecessor, 'predecessor_ids') else predecessor.predecessors
    if not set(pred) <= confirmed:
        raise ValueError('STATE_COMMIT predecessor not confirmed')
    if batch.previous_commit_request_id is not None and batch.previous_commit_request_id not in confirmed:
        raise ValueError('prior neuron commit unconfirmed')

    snapshots = audit_committed_internal_history_v0(
        network, state, requests, graph,
        architecture=architecture, manifest=manifest, admission=admission,
    )
    preparations = [x for x in state.prepared if x.consume_request_id == batch.consume_request_id]
    if len(preparations) != 1:
        raise ValueError('missing unique witnessed Core preparation')
    preparation = preparations[0]
    trans = preparation.transition
    witnessed = next((x for x in state.pending_batches
                     if x.consume_request_id == batch.consume_request_id), None)
    reads = {x.request_id: x for x in state.reads}
    p = reads.get(batch.program_request_id)
    s = reads.get(batch.state_load_request_id)
    if (witnessed is None or p is None or s is None
            or preparation.program_read_request_id != batch.program_request_id
            or preparation.state_read_request_id != batch.state_load_request_id
            or not {batch.program_request_id, batch.state_load_request_id, batch.consume_request_id} <= confirmed
            or p.kind is not Kind.PROGRAM_REFERENCE or s.kind is not Kind.STATE_LOAD
            or trans.node_id != batch.node_id or trans.event_time != batch.event_time
            or trans.epoch_id != batch.epoch_id or trans.channels != witnessed.channels
            or witnessed.node_id != batch.node_id or witnessed.event_time != batch.event_time):
        raise ValueError('atomic Core inputs lack authenticated P/S/EVENT service')
    image_node = next(x for x in state.image.neurons if x.node_id == batch.node_id)
    node = next(x for x in network.nodes if x.node_id == batch.node_id)
    if (s.state_version != image_node.version or s.raw != image_node.raw
            or s.last_timestamp != image_node.last_timestamp
            or snapshots.get((batch.node_id, image_node.version)) != image_node
            or p.program != node.program or p.config != node.config
            or trans.base_version != image_node.version):
        raise ValueError('stale or mismatched P/S read for atomic transition')
    # Reconcile the input channels against the actual consumed occurrence IDs.
    driver = state.owned.boundary.driver
    storage = driver.boundary.storage
    ingress_ledger = driver.boundary.ledger
    route_map = {x.route_request_id: x for x in manifest.routes}
    arrivals = {x.input_index: x for x in ingress_ledger.ingress.arrivals}
    if not witnessed.route_request_ids and not witnessed.external_input_indices:
        raise ValueError('Core preparation has no witnessed EVENT input')
    if (set(witnessed.route_request_ids) - set(storage.consumed_ids)
            or set(witnessed.external_input_indices) - set(ingress_ledger.external_consumed)):
        raise ValueError('missing actual EVENT consumption tombstone')
    actual = []
    for rid in witnessed.route_request_ids:
        route = route_map.get(rid)
        if route is None or route.consume_request_id != batch.consume_request_id:
            raise ValueError('invalid witnessed route for atomic batch')
        x = route.occurrence
        actual.append((x.target_node_id, x.target_pe_id, x.delivery_event_time, x.target_channel))
    for idx in witnessed.external_input_indices:
        arrival = arrivals.get(idx)
        if arrival is None or arrival.consume_request_id != batch.consume_request_id:
            raise ValueError('invalid witnessed external input')
        actual.append((arrival.node_id, arrival.target_pe_id, arrival.event_time, arrival.channel))
    if (any((n, pe, et) != (batch.node_id, batch.target_pe_id, batch.event_time)
            for n, pe, et, _ in actual)
            or tuple(sorted(ch for _, _, _, ch in actual)) != witnessed.channels):
        raise ValueError('EVENT witness identities disagree with computed channels')

    binding = bind_computed_emission_v0(
        architecture, network, state.image, trans, manifest, admission,
        requests, emission_request_id=emission_request_id,
    )
    if not binding.route_request_ids:
        raise ValueError('terminal-only Core emission not supported by atomic owner v0')
    if emission_request_id not in {x.emission_request_id for x in state.owned.output.active}:
        raise ValueError('no live OUTPUT reservation for Core emission')
    # The existing controller produces the only authoritative OFFER evidence.
    # The returned state is not exposed until the Core commit also succeeds.
    frame = BackpressureServiceFrameV0(
        service_boundary=boundary, new_ready_emission_ids=(emission_request_id,),
    )
    offered = advance_owned_service_tick_v0(
        architecture, manifest, admission, requests, graph, state.owned,
        frame, ingress=ingress,
    )
    effects = offered.authenticated_effects.effects
    published = [e for e in effects if e.request_id == emission_request_id
                 and e.kind is Kind.EMISSION_RECORD]
    if (len(published) != 1
            or published[0].route_request_ids != binding.route_request_ids
            or emission_request_id not in offered.state.output.completed_emission_ids):
        raise ValueError('full computed emission was not physically published')
    # Exact publication identities must materialize in OUTPUT *at this boundary*.
    before_ids = {x.event_id for x in storage.pending_output}
    after_storage = offered.state.boundary.driver.boundary.storage
    new_pending = {x.event_id for x in after_storage.pending_output} - before_ids
    if new_pending != set(binding.route_request_ids):
        raise ValueError('atomic OUTPUT publication did not occupy all routed slots')
    committed = commit_core_transition_v0(network, state.image, trans)
    after_svc = offered.state.boundary.service
    if commit_request_id not in {x.request_id for x in after_svc.awaiting_confirmation}:
        raise ValueError('STATE_COMMIT service vanished during publication')
    confirmation_boundary = after_svc.next_service_tick
    final_service = ServiceQuantumStateV0(
        next_service_tick=confirmation_boundary,
        partial=after_svc.partial,
        awaiting_confirmation=tuple(x for x in after_svc.awaiting_confirmation
                                    if x.request_id != commit_request_id),
        confirmed=tuple(sorted(after_svc.confirmed + (
            ServiceConfirmedV0(commit_request_id, confirmation_boundary),
        ), key=lambda x: x.request_id)),
    )
    evidence = OwnedInternalCommitEvidenceV0(
        commit_request_id, preparation, committed.receipt,
        confirmation_boundary, binding,
    )
    after_owned = replace(offered.state, boundary=replace(
        offered.state.boundary, service=final_service,
    ))
    next_state = replace(
        state, owned=after_owned, image=committed.state,
        prepared=tuple(x for x in state.prepared
                       if x.consume_request_id != batch.consume_request_id),
        commits=state.commits + (evidence,),
    )
    audit_committed_internal_history_v0(
        network, next_state, requests, graph,
        architecture=architecture, manifest=manifest, admission=admission,
    )
    return AtomicNeuronalCommitStepV0(
        commit_request_id, emission_request_id, binding,
        offered, evidence, next_state,
    )
