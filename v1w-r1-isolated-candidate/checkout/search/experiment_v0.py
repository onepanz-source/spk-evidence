from search.enumerate import enumerate_programs
from search.equivalence import (
    Sample,
    cluster_by_signature,
)
from spk.event import SpikeTrain
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


CORPUS = (
    Sample(
        SpikeTrain.from_pairs([]),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [
                (1, 0),
                (2, 0),
            ]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [
                (1, 0),
                (2, 0),
                (3, 0),
            ]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [
                (1, 0),
                (3, 0),
                (8, 0),
            ]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [
                (1, 1),
                (2, 1),
            ]
        ),
        initial_x=0.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=1.0,
    ),
    Sample(
        SpikeTrain.from_pairs(
            [(1, 0)]
        ),
        initial_x=2.0,
    ),
)


def format_program(program: Program) -> str:
    if not program.operators:
        return "<EMPTY>"

    return " -> ".join(
        repr(operator)
        for operator in program.operators
    )


def main() -> None:
    programs = tuple(
        enumerate_programs(
            OPERATORS,
            min_length=0,
            max_length=4,
        )
    )

    clusters = cluster_by_signature(
        programs,
        CORPUS,
    )

    class_sizes = sorted(
        (
            len(members)
            for members in clusters.values()
        ),
        reverse=True,
    )

    print(
        f"operators: {len(OPERATORS)}"
    )

    print(
        f"syntactic programs: {len(programs)}"
    )

    print(
        f"empirical classes: {len(clusters)}"
    )

    print(
        "compression ratio: "
        f"{len(programs) / len(clusters):.3f}"
    )

    print(
        f"largest class: {class_sizes[0]}"
    )

    print()
    print("Largest equivalence classes:")
    print()

    ranked = sorted(
        clusters.values(),
        key=len,
        reverse=True,
    )

    for index, members in enumerate(
        ranked[:10],
        start=1,
    ):
        print(
            f"class {index}: "
            f"{len(members)} programs"
        )

        for program in members[:5]:
            print(
                "  ",
                format_program(program),
            )

        if len(members) > 5:
            print(
                f"   ... +{len(members) - 5}"
            )

        print()


if __name__ == "__main__":
    main()
