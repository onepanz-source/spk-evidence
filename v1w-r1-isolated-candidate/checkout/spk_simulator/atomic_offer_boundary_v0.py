"""SPK S3.7d/3b2b2a: compose atomic OUTPUT admission with bounded boundary control.

A single *caller-authenticated* SERVICE_TIME boundary, not an active scheduler.
A blocked emission remains uncompleted in its caller's causal queue; there is
no hidden pending-event storage and no inference of SERVICE_TIME from EVENT_TIME.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.atomic_emission_offer_plan_v0 import (
    AtomicEmissionOfferPlanV0, plan_atomic_emission_offers_v0,
)
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryStateV0, BackpressureBoundaryActionsV0,
    BackpressureBoundaryResultV0, advance_backpressure_boundary_v0,
)
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class AtomicOfferBoundaryResultV0:
    offer_plan: AtomicEmissionOfferPlanV0
    boundary: BackpressureBoundaryResultV0
    admitted_emission_ids: tuple[int, ...]
    blocked_emission_ids: tuple[int, ...]
    granted_route_ids: tuple[int, ...]
    waiting_route_ids: tuple[int, ...]


def advance_atomic_offer_boundary_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    state: BackpressureBoundaryStateV0,
    *,
    service_boundary: int,
    ready_emission_ids: tuple[int, ...] = (),
    route_consumptions: tuple[int, ...] = (),
    external_consumptions: tuple[int, ...] = (),
    route_commits: tuple[int, ...] = (),
    external_arrivals: tuple[int, ...] = (),
    newly_ready_route_ids: tuple[int, ...] = (),
) -> AtomicOfferBoundaryResultV0:
    """Plan atomic offers, then advance one finite-capacity service boundary.

    The caller authenticates completed service requests, dependency readiness,
    and ingress availability. Groups refused for lack of OUTPUT space are NOT
    completed and must be reoffered by a future scheduler. The arbiter's route
    waiters are carried in the returned boundary state and retried automatically
    at subsequent boundaries. A denied external ingress aborts the entire call.

    Conservative v0 admission uses PRE-BOUNDARY OUTPUT occupancy: releases from
    route commits on the same boundary become available to emission offers at
    the next boundary, even though the controller could process them immediately.
    This conservative deferral preserves capacity without assuming transient
    (unmodeled) slots or silently completing EMISSION_RECORD.
    """
    if type(service_boundary) is not int or service_boundary < 0:
        raise ValueError('invalid SERVICE_TIME boundary')
    if (type(ready_emission_ids) is not tuple
            or any(type(x) is not int or x < 0 for x in ready_emission_ids)
            or len(set(ready_emission_ids)) != len(ready_emission_ids)):
        raise ValueError('invalid ready emission identities')
    if (type(newly_ready_route_ids) is not tuple
            or any(type(x) is not int or x < 0 for x in newly_ready_route_ids)
            or len(set(newly_ready_route_ids)) != len(newly_ready_route_ids)):
        raise ValueError('invalid ready route identities')

    offer_plan = plan_atomic_emission_offers_v0(
        architecture, manifest, admission, state,
        ready_emission_ids=ready_emission_ids,
    )
    # A scheduler must not start ROUTE_ENQUEUE for a group whose atomic offer
    # has been denied. Only already resident or currently admitted occurrences
    # may request a reservation at this boundary.
    resident = {event.event_id for event in state.storage.pending_output}
    may_start = resident | set(offer_plan.routed_offers)
    if set(newly_ready_route_ids) - may_start:
        raise ValueError('ready routing lacks retained or newly admitted OUTPUT')

    actions = BackpressureBoundaryActionsV0(
        route_consumptions=route_consumptions,
        external_consumptions=external_consumptions,
        route_commits=route_commits,
        external_arrivals=external_arrivals,
        routed_offers=offer_plan.routed_offers,
        newly_ready_routes=newly_ready_route_ids,
    )
    boundary = advance_backpressure_boundary_v0(
        architecture, manifest, state,
        service_boundary=service_boundary,
        actions=actions,
    )
    # Defensive cross-check: every selected atomic output was actually
    # published; the boundary controller is the single state owner.
    performed_offers = tuple(sorted(
        op.occurrence_id for op in boundary.operations if op.operation == 'OFFER'
    ))
    if performed_offers != offer_plan.routed_offers:
        raise ValueError('atomic OUTPUT offer boundary disagreement')

    return AtomicOfferBoundaryResultV0(
        offer_plan=offer_plan,
        boundary=boundary,
        admitted_emission_ids=offer_plan.admitted_emission_ids,
        blocked_emission_ids=tuple(x.emission_request_id for x in offer_plan.blocked),
        granted_route_ids=boundary.granted_route_ids,
        waiting_route_ids=boundary.state.arbiter.waiting_route_ids,
    )
