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


NODE_NAMES = (
    "a",
    "b",
    "c",
    "d",
)


EDGE_SLOTS = (
    ("a", "b"),
    ("a", "c"),
    ("a", "d"),
    ("b", "c"),
    ("b", "d"),
    ("c", "d"),
)


DELAY_CHOICES = (
    None,
    1,
    2,
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
    (0, 0, 2, 2),
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


def make_nodes() -> tuple[NetworkNode, ...]:
    program = relay_program()

    return tuple(
        NetworkNode(
            name,
            CONFIG,
            program,
        )
        for name in NODE_NAMES
    )


def make_network(
    delays: tuple[
        int | None,
        ...,
    ],
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
            NetworkEdge(
                source=source,
                source_channel=7,
                target=target,
                target_channel=0,
                delay=delay,
            )
        )

    return CoreNetwork(
        nodes=make_nodes(),
        edges=tuple(edges),
    )


def external_events(
    timestamps: tuple[int, ...],
) -> tuple[NetworkEvent, ...]:
    return tuple(
        NetworkEvent(
            timestamp=timestamp,
            node="a",
            channel=0,
        )
        for timestamp in timestamps
    )


def outgoing_map(
    network: CoreNetwork,
):
    outgoing = defaultdict(
        list
    )

    for edge in network.edges:
        outgoing[
            edge.source
        ].append(
            edge
        )

    return outgoing


def delay_set_normal_form(
    network: CoreNetwork,
) -> tuple[
    tuple[
        str,
        tuple[int, ...],
    ],
    ...,
]:
    """
    Relay-fragment candidate normal form.

    Start with one event at a at relative time 0.

    Each relay:
      - emits at most one event for each timestamp;
      - therefore arrival multiplicity collapses to a set;
      - outgoing edges translate timestamps by their delays.

    The normal form records, for each reachable terminal node,
    the finite set of relative output delays.
    """

    outgoing = outgoing_map(
        network
    )

    arrivals = {
        name: set()
        for name in NODE_NAMES
    }

    arrivals["a"].add(0)

    terminals = defaultdict(
        set
    )

    for node_name in NODE_NAMES:
        node_arrivals = arrivals[
            node_name
        ]

        if not node_arrivals:
            continue

        routes = outgoing.get(
            node_name,
            (),
        )

        if not routes:
            terminals[
                node_name
            ].update(
                node_arrivals
            )
            continue

        for edge in routes:
            target_arrivals = arrivals[
                edge.target
            ]

            for timestamp in node_arrivals:
                target_arrivals.add(
                    timestamp
                    + edge.delay
                )

    return tuple(
        (
            node,
            tuple(
                sorted(
                    delays
                )
            ),
        )
        for node, delays in sorted(
            terminals.items()
        )
    )


def predict_outputs(
    normal_form,
    timestamps: tuple[int, ...],
) -> tuple[NetworkEvent, ...]:
    #
    # The input relay at a also collapses repeated events having
    # identical timestamps.
    #
    input_times = set(
        timestamps
    )

    outputs = set()

    for (
        node,
        delays,
    ) in normal_form:
        for input_timestamp in input_times:
            for delay in delays:
                outputs.add(
                    NetworkEvent(
                        timestamp=(
                            input_timestamp
                            + delay
                        ),
                        node=node,
                        channel=7,
                    )
                )

    return tuple(
        sorted(
            outputs
        )
    )


def runtime_signature(
    network: CoreNetwork,
):
    return tuple(
        run_core_network(
            network,
            external_events(
                scenario
            ),
        ).terminal_outputs
        for scenario in INPUT_SCENARIOS
    )


def predicted_signature(
    normal_form,
):
    return tuple(
        predict_outputs(
            normal_form,
            scenario,
        )
        for scenario in INPUT_SCENARIOS
    )


def topology_name(
    delays,
) -> str:
    parts = []

    for (
        source,
        target,
    ), delay in zip(
        EDGE_SLOTS,
        delays,
    ):
        parts.append(
            f"{source}{target}="
            + (
                "-"
                if delay is None
                else str(delay)
            )
        )

    return " ".join(
        parts
    )


def main() -> None:
    print(
        "SPK NETWORK RELAY ALGEBRA v0"
    )

    print(
        "nodes: a,b,c,d"
    )

    print(
        "DAG edge slots: 6"
    )

    print(
        "delay choices: absent,1,2"
    )

    print(
        "candidate normal form: "
        "terminal -> finite set of path delays"
    )

    print(
        "parallel operator: set union"
    )

    print(
        "serial operator: Minkowski addition"
    )

    print()

    syntactic = 0
    runtime_mismatches = 0

    nf_to_topologies = defaultdict(
        list
    )

    behavior_to_nf = defaultdict(
        set
    )

    first_failure = None

    for delays in product(
        DELAY_CHOICES,
        repeat=len(
            EDGE_SLOTS
        ),
    ):
        syntactic += 1

        network = make_network(
            delays
        )

        normal_form = (
            delay_set_normal_form(
                network
            )
        )

        predicted = (
            predicted_signature(
                normal_form
            )
        )

        actual = runtime_signature(
            network
        )

        if predicted != actual:
            runtime_mismatches += 1

            if first_failure is None:
                first_failure = (
                    delays,
                    normal_form,
                    predicted,
                    actual,
                )

        nf_to_topologies[
            normal_form
        ].append(
            delays
        )

        behavior_to_nf[
            actual
        ].add(
            normal_form
        )

    normal_forms = len(
        nf_to_topologies
    )

    behavioral_classes = len(
        behavior_to_nf
    )

    ambiguous_behavior_classes = sum(
        1
        for normal_form_set
        in behavior_to_nf.values()
        if len(normal_form_set) > 1
    )

    print(
        "=" * 88
    )
    print(
        "FINITE DAG CENSUS"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic networks: "
        f"{syntactic}"
    )

    print(
        f"delay-set normal forms: "
        f"{normal_forms}"
    )

    print(
        f"runtime behavioral classes: "
        f"{behavioral_classes}"
    )

    print(
        f"runtime/predictor mismatches: "
        f"{runtime_mismatches}"
    )

    print(
        f"behavior classes containing "
        f"multiple normal forms: "
        f"{ambiguous_behavior_classes}"
    )

    print(
        f"collapsed excess: "
        f"{syntactic - normal_forms}"
    )

    if first_failure is not None:
        (
            delays,
            normal_form,
            predicted,
            actual,
        ) = first_failure

        print()
        print(
            "FIRST COUNTEREXAMPLE"
        )

        print(
            topology_name(
                delays
            )
        )

        print(
            f"normal_form={normal_form}"
        )

        print(
            f"predicted={predicted}"
        )

        print(
            f"actual={actual}"
        )

        raise SystemExit(1)

    if (
        normal_forms
        != behavioral_classes
    ):
        raise AssertionError(
            "normal-form count does not match "
            "runtime behavioral-class count"
        )

    if ambiguous_behavior_classes:
        raise AssertionError(
            "distinct delay-set normal forms "
            "collapsed behaviorally"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "LARGEST EQUIVALENCE CLASSES"
    )
    print(
        "=" * 88
    )

    groups = sorted(
        nf_to_topologies.items(),
        key=lambda item: (
            -len(
                item[1]
            ),
            repr(
                item[0]
            ),
        ),
    )

    for index, (
        normal_form,
        members,
    ) in enumerate(
        groups[:10],
        start=1,
    ):
        print(
            f"class {index}: "
            f"size={len(members)} "
            f"NF={normal_form}"
        )

        for delays in members[:8]:
            print(
                "    "
                + topology_name(
                    delays
                )
            )

        if len(members) > 8:
            print(
                f"    ... "
                f"{len(members) - 8} more"
            )

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
        "runtime/predictor mismatches: 0"
    )

    print(
        "normal-form ambiguities: 0"
    )

    print(
        "RELAY DELAY-SET ALGEBRA "
        "FINITE CHECKPOINT: PASS"
    )

    print()

    print(
        "Scope:"
    )

    print(
        "- four-node feed-forward DAGs"
    )

    print(
        "- homogeneous relay nodes"
    )

    print(
        "- edge delays in {1,2}"
    )

    print(
        "- external input only at a:0"
    )

    print(
        "- terminal output observation"
    )

    print(
        "- no universal algebraic "
        "completeness claim"
    )


if __name__ == "__main__":
    main()
