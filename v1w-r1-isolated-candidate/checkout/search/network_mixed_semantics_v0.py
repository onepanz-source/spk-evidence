from __future__ import annotations

from collections import defaultdict
from itertools import product

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_core.network import (
    CoreNetwork,
    NetworkEdge,
    NetworkEvent,
    NetworkNode,
    run_core_network,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


# ----------------------------------------------------------------------
# Node species
# ----------------------------------------------------------------------

def relay_program() -> CoreProgram:
    return CoreProgram(
        (
            CoreAcc(1, 0),
            CoreCmp(1),
            CoreEmit(7),
            CoreReset(0),
        )
    )


def threshold2_program() -> CoreProgram:
    return CoreProgram(
        (
            CoreAcc(1, 0),
            CoreCmp(2),
            CoreEmit(7),
            CoreReset(0),
        )
    )


PROGRAMS = {
    "R": relay_program(),
    "T2": threshold2_program(),
}


# ----------------------------------------------------------------------
# Three-node feed-forward topology.
#
# a is always R and is the external input adapter.
#
# b,c may independently be R or T2.
# ----------------------------------------------------------------------

EDGE_SLOTS = (
    ("a", "b"),
    ("a", "c"),
    ("b", "c"),
)


DELAY_CHOICES = (
    None,
    1,
    2,
)


NODE_TYPE_CHOICES = (
    "R",
    "T2",
)


INPUT_SCENARIOS = (
    (),
    (0,),
    (1,),
    (2,),

    (0, 0),

    (0, 1),
    (0, 2),
    (1, 2),

    (0, 0, 1),
    (0, 1, 1),

    (0, 1, 2),
    (0, 2, 4),

    (0, 1, 2, 3),
    (0, 0, 2, 2),

    (0, 2, 2, 4),
    (0, 1, 3, 4),
)


def make_nodes(
    b_type: str,
    c_type: str,
) -> tuple[NetworkNode, ...]:
    return (
        NetworkNode(
            "a",
            CONFIG,
            PROGRAMS["R"],
        ),
        NetworkNode(
            "b",
            CONFIG,
            PROGRAMS[b_type],
        ),
        NetworkNode(
            "c",
            CONFIG,
            PROGRAMS[c_type],
        ),
    )


def make_edge(
    source: str,
    target: str,
    delay: int,
) -> NetworkEdge:
    return NetworkEdge(
        source=source,
        source_channel=7,
        target=target,
        target_channel=0,
        delay=delay,
    )


def make_network(
    delays,
    b_type: str,
    c_type: str,
) -> CoreNetwork:
    edges = []

    for (
        source,
        target,
    ), delay in zip(
        EDGE_SLOTS,
        delays,
    ):
        if delay is None:
            continue

        edges.append(
            make_edge(
                source,
                target,
                delay,
            )
        )

    return CoreNetwork(
        nodes=make_nodes(
            b_type,
            c_type,
        ),
        edges=tuple(edges),
    )


def external_events(
    timestamps,
) -> tuple[NetworkEvent, ...]:
    return tuple(
        NetworkEvent(
            timestamp=timestamp,
            node="a",
            channel=0,
        )
        for timestamp in timestamps
    )


def output_signature(
    network: CoreNetwork,
):
    """
    Boundary-only finite observation.

    Internal state is intentionally hidden.
    """

    signature = []

    for scenario in INPUT_SCENARIOS:
        result = run_core_network(
            network,
            external_events(
                scenario
            ),
        )

        signature.append(
            result.terminal_outputs
        )

    return tuple(signature)


def stateful_signature(
    network: CoreNetwork,
):
    """
    Stronger diagnostic observation.

    Includes persistent node state after every finite input history.
    This is NOT yet declared to be the external network semantics.

    It is used to detect hidden distinctions that may become observable
    under a future continuation.
    """

    signature = []

    for scenario in INPUT_SCENARIOS:
        result = run_core_network(
            network,
            external_events(
                scenario
            ),
        )

        signature.append(
            (
                result.terminal_outputs,
                tuple(
                    (
                        state.node,
                        state.raw,
                        state.last_timestamp,
                    )
                    for state in result.states
                ),
            )
        )

    return tuple(signature)


def topology_name(
    delays,
    b_type,
    c_type,
) -> str:
    edge_parts = []

    for (
        source,
        target,
    ), delay in zip(
        EDGE_SLOTS,
        delays,
    ):
        edge_parts.append(
            f"{source}{target}="
            + (
                "-"
                if delay is None
                else str(delay)
            )
        )

    return (
        f"b={b_type} "
        f"c={c_type} "
        + " ".join(edge_parts)
    )


# ----------------------------------------------------------------------
# Targeted probes
# ----------------------------------------------------------------------

def multiplicity_probe() -> None:
    print()
    print(
        "=" * 88
    )
    print(
        "MULTIPLICITY-SENSITIVE SINK"
    )
    print(
        "=" * 88
    )

    #
    # One path:
    #
    #     a --2--> c(T2)
    #
    single = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(
            make_edge(
                "a",
                "c",
                2,
            ),
        ),
    )

    #
    # Two equal-delay paths:
    #
    #     a --------2------> c(T2)
    #      \--1--> b(R) --1-/
    #
    double = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(
            make_edge(
                "a",
                "b",
                1,
            ),
            make_edge(
                "b",
                "c",
                1,
            ),
            make_edge(
                "a",
                "c",
                2,
            ),
        ),
    )

    scenario = (
        NetworkEvent(
            0,
            "a",
            0,
        ),
    )

    one = run_core_network(
        single,
        scenario,
    )

    two = run_core_network(
        double,
        scenario,
    )

    print(
        "single path terminal outputs:"
    )
    print(
        f"    {one.terminal_outputs}"
    )

    print(
        "two coincident paths terminal outputs:"
    )
    print(
        f"    {two.terminal_outputs}"
    )

    c_one = next(
        state
        for state in one.states
        if state.node == "c"
    )

    c_two = next(
        state
        for state in two.states
        if state.node == "c"
    )

    print(
        "single path c state:"
    )
    print(
        f"    {c_one}"
    )

    print(
        "double path c state:"
    )
    print(
        f"    {c_two}"
    )

    print(
        "multiplicity distinguished="
        f"{one != two}"
    )


def relay_quotient_probe() -> None:
    print()
    print(
        "=" * 88
    )
    print(
        "RELAY AS MULTIPLICITY QUOTIENT"
    )
    print(
        "=" * 88
    )

    #
    # Direct duplicate transport into T2:
    #
    #     a ==two parallel edges==> c(T2)
    #
    direct = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(
            make_edge(
                "a",
                "c",
                1,
            ),
            make_edge(
                "a",
                "c",
                1,
            ),
        ),
    )

    #
    # Same multiplicity first enters relay b.
    #
    # b collapses the batch to one emitted event.
    #
    through_relay = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(
            make_edge(
                "a",
                "b",
                1,
            ),
            make_edge(
                "a",
                "b",
                1,
            ),
            make_edge(
                "b",
                "c",
                1,
            ),
        ),
    )

    scenario = (
        NetworkEvent(
            0,
            "a",
            0,
        ),
    )

    direct_result = run_core_network(
        direct,
        scenario,
    )

    relay_result = run_core_network(
        through_relay,
        scenario,
    )

    print(
        "direct duplicate transport:"
    )
    print(
        f"    outputs="
        f"{direct_result.terminal_outputs}"
    )

    print(
        "through relay:"
    )
    print(
        f"    outputs="
        f"{relay_result.terminal_outputs}"
    )

    print(
        "relay quotient visible="
        f"{direct_result.terminal_outputs != relay_result.terminal_outputs}"
    )


def hidden_state_continuation_probe() -> None:
    print()
    print(
        "=" * 88
    )
    print(
        "HIDDEN STATE / CONTINUATION PROBE"
    )
    print(
        "=" * 88
    )

    connected = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(
            make_edge(
                "a",
                "c",
                1,
            ),
        ),
    )

    disconnected = CoreNetwork(
        nodes=make_nodes(
            "R",
            "T2",
        ),
        edges=(),
    )

    prefix = (
        NetworkEvent(
            0,
            "a",
            0,
        ),
    )

    connected_prefix = run_core_network(
        connected,
        prefix,
    )

    disconnected_prefix = run_core_network(
        disconnected,
        prefix,
    )

    print(
        "after one external event:"
    )

    print(
        "    boundary outputs equal="
        f"{connected_prefix.terminal_outputs == disconnected_prefix.terminal_outputs}"
    )

    print(
        "    full states equal="
        f"{connected_prefix.states == disconnected_prefix.states}"
    )

    #
    # Compare complete executions from the initial state with a longer
    # input history. This is the observable continuation witness.
    #
    continuation = (
        NetworkEvent(
            0,
            "a",
            0,
        ),
        NetworkEvent(
            2,
            "a",
            0,
        ),
    )

    connected_long = run_core_network(
        connected,
        continuation,
    )

    disconnected_long = run_core_network(
        disconnected,
        continuation,
    )

    print()
    print(
        "after a future continuation:"
    )

    print(
        "    connected outputs="
        f"{connected_long.terminal_outputs}"
    )

    print(
        "    disconnected outputs="
        f"{disconnected_long.terminal_outputs}"
    )

    print(
        "    continuation distinguishes="
        f"{connected_long.terminal_outputs != disconnected_long.terminal_outputs}"
    )


def main() -> None:
    print(
        "SPK NETWORK MIXED SEMANTICS v0"
    )

    print(
        "source node a: R"
    )

    print(
        "internal/terminal node types: R,T2"
    )

    print(
        "edge slots: a->b, a->c, b->c"
    )

    print(
        "delay choices: absent,1,2"
    )

    print(
        f"input scenarios: "
        f"{len(INPUT_SCENARIOS)}"
    )

    print()

    output_groups = defaultdict(
        list
    )

    stateful_groups = defaultdict(
        list
    )

    syntactic = 0

    for (
        b_type,
        c_type,
    ) in product(
        NODE_TYPE_CHOICES,
        repeat=2,
    ):
        for delays in product(
            DELAY_CHOICES,
            repeat=len(
                EDGE_SLOTS
            ),
        ):
            syntactic += 1

            network = make_network(
                delays,
                b_type,
                c_type,
            )

            label = topology_name(
                delays,
                b_type,
                c_type,
            )

            output_groups[
                output_signature(
                    network
                )
            ].append(
                label
            )

            stateful_groups[
                stateful_signature(
                    network
                )
            ].append(
                label
            )

    print(
        "=" * 88
    )
    print(
        "FINITE MIXED-NODE CENSUS"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic typed networks: "
        f"{syntactic}"
    )

    print(
        f"boundary-output classes: "
        f"{len(output_groups)}"
    )

    print(
        f"state-aware classes: "
        f"{len(stateful_groups)}"
    )

    print(
        f"boundary collapsed excess: "
        f"{syntactic - len(output_groups)}"
    )

    print(
        f"state-aware collapsed excess: "
        f"{syntactic - len(stateful_groups)}"
    )

    hidden_state_aliases = 0

    for (
        output_signature_key,
        members,
    ) in output_groups.items():
        if len(members) < 2:
            continue

        #
        # Count how many distinct state-aware signatures occur inside
        # one boundary-output equivalence class.
        #
        member_set = set(
            members
        )

        contained_state_classes = 0

        for state_members in (
            stateful_groups.values()
        ):
            if (
                member_set
                & set(state_members)
            ):
                contained_state_classes += 1

        if contained_state_classes > 1:
            hidden_state_aliases += 1

    print(
        f"boundary classes hiding "
        f"multiple state classes: "
        f"{hidden_state_aliases}"
    )

    multiplicity_probe()

    relay_quotient_probe()

    hidden_state_continuation_probe()

    print()
    print(
        "=" * 88
    )
    print(
        "CHECKPOINT"
    )
    print(
        "=" * 88
    )

    print(
        "MIXED NETWORK SEMANTICS v0 COMPLETE"
    )

    print(
        "No mixed-node algebra claimed yet."
    )


if __name__ == "__main__":
    main()
