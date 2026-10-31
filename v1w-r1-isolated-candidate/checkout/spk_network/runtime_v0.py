from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import heapq

from spk_core.runtime import (
    run_core_batch,
)

from .events_v0 import (
    NetworkEventV0,
    validate_network_events_v0,
)
from .learning_v0 import (
    NetworkBatchObservationV0,
    NetworkLearningObserverV0,
    NetworkRouteObservationV0,
)
from .model_v0 import (
    NetworkV0,
)


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class NetworkNodeStateV0:
    node_id: str
    raw: int
    last_timestamp: int


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkResultV0:
    #
    # Every Core EMIT produced during execution.
    #
    emissions: tuple[
        NetworkEventV0,
        ...,
    ]

    #
    # Emissions for which no outgoing edge exists.
    #
    terminal_outputs: tuple[
        NetworkEventV0,
        ...,
    ]

    #
    # Final persistent state of every node.
    #
    states: tuple[
        NetworkNodeStateV0,
        ...,
    ]

    processed_batches: int
    processed_events: int


class NetworkExecutionLimitV0(
    RuntimeError
):
    pass


def _require_positive_limit(
    name: str,
    value: int,
) -> None:
    if (
        type(value) is not int
        or value <= 0
    ):
        raise ValueError(
            f"{name} must be a positive integer"
        )


def run_network_v0(
    network: NetworkV0,
    events: tuple[
        NetworkEventV0,
        ...,
    ],
    *,
    max_batches: int = 100_000,
    max_events: int = 1_000_000,
    learning_observer:
        NetworkLearningObserverV0
        | None = None,
) -> NetworkResultV0:
    """
    Execute one strictly causal Network v0.

    Semantics:

    - events are (timestamp, node_id, channel);
    - one Core batch is the complete equivalence class
      (timestamp, node_id);
    - each node owns persistent (raw, last_timestamp);
    - Core guard remains transient per batch;
    - an EMIT is routed through every matching outgoing edge;
    - parallel edges preserve multiplicity;
    - every edge has delay_ticks > 0, therefore routing is
      strictly causal;
    - structural cycles are allowed but execution is bounded
      by max_batches and max_events.
    """

    _require_positive_limit(
        "max_batches",
        max_batches,
    )

    _require_positive_limit(
        "max_events",
        max_events,
    )

    validate_network_events_v0(
        network,
        events,
    )

    nodes = {
        node.node_id: node
        for node in network.nodes
    }

    states = {
        node.node_id: NetworkNodeStateV0(
            node_id=node.node_id,
            raw=node.initial_raw,
            last_timestamp=0,
        )
        for node in network.nodes
    }

    outgoing = defaultdict(
        list
    )

    for edge in network.edges:
        outgoing[
            (
                edge.source_node,
                edge.source_channel,
            )
        ].append(
            edge
        )

    #
    # Canonical heap tuples.
    # Identical tuples are deliberately retained:
    # heapq is a multiset here, not a set.
    #
    pending = [
        (
            event.timestamp,
            event.node_id,
            event.channel,
        )
        for event in events
    ]

    heapq.heapify(
        pending
    )

    scheduled_events = len(
        pending
    )

    if scheduled_events > max_events:
        raise NetworkExecutionLimitV0(
            "initial event set exceeds "
            f"max_events={max_events}"
        )

    emissions = []
    terminal_outputs = []

    processed_batches = 0
    processed_events = 0

    while pending:
        if processed_batches >= max_batches:
            raise NetworkExecutionLimitV0(
                "network exceeded "
                f"max_batches={max_batches}"
            )

        (
            timestamp,
            node_id,
            channel,
        ) = heapq.heappop(
            pending
        )

        channels = [
            channel
        ]

        #
        # Collect the complete (timestamp,node) batch before
        # executing the node.
        #
        while (
            pending
            and pending[0][0] == timestamp
            and pending[0][1] == node_id
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

        channels.sort()

        processed_batches += 1
        processed_events += len(
            channels
        )

        node = nodes[
            node_id
        ]

        state = states[
            node_id
        ]

        result = run_core_batch(
            node.config,
            node.program,
            timestamp=timestamp,
            channels=tuple(
                channels
            ),
            initial_raw=state.raw,
            previous_timestamp=(
                state.last_timestamp
            ),
        )

        states[
            node_id
        ] = NetworkNodeStateV0(
            node_id=node_id,
            raw=result.final_raw,
            last_timestamp=(
                result.last_timestamp
            ),
        )

        if learning_observer is not None:
            learning_observer.on_batch(
                NetworkBatchObservationV0(
                    timestamp=timestamp,
                    node_id=node_id,
                    channels=tuple(
                        channels
                    ),
                    final_raw=(
                        result.final_raw
                    ),
                    final_guard=(
                        result.final_guard
                    ),
                    output_channels=tuple(
                        channel
                        for (
                            _,
                            channel,
                        )
                        in result.output.as_pairs()
                    ),
                )
            )

        for (
            output_timestamp,
            output_channel,
        ) in result.output.as_pairs():
            emitted = NetworkEventV0(
                timestamp=output_timestamp,
                node_id=node_id,
                channel=output_channel,
            )

            emissions.append(
                emitted
            )

            routes = outgoing.get(
                (
                    node_id,
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
                routed = NetworkEventV0(
                    timestamp=(
                        output_timestamp
                        + edge.delay_ticks
                    ),
                    node_id=edge.target_node,
                    channel=edge.target_channel,
                )

                if learning_observer is not None:
                    learning_observer.on_route(
                        NetworkRouteObservationV0(
                            emission_timestamp=(
                                output_timestamp
                            ),
                            source_node=node_id,
                            source_channel=(
                                output_channel
                            ),
                            delivery_timestamp=(
                                routed.timestamp
                            ),
                            target_node=(
                                edge.target_node
                            ),
                            target_channel=(
                                edge.target_channel
                            ),
                            delay_ticks=(
                                edge.delay_ticks
                            ),
                        )
                    )

                scheduled_events += 1

                if scheduled_events > max_events:
                    raise NetworkExecutionLimitV0(
                        "network exceeded "
                        f"max_events={max_events}"
                    )

                heapq.heappush(
                    pending,
                    (
                        routed.timestamp,
                        routed.node_id,
                        routed.channel,
                    ),
                )

    return NetworkResultV0(
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
            states[node_id]
            for node_id in sorted(
                states
            )
        ),
        processed_batches=(
            processed_batches
        ),
        processed_events=(
            processed_events
        ),
    )
