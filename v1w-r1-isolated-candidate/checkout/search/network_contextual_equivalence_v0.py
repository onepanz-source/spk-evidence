from __future__ import annotations

from collections import defaultdict
from itertools import (
    combinations,
    combinations_with_replacement,
    product,
)

from spk_core.network import (
    run_core_network,
)

from search.network_mixed_semantics_v0 import (
    DELAY_CHOICES,
    EDGE_SLOTS,
    INPUT_SCENARIOS,
    NODE_TYPE_CHOICES,
    external_events,
    make_network,
    topology_name,
)


def enumerate_networks():
    result = []

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

            result.append(
                (
                    label,
                    network,
                )
            )

    return tuple(result)


def boundary_signature(
    network,
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


def raw_state_signature(
    network,
):
    """
    Persistent computational state only.

    last_timestamp is deliberately excluded because the current
    R/T2 programs contain no ShiftDecay and therefore cannot observe
    elapsed time.
    """

    result = []

    for scenario in INPUT_SCENARIOS:
        execution = run_core_network(
            network,
            external_events(
                scenario
            ),
        )

        result.append(
            (
                execution.terminal_outputs,
                tuple(
                    (
                        state.node,
                        state.raw,
                    )
                    for state in execution.states
                ),
            )
        )

    return tuple(result)


def operational_state_signature(
    network,
):
    """
    Full runtime state, including last_timestamp.

    This is stronger than contextual state for the current R/T2
    fragment because R and T2 contain no temporal instruction.
    """

    result = []

    for scenario in INPUT_SCENARIOS:
        execution = run_core_network(
            network,
            external_events(
                scenario
            ),
        )

        result.append(
            (
                execution.terminal_outputs,
                tuple(
                    (
                        state.node,
                        state.raw,
                        state.last_timestamp,
                    )
                    for state in execution.states
                ),
            )
        )

    return tuple(result)


def raw_state(
    execution,
):
    return tuple(
        (
            state.node,
            state.raw,
        )
        for state in execution.states
    )


def operational_state(
    execution,
):
    return tuple(
        (
            state.node,
            state.raw,
            state.last_timestamp,
        )
        for state in execution.states
    )


def quiescent_timestamp(
    execution,
) -> int:
    if not execution.states:
        return 0

    return max(
        state.last_timestamp
        for state in execution.states
    )


def future_suffixes(
    start_timestamp: int,
):
    """
    Small exhaustive continuation corpus.

    All continuation events occur strictly after both networks have
    completed every event caused by the prefix.
    """

    times = tuple(
        range(
            start_timestamp,
            start_timestamp + 6,
        )
    )

    for length in range(
        1,
        5,
    ):
        yield from (
            tuple(items)
            for items
            in combinations_with_replacement(
                times,
                length,
            )
        )


def find_contextual_witness(
    boundary_groups,
):
    """
    Search for:

        same observed prefix
        different persistent raw state
        future continuation distinguishes outputs

    This is a concrete witness that finite-prefix boundary equality is
    not a congruence under continuation.
    """

    examined_pairs = 0
    latent_raw_pairs = 0
    continuations_checked = 0

    for members in (
        boundary_groups.values()
    ):
        if len(members) < 2:
            continue

        for (
            left_label,
            left,
        ), (
            right_label,
            right,
        ) in combinations(
            members,
            2,
        ):
            examined_pairs += 1

            for prefix in INPUT_SCENARIOS:
                left_prefix = run_core_network(
                    left,
                    external_events(
                        prefix
                    ),
                )

                right_prefix = run_core_network(
                    right,
                    external_events(
                        prefix
                    ),
                )

                if (
                    left_prefix.terminal_outputs
                    != right_prefix.terminal_outputs
                ):
                    #
                    # Should not happen inside one boundary group,
                    # but keep the condition explicit.
                    #
                    continue

                left_raw = raw_state(
                    left_prefix
                )

                right_raw = raw_state(
                    right_prefix
                )

                if left_raw == right_raw:
                    continue

                latent_raw_pairs += 1

                barrier = max(
                    quiescent_timestamp(
                        left_prefix
                    ),
                    quiescent_timestamp(
                        right_prefix
                    ),
                )

                for suffix in future_suffixes(
                    barrier + 1
                ):
                    continuations_checked += 1

                    full_history = tuple(
                        sorted(
                            prefix
                            + suffix
                        )
                    )

                    left_full = run_core_network(
                        left,
                        external_events(
                            full_history
                        ),
                    )

                    right_full = run_core_network(
                        right,
                        external_events(
                            full_history
                        ),
                    )

                    if (
                        left_full.terminal_outputs
                        != right_full.terminal_outputs
                    ):
                        return {
                            "left_label": (
                                left_label
                            ),
                            "right_label": (
                                right_label
                            ),
                            "prefix": prefix,
                            "prefix_outputs": (
                                left_prefix.terminal_outputs
                            ),
                            "left_raw": (
                                left_raw
                            ),
                            "right_raw": (
                                right_raw
                            ),
                            "left_operational": (
                                operational_state(
                                    left_prefix
                                )
                            ),
                            "right_operational": (
                                operational_state(
                                    right_prefix
                                )
                            ),
                            "barrier": barrier,
                            "suffix": suffix,
                            "full_history": (
                                full_history
                            ),
                            "left_future_outputs": (
                                left_full.terminal_outputs
                            ),
                            "right_future_outputs": (
                                right_full.terminal_outputs
                            ),
                            "examined_pairs": (
                                examined_pairs
                            ),
                            "latent_raw_pairs": (
                                latent_raw_pairs
                            ),
                            "continuations_checked": (
                                continuations_checked
                            ),
                        }

    return {
        "witness": None,
        "examined_pairs": examined_pairs,
        "latent_raw_pairs": latent_raw_pairs,
        "continuations_checked": (
            continuations_checked
        ),
    }


def count_hidden_classes(
    coarse_groups,
    fine_signature,
):
    count = 0

    for members in coarse_groups.values():
        signatures = {
            fine_signature(
                network
            )
            for _, network in members
        }

        if len(signatures) > 1:
            count += 1

    return count


def main() -> None:
    print(
        "SPK NETWORK CONTEXTUAL "
        "EQUIVALENCE v0"
    )

    networks = enumerate_networks()

    boundary_groups = defaultdict(
        list
    )

    raw_groups = defaultdict(
        list
    )

    operational_groups = defaultdict(
        list
    )

    for label, network in networks:
        boundary_groups[
            boundary_signature(
                network
            )
        ].append(
            (
                label,
                network,
            )
        )

        raw_groups[
            raw_state_signature(
                network
            )
        ].append(
            (
                label,
                network,
            )
        )

        operational_groups[
            operational_state_signature(
                network
            )
        ].append(
            (
                label,
                network,
            )
        )

    print()
    print(
        "=" * 88
    )
    print(
        "OBSERVATION HIERARCHY"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic typed networks: "
        f"{len(networks)}"
    )

    print(
        f"boundary-output classes: "
        f"{len(boundary_groups)}"
    )

    print(
        f"raw-state classes: "
        f"{len(raw_groups)}"
    )

    print(
        f"operational-state classes: "
        f"{len(operational_groups)}"
    )

    raw_hidden = count_hidden_classes(
        boundary_groups,
        raw_state_signature,
    )

    operational_hidden = (
        count_hidden_classes(
            boundary_groups,
            operational_state_signature,
        )
    )

    timestamp_only = (
        operational_hidden
        - raw_hidden
    )

    print()
    print(
        f"boundary classes hiding "
        f"multiple raw-state classes: "
        f"{raw_hidden}"
    )

    print(
        f"boundary classes hiding "
        f"multiple operational-state classes: "
        f"{operational_hidden}"
    )

    print(
        f"extra distinctions attributable "
        f"to operational timing metadata: "
        f"{timestamp_only}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "CONTEXTUAL CONTINUATION SEARCH"
    )
    print(
        "=" * 88
    )

    witness = find_contextual_witness(
        boundary_groups
    )

    if witness.get(
        "witness"
    ) is None and (
        "left_label"
        not in witness
    ):
        print(
            "No continuation witness found "
            "inside the searched finite horizon."
        )

        print(
            f"network pairs examined: "
            f"{witness['examined_pairs']}"
        )

        print(
            f"latent raw-state prefixes: "
            f"{witness['latent_raw_pairs']}"
        )

        print(
            f"continuations checked: "
            f"{witness['continuations_checked']}"
        )

        raise SystemExit(2)

    print(
        "CONTEXTUAL WITNESS FOUND"
    )

    print()
    print(
        "network L:"
    )
    print(
        f"    {witness['left_label']}"
    )

    print(
        "network R:"
    )
    print(
        f"    {witness['right_label']}"
    )

    print()
    print(
        f"prefix input: "
        f"{witness['prefix']}"
    )

    print(
        f"equal prefix outputs: "
        f"{witness['prefix_outputs']}"
    )

    print()
    print(
        "hidden raw states:"
    )

    print(
        f"    L = "
        f"{witness['left_raw']}"
    )

    print(
        f"    R = "
        f"{witness['right_raw']}"
    )

    print()
    print(
        "full operational states:"
    )

    print(
        f"    L = "
        f"{witness['left_operational']}"
    )

    print(
        f"    R = "
        f"{witness['right_operational']}"
    )

    print()
    print(
        f"quiescent barrier: "
        f"{witness['barrier']}"
    )

    print(
        f"continuation input: "
        f"{witness['suffix']}"
    )

    print(
        f"full input history: "
        f"{witness['full_history']}"
    )

    print()
    print(
        "future observations:"
    )

    print(
        f"    L = "
        f"{witness['left_future_outputs']}"
    )

    print(
        f"    R = "
        f"{witness['right_future_outputs']}"
    )

    print()
    print(
        "continuation distinguishes: "
        f"{witness['left_future_outputs'] != witness['right_future_outputs']}"
    )

    print()
    print(
        f"network pairs examined: "
        f"{witness['examined_pairs']}"
    )

    print(
        f"latent raw-state prefixes seen: "
        f"{witness['latent_raw_pairs']}"
    )

    print(
        f"continuations checked: "
        f"{witness['continuations_checked']}"
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
        "FINITE-PREFIX BOUNDARY "
        "EQUIVALENCE IS NOT CONTEXTUAL"
    )


if __name__ == "__main__":
    main()
