from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Callable


MAX_TIMESTAMP = 16


RoundFunction = Callable[[float], float]


@dataclass(
    frozen=True,
    slots=True,
)
class PrecisionProfile:
    name: str
    round_value: RoundFunction


def identity(
    value: float,
) -> float:
    return float(value)


def float32(
    value: float,
) -> float:
    return struct.unpack(
        ">f",
        struct.pack(
            ">f",
            float(value),
        ),
    )[0]


def float16(
    value: float,
) -> float:
    return struct.unpack(
        ">e",
        struct.pack(
            ">e",
            float(value),
        ),
    )[0]


def fixed_rounder(
    fractional_bits: int,
) -> RoundFunction:
    scale = float(
        1 << fractional_bits
    )

    def round_value(
        value: float,
    ) -> float:
        return (
            round(
                value * scale
            )
            / scale
        )

    return round_value


PROFILES = (
    PrecisionProfile(
        "FIXED_F4",
        fixed_rounder(4),
    ),
    PrecisionProfile(
        "FIXED_F6",
        fixed_rounder(6),
    ),
    PrecisionProfile(
        "FIXED_F8",
        fixed_rounder(8),
    ),
    PrecisionProfile(
        "FIXED_F10",
        fixed_rounder(10),
    ),
    PrecisionProfile(
        "FIXED_F12",
        fixed_rounder(12),
    ),
    PrecisionProfile(
        "FIXED_F16",
        fixed_rounder(16),
    ),
    PrecisionProfile(
        "FLOAT16",
        float16,
    ),
    PrecisionProfile(
        "FLOAT32",
        float32,
    ),
    PrecisionProfile(
        "FLOAT64",
        identity,
    ),
)


def timestamps_from_mask(
    mask: int,
    final_timestamp: int,
) -> tuple[int, ...]:
    result = []

    for timestamp in range(
        final_timestamp
    ):
        if mask & (
            1 << timestamp
        ):
            result.append(
                timestamp
            )

    result.append(
        final_timestamp
    )

    return tuple(
        result
    )


def simulate(
    *,
    timestamps: tuple[int, ...],
    round_value: RoundFunction,
    decay_factor,
) -> float:
    #
    # No temporal anchor here.
    #
    # The final timestamp T is considered known externally.
    #
    x = round_value(
        0.0
    )

    previous_timestamp = 0

    for timestamp in timestamps:
        delta = (
            timestamp
            - previous_timestamp
        )

        factor = round_value(
            decay_factor(
                delta
            )
        )

        x = round_value(
            x * factor
        )

        x = round_value(
            x + 1.0
        )

        previous_timestamp = (
            timestamp
        )

    return x


def exponential_factor(
    delta: int,
) -> float:
    return math.exp(
        -float(delta)
    )


def dyadic_factor(
    delta: int,
) -> float:
    #
    # Exact binary power:
    #
    #     2 ** (-delta)
    #
    return math.ldexp(
        1.0,
        -delta,
    )


def first_collision(
    profile,
    decay_factor,
):
    last_safe = -1

    for final_timestamp in range(
        MAX_TIMESTAMP + 1
    ):
        seen = {}

        for mask in range(
            1 << final_timestamp
        ):
            timestamps = (
                timestamps_from_mask(
                    mask,
                    final_timestamp,
                )
            )

            value = simulate(
                timestamps=timestamps,
                round_value=(
                    profile.round_value
                ),
                decay_factor=(
                    decay_factor
                ),
            )

            if value in seen:
                return (
                    last_safe,
                    final_timestamp,
                    seen[value],
                    mask,
                    value,
                )

            seen[value] = mask

        last_safe = (
            final_timestamp
        )

    return (
        last_safe,
        None,
        None,
        None,
        None,
    )


def history(
    mask,
    final_timestamp,
):
    return timestamps_from_mask(
        mask,
        final_timestamp,
    )


def main() -> None:
    models = (
        (
            "EXP_q=e^-1",
            exponential_factor,
        ),
        (
            "DYADIC_q=1/2",
            dyadic_factor,
        ),
    )

    for (
        model_name,
        factor,
    ) in models:
        print()
        print(
            "=" * 72
        )

        print(
            model_name
        )

        print(
            "=" * 72
        )

        for profile in PROFILES:
            (
                last_safe,
                collision_t,
                mask_a,
                mask_b,
                value,
            ) = first_collision(
                profile,
                factor,
            )

            if collision_t is None:
                print(
                    f"{profile.name:10s} "
                    f"safe through "
                    f"T={last_safe:2d}"
                )
                continue

            print(
                f"{profile.name:10s} "
                f"safe={last_safe:2d} "
                f"collision={collision_t:2d} "
                f"value={value!r}"
            )

            print(
                "  A:",
                history(
                    mask_a,
                    collision_t,
                ),
            )

            print(
                "  B:",
                history(
                    mask_b,
                    collision_t,
                ),
            )


if __name__ == "__main__":
    main()
