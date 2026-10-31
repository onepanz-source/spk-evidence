"""SPK S3.7d/3b2b2i: derive storage-effect frames from owned service state.

The caller supplies no memory-effect frame. This is an autonomous *frame
producer for storage effects*, not a complete network scheduler: non-storage
service completions require a future explicitly modeled authority.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.bounded_backpressure_driver_v0 import BackpressureServiceFrameV0
from spk_simulator.causal_service_frontier_v0 import classify_causal_service_frontier_v0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.owned_service_tick_v0 import (
    OwnedServiceTickStateV0, OwnedServiceTickResultV0,
    advance_owned_service_tick_v0,
)
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class AutoFramedOwnedTickV0:
    """The generated frame is retained for audit and deterministic replay."""
    frame: BackpressureServiceFrameV0
    result: OwnedServiceTickResultV0


def derive_owned_storage_frame_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedServiceTickStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
    allow_owned_internal_awaiting: bool = False,
    deferred_emission_ids: tuple[int, ...] = (),
) -> BackpressureServiceFrameV0:
    """Derive storage transitions only from authenticated, persistent state.

    An unserviceable storage completion is retained, not invented. External
    ingress due at the present SERVICE_TIME boundary is never silently skipped.
    Routing starts use *prior* confirmed predecessors and already resident
    OUTPUT; newly published OUTPUT is eligible from a following boundary.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing manifest')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid emission admission')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid memory service requests')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid dependency graph')
    if type(state) is not OwnedServiceTickStateV0:
        raise TypeError('invalid owned service state')
    service = state.boundary.service
    driver = state.boundary.driver
    bound_ingress = driver.boundary.ledger.ingress
    if (ingress is None and bound_ingress.arrivals or
            ingress is not None and (type(ingress) is not ExternalIngressBindingV0 or ingress != bound_ingress)):
        raise ValueError('external ingress binding mismatch')
    tick = service.next_service_tick
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate request identities')
    emission = {g.emission_request_id: g for g in admission.groups}
    routes = {r.route_request_id: r for r in manifest.routes}
    if len(emission) != len(admission.groups) or len(routes) != len(manifest.routes):
        raise ValueError('duplicate emission or route identities')
    if not (set(emission) | set(routes)) <= set(by_id):
        raise ValueError('missing service request for routed identity')
    if any(by_id[rid].kind is not Kind.EMISSION_RECORD for rid in emission):
        raise ValueError('emission request kind mismatch')
    if any(by_id[rid].kind is not Kind.ROUTE_ENQUEUE for rid in routes):
        raise ValueError('route request kind mismatch')

    awaiting = {item.request_id: item.finish_boundary for item in service.awaiting_confirmation}
    confirmed = {item.request_id for item in service.confirmed}
    partial = {item.request_id for item in service.partial}
    if (set(awaiting) | confirmed | partial) - by_id.keys():
        raise ValueError('unknown service identity in state')
    if any(boundary > tick for boundary in awaiting.values()):
        raise ValueError('future finished service work')
    # No authority exists for internal P/S/O operations yet. Fail closed rather
    # than fabricate completion, but permit them to receive service if present.
    unsupported = tuple(sorted(rid for rid in awaiting if by_id[rid].kind not in (
        Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE, Kind.BATCH_CONSUME,
    )))
    if unsupported and (not allow_owned_internal_awaiting or any(
            by_id[rid].kind is not Kind.STATE_COMMIT for rid in unsupported)):
        raise ValueError(f'unsupported internal service completion: {unsupported}')
    if (type(deferred_emission_ids) is not tuple or
        any(type(x) is not int or x not in emission for x in deferred_emission_ids) or
        len(set(deferred_emission_ids)) != len(deferred_emission_ids)):
        raise ValueError('invalid deferred emission identities')

    storage = driver.boundary.storage
    ledger = driver.boundary.ledger
    pending = {r.event_id for r in storage.pending_output}
    resident_routes = {r.event_id for r in storage.admitted_events}
    reserved = set(ledger.reserved_routes)
    resident_external = set(ledger.external_resident)
    accounted_external = resident_external | set(ledger.external_consumed)
    if len(pending) != len(storage.pending_output) or len(resident_routes) != len(storage.admitted_events):
        raise ValueError('duplicate storage identity')
    arrival_by_id = {a.input_index: a for a in bound_ingress.arrivals}
    if len(arrival_by_id) != len(bound_ingress.arrivals):
        raise ValueError('duplicate ingress occurrence')
    due_before = tuple(sorted(a.input_index for a in bound_ingress.arrivals
                              if a.arrival_boundary < tick and a.input_index not in accounted_external))
    if due_before:
        raise ValueError(f'missing external ingress from previous boundary: {due_before}')
    arrivals = tuple(sorted(a.input_index for a in bound_ingress.arrivals
                            if a.arrival_boundary == tick and a.input_index not in accounted_external))
    if any(a.input_index in accounted_external and a.arrival_boundary >= tick
           for a in bound_ingress.arrivals):
        raise ValueError('external ingress accounted before arrival')

    active_emissions = {item.emission_request_id for item in state.output.active}
    completed_emissions = set(state.output.completed_emission_ids)
    offers = tuple(sorted(rid for rid in awaiting
                          if by_id[rid].kind is Kind.EMISSION_RECORD
                          and rid in active_emissions and rid not in completed_emissions
                          and rid not in deferred_emission_ids))
    unfinished_emissions = tuple(sorted(rid for rid in awaiting
                                       if by_id[rid].kind is Kind.EMISSION_RECORD
                                       and rid not in active_emissions))
    if unfinished_emissions:
        raise ValueError(f'finished emission lacks OUTPUT start reservation: {unfinished_emissions}')
    commits = tuple(sorted(rid for rid in awaiting
                           if by_id[rid].kind is Kind.ROUTE_ENQUEUE and rid in reserved))
    orphan_finished_routes = tuple(sorted(rid for rid in awaiting
                                          if by_id[rid].kind is Kind.ROUTE_ENQUEUE and rid not in reserved))
    if orphan_finished_routes:
        raise ValueError(f'finished routing lacks EVENT reservation: {orphan_finished_routes}')

    # A completed BATCH_CONSUME releases its *complete* set of occurrences.
    # If some have not been delivered, leave the service awaiting evidence.
    by_batch_routes = {}
    by_batch_external = {}
    for r in manifest.routes:
        by_batch_routes.setdefault(r.consume_request_id, set()).add(r.route_request_id)
    for a in bound_ingress.arrivals:
        by_batch_external.setdefault(a.consume_request_id, set()).add(a.input_index)
    consume_routes, consume_external = set(), set()
    for rid in sorted(awaiting):
        if by_id[rid].kind is not Kind.BATCH_CONSUME:
            continue
        expected_r = by_batch_routes.get(rid, set())
        expected_e = by_batch_external.get(rid, set())
        if not (expected_r or expected_e):
            raise ValueError('empty BATCH_CONSUME lacks storage-effect evidence')
        if expected_r <= resident_routes and expected_e <= resident_external:
            consume_routes.update(expected_r)
            consume_external.update(expected_e)
    # Do not authorize consumption before a route/external occurrence actually
    # resides in an EVENT slot, even if its neuronal EVENT_TIME is in the past.

    submitted = set(driver.submitted_route_ids)
    candidates = tuple(sorted((pending & set(routes)) - submitted - confirmed - partial - set(awaiting)))
    frontier = classify_causal_service_frontier_v0(
        architecture, requests, graph,
        service_boundary=tick,
        completed_request_ids=tuple(sorted(confirmed)),
        in_flight_request_ids=tuple(sorted(partial | set(awaiting))),
        granted_memory_request_ids=candidates,
        ingress=ingress,
    )
    route_starts = tuple(sorted(set(candidates) & set(frontier.ready_request_ids)))
    return BackpressureServiceFrameV0(
        service_boundary=tick,
        new_ready_emission_ids=offers,
        new_ready_route_ids=route_starts,
        route_consumptions=tuple(sorted(consume_routes)),
        external_consumptions=tuple(sorted(consume_external)),
        route_commits=commits,
        external_arrivals=arrivals,
    )


def advance_autoframed_owned_tick_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedServiceTickStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
    allow_owned_internal_awaiting: bool = False,
    deferred_emission_ids: tuple[int, ...] = (),
) -> AutoFramedOwnedTickV0:
    """Derive a frame and apply exactly one owned SERVICE_TIME tick."""
    frame = derive_owned_storage_frame_v0(
        architecture, manifest, admission, requests, graph, state,
        ingress=ingress, allow_owned_internal_awaiting=allow_owned_internal_awaiting,
        deferred_emission_ids=deferred_emission_ids,
    )
    result = advance_owned_service_tick_v0(
        architecture, manifest, admission, requests, graph, state, frame, ingress=ingress,
    )
    return AutoFramedOwnedTickV0(frame, result)
