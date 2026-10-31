"""SPK S3.7d/3b2b2k/22: physical sealed-root EVENT batch consumption.

A deliberately limited exclusive SERVICE_TIME owner. It admits due sealed
external inputs, serves only authenticated READY root BATCH_CONSUME requests,
and confirms them only in a later service boundary by moving complete external
occurrences from resident EVENT to consumed tombstones. It refuses scheduling
requests belonging to other authorities; not a global network scheduler.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceConfirmedV0, advance_service_quantum_v0,
)
from spk_simulator.owned_dynamic_route_transit_v0 import OwnedDynamicRouteTransitStateV0
from spk_simulator.owned_dynamic_route_service_cycle_v0 import OwnedDynamicRouteServiceCycleStateV0
from spk_simulator.owned_shared_event_cycle_v0 import (
    OwnedSharedEventCycleStateV0, SharedExternalIngressOverflowV0,
    owned_shared_event_usage_v0,
)
from spk_simulator.owned_sealed_root_batch_v0 import analyze_owned_sealed_root_batches_v0


@dataclass(frozen=True, slots=True)
class OwnedRootBatchConsumptionStepV0:
    service_tick: int
    admitted_external_input_indices: tuple[int, ...]
    service_slices: tuple
    work_finished_consume_request_ids: tuple[int, ...]
    confirmed_consume_request_ids: tuple[int, ...]
    newly_consumed_external_input_indices: tuple[int, ...]
    state: OwnedSharedEventCycleStateV0
    status: str


def _successor(state, service, residents, consumed):
    transit = state.dynamic.transit
    next_transit = OwnedDynamicRouteTransitStateV0(transit.registry, transit.storage, service)
    next_dynamic = OwnedDynamicRouteServiceCycleStateV0(
        next_transit, state.dynamic.reserved_route_request_ids,
    )
    return OwnedSharedEventCycleStateV0(
        next_dynamic, state.seal, tuple(sorted(residents)), tuple(sorted(consumed)),
    )


def advance_owned_root_batch_consumption_v0(
    state: OwnedSharedEventCycleStateV0,
) -> OwnedRootBatchConsumptionStepV0:
    """Advance exactly ONE exclusive service boundary.

    The sealed plan is immutable. External arrivals due at this boundary are
    mandatory. Completed service is confirmed only at a LATER boundary after
    its entire resident input set has been verified and physically consumed.
    Confirmation takes a full boundary here, conservatively spending no other
    PE service units. Other P/S, emission and route service must use their own
    owner; this narrow function rejects those requests rather than advancing
    them or forging completions.

    Initial snapshots remain trust roots and cannot be authenticated here.
    """
    if type(state) is not OwnedSharedEventCycleStateV0:
        raise TypeError('invalid root batch shared EVENT state')
    transit = state.dynamic.transit
    service = transit.service
    registry = transit.registry
    arch = registry.architecture
    tick = service.next_service_tick
    seal = state.seal
    arr = seal.binding.arrivals
    by_request = {r.request_id: r for r in registry.staged_requests}
    pre_audit = analyze_owned_sealed_root_batches_v0(state)
    root_batches = {b.consume_request_id: b for b in pre_audit.batches
                    if b.status != 'NONROOT_REQUIRES_CAUSAL_FRONTIER'}
    eligible = {rid for rid,b in root_batches.items() if b.sealed_input_set_complete}
    awaiting = {f.request_id: f for f in service.awaiting_confirmation}
    # Never confirm an unowned, non-root or not-ready batch.
    ready_to_confirm = tuple(sorted(eligible & set(awaiting)))
    if len(ready_to_confirm) != len(set(awaiting) & set(root_batches)):
        raise ValueError('finished root consume lacks complete sealed input set')
    resident = set(state.external_resident_input_indices)
    consumed = set(state.external_consumed_input_indices)
    consumption_indices = set()
    for rid in ready_to_confirm:
        request = by_request[rid]
        if request.kind is not Kind.BATCH_CONSUME or awaiting[rid].finish_boundary > tick:
            raise ValueError('premature or invalid root consumption')
        batch = root_batches[rid]
        indices = set(batch.expected_external_indices)
        if not indices <= resident or indices & consumed:
            raise ValueError('root consumption lacks physically resident inputs')
        consumption_indices.update(indices)
    # The physical consume effect and service confirmation are one successor.
    resident.difference_update(consumption_indices)
    consumed.update(consumption_indices)
    used = {u.pe_id: u.claimed for u in owned_shared_event_usage_v0(state)}
    capacity = {p.pe_id: p.event_slots for p in arch.pes}
    for idx in consumption_indices:
        a = arr[idx]
        used[a.target_pe_id] -= 1
    due = []
    for a in arr:
        if a.arrival_boundary != tick:
            continue
        if used[a.target_pe_id] >= capacity[a.target_pe_id]:
            raise SharedExternalIngressOverflowV0(
                tick, a.input_index, a.target_pe_id, used[a.target_pe_id],
                capacity[a.target_pe_id],
            )
        resident.add(a.input_index)
        due.append(a.input_index)
        used[a.target_pe_id] += 1
    if ready_to_confirm:
        # Do not accidentally perform an unowned STATE_COMMIT or route service
        # within the same confirmation boundary.
        next_service = replace(
            service, next_service_tick=tick + 1,
            awaiting_confirmation=tuple(f for f in service.awaiting_confirmation
                                         if f.request_id not in ready_to_confirm),
            confirmed=tuple(sorted(
                service.confirmed + tuple(ServiceConfirmedV0(rid, tick)
                                          for rid in ready_to_confirm),
                key=lambda x: x.request_id,
            )),
        )
        successor = _successor(state, next_service, resident, consumed)
        return OwnedRootBatchConsumptionStepV0(
            tick, tuple(due), (), (), ready_to_confirm,
            tuple(sorted(consumption_indices)), successor, 'CONSUMED',
        )
    # No confirmation available: grant service only to a complete root batch.
    # Audit a provisional post-admission view at the successor boundary;
    # at SERVICE_TIME=t, arrivals due at t are not yet historical residents.
    provisional_service = replace(service, next_service_tick=tick + 1)
    admitted_state = _successor(state, provisional_service, resident, consumed)
    audit = analyze_owned_sealed_root_batches_v0(admitted_state)
    now_ready = {b.consume_request_id for b in audit.batches
                 if b.sealed_input_set_complete}
    # For this narrow owner, an already confirmed root request must have
    # been physically consumed, never silently pre-confirmed.
    for rid in now_ready:
        if any(c.request_id == rid for c in service.confirmed):
            raise ValueError('root batch service already confirmed without consumption')
    quantum = advance_service_quantum_v0(
        arch, registry.staged_requests, registry.staged_graph, service,
        ingress=seal.binding,
    )
    for slice_ in quantum.slices:
        rid = slice_.request_id
        if rid not in now_ready or by_request[rid].kind is not Kind.BATCH_CONSUME:
            raise ValueError('unowned or unsealed service must be advanced by its authority')
    next_state = _successor(state, quantum.state, resident, consumed)
    finished = tuple(sorted(rid for rid in quantum.work_finished_request_ids
                            if rid in now_ready))
    return OwnedRootBatchConsumptionStepV0(
        tick, tuple(due), quantum.slices, finished, (), (), next_state,
        'SERVICE_PROGRESSED' if quantum.slices else
        'EXTERNAL_ADMITTED' if due else 'WAITING',
    )
