from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import heapq

from .isa import (
    CoreConfig,
    CoreProgram,
)
from .runtime import run_core_batch


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkNode:
    name: str
    config: CoreConfig
    program: CoreProgram
    initial_raw: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(
                "network node name must not be empty"
            )

        if not (
            0
            <= self.initial_raw
            <= self.config.max_raw
        ):
            raise ValueError(
                f"initial_raw for node "
                f"{self.name!r} must be in "
                f"[0,{self.config.max_raw}]"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkEdge:
    source: str
    source_channel: int

    target: str
    target_channel: int

    delay: int = 1

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError(
                "edge source must not be empty"
            )

        if not self.target:
            raise ValueError(
                "edge target must not be empty"
            )

        if self.source_channel < 0:
            raise ValueError(
                "source_channel must be non-negative"
            )

        if self.target_channel < 0:
            raise ValueError(
                "target_channel must be non-negative"
            )

        #
        # Network v0 is strictly causal.
        #
        # Zero-delay edges are intentionally excluded because they
        # require a separate semantics for instantaneous cycles and
        # fixed-point scheduling.
        #
        if self.delay < 1:
            raise ValueError(
                "SPK Network v0 requires edge delay >= 1"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class CoreNetwork:
    nodes: tuple[NetworkNode, ...]
    edges: tuple[NetworkEdge, ...]

    def __post_init__(self) -> None:
        names = [
            node.name
            for node in self.nodes
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "duplicate network node name"
            )

        known = set(names)

        for edge in self.edges:
            if edge.source not in known:
                raise ValueError(
                    f"unknown edge source: "
                    f"{edge.source!r}"
                )

            if edge.target not in known:
                raise ValueError(
                    f"unknown edge target: "
                    f"{edge.target!r}"
                )

        #
        # Canonical storage makes construction order observationally
        # irrelevant.
        #
        object.__setattr__(
            self,
            "nodes",
            tuple(
                sorted(
                    self.nodes,
                    key=lambda node: node.name,
                )
            ),
        )

        object.__setattr__(
            self,
            "edges",
            tuple(
                sorted(
                    self.edges,
                    key=lambda edge: (
                        edge.source,
                        edge.source_channel,
                        edge.target,
                        edge.target_channel,
                        edge.delay,
                    ),
                )
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class NetworkEvent:
    timestamp: int
    node: str
    channel: int

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError(
                "event timestamp must be non-negative"
            )

        if not self.node:
            raise ValueError(
                "event node must not be empty"
            )

        if self.channel < 0:
            raise ValueError(
                "event channel must be non-negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkNodeState:
    node: str
    raw: int
    last_timestamp: int


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkResult:
    #
    # Every CoreEmit produced by every node.
    #
    emissions: tuple[NetworkEvent, ...]

    #
    # Emissions for which no outgoing matching edge exists.
    #
    terminal_outputs: tuple[NetworkEvent, ...]

    #
    # Final persistent state of every node.
    #
    states: tuple[NetworkNodeState, ...]

    processed_batches: int
    processed_events: int


class NetworkExecutionLimit(
    RuntimeError
):
    pass


def run_core_network(
    network: CoreNetwork,
    events: tuple[NetworkEvent, ...],
    *,
    max_batches: int = 100_000,
    max_events: int = 1_000_000,
) -> NetworkResult:
    """
    Execute a strictly causal SPK/Core network.

    Network v0 semantics:

    - events are triples (timestamp, node, channel);
    - every set of events sharing (timestamp, node) is one Core batch;
    - event multiplicity is preserved;
    - every edge has delay >= 1;
    - node raw state and last_timestamp persist between batches;
    - Core guard remains transient because run_core_batch() resets it;
    - emitted events are routed through every matching edge;
    - parallel edges preserve multiplicity;
    - unmatched emissions are terminal outputs.

    Positive-delay cycles are legal and may diverge. max_batches and
    max_events are operational guards, not algebraic termination
    assumptions.
    """

    if max_batches < 1:
        raise ValueError(
            "max_batches must be >= 1"
        )

    if max_events < 1:
        raise ValueError(
            "max_events must be >= 1"
        )

    nodes = {
        node.name: node
        for node in network.nodes
    }

    states = {
        node.name: NetworkNodeState(
            node=node.name,
            raw=node.initial_raw,
            last_timestamp=0,
        )
        for node in network.nodes
    }

    outgoing = defaultdict(list)

    for edge in network.edges:
        outgoing[
            (
                edge.source,
                edge.source_channel,
            )
        ].append(
            edge
        )

    #
    # Heap entries are canonical triples.
    #
    # Identical tuples may occur more than once, which is exactly how
    # event multiplicity is represented.
    #
    pending: list[
        tuple[int, str, int]
    ] = []

    for event in events:
        if event.node not in nodes:
            raise ValueError(
                f"event targets unknown node: "
                f"{event.node!r}"
            )

        heapq.heappush(
            pending,
            (
                event.timestamp,
                event.node,
                event.channel,
            ),
        )

    scheduled_events = len(
        pending
    )

    if scheduled_events > max_events:
        raise NetworkExecutionLimit(
            "initial event set exceeds max_events"
        )

    emissions: list[
        NetworkEvent
    ] = []

    terminal_outputs: list[
        NetworkEvent
    ] = []

    processed_batches = 0
    processed_events = 0

    while pending:
        if processed_batches >= max_batches:
            raise NetworkExecutionLimit(
                f"network exceeded "
                f"max_batches={max_batches}"
            )

        (
            timestamp,
            node_name,
            channel,
        ) = heapq.heappop(
            pending
        )

        channels = [
            channel
        ]

        #
        # Collect the entire (timestamp,node) equivalence class before
        # executing the node.
        #
        while (
            pending
            and pending[0][0]
            == timestamp
            and pending[0][1]
            == node_name
        ):
            (
                _,
                _,
                next_channel,
            ) = heapq.heappop(
                pending
            )

            channels.append(
                next_channel
            )

        processed_batches += 1
        processed_events += len(
            channels
        )

        node = nodes[
            node_name
        ]

        state = states[
            node_name
        ]

        result = run_core_batch(
            node.config,
            node.program,
            timestamp=timestamp,
            channels=tuple(channels),
            initial_raw=state.raw,
            previous_timestamp=(
                state.last_timestamp
            ),
        )

        states[
            node_name
        ] = NetworkNodeState(
            node=node_name,
            raw=result.final_raw,
            last_timestamp=(
                result.last_timestamp
            ),
        )

        for (
            output_timestamp,
            output_channel,
        ) in result.output.as_pairs():
            emitted = NetworkEvent(
                timestamp=output_timestamp,
                node=node_name,
                channel=output_channel,
            )

            emissions.append(
                emitted
            )

            routes = outgoing.get(
                (
                    node_name,
                    output_channel,
                ),
                (),
            )

            if not routes:
                terminal_outputs.append(
                    emitted
                )

                continue

            for edge in routes:
                routed = NetworkEvent(
                    timestamp=(
                        output_timestamp
                        + edge.delay
                    ),
                    node=edge.target,
                    channel=edge.target_channel,
                )

                scheduled_events += 1

                if scheduled_events > max_events:
                    raise NetworkExecutionLimit(
                        f"network exceeded "
                        f"max_events={max_events}"
                    )

                heapq.heappush(
                    pending,
                    (
                        routed.timestamp,
                        routed.node,
                        routed.channel,
                    ),
                )

    return NetworkResult(
        emissions=tuple(
            sorted(
                emissions
            )
        ),
        terminal_outputs=tuple(
            sorted(
                terminal_outputs
            )
        ),
        states=tuple(
            states[
                node.name
            ]
            for node in network.nodes
        ),
        processed_batches=processed_batches,
        processed_events=processed_events,
    )
