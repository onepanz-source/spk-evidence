from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.runtime import run_core_batch


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


POOL = (
    ShiftDecay(1),
    ShiftDecay(2),
    CoreAcc(0, 0),
    CoreAcc(1, 0),
    CoreCmp(0),
    CoreCmp(1),
    CoreEmit(7),
    CoreReset(0),
    CoreReset(1),
)


MAX_DEPTH = 4


RAWS = (
    0,
    1,
    2,
    3,
    7,
    15,
    31,
    63,
    127,
    128,
    254,
    255,
)


DELTAS = (
    0,
    1,
    2,
    3,
    4,
    8,
)


BATCHES = (
    (0,),
    (0, 0),
    (1,),
    (0, 1),
    (2, 2),
)


@dataclass(
    frozen=True,
    slots=True,
)
class Observation:
    status: str
    output_channels: tuple[int, ...] = ()
    final_raw: int | None = None
    final_guard: bool | None = None


def commutes_with_shift(
    instruction,
) -> bool:
    if isinstance(
        instruction,
        ShiftDecay,
    ):
        return True

    if isinstance(
        instruction,
        CoreAcc,
    ):
        return (
            instruction.weight
            == 0
        )

    if isinstance(
        instruction,
        CoreCmp,
    ):
        return (
            instruction.threshold_raw
            == 0
        )

    if isinstance(
        instruction,
        CoreEmit,
    ):
        return True

    if isinstance(
        instruction,
        CoreReset,
    ):
        return (
            instruction.value_raw
            == 0
        )

    return False


def normalize_temporal(
    program: CoreProgram,
) -> CoreProgram:
    instructions = list(
        program.instructions
    )

    #
    # Bubble every ShiftDecay left across instructions proven to
    # commute with the temporal action.
    #
    # Each swap decreases the number of commuting instructions lying
    # to the left of a shift, so termination is immediate.
    #
    changed = True

    while changed:
        changed = False

        for index in range(
            1,
            len(instructions),
        ):
            current = instructions[
                index
            ]

            previous = instructions[
                index - 1
            ]

            if not isinstance(
                current,
                ShiftDecay,
            ):
                continue

            if isinstance(
                previous,
                ShiftDecay,
            ):
                continue

            if not commutes_with_shift(
                previous
            ):
                continue

            instructions[
                index - 1
            ], instructions[
                index
            ] = (
                current,
                previous,
            )

            changed = True

    #
    # Fuse every maximal adjacent ShiftDecay run.
    #
    fused = []

    for instruction in instructions:
        if (
            isinstance(
                instruction,
                ShiftDecay,
            )
            and fused
            and isinstance(
                fused[-1],
                ShiftDecay,
            )
        ):
            fused[-1] = ShiftDecay(
                fused[-1].bits_per_tick
                + instruction.bits_per_tick
            )

        else:
            fused.append(
                instruction
            )

    return CoreProgram(
        tuple(fused)
    )


def is_temporal_normal_form(
    program: CoreProgram,
) -> bool:
    instructions = (
        program.instructions
    )

    for index in range(
        1,
        len(instructions),
    ):
        previous = instructions[
            index - 1
        ]

        current = instructions[
            index
        ]

        #
        # Adjacent shifts should already be fused.
        #
        if (
            isinstance(
                previous,
                ShiftDecay,
            )
            and isinstance(
                current,
                ShiftDecay,
            )
        ):
            return False

        #
        # If a commuting instruction precedes a shift, the shift could
        # still move left.
        #
        if (
            isinstance(
                current,
                ShiftDecay,
            )
            and not isinstance(
                previous,
                ShiftDecay,
            )
            and commutes_with_shift(
                previous
            )
        ):
            return False

    return True


def observe(
    program: CoreProgram,
    *,
    raw: int,
    delta: int,
    channels: tuple[int, ...],
) -> Observation:
    try:
        result = run_core_batch(
            CONFIG,
            program,
            timestamp=delta,
            channels=channels,
            initial_raw=raw,
            previous_timestamp=0,
        )

    except OverflowError:
        return Observation(
            status="overflow"
        )

    return Observation(
        status="ok",
        output_channels=tuple(
            channel
            for _, channel
            in result.output.as_pairs()
        ),
        final_raw=result.final_raw,
        final_guard=result.final_guard,
    )


def programs():
    for depth in range(
        1,
        MAX_DEPTH + 1,
    ):
        yield from (
            CoreProgram(
                tuple(items)
            )
            for items in product(
                POOL,
                repeat=depth,
            )
        )


def program_key(
    program: CoreProgram,
):
    return repr(
        program.instructions
    )


def main() -> None:
    print(
        "SPK CORE TEMPORAL NORMALIZATION v0"
    )

    print(
        f"instruction pool: "
        f"{len(POOL)}"
    )

    print(
        f"maximum depth: "
        f"{MAX_DEPTH}"
    )

    expected_syntactic = sum(
        len(POOL) ** depth
        for depth in range(
            1,
            MAX_DEPTH + 1,
        )
    )

    print(
        f"expected syntactic programs: "
        f"{expected_syntactic}"
    )

    print()

    syntactic = 0
    changed_programs = 0

    idempotence_failures = 0
    normal_form_failures = 0
    observation_mismatches = 0

    observation_cases = 0

    normal_forms = set()

    first_failure = None

    for program in programs():
        syntactic += 1

        normalized = normalize_temporal(
            program
        )

        normal_forms.add(
            program_key(
                normalized
            )
        )

        if (
            normalized.instructions
            != program.instructions
        ):
            changed_programs += 1

        normalized_again = (
            normalize_temporal(
                normalized
            )
        )

        if (
            normalized_again.instructions
            != normalized.instructions
        ):
            idempotence_failures += 1

            if first_failure is None:
                first_failure = (
                    "idempotence",
                    program,
                    normalized,
                    normalized_again,
                )

        if not is_temporal_normal_form(
            normalized
        ):
            normal_form_failures += 1

            if first_failure is None:
                first_failure = (
                    "normal-form",
                    program,
                    normalized,
                )

        for raw in RAWS:
            for delta in DELTAS:
                for channels in BATCHES:
                    source = observe(
                        program,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    target = observe(
                        normalized,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    observation_cases += 1

                    if source == target:
                        continue

                    observation_mismatches += 1

                    if first_failure is None:
                        first_failure = (
                            "semantic",
                            program,
                            normalized,
                            raw,
                            delta,
                            channels,
                            source,
                            target,
                        )

        if (
            syntactic % 1000
            == 0
        ):
            print(
                f"programs={syntactic:5d} "
                f"changed={changed_programs:5d} "
                f"normal_forms="
                f"{len(normal_forms):5d} "
                f"cases="
                f"{observation_cases:8d} "
                f"mismatches="
                f"{observation_mismatches}"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "FINITE NORMALIZATION CENSUS"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"changed programs: "
        f"{changed_programs}"
    )

    print(
        f"distinct temporal normal forms: "
        f"{len(normal_forms)}"
    )

    print(
        f"syntactic collapse: "
        f"{syntactic - len(normal_forms)}"
    )

    print()
    print(
        f"observation cases: "
        f"{observation_cases}"
    )

    print(
        f"observation mismatches: "
        f"{observation_mismatches}"
    )

    print(
        f"idempotence failures: "
        f"{idempotence_failures}"
    )

    print(
        f"normal-form structural failures: "
        f"{normal_form_failures}"
    )

    if first_failure is not None:
        print()
        print(
            "FIRST FAILURE"
        )

        print(
            first_failure
        )

        raise SystemExit(1)

    print()
    print(
        "=" * 88
    )
    print(
        "CHECKPOINT"
    )
    print(
        "=" * 88
    )

    print(
        "temporal normalization "
        "observation mismatches: 0"
    )

    print(
        "temporal normalization "
        "idempotence failures: 0"
    )

    print(
        "temporal normal-form "
        "structural failures: 0"
    )

    print()
    print(
        "TEMPORAL REGION "
        "NORMALIZATION CHECKPOINT: PASS"
    )

    print()
    print(
        "Scope:"
    )

    print(
        "- nine-instruction finite pool"
    )

    print(
        "- program depth <= 4"
    )

    print(
        "- 8-bit unsigned Core"
    )

    print(
        "- overflow included as observable"
    )

    print(
        "- finite raw/delta/batch corpus"
    )

    print(
        "- no universal completeness claim"
    )


if __name__ == "__main__":
    main()
