from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import groupby, product

from search.core_synthesis_v1 import (
    CONFIG,
    INITIAL_STATES,
    INSTRUCTION_POOL,
    SAMPLES,
    program_signature,
    render_program,
)
from spk.event import SpikeTrain

from spk_core.isa import (
    CoreProgram,
)


def specification_observation(
    train: SpikeTrain,
    initial_raw: int,
):
    """
    Declarative behavior.

    No Core instructions are used here.

    Semantics:
      * persistent integer state x
      * on every nonempty event batch:
          x += count(channel 0)
          guard = (x >= 2)
          if guard:
              emit channel 7
              x = 0
      * channel 1 does not contribute
    """

    x = initial_raw

    guard = False

    outputs = []

    pairs = train.as_pairs()

    for timestamp, group in groupby(
        pairs,
        key=lambda pair: pair[0],
    ):
        batch = tuple(
            group
        )

        counts = Counter(
            channel
            for _, channel
            in batch
        )

        x += counts[0]

        guard = (
            x >= 2
        )

        if guard:
            outputs.append(
                (
                    timestamp,
                    7,
                )
            )

            x = 0

    return (
        tuple(outputs),
        x,
        guard,
    )


def specification_signature():
    return tuple(
        specification_observation(
            train,
            initial_raw,
        )
        for train, initial_raw
        in SAMPLES
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DepthResult:
    length: int
    syntactic_programs: int
    behavioral_classes: int
    specification_matches: int


@dataclass(
    frozen=True,
    slots=True,
)
class SynthesisResult:
    minimum_length: int
    minimal_programs: tuple[
        CoreProgram,
        ...,
    ]
    depth_results: tuple[
        DepthResult,
        ...,
    ]


def synthesize_from_specification(
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
        signatures = set()

        matches = []

        for instructions in product(
            INSTRUCTION_POOL,
            repeat=length,
        ):
            program = CoreProgram(
                instructions
            )

            signature = (
                program_signature(
                    program
                )
            )

            signatures.add(
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
                    len(
                        INSTRUCTION_POOL
                    )
                    ** length
                ),
                behavioral_classes=(
                    len(signatures)
                ),
                specification_matches=(
                    len(matches)
                ),
            )
        )

        if matches:
            return SynthesisResult(
                minimum_length=length,
                minimal_programs=tuple(
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
        "SPK/CORE SPECIFICATION SYNTHESIS v2"
    )

    print(
        f"instruction pool: "
        f"{len(INSTRUCTION_POOL)}"
    )

    print(
        f"behavioral samples: "
        f"{len(SAMPLES)}"
    )

    print()

    result = (
        synthesize_from_specification()
    )

    print(
        "SEARCH"
    )

    for depth in (
        result.depth_results
    ):
        print(
            f"  length={depth.length} "
            f"syntactic="
            f"{depth.syntactic_programs} "
            f"behavioral="
            f"{depth.behavioral_classes} "
            f"spec_matches="
            f"{depth.specification_matches}"
        )

    print()

    print(
        f"minimum program length: "
        f"{result.minimum_length}"
    )

    print(
        f"minimal solutions: "
        f"{len(result.minimal_programs)}"
    )

    print()

    print(
        "ALL MINIMAL SOLUTIONS"
    )

    for index, program in enumerate(
        result.minimal_programs,
        start=1,
    ):
        print()

        print(
            f"SOLUTION {index}"
        )

        print(
            render_program(
                program
            )
        )

    print()

    desired = (
        specification_signature()
    )

    print(
        "all solutions satisfy specification: ",
        all(
            program_signature(
                program
            ) == desired
            for program
            in result.minimal_programs
        ),
    )


if __name__ == "__main__":
    main()
