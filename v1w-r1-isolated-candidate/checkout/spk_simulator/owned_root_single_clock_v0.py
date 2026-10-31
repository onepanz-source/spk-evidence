"""SPK k24b: one clock for finite root EVENT input and physical P/S service.

Narrow owned experimental path: P/S reads, root BATCH_CONSUME, Core prepare.
STATE_COMMIT and output publication are intentionally NOT scheduled here.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceConfirmedV0, advance_service_quantum_v0,
)
from spk_simulator.owned_shared_event_cycle_v0 import (
    OwnedSharedEventCycleStateV0, SharedExternalIngressOverflowV0,
    owned_shared_event_usage_v0,
)
from spk_simulator.owned_dynamic_route_transit_v0 import OwnedDynamicRouteTransitStateV0
from spk_simulator.owned_dynamic_route_service_cycle_v0 import OwnedDynamicRouteServiceCycleStateV0
from spk_simulator.owned_sealed_root_batch_v0 import analyze_owned_sealed_root_batches_v0
from spk_simulator.owned_root_core_handoff_v0 import (
    OwnedRootCoreHandoffStateV0, _witness,
)
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, initialize_neuron_image_v0, prepare_core_transition_v0,
)
from spk_simulator.witnessed_core_input_v0 import WitnessedCoreInputBatchV0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0


@dataclass(frozen=True, slots=True)
class RootPhysicalReadV0:
    request_id: int
    kind: Kind
    node_id: str
    event_time: int
    boundary: int
    value: object


@dataclass(frozen=True, slots=True)
class RootPreparedV0:
    consume_request_id: int
    transition: object


@dataclass(frozen=True, slots=True)
class OwnedRootSingleClockStateV0:
    shared: OwnedSharedEventCycleStateV0
    image: VersionedNeuronImageV0
    reads: tuple[RootPhysicalReadV0, ...] = ()
    witnesses: tuple[WitnessedCoreInputBatchV0, ...] = ()
    prepared: tuple[RootPreparedV0, ...] = ()

    def __post_init__(self):
        if type(self.shared) is not OwnedSharedEventCycleStateV0:
            raise TypeError('invalid shared EVENT snapshot')
        if type(self.image) is not VersionedNeuronImageV0:
            raise TypeError('invalid Core image')
        registry = self.shared.dynamic.transit.registry
        network = registry.allocation_ledger.network
        if self.image.network != network or self.image.epoch_id != self.shared.seal.epoch_id:
            raise ValueError('Core image / owned EVENT epoch mismatch')
        if type(self.reads) is not tuple or any(type(x) is not RootPhysicalReadV0 for x in self.reads):
            raise TypeError('invalid physical P/S receipts')
        if type(self.prepared) is not tuple or any(type(x) is not RootPreparedV0 for x in self.prepared):
            raise TypeError('invalid Core preparations')
        if (registry.registrations or self.shared.dynamic.reserved_route_request_ids or
                self.shared.dynamic.transit.storage.pending_output or
                self.shared.dynamic.transit.storage.admitted_events):
            raise ValueError('root-only owner cannot accept dynamic routing state')
        by_id = {r.request_id: r for r in registry.base_requests}
        if len(by_id) != len(registry.base_requests):
            raise ValueError('duplicate service request IDs')
        service = self.shared.dynamic.transit.service
        live_ids = {x.request_id for x in (
            service.partial + service.awaiting_confirmation + service.confirmed)}
        if live_ids - set(by_id):
            raise ValueError('unknown service ID in owner snapshot')
        active_commit = {rid for rid in live_ids
                         if by_id[rid].kind is Kind.STATE_COMMIT}
        if active_commit:
            raise ValueError('STATE_COMMIT outside root P/S-EVENT owner')
        confirmations = {x.request_id: x.confirmation_boundary
                         for x in self.shared.dynamic.transit.service.confirmed}
        if tuple(x.request_id for x in self.reads) != tuple(sorted(x.request_id for x in self.reads)):
            raise ValueError('noncanonical P/S receipt order')
        reads_seen = set()
        for read in self.reads:
            req = by_id.get(read.request_id)
            if (req is None or req.kind != read.kind or read.kind not in
                    (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD) or
                    read.request_id in reads_seen or
                    confirmations.get(read.request_id) != read.boundary or
                    read.event_time != req.event_time):
                raise ValueError('physical P/S receipt without matching finished service')
            reads_seen.add(read.request_id)
            node = read.node_id
            if req.target_id != f'{"program" if read.kind is Kind.PROGRAM_REFERENCE else "state"}:{node}':
                raise ValueError('physical P/S receipt target mismatch')
            if read.kind is Kind.PROGRAM_REFERENCE:
                active = next(x for x in network.nodes if x.node_id == node)
                if read.value != (active.config, active.program):
                    raise ValueError('program receipt does not match active P image')
            else:
                version = next(x for x in self.image.neurons if x.node_id == node)
                if read.value != (version.raw, version.last_timestamp, version.version):
                    raise ValueError('state receipt does not match active S image')
        confirmed_ps = {rid for rid in confirmations
                        if by_id[rid].kind in (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD)}
        if reads_seen != confirmed_ps:
            raise ValueError('P/S confirmation/physical read receipt coverage mismatch')
        # Existing owner validates EVERY external tombstone and service confirmation.
        OwnedRootCoreHandoffStateV0(self.shared, self.witnesses)
        batches = serialize_internal_access_graph_v0(
            registry.base_requests, registry.base_graph).batches
        if tuple(x.consume_request_id for x in self.prepared) != tuple(
                sorted(x.consume_request_id for x in self.prepared)):
            raise ValueError('noncanonical Core preparation order')
        prepared_ids = set()
        for p in self.prepared:
            if p.consume_request_id in prepared_ids:
                raise ValueError('duplicate Core preparation')
            prepared_ids.add(p.consume_request_id)
            binding = next((b for b in batches if b.consume_request_id == p.consume_request_id), None)
            witness = next((w for w in self.witnesses
                            if w.consume_request_id == p.consume_request_id), None)
            if binding is None or witness is None:
                raise ValueError('Core preparation lacks physical root EVENT witness')
            trans = prepare_core_transition_v0(
                network, self.image, node_id=witness.node_id,
                timestamp=witness.event_time, channels=witness.channels,
            )
            if p.transition != trans:
                raise ValueError('prepared Core differs from frozen computation')
            if not {binding.program_request_id, binding.state_load_request_id} <= reads_seen:
                raise ValueError('Core preparation lacks real P/S reads')


@dataclass(frozen=True, slots=True)
class OwnedRootSingleClockStepV0:
    service_tick: int
    admitted_external_input_indices: tuple[int, ...]
    consumed_external_input_indices: tuple[int, ...]
    confirmed_request_ids: tuple[int, ...]
    newly_read_request_ids: tuple[int, ...]
    newly_prepared_consume_request_ids: tuple[int, ...]
    service_slices: tuple
    state: OwnedRootSingleClockStateV0


def initialize_owned_root_single_clock_v0(shared: OwnedSharedEventCycleStateV0):
    """Initialize ONLY from untouched P/S and EVENT service state, no preconfirmed IDs."""
    if type(shared) is not OwnedSharedEventCycleStateV0:
        raise TypeError('invalid initial owned shared EVENT state')
    registry = shared.dynamic.transit.registry
    service = shared.dynamic.transit.service
    if (service.partial or service.confirmed or service.awaiting_confirmation or
            shared.external_resident_input_indices or shared.external_consumed_input_indices or
            shared.dynamic.reserved_route_request_ids or registry.registrations or
            shared.dynamic.transit.storage.pending_output or
            shared.dynamic.transit.storage.admitted_events):
        raise ValueError('single clock must initialize from fresh, unconfirmed epoch')
    serialized = serialize_internal_access_graph_v0(registry.base_requests, registry.base_graph)
    if serialized.graph != registry.base_graph:
        raise ValueError('root access graph lacks serialized causal dependencies')
    batches = serialized.batches
    if not batches:
        raise ValueError('root clock needs a neuronal batch')
    by_id = {x.request_id: x for x in registry.base_requests}
    incoming = {e.target_node for e in registry.allocation_ledger.network.edges}
    for b in batches:
        if b.node_id in incoming:
            raise ValueError('nonroot batch is not supported')
        if {by_id[x].kind for x in (b.program_request_id, b.state_load_request_id,
                                      b.consume_request_id, b.state_commit_request_id)} != {
            Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD, Kind.BATCH_CONSUME, Kind.STATE_COMMIT
        }:
            raise ValueError('invalid canonical root P/S/EVENT/COMMIT batch')
    if len(batches) * 4 != len(registry.base_requests):
        raise ValueError('root clock owns only canonical static requests')
    return OwnedRootSingleClockStateV0(
        shared, initialize_neuron_image_v0(registry.allocation_ledger.network,
                                           epoch_id=shared.seal.epoch_id),
    )


def _shared_with(state, service, resident, consumed):
    transit = state.dynamic.transit
    transit = OwnedDynamicRouteTransitStateV0(transit.registry, transit.storage, service)
    dynamic = OwnedDynamicRouteServiceCycleStateV0(
        transit, state.dynamic.reserved_route_request_ids)
    return OwnedSharedEventCycleStateV0(dynamic, state.seal,
                                        tuple(sorted(resident)), tuple(sorted(consumed)))


def advance_owned_root_single_clock_v0(state: OwnedRootSingleClockStateV0):
    """Exactly one SERVICE_TIME step, own P/S completions and root EVENT effects.

    STATE_COMMIT is never scheduled. Output-free commit authority is deliberately
    postponed to the next integration phase; no state version is invented.
    """
    if type(state) is not OwnedRootSingleClockStateV0:
        raise TypeError('invalid root owner')
    state.__post_init__()
    shared = state.shared
    transit = shared.dynamic.transit
    registry = transit.registry
    service = transit.service
    tick = service.next_service_tick
    by_id = {x.request_id: x for x in registry.base_requests}
    batches = serialize_internal_access_graph_v0(registry.base_requests,registry.base_graph).batches
    network = registry.allocation_ledger.network
    waiting = tuple(service.awaiting_confirmation)
    # This restricted owner can never acquire an unexpected outstanding effect.
    if any(by_id[x.request_id].kind is Kind.STATE_COMMIT for x in waiting):
        raise ValueError('STATE_COMMIT requires independent atomic commit owner')
    consumption = set()
    confirmed = []
    new_reads = []
    new_witnesses = []
    residents = set(shared.external_resident_input_indices)
    consumed = set(shared.external_consumed_input_indices)
    root_candidates = {b.consume_request_id:b for b in analyze_owned_sealed_root_batches_v0(shared).batches}
    for finished in waiting:
        req = by_id[finished.request_id]
        if finished.finish_boundary > tick:
            raise ValueError('premature service confirmation')
        if req.kind in (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD):
            prefix = 'program:' if req.kind is Kind.PROGRAM_REFERENCE else 'state:'
            if not req.target_id.startswith(prefix):
                raise ValueError('P/S target mismatch')
            node_id = req.target_id[len(prefix):]
            node = next(x for x in network.nodes if x.node_id == node_id)
            value = ((node.config, node.program) if req.kind is Kind.PROGRAM_REFERENCE else
                     next((x.raw, x.last_timestamp, x.version)
                          for x in state.image.neurons if x.node_id == node_id))
            new_reads.append(RootPhysicalReadV0(
                req.request_id, req.kind, node_id, req.event_time, tick, value))
        elif req.kind is Kind.BATCH_CONSUME:
            batch = root_candidates.get(req.request_id)
            if batch is None or not batch.sealed_input_set_complete:
                raise ValueError('finished root batch is not physically complete')
            indices = set(batch.expected_external_indices)
            if not indices <= residents or indices & consumed:
                raise ValueError('root batch missing physical EVENT occurrences')
            residents -= indices
            consumed |= indices
            consumption |= indices
            # Create after service-confirmed shared state below.
            new_witnesses.append(req.request_id)
        else:
            raise ValueError('unowned service completion')
        confirmed.append(req.request_id)
    confirmed = tuple(sorted(confirmed))
    # Admit all due inputs (mandatory, cannot delay or evict reservations).
    used = {x.pe_id: x.claimed for x in owned_shared_event_usage_v0(shared)}
    slots = {x.pe_id: x.event_slots for x in registry.architecture.pes}
    arrivals = shared.seal.binding.arrivals
    for i in consumption:
        used[arrivals[i].target_pe_id] -= 1
    admitted = []
    for a in arrivals:
        if a.arrival_boundary != tick:
            continue
        if used[a.target_pe_id] >= slots[a.target_pe_id]:
            raise SharedExternalIngressOverflowV0(
                tick, a.input_index, a.target_pe_id, used[a.target_pe_id], slots[a.target_pe_id])
        residents.add(a.input_index)
        used[a.target_pe_id] += 1
        admitted.append(a.input_index)
    # Build provisional post-effect owner only for authentication of newly consumed IDs.
    provisional_service = replace(
        service, next_service_tick=tick + 1,
        awaiting_confirmation=tuple(x for x in waiting if x.request_id not in confirmed),
        confirmed=tuple(sorted(service.confirmed +
                               tuple(ServiceConfirmedV0(i, tick) for i in confirmed),
                               key=lambda x:x.request_id)))
    provisional_shared = _shared_with(shared, provisional_service, residents, consumed)
    witnesses = tuple(sorted(
        state.witnesses + tuple(_witness(provisional_shared, rid, tick)
                                for rid in new_witnesses),
        key=lambda x: x.consume_request_id))
    reads = tuple(sorted(state.reads + tuple(new_reads), key=lambda x:x.request_id))
    prepared = list(state.prepared)
    newly_prepared = []
    read_ids = {x.request_id for x in reads}
    witness_ids = {w.consume_request_id for w in witnesses}
    for b in batches:
        if (b.consume_request_id not in witness_ids or
            not {b.program_request_id,b.state_load_request_id} <= read_ids or
            any(p.consume_request_id == b.consume_request_id for p in prepared)):
            continue
        witness = next(w for w in witnesses if w.consume_request_id == b.consume_request_id)
        prep = prepare_core_transition_v0(
            network, state.image, node_id=witness.node_id,
            timestamp=witness.event_time, channels=witness.channels)
        prepared.append(RootPreparedV0(b.consume_request_id, prep))
        newly_prepared.append(b.consume_request_id)
    prepared = tuple(sorted(prepared, key=lambda p:p.consume_request_id))
    # Determine owned executable subset from the true post-admission ledger.
    audited = analyze_owned_sealed_root_batches_v0(provisional_shared)
    root_ready = {b.consume_request_id for b in audited.batches if b.sealed_input_set_complete}
    completed = {x.request_id for x in provisional_service.confirmed}
    pending = {x.request_id for x in provisional_service.awaiting_confirmation}
    partial = {x.request_id for x in provisional_service.partial}
    dispatch = set(partial)
    for req in registry.base_requests:
        if req.request_id in completed | pending | partial:
            continue
        if req.kind in (Kind.PROGRAM_REFERENCE,Kind.STATE_LOAD):
            dispatch.add(req.request_id)
        elif req.kind is Kind.BATCH_CONSUME and req.request_id in root_ready:
            dispatch.add(req.request_id)
        # STATE_COMMIT deliberately not dispatched by this partial owner.
    dispatch = tuple(sorted(dispatch))
    quantum = advance_service_quantum_v0(
        registry.architecture, registry.staged_requests, registry.staged_graph,
        service, confirmed_request_ids=confirmed,
        ingress=shared.seal.binding,
        owned_service_request_ids=dispatch,
    )
    successor = _shared_with(shared, quantum.state, residents, consumed)
    owner = OwnedRootSingleClockStateV0(successor, state.image, reads, witnesses, prepared)
    return OwnedRootSingleClockStepV0(
        tick, tuple(admitted), tuple(sorted(consumption)), confirmed,
        tuple(x.request_id for x in new_reads), tuple(newly_prepared),
        quantum.slices, owner,
    )
