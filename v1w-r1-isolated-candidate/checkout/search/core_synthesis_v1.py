from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

from spk.event import SpikeTrain

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_core.runtime import (
    run_core_program,
)


CONFIG = CoreConfig(
    state_bits=16,
    fractional_bits=0,
)


INSTRUCTION_POOL = (
    CoreAcc(
        weight=1,
        channel=0,
    ),
    CoreAcc(
        weight=1,
        channel=1,
    ),
    CoreCmp(
        threshold_raw=1,
    ),
    CoreCmp(
        threshold_raw=2,
    ),
    CoreEmit(
        channel_out=7,
    ),
    CoreReset(
        value_raw=0,
    ),
)


TARGET_PROGRAM = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2,
        ),
        CoreEmit(
            channel_out=7,
        ),
        CoreReset(
            value_raw=0,
        ),
    )
)


INITIAL_STATES = (
    0,
    1,
)


def history_to_train(
    history,
) -> SpikeTrain:
    pairs = []

    for timestamp, (
        ch0_count,
        ch1_count,
    ) in enumerate(
        history
    ):
        pairs.extend(
            (
                timestamp,
                0,
            )
            for _ in range(
                ch0_count
            )
        )

        pairs.extend(
            (
                timestamp,
                1,
            )
            for _ in range(
                ch1_count
            )
        )

    return SpikeTrain.from_pairs(
        pairs
    )


POSSIBLE_BATCHES = tuple(
    product(
        range(3),
        range(2),
    )
)


HISTORIES = tuple(
    product(
        POSSIBLE_BATCHES,
        repeat=3,
    )
)


SAMPLES = tuple(
    (
        history_to_train(
            history
        ),
        initial_raw,
    )
    for history in HISTORIES
    for initial_raw in INITIAL_STATES
)


def observation(
    program: CoreProgram,
    train: SpikeTrain,
    initial_raw: int,
):
    result = run_core_program(
        CONFIG,
        program,
        train,
        initial_raw=initial_raw,
    )

    return (
        result.output.as_pairs(),
        result.final_raw,
        result.final_guard,
    )


@lru_cache(
    maxsize=None
)
def program_signature(
    program: CoreProgram,
):
    return tuple(
        observation(
            program,
            train,
            initial_raw,
        )
        for (
            train,
            initial_raw,
        ) in SAMPLES
    )


def render_instruction(
    instruction,
) -> str:
    if isinstance(
        instruction,
        CoreAcc,
    ):
        return (
            f"ACC "
            f"w={instruction.weight} "
            f"ch={instruction.channel}"
        )

    if isinstance(
        instruction,
        CoreCmp,
    ):
        return (
            f"CMP "
            f"threshold="
            f"{instruction.threshold_raw}"
        )

    if isinstance(
        instruction,
        CoreEmit,
    ):
        return (
            f"EMIT "
            f"ch={instruction.channel_out}"
        )

    if isinstance(
        instruction,
        CoreReset,
    ):
        return (
            f"RESET "
            f"value="
            f"{instruction.value_raw}"
        )

    return repr(
        instruction
    )


def render_program(
    program: CoreProgram,
) -> str:
    return "\n".join(
        f"  {pc:02d}: "
        f"{render_instruction(instruction)}"
        for pc, instruction
        in enumerate(
            program.instructions
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DepthResult:
    length: int
    syntactic_programs: int
    behavioral_classes: int
    target_matches: int


@dataclass(
    frozen=True,
    slots=True,
)
class SynthesisResult:
    minimum_length: int
    representative: CoreProgram
    minimal_programs: tuple[
        CoreProgram,
        ...,
    ]
    depth_results: tuple[
        DepthResult,
        ...,
    ]


@lru_cache(
    maxsize=1
)
def synthesize_target(
    max_length: int = 4,
) -> SynthesisResult:
    target_signature = (
        program_signature(
            TARGET_PROGRAM
        )
    )

    depth_results = []

    for length in range(
        1,
        max_length + 1,
    ):
        signatures = set()

        matches = []

        syntactic_programs = 0

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

            syntactic_programs += 1

            signatures.add(
                signature
            )

            if (
                signature
                == target_signature
            ):
                matches.append(
                    program
                )

        depth_results.append(
            DepthResult(
                length=length,
                syntactic_programs=(
                    syntactic_programs
                ),
                behavioral_classes=(
                    len(signatures)
                ),
                target_matches=(
                    len(matches)
                ),
            )
        )

        if matches:
            return SynthesisResult(
                minimum_length=length,
                representative=(
                    matches[0]
                ),
                minimal_programs=tuple(
                    matches
                ),
                depth_results=tuple(
                    depth_results
                ),
            )

    raise LookupError(
        "target behavior not synthesized "
        f"through length {max_length}"
    )


def main() -> None:
    print(
        "SPK/CORE PROGRAM SYNTHESIS v1"
    )

    print(
        f"instruction pool: "
        f"{len(INSTRUCTION_POOL)}"
    )

    print(
        f"histories: "
        f"{len(HISTORIES)}"
    )

    print(
        f"initial states: "
        f"{len(INITIAL_STATES)}"
    )

    print(
        f"behavioral samples: "
        f"{len(SAMPLES)}"
    )

    print()

    result = synthesize_target()

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
            f"target_matches="
            f"{depth.target_matches}"
        )

    print()

    print(
        f"minimum program length: "
        f"{result.minimum_length}"
    )

    print(
        f"minimal equivalent programs: "
        f"{len(result.minimal_programs)}"
    )

    print()

    print(
        "SYNTHESIZED REPRESENTATIVE"
    )

    print(
        render_program(
            result.representative
        )
    )

    print()

    print(
        "REFERENCE PROGRAM"
    )

    print(
        render_program(
            TARGET_PROGRAM
        )
    )

    print()

    print(
        "exact behavioral agreement: "
        f"{program_signature(
            result.representative
        ) == program_signature(
            TARGET_PROGRAM
        )}"
    )


if __name__ == "__main__":
    main()
