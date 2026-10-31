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


def relay_program() -> CoreProgram:
    return CoreProgram(
        (
            CoreAcc(1, 0),
            CoreCmp(1),
            CoreEmit(7),
            CoreReset(0),
        )
    )


def nodes(
    *,
    c_program: CoreProgram | None = None,
) -> tuple[NetworkNode, ...]:
    relay = relay_program()

    return (
        NetworkNode(
            "a",
            CONFIG,
            relay,
        ),
        NetworkNode(
            "b",
            CONFIG,
            relay,
        ),
        NetworkNode(
            "c",
            CONFIG,
            c_program
            if c_program is not None
            else relay,
        ),
    )


EDGE_SLOTS = (
    (
        "a",
        "b",
    ),
    (
        "a",
        "c",
    ),
    (
        "b",
        "c",
    ),
)


DELAY_CHOICES = (
    None,
    1,
    2,
)


#
# External interface corpus:
#
#     input node    = a
#     input channel = 0
#
# Multiplicity and temporal separation are both exercised.
#
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
    (0, 0, 2, 2),
)


def external_events(
    timestamps: tuple[int, ...],
) -> tuple[NetworkEvent, ...]:
    return tuple(
        NetworkEvent(
            timestamp,
            "a",
            0,
        )
        for timestamp in timestamps
    )


def edge(
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


def topology_network(
    delays: tuple[
        int | None,
        int | None,
        int | None,
    ],
) -> CoreNetwork:
    edges = []

    for (
        (
            source,
            target,
        ),
        delay,
    ) in zip(
        EDGE_SLOTS,
        delays,
    ):
        if delay is None:
            continue

        edges.append(
            edge(
                source,
                target,
                delay,
            )
        )

    return CoreNetwork(
        nodes=nodes(),
        edges=tuple(edges),
    )


def topology_name(
    delays: tuple[
        int | None,
        int | None,
        int | None,
    ],
) -> str:
    parts = []

    for (
        (
            source,
            target,
        ),
        delay,
    ) in zip(
        EDGE_SLOTS,
        delays,
    ):
        if delay is None:
            parts.append(
                f"{source}{target}=-"
            )
        else:
            parts.append(
                f"{source}{target}={delay}"
            )

    return " ".join(parts)


def terminal_signature(
    network: CoreNetwork,
) -> tuple:
    signature = []

    for timestamps in INPUT_SCENARIOS:
        result = run_core_network(
            network,
            external_events(
                timestamps
            ),
        )

        signature.append(
            tuple(
                (
                    event.timestamp,
                    event.node,
                    event.channel,
                )
                for event
                in result.terminal_outputs
            )
        )

    return tuple(signature)


def final_state_signature(
    network: CoreNetwork,
    timestamps: tuple[int, ...],
) -> tuple:
    result = run_core_network(
        network,
        external_events(
            timestamps
        ),
    )

    return tuple(
        (
            state.node,
            state.raw,
            state.last_timestamp,
        )
        for state in result.states
    )


def make_network(
    edges: tuple[NetworkEdge, ...],
    *,
    c_program: CoreProgram | None = None,
) -> CoreNetwork:
    return CoreNetwork(
        nodes=nodes(
            c_program=c_program
        ),
        edges=edges,
    )


def check_serial_delay_composition() -> None:
    print()
    print(
        "=" * 88
    )
    print(
        "SERIAL RELAY DELAY COMPOSITION"
    )
    print(
        "=" * 88
    )

    all_pass = True

    for d1, d2 in product(
        (
            1,
            2,
        ),
        repeat=2,
    ):
        serial = make_network(
            (
                edge(
                    "a",
                    "b",
                    d1,
                ),
                edge(
                    "b",
                    "c",
                    d2,
                ),
            )
        )

        direct = make_network(
            (
                edge(
                    "a",
                    "c",
                    d1 + d2,
                ),
            )
        )

        equal = (
            terminal_signature(serial)
            == terminal_signature(direct)
        )

        all_pass &= equal

        print(
            f"d1={d1} "
            f"d2={d2} "
            f"direct={d1 + d2} "
            f"equivalent={equal}"
        )

    print()

    print(
        "SERIAL DELAY CANDIDATE: "
        + (
            "SUPPORTED"
            if all_pass
            else "REFUTED"
        )
    )


def check_parallel_edge_behavior() -> None:
    print()
    print(
        "=" * 88
    )
    print(
        "PARALLEL EDGE PROBE"
    )
    print(
        "=" * 88
    )

    single = make_network(
        (
            edge(
                "a",
                "c",
                1,
            ),
        )
    )

    double = make_network(
        (
            edge(
                "a",
                "c",
                1,
            ),
            edge(
                "a",
                "c",
                1,
            ),
        )
    )

    relay_equal = (
        terminal_signature(single)
        == terminal_signature(double)
    )

    print(
        "relay sink, one edge vs two identical edges:"
    )

    print(
        f"terminal-equivalent={relay_equal}"
    )

    #
    # Counterexample to any temptation to promote this to a universal
    # network law.
    #
    # A stateful counting sink distinguishes multiplicity.
    #
    counting_sink = CoreProgram(
        (
            CoreAcc(
                1,
                0,
            ),
        )
    )

    single_count = make_network(
        (
            edge(
                "a",
                "c",
                1,
            ),
        ),
        c_program=counting_sink,
    )

    double_count = make_network(
        (
            edge(
                "a",
                "c",
                1,
            ),
            edge(
                "a",
                "c",
                1,
            ),
        ),
        c_program=counting_sink,
    )

    state_single = final_state_signature(
        single_count,
        (0,),
    )

    state_double = final_state_signature(
        double_count,
        (0,),
    )

    print()
    print(
        "counting sink counterexample:"
    )

    print(
        f"single={state_single}"
    )

    print(
        f"double={state_double}"
    )

    print(
        "state-equivalent="
        f"{state_single == state_double}"
    )


def main() -> None:
    print(
        "SPK NETWORK SYNTHESIS v0"
    )

    print(
        "nodes: a,b,c"
    )

    print(
        "node program: "
        "ACC1(0);CMP1;EMIT7;RESET0"
    )

    print(
        "edge slots: "
        "a->b, a->c, b->c"
    )

    print(
        "edge delay choices: absent,1,2"
    )

    print(
        "external input interface: a:0"
    )

    print(
        "observable boundary: terminal outputs"
    )

    print(
        f"input scenarios: "
        f"{len(INPUT_SCENARIOS)}"
    )

    groups = defaultdict(
        list
    )

    syntactic = 0

    for delays in product(
        DELAY_CHOICES,
        repeat=len(
            EDGE_SLOTS
        ),
    ):
        syntactic += 1

        network = topology_network(
            delays
        )

        signature = terminal_signature(
            network
        )

        groups[
            signature
        ].append(
            delays
        )

    behavioral = len(
        groups
    )

    print()
    print(
        "=" * 88
    )
    print(
        "FINITE TOPOLOGY CENSUS"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic networks: "
        f"{syntactic}"
    )

    print(
        f"behavioral classes: "
        f"{behavioral}"
    )

    print(
        f"collapsed excess: "
        f"{syntactic - behavioral}"
    )

    equivalent_groups = [
        members
        for members in groups.values()
        if len(members) > 1
    ]

    print(
        f"non-singleton classes: "
        f"{len(equivalent_groups)}"
    )

    print()

    for index, members in enumerate(
        sorted(
            equivalent_groups,
            key=lambda group: (
                -len(group),
                tuple(
                    topology_name(item)
                    for item in group
                ),
            ),
        ),
        start=1,
    ):
        print(
            f"class {index}: "
            f"size={len(members)}"
        )

        for delays in members:
            print(
                "    "
                + topology_name(
                    delays
                )
            )

    check_serial_delay_composition()

    check_parallel_edge_behavior()

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
        "NETWORK SYNTHESIS v0 COMPLETE"
    )

    print(
        "No algebraic completeness claim."
    )


if __name__ == "__main__":
    main()
