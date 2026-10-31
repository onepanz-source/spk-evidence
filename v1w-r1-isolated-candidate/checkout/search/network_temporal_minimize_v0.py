from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from itertools import combinations

from search.network_temporal_state_v0 import (
    INPUT_ALPHABET,
    TemporalMachine,
    TemporalState,
    enumerate_networks,
)


def stable_partition(
    machine: TemporalMachine,
):
    """
    Exact minimization of the reachable deterministic Mealy machine.

    Two states remain equivalent iff, for every input symbol:

      - their immediate outputs agree;
      - their successor states remain equivalent.
    """

    states = tuple(
        sorted(
            machine.reachable_states(),
            key=repr,
        )
    )

    blocks = (
        frozenset(states),
    )

    rounds = 0

    while True:
        rounds += 1

        block_of = {
            state: index
            for index, block in enumerate(
                blocks
            )
            for state in block
        }

        groups = defaultdict(
            list
        )

        for state in states:
            signature = []

            for symbol in INPUT_ALPHABET:
                step = machine.step(
                    state,
                    symbol,
                )

                signature.append(
                    (
                        step.output,
                        block_of[
                            step.state
                        ],
                    )
                )

            groups[
                tuple(signature)
            ].append(
                state
            )

        new_blocks = tuple(
            frozenset(members)
            for _, members in sorted(
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
        for index, block in enumerate(
            blocks
        )
        for state in block
    }

    return (
        blocks,
        block_of,
        rounds,
    )


def canonical_minimized_machine(
    machine: TemporalMachine,
):
    """
    Isomorphism-independent canonical representation.

    Semantic states are numbered by BFS from the initial block.
    Input order is fixed as 0,1.
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

        representative = min(
            blocks[
                block_index
            ],
            key=repr,
        )

        transitions = []

        for symbol in INPUT_ALPHABET:
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
        blocks,
        block_of,
        rounds,
    )


def exact_equivalence(
    left: TemporalMachine,
    right: TemporalMachine,
):
    """
    Independent product-state equivalence.

    Returns:
        equivalent,
        shortest distinguishing word or None,
        product states explored
    """

    initial = (
        left.initial,
        right.initial,
    )

    words = {
        initial: ()
    }

    queue = deque(
        (
            initial,
        )
    )

    explored = 0

    while queue:
        (
            left_state,
            right_state,
        ) = queue.popleft()

        prefix = words[
            (
                left_state,
                right_state,
            )
        ]

        explored += 1

        for symbol in INPUT_ALPHABET:
            left_step = left.step(
                left_state,
                symbol,
            )

            right_step = right.step(
                right_state,
                symbol,
            )

            word = (
                prefix
                + (
                    symbol,
                )
            )

            if (
                left_step.output
                != right_step.output
            ):
                return (
                    False,
                    word,
                    explored,
                )

            pair = (
                left_step.state,
                right_step.state,
            )

            if pair in words:
                continue

            words[
                pair
            ] = word

            queue.append(
                pair
            )

    return (
        True,
        None,
        explored,
    )


def block_has_age_quotient(
    block,
):
    if len(block) < 2:
        return False

    age_values = {
        state.ages
        for state in block
    }

    return len(age_values) > 1


def block_has_raw_quotient(
    block,
):
    if len(block) < 2:
        return False

    raw_values = {
        state.raws
        for state in block
    }

    return len(raw_values) > 1


def block_has_pending_quotient(
    block,
):
    if len(block) < 2:
        return False

    pending_values = {
        state.pending
        for state in block
    }

    return len(
        pending_values
    ) > 1


def first_age_quotient_example(
    records,
):
    for (
        label,
        _,
        _,
        _,
        blocks,
        _,
    ) in records:
        for block in blocks:
            if not block_has_age_quotient(
                block
            ):
                continue

            states = sorted(
                block,
                key=repr,
            )

            for left, right in combinations(
                states,
                2,
            ):
                if (
                    left.ages
                    == right.ages
                ):
                    continue

                return (
                    label,
                    left,
                    right,
                    len(block),
                )

    return None


def main() -> None:
    print(
        "SPK NETWORK TEMPORAL "
        "TRANSDUCER MINIMIZATION v0"
    )

    networks = enumerate_networks()

    print(
        f"typed networks: "
        f"{len(networks)}"
    )

    print(
        "input alphabet: {0,1}"
    )

    print(
        "operational state: "
        "(raw, bounded relative age, pending)"
    )

    records = []

    canonical_groups = defaultdict(
        list
    )

    concrete_total = 0
    semantic_total = 0

    reduced_networks = 0

    age_quotient_networks = 0
    raw_quotient_networks = 0
    pending_quotient_networks = 0

    age_quotient_blocks = 0
    raw_quotient_blocks = 0
    pending_quotient_blocks = 0

    refinement_rounds = []

    for label, network in networks:
        machine = TemporalMachine(
            network
        )

        reachable = (
            machine.reachable_states()
        )

        (
            canonical,
            blocks,
            block_of,
            rounds,
        ) = canonical_minimized_machine(
            machine
        )

        concrete = len(
            reachable
        )

        semantic = len(
            blocks
        )

        concrete_total += concrete
        semantic_total += semantic

        refinement_rounds.append(
            rounds
        )

        if semantic < concrete:
            reduced_networks += 1

        network_age_blocks = sum(
            1
            for block in blocks
            if block_has_age_quotient(
                block
            )
        )

        network_raw_blocks = sum(
            1
            for block in blocks
            if block_has_raw_quotient(
                block
            )
        )

        network_pending_blocks = sum(
            1
            for block in blocks
            if block_has_pending_quotient(
                block
            )
        )

        age_quotient_blocks += (
            network_age_blocks
        )

        raw_quotient_blocks += (
            network_raw_blocks
        )

        pending_quotient_blocks += (
            network_pending_blocks
        )

        if network_age_blocks:
            age_quotient_networks += 1

        if network_raw_blocks:
            raw_quotient_networks += 1

        if network_pending_blocks:
            pending_quotient_networks += 1

        records.append(
            (
                label,
                machine,
                concrete,
                semantic,
                blocks,
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
        "TEMPORAL STATE MINIMIZATION"
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

    print(
        f"networks reduced by quotient: "
        f"{reduced_networks}"
    )

    print(
        f"minimum refinement rounds: "
        f"{min(refinement_rounds)}"
    )

    print(
        f"maximum refinement rounds: "
        f"{max(refinement_rounds)}"
    )

    print()
    print(
        "semantic blocks that quotient "
        "physical components:"
    )

    print(
        f"    age blocks: "
        f"{age_quotient_blocks}"
    )

    print(
        f"    raw blocks: "
        f"{raw_quotient_blocks}"
    )

    print(
        f"    pending blocks: "
        f"{pending_quotient_blocks}"
    )

    print()
    print(
        "networks containing at least one "
        "such quotient:"
    )

    print(
        f"    age: "
        f"{age_quotient_networks}"
    )

    print(
        f"    raw: "
        f"{raw_quotient_networks}"
    )

    print(
        f"    pending: "
        f"{pending_quotient_networks}"
    )

    state_pairs = Counter(
        (
            concrete,
            semantic,
        )
        for (
            _,
            _,
            concrete,
            semantic,
            _,
            _,
        ) in records
    )

    print()
    print(
        "concrete -> semantic "
        "state-count distribution:"
    )

    for (
        concrete,
        semantic,
    ), count in sorted(
        state_pairs.items()
    ):
        print(
            f"    "
            f"{concrete:5d} -> "
            f"{semantic:5d}: "
            f"{count:3d} networks"
        )

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
    # Explicit proof that bounded age itself is still overcomplete.
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "AGE QUOTIENT WITNESS"
    )
    print(
        "=" * 88
    )

    example = first_age_quotient_example(
        records
    )

    if example is None:
        print(
            "No semantically equivalent states "
            "with different ages were found."
        )

    else:
        (
            label,
            left,
            right,
            block_size,
        ) = example

        print(
            "Different bounded ages belong to "
            "one exact semantic state."
        )

        print()
        print(
            "network:"
        )

        print(
            f"    {label}"
        )

        print(
            f"semantic block size: "
            f"{block_size}"
        )

        print()
        print(
            "state L:"
        )

        print(
            f"    raw="
            f"{left.raws}"
        )

        print(
            f"    age="
            f"{left.ages}"
        )

        print(
            f"    pending="
            f"{left.pending}"
        )

        print()
        print(
            "state R:"
        )

        print(
            f"    raw="
            f"{right.raws}"
        )

        print(
            f"    age="
            f"{right.ages}"
        )

        print(
            f"    pending="
            f"{right.pending}"
        )

        print()
        print(
            "These states survive exhaustive "
            "partition refinement in one block."
        )

    #
    # --------------------------------------------------------------
    # Canonical temporal network classes.
    # --------------------------------------------------------------
    #
    print()
    print(
        "=" * 88
    )
    print(
        "CANONICAL TEMPORAL TRANSDUCERS"
    )
    print(
        "=" * 88
    )

    print(
        f"canonical network classes: "
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
        f"non-singleton classes: "
        f"{len(non_singletons)}"
    )

    print()
    print(
        "largest classes:"
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
    # Independent pair-product cross-check.
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
    product_states = 0
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
            _,
            left_canonical,
        ) = left

        (
            right_label,
            right_machine,
            _,
            _,
            _,
            right_canonical,
        ) = right

        (
            product_equal,
            witness,
            explored,
        ) = exact_equivalence(
            left_machine,
            right_machine,
        )

        canonical_equal = (
            left_canonical
            == right_canonical
        )

        pair_checks += 1
        product_states += explored

        if (
            pair_checks % 500
            == 0
        ):
            print(
                f"pairs={pair_checks} "
                f"product_states="
                f"{product_states} "
                f"mismatches="
                f"{mismatches}"
            )

        if (
            product_equal
            == canonical_equal
        ):
            continue

        mismatches += 1

        if first_mismatch is None:
            first_mismatch = (
                left_label,
                right_label,
                product_equal,
                canonical_equal,
                witness,
            )

    print()
    print(
        f"network pairs checked: "
        f"{pair_checks}"
    )

    print(
        f"product-state pairs explored: "
        f"{product_states}"
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
    # Final checkpoint.
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

    print(
        "canonical/product mismatches: 0"
    )

    print(
        f"temporal semantic states: "
        f"{semantic_total}"
    )

    print(
        f"temporal network classes: "
        f"{len(canonical_groups)}"
    )

    print(
        "TEMPORAL MINIMAL SEMANTIC "
        "STATE CHECKPOINT: PASS"
    )

    print()
    print(
        "Scope:"
    )

    print(
        "- declared 108 R/D DAG networks"
    )

    print(
        "- binary source interface"
    )

    print(
        "- edge delays in {1,2}"
    )

    print(
        "- bounded relative-age model"
    )

    print(
        "- terminal-output observation"
    )

    print(
        "- exact finite Mealy minimization"
    )


if __name__ == "__main__":
    main()
