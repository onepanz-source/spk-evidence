from __future__ import annotations

from dataclasses import dataclass

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


BODY = (
    CoreAcc(16, 0),
    CoreCmp(19),
    CoreEmit(7),
    CoreReset(0),
)


PROGRAMS = {
    #
    # Candidate normalizable forms.
    #
    "prefix_shift1": CoreProgram(
        (
            ShiftDecay(1),
            *BODY,
        )
    ),

    "prefix_shift2": CoreProgram(
        (
            ShiftDecay(2),
            *BODY,
        )
    ),

    #
    # Two temporal prefix operations should fuse:
    #
    #     (x >> delta) >> (2*delta)
    #         =
    #     x >> (3*delta)
    #
    "prefix_shift1_shift2": CoreProgram(
        (
            ShiftDecay(1),
            ShiftDecay(2),
            *BODY,
        )
    ),

    #
    # Position probes.
    #
    "after_acc": CoreProgram(
        (
            CoreAcc(16, 0),
            ShiftDecay(1),
            CoreCmp(19),
            CoreEmit(7),
            CoreReset(0),
        )
    ),

    "after_cmp": CoreProgram(
        (
            CoreAcc(16, 0),
            CoreCmp(19),
            ShiftDecay(1),
            CoreEmit(7),
            CoreReset(0),
        )
    ),

    "after_emit": CoreProgram(
        (
            CoreAcc(16, 0),
            CoreCmp(19),
            CoreEmit(7),
            ShiftDecay(1),
            CoreReset(0),
        )
    ),

    "after_reset": CoreProgram(
        (
            CoreAcc(16, 0),
            CoreCmp(19),
            CoreEmit(7),
            CoreReset(0),
            ShiftDecay(1),
        )
    ),
}


EXPECTED_ABSORPTION = {
    "prefix_shift1": True,
    "prefix_shift2": True,
    "prefix_shift1_shift2": True,

    "after_acc": False,
    "after_cmp": False,
    "after_emit": False,
    "after_reset": False,
}


INITIAL_RAWS = range(
    CONFIG.max_raw + 1
)


AGES = range(
    0,
    9,
)


MULTIPLICITIES = (
    1,
    2,
)


@dataclass(
    frozen=True,
    slots=True,
)
class Observation:
    status: str

    output_channels: tuple[int, ...] = ()

    final_guard: bool | None = None

    next_effective_raw: int | None = None


def total_shift_rate(
    program: CoreProgram,
) -> int:
    return sum(
        instruction.bits_per_tick
        for instruction
        in program.instructions
        if isinstance(
            instruction,
            ShiftDecay,
        )
    )


def execute_and_project(
    program: CoreProgram,
    *,
    initial_raw: int,
    delta: int,
    multiplicity: int,
    post_tick_shift: int,
) -> Observation:
    channels = (
        (0,)
        * multiplicity
    )

    try:
        result = run_core_batch(
            CONFIG,
            program,
            timestamp=delta,
            channels=channels,
            initial_raw=initial_raw,
            previous_timestamp=0,
        )

    except OverflowError:
        return Observation(
            status="overflow"
        )

    output_channels = tuple(
        channel
        for _, channel
        in result.output.as_pairs()
    )

    next_raw = (
        result.final_raw
        >> post_tick_shift
    )

    return Observation(
        status="ok",
        output_channels=output_channels,
        final_guard=result.final_guard,
        next_effective_raw=next_raw,
    )


def lazy_transition(
    program: CoreProgram,
    *,
    raw: int,
    age: int,
    multiplicity: int,
) -> Observation:
    rate = total_shift_rate(
        program
    )

    #
    # Lazy representation:
    #
    # raw was retained at the last event.
    # The full elapsed age is presented to ShiftDecay now.
    #
    return execute_and_project(
        program,
        initial_raw=raw,
        delta=age,
        multiplicity=multiplicity,
        post_tick_shift=rate,
    )


def eager_transition(
    program: CoreProgram,
    *,
    raw: int,
    age: int,
    multiplicity: int,
) -> Observation:
    rate = total_shift_rate(
        program
    )

    #
    # Candidate quotient:
    #
    # elapsed time has already been absorbed into raw.
    #
    effective_raw = (
        raw
        >> (
            rate
            * age
        )
    )

    #
    # Therefore every ShiftDecay sees delta=0 at the event.
    #
    return execute_and_project(
        program,
        initial_raw=effective_raw,
        delta=0,
        multiplicity=multiplicity,
        post_tick_shift=rate,
    )


def audit_program(
    name: str,
    program: CoreProgram,
):
    checks = 0

    first_mismatch = None

    for raw in INITIAL_RAWS:
        for age in AGES:
            for multiplicity in (
                MULTIPLICITIES
            ):
                lazy = lazy_transition(
                    program,
                    raw=raw,
                    age=age,
                    multiplicity=multiplicity,
                )

                eager = eager_transition(
                    program,
                    raw=raw,
                    age=age,
                    multiplicity=multiplicity,
                )

                checks += 1

                if lazy == eager:
                    continue

                if first_mismatch is None:
                    first_mismatch = (
                        raw,
                        age,
                        multiplicity,
                        lazy,
                        eager,
                    )

    return (
        checks,
        first_mismatch,
    )


def main() -> None:
    print(
        "SPK CORE TEMPORAL "
        "ABSORPTION BOUNDARY v0"
    )

    print(
        "candidate quotient:"
    )

    print(
        "    effective_raw = "
        "raw >> (total_shift_rate * age)"
    )

    print()

    total_checks = 0

    classification_errors = 0

    for (
        name,
        program,
    ) in PROGRAMS.items():
        (
            checks,
            mismatch,
        ) = audit_program(
            name,
            program,
        )

        total_checks += checks

        supported = (
            mismatch is None
        )

        expected = (
            EXPECTED_ABSORPTION[
                name
            ]
        )

        classification_ok = (
            supported
            == expected
        )

        if not classification_ok:
            classification_errors += 1

        print(
            "=" * 88
        )

        print(
            name
        )

        print(
            f"shift rate total: "
            f"{total_shift_rate(program)}"
        )

        print(
            f"cases checked: "
            f"{checks}"
        )

        print(
            f"absorption supported: "
            f"{supported}"
        )

        print(
            f"expected: "
            f"{expected}"
        )

        print(
            f"classification correct: "
            f"{classification_ok}"
        )

        if mismatch is not None:
            (
                raw,
                age,
                multiplicity,
                lazy,
                eager,
            ) = mismatch

            print()

            print(
                "first counterexample:"
            )

            print(
                f"    raw="
                f"{raw}"
            )

            print(
                f"    age="
                f"{age}"
            )

            print(
                f"    multiplicity="
                f"{multiplicity}"
            )

            print(
                f"    lazy="
                f"{lazy}"
            )

            print(
                f"    eager="
                f"{eager}"
            )

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
        f"total concrete cases: "
        f"{total_checks}"
    )

    print(
        f"classification errors: "
        f"{classification_errors}"
    )

    if classification_errors:
        raise SystemExit(1)

    print()
    print(
        "PREFIX TEMPORAL ABSORPTION: "
        "SUPPORTED"
    )

    print(
        "NON-PREFIX ABSORPTION: "
        "REFUTED ON DECLARED PROBES"
    )

    print()

    print(
        "No universal theorem is claimed "
        "by this finite audit."
    )


if __name__ == "__main__":
    main()
