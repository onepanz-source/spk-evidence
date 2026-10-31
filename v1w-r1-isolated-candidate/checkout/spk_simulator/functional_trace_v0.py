"""SPK functional execution trace v0.

Non-mutating observation of frozen Network v0.

This module records actual runtime observations.
It does not simulate memory transactions or timing.
"""

from dataclasses import dataclass

from spk_network.model_v0 import NetworkV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import (
    NetworkResultV0,
    run_network_v0,
)


@dataclass(frozen=True, slots=True)
class BatchTraceV0:
    timestamp: int
    node_id: str
    channels: tuple[int, ...]
    final_raw: int
    final_guard: bool
    output_channels: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RouteTraceV0:
    emission_timestamp: int
    source_node: str
    source_channel: int
    delivery_timestamp: int
    target_node: str
    target_channel: int
    delay_ticks: int


@dataclass(frozen=True, slots=True)
class ObservedExecutionV0:
    result: NetworkResultV0
    batches: tuple[BatchTraceV0, ...]
    routes: tuple[RouteTraceV0, ...]


class _FunctionalRecorderV0:
    def __init__(self):
        self.batches = []
        self.routes = []

    def on_batch(self, observation):
        self.batches.append(
            BatchTraceV0(
                timestamp=observation.timestamp,
                node_id=observation.node_id,
                channels=observation.channels,
                final_raw=observation.final_raw,
                final_guard=observation.final_guard,
                output_channels=observation.output_channels,
            )
        )

    def on_route(self, observation):
        self.routes.append(
            RouteTraceV0(
                emission_timestamp=(
                    observation.emission_timestamp
                ),
                source_node=observation.source_node,
                source_channel=observation.source_channel,
                delivery_timestamp=(
                    observation.delivery_timestamp
                ),
                target_node=observation.target_node,
                target_channel=observation.target_channel,
                delay_ticks=observation.delay_ticks,
            )
        )


def run_network_observed_v0(
    network: NetworkV0,
    events: tuple[NetworkEventV0, ...],
    *,
    max_batches: int = 100_000,
    max_events: int = 1_000_000,
) -> ObservedExecutionV0:
    """Run Network v0 and collect its observations."""

    recorder = _FunctionalRecorderV0()

    result = run_network_v0(
        network,
        events,
        max_batches=max_batches,
        max_events=max_events,
        learning_observer=recorder,
    )

    return ObservedExecutionV0(
        result=result,
        batches=tuple(recorder.batches),
        routes=tuple(recorder.routes),
    )
