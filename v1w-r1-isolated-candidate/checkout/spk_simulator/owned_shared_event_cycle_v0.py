"""SPK S3.7d/3b2b2k/20: joint finite EVENT ownership for external + computed routes.

Admission of SEALED external occurrences happens at exact SERVICE_TIME boundaries
before any new dynamic route capacity grants. The same immutable snapshot counts
external residents, routed EVENT residents and route reservations against ONE
physical per-PE capacity. The original shared-cycle transition never consumes
external input; a separate sealed-root consumption owner may now retain
confirmed consumption tombstones in the same state. No general scheduler.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import advance_service_quantum_v0
from spk_simulator.owned_dynamic_route_service_cycle_v0 import (
    OwnedDynamicRouteServiceCycleStateV0,
)
from spk_simulator.owned_dynamic_route_transit_v0 import (
    OwnedDynamicRouteTransitStateV0,
    advance_owned_dynamic_route_transit_v0,
)
from spk_simulator.owned_external_ingress_prefix_v0 import (
    SealedExternalIngressEpochV0, seal_finite_external_ingress_v0,
)


def _occurrences(registry):
    return {
        route.occurrence.event_id: route.occurrence
        for registration in registry.registrations
        for route in registration.allocation.topology.routes
    }


class SharedExternalIngressOverflowV0(RuntimeError):
    """Non-backpressurable, due external ingress has no physical EVENT slot."""
    code = 'EXTERNAL_INGRESS_OVERFLOW'

    def __init__(self, boundary, input_index, pe_id, claimed, capacity):
        self.service_boundary = boundary
        self.input_index = input_index
        self.pe_id = pe_id
        self.claimed = claimed
        self.capacity = capacity
        super().__init__(
            f'EXTERNAL_INGRESS_OVERFLOW: SERVICE_TIME={boundary} input={input_index} '
            f'PE={pe_id} occupied={claimed} capacity={capacity}'
        )


@dataclass(frozen=True, slots=True)
class SharedEventPEUsageV0:
    pe_id: str
    event_capacity: int
    external_resident: int
    routed_resident: int
    routed_reserved: int
    claimed: int
    free: int


@dataclass(frozen=True, slots=True)
class OwnedSharedEventCycleStateV0:
    """Single snapshot owning BOTH external residency and dynamic route claims.

    The seal and initial snapshot must be installed by a trusted epoch owner.
    `external_consumed_input_indices` are historical tombstones; the separate
    root batch consumption owner produces new ones after service completion.
    A caller can forge an initial history; this dataclass cannot attest it.
    """
    dynamic: OwnedDynamicRouteServiceCycleStateV0
    seal: SealedExternalIngressEpochV0
    external_resident_input_indices: tuple[int, ...] = ()
    external_consumed_input_indices: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.dynamic) is not OwnedDynamicRouteServiceCycleStateV0:
            raise TypeError('invalid owned dynamic route service state')
        if type(self.seal) is not SealedExternalIngressEpochV0:
            raise TypeError('invalid sealed external ingress')
        ids = self.external_resident_input_indices
        consumed = self.external_consumed_input_indices
        if (type(consumed) is not tuple or
                any(type(x) is not int or x < 0 for x in consumed) or
                consumed != tuple(sorted(set(consumed)))):
            raise ValueError('noncanonical consumed external indices')
        if set(ids) & set(consumed):
            raise ValueError('external input simultaneously resident and consumed')
        if (type(ids) is not tuple or
                any(type(x) is not int or x < 0 for x in ids) or
                ids != tuple(sorted(set(ids)))):
            raise ValueError('noncanonical external resident indices')
        registry = self.dynamic.transit.registry
        arch = registry.architecture
        epoch = registry.allocation_ledger.epoch_id
        if self.seal.profile_id != arch.profile_id or self.seal.epoch_id != epoch:
            raise ValueError('external/dynamic profile or epoch mismatch')
        expected_seal = seal_finite_external_ingress_v0(
            arch, registry.allocation_ledger.network, self.seal.binding,
            epoch_id=epoch,
        )
        if expected_seal != self.seal:
            raise ValueError('altered external ingress seal')
        tick = self.dynamic.transit.service.next_service_tick
        arrivals = self.seal.binding.arrivals
        by_id = {a.input_index: a for a in arrivals}
        if (set(ids) | set(consumed)) - set(by_id):
            raise ValueError('external index not in sealed plan')
        past_due = {a.input_index for a in arrivals if a.arrival_boundary < tick}
        if set(ids) | set(consumed) != past_due:
            raise ValueError('external ingress history missing, early or forged')
        if consumed:
            confirmed = {r.request_id for r in self.dynamic.transit.service.confirmed}
            # The complete input multiplicity of one batch must be consumed
            # as one physical effect, and never before service confirmation.
            for rid in {by_id[i].consume_request_id for i in consumed}:
                batch = {a.input_index for a in arrivals if a.consume_request_id == rid}
                if not batch <= set(consumed) or rid not in confirmed:
                    raise ValueError('external consumed without complete confirmed batch')
            incoming = {edge.target_node for edge in registry.allocation_ledger.network.edges}
            if any(by_id[i].node_id in incoming for i in consumed):
                raise ValueError('nonroot external consumption is not owned')
            # No later logical batch may have been consumed while an earlier
            # batch of the same neuron remains resident or pending.
            for i in consumed:
                a = by_id[i]
                if any(b.node_id == a.node_id and b.event_time < a.event_time
                       and b.input_index not in consumed for b in arrivals):
                    raise ValueError('external consumption violates EVENT_TIME order')
        _usage(self.dynamic, ids, arrivals)


def _usage(dynamic, external_indices, arrivals):
    transit = dynamic.transit
    arch = transit.registry.architecture
    pes = {p.pe_id: p for p in arch.pes}
    external = {p: 0 for p in pes}
    routed = {p: 0 for p in pes}
    reserved = {p: 0 for p in pes}
    by_external = {a.input_index: a for a in arrivals}
    occurrences = _occurrences(transit.registry)
    for idx in external_indices:
        external[by_external[idx].target_pe_id] += 1
    for occurrence in transit.storage.admitted_events:
        routed[occurrence.target_pe_id] += 1
    for rid in dynamic.reserved_route_request_ids:
        reserved[occurrences[rid].target_pe_id] += 1
    usages = []
    for pe_id in sorted(pes):
        total = external[pe_id] + routed[pe_id] + reserved[pe_id]
        if total > pes[pe_id].event_slots:
            raise ValueError('shared EVENT capacity exceeded')
        usages.append(SharedEventPEUsageV0(
            pe_id, pes[pe_id].event_slots, external[pe_id],
            routed[pe_id], reserved[pe_id], total,
            pes[pe_id].event_slots - total,
        ))
    return tuple(usages)


def owned_shared_event_usage_v0(state: OwnedSharedEventCycleStateV0):
    """Audit the one physical EVENT slot budget across both lanes."""
    if type(state) is not OwnedSharedEventCycleStateV0:
        raise TypeError('invalid owned shared EVENT state')
    return _usage(
        state.dynamic, state.external_resident_input_indices,
        state.seal.binding.arrivals,
    )


@dataclass(frozen=True, slots=True)
class OwnedSharedEventCycleStepV0:
    service_tick: int
    admitted_external_input_indices: tuple[int, ...]
    newly_reserved_route_request_ids: tuple[int, ...]
    waiting_capacity_route_request_ids: tuple[int, ...]
    delivered_route_request_ids: tuple[int, ...]
    finished_route_request_ids: tuple[int, ...]
    service_slices: tuple
    pe_usage: tuple[SharedEventPEUsageV0, ...]
    state: OwnedSharedEventCycleStateV0
    status: str


def advance_owned_shared_event_cycle_v0(
    state: OwnedSharedEventCycleStateV0,
) -> OwnedSharedEventCycleStepV0:
    """One immutable SERVICE_TIME transition with one global EVENT budget.

    1. Non-backpressurable sealed external arrivals due *now* are mandatory.
    2. Free slots (if any) are claimed by routed events with stable ID priority.
    3. Service Quantum spends service only for dynamic ROUTE_ENQUEUEs.
    4. Finished routes enter EVENT physically and release their claims.

    An external capacity overflow raises and returns no new state. This cycle
    never consumes external inputs; those slots stay occupied until a future
    batch-consumption owner is introduced. TICK_LIMIT is not deadlock.
    """
    if type(state) is not OwnedSharedEventCycleStateV0:
        raise TypeError('invalid owned shared EVENT cycle')
    dynamic = state.dynamic
    transit = dynamic.transit
    registry = transit.registry
    service = transit.service
    stored = transit.storage
    arch = registry.architecture
    tick = service.next_service_tick
    routes = _occurrences(registry)
    arrivals = state.seal.binding.arrivals
    resident = set(state.external_resident_input_indices)
    capacity = {p.pe_id: p.event_slots for p in arch.pes}
    counts = {u.pe_id: u.claimed for u in owned_shared_event_usage_v0(state)}
    admitted = []
    # External arrivals cannot be delayed and cannot evict a reserved route.
    for arrival in arrivals:
        if arrival.arrival_boundary != tick:
            continue
        target = arrival.target_pe_id
        if counts[target] >= capacity[target]:
            raise SharedExternalIngressOverflowV0(
                tick, arrival.input_index, target, counts[target], capacity[target]
            )
        resident.add(arrival.input_index)
        admitted.append(arrival.input_index)
        counts[target] += 1

    reservations = set(dynamic.reserved_route_request_ids)
    confirmed = {x.request_id for x in service.confirmed}
    already = {x.request_id for x in service.partial + service.awaiting_confirmation}
    pending = {x.event_id for x in stored.pending_output}
    source_of = {
        rid: registration.allocation.emission_request_id
        for registration in registry.registrations
        for rid in registration.allocation.route_request_ids
    }
    granted, blocked = [], []
    for rid in sorted(routes):
        if rid not in pending or rid in confirmed | already | reservations:
            continue
        if source_of[rid] not in confirmed:
            continue
        target = routes[rid].target_pe_id
        if counts[target] >= capacity[target]:
            blocked.append(rid)
            continue
        reservations.add(rid)
        granted.append(rid)
        counts[target] += 1

    quantum = advance_service_quantum_v0(
        arch, registry.staged_requests, registry.staged_graph, service,
        granted_memory_request_ids=tuple(granted),
    )
    if any(s.request_id not in routes for s in quantum.slices):
        raise ValueError('unowned non-route service must be advanced by its authority')
    interim = OwnedDynamicRouteTransitStateV0(registry, stored, quantum.state)
    delivered = advance_owned_dynamic_route_transit_v0(interim)
    delivered_ids = set(delivered.delivered_route_request_ids)
    reservations.difference_update(delivered_ids)
    next_dynamic = OwnedDynamicRouteServiceCycleStateV0(
        delivered.state, tuple(sorted(reservations)),
    )
    successor = OwnedSharedEventCycleStateV0(
        next_dynamic, state.seal, tuple(sorted(resident)),
        state.external_consumed_input_indices,
    )
    finished = tuple(sorted(
        rid for rid in quantum.work_finished_request_ids if rid in routes
    ))
    if admitted and delivered_ids:
        status = 'EXTERNAL_AND_ROUTE_DELIVERED'
    elif admitted:
        status = 'EXTERNAL_ARRIVED'
    elif delivered_ids:
        status = 'ROUTE_DELIVERED'
    elif quantum.slices:
        status = 'SERVICE_PROGRESSED'
    elif blocked:
        status = 'EVENT_BACKPRESSURE'
    else:
        status = 'WAITING'
    return OwnedSharedEventCycleStepV0(
        tick, tuple(admitted), tuple(granted), tuple(blocked),
        delivered.delivered_route_request_ids, finished, quantum.slices,
        owned_shared_event_usage_v0(successor), successor, status,
    )
