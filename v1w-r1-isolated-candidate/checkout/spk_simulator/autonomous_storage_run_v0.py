"""SPK S3.7d/3b2b2j: bounded autonomous loop for storage-effect requests.

This is an execution controller, not merely a frame serializer: it repeatedly
runs the single-owner quantum/OUTPUT/EVENT integration and derives all storage
frames from state. Its supported request universe is intentionally limited to
BATCH_CONSUME, EMISSION_RECORD, ROUTE_ENQUEUE; other kinds require distinct
semantic completion authorities. Exhausting the tick cap is NOT a deadlock proof.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.owned_service_autoframe_v0 import (
    AutoFramedOwnedTickV0, advance_autoframed_owned_tick_v0,
)
from spk_simulator.owned_service_tick_v0 import OwnedServiceTickStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0

_STORAGE_ONLY = frozenset((Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE, Kind.BATCH_CONSUME))


@dataclass(frozen=True, slots=True)
class AutonomousStorageRunV0:
    status: str  # COMPLETED or TICK_LIMIT, never an inferred DEADLOCK
    start_service_boundary: int
    end_service_boundary: int
    steps: tuple[AutoFramedOwnedTickV0, ...]
    completed_request_ids: tuple[int, ...]
    unfinished_request_ids: tuple[int, ...]
    future_external_boundaries: tuple[int, ...]
    state: OwnedServiceTickStateV0

    @property
    def service_ticks(self) -> int:
        return self.end_service_boundary - self.start_service_boundary


def _completion_ids(state, requests):
    completed = tuple(sorted(x.request_id for x in state.boundary.service.confirmed))
    all_ids = tuple(sorted(r.request_id for r in requests))
    if len(set(all_ids)) != len(all_ids) or set(completed) - set(all_ids):
        raise ValueError('service request/confirmation identity mismatch')
    return completed, tuple(sorted(set(all_ids) - set(completed)))


def _terminal_conservation(manifest, admission, state, ingress):
    """Require no live spike or grant before reporting successful completion."""
    driver = state.boundary.driver
    boundary = driver.boundary
    storage = boundary.storage
    ledger = boundary.ledger
    route_ids = {route.route_request_id for route in manifest.routes}
    if (storage.pending_output or storage.admitted_events or
            boundary.arbiter.waiting_route_ids or ledger.reserved_routes or
            ledger.external_resident or state.output.active or
            driver.pending_emission_ids or state.boundary.service.partial or
            state.boundary.service.awaiting_confirmation):
        raise ValueError('completed storage service has live pending resource ownership')
    if set(storage.consumed_ids) != route_ids:
        raise ValueError('completed storage service lost or duplicated routed occurrence')
    expected_external = {arrival.input_index for arrival in ingress.arrivals} if ingress else set()
    if set(ledger.external_consumed) != expected_external:
        raise ValueError('completed storage service lost external occurrence')
    if set(state.output.completed_emission_ids) != {
            group.emission_request_id for group in admission.groups}:
        raise ValueError('completed service lacks atomic emission publication')


def run_autonomous_storage_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    initial_state: OwnedServiceTickStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
    max_service_ticks: int = 10000,
) -> AutonomousStorageRunV0:
    """Run consecutive SERVICE_TIME boundaries without caller-produced frames.

    No skip of future ingress boundaries, no modification of EVENT_TIME and no
    interpolation of neuronal time. The step budget is a bounded observation
    horizon, not physical memory, and reaching it implies no deadlock claim.
    Can restart from a returned immutable state with a fresh budget.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing binding')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid atomic emission admission')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service request tuple')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid causal graph')
    if type(initial_state) is not OwnedServiceTickStateV0:
        raise TypeError('invalid initial owned state')
    if ingress is not None and type(ingress) is not ExternalIngressBindingV0:
        raise TypeError('invalid ingress binding')
    if type(max_service_ticks) is not int or max_service_ticks < 1:
        raise ValueError('max_service_ticks must be a positive integer')
    unsupported = tuple(sorted(r.request_id for r in requests if r.kind not in _STORAGE_ONLY))
    if unsupported:
        raise ValueError(f'internal service kinds require an independent authority: {unsupported}')
    # No assumptions about caller-supplied ordering. Identity is canonicalized.
    completed, unfinished = _completion_ids(initial_state, requests)
    start = initial_state.boundary.service.next_service_tick
    state = initial_state
    steps = []
    while unfinished and len(steps) < max_service_ticks:
        item = advance_autoframed_owned_tick_v0(
            architecture, manifest, admission, requests, graph, state, ingress=ingress,
        )
        if (item.frame.service_boundary != state.boundary.service.next_service_tick or
                item.result.state.boundary.service.next_service_tick !=
                state.boundary.service.next_service_tick + 1):
            raise ValueError('nonconsecutive SERVICE_TIME transition')
        steps.append(item)
        state = item.result.state
        completed, unfinished = _completion_ids(state, requests)
    if not unfinished:
        _terminal_conservation(manifest, admission, state, ingress)
        status = 'COMPLETED'
    else:
        status = 'TICK_LIMIT'
    boundary = state.boundary.service.next_service_tick
    if boundary - start != len(steps):
        raise ValueError('SERVICE_TIME advancement not conserved')
    consumed_external = set(state.boundary.driver.boundary.ledger.external_consumed)
    future = tuple(sorted({arrival.arrival_boundary for arrival in ingress.arrivals
                          if arrival.input_index not in consumed_external
                          and arrival.arrival_boundary >= boundary})) if ingress else ()
    return AutonomousStorageRunV0(
        status, start, boundary, tuple(steps), completed, unfinished, future, state,
    )
