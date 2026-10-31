from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from itertools import (
    combinations,
    product,
)

from spk_core.network import (
    NetworkEvent,
    run_core_network,
)

from search.network_exact_transducer_v0 import (
    ExactMachine,
    INPUT_ALPHABET,
    enumerate_networks,
    exact_equivalence,
)


BRIDGE_MAX_HORIZON = 6


def input_words_up_to(
    maximum: int,
):
    yield ()

    for length in range(
        1,
        maximum + 1,
    ):
        yield from product(
            INPUT_ALPHABET,
            repeat=length,
        )


def external_events(
    word,
):
    return tuple(
        NetworkEvent(
            timestamp=timestamp,
            node="a",
            channel=0,
        )
        for timestamp, symbol
        in enumerate(word)
        if symbol
    )


def machine_trace(
    machine: ExactMachine,
    word,
):
    """
    Execute one finite input word and flush all events already in
    flight after the final input symbol.

    Return the same terminal observation shape as run_core_network(),
    but represented as primitive tuples.
    """

    state = machine.initial

    outputs = []

    timestamp = 0

    def record(
        step_output,
        current_timestamp,
    ):
        for (
            node,
            channel,
            multiplicity,
        ) in step_output:
            outputs.extend(
                (
                    current_timestamp,
                    node,
                    channel,
                )
                for _ in range(
                    multiplicity
                )
            )

    for symbol in word:
        step = machine.step(
            state,
            symbol,
        )

        record(
            step.output,
            timestamp,
        )

        state = step.state

        timestamp += 1

    #
    # No more external input, but previously emitted events may still
    # be traversing positive-delay edges.
    #
    while state.pending:
        step = machine.step(
            state,
            0,
        )

        record(
            step.output,
            timestamp,
        )

        state = step.state

        timestamp += 1

    return tuple(
        sorted(
            outputs
        )
    )


def runtime_trace(
    network,
    word,
):
    result = run_core_network(
        network,
        external_events(
            word
        ),
    )

    return tuple(
        (
            event.timestamp,
            event.node,
            event.channel,
        )
        for event
        in result.terminal_outputs
    )


def validate_runtime_bridge(
    networks,
):
    checks = 0

    first_failure = None

    words = tuple(
        input_words_up_to(
            BRIDGE_MAX_HORIZON
        )
    )

    for label, network in networks:
        machine = ExactMachine(
            network
        )

        for word in words:
            expected = runtime_trace(
                network,
                word,
            )

            actual = machine_trace(
                machine,
                word,
            )

            checks += 1

            if expected != actual:
                first_failure = (
                    label,
                    word,
                    expected,
                    actual,
                )

                return (
                    checks,
                    first_failure,
                )

    return (
        checks,
        first_failure,
    )


def stable_partition(
    machine: ExactMachine,
):
    """
    Exact deterministic Mealy-machine minimization by partition
    refinement.

    Two reachable states remain in the same block iff, for every input
    symbol:

      - their immediate outputs agree;
      - their successors belong to the same equivalence block.
    """

    states = tuple(
        sorted(
            machine.reachable_states(),
            key=repr,
        )
    )

    blocks = (
        frozenset(
            states
        ),
    )

    rounds = 0

    while True:
        rounds += 1

        block_of = {
            state: index
            for index, block
            in enumerate(blocks)
            for state in block
        }

        groups = defaultdict(
            list
        )

        for state in states:
            key = []

            for symbol in (
                INPUT_ALPHABET
            ):
                step = machine.step(
                    state,
                    symbol,
                )

                key.append(
                    (
                        step.output,
                        block_of[
                            step.state
                        ],
                    )
                )

            groups[
                tuple(key)
            ].append(
                state
            )

        new_blocks = tuple(
            frozenset(
                members
            )
            for _, members
            in sorted(
                groups.items(),
                key=lambda item: repr(
                    item[0]
                ),
            )
        )

        if (
            frozenset(new_blocks)
            == frozenset(blocks)
        ):
            break

        blocks = new_blocks

    block_of = {
        state: index
        for index, block
        in enumerate(blocks)
        for state in block
    }

    return (
        blocks,
        block_of,
        rounds,
    )


def canonical_minimized_machine(
    machine: ExactMachine,
):
    """
    Produce an isomorphism-independent canonical encoding of the
    minimized Mealy machine.

    Canonical state numbers are assigned by BFS from the initial
    semantic state, following input symbols in fixed order 0,1.
    """

    (
        blocks,
        block_of,
        rounds,
    ) = stable_partition(
        machine
    )

    initial_block = block_of[
        machine.initial
    ]

    canonical_id = {
        initial_block: 0
    }

    queue = deque(
        (
            initial_block,
        )
    )

    rows = {}

    while queue:
        block_index = queue.popleft()

        block = blocks[
            block_index
        ]

        representative = min(
            block,
            key=repr,
        )

        transitions = []

        for symbol in (
            INPUT_ALPHABET
        ):
            step = machine.step(
                representative,
                symbol,
            )

            target_block = block_of[
                step.state
            ]

            if (
                target_block
                not in canonical_id
            ):
                canonical_id[
                    target_block
                ] = len(
                    canonical_id
                )

                queue.append(
                    target_block
                )

            transitions.append(
                (
                    step.output,
                    canonical_id[
                        target_block
                    ],
                )
            )

        rows[
            canonical_id[
                block_index
            ]
        ] = tuple(
            transitions
        )

    canonical = tuple(
        rows[index]
        for index in range(
            len(rows)
        )
    )

    return (
        canonical,
        len(blocks),
        rounds,
    )


def main() -> None:
    print(
        "SPK NETWORK TRANSDUCER "
        "MINIMIZATION v0"
    )

    networks = enumerate_networks()

    print(
        f"typed networks: "
        f"{len(networks)}"
    )

    print(
        "input alphabet: {0,1}"
    )

    print()

    #
    # --------------------------------------------------------------
    # Runtime bridge
    # --------------------------------------------------------------
    #
    print(
        "=" * 88
    )
    print(
        "EXACT-MACHINE / RUNTIME BRIDGE"
    )
    print(
        "=" * 88
    )

    (
        bridge_checks,
        bridge_failure,
    ) = validate_runtime_bridge(
        networks
    )

    print(
        f"maximum bridge horizon: "
        f"{BRIDGE_MAX_HORIZON}"
    )

    print(
        f"runtime comparisons: "
        f"{bridge_checks}"
    )

    if bridge_failure is not None:
        (
            label,
            word,
            expected,
            actual,
        ) = bridge_failure

        print()
        print(
            "BRIDGE FAILURE"
        )

        print(
            f"network: {label}"
        )

        print(
            f"word: {word}"
        )

        print(
            f"runtime: {expected}"
        )

        print(
            f"machine: {actual}"
        )

        raise SystemExit(1)

    print(
        "runtime mismatches: 0"
    )

    #
    # --------------------------------------------------------------
    # Build and minimize all machines
    # --------------------------------------------------------------
    #
    records = []

    canonical_groups = defaultdict(
        list
    )

    concrete_total = 0
    semantic_total = 0

    refinement_rounds = []

    for label, network in networks:
        machine = ExactMachine(
            network
        )

        concrete_states = len(
            machine.reachable_states()
        )

        (
            canonical,
            semantic_states,
            rounds,
        ) = canonical_minimized_machine(
            machine
        )

        concrete_total += (
            concrete_states
        )

        semantic_total += (
            semantic_states
        )

        refinement_rounds.append(
            rounds
        )

        records.append(
            (
                label,
                machine,
                concrete_states,
                semantic_states,
                canonical,
            )
        )

        canonical_groups[
            canonical
        ].append(
            label
        )

    print()
    print(
        "=" * 88
    )
    print(
        "STATE MINIMIZATION"
    )
    print(
        "=" * 88
    )

    print(
        f"concrete reachable states: "
        f"{concrete_total}"
    )

    print(
        f"minimal semantic states: "
        f"{semantic_total}"
    )

    print(
        f"states quotiented away: "
        f"{concrete_total - semantic_total}"
    )

    reduced_networks = [
        record
        for record in records
        if (
            record[3]
            < record[2]
        )
    ]

    print(
        f"networks reduced by "
        f"state quotient: "
        f"{len(reduced_networks)}"
    )

    print(
        f"minimum refinement rounds: "
        f"{min(refinement_rounds)}"
    )

    print(
        f"maximum refinement rounds: "
        f"{max(refinement_rounds)}"
    )

    concrete_distribution = Counter(
        record[2]
        for record in records
    )

    semantic_distribution = Counter(
        record[3]
        for record in records
    )

    print()
    print(
        "concrete -> semantic "
        "state-count distribution:"
    )

    pairs = Counter(
        (
            record[2],
            record[3],
        )
        for record in records
    )

    for (
        concrete,
        semantic,
    ), count in sorted(
        pairs.items()
    ):
        print(
            f"    "
            f"{concrete:3d} -> "
            f"{semantic:3d}: "
            f"{count:3d} networks"
        )

    #
    # Largest per-network quotient.
    #
    greatest = max(
        records,
        key=lambda record: (
            record[2]
            - record[3],
            record[2],
        ),
    )

    print()
    print(
        "largest state quotient:"
    )

    print(
        f"    network: "
        f"{greatest[0]}"
    )

    print(
        f"    concrete: "
        f"{greatest[2]}"
    )

    print(
        f"    semantic: "
        f"{greatest[3]}"
    )

    print(
        f"    removed: "
        f"{greatest[2] - greatest[3]}"
    )

    #
    # --------------------------------------------------------------
    # Canonical network behavior classes
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "CANONICAL MINIMAL TRANSDUCERS"
    )
    print(
        "=" * 88
    )

    print(
        f"canonical transducer classes: "
        f"{len(canonical_groups)}"
    )

    print(
        f"collapsed network excess: "
        f"{len(networks) - len(canonical_groups)}"
    )

    non_singletons = [
        members
        for members
        in canonical_groups.values()
        if len(members) > 1
    ]

    print(
        f"non-singleton canonical classes: "
        f"{len(non_singletons)}"
    )

    print()
    print(
        "largest canonical classes:"
    )

    for index, members in enumerate(
        sorted(
            canonical_groups.values(),
            key=lambda group: (
                -len(group),
                group[0],
            ),
        )[:10],
        start=1,
    ):
        print(
            f"class {index}: "
            f"size={len(members)}"
        )

        for label in members[:6]:
            print(
                f"    {label}"
            )

        if len(members) > 6:
            print(
                f"    ... "
                f"{len(members) - 6} more"
            )

    #
    # --------------------------------------------------------------
    # Independent cross-check against product equivalence
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "CANONICAL / PRODUCT "
        "EQUIVALENCE CROSS-CHECK"
    )
    print(
        "=" * 88
    )

    pair_checks = 0
    mismatches = 0
    first_mismatch = None

    for left, right in combinations(
        records,
        2,
    ):
        (
            left_label,
            left_machine,
            _,
            _,
            left_canonical,
        ) = left

        (
            right_label,
            right_machine,
            _,
            _,
            right_canonical,
        ) = right

        product_equal = (
            exact_equivalence(
                left_machine,
                right_machine,
            ).equivalent
        )

        canonical_equal = (
            left_canonical
            == right_canonical
        )

        pair_checks += 1

        if (
            product_equal
            != canonical_equal
        ):
            mismatches += 1

            if first_mismatch is None:
                first_mismatch = (
                    left_label,
                    right_label,
                    product_equal,
                    canonical_equal,
                )

    print(
        f"network pairs checked: "
        f"{pair_checks}"
    )

    print(
        f"equivalence mismatches: "
        f"{mismatches}"
    )

    if first_mismatch is not None:
        print(
            f"first mismatch: "
            f"{first_mismatch}"
        )

        raise SystemExit(1)

    #
    # --------------------------------------------------------------
    # Final checkpoint
    # --------------------------------------------------------------
    #
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

    if len(canonical_groups) != 52:
        raise AssertionError(
            "minimal transducer class count "
            "differs from exact product partition"
        )

    print(
        "runtime bridge mismatches: 0"
    )

    print(
        "canonical/product mismatches: 0"
    )

    print(
        "canonical transducer classes: 52"
    )

    print(
        "exact product classes: 52"
    )

    print(
        "MINIMAL SEMANTIC STATE "
        "CHECKPOINT: PASS"
    )

    print()
    print(
        "Scope:"
    )

    print(
        "- declared 108 R/T2 DAG networks"
    )

    print(
        "- binary source interface"
    )

    print(
        "- edge delays in {1,2}"
    )

    print(
        "- no ShiftDecay"
    )

    print(
        "- terminal-output observation"
    )

    print(
        "- deterministic finite "
        "Mealy semantics"
    )


if __name__ == "__main__":
    main()
