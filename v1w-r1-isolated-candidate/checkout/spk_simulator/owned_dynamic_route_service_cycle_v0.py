"""SPK S3.7d/3b2b2k/19: finite EVENT reservation + service + real dynamic route transit.

A deliberately narrow, routed-only transaction owner. No source emission is
published here, no external EVENT occupants are modeled, and no BATCH_CONSUME
is authorized. The initial snapshot remains the caller's responsibility.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import advance_service_quantum_v0
from spk_simulator.owned_dynamic_route_transit_v0 import (
    OwnedDynamicRouteTransitStateV0,
    OwnedDynamicRouteTransitStepV0,
    advance_owned_dynamic_route_transit_v0,
)


def _routes(registry):
    return {
        route.occurrence.event_id: route.occurrence
        for registration in registry.registrations
        for route in registration.allocation.topology.routes
    }


@dataclass(frozen=True, slots=True)
class OwnedDynamicRouteServiceCycleStateV0:
    """Finite EVENT claims and physical/service state in one immutable snapshot.

    `reserved_route_request_ids` are real EVENT capacity claims, not merely
    service-readiness declarations. They persist throughout partial service.
    """
    transit: OwnedDynamicRouteTransitStateV0
    reserved_route_request_ids: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.transit) is not OwnedDynamicRouteTransitStateV0:
            raise TypeError('invalid owned dynamic route transit snapshot')
        ids = self.reserved_route_request_ids
        if (type(ids) is not tuple or
                any(type(x) is not int or x < 0 for x in ids) or
                ids != tuple(sorted(set(ids)))):
            raise ValueError('noncanonical dynamic EVENT reservations')
        registry = self.transit.registry
        service = self.transit.service
        storage = self.transit.storage
        arch = registry.architecture
        expected = _routes(registry)
        pending = {x.event_id for x in storage.pending_output}
        active = {x.request_id for x in service.partial + service.awaiting_confirmation}
        completed = {x.request_id for x in service.confirmed}
        requests = {x.request_id: x for x in registry.staged_requests}
        if set(ids) - set(expected) or set(ids) - pending:
            raise ValueError('EVENT reservation without pending dynamic OUTPUT')
        if set(ids) & completed:
            raise ValueError('EVENT slot retained after route completion')
        for rid in ids:
            if requests[rid].kind is not Kind.ROUTE_ENQUEUE:
                raise ValueError('reservation for non-route request')
        if (active & set(expected)) - set(ids):
            raise ValueError('dynamic route service missing finite EVENT reservation')
        pes = {x.pe_id: x for x in arch.pes}
        occupied = {pe_id: 0 for pe_id in pes}
        for event in storage.admitted_events:
            occupied[event.target_pe_id] += 1
        for rid in ids:
            occupied[expected[rid].target_pe_id] += 1
        if any(occupied[pe_id] > pe.event_slots for pe_id, pe in pes.items()):
            raise ValueError('EVENT reservation exceeds physical capacity')


@dataclass(frozen=True, slots=True)
class OwnedDynamicRouteServiceCycleStepV0:
    service_tick: int
    newly_reserved_route_request_ids: tuple[int, ...]
    service_slices: tuple
    finished_route_request_ids: tuple[int, ...]
    delivered_route_request_ids: tuple[int, ...]
    waiting_capacity_route_request_ids: tuple[int, ...]
    state: OwnedDynamicRouteServiceCycleStateV0
    status: str


def advance_owned_dynamic_route_service_cycle_v0(
    state: OwnedDynamicRouteServiceCycleStateV0,
) -> OwnedDynamicRouteServiceCycleStepV0:
    """Reserve free EVENT slots, spend one quantum, and commit finished routes.

    The causal grant to start ROUTE_ENQUEUE is created *only* by successfully
    claiming a finite EVENT slot for an occurrence present in OUTPUT. Already
    started work retains its claim until physical delivery. The entire step is
    pure: failures never mutate the input state. No external ingress policy is
    passed to the scheduler; callers requiring external admissions must use a
    unified ledger in a later release.
    """
    if type(state) is not OwnedDynamicRouteServiceCycleStateV0:
        raise TypeError('invalid owned dynamic route service cycle')
    transit = state.transit
    registry = transit.registry
    arch = registry.architecture
    stored = transit.storage
    service = transit.service
    routes = _routes(registry)
    confirmed = {x.request_id for x in service.confirmed}
    already = {x.request_id for x in service.partial + service.awaiting_confirmation}
    pending = {x.event_id for x in stored.pending_output}
    reservations = set(state.reserved_route_request_ids)
    occupied = {pe.pe_id: 0 for pe in arch.pes}
    capacity = {pe.pe_id: pe.event_slots for pe in arch.pes}
    for event in stored.admitted_events:
        occupied[event.target_pe_id] += 1
    for rid in reservations:
        occupied[routes[rid].target_pe_id] += 1
    acquired, denied = [], []
    # Stable ID priority, even for parallel edges with the same EVENT_TIME.
    for rid in sorted(routes):
        if rid not in pending or rid in confirmed | already | reservations:
            continue
        emission_id = next(
            item.allocation.emission_request_id
            for item in registry.registrations if rid in item.allocation.route_request_ids
        )
        if emission_id not in confirmed:
            continue
        target = routes[rid].target_pe_id
        if occupied[target] >= capacity[target]:
            denied.append(rid)
            continue
        reservations.add(rid)
        acquired.append(rid)
        occupied[target] += 1
    # Only new claims are grants; existing partial jobs already hold theirs.
    quantum = advance_service_quantum_v0(
        arch, registry.staged_requests, registry.staged_graph, service,
        granted_memory_request_ids=tuple(acquired),
    )
    # This owner may spend service only for its own dynamic ROUTE_ENQUEUEs.
    # Core/P/S and source EMISSION_RECORD are controlled elsewhere. A quantum
    # schedule that would advance any of those must be handed to that owner.
    route_ids = set(routes)
    if any(slice_.request_id not in route_ids for slice_ in quantum.slices):
        raise ValueError('unowned non-route service must be advanced by its authority')
    interim = OwnedDynamicRouteTransitStateV0(registry, stored, quantum.state)
    delivered = advance_owned_dynamic_route_transit_v0(interim)
    delivered_ids = set(delivered.delivered_route_request_ids)
    # Claimed capacity becomes physical EVENT residency, never double counted.
    reservations.difference_update(delivered_ids)
    successor = OwnedDynamicRouteServiceCycleStateV0(
        delivered.state, tuple(sorted(reservations)),
    )
    finished_routes = tuple(sorted(rid for rid in quantum.work_finished_request_ids if rid in routes))
    if delivered_ids:
        status = 'DELIVERED'
    elif quantum.slices:
        status = 'SERVICE_PROGRESSED'
    elif denied:
        status = 'EVENT_BACKPRESSURE'
    else:
        status = 'WAITING'
    return OwnedDynamicRouteServiceCycleStepV0(
        quantum.service_tick, tuple(acquired), quantum.slices, finished_routes,
        delivered.delivered_route_request_ids, tuple(denied), successor, status,
    )
