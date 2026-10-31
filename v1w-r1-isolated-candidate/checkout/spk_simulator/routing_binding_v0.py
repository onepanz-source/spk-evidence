"""SPK S3.7b: bind routed storage occurrences to Network v0 provenance.

Grounded in a completed frozen-Network trace. No runtime authentication,
service scheduling, producer stalls, or physical event transfer is modeled.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, ActivityV0
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.event_provenance_v0 import (
    EventProvenanceV0, reconcile_event_provenance_v0,
)
from spk_simulator.event_storage_v0 import (
    RoutedOccurrenceV0, RoutedStorageStateV0,
    offer_routed_output_v0, admit_routed_event_v0, consume_routed_event_v0,
)
from spk_simulator.functional_trace_v0 import ObservedExecutionV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0


def _valid_id(label, value):
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class BoundRouteV0:
    """One witnessed routed event, tied to its destination batch consumption."""

    route_request_id: int
    consume_request_id: int
    target_batch_index: int
    occurrence: RoutedOccurrenceV0

    def __post_init__(self):
        for name in ("route_request_id", "consume_request_id", "target_batch_index"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid {name}")
        if type(self.occurrence) is not RoutedOccurrenceV0:
            raise TypeError("invalid routed occurrence")
        if self.occurrence.event_id != self.route_request_id:
            raise ValueError("route/event ID mismatch")
        if self.route_request_id == self.consume_request_id:
            raise ValueError("route cannot consume itself")


@dataclass(frozen=True, slots=True)
class RoutedBindingManifestV0:
    profile_id: str
    epoch_id: str
    routes: tuple[BoundRouteV0, ...]

    def __post_init__(self):
        _valid_id("profile_id", self.profile_id)
        _valid_id("epoch_id", self.epoch_id)
        if type(self.routes) is not tuple:
            raise TypeError("routes must be a tuple")
        if any(type(route) is not BoundRouteV0 for route in self.routes):
            raise TypeError("invalid bound route")
        ids = tuple(route.route_request_id for route in self.routes)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("noncanonical bound route IDs")
        if any(route.occurrence.epoch_id != self.epoch_id for route in self.routes):
            raise ValueError("bound route epoch mismatch")

    def get(self, route_request_id: int) -> BoundRouteV0:
        if type(route_request_id) is not int or route_request_id < 0:
            raise ValueError("invalid route_request_id")
        for route in self.routes:
            if route.route_request_id == route_request_id:
                return route
        raise KeyError(route_request_id)


def bind_network_routes_v0(
    network: NetworkV0,
    observed: ObservedExecutionV0,
    placement: PEAdmissionManifestV0,
    plan: LogicalAccessPlanV0,
    provenance: EventProvenanceV0,
    initial_events: tuple[NetworkEventV0, ...],
    architecture: ArchitectureProfileV0,
) -> RoutedBindingManifestV0:
    """Build identities from *observed* routing, never from caller-proposed spikes.

    Routing occurrence event_id = ROUTE_ENQUEUE request_id, scoped to epoch.
    One route has one matching destination BATCH_CONSUME request.
    """
    if type(network) is not NetworkV0:
        raise TypeError("invalid network")
    if type(observed) is not ObservedExecutionV0:
        raise TypeError("invalid observed execution")
    if type(placement) is not PEAdmissionManifestV0:
        raise TypeError("invalid placement")
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError("invalid access plan")
    if type(provenance) is not EventProvenanceV0:
        raise TypeError("invalid provenance")
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")
    if type(initial_events) is not tuple or any(
        type(event) is not NetworkEventV0 for event in initial_events
    ):
        raise TypeError("invalid initial events")
    if architecture.profile_id != placement.profile_id:
        raise ValueError("architecture/placement profile mismatch")

    available_pes = {pe.pe_id for pe in architecture.pes}
    node_pe = {}
    for usage in placement.pe_usage:
        if usage.pe_id not in available_pes:
            raise ValueError("placement references unknown PE")
        for node_id in usage.node_ids:
            if node_id in node_pe:
                raise ValueError("duplicate node placement")
            node_pe[node_id] = usage.pe_id
    if set(node_pe) != {node.node_id for node in network.nodes}:
        raise ValueError("placement/network mismatch")

    expected = reconcile_event_provenance_v0(
        network, observed, placement, plan, initial_events,
    )
    if provenance != expected:
        raise ValueError("provenance mismatch")

    consume_by_batch = {}
    for reference in plan.references:
        intent = reference.intent
        if intent.kind is Kind.BATCH_CONSUME:
            key = (intent.event_time, intent.node_id)
            if key in consume_by_batch:
                raise ValueError("duplicate batch consume")
            if reference.target_id != f"events:{intent.node_id}":
                raise ValueError("batch consume target mismatch")
            consume_by_batch[key] = intent.request_id

    routes_by_source = defaultdict(list)
    for route in observed.routes:
        routes_by_source[(route.emission_timestamp, route.source_node)].append(route)

    ordered_routes = []
    for batch in observed.batches:
        ordered_routes.extend(
            routes_by_source.pop((batch.timestamp, batch.node_id), ())
        )
    if routes_by_source:
        raise ValueError("routing without source batch")

    route_references = tuple(
        reference for reference in plan.references
        if reference.intent.kind is Kind.ROUTE_ENQUEUE
    )
    if len(ordered_routes) != len(route_references):
        raise ValueError("route/reference count mismatch")

    incoming_batches = {}
    for batch in provenance.batches:
        for route_id in batch.routed_request_ids:
            if route_id in incoming_batches:
                raise ValueError("duplicate routed consumption identity")
            incoming_batches[route_id] = batch

    if set(incoming_batches) != {
        reference.intent.request_id for reference in route_references
    }:
        raise ValueError("route/consumption coverage mismatch")

    channel_counts = Counter()
    bound = []
    for route, reference in zip(ordered_routes, route_references):
        intent = reference.intent
        route_id = intent.request_id
        consumed_batch = incoming_batches[route_id]
        if (
            intent.activity is not ActivityV0.ROUTER
            or intent.quantity != 1
            or intent.node_id != route.target_node
            or intent.pe_id != node_pe[route.source_node]
            or intent.event_time != route.emission_timestamp
            or intent.epoch_id != plan.epoch_id
            or reference.target_id != f"events:{route.target_node}"
        ):
            raise ValueError("route/request binding mismatch")

        if (
            consumed_batch.timestamp != route.delivery_timestamp
            or consumed_batch.node_id != route.target_node
            or route.target_channel not in consumed_batch.channels
        ):
            raise ValueError("route/consuming batch mismatch")

        key = (
            consumed_batch.timestamp, consumed_batch.node_id,
            route.target_channel,
        )
        channel_counts[key] += 1
        if channel_counts[key] > consumed_batch.channels.count(route.target_channel):
            raise ValueError("routed channel multiplicity exceeds consumed batch")

        consume_id = consume_by_batch.get(
            (consumed_batch.timestamp, consumed_batch.node_id)
        )
        if consume_id is None:
            raise ValueError("missing destination BATCH_CONSUME")

        occurrence = RoutedOccurrenceV0(
            event_id=route_id,
            epoch_id=plan.epoch_id,
            source_node_id=route.source_node,
            source_pe_id=node_pe[route.source_node],
            source_channel=route.source_channel,
            target_node_id=route.target_node,
            target_pe_id=node_pe[route.target_node],
            target_channel=route.target_channel,
            emission_event_time=route.emission_timestamp,
            delivery_event_time=route.delivery_timestamp,
        )
        bound.append(BoundRouteV0(
            route_request_id=route_id,
            consume_request_id=consume_id,
            target_batch_index=consumed_batch.batch_index,
            occurrence=occurrence,
        ))

    return RoutedBindingManifestV0(
        profile_id=architecture.profile_id,
        epoch_id=plan.epoch_id,
        routes=tuple(bound),
    )


def _bound(architecture, state, manifest, route_request_id):
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError("invalid routed binding manifest")
    if type(state) is not RoutedStorageStateV0:
        raise TypeError("invalid storage state")
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")
    if (
        architecture.profile_id != manifest.profile_id
        or state.profile_id != manifest.profile_id
        or state.epoch_id != manifest.epoch_id
    ):
        raise ValueError("routed binding architecture/epoch mismatch")
    # The entire routed-storage state must belong to this exact binding.
    # Otherwise a legitimate operation could coexist with forged occupants.
    for stored in state.pending_output + state.admitted_events:
        try:
            expected = manifest.get(stored.event_id).occurrence
        except KeyError as exc:
            raise ValueError("unbound stored occurrence") from exc
        if stored != expected:
            raise ValueError("stored occurrence differs from binding")
    for event_id in state.consumed_ids:
        try:
            manifest.get(event_id)
        except KeyError as exc:
            raise ValueError("unbound consumed identity") from exc
    return manifest.get(route_request_id)


def offer_bound_routed_event_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    manifest: RoutedBindingManifestV0,
    route_request_id: int,
) -> RoutedStorageStateV0:
    """Offer only the stored occurrence described by a route binding."""
    route = _bound(architecture, state, manifest, route_request_id)
    return offer_routed_output_v0(architecture, state, route.occurrence)


def admit_bound_routed_event_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    manifest: RoutedBindingManifestV0,
    route_request_id: int,
) -> RoutedStorageStateV0:
    route = _bound(architecture, state, manifest, route_request_id)
    if route.occurrence not in state.pending_output:
        raise ValueError("stored pending occurrence differs from binding")
    return admit_routed_event_v0(architecture, state, route_request_id)


def consume_bound_routed_event_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    manifest: RoutedBindingManifestV0,
    route_request_id: int,
    *,
    consume_request_id: int,
) -> RoutedStorageStateV0:
    route = _bound(architecture, state, manifest, route_request_id)
    if type(consume_request_id) is not int or consume_request_id < 0:
        raise ValueError("invalid consume_request_id")
    if route.consume_request_id != consume_request_id:
        raise ValueError("wrong consuming batch request")
    if route.occurrence not in state.admitted_events:
        raise ValueError("stored admitted occurrence differs from binding")
    return consume_routed_event_v0(
        architecture, state, route_request_id,
        target_pe_id=route.occurrence.target_pe_id,
    )
