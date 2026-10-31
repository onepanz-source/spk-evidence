from __future__ import annotations

from dataclasses import dataclass

from spk_core.isa import (
    CoreCmp,
    CoreConfig,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.runtime import run_core_batch


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


SHIFT_RATES = (
    1,
    2,
)


DELTAS = (
    0,
    1,
    2,
    8,
)


@dataclass(
    frozen=True,
    slots=True,
)
class Observation:
    status: str
    final_raw: int | None = None
    final_guard: bool | None = None


def observe(
    program,
    *,
    raw,
    delta,
):
    try:
        result = run_core_batch(
            CONFIG,
            program,
            timestamp=delta,
            channels=(0,),
            initial_raw=raw,
            previous_timestamp=0,
        )

    except OverflowError:
        return Observation(
            status="overflow"
        )

    return Observation(
        status="ok",
        final_raw=result.final_raw,
        final_guard=result.final_guard,
    )


def programs(
    threshold,
    shift_rate,
    reset_value,
):
    with_shift = CoreProgram(
        (
            CoreCmp(threshold),
            ShiftDecay(
                shift_rate
            ),
            CoreReset(
                reset_value
            ),
        )
    )

    without_shift = CoreProgram(
        (
            CoreCmp(threshold),
            CoreReset(
                reset_value
            ),
        )
    )

    return (
        with_shift,
        without_shift,
    )


def main():
    print(
        "SPK CORE GUARDED "
        "TEMPORAL OVERWRITE v0"
    )

    #
    # First determine, for every 8-bit threshold, whether
    #
    #   CMP(t); SHIFT(k); RESET(1)
    #
    # equals
    #
    #   CMP(t); RESET(1)
    #
    # on the complete raw-state domain.
    #
    supported_thresholds = []

    checks = 0
    mismatches = 0

    first_counterexample = {}

    for threshold in range(
        CONFIG.max_raw + 1
    ):
        supported = True

        for shift_rate in (
            SHIFT_RATES
        ):
            (
                with_shift,
                without_shift,
            ) = programs(
                threshold,
                shift_rate,
                1,
            )

            for raw in range(
                CONFIG.max_raw + 1
            ):
                for delta in DELTAS:
                    left = observe(
                        with_shift,
                        raw=raw,
                        delta=delta,
                    )

                    right = observe(
                        without_shift,
                        raw=raw,
                        delta=delta,
                    )

                    checks += 1

                    if left == right:
                        continue

                    supported = False
                    mismatches += 1

                    first_counterexample.setdefault(
                        threshold,
                        (
                            shift_rate,
                            raw,
                            delta,
                            left,
                            right,
                        ),
                    )

        if supported:
            supported_thresholds.append(
                threshold
            )

    print()
    print(
        "=" * 88
    )
    print(
        "THRESHOLD CLASSIFICATION"
    )
    print(
        "=" * 88
    )

    print(
        f"cases checked: "
        f"{checks}"
    )

    print(
        f"supported thresholds: "
        f"{supported_thresholds}"
    )

    expected = [
        0,
        1,
    ]

    print(
        f"expected: "
        f"{expected}"
    )

    if (
        supported_thresholds
        != expected
    ):
        print(
            "threshold classification "
            "FAILED"
        )

        raise SystemExit(1)

    print(
        "threshold classification: PASS"
    )

    print()
    print(
        "first refuting examples:"
    )

    for threshold in (
        2,
        3,
        128,
        255,
    ):
        witness = (
            first_counterexample[
                threshold
            ]
        )

        print(
            f"    threshold="
            f"{threshold}: "
            f"{witness}"
        )

    #
    # Verify that the valid t=0/1 law does not depend on reset value.
    #
    print()
    print(
        "=" * 88
    )
    print(
        "RESET-VALUE INDEPENDENCE"
    )
    print(
        "=" * 88
    )

    reset_checks = 0

    for threshold in (
        0,
        1,
    ):
        for reset_value in range(
            CONFIG.max_raw + 1
        ):
            for shift_rate in (
                SHIFT_RATES
            ):
                (
                    with_shift,
                    without_shift,
                ) = programs(
                    threshold,
                    shift_rate,
                    reset_value,
                )

                for raw in range(
                    CONFIG.max_raw + 1
                ):
                    for delta in DELTAS:
                        left = observe(
                            with_shift,
                            raw=raw,
                            delta=delta,
                        )

                        right = observe(
                            without_shift,
                            raw=raw,
                            delta=delta,
                        )

                        reset_checks += 1

                        if left != right:
                            print(
                                "RESET-VALUE FAILURE"
                            )

                            print(
                                f"threshold="
                                f"{threshold}"
                            )

                            print(
                                f"reset="
                                f"{reset_value}"
                            )

                            print(
                                f"shift="
                                f"{shift_rate}"
                            )

                            print(
                                f"raw="
                                f"{raw}"
                            )

                            print(
                                f"delta="
                                f"{delta}"
                            )

                            print(
                                f"with="
                                f"{left}"
                            )

                            print(
                                f"without="
                                f"{right}"
                            )

                            raise SystemExit(
                                1
                            )

    print(
        f"cases checked: "
        f"{reset_checks}"
    )

    print(
        "mismatches: 0"
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
        "CMP(0);SHIFT(k);RESET(v)"
    )

    print(
        "    -> CMP(0);RESET(v)"
    )

    print(
        "CMP(1);SHIFT(k);RESET(v)"
    )

    print(
        "    -> CMP(1);RESET(v)"
    )

    print(
        "CMP(t>1): refuted"
    )

    print()
    print(
        "GUARDED TEMPORAL OVERWRITE "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
