"""SPK logical resource admission v0.

Architecture-independent structural admission.
No host memory measurements or PE mapping.
"""

from collections import Counter
from dataclasses import dataclass, fields

from spk_core.isa import CoreEmit
from spk_network.events_v0 import (
    NetworkEventV0,
    validate_network_events_v0,
)
from spk_network.model_v0 import NetworkV0


class AdmissionRejectedV0(ValueError):
    """The network exceeds a declared resource budget."""

    code = "ADMISSION_REJECTED"

    def __init__(self, metric, actual, limit):
        self.metric = metric
        self.actual = actual
        self.limit = limit
        super().__init__(
            f"{metric}: required={actual}, limit={limit}"
        )


@dataclass(frozen=True, slots=True)
class ResourceProfileV0:
    profile_id: str = "spk-logical-lab-v0"

    max_nodes: int = 128
    max_edges: int = 2048
    max_instructions_per_node: int = 64
    max_emit_instructions_per_node: int = 10
    max_fanout_per_channel: int = 32

    max_initial_events: int = 4096
    max_batches: int = 5000
    max_scheduled_events: int = 25000
    max_emissions: int = 50000

    max_initial_timestamp: int = 1000000
    max_edge_delay_ticks: int = 100000

    def __post_init__(self):
        if (
            type(self.profile_id) is not str
            or not self.profile_id
        ):
            raise ValueError("invalid profile_id")

        zero_allowed = {
            "max_initial_events",
            "max_initial_timestamp",
        }

        for field in fields(self):
            if field.name == "profile_id":
                continue

            value = getattr(self, field.name)
            minimum = (
                0 if field.name in zero_allowed else 1
            )

            if type(value) is not int or value < minimum:
                raise ValueError(
                    f"invalid resource limit: {field.name}"
                )

        if (
            self.max_initial_events
            > self.max_scheduled_events
        ):
            raise ValueError(
                "initial-event capacity exceeds "
                "scheduled-event capacity"
            )


@dataclass(frozen=True, slots=True)
class AdmissionManifestV0:
    profile_id: str
    node_count: int
    edge_count: int
    instruction_count: int
    max_node_instructions: int
    max_node_emits: int
    max_channel_fanout: int
    initial_event_count: int
    conservative_emission_bound: int
    runtime_max_batches: int
    runtime_max_events: int


def _check(metric, actual, limit):
    if actual > limit:
        raise AdmissionRejectedV0(
            metric, actual, limit
        )


def admit_network_v0(
    network: NetworkV0,
    events: tuple[NetworkEventV0, ...],
    profile: ResourceProfileV0,
) -> AdmissionManifestV0:
    """Admit a network under logical resource limits."""

    if not isinstance(network, NetworkV0):
        raise TypeError("expected NetworkV0")

    if not isinstance(profile, ResourceProfileV0):
        raise TypeError("expected ResourceProfileV0")

    if type(events) is not tuple:
        raise TypeError("events must be a tuple")

    if any(
        not isinstance(event, NetworkEventV0)
        for event in events
    ):
        raise TypeError("invalid network event")

    validate_network_events_v0(network, events)

    node_count = len(network.nodes)
    edge_count = len(network.edges)

    instruction_counts = [
        len(node.program.instructions)
        for node in network.nodes
    ]

    emit_counts = [
        sum(
            isinstance(instruction, CoreEmit)
            for instruction in node.program.instructions
        )
        for node in network.nodes
    ]

    total_instructions = sum(instruction_counts)
    max_instructions = max(instruction_counts)
    max_emits = max(emit_counts)

    fanouts = Counter(
        (edge.source_node, edge.source_channel)
        for edge in network.edges
    )

    max_fanout = max(
        fanouts.values(),
        default=0,
    )

    max_delay = max(
        (edge.delay_ticks for edge in network.edges),
        default=0,
    )

    max_timestamp = max(
        (event.timestamp for event in events),
        default=0,
    )

    emission_bound = profile.max_batches * max_emits

    _check("nodes", node_count, profile.max_nodes)
    _check("edges", edge_count, profile.max_edges)

    _check(
        "instructions_per_node",
        max_instructions,
        profile.max_instructions_per_node,
    )

    _check(
        "emit_instructions_per_node",
        max_emits,
        profile.max_emit_instructions_per_node,
    )

    _check(
        "fanout_per_channel",
        max_fanout,
        profile.max_fanout_per_channel,
    )

    _check(
        "initial_events",
        len(events),
        profile.max_initial_events,
    )

    _check(
        "initial_timestamp",
        max_timestamp,
        profile.max_initial_timestamp,
    )

    _check(
        "edge_delay_ticks",
        max_delay,
        profile.max_edge_delay_ticks,
    )

    _check(
        "conservative_emissions",
        emission_bound,
        profile.max_emissions,
    )

    return AdmissionManifestV0(
        profile_id=profile.profile_id,
        node_count=node_count,
        edge_count=edge_count,
        instruction_count=total_instructions,
        max_node_instructions=max_instructions,
        max_node_emits=max_emits,
        max_channel_fanout=max_fanout,
        initial_event_count=len(events),
        conservative_emission_bound=emission_bound,
        runtime_max_batches=profile.max_batches,
        runtime_max_events=profile.max_scheduled_events,
    )
