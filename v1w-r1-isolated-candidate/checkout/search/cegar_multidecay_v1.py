from __future__ import annotations

import math
from itertools import combinations

from search.canonicalize import canonicalize
from search.corpus_decay_v1 import CORPUS_DECAY_V1
from search.counterexample import find_counterexample
from search.enumerate import enumerate_programs
from search.equivalence import (
    Sample,
    cluster_by_signature,
)
from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)
from spk.program import Program


OPERATORS = (
    Acc(weight=0.0, channel=0),
    Acc(weight=1.0, channel=0),
    Acc(weight=2.0, channel=0),

    Decay(tau=1.0),
    Decay(tau=2.0),

    Compare(threshold=1.0),
    Compare(threshold=2.0),

    Emit(channel_out=0),
    Reset(value=0.0),
)


TIMESTAMPS = (
    0,
    1,
    2,
    3,
    5,
    8,
)


#
# With base rates:
#
#   lambda = 1/tau = 1.0 and 0.5
#
# and program length <= 4, a consecutive run can produce:
#
#   0.5, 1.0, 1.5, ..., 4.0
#
EFFECTIVE_RATES = tuple(
    index / 2.0
    for index in range(1, 9)
)


def build_candidate_trains() -> tuple[SpikeTrain, ...]:
    trains = []

    #
    # Single batches.
    #
    # Channel 1 advances time without activating ACC(channel=0).
    #
    for timestamp in TIMESTAMPS:
        trains.append(
            SpikeTrain.from_pairs(
                [(timestamp, 1)]
            )
        )

        trains.append(
            SpikeTrain.from_pairs(
                [(timestamp, 0)]
            )
        )

    #
    # Multi-batch temporal probes.
    #
    for channel in (0, 1):
        trains.extend(
            (
                SpikeTrain.from_pairs(
                    [
                        (0, channel),
                        (1, channel),
                    ]
                ),
                SpikeTrain.from_pairs(
                    [
                        (0, channel),
                        (3, channel),
                    ]
                ),
                SpikeTrain.from_pairs(
                    [
                        (1, channel),
                        (2, channel),
                    ]
                ),
                SpikeTrain.from_pairs(
                    [
                        (1, channel),
                        (8, channel),
                    ]
                ),
            )
        )

    return tuple(
        dict.fromkeys(trains)
    )


def build_candidate_initial_states() -> tuple[float, ...]:
    values = {
        value / 4.0
        for value in range(
            -64,
            129,
        )
    }

    #
    # Construct states around every analytically relevant threshold
    # preimage:
    #
    #     x * exp(-lambda * delta) = theta
    #
    # therefore:
    #
    #     x = theta * exp(lambda * delta)
    #
    # This includes the newly synthesized decay rates.
    #
    for threshold in (
        1.0,
        2.0,
    ):
        for rate in EFFECTIVE_RATES:
            for delta in TIMESTAMPS:
                critical = (
                    threshold
                    * math.exp(
                        rate * delta
                    )
                )

                values.add(
                    critical
                )

                values.add(
                    critical * 0.999
                )

                values.add(
                    critical * 1.001
                )

    return tuple(
        sorted(values)
    )


CANDIDATE_TRAINS = (
    build_candidate_trains()
)

CANDIDATE_INITIAL_STATES = (
    build_candidate_initial_states()
)


def canonical_forms() -> tuple[Program, ...]:
    return tuple(
        sorted(
            {
                canonicalize(program)
                for program in enumerate_programs(
                    OPERATORS,
                    min_length=0,
                    max_length=4,
                )
            },
            key=lambda program: (
                len(program),
                repr(program.operators),
            ),
        )
    )


def candidate_samples() -> tuple[Sample, ...]:
    existing = set(
        CORPUS_DECAY_V1
    )

    result = []

    for train in CANDIDATE_TRAINS:
        for initial_x in CANDIDATE_INITIAL_STATES:
            sample = Sample(
                train=train,
                initial_x=initial_x,
            )

            if sample not in existing:
                result.append(sample)

    return tuple(result)


def find_class_counterexample(
    members: tuple[Program, ...],
    candidates: tuple[Sample, ...],
):
    for left, right in combinations(
        members,
        2,
    ):
        counterexample = (
            find_counterexample(
                left,
                right,
                candidates,
            )
        )

        if counterexample is not None:
            return (
                left,
                right,
                counterexample,
            )

    return None


def format_program(
    program: Program,
) -> str:
    if not program.operators:
        return "<EMPTY>"

    return " -> ".join(
        repr(operator)
        for operator in program.operators
    )


def main() -> None:
    programs = canonical_forms()

    corpus = list(
        CORPUS_DECAY_V1
    )

    candidates = list(
        candidate_samples()
    )

    print(
        f"canonical forms: {len(programs)}"
    )

    print(
        f"initial corpus samples: "
        f"{len(corpus)}"
    )

    print(
        f"candidate trains: "
        f"{len(CANDIDATE_TRAINS)}"
    )

    print(
        f"candidate initial states: "
        f"{len(CANDIDATE_INITIAL_STATES)}"
    )

    print(
        f"candidate samples: "
        f"{len(candidates)}"
    )

    print()

    round_number = 0

    while True:
        clusters = cluster_by_signature(
            programs,
            corpus,
        )

        ambiguous = [
            members
            for members in clusters.values()
            if len(members) > 1
        ]

        excess = sum(
            len(members) - 1
            for members in ambiguous
        )

        print(
            f"round {round_number}: "
            f"classes={len(clusters)} "
            f"ambiguous={len(ambiguous)} "
            f"excess={excess} "
            f"corpus={len(corpus)}"
        )

        additions = []

        candidates_tuple = tuple(
            candidates
        )

        for members in ambiguous:
            found = find_class_counterexample(
                members,
                candidates_tuple,
            )

            if found is None:
                continue

            left, right, counterexample = found

            additions.append(
                (
                    counterexample.sample,
                    left,
                    right,
                    counterexample,
                )
            )

        if not additions:
            break

        unique = {}

        for (
            sample,
            left,
            right,
            counterexample,
        ) in additions:
            unique.setdefault(
                sample,
                (
                    left,
                    right,
                    counterexample,
                ),
            )

        print(
            "  discovered counterexamples: "
            f"{len(unique)}"
        )

        for sample, (
            left,
            right,
            counterexample,
        ) in tuple(
            unique.items()
        )[:20]:
            print()

            print(
                f"  initial_x="
                f"{sample.initial_x:.17g}"
            )

            print(
                "  train="
                f"{sample.train.as_pairs()}"
            )

            print(
                "  left: ",
                format_program(left),
            )

            print(
                "  right:",
                format_program(right),
            )

            print(
                "  left observation: ",
                counterexample.left,
            )

            print(
                "  right observation:",
                counterexample.right,
            )

        new_samples = set(
            unique.keys()
        )

        corpus.extend(
            sorted(
                new_samples,
                key=lambda sample: (
                    sample.initial_x,
                    sample.train.as_pairs(),
                ),
            )
        )

        candidates = [
            sample
            for sample in candidates
            if sample not in new_samples
        ]

        round_number += 1
        print()

    final_clusters = cluster_by_signature(
        programs,
        corpus,
    )

    unresolved = [
        tuple(
            sorted(
                members,
                key=lambda program: (
                    len(program),
                    repr(program.operators),
                ),
            )
        )
        for members in final_clusters.values()
        if len(members) > 1
    ]

    unresolved.sort(
        key=lambda members: (
            -len(members),
            repr(members),
        )
    )

    print()
    print("FINAL")

    print(
        f"corpus samples: "
        f"{len(corpus)}"
    )

    print(
        f"empirical classes: "
        f"{len(final_clusters)}"
    )

    print(
        "unresolved ambiguous classes: "
        f"{len(unresolved)}"
    )

    print(
        "unresolved excess forms: "
        f"{sum(len(members) - 1 for members in unresolved)}"
    )

    print()
    print("Unresolved classes:")
    print()

    for index, members in enumerate(
        unresolved,
        start=1,
    ):
        print(
            f"class {index}: "
            f"{len(members)} forms"
        )

        for program in members:
            print(
                "  ",
                format_program(program),
            )

        print()


if __name__ == "__main__":
    main()
