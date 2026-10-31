from __future__ import annotations

from itertools import product

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.network import (
    CoreNetwork,
    NetworkEdge,
    NetworkEvent,
    NetworkNode,
    run_core_network,
)

from spk_network.events_v0 import (
    NetworkEventV0,
)
from spk_network.model_v0 import (
    NetworkEdgeV0,
    NetworkNodeV0,
    NetworkV0,
)
from spk_network.runtime_v0 import (
    run_network_v0,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


PROGRAMS = (
    CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    ),
    CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    ),
    CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=1,
            ),
        )
    ),
)


EVENT_SETS = (
    (),
    (
        NetworkEventV0(
            0,
            "a",
            0,
        ),
    ),
    (
        NetworkEventV0(
            1,
            "a",
            0,
        ),
        NetworkEventV0(
            1,
            "a",
            0,
        ),
    ),
    (
        NetworkEventV0(
            1,
            "a",
            0,
        ),
        NetworkEventV0(
            3,
            "a",
            0,
        ),
    ),
    (
        NetworkEventV0(
            1,
            "a",
            0,
        ),
        NetworkEventV0(
            1,
            "b",
            0,
        ),
        NetworkEventV0(
            4,
            "a",
            0,
        ),
    ),
)


def topologies():
    yield ()

    yield (
        NetworkEdgeV0(
            source_node="a",
            source_channel=7,
            target_node="b",
            target_channel=0,
            delay_ticks=1,
        ),
    )

    yield (
        NetworkEdgeV0(
            source_node="a",
            source_channel=7,
            target_node="b",
            target_channel=0,
            delay_ticks=2,
        ),
    )

    edge = NetworkEdgeV0(
        source_node="a",
        source_channel=7,
        target_node="b",
        target_channel=0,
        delay_ticks=1,
    )

    yield (
        edge,
        edge,
    )


def to_old_network(
    network: NetworkV0,
) -> CoreNetwork:
    return CoreNetwork(
        nodes=tuple(
            NetworkNode(
                node.node_id,
                node.config,
                node.program,
                initial_raw=(
                    node.initial_raw
                ),
            )
            for node in network.nodes
        ),
        edges=tuple(
            NetworkEdge(
                source=(
                    edge.source_node
                ),
                source_channel=(
                    edge.source_channel
                ),
                target=(
                    edge.target_node
                ),
                target_channel=(
                    edge.target_channel
                ),
                delay=(
                    edge.delay_ticks
                ),
            )
            for edge in network.edges
        ),
    )


def to_old_events(
    events,
):
    return tuple(
        NetworkEvent(
            event.timestamp,
            event.node_id,
            event.channel,
        )
        for event in events
    )


def normalize_new_result(
    result,
):
    return {
        "emissions": tuple(
            (
                event.timestamp,
                event.node_id,
                event.channel,
            )
            for event
            in result.emissions
        ),
        "terminal_outputs": tuple(
            (
                event.timestamp,
                event.node_id,
                event.channel,
            )
            for event
            in result.terminal_outputs
        ),
        "states": tuple(
            sorted(
                (
                    state.node_id,
                    state.raw,
                    state.last_timestamp,
                )
                for state
                in result.states
            )
        ),
        "processed_batches": (
            result.processed_batches
        ),
        "processed_events": (
            result.processed_events
        ),
    }


def normalize_old_result(
    result,
):
    return {
        "emissions": tuple(
            (
                event.timestamp,
                event.node,
                event.channel,
            )
            for event
            in result.emissions
        ),
        "terminal_outputs": tuple(
            (
                event.timestamp,
                event.node,
                event.channel,
            )
            for event
            in result.terminal_outputs
        ),
        "states": tuple(
            sorted(
                (
                    state.node,
                    state.raw,
                    state.last_timestamp,
                )
                for state
                in result.states
            )
        ),
        "processed_batches": (
            result.processed_batches
        ),
        "processed_events": (
            result.processed_events
        ),
    }


def main():
    cases = 0
    mismatches = 0

    first_mismatch = None

    for (
        program_a,
        program_b,
    ) in product(
        PROGRAMS,
        repeat=2,
    ):
        for edges in topologies():
            network = NetworkV0(
                nodes=(
                    NetworkNodeV0(
                        node_id="a",
                        config=CONFIG,
                        program=program_a,
                        initial_raw=8,
                    ),
                    NetworkNodeV0(
                        node_id="b",
                        config=CONFIG,
                        program=program_b,
                        initial_raw=4,
                    ),
                ),
                edges=edges,
            )

            old_network = (
                to_old_network(
                    network
                )
            )

            for events in EVENT_SETS:
                cases += 1

                new_result = (
                    run_network_v0(
                        network,
                        events,
                    )
                )

                old_result = (
                    run_core_network(
                        old_network,
                        to_old_events(
                            events
                        ),
                    )
                )

                new_view = (
                    normalize_new_result(
                        new_result
                    )
                )

                old_view = (
                    normalize_old_result(
                        old_result
                    )
                )

                if new_view != old_view:
                    mismatches += 1

                    if (
                        first_mismatch
                        is None
                    ):
                        first_mismatch = (
                            program_a,
                            program_b,
                            edges,
                            events,
                            new_view,
                            old_view,
                        )

    print(
        "SPK NETWORK V0 "
        "DIFFERENTIAL GATE"
    )
    print()

    print(
        "program variants:",
        len(PROGRAMS),
    )
    print(
        "event-set variants:",
        len(EVENT_SETS),
    )
    print(
        "cases:",
        cases,
    )
    print(
        "mismatches:",
        mismatches,
    )

    if first_mismatch is not None:
        print()
        print(
            "FIRST MISMATCH:"
        )

        for item in first_mismatch:
            print(
                item
            )

    if cases != 180:
        raise SystemExit(
            "NETWORK DIFFERENTIAL FAIL: "
            f"unexpected case count "
            f"{cases}"
        )

    if mismatches:
        raise SystemExit(
            "NETWORK DIFFERENTIAL FAIL: "
            f"{mismatches} mismatches"
        )

    print()
    print(
        "finite claim:"
    )
    print(
        "  new Network v0 runtime "
        "matches historical spk_core.network"
    )
    print(
        "  on all 180 declared "
        "finite compatibility cases"
    )

    print()
    print(
        "SPK NETWORK V0 DIFFERENTIAL "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
