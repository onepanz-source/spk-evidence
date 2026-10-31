from __future__ import annotations

import math
from itertools import combinations

from search.canonicalize import canonicalize
from search.corpus_multidecay_v1 import (
    CORPUS_MULTIDECAY_V1,
)
from search.counterexample import (
    find_counterexample,
)
from search.enumerate import (
    enumerate_programs,
)
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


#
# With max program length 5 and primitive rates:
#
#     lambda = 1.0
#     lambda = 0.5
#
# consecutive DECAY runs can synthesize rates from:
#
#     0.5 ... 5.0
#
EFFECTIVE_RATES = tuple(
    index / 2.0
    for index in range(1, 11)
)


TIMESTAMPS = (
    0,
    1,
    2,
    3,
)


def build_candidate_trains() -> tuple[SpikeTrain, ...]:
    trains = []

    #
    # Channel 1:
    # advances time without activating ACC(channel=0).
    #
    for timestamp in TIMESTAMPS:
        trains.append(
            SpikeTrain.from_pairs(
                [(timestamp, 1)]
            )
        )

    #
    # Channel 0:
    # exercise ACC with multiplicities 1, 2 and 3.
    #
    for timestamp in TIMESTAMPS:
        for multiplicity in (
            1,
            2,
            3,
        ):
            trains.append(
                SpikeTrain.from_pairs(
                    [(timestamp, 0)]
                    * multiplicity
                )
            )

    #
    # A few multi-batch probes.
    #
    trains.extend(
        (
            SpikeTrain.from_pairs(
                [
                    (0, 0),
                    (1, 0),
                ]
            ),
            SpikeTrain.from_pairs(
                [
                    (0, 1),
                    (1, 1),
                ]
            ),
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (2, 0),
                ]
            ),
            SpikeTrain.from_pairs(
                [
                    (1, 1),
                    (2, 1),
                ]
            ),
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (3, 0),
                ]
            ),
            SpikeTrain.from_pairs(
                [
                    (1, 1),
                    (3, 1),
                ]
            ),
        )
    )

    return tuple(
        dict.fromkeys(
            trains
        )
    )


def build_candidate_initial_states() -> tuple[float, ...]:
    values = {
        value / 4.0
        for value in range(
            -128,
            257,
        )
    }

    #
    # Add robust probes around every threshold preimage.
    #
    # Deliberately avoid using only the exact critical value:
    # the +/-0.1% probes prevent a half-ULP threshold accident from
    # masquerading as an algebraic counterexample.
    #
    for threshold in (
        1.0,
        2.0,
    ):
        for rate in EFFECTIVE_RATES:
            for delta in (
                1,
                2,
                3,
            ):
                critical = (
                    threshold
                    * math.exp(
                        rate * delta
                    )
                )

                values.add(
                    critical * 0.999
                )

                values.add(
                    critical * 1.001
                )

    return tuple(
        sorted(
            values
        )
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
                for program
                in enumerate_programs(
                    OPERATORS,
                    min_length=0,
                    max_length=5,
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
        CORPUS_MULTIDECAY_V1
    )

    result = []

    for train in CANDIDATE_TRAINS:
        for initial_x in CANDIDATE_INITIAL_STATES:
            sample = Sample(
                train=train,
                initial_x=initial_x,
            )

            if sample not in existing:
                result.append(
                    sample
                )

    return tuple(
        result
    )


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
        CORPUS_MULTIDECAY_V1
    )

    candidates = list(
        candidate_samples()
    )

    print(
        f"canonical forms: "
        f"{len(programs)}"
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
            for members
            in clusters.values()
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

        candidate_tuple = tuple(
            candidates
        )

        for members in ambiguous:
            found = (
                find_class_counterexample(
                    tuple(members),
                    candidate_tuple,
                )
            )

            if found is None:
                continue

            left, right, counterexample = (
                found
            )

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
            "  discovered robust counterexamples: "
            f"{len(unique)}"
        )

        for sample, (
            left,
            right,
            counterexample,
        ) in tuple(
            unique.items()
        )[:25]:
            print()

            print(
                "  initial_x=",
                repr(
                    sample.initial_x
                ),
            )

            print(
                "  train=",
                sample.train.as_pairs(),
            )

            print(
                "  left: ",
                format_program(
                    left
                ),
            )

            print(
                "  right:",
                format_program(
                    right
                ),
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

    final_clusters = (
        cluster_by_signature(
            programs,
            corpus,
        )
    )

    unresolved = [
        tuple(
            sorted(
                members,
                key=lambda program: (
                    len(program),
                    repr(
                        program.operators
                    ),
                ),
            )
        )
        for members
        in final_clusters.values()
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
        f"runtime empirical classes: "
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
    print(
        "Unresolved candidate identities:"
    )
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
                format_program(
                    program
                ),
            )

        print()


if __name__ == "__main__":
    main()
