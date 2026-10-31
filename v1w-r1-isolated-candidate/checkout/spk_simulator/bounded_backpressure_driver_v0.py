"""SPK S3.7d/3b2b2b: bounded, pure multi-boundary backpressure driver.

Retains *identities* of blocked atomic emission requests for retries. Storage
ownership remains exclusively in BackpressureBoundaryStateV0. The caller
supplies causally authenticated readiness and service completions: this is NOT
a live service scheduler, and no deadlock conclusion follows from no progress.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.atomic_offer_boundary_v0 import (
    AtomicOfferBoundaryResultV0, advance_atomic_offer_boundary_v0,
)
from spk_simulator.backpressure_boundary_v0 import BackpressureBoundaryStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


def _ids(name: str, values: tuple[int, ...]) -> None:
    if (type(values) is not tuple
            or any(type(x) is not int or x < 0 for x in values)
            or len(values) != len(set(values))):
        raise ValueError(f'invalid {name}')


@dataclass(frozen=True, slots=True)
class BackpressureServiceFrameV0:
    """One caller-authenticated SERVICE_TIME boundary and completed actions."""
    service_boundary: int
    new_ready_emission_ids: tuple[int, ...] = ()
    new_ready_route_ids: tuple[int, ...] = ()
    route_consumptions: tuple[int, ...] = ()
    external_consumptions: tuple[int, ...] = ()
    route_commits: tuple[int, ...] = ()
    external_arrivals: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.service_boundary) is not int or self.service_boundary < 0:
            raise ValueError('invalid SERVICE_TIME boundary')
        for name in (
            'new_ready_emission_ids', 'new_ready_route_ids',
            'route_consumptions', 'external_consumptions',
            'route_commits', 'external_arrivals',
        ):
            _ids(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class BoundedBackpressureStateV0:
    """Driver metadata is an identity ledger, not extra event storage."""
    boundary: BackpressureBoundaryStateV0
    pending_emission_ids: tuple[int, ...] = ()
    submitted_emission_ids: tuple[int, ...] = ()
    admitted_emission_ids: tuple[int, ...] = ()
    submitted_route_ids: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.boundary) is not BackpressureBoundaryStateV0:
            raise TypeError('invalid boundary state')
        for name in (
            'pending_emission_ids', 'submitted_emission_ids',
            'admitted_emission_ids', 'submitted_route_ids',
        ):
            values = getattr(self, name)
            _ids(name, values)
            if values != tuple(sorted(values)):
                raise ValueError(f'noncanonical {name}')
        pending = set(self.pending_emission_ids)
        admitted = set(self.admitted_emission_ids)
        submitted = set(self.submitted_emission_ids)
        if not (pending | admitted <= submitted and not pending & admitted
                and pending | admitted == submitted):
            raise ValueError('emission submission not conserved')


@dataclass(frozen=True, slots=True)
class BackpressureStepV0:
    service_boundary: int
    transition: AtomicOfferBoundaryResultV0
    pending_emission_ids: tuple[int, ...]
    status: str  # PROGRESSED, WAITING, IDLE; NOT deadlock classifications


@dataclass(frozen=True, slots=True)
class BoundedBackpressureRunV0:
    state: BoundedBackpressureStateV0
    steps: tuple[BackpressureStepV0, ...]


def advance_bounded_backpressure_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    state: BoundedBackpressureStateV0,
    frame: BackpressureServiceFrameV0,
) -> tuple[BoundedBackpressureStateV0, BackpressureStepV0]:
    """Advance exactly one consecutive SERVICE_TIME boundary.

    Retrying a blocked emission needs no new caller-ready notification.
    A denied routing is retained by the existing route arbiter. All actions
    and initial readiness must be *authenticated by a future causal scheduler*.
    Failure is atomic with respect to the caller's immutable snapshot.
    """
    if type(state) is not BoundedBackpressureStateV0:
        raise TypeError('invalid driver state')
    if type(frame) is not BackpressureServiceFrameV0:
        raise TypeError('invalid service frame')
    last = state.boundary.arbiter.last_service_boundary
    expected = (0 if last is None else last + 1)
    if frame.service_boundary != expected:
        raise ValueError('driver requires consecutive SERVICE_TIME boundaries')
    submitted = set(state.submitted_emission_ids)
    fresh_emissions = set(frame.new_ready_emission_ids)
    if submitted & fresh_emissions:
        raise ValueError('emission readiness replayed')
    known_routes = set(state.submitted_route_ids)
    fresh_routes = set(frame.new_ready_route_ids)
    if known_routes & fresh_routes:
        raise ValueError('route readiness replayed')
    # Revalidate whole submission ledger against the actual manifest.
    grouped = {group.emission_request_id for group in admission.groups}
    route_ids = {route.route_request_id for route in manifest.routes}
    if (submitted | fresh_emissions) - grouped:
        raise ValueError('unknown emission in driver')
    if (known_routes | fresh_routes) - route_ids:
        raise ValueError('unknown route in driver')
    # Prior admitted groups must still have evidence of their publication,
    # unless the group has zero fanout (which needs no OUTPUT storage).
    observed = (
        {item.event_id for item in state.boundary.storage.pending_output} |
        {item.event_id for item in state.boundary.storage.admitted_events} |
        set(state.boundary.storage.consumed_ids)
    )
    for group in admission.groups:
        if (group.emission_request_id in state.admitted_emission_ids
                and not set(group.route_request_ids) <= observed):
            raise ValueError('previously admitted emission missing owned route')
    ready = tuple(sorted(set(state.pending_emission_ids) | fresh_emissions))
    result = advance_atomic_offer_boundary_v0(
        architecture, manifest, admission, state.boundary,
        service_boundary=frame.service_boundary,
        ready_emission_ids=ready,
        newly_ready_route_ids=tuple(sorted(fresh_routes)),
        route_consumptions=frame.route_consumptions,
        external_consumptions=frame.external_consumptions,
        route_commits=frame.route_commits,
        external_arrivals=frame.external_arrivals,
    )
    after = BoundedBackpressureStateV0(
        boundary=result.boundary.state,
        pending_emission_ids=tuple(sorted(result.blocked_emission_ids)),
        submitted_emission_ids=tuple(sorted(submitted | fresh_emissions)),
        admitted_emission_ids=tuple(sorted(
            set(state.admitted_emission_ids) | set(result.admitted_emission_ids)
        )),
        submitted_route_ids=tuple(sorted(known_routes | fresh_routes)),
    )
    # WAIT is a denial, not progress. Empty fanout emission admissions do
    # count as progress even without physical OFFER operations.
    progressed = bool(result.admitted_emission_ids) or any(
        event.operation != 'WAIT' for event in result.boundary.operations
    )
    outstanding = bool(
        after.pending_emission_ids or after.boundary.arbiter.waiting_route_ids
        or after.boundary.ledger.reserved_routes
        or after.boundary.storage.pending_output
        or after.boundary.storage.admitted_events
        or after.boundary.ledger.external_resident
    )
    status = 'PROGRESSED' if progressed else ('WAITING' if outstanding else 'IDLE')
    return after, BackpressureStepV0(
        frame.service_boundary, result, after.pending_emission_ids, status,
    )


def run_bounded_backpressure_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    state: BoundedBackpressureStateV0,
    frames: tuple[BackpressureServiceFrameV0, ...],
    *,
    max_frames: int = 10_000,
) -> BoundedBackpressureRunV0:
    """Deterministic replay over a finite, explicitly supplied service horizon.

    No fabricated completions, no implicit future arrivals, no deadlock claim.
    Exhausting max_frames is a limit error, not a deadlock finding.
    """
    if type(state) is not BoundedBackpressureStateV0:
        raise TypeError('invalid driver state')
    if (type(frames) is not tuple or
            any(type(f) is not BackpressureServiceFrameV0 for f in frames)):
        raise TypeError('invalid service frames')
    if type(max_frames) is not int or max_frames < 1:
        raise ValueError('invalid max_frames')
    if len(frames) > max_frames:
        raise RuntimeError('BACKPRESSURE_FRAME_LIMIT (not a deadlock diagnosis)')
    steps = []
    current = state
    for frame in frames:
        current, step = advance_bounded_backpressure_v0(
            architecture, manifest, admission, current, frame,
        )
        steps.append(step)
    return BoundedBackpressureRunV0(current, tuple(steps))
