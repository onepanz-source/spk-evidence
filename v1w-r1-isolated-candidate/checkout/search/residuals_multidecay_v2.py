from __future__ import annotations

from collections import Counter

from search.canonicalize import canonicalize
from search.corpus_decay_v1 import CORPUS_DECAY_V1
from search.enumerate import enumerate_programs
from search.equivalence import cluster_by_signature
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


def program_key(
    program: Program,
) -> tuple[int, str]:
    return (
        len(program),
        repr(program.operators),
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


def main() -> None:
    syntactic_programs = tuple(
        enumerate_programs(
            OPERATORS,
            min_length=0,
            max_length=4,
        )
    )

    canonical_forms = tuple(
        sorted(
            {
                canonicalize(program)
                for program in syntactic_programs
            },
            key=program_key,
        )
    )

    clusters = cluster_by_signature(
        canonical_forms,
        CORPUS_DECAY_V1,
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

    singleton_count = sum(
        1
        for members in clusters.values()
        if len(members) == 1
    )

    ambiguous_form_count = sum(
        len(members)
        for members in ambiguous
    )

    histogram = Counter(
        len(members)
        for members in clusters.values()
    )

    print(
        f"corpus samples: {len(CORPUS_DECAY_V1)}"
    )

    print(
        f"syntactic programs: "
        f"{len(syntactic_programs)}"
    )

    print(
        f"canonical forms: "
        f"{len(canonical_forms)}"
    )

    print(
        f"empirical classes: "
        f"{len(clusters)}"
    )

    print(
        f"singleton classes: "
        f"{singleton_count}"
    )

    print(
        f"ambiguous classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"canonical forms in ambiguous classes: "
        f"{ambiguous_form_count}"
    )

    print(
        "residual excess forms: "
        f"{sum(len(members) - 1 for members in ambiguous)}"
    )

    if ambiguous:
        print(
            f"largest residual class: "
            f"{len(ambiguous[0])}"
        )

    print()
    print("Class-size histogram:")

    for size in sorted(histogram):
        print(
            f"  size={size}: "
            f"{histogram[size]}"
        )

    print()
    print("Largest residual equivalence classes:")
    print()

    for index, members in enumerate(
        ambiguous[:30],
        start=1,
    ):
        print(
            f"class {index}: "
            f"{len(members)} canonical forms"
        )

        for program in members:
            print(
                "  ",
                format_program(program),
            )

        print()


if __name__ == "__main__":
    main()
