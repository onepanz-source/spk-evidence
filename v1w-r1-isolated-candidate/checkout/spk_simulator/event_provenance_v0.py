"""SPK event provenance reconciliation v0.

Reconciles consumed events with initial stimuli and
routed deliveries, preserving event multiplicity.

No SERVICE_TIME or memory scheduling.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0,
)
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.functional_trace_v0 import ObservedExecutionV0
from spk_simulator.logical_access_v0 import (
    LogicalAccessPlanV0,
    generate_logical_accesses_v0,
)


@dataclass(frozen=True, slots=True)
class BatchInputProvenanceV0:
    batch_index: int
    timestamp: int
    node_id: str
    channels: tuple[int, ...]
    initial_count: int
    routed_request_ids: tuple[int, ...]

    @property
    def routed_count(self) -> int:
        return len(self.routed_request_ids)


@dataclass(frozen=True, slots=True)
class EventProvenanceV0:
    batches: tuple[BatchInputProvenanceV0, ...]
    initial_count: int
    routed_count: int
    processed_count: int


def _event_key(event):
    return (event.timestamp, event.node_id, event.channel)


def reconcile_event_provenance_v0(
    network: NetworkV0,
    observed: ObservedExecutionV0,
    placement: PEAdmissionManifestV0,
    plan: LogicalAccessPlanV0,
    initial_events: tuple[NetworkEventV0, ...],
) -> EventProvenanceV0:
    """Reconcile all consumed event occurrences.

    Routed request IDs identify their associated
    ROUTE_ENQUEUE logical access intents.

    No physical delivery time is inferred.
    """

    if type(network) is not NetworkV0:
        raise TypeError("invalid network")
    if type(observed) is not ObservedExecutionV0:
        raise TypeError("invalid observation")
    if type(placement) is not PEAdmissionManifestV0:
        raise TypeError("invalid placement")
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError("invalid access plan")

    if type(initial_events) is not tuple:
        raise TypeError("initial events must be a tuple")

    if any(
        type(event) is not NetworkEventV0
        for event in initial_events
    ):
        raise TypeError("invalid initial event")

    # Bind provenance to the exact deterministic
    # logical access plan expected for this trace.
    expected_plan = generate_logical_accesses_v0(
        network,
        observed,
        placement,
        epoch_id=plan.epoch_id,
    )

    if plan != expected_plan:
        raise ValueError("access plan/trace mismatch")

    batch_keys = [
        (batch.timestamp, batch.node_id)
        for batch in observed.batches
    ]

    if len(batch_keys) != len(set(batch_keys)):
        raise ValueError("duplicate batch identity")

    initial = Counter(
        _event_key(event) for event in initial_events
    )

    routed = Counter(
        (
            route.delivery_timestamp,
            route.target_node,
            route.target_channel,
        )
        for route in observed.routes
    )

    consumed = Counter(
        (batch.timestamp, batch.node_id, channel)
        for batch in observed.batches
        for channel in batch.channels
    )

    if consumed != initial + routed:
        raise ValueError(
            "event provenance conservation failure"
        )

    # Logical route references are generated in batch
    # order. Within each batch, they retain the
    # corresponding observed route order.
    routes_by_source = defaultdict(list)

    for route in observed.routes:
        routes_by_source[
            (route.emission_timestamp, route.source_node)
        ].append(route)

    ordered_routes = []

    for batch in observed.batches:
        ordered_routes.extend(
            routes_by_source.pop(
                (batch.timestamp, batch.node_id),
                (),
            )
        )

    if routes_by_source:
        raise ValueError("route without source batch")

    route_refs = tuple(
        reference
        for reference in plan.references
        if reference.intent.kind
        is AccessIntentKindV0.ROUTE_ENQUEUE
    )

    if len(route_refs) != len(ordered_routes):
        raise ValueError("route/reference count mismatch")

    incoming = defaultdict(list)

    for route, reference in zip(
        ordered_routes, route_refs
    ):
        intent = reference.intent
        source_pe = plan.catalog.get(
            f"state:{route.source_node}"
        ).pe_id

        if not (
            intent.activity is ActivityV0.ROUTER
            and intent.node_id == route.target_node
            and intent.pe_id == source_pe
            and intent.event_time
                == route.emission_timestamp
            and intent.quantity == 1
            and reference.target_id
                == f"events:{route.target_node}"
        ):
            raise ValueError(
                "route/reference identity mismatch"
            )

        key = (
            route.delivery_timestamp,
            route.target_node,
            route.target_channel,
        )

        incoming[key].append(intent.request_id)

    batch_provenance = []

    for index, batch in enumerate(observed.batches):
        counts = Counter(batch.channels)
        initial_count = 0
        route_ids = []

        for channel in sorted(counts):
            key = (batch.timestamp, batch.node_id, channel)

            external_count = initial[key]
            ids = incoming.pop(key, [])

            if external_count + len(ids) != counts[channel]:
                raise ValueError(
                    "batch event provenance mismatch"
                )

            initial_count += external_count
            route_ids.extend(ids)

        batch_provenance.append(
            BatchInputProvenanceV0(
                batch_index=index,
                timestamp=batch.timestamp,
                node_id=batch.node_id,
                channels=batch.channels,
                initial_count=initial_count,
                routed_request_ids=tuple(sorted(route_ids)),
            )
        )

    if incoming:
        raise ValueError("unconsumed routed provenance")

    return EventProvenanceV0(
        batches=tuple(batch_provenance),
        initial_count=len(initial_events),
        routed_count=len(observed.routes),
        processed_count=sum(
            len(batch.channels)
            for batch in observed.batches
        ),
    )
