from __future__ import annotations

from collections import Counter, defaultdict
from itertools import product

from search.core_synthesis_v1 import (
    INSTRUCTION_POOL,
    program_signature,
    render_instruction,
    render_program,
)

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
)


MAX_LENGTH = 4


def program_key(
    program: CoreProgram,
):
    return (
        len(
            program.instructions
        ),
        repr(
            program.instructions
        ),
    )


def one_instruction_removal(
    longer: CoreProgram,
    shorter: CoreProgram,
):
    """
    Return the removed instruction if deleting exactly one instruction
    from longer produces shorter.
    """

    if (
        len(longer.instructions)
        != len(shorter.instructions) + 1
    ):
        return None

    for index in range(
        len(longer.instructions)
    ):
        candidate = CoreProgram(
            longer.instructions[:index]
            + longer.instructions[
                index + 1:
            ]
        )

        if candidate == shorter:
            return longer.instructions[
                index
            ]

    return None


def main() -> None:
    syntactic_count = 0

    canonical_programs = set()

    behavior_to_canonical = (
        defaultdict(set)
    )

    source_behaviors = set()

    violations = []

    canonical_origin_lengths = (
        defaultdict(set)
    )

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            INSTRUCTION_POOL,
            repeat=length,
        ):
            source = CoreProgram(
                instructions
            )

            canonical = (
                canonicalize_core_program(
                    source
                )
            )

            source_signature = (
                program_signature(
                    source
                )
            )

            canonical_signature = (
                program_signature(
                    canonical
                )
            )

            syntactic_count += 1

            source_behaviors.add(
                source_signature
            )

            canonical_programs.add(
                canonical
            )

            canonical_origin_lengths[
                canonical
            ].add(
                length
            )

            behavior_to_canonical[
                canonical_signature
            ].add(
                canonical
            )

            if (
                source_signature
                != canonical_signature
            ):
                violations.append(
                    (
                        source,
                        canonical,
                    )
                )

    ambiguous = [
        (
            signature,
            tuple(
                sorted(
                    programs,
                    key=program_key,
                )
            ),
        )
        for signature, programs
        in behavior_to_canonical.items()
        if len(programs) > 1
    ]

    ambiguous.sort(
        key=lambda item: (
            -len(item[1]),
            program_key(
                item[1][0]
            ),
        )
    )

    residual_excess = sum(
        len(programs) - 1
        for _, programs
        in ambiguous
    )

    class_sizes = Counter(
        len(programs)
        for _, programs
        in behavior_to_canonical.items()
    )

    print(
        "SPK/CORE RESIDUAL ANALYSIS v1"
    )

    print()

    print(
        f"syntactic programs: "
        f"{syntactic_count}"
    )

    print(
        f"unique canonical programs: "
        f"{len(canonical_programs)}"
    )

    print(
        f"unique behavioral classes: "
        f"{len(source_behaviors)}"
    )

    print(
        f"canonical/behavior ratio: "
        f"{len(canonical_programs) / len(source_behaviors):.6f}"
    )

    print(
        f"ambiguous behavioral classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"residual excess canonical forms: "
        f"{residual_excess}"
    )

    print(
        f"semantic preservation violations: "
        f"{len(violations)}"
    )

    print()

    print(
        "BEHAVIORAL CLASS SIZE DISTRIBUTION"
    )

    for size in sorted(
        class_sizes
    ):
        print(
            f"  size={size}: "
            f"{class_sizes[size]}"
        )

    print()

    #
    # Find residual equivalences where one canonical program differs
    # from the shortest representative by exactly one instruction.
    #
    removable_candidates = []

    same_length_candidates = []

    for _, programs in ambiguous:
        shortest_length = min(
            len(
                program.instructions
            )
            for program in programs
        )

        shortest = [
            program
            for program in programs
            if len(
                program.instructions
            ) == shortest_length
        ]

        representative = min(
            shortest,
            key=repr,
        )

        for alternative in programs:
            if alternative == representative:
                continue

            removed = (
                one_instruction_removal(
                    alternative,
                    representative,
                )
            )

            if removed is not None:
                removable_candidates.append(
                    (
                        representative,
                        alternative,
                        removed,
                    )
                )

            elif (
                len(
                    alternative.instructions
                )
                == len(
                    representative.instructions
                )
            ):
                same_length_candidates.append(
                    (
                        representative,
                        alternative,
                    )
                )

    print(
        "ONE-EXTRA-INSTRUCTION CANDIDATES"
    )

    print(
        f"count: "
        f"{len(removable_candidates)}"
    )

    for index, (
        representative,
        alternative,
        removed,
    ) in enumerate(
        removable_candidates[:20],
        start=1,
    ):
        print()
        print(
            f"CANDIDATE {index}"
        )

        print(
            "short:"
        )

        print(
            render_program(
                representative
            )
        )

        print(
            "long:"
        )

        print(
            render_program(
                alternative
            )
        )

        print(
            "extra:"
        )

        print(
            "  "
            + render_instruction(
                removed
            )
        )

    print()
    print(
        "SAME-LENGTH RESIDUAL CANDIDATES"
    )

    print(
        f"count: "
        f"{len(same_length_candidates)}"
    )

    for index, (
        left,
        right,
    ) in enumerate(
        same_length_candidates[:20],
        start=1,
    ):
        print()
        print(
            f"CANDIDATE {index}"
        )

        print(
            "left:"
        )

        print(
            render_program(
                left
            )
        )

        print(
            "right:"
        )

        print(
            render_program(
                right
            )
        )

    print()
    print(
        "LARGEST RESIDUAL CLASSES"
    )

    for index, (
        _,
        programs,
    ) in enumerate(
        ambiguous[:20],
        start=1,
    ):
        print()

        print(
            f"CLASS {index}: "
            f"{len(programs)} canonical forms"
        )

        for program in programs:
            origins = sorted(
                canonical_origin_lengths[
                    program
                ]
            )

            print(
                f"  [from lengths "
                f"{origins}]"
            )

            rendered = (
                render_program(
                    program
                )
            )

            for line in (
                rendered.splitlines()
            ):
                print(
                    "   ",
                    line,
                )

            if not program.instructions:
                print(
                    "    <EMPTY>"
                )

    if violations:
        print()
        print(
            "FIRST PRESERVATION VIOLATION"
        )

        source, canonical = (
            violations[0]
        )

        print(
            "SOURCE"
        )

        print(
            render_program(
                source
            )
        )

        print(
            "CANONICAL"
        )

        print(
            render_program(
                canonical
            )
        )


if __name__ == "__main__":
    main()
