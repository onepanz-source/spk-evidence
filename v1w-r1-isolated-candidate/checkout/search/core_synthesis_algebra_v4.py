from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from search.core_synthesis_spec_v2 import (
    specification_signature,
)
from search.core_synthesis_v1 import (
    INSTRUCTION_POOL,
    program_signature,
    render_program,
)

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
)


MAX_LENGTH = 4


@dataclass(
    frozen=True,
    slots=True,
)
class DepthResult:
    length: int
    syntactic: int
    canonical: int
    behavioral: int
    preservation_violations: int
    specification_matches: int


def main() -> None:
    desired = (
        specification_signature()
    )

    print(
        "SPK/CORE ALGEBRA-GUIDED "
        "SYNTHESIS v4"
    )

    print(
        f"instruction pool: "
        f"{len(INSTRUCTION_POOL)}"
    )

    print()

    total_syntactic = 0
    total_canonical = 0

    all_violations = []

    solution = None

    results = []

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        syntactic_count = 0

        canonical_programs = set()

        behavioral = set()

        matches = set()

        violations = []

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

            canonical_programs.add(
                canonical
            )

            behavioral.add(
                source_signature
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

            if (
                canonical_signature
                == desired
            ):
                matches.add(
                    canonical
                )

        result = DepthResult(
            length=length,
            syntactic=syntactic_count,
            canonical=len(
                canonical_programs
            ),
            behavioral=len(
                behavioral
            ),
            preservation_violations=len(
                violations
            ),
            specification_matches=len(
                matches
            ),
        )

        results.append(
            result
        )

        total_syntactic += (
            syntactic_count
        )

        total_canonical += len(
            canonical_programs
        )

        all_violations.extend(
            violations
        )

        if (
            solution is None
            and matches
        ):
            solution = min(
                matches,
                key=repr,
            )

    print(
        "SEARCH"
    )

    for result in results:
        ratio = (
            result.canonical
            / result.behavioral
        )

        print(
            f"  length="
            f"{result.length} "
            f"syntactic="
            f"{result.syntactic} "
            f"canonical="
            f"{result.canonical} "
            f"behavioral="
            f"{result.behavioral} "
            f"canon/beh="
            f"{ratio:.3f} "
            f"violations="
            f"{result.preservation_violations} "
            f"spec_matches="
            f"{result.specification_matches}"
        )

    print()

    print(
        f"total syntactic: "
        f"{total_syntactic}"
    )

    print(
        f"total canonical: "
        f"{total_canonical}"
    )

    print(
        f"total algebraic reduction: "
        f"{total_syntactic - total_canonical}"
    )

    print(
        f"evaluation ratio: "
        f"{total_canonical / total_syntactic:.6f}"
    )

    print(
        f"semantic preservation "
        f"violations: "
        f"{len(all_violations)}"
    )

    if solution is not None:
        print()
        print(
            "CANONICAL SYNTHESIZED "
            "PROGRAM"
        )

        print(
            render_program(
                solution
            )
        )

    if all_violations:
        print()
        print(
            "FIRST PRESERVATION "
            "VIOLATION"
        )

        source, canonical = (
            all_violations[0]
        )

        print()

        print(
            "SOURCE"
        )

        print(
            render_program(
                source
            )
        )

        print()

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
