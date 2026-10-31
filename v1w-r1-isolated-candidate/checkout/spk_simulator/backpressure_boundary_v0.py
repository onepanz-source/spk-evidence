"""SPK S3.7d/3b1: deterministic boundary controller for bounded event ownership.

One serial owner advances storage, external admissions, route commits and
route reservations at an explicit SERVICE_TIME boundary. Not a scheduler:
request completions and route readiness are supplied by its future caller.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.backpressure_arbiter_v0 import (
    BackpressureArbiterStateV0, BackpressureDenialV0,
    arbitrate_routed_reservations_v0,
)
from spk_simulator.event_reservation_v0 import (
    EventReservationStateV0, EventSlotUnavailableV0,
    arrive_external_event_slot_v0, consume_external_event_slot_v0,
    commit_routed_event_slot_v0, consume_reserved_routed_event_v0,
    event_reservation_usage_v0,
)
from spk_simulator.event_storage_v0 import (
    RoutedStorageBlockedV0, RoutedStorageStateV0, routed_storage_usage_v0,
)
from spk_simulator.routing_binding_v0 import (
    RoutedBindingManifestV0, offer_bound_routed_event_v0,
)


class BoundaryCapacityDeniedV0(RuntimeError):
    """Explicit refusal of a non-backpressurable arrival/output publication."""
    def __init__(self, reason: str, boundary: int, occurrence_id: int, pe_id: str):
        self.code = reason
        self.service_boundary = boundary
        self.occurrence_id = occurrence_id
        self.pe_id = pe_id
        super().__init__(f'{reason}: id={occurrence_id} PE={pe_id} SERVICE_TIME={boundary}')


@dataclass(frozen=True, slots=True)
class BackpressureBoundaryStateV0:
    storage: RoutedStorageStateV0
    ledger: EventReservationStateV0
    arbiter: BackpressureArbiterStateV0


@dataclass(frozen=True, slots=True)
class BackpressureBoundaryActionsV0:
    """Caller-produced completions/readiness; identities, not spike payloads.

    Tuple fields are sets of distinct occurrence IDs; caller input order is
    semantically irrelevant. `external_consumptions` identify initial inputs,
    not their consuming service requests (validated against ingress binding).
    """
    route_consumptions: tuple[int, ...] = ()
    external_consumptions: tuple[int, ...] = ()
    route_commits: tuple[int, ...] = ()
    external_arrivals: tuple[int, ...] = ()
    routed_offers: tuple[int, ...] = ()
    newly_ready_routes: tuple[int, ...] = ()

    def __post_init__(self):
        for name in (
            'route_consumptions', 'external_consumptions',
            'route_commits', 'external_arrivals', 'routed_offers',
            'newly_ready_routes',
        ):
            values = getattr(self, name)
            if (type(values) is not tuple or any(type(x) is not int or x < 0 for x in values)
                    or len(values) != len(set(values))):
                raise ValueError(f'invalid occurrence identities in {name}')
        if (set(self.route_commits) & set(self.newly_ready_routes)):
            raise ValueError('route cannot start and complete service at one boundary')
        if (set(self.route_consumptions) & set(self.route_commits)):
            raise ValueError('route cannot be delivered and consumed at one boundary')
        if (set(self.external_arrivals) & set(self.external_consumptions)):
            raise ValueError('external event cannot arrive and be consumed at one boundary')


@dataclass(frozen=True, slots=True)
class BackpressureBoundaryEventV0:
    service_boundary: int
    operation: str
    occurrence_id: int


@dataclass(frozen=True, slots=True)
class BackpressureBoundaryPEUsageV0:
    pe_id: str
    pending_output: int
    output_capacity: int
    claimed_events: int
    event_capacity: int
    reserved_routes: int


@dataclass(frozen=True, slots=True)
class BackpressureBoundaryResultV0:
    state: BackpressureBoundaryStateV0
    operations: tuple[BackpressureBoundaryEventV0, ...]
    granted_route_ids: tuple[int, ...]
    denied: tuple[BackpressureDenialV0, ...]
    pe_usage: tuple[BackpressureBoundaryPEUsageV0, ...]


def advance_backpressure_boundary_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    state: BackpressureBoundaryStateV0,
    *,
    service_boundary: int,
    actions: BackpressureBoundaryActionsV0 = BackpressureBoundaryActionsV0(),
) -> BackpressureBoundaryResultV0:
    """Advance one SERVICE_TIME boundary atomically as a pure state change.

    Strict phases: consume resident events; commit previously reserved routes;
    process non-backpressurable external arrivals; publish routed outputs;
    reserve newly-ready or previously blocked routes. Failed arrivals/offers
    abort the WHOLE boundary. Denied reservations retain source OUTPUT.

    This controller does not authenticate request completions, check the
    scheduler dependency DAG, delay EMISSION_RECORD or detect deadlock.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid manifest')
    if type(state) is not BackpressureBoundaryStateV0:
        raise TypeError('invalid boundary state')
    if type(actions) is not BackpressureBoundaryActionsV0:
        raise TypeError('invalid actions')
    if type(service_boundary) is not int or service_boundary < 0:
        raise ValueError('invalid SERVICE_TIME boundary')
    if (state.arbiter.last_service_boundary is not None and
            service_boundary <= state.arbiter.last_service_boundary):
        raise ValueError('SERVICE_TIME boundaries must increase strictly')
    if (manifest.profile_id != architecture.profile_id
            or state.storage.profile_id != manifest.profile_id
            or state.ledger.profile_id != manifest.profile_id
            or state.arbiter.profile_id != manifest.profile_id
            or state.storage.epoch_id != manifest.epoch_id
            or state.ledger.epoch_id != manifest.epoch_id
            or state.arbiter.epoch_id != manifest.epoch_id):
        raise ValueError('profile or epoch mismatch')

    routes = {route.route_request_id: route for route in manifest.routes}
    arrivals = {arrival.input_index: arrival for arrival in state.ledger.ingress.arrivals}
    if len(arrivals) != len(state.ledger.ingress.arrivals):
        raise ValueError('duplicate ingress occurrence')
    for name in ('route_consumptions', 'route_commits', 'routed_offers', 'newly_ready_routes'):
        if set(getattr(actions, name)) - routes.keys():
            raise ValueError(f'unknown route occurrence in {name}')
    for name in ('external_consumptions', 'external_arrivals'):
        if set(getattr(actions, name)) - arrivals.keys():
            raise ValueError(f'unknown external occurrence in {name}')
    for input_index in actions.external_arrivals:
        if arrivals[input_index].arrival_boundary != service_boundary:
            raise ValueError('external arrival not at its bound SERVICE_TIME')
    for input_index in actions.external_consumptions:
        if arrivals[input_index].arrival_boundary >= service_boundary:
            raise ValueError('external consume not after availability boundary')

    # Arrivals are non-backpressurable and MUST be accounted for at their
    # bound boundary. Silently skipping an ingress occurrence is forbidden.
    # This also detects callers that skip an entire boundary with due input.
    accounted = (set(state.ledger.external_resident)
                 | set(state.ledger.external_consumed))
    due = {idx for idx, arrival in arrivals.items()
           if arrival.arrival_boundary <= service_boundary and idx not in accounted}
    at_boundary = {idx for idx in due
                   if arrivals[idx].arrival_boundary == service_boundary}
    if due != at_boundary or set(actions.external_arrivals) != at_boundary:
        raise ValueError('missing, late, or unscheduled external ingress')

    storage, ledger = state.storage, state.ledger
    # Fail closed on any corrupt input snapshot, before processing transitions.
    event_reservation_usage_v0(architecture, storage, manifest, ledger)
    routed_storage_usage_v0(architecture, storage)
    operations = []

    def emit(op, occurrence_id):
        operations.append(BackpressureBoundaryEventV0(service_boundary, op, occurrence_id))

    for route_id in sorted(actions.route_consumptions):
        route = routes[route_id]
        storage = consume_reserved_routed_event_v0(
            architecture, storage, manifest, ledger, route_id,
            consume_request_id=route.consume_request_id,
        )
        emit('CONSUME_ROUTE', route_id)

    for input_index in sorted(actions.external_consumptions):
        ledger = consume_external_event_slot_v0(
            architecture, storage, manifest, ledger, input_index,
            consume_request_id=arrivals[input_index].consume_request_id,
        )
        emit('CONSUME_EXTERNAL', input_index)

    for route_id in sorted(actions.route_commits):
        storage, ledger = commit_routed_event_slot_v0(
            architecture, storage, manifest, ledger, route_id,
        )
        emit('COMMIT', route_id)

    for input_index in sorted(actions.external_arrivals):
        try:
            ledger = arrive_external_event_slot_v0(
                architecture, storage, manifest, ledger, input_index,
            )
        except EventSlotUnavailableV0 as error:
            raise BoundaryCapacityDeniedV0(
                'EXTERNAL_INGRESS_OVERFLOW', service_boundary, input_index, error.pe_id,
            ) from error
        emit('ARRIVE_EXTERNAL', input_index)

    for route_id in sorted(actions.routed_offers):
        try:
            storage = offer_bound_routed_event_v0(
                architecture, storage, manifest, route_id,
            )
        except RoutedStorageBlockedV0 as error:
            raise BoundaryCapacityDeniedV0(
                'OUTPUT_STORAGE_BLOCKED', service_boundary, route_id, error.pe_id,
            ) from error
        emit('OFFER', route_id)

    result = arbitrate_routed_reservations_v0(
        architecture, manifest, storage, ledger, state.arbiter,
        service_boundary=service_boundary,
        newly_ready_route_ids=tuple(sorted(actions.newly_ready_routes)),
    )
    for route_id in result.granted_route_ids:
        emit('RESERVE', route_id)
    for denied in result.denied:
        emit('WAIT', denied.route_request_id)
    ledger = result.ledger
    ev_usage = {x.pe_id: x for x in event_reservation_usage_v0(
        architecture, storage, manifest, ledger,
    )}
    out_usage = {x.pe_id: x for x in routed_storage_usage_v0(architecture, storage)}
    usages = tuple(BackpressureBoundaryPEUsageV0(
        pe_id=pe_id,
        pending_output=out_usage[pe_id].pending_output,
        output_capacity=out_usage[pe_id].output_capacity,
        claimed_events=ev_usage[pe_id].claimed,
        event_capacity=ev_usage[pe_id].capacity,
        reserved_routes=ev_usage[pe_id].reserved,
    ) for pe_id in sorted(ev_usage))
    return BackpressureBoundaryResultV0(
        state=BackpressureBoundaryStateV0(storage, ledger, result.state),
        operations=tuple(operations),
        granted_route_ids=result.granted_route_ids,
        denied=result.denied,
        pe_usage=usages,
    )
