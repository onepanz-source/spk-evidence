from __future__ import annotations

from collections import Counter

from search.canonicalize import canonicalize
from search.corpus_depth5_v1 import (
    CORPUS_DEPTH5_V1,
)
from search.enumerate import (
    enumerate_programs,
)
from search.equivalence import (
    cluster_by_signature,
)
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)


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


def program_key(program):
    return (
        len(program),
        repr(program.operators),
    )


def main() -> None:
    programs = tuple(
        enumerate_programs(
            OPERATORS,
            min_length=0,
            max_length=5,
        )
    )

    canonical_forms = tuple(
        sorted(
            {
                canonicalize(program)
                for program in programs
            },
            key=program_key,
        )
    )

    clusters = cluster_by_signature(
        canonical_forms,
        CORPUS_DEPTH5_V1,
    )

    ambiguous = [
        tuple(
            sorted(
                members,
                key=program_key,
            )
        )
        for members in clusters.values()
        if len(members) > 1
    ]

    ambiguous.sort(
        key=lambda members: (
            -len(members),
            program_key(members[0]),
        )
    )

    excess = sum(
        len(members) - 1
        for members in ambiguous
    )

    histogram = Counter(
        len(members)
        for members in clusters.values()
    )

    print(
        f"syntactic programs: "
        f"{len(programs)}"
    )

    print(
        f"canonical forms: "
        f"{len(canonical_forms)}"
    )

    print(
        "syntactic/canonical ratio: "
        f"{len(programs) / len(canonical_forms):.3f}"
    )

    print(
        f"runtime empirical classes: "
        f"{len(clusters)}"
    )

    print(
        "canonical/runtime ratio: "
        f"{len(canonical_forms) / len(clusters):.3f}"
    )

    print(
        f"ambiguous runtime classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"residual excess forms: "
        f"{excess}"
    )

    print()
    print("Class-size histogram:")

    for size in sorted(
        histogram
    ):
        print(
            f"  size={size}: "
            f"{histogram[size]}"
        )

    print()
    print(
        "NOTE:"
    )

    print(
        "  These are runtime IEEE-754 empirical classes."
    )

    print(
        "  Algebraic rewrite validity is tracked separately."
    )

    print()

    for index, members in enumerate(
        ambiguous[:30],
        start=1,
    ):
        print(
            f"class {index}: "
            f"{len(members)} forms"
        )

        for program in members:
            if program.operators:
                rendered = " -> ".join(
                    repr(operator)
                    for operator
                    in program.operators
                )
            else:
                rendered = "<EMPTY>"

            print(
                f"  {rendered}"
            )

        print()


if __name__ == "__main__":
    main()
