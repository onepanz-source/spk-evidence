"""SPK S3.7d/3b2b2f: connect witnessed storage effects to causal service state.

This *single-boundary* functional adapter never accepts arbitrary completion IDs.
It is NOT a service-start grant generator or autonomous scheduler.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.bounded_backpressure_driver_v0 import (
    BoundedBackpressureStateV0, BackpressureServiceFrameV0,
)
from spk_simulator.causal_service_frontier_v0 import classify_causal_service_frontier_v0
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0, ServiceQuantumStepV0, advance_service_quantum_v0,
)
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.service_effect_authority_v0 import (
    ServiceEffectAuthorityResultV0, authenticate_service_storage_effects_v0,
)


@dataclass(frozen=True, slots=True)
class AuthenticatedServiceBoundaryStateV0:
    service: ServiceQuantumStateV0
    driver: BoundedBackpressureStateV0

    def __post_init__(self):
        if type(self.service) is not ServiceQuantumStateV0:
            raise TypeError('invalid service state')
        if type(self.driver) is not BoundedBackpressureStateV0:
            raise TypeError('invalid backpressure state')
        last = self.driver.boundary.arbiter.last_service_boundary
        if self.service.next_service_tick != (0 if last is None else last + 1):
            raise ValueError('service/driver boundary mismatch')


@dataclass(frozen=True, slots=True)
class AuthenticatedServiceBoundaryStepV0:
    service_boundary: int
    authority: ServiceEffectAuthorityResultV0
    quantum: ServiceQuantumStepV0
    state: AuthenticatedServiceBoundaryStateV0


def advance_authenticated_service_boundary_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: AuthenticatedServiceBoundaryStateV0,
    frame: BackpressureServiceFrameV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> AuthenticatedServiceBoundaryStepV0:
    """Witness completed storage effects and spend the next service quantum.

    Storage completions and route reservations are ONLY those observed from
    real bounded driver transitions. Caller cannot pass confirmed IDs or grants.
    New route submission is checked against the DAG even when reservation is
    denied. Internal/non-storage completions and initial OUTPUT grants are not
    handled by this adapter. No deadlock claims and no mutation on rejection.
    """
    if type(state) is not AuthenticatedServiceBoundaryStateV0:
        raise TypeError('invalid bridge state')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid dependency graph')
    if type(frame) is not BackpressureServiceFrameV0:
        raise TypeError('invalid driver frame')
    if frame.service_boundary != state.service.next_service_tick:
        raise ValueError('SERVICE_TIME mismatch')
    bound = state.driver.boundary.ledger.ingress
    if ingress is not None and (type(ingress) is not ExternalIngressBindingV0 or ingress != bound):
        raise ValueError('ingress binding mismatch')
    if ingress is None and bound.arrivals:
        raise ValueError('external ingress requires explicit release binding')

    # Driver state remains unchanged if any subsequent verification fails.
    authority = authenticate_service_storage_effects_v0(
        architecture, manifest, admission, requests,
        state.service, state.driver, frame,
    )
    completions = authority.confirmed_request_ids
    done = tuple(sorted(
        {item.request_id for item in state.service.confirmed} | set(completions)
    ))
    still_awaiting = (
        {item.request_id for item in state.service.awaiting_confirmation} - set(completions)
    )
    in_flight = tuple(sorted(
        {item.request_id for item in state.service.partial} | still_awaiting
    ))
    # Check DAG authorization of route submissions even if the arbiter denies
    # capacity. An identity kept pending cannot bypass its causal ancestors.
    proposed = tuple(sorted(frame.new_ready_route_ids))
    candidate = classify_causal_service_frontier_v0(
        architecture, requests, graph,
        service_boundary=frame.service_boundary,
        completed_request_ids=done,
        in_flight_request_ids=in_flight,
        granted_memory_request_ids=proposed,
        ingress=ingress,
    )
    if not set(proposed) <= set(candidate.ready_request_ids):
        raise ValueError('premature route submission against causal frontier')

    quantum = advance_service_quantum_v0(
        architecture, requests, graph, state.service,
        confirmed_request_ids=completions,
        granted_memory_request_ids=authority.granted_route_request_ids,
        ingress=ingress,
    )
    next_state = AuthenticatedServiceBoundaryStateV0(
        service=quantum.state,
        driver=authority.driver_state,
    )
    return AuthenticatedServiceBoundaryStepV0(
        frame.service_boundary, authority, quantum, next_state,
    )
