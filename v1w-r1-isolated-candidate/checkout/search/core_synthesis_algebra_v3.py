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

from spk_core.isa import (
    CoreCmp,
    CoreEmit,
    CoreProgram,
    CoreReset,
)


def canonicalize_core_program(
    program: CoreProgram,
) -> CoreProgram:
    """
    Core algebra v0 canonicalization.

    Proven local law:

        CMP ; RESET ; EMIT
          ==
        CMP ; EMIT ; RESET

    because:
      * CMP establishes guard
      * RESET changes state but not guard
      * EMIT observes guard but not state

    Canonical orientation:
        EMIT before RESET.
    """

    instructions = list(
        program.instructions
    )

    changed = True

    while changed:
        changed = False

        index = 0

        while (
            index + 2
            < len(instructions)
        ):
            first = instructions[
                index
            ]

            second = instructions[
                index + 1
            ]

            third = instructions[
                index + 2
            ]

            if (
                isinstance(
                    first,
                    CoreCmp,
                )
                and isinstance(
                    second,
                    CoreReset,
                )
                and isinstance(
                    third,
                    CoreEmit,
                )
            ):
                instructions[
                    index + 1
                ] = third

                instructions[
                    index + 2
                ] = second

                changed = True

                index += 3
                continue

            index += 1

    return CoreProgram(
        tuple(
            instructions
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DepthResult:
    length: int
    syntactic_programs: int
    canonical_programs: int
    behavioral_classes: int
    specification_matches: int

    @property
    def pruned_programs(
        self,
    ) -> int:
        return (
            self.syntactic_programs
            - self.canonical_programs
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SynthesisResult:
    minimum_length: int
    solutions: tuple[
        CoreProgram,
        ...,
    ]
    depth_results: tuple[
        DepthResult,
        ...,
    ]


def synthesize_algebra_guided(
    max_length: int = 4,
) -> SynthesisResult:
    desired = (
        specification_signature()
    )

    depth_results = []

    for length in range(
        1,
        max_length + 1,
    ):
        canonical_candidates = set()

        syntactic_count = 0

        for instructions in product(
            INSTRUCTION_POOL,
            repeat=length,
        ):
            syntactic_count += 1

            program = CoreProgram(
                instructions
            )

            canonical = (
                canonicalize_core_program(
                    program
                )
            )

            canonical_candidates.add(
                canonical
            )

        behavioral_signatures = set()

        matches = []

        for program in sorted(
            canonical_candidates,
            key=repr,
        ):
            signature = (
                program_signature(
                    program
                )
            )

            behavioral_signatures.add(
                signature
            )

            if signature == desired:
                matches.append(
                    program
                )

        depth_results.append(
            DepthResult(
                length=length,
                syntactic_programs=(
                    syntactic_count
                ),
                canonical_programs=(
                    len(
                        canonical_candidates
                    )
                ),
                behavioral_classes=(
                    len(
                        behavioral_signatures
                    )
                ),
                specification_matches=(
                    len(matches)
                ),
            )
        )

        if matches:
            return SynthesisResult(
                minimum_length=length,
                solutions=tuple(
                    matches
                ),
                depth_results=tuple(
                    depth_results
                ),
            )

    raise LookupError(
        "specification not synthesized "
        f"through length {max_length}"
    )


def main() -> None:
    print(
        "SPK/CORE ALGEBRA-GUIDED "
        "SYNTHESIS v3"
    )

    print(
        f"instruction pool: "
        f"{len(INSTRUCTION_POOL)}"
    )

    print()

    result = (
        synthesize_algebra_guided()
    )

    print(
        "SEARCH"
    )

    total_syntactic = 0
    total_canonical = 0

    for depth in (
        result.depth_results
    ):
        total_syntactic += (
            depth.syntactic_programs
        )

        total_canonical += (
            depth.canonical_programs
        )

        print(
            f"  length={depth.length} "
            f"syntactic="
            f"{depth.syntactic_programs} "
            f"canonical="
            f"{depth.canonical_programs} "
            f"pruned="
            f"{depth.pruned_programs} "
            f"behavioral="
            f"{depth.behavioral_classes} "
            f"spec_matches="
            f"{depth.specification_matches}"
        )

    print()

    print(
        f"total syntactic candidates: "
        f"{total_syntactic}"
    )

    print(
        f"total canonical candidates: "
        f"{total_canonical}"
    )

    print(
        f"algebraic candidates removed: "
        f"{total_syntactic - total_canonical}"
    )

    print(
        f"canonical evaluation ratio: "
        f"{total_canonical / total_syntactic:.6f}"
    )

    print()

    print(
        f"minimum program length: "
        f"{result.minimum_length}"
    )

    print(
        f"canonical minimal solutions: "
        f"{len(result.solutions)}"
    )

    print()

    print(
        "CANONICAL SOLUTIONS"
    )

    for number, program in enumerate(
        result.solutions,
        start=1,
    ):
        print()

        print(
            f"SOLUTION {number}"
        )

        print(
            render_program(
                program
            )
        )


if __name__ == "__main__":
    main()
