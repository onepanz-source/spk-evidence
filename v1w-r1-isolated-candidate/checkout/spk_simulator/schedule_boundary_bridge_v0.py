"""SPK S3.7d/3b2a: verify completed service plans against bounded boundary control.

A deterministic bridge only: never starts or resumes actual memory service.
"""
from collections import defaultdict
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.backpressure_arbiter_v0 import BackpressureArbiterStateV0
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryStateV0, BackpressureBoundaryActionsV0,
    BackpressureBoundaryResultV0, advance_backpressure_boundary_v0,
)
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0
from spk_simulator.event_reservation_v0 import EventReservationStateV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.routed_service_replay_v0 import replay_routed_service_ownership_v0
from spk_simulator.service_reservation_gate_v0 import gate_service_reservations_v0


class ScheduledRouteWithoutReservationV0(RuntimeError):
    code = 'SCHEDULED_ROUTE_WITHOUT_RESERVATION'

    def __init__(self, service_boundary, route_ids):
        self.service_boundary = service_boundary
        self.route_ids = route_ids
        super().__init__(f'route service begins without capacity reservation at '
                         f'SERVICE_TIME={service_boundary}: {route_ids}')


@dataclass(frozen=True, slots=True)
class ScheduleBoundaryFrameV0:
    service_boundary: int
    actions: BackpressureBoundaryActionsV0
    result: BackpressureBoundaryResultV0


@dataclass(frozen=True, slots=True)
class ScheduleBoundaryBridgeResultV0:
    frames: tuple[ScheduleBoundaryFrameV0, ...]
    final_state: BackpressureBoundaryStateV0
    checked_route_count: int
    checked_external_count: int


def verify_schedule_boundaries_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    plan: LogicalAccessPlanV0,
    requests: tuple,
    schedule: CausalScheduleResultV0,
    ingress: ExternalIngressBindingV0,
    *, max_boundaries: int = 10_000,
) -> ScheduleBoundaryBridgeResultV0:
    """Replay each SERVICE_TIME boundary through the single-owner controller.

    The existing service-reservation gate authenticates and validates the
    completed request timeline. This bridge ALSO requires every route that
    *starts* service to obtain a slot claim at the same boundary, and checks
    that the controller's terminal event ownership agrees with the gate.

    Any denial rejects THIS precomputed schedule. No alternative schedule is
    generated and no assertion of deadlock-freedom is made.
    """
    if type(max_boundaries) is not int or max_boundaries <= 0:
        raise ValueError('invalid max_boundaries')
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid manifest')
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError('invalid plan')
    if type(schedule) is not CausalScheduleResultV0:
        raise TypeError('invalid schedule')
    if type(ingress) is not ExternalIngressBindingV0:
        raise TypeError('invalid ingress')

    # Fail-closed source validation, including the conservation of service
    # slices, exact route binding, arrival releases, and finite reservation.
    verified = gate_service_reservations_v0(
        architecture, manifest, plan, requests, schedule, ingress,
    )
    routed = replay_routed_service_ownership_v0(
        architecture, manifest, plan, requests, schedule,
    )
    route_ids = {route.route_request_id for route in manifest.routes}
    first_slices = {}
    for sl in schedule.slices:
        if sl.request_id in route_ids:
            first_slices[sl.request_id] = min(
                sl.service_tick, first_slices.get(sl.request_id, sl.service_tick),
            )
    if set(first_slices) != route_ids:
        raise ValueError('missing route service start')

    action_map = defaultdict(lambda: defaultdict(list))
    route_op = {
        'OFFER': 'routed_offers',
        'ADMIT': 'route_commits',
        'CONSUME': 'route_consumptions',
    }
    for transition in routed.transitions:
        action_map[transition.service_boundary][route_op[transition.operation]].append(
            transition.route_request_id
        )
    for route_id, start in first_slices.items():
        action_map[start]['newly_ready_routes'].append(route_id)

    completion_ticks = {c.request_id: c.completion_tick for c in schedule.completions}
    for arrival in ingress.arrivals:
        action_map[arrival.arrival_boundary]['external_arrivals'].append(arrival.input_index)
        action_map[completion_ticks[arrival.consume_request_id]]['external_consumptions'].append(
            arrival.input_index
        )

    last = max(action_map, default=0)
    if last + 1 > max_boundaries:
        raise ValueError('service boundary replay limit exceeded')
    state = BackpressureBoundaryStateV0(
        RoutedStorageStateV0(manifest.profile_id, manifest.epoch_id),
        EventReservationStateV0(manifest.profile_id, manifest.epoch_id, ingress),
        BackpressureArbiterStateV0(manifest.profile_id, manifest.epoch_id),
    )
    frames = []
    for boundary in range(last + 1):
        kw = action_map.get(boundary, {})
        actions = BackpressureBoundaryActionsV0(**{
            field: tuple(sorted(kw.get(field, ())))
            for field in (
                'route_consumptions', 'external_consumptions',
                'route_commits', 'external_arrivals',
                'routed_offers', 'newly_ready_routes',
            )
        })
        result = advance_backpressure_boundary_v0(
            architecture, manifest, state, service_boundary=boundary,
            actions=actions,
        )
        # A fixed service plan must not claim to have serviced a route whose
        # reservation the actual bounded controller refused.
        if result.denied:
            raise ScheduledRouteWithoutReservationV0(
                boundary, tuple(d.route_request_id for d in result.denied),
            )
        frames.append(ScheduleBoundaryFrameV0(boundary, actions, result))
        state = result.state

    if (state.storage != verified.final_storage
            or state.ledger != verified.final_ledger
            or state.arbiter.waiting_route_ids
            or state.ledger.reserved_routes):
        raise ValueError('boundary controller and scheduled replay disagree')
    return ScheduleBoundaryBridgeResultV0(
        frames=tuple(frames), final_state=state,
        checked_route_count=len(manifest.routes),
        checked_external_count=len(ingress.arrivals),
    )
