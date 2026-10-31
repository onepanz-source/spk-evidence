"""Derive logical memory access requirements from Network v0.

Requirements, not observed physical memory transactions.
No scheduling or SERVICE_TIME assignment.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
    MemoryDomainV0 as Domain,
    MemoryAccessIntentV0,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0 as Space,
    MemoryTargetV0,
    MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
)
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.functional_trace_v0 import ObservedExecutionV0


@dataclass(frozen=True, slots=True)
class LogicalAccessPlanV0:
    epoch_id: str
    catalog: MemoryTargetCatalogV0
    references: tuple[MemoryTargetReferenceV0, ...]


def generate_logical_accesses_v0(
    network: NetworkV0,
    observed: ObservedExecutionV0,
    placement: PEAdmissionManifestV0,
    *,
    epoch_id: str = "E0",
) -> LogicalAccessPlanV0:
    """Derive logical requirements from a validated trace."""

    if type(network) is not NetworkV0:
        raise TypeError("invalid network")
    if type(observed) is not ObservedExecutionV0:
        raise TypeError("invalid observed execution")
    if type(placement) is not PEAdmissionManifestV0:
        raise TypeError("invalid placement")
    if (
        type(epoch_id) is not str
        or not epoch_id
        or epoch_id.strip() != epoch_id
    ):
        raise ValueError("invalid epoch_id")

    node_ids = {node.node_id for node in network.nodes}
    node_pe = {}

    for usage in placement.pe_usage:
        for node_id in usage.node_ids:
            if node_id in node_pe:
                raise ValueError("duplicate placed node")
            node_pe[node_id] = usage.pe_id

    if set(node_pe) != node_ids:
        raise ValueError("placement/network node mismatch")

    for node_id in node_ids:
        if node_id.strip() != node_id:
            raise ValueError(
                "node identifier unsupported by access v0"
            )

    if observed.result.processed_batches != len(
        observed.batches
    ):
        raise ValueError("inconsistent batch count")

    if observed.result.processed_events != sum(
        len(batch.channels) for batch in observed.batches
    ):
        raise ValueError("inconsistent event count")

    batch_emissions = Counter(
        (batch.timestamp, batch.node_id, channel)
        for batch in observed.batches
        for channel in batch.output_channels
    )

    result_emissions = Counter(
        (event.timestamp, event.node_id, event.channel)
        for event in observed.result.emissions
    )

    if batch_emissions != result_emissions:
        raise ValueError("inconsistent emission trace")

    expected_routes = Counter(
        (
            event.timestamp,
            event.node_id,
            event.channel,
            event.timestamp + edge.delay_ticks,
            edge.target_node,
            edge.target_channel,
            edge.delay_ticks,
        )
        for event in observed.result.emissions
        for edge in network.edges
        if (
            edge.source_node == event.node_id
            and edge.source_channel == event.channel
        )
    )

    actual_routes = Counter(
        (
            route.emission_timestamp,
            route.source_node,
            route.source_channel,
            route.delivery_timestamp,
            route.target_node,
            route.target_channel,
            route.delay_ticks,
        )
        for route in observed.routes
    )

    if actual_routes != expected_routes:
        raise ValueError("inconsistent routing trace")

    targets = []

    for node_id in sorted(node_ids):
        pe_id = node_pe[node_id]

        for prefix, domain in (
            ("program", Domain.PROGRAM),
            ("state", Domain.STATE),
            ("events", Domain.EVENT),
            ("outputs", Domain.EVENT),
        ):
            targets.append(
                MemoryTargetV0(
                    target_id=f"{prefix}:{node_id}",
                    space=Space.ACTIVE,
                    epoch_id=epoch_id,
                    pe_id=pe_id,
                    domain=domain,
                    owner_node_id=node_id,
                )
            )

    catalog = MemoryTargetCatalogV0(tuple(targets))
    references = []

    def add(kind, node_id, requester_pe, timestamp,
            target_id, quantity=1, activity=Activity.EXECUTE):
        intent = MemoryAccessIntentV0(
            request_id=len(references),
            epoch_id=epoch_id,
            pe_id=requester_pe,
            activity=activity,
            kind=kind,
            node_id=node_id,
            event_time=timestamp,
            quantity=quantity,
        )
        references.append(
            MemoryTargetReferenceV0(intent, target_id)
        )

    routes_by_batch = defaultdict(list)

    for route in observed.routes:
        routes_by_batch[
            (route.emission_timestamp, route.source_node)
        ].append(route)

    for batch in observed.batches:
        node_id = batch.node_id

        if node_id not in node_pe:
            raise ValueError("trace references unknown node")

        pe_id = node_pe[node_id]
        timestamp = batch.timestamp

        add(Kind.PROGRAM_REFERENCE, node_id, pe_id,
            timestamp, f"program:{node_id}")

        add(Kind.STATE_LOAD, node_id, pe_id,
            timestamp, f"state:{node_id}")

        add(Kind.BATCH_CONSUME, node_id, pe_id,
            timestamp, f"events:{node_id}",
            quantity=len(batch.channels))

        add(Kind.STATE_COMMIT, node_id, pe_id,
            timestamp, f"state:{node_id}")

        if batch.output_channels:
            add(Kind.EMISSION_RECORD, node_id, pe_id,
                timestamp, f"outputs:{node_id}",
                quantity=len(batch.output_channels))

        for route in routes_by_batch[(timestamp, node_id)]:
            add(
                Kind.ROUTE_ENQUEUE,
                route.target_node,
                pe_id,
                route.emission_timestamp,
                f"events:{route.target_node}",
                activity=Activity.ROUTER,
            )

    return LogicalAccessPlanV0(
        epoch_id=epoch_id,
        catalog=catalog,
        references=tuple(references),
    )
