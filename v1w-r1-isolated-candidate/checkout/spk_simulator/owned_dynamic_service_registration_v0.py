"""SPK S3.7d/3b2b2k/11: stage service requests owned by Core-derived emissions.

Generated requests are NOT active, admitted, published, or bound to consumers.
No Network v0 execution trace is inspected. No service progress is asserted.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import (
    AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain, ActivityV0 as Activity,
)
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.owned_computed_emission_allocation_v0 import (
    ComputedEmissionAllocationLedgerV0, OwnedComputedEmissionAllocationV0,
    initialize_computed_emission_allocation_v0, allocate_computed_emission_v0,
)
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, PreparedCoreTransitionV0,
)


def _predecessors(dep: AccessDependencyV0) -> tuple[int, ...]:
    return dep.predecessor_ids if hasattr(dep, 'predecessor_ids') else dep.predecessors


def _require_request_graph(requests, graph):
    if (type(requests) is not tuple or
            any(type(x) is not MemoryServiceRequestV0 for x in requests)):
        raise TypeError('invalid service request tuple')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid dependency graph')
    ids = tuple(r.request_id for r in requests)
    if ids != tuple(sorted(set(ids))) or any(type(x) is not int or x < 0 for x in ids):
        raise ValueError('noncanonical request IDs')
    depids = tuple(d.request_id for d in graph.dependencies)
    if depids != ids:
        raise ValueError('dependency/request ID coverage mismatch')
    # Also checks cycles, dangling predecessors, and P/S neuron serialization.
    out = serialize_internal_access_graph_v0(requests, graph)
    if out.graph != graph:
        raise ValueError('service graph lacks serialized internal state dependencies')
    return out


@dataclass(frozen=True, slots=True)
class DynamicServiceCostsV0:
    """Explicit workload policy; not a claim about calibrated hardware latency."""
    service_profile_id: str
    emission_units: int
    route_units: int

    def __post_init__(self):
        if (type(self.service_profile_id) is not str or
                not self.service_profile_id or self.service_profile_id.strip() != self.service_profile_id):
            raise ValueError('invalid service profile')
        for name in ('emission_units', 'route_units'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError('service cost must be a positive integer')


@dataclass(frozen=True, slots=True)
class DynamicEmissionServiceRegistrationV0:
    allocation: OwnedComputedEmissionAllocationV0
    source_commit_request_id: int
    generated_request_ids: tuple[int, ...]
    unbound_route_request_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class OwnedDynamicServiceRegistrationStateV0:
    """Immutable single-owner staging snapshot, never a runnable scheduler state."""
    architecture: ArchitectureProfileV0
    allocation_ledger: ComputedEmissionAllocationLedgerV0
    cost_policy: DynamicServiceCostsV0
    base_requests: tuple[MemoryServiceRequestV0, ...]
    base_graph: AccessDependencyGraphV0
    staged_requests: tuple[MemoryServiceRequestV0, ...]
    staged_graph: AccessDependencyGraphV0
    registrations: tuple[DynamicEmissionServiceRegistrationV0, ...]

    def __post_init__(self):
        if (type(self.architecture) is not ArchitectureProfileV0 or
                type(self.allocation_ledger) is not ComputedEmissionAllocationLedgerV0 or
                type(self.cost_policy) is not DynamicServiceCostsV0):
            raise TypeError('invalid dynamic service owner')
        if self.architecture.profile_id != self.allocation_ledger.profile_id:
            raise ValueError('dynamic service owner profile mismatch')
        _require_request_graph(self.base_requests, self.base_graph)
        _require_request_graph(self.staged_requests, self.staged_graph)
        if (tuple(r.request_id for r in self.base_requests) !=
                self.allocation_ledger.existing_request_ids):
            raise ValueError('initial request namespace does not match allocation owner')
        base_ids = {r.request_id for r in self.base_requests}
        staged = {r.request_id: r for r in self.staged_requests}
        if any(staged.get(r.request_id) != r for r in self.base_requests):
            raise ValueError('base service request mutated')
        original = {d.request_id: _predecessors(d) for d in self.base_graph.dependencies}
        new = {d.request_id: _predecessors(d) for d in self.staged_graph.dependencies}
        if any(new.get(rid) != predecessors for rid, predecessors in original.items()):
            raise ValueError('base causal history mutated')
        if (type(self.registrations) is not tuple or
                len(self.registrations) != len(self.allocation_ledger.allocations) or
                any(type(x) is not DynamicEmissionServiceRegistrationV0
                    for x in self.registrations)):
            raise ValueError('registration/allocation history mismatch')
        dynamic_ids = []
        batches = {b.state_commit_request_id: b for b in
                   serialize_internal_access_graph_v0(self.base_requests, self.base_graph).batches}
        for registration, allocation in zip(self.registrations, self.allocation_ledger.allocations):
            if registration.allocation != allocation:
                raise ValueError('registration does not match owned allocation')
            ids = (allocation.emission_request_id,) + allocation.route_request_ids
            if (registration.generated_request_ids != ids or
                    registration.unbound_route_request_ids != allocation.route_request_ids):
                raise ValueError('inconsistent staged dynamic service IDs')
            dynamic_ids.extend(ids)
            topo = allocation.topology
            batch = batches.get(registration.source_commit_request_id)
            if (batch is None or batch.node_id != topo.source_node_id or
                    batch.epoch_id != topo.epoch_id or batch.event_time != topo.event_time or
                    batch.target_pe_id != topo.source_pe_id):
                raise ValueError('staged emission not bound to source neuronal batch')
            emission = staged.get(allocation.emission_request_id)
            if (emission is None or emission.kind is not Kind.EMISSION_RECORD or
                    emission.domain is not Domain.EVENT or
                    emission.target_id != f'outputs:{topo.source_node_id}' or
                    emission.target_pe_id != topo.source_pe_id or
                    emission.requester_pe_id != topo.source_pe_id or
                    emission.epoch_id != topo.epoch_id or
                    emission.event_time != topo.event_time or
                    emission.quantity != len(topo.candidate_outputs) or
                    emission.activity is not Activity.EXECUTE or
                    emission.profile_id != self.cost_policy.service_profile_id or
                    emission.principal_id != f'computed-emission-{emission.request_id}' or
                    emission.service_units != self.cost_policy.emission_units or
                    new.get(emission.request_id) != tuple(sorted((
                        batch.program_request_id, batch.state_load_request_id,
                        batch.consume_request_id,
                    )))):
                raise ValueError('invalid staged EMISSION_RECORD request/dependency')
            for route, rid in zip(topo.routes, allocation.route_request_ids):
                oc = route.occurrence
                request = staged.get(rid)
                if (request is None or request.kind is not Kind.ROUTE_ENQUEUE or
                        request.domain is not Domain.EVENT or
                        request.target_id != f'events:{oc.target_node_id}' or
                        request.target_pe_id != oc.target_pe_id or
                        request.requester_pe_id != oc.source_pe_id or
                        request.epoch_id != topo.epoch_id or
                        request.event_time != oc.emission_event_time or
                        request.quantity != 1 or
                        request.activity is not Activity.ROUTER or
                        request.profile_id != self.cost_policy.service_profile_id or
                        request.principal_id != f'computed-route-{request.request_id}' or
                        request.service_units != self.cost_policy.route_units or
                        new.get(rid) != (allocation.emission_request_id,)):
                    raise ValueError('invalid staged ROUTE_ENQUEUE request/dependency')
        if (set(dynamic_ids) & base_ids or
                len(dynamic_ids) != len(set(dynamic_ids)) or
                set(staged) != base_ids | set(dynamic_ids)):
            raise ValueError('staged request namespace/coverage mismatch')


@dataclass(frozen=True, slots=True)
class OwnedDynamicServiceRegistrationStepV0:
    registration: DynamicEmissionServiceRegistrationV0
    state: OwnedDynamicServiceRegistrationStateV0


def initialize_owned_dynamic_services_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    placement: PEAdmissionManifestV0,
    image: VersionedNeuronImageV0,
    base_requests: tuple[MemoryServiceRequestV0, ...],
    base_graph: AccessDependencyGraphV0,
    cost_policy: DynamicServiceCostsV0,
    *,
    first_dynamic_request_id: int | None = None,
) -> OwnedDynamicServiceRegistrationStateV0:
    """Initialize staged dynamic namespace after all existing service IDs."""
    if type(cost_policy) is not DynamicServiceCostsV0:
        raise TypeError('invalid dynamic service cost policy')
    _require_request_graph(base_requests, base_graph)
    if any(r.epoch_id != image.epoch_id for r in base_requests):
        raise ValueError('mixed service request epochs')
    ledger = initialize_computed_emission_allocation_v0(
        architecture, network, placement, image,
        existing_request_ids=tuple(r.request_id for r in base_requests),
        first_dynamic_request_id=first_dynamic_request_id,
    )
    return OwnedDynamicServiceRegistrationStateV0(
        architecture, ledger, cost_policy, base_requests, base_graph,
        base_requests, base_graph, (),
    )


def register_owned_computed_emission_services_v0(
    state: OwnedDynamicServiceRegistrationStateV0,
    image: VersionedNeuronImageV0,
    prepared: PreparedCoreTransitionV0,
) -> OwnedDynamicServiceRegistrationStepV0:
    """Allocate Core emission IDs and stage service requests atomically.

    These requests are NOT admitted to Service Quantum or the OUTPUT controller:
    route-to-destination-consumer ownership and physical grants remain unbound.
    """
    if (type(state) is not OwnedDynamicServiceRegistrationStateV0 or
            type(image) is not VersionedNeuronImageV0 or
            type(prepared) is not PreparedCoreTransitionV0):
        raise TypeError('invalid dynamic emission registration inputs')
    # Source batch must already have causally serialized P/S/EVENT/COMMIT.
    serialized = _require_request_graph(state.staged_requests, state.staged_graph)
    batches = [b for b in serialized.batches if
               (b.node_id, b.epoch_id, b.event_time) ==
               (prepared.node_id, prepared.epoch_id, prepared.event_time)]
    if len(batches) != 1:
        raise ValueError('no unique prepared source neuronal batch')
    batch = batches[0]
    alloc = allocate_computed_emission_v0(
        state.architecture, image, prepared, state.allocation_ledger,
    )
    allocation = alloc.allocation
    topology = allocation.topology
    if batch.target_pe_id != topology.source_pe_id:
        raise ValueError('computed emission source PE mismatch')
    emit_id = allocation.emission_request_id
    policy = state.cost_policy
    emitted = MemoryServiceRequestV0(
        request_id=emit_id, principal_id=f'computed-emission-{emit_id}',
        activity=Activity.EXECUTE, profile_id=policy.service_profile_id,
        epoch_id=topology.epoch_id,
        requester_pe_id=topology.source_pe_id,
        target_pe_id=topology.source_pe_id,
        target_id=f'outputs:{topology.source_node_id}',
        domain=Domain.EVENT, kind=Kind.EMISSION_RECORD,
        quantity=len(topology.candidate_outputs),
        service_units=policy.emission_units,
        event_time=topology.event_time,
    )
    routed = tuple(MemoryServiceRequestV0(
        request_id=route.occurrence.event_id,
        principal_id=f'computed-route-{route.occurrence.event_id}',
        activity=Activity.ROUTER, profile_id=policy.service_profile_id,
        epoch_id=topology.epoch_id,
        requester_pe_id=route.occurrence.source_pe_id,
        target_pe_id=route.occurrence.target_pe_id,
        target_id=f'events:{route.occurrence.target_node_id}',
        domain=Domain.EVENT, kind=Kind.ROUTE_ENQUEUE,
        quantity=1, service_units=policy.route_units,
        event_time=route.occurrence.emission_event_time,
    ) for route in topology.routes)
    additions = (emitted,) + routed
    deps = (
        AccessDependencyV0(emit_id, tuple(sorted((
            batch.program_request_id, batch.state_load_request_id,
            batch.consume_request_id,
        )))),
    ) + tuple(AccessDependencyV0(route.request_id, (emit_id,)) for route in routed)
    registration = DynamicEmissionServiceRegistrationV0(
        allocation, batch.state_commit_request_id,
        (emit_id,) + allocation.route_request_ids,
        allocation.route_request_ids,
    )
    successor = OwnedDynamicServiceRegistrationStateV0(
        state.architecture, alloc.ledger, policy,
        state.base_requests, state.base_graph,
        tuple(sorted(state.staged_requests + additions, key=lambda r: r.request_id)),
        AccessDependencyGraphV0(tuple(sorted(
            state.staged_graph.dependencies + deps, key=lambda d: d.request_id,
        ))),
        state.registrations + (registration,),
    )
    return OwnedDynamicServiceRegistrationStepV0(registration, successor)
