from __future__ import annotations

from collections import defaultdict
from itertools import product

from spk_core.network import (
    NetworkEvent,
    run_core_network,
)

from search.network_mixed_semantics_v0 import (
    DELAY_CHOICES,
    EDGE_SLOTS,
    NODE_TYPE_CHOICES,
    make_network,
    topology_name,
)


MAX_HORIZON = 12


def enumerate_networks():
    networks = []

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

            networks.append(
                (
                    topology_name(
                        delays,
                        b_type,
                        c_type,
                    ),
                    network,
                )
            )

    return tuple(networks)


def input_words(
    horizon: int,
):
    """
    Complete binary input language of fixed horizon.

    Bit i = 1:
        one non-empty external batch at timestamp i.

    Because source node a is R, multiplicity inside an external batch
    is quotiented immediately, so binary temporal support is complete
    for this interface.
    """

    yield from product(
        (
            0,
            1,
        ),
        repeat=horizon,
    )


def events_for_word(
    word,
):
    return tuple(
        NetworkEvent(
            timestamp=timestamp,
            node="a",
            channel=0,
        )
        for timestamp, bit in enumerate(
            word
        )
        if bit
    )


def observe(
    network,
    word,
):
    result = run_core_network(
        network,
        events_for_word(
            word
        ),
    )

    return result.terminal_outputs


def full_signature(
    network,
    words,
):
    return tuple(
        observe(
            network,
            word,
        )
        for word in words
    )


def find_first_distinguishing_word(
    left,
    right,
    words,
):
    for word in words:
        left_output = observe(
            left,
            word,
        )

        right_output = observe(
            right,
            word,
        )

        if left_output != right_output:
            return (
                word,
                left_output,
                right_output,
            )

    return None


def main() -> None:
    print(
        "SPK NETWORK CONTEXTUAL HORIZON v0"
    )

    networks = enumerate_networks()

    print(
        f"typed networks: "
        f"{len(networks)}"
    )

    print(
        f"maximum horizon: "
        f"{MAX_HORIZON}"
    )

    print()

    previous_groups = None

    #
    # Keep class membership by labels so that refinement can be
    # examined without depending on object identity.
    #
    previous_membership = None

    first_refinement = None

    for horizon in range(
        1,
        MAX_HORIZON + 1,
    ):
        words = tuple(
            input_words(
                horizon
            )
        )

        groups = defaultdict(
            list
        )

        signatures = {}

        for label, network in networks:
            signature = full_signature(
                network,
                words,
            )

            signatures[
                label
            ] = signature

            groups[
                signature
            ].append(
                (
                    label,
                    network,
                )
            )

        class_count = len(
            groups
        )

        largest = max(
            len(members)
            for members in groups.values()
        )

        non_singletons = sum(
            1
            for members in groups.values()
            if len(members) > 1
        )

        print(
            f"H={horizon:2d} "
            f"words={len(words):5d} "
            f"classes={class_count:3d} "
            f"non_singleton={non_singletons:3d} "
            f"largest={largest:3d}"
        )

        membership = {
            label: signature
            for signature, members
            in groups.items()
            for label, _ in members
        }

        if previous_membership is not None:
            #
            # Find a pair that was equivalent at H-1 and becomes
            # distinguishable at H.
            #
            labels = tuple(
                label
                for label, _
                in networks
            )

            network_by_label = dict(
                networks
            )

            for i, left_label in enumerate(
                labels
            ):
                for right_label in labels[
                    i + 1:
                ]:
                    if (
                        previous_membership[
                            left_label
                        ]
                        != previous_membership[
                            right_label
                        ]
                    ):
                        continue

                    if (
                        membership[
                            left_label
                        ]
                        == membership[
                            right_label
                        ]
                    ):
                        continue

                    witness = (
                        find_first_distinguishing_word(
                            network_by_label[
                                left_label
                            ],
                            network_by_label[
                                right_label
                            ],
                            words,
                        )
                    )

                    if witness is not None:
                        first_refinement = (
                            horizon,
                            left_label,
                            right_label,
                            witness,
                        )

                        break

                if first_refinement:
                    break

        previous_groups = groups
        previous_membership = (
            membership
        )

    print()
    print(
        "=" * 88
    )
    print(
        "FINAL HORIZON"
    )
    print(
        "=" * 88
    )

    print(
        f"H={MAX_HORIZON}"
    )

    print(
        f"complete binary histories: "
        f"{2 ** MAX_HORIZON}"
    )

    print(
        f"contextual classes: "
        f"{len(previous_groups)}"
    )

    print(
        f"collapsed excess: "
        f"{len(networks) - len(previous_groups)}"
    )

    if first_refinement is not None:
        (
            horizon,
            left_label,
            right_label,
            witness,
        ) = first_refinement

        (
            word,
            left_output,
            right_output,
        ) = witness

        print()
        print(
            "=" * 88
        )
        print(
            "FIRST HORIZON REFINEMENT WITNESS"
        )
        print(
            "=" * 88
        )

        print(
            f"horizon: {horizon}"
        )

        print(
            "network L:"
        )
        print(
            f"    {left_label}"
        )

        print(
            "network R:"
        )
        print(
            f"    {right_label}"
        )

        print(
            f"input word: "
            f"{''.join(map(str, word))}"
        )

        print(
            f"input timestamps: "
            f"{tuple(
                i
                for i, bit in enumerate(word)
                if bit
            )}"
        )

        print(
            "L output:"
        )
        print(
            f"    {left_output}"
        )

        print(
            "R output:"
        )
        print(
            f"    {right_output}"
        )

    else:
        print()
        print(
            "No behavioral refinement was detected "
            "between consecutive horizons."
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
        "CONTEXTUAL HORIZON CENSUS COMPLETE"
    )

    print(
        "No infinite-horizon equivalence "
        "claim is made."
    )


if __name__ == "__main__":
    main()
