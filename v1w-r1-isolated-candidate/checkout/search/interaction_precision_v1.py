from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Callable

from spk.event import SpikeTrain
from spk.operators import Acc, Decay
from spk.program import Program
from spk.runner import run_program


MAX_TIMESTAMP = 16


RoundFunction = Callable[[float], float]


@dataclass(
    frozen=True,
    slots=True,
)
class PrecisionProfile:
    name: str
    round_value: RoundFunction
    description: str


PROGRAM = Program(
    (
        Decay(
            tau=1.0,
        ),
        Acc(
            weight=1.0,
            channel=0,
        ),
    )
)


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
        name="FIXED_F4",
        round_value=fixed_rounder(4),
        description="fixed lattice, 4 fractional bits",
    ),
    PrecisionProfile(
        name="FIXED_F6",
        round_value=fixed_rounder(6),
        description="fixed lattice, 6 fractional bits",
    ),
    PrecisionProfile(
        name="FIXED_F8",
        round_value=fixed_rounder(8),
        description="fixed lattice, 8 fractional bits",
    ),
    PrecisionProfile(
        name="FIXED_F10",
        round_value=fixed_rounder(10),
        description="fixed lattice, 10 fractional bits",
    ),
    PrecisionProfile(
        name="FIXED_F12",
        round_value=fixed_rounder(12),
        description="fixed lattice, 12 fractional bits",
    ),
    PrecisionProfile(
        name="FIXED_F16",
        round_value=fixed_rounder(16),
        description="fixed lattice, 16 fractional bits",
    ),
    PrecisionProfile(
        name="FLOAT16",
        round_value=float16,
        description="IEEE-754 binary16-like rounding",
    ),
    PrecisionProfile(
        name="FLOAT32",
        round_value=float32,
        description="IEEE-754 binary32-like rounding",
    ),
    PrecisionProfile(
        name="FLOAT64",
        round_value=identity,
        description="current Python/runtime arithmetic",
    ),
)


def event_timestamps(
    prefix_mask: int,
    final_timestamp: int,
) -> tuple[int, ...]:
    """
    Construct a binary event history.

    Bits 0 .. final_timestamp-1 are taken from prefix_mask.

    The final timestamp always contains an event.

    This makes T observable as the last event time and gives exactly:

        2**T

    histories for each T.
    """

    result = []

    for timestamp in range(
        final_timestamp
    ):
        if (
            prefix_mask
            & (1 << timestamp)
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


def simulate_quantized(
    timestamps: tuple[int, ...],
    round_value: RoundFunction,
) -> float:
    """
    Event-driven simulation of:

        DECAY(tau=1)
        ACC(1, channel=0)

    with x0=1.

    Rounding is applied to:
      * the stored state,
      * the decay factor,
      * the decay result,
      * the accumulation result.

    No updates occur during empty ticks; elapsed time is accumulated
    exactly as in the SPK runner.
    """

    x = round_value(
        1.0
    )

    previous_timestamp = 0

    for timestamp in timestamps:
        delta = (
            timestamp
            - previous_timestamp
        )

        factor = round_value(
            math.exp(
                -float(delta)
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


def simulate_runtime_float64(
    timestamps: tuple[int, ...],
) -> float:
    train = SpikeTrain.from_pairs(
        (
            timestamp,
            0,
        )
        for timestamp
        in timestamps
    )

    result = run_program(
        PROGRAM,
        train,
        initial_x=1.0,
    )

    return result.final_state[0]


@dataclass(
    frozen=True,
    slots=True,
)
class Collision:
    timestamp: int
    encoded_value: float
    first_mask: int
    second_mask: int


def find_first_collision(
    profile: PrecisionProfile,
) -> tuple[
    int,
    Collision | None,
]:
    last_collision_free = -1

    for final_timestamp in range(
        MAX_TIMESTAMP + 1
    ):
        seen: dict[
            float,
            int,
        ] = {}

        history_count = (
            1 << final_timestamp
        )

        for prefix_mask in range(
            history_count
        ):
            timestamps = (
                event_timestamps(
                    prefix_mask,
                    final_timestamp,
                )
            )

            encoded = (
                simulate_quantized(
                    timestamps,
                    profile.round_value,
                )
            )

            previous = seen.get(
                encoded
            )

            if previous is not None:
                return (
                    last_collision_free,
                    Collision(
                        timestamp=(
                            final_timestamp
                        ),
                        encoded_value=encoded,
                        first_mask=previous,
                        second_mask=prefix_mask,
                    ),
                )

            seen[
                encoded
            ] = prefix_mask

        last_collision_free = (
            final_timestamp
        )

    return (
        last_collision_free,
        None,
    )


def render_history(
    mask: int,
    final_timestamp: int,
) -> str:
    timestamps = event_timestamps(
        mask,
        final_timestamp,
    )

    return (
        "{"
        + ", ".join(
            str(timestamp)
            for timestamp
            in timestamps
        )
        + "}"
    )


def verify_float64_model() -> None:
    samples = (
        (0,),
        (1,),
        (0, 1),
        (0, 2),
        (1, 3),
        (0, 2, 5),
        (0, 1, 4, 7),
    )

    for timestamps in samples:
        simulated = (
            simulate_quantized(
                timestamps,
                identity,
            )
        )

        runtime = (
            simulate_runtime_float64(
                timestamps
            )
        )

        if simulated != runtime:
            raise AssertionError(
                (
                    "float64 simulator/runtime mismatch: "
                    f"{timestamps}: "
                    f"{simulated!r} != {runtime!r}"
                )
            )


def main() -> None:
    verify_float64_model()

    print(
        "FLOAT64_MODEL_MATCHES_RUNTIME"
    )

    print()

    print(
        "Single-channel temporal encoding:"
    )

    print(
        "  x0 = 1"
    )

    print(
        "  DECAY(tau=1) -> "
        "ACC(weight=1, channel=0)"
    )

    print(
        "  binary event multiplicity"
    )

    print(
        "  final timestamp always occupied"
    )

    print(
        f"  search horizon: "
        f"T <= {MAX_TIMESTAMP}"
    )

    print()

    results = []

    for profile in PROFILES:
        (
            last_safe,
            collision,
        ) = find_first_collision(
            profile
        )

        results.append(
            (
                profile,
                last_safe,
                collision,
            )
        )

        if collision is None:
            collision_text = (
                f"none through "
                f"T={MAX_TIMESTAMP}"
            )
        else:
            collision_text = (
                f"T={collision.timestamp}"
            )

        print(
            f"{profile.name:10s} "
            f"last_collision_free="
            f"{last_safe:2d} "
            f"first_collision="
            f"{collision_text}"
        )

    print()
    print(
        "FIRST COLLISION EXAMPLES"
    )

    for (
        profile,
        _,
        collision,
    ) in results:
        if collision is None:
            continue

        print()

        print(
            profile.name
        )

        print(
            f"  {profile.description}"
        )

        print(
            f"  T="
            f"{collision.timestamp}"
        )

        print(
            f"  encoded="
            f"{collision.encoded_value!r}"
        )

        print(
            "  history A:",
            render_history(
                collision.first_mask,
                collision.timestamp,
            ),
        )

        print(
            "  history B:",
            render_history(
                collision.second_mask,
                collision.timestamp,
            ),
        )

    print()
    print(
        "CAPACITY INTERPRETATION"
    )

    print(
        "  At fixed final timestamp T there are 2**T "
        "possible binary histories."
    )

    print(
        "  Collision-free through T therefore means at least "
        "T bits of temporal-history discrimination "
        "for this restricted experiment."
    )


if __name__ == "__main__":
    main()
