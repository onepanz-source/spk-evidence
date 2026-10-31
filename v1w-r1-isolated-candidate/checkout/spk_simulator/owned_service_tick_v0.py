"""SPK S3.7d/3b2b2h: a single serialized OUTPUT-grant/service/effect tick.

This is an integration seam, NOT a complete autonomous scheduler. The caller
still supplies service-effect frames and initial state, while the module alone
allocates OUTPUT start grants and applies witnessed storage completions.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.authenticated_service_bridge_v0 import AuthenticatedServiceBoundaryStateV0
from spk_simulator.bounded_backpressure_driver_v0 import BackpressureServiceFrameV0
from spk_simulator.causal_service_frontier_v0 import classify_causal_service_frontier_v0
from spk_simulator.causal_service_quantum_v0 import advance_service_quantum_v0, ServiceQuantumStepV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.output_start_reservation_v0 import (
    OutputStartLedgerV0, OutputStartDecisionV0,
    output_start_usage_v0, reserve_output_starts_v0, confirm_output_publications_v0,
)
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.service_effect_authority_v0 import (
    authenticate_service_storage_effects_v0, ServiceEffectAuthorityResultV0,
)


@dataclass(frozen=True, slots=True)
class OwnedServiceTickStateV0:
    boundary: AuthenticatedServiceBoundaryStateV0
    output: OutputStartLedgerV0

    def __post_init__(self):
        if type(self.boundary) is not AuthenticatedServiceBoundaryStateV0:
            raise TypeError('invalid service/boundary owner state')
        if type(self.output) is not OutputStartLedgerV0:
            raise TypeError('invalid OUTPUT start ledger')


@dataclass(frozen=True, slots=True)
class OwnedServiceTickResultV0:
    service_boundary: int
    output_start_decision: OutputStartDecisionV0
    authenticated_effects: ServiceEffectAuthorityResultV0
    quantum: ServiceQuantumStepV0
    state: OwnedServiceTickStateV0


def advance_owned_service_tick_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedServiceTickStateV0,
    frame: BackpressureServiceFrameV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> OwnedServiceTickResultV0:
    """Reserve whole OUTPUT bundles before work, then witness effect and advance.

    Start grants are calculated from the *pre-boundary* storage snapshot:
    capacity freed by a delivery at s cannot initiate a new emission at s.
    At most one owner transforms the immutable state. A refused boundary
    returns no replacement state. Pending emission identities already under
    service keep their reservation until witnessed publication.

    No caller-supplied completed IDs or memory-grant IDs are accepted here.
    A caller still supplies boundary frames with effect claims, which are
    checked against completed service work by ServiceEffectAuthority.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing binding')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid atomic admission')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid requests')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid causal graph')
    if type(state) is not OwnedServiceTickStateV0:
        raise TypeError('invalid owned tick state')
    if type(frame) is not BackpressureServiceFrameV0:
        raise TypeError('invalid service frame')
    svc = state.boundary.service
    driver = state.boundary.driver
    ledger = state.output
    if frame.service_boundary != svc.next_service_tick:
        raise ValueError('SERVICE_TIME mismatch')
    bound = driver.boundary.ledger.ingress
    if ingress is None and bound.arrivals:
        raise ValueError('nonempty external ingress requires explicit binding')
    if ingress is not None and (type(ingress) is not ExternalIngressBindingV0 or ingress != bound):
        raise ValueError('external ingress binding mismatch')
    storage_before = driver.boundary.storage
    output_start_usage_v0(architecture, admission, storage_before, ledger)

    reqs = {r.request_id: r for r in requests}
    groups = {g.emission_request_id for g in admission.groups}
    if len(reqs) != len(requests) or len(groups) != len(admission.groups) or not groups <= reqs.keys():
        raise ValueError('request/emission identity coverage mismatch')
    if any(reqs[rid].kind is not Kind.EMISSION_RECORD for rid in groups):
        raise ValueError('emission request kind mismatch')

    active = {x.emission_request_id for x in ledger.active}
    published = set(ledger.completed_emission_ids)
    partial_ids = {x.request_id for x in svc.partial}
    awaiting_ids = {x.request_id for x in svc.awaiting_confirmation}
    confirmed_ids = {x.request_id for x in svc.confirmed}
    if (groups & (partial_ids | awaiting_ids)) - active:
        raise ValueError('in-flight emission without OUTPUT start grant')
    if groups & confirmed_ids != published:
        raise ValueError('OUTPUT publication/service confirmation mismatch')
    if set(driver.admitted_emission_ids) != published:
        raise ValueError('driver/OUTPUT completed emission mismatch')
    if not set(driver.pending_emission_ids) <= active:
        raise ValueError('retrying an emission without OUTPUT start grant')
    if set(frame.new_ready_emission_ids) - active:
        raise ValueError('emission completion submitted without prior start grant')

    running = partial_ids | awaiting_ids
    # Preview only never-started emissions. Hypothetical grants here only
    # permit the frontier to check DAG/release; real grants follow below.
    preview = tuple(sorted(groups - active - published - running))
    pre = classify_causal_service_frontier_v0(
        architecture, requests, graph,
        service_boundary=frame.service_boundary,
        completed_request_ids=tuple(sorted(confirmed_ids)),
        in_flight_request_ids=tuple(sorted(running)),
        granted_memory_request_ids=preview,
        ingress=ingress,
    )
    ready_emissions = tuple(sorted(set(pre.ready_request_ids) & set(preview)))
    decision = reserve_output_starts_v0(
        architecture, admission, storage_before, ledger, ready_emissions,
    )
    ledger_with_grants = decision.ledger

    # Apply real driver transitions, authenticate *finished* storage work.
    authority = authenticate_service_storage_effects_v0(
        architecture, manifest, admission, requests,
        svc, driver, frame,
    )
    emission_completions = tuple(sorted(
        effect.request_id for effect in authority.effects
        if effect.kind is Kind.EMISSION_RECORD
    ))
    if emission_completions:
        next_output = confirm_output_publications_v0(
            architecture, admission,
            storage_before, authority.driver_state.boundary.storage,
            ledger_with_grants, emission_completions,
        )
    else:
        next_output = ledger_with_grants
    output_start_usage_v0(
        architecture, admission, authority.driver_state.boundary.storage, next_output,
    )

    completions = authority.confirmed_request_ids
    done = confirmed_ids | set(completions)
    remaining_awaiting = awaiting_ids - set(completions)
    in_flight = partial_ids | remaining_awaiting
    proposal = tuple(sorted(frame.new_ready_route_ids))
    route_frontier = classify_causal_service_frontier_v0(
        architecture, requests, graph,
        service_boundary=frame.service_boundary,
        completed_request_ids=tuple(sorted(done)),
        in_flight_request_ids=tuple(sorted(in_flight)),
        granted_memory_request_ids=proposal,
        ingress=ingress,
    )
    if not set(proposal) <= set(route_frontier.ready_request_ids):
        raise ValueError('premature route submission against causal frontier')

    # Active, not already in-flight OUTPUT claims authorize service start.
    starts = {
        x.emission_request_id for x in next_output.active
        if x.emission_request_id not in (in_flight | done)
    }
    grants = tuple(sorted(starts | set(authority.granted_route_request_ids)))
    quantum = advance_service_quantum_v0(
        architecture, requests, graph, svc,
        confirmed_request_ids=completions,
        granted_memory_request_ids=grants,
        ingress=ingress,
    )
    after = OwnedServiceTickStateV0(
        AuthenticatedServiceBoundaryStateV0(quantum.state, authority.driver_state),
        next_output,
    )
    return OwnedServiceTickResultV0(
        frame.service_boundary, decision, authority, quantum, after,
    )
