from __future__ import annotations

from itertools import combinations

from search.canonicalize import canonicalize
from search.corpus_v1 import CORPUS_V1, TRAINS
from search.counterexample import find_counterexample
from search.enumerate import enumerate_programs
from search.equivalence import (
    Sample,
    cluster_by_signature,
)
from spk.operators import (
    Acc,
    Compare,
    Emit,
    Reset,
)
from spk.program import Program


OPERATORS = (
    Acc(
        weight=0.0,
        channel=0,
    ),
    Acc(
        weight=1.0,
        channel=0,
    ),
    Acc(
        weight=2.0,
        channel=0,
    ),
    Compare(
        threshold=1.0,
    ),
    Compare(
        threshold=2.0,
    ),
    Emit(
        channel_out=0,
    ),
    Reset(
        value=0.0,
    ),
)


#
# Quarter-grid rather than the half-grid of corpus v1.
#
# It deliberately reaches farther into negative initial states,
# where several current residual collisions are expected to split.
#
CANDIDATE_INITIAL_STATES = tuple(
    value / 4.0
    for value in range(-32, 17)
)


def format_program(
    program: Program,
) -> str:
    if not program.operators:
        return "<EMPTY>"

    return " -> ".join(
        repr(operator)
        for operator in program.operators
    )


def canonical_forms() -> tuple[Program, ...]:
    programs = enumerate_programs(
        OPERATORS,
        min_length=0,
        max_length=4,
    )

    return tuple(
        sorted(
            {
                canonicalize(program)
                for program in programs
            },
            key=lambda program: (
                len(program),
                repr(program.operators),
            ),
        )
    )


def candidate_samples() -> tuple[Sample, ...]:
    existing = set(CORPUS_V1)

    candidates = []

    for train in TRAINS:
        for initial_x in CANDIDATE_INITIAL_STATES:
            sample = Sample(
                train=train,
                initial_x=initial_x,
            )

            if sample not in existing:
                candidates.append(sample)

    return tuple(candidates)


def find_class_counterexample(
    members: tuple[Program, ...],
    candidates: tuple[Sample, ...],
):
    """
    Search all pairs in one empirical class.

    Important: the first pair may be genuinely equivalent while
    another pair in the same class is not.
    """

    for left, right in combinations(
        members,
        2,
    ):
        counterexample = find_counterexample(
            left,
            right,
            candidates,
        )

        if counterexample is not None:
            return (
                left,
                right,
                counterexample,
            )

    return None


def main() -> None:
    programs = canonical_forms()

    corpus = list(CORPUS_V1)
    candidates = list(
        candidate_samples()
    )

    print(
        f"canonical forms: {len(programs)}"
    )

    print(
        f"initial corpus samples: {len(corpus)}"
    )

    print(
        f"candidate samples: {len(candidates)}"
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

        for members in ambiguous:
            found = find_class_counterexample(
                members,
                tuple(candidates),
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

        #
        # Deduplicate samples because one sample may split several
        # classes at once.
        #
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
            f"  discovered counterexamples: "
            f"{len(unique)}"
        )

        for sample, (
            left,
            right,
            counterexample,
        ) in tuple(unique.items())[:10]:
            print()
            print(
                f"  initial_x={sample.initial_x}"
            )

            print(
                f"  train={sample.train.as_pairs()}"
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
                f"  left observation: "
                f"{counterexample.left}"
            )

            print(
                f"  right observation: "
                f"{counterexample.right}"
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
        f"corpus samples: {len(corpus)}"
    )
    print(
        f"empirical classes: "
        f"{len(final_clusters)}"
    )
    print(
        f"unresolved ambiguous classes: "
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
