"""SPK S3.7d/3b2b2k/18: bounded dynamic ROUTE_ENQUEUE transit.

Executes OUTPUT -> EVENT and confirms completed route service on a joint
immutable *dynamic-lane* snapshot. It does not mint route IDs, publish source
OUTPUT, consume destination batches, or authenticate the provenance of an
initial snapshot. No existing frozen component is modified.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0, ServiceConfirmedV0,
)
from spk_simulator.dynamic_destination_inventory_v0 import (
    ComputedDestinationInventoryV0, derive_dynamic_destination_inventory_v0,
)
from spk_simulator.event_storage_v0 import (
    RoutedStorageBlockedV0, RoutedStorageStateV0,
    admit_routed_event_v0, routed_storage_usage_v0,
)
from spk_simulator.owned_dynamic_service_registration_v0 import (
    OwnedDynamicServiceRegistrationStateV0,
)


def _mappings(registry):
    route_to_emit = {}
    expected = {}
    for record in registry.registrations:
        emission = record.allocation.emission_request_id
        for route in record.allocation.topology.routes:
            rid = route.occurrence.event_id
            if rid in expected:
                raise ValueError('duplicate dynamic route registration')
            expected[rid] = route.occurrence
            route_to_emit[rid] = emission
    return expected, route_to_emit


@dataclass(frozen=True, slots=True)
class OwnedDynamicRouteTransitStateV0:
    """Joint snapshot. Only its owner may publish successive versions.

    Caller-created snapshots remain untrusted. Full integration must bind the
    state to one scheduler and its boundary/effect authority.
    """
    registry: OwnedDynamicServiceRegistrationStateV0
    storage: RoutedStorageStateV0
    service: ServiceQuantumStateV0

    def __post_init__(self):
        if (type(self.registry) is not OwnedDynamicServiceRegistrationStateV0 or
                type(self.storage) is not RoutedStorageStateV0 or
                type(self.service) is not ServiceQuantumStateV0):
            raise TypeError('invalid dynamic transit snapshot')
        architecture = self.registry.architecture
        routed_storage_usage_v0(architecture, self.storage)
        if (architecture.profile_id != self.storage.profile_id or
                self.registry.allocation_ledger.epoch_id != self.storage.epoch_id):
            raise ValueError('transit profile/epoch mismatch')
        inventory = derive_dynamic_destination_inventory_v0(
            architecture, self.registry, self.storage,
        )
        # Inventory also validates all route occurrence identities/provenance.
        if inventory.supports_consume_admission:
            raise ValueError('dynamic transit must not close destination batches')
        request_by_id = {r.request_id: r for r in self.registry.staged_requests}
        deps = {d.request_id: (d.predecessor_ids if hasattr(d, "predecessor_ids") else d.predecessors) for d in self.registry.staged_graph.dependencies}
        partial = {x.request_id for x in self.service.partial}
        awaiting = {x.request_id for x in self.service.awaiting_confirmation}
        completed = {x.request_id for x in self.service.confirmed}
        if (partial | awaiting | completed) - set(request_by_id):
            raise ValueError('unknown request in dynamic service state')
        for rid in partial | awaiting | completed:
            if not set(deps[rid]) <= completed:
                raise ValueError('service history violates causal dependencies')
        for x in self.service.partial:
            if x.served_units >= request_by_id[x.request_id].service_units:
                raise ValueError('invalid partial service quantity')
        expected, route_to_emit = _mappings(self.registry)
        physical = {x.event_id: 'OUTPUT' for x in self.storage.pending_output}
        physical.update({x.event_id: 'EVENT' for x in self.storage.admitted_events})
        physical.update({x: 'CONSUMED' for x in self.storage.consumed_ids})
        for record in self.registry.registrations:
            emission = record.allocation.emission_request_id
            stages = tuple(physical.get(rid, 'STAGED') for rid in record.allocation.route_request_ids)
            # Published bundles cannot be partial. All routed slots must have
            # existed in OUTPUT before individual route deliveries started.
            if 'STAGED' in stages and any(s != 'STAGED' for s in stages):
                raise ValueError('partial dynamic source fan-out publication')
            if any(s != 'STAGED' for s in stages) and emission not in completed:
                raise ValueError('physical output without confirmed source emission')
        for rid in expected:
            stage = physical.get(rid, 'STAGED')
            if stage == 'STAGED' and rid in (partial | awaiting | completed):
                raise ValueError('dynamic route serviced before OUTPUT publication')
            if stage == 'OUTPUT' and rid in completed:
                raise ValueError('route confirmed before EVENT delivery')
            if stage in ('EVENT', 'CONSUMED') and rid not in completed:
                raise ValueError('route delivered without confirmed service')
            if stage == 'EVENT' and rid in (partial | awaiting):
                raise ValueError('delivered route cannot be in flight')
            if rid in partial | awaiting | completed and route_to_emit[rid] not in completed:
                raise ValueError('route serviced before emission confirmation')
            if request_by_id[rid].kind is not Kind.ROUTE_ENQUEUE:
                raise ValueError('dynamic route request kind mismatch')


@dataclass(frozen=True, slots=True)
class OwnedDynamicRouteTransitStepV0:
    service_boundary: int
    delivered_route_request_ids: tuple[int, ...]
    blocked_route_request_ids: tuple[int, ...]
    inventory: ComputedDestinationInventoryV0
    state: OwnedDynamicRouteTransitStateV0
    status: str


def advance_owned_dynamic_route_transit_v0(
    state: OwnedDynamicRouteTransitStateV0,
) -> OwnedDynamicRouteTransitStepV0:
    """Deterministically deliver finished ROUTE_ENQUEUE requests when EVENT fits.

    A finished route must already have its own occurrence in OUTPUT, all causal
    predecessors confirmed, and its own service cost fully exhausted. This
    operation does not advance SERVICE_TIME or start new memory service.
    """
    if type(state) is not OwnedDynamicRouteTransitStateV0:
        raise TypeError('invalid transit state')
    registry = state.registry
    architecture = registry.architecture
    expected, _ = _mappings(registry)
    finished = {x.request_id: x for x in state.service.awaiting_confirmation}
    pending = {x.event_id: x for x in state.storage.pending_output}
    completed = {x.request_id for x in state.service.confirmed}
    boundary = state.service.next_service_tick
    # Only registered, fully served dynamic route requests are eligible. The
    # route's id is also the physical occurrence id, never caller-assigned.
    eligible = tuple(sorted(
        rid for rid in expected if rid in finished and rid in pending
    ))
    storage = state.storage
    delivered, blocked = [], []
    for rid in eligible:
        if finished[rid].finish_boundary > boundary:
            raise ValueError('route service is not finished at current boundary')
        try:
            storage = admit_routed_event_v0(architecture, storage, rid)
        except RoutedStorageBlockedV0 as exc:
            if exc.domain != 'EVENT':
                raise
            blocked.append(rid)
            continue
        delivered.append(rid)
    service = replace(
        state.service,
        awaiting_confirmation=tuple(x for x in state.service.awaiting_confirmation
                                    if x.request_id not in delivered),
        confirmed=tuple(sorted(state.service.confirmed + tuple(
            ServiceConfirmedV0(rid, boundary) for rid in delivered
        ), key=lambda x: x.request_id)),
    )
    successor = OwnedDynamicRouteTransitStateV0(registry, storage, service)
    inventory = derive_dynamic_destination_inventory_v0(
        architecture, registry, successor.storage,
    )
    assert inventory.supports_consume_admission is False
    return OwnedDynamicRouteTransitStepV0(
        boundary, tuple(delivered), tuple(blocked), inventory, successor,
        'PROGRESSED' if delivered else 'BACKPRESSURE' if blocked else 'IDLE',
    )
