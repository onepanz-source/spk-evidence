from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class CoreConfig:
    state_bits: int
    fractional_bits: int

    def __post_init__(self):
        if self.state_bits < 1:
            raise ValueError(
                "state_bits must be positive"
            )

        if not (
            0 <= self.fractional_bits
            < self.state_bits
        ):
            raise ValueError(
                "fractional_bits must satisfy "
                "0 <= F < state_bits"
            )

    @property
    def scale(self) -> int:
        return (
            1 << self.fractional_bits
        )

    @property
    def max_raw(self) -> int:
        return (
            (1 << self.state_bits)
            - 1
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShiftDecay:
    """
    Dyadic temporal decay:

        raw >>= bits_per_tick * delta_ticks
    """

    bits_per_tick: int

    def __post_init__(self):
        if self.bits_per_tick < 0:
            raise ValueError(
                "bits_per_tick must be nonnegative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class CoreAcc:
    """
    Add:

        count(channel) * weight

    in the integer part of the fixed-point register.
    """

    weight: int
    channel: int | None

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError(
                "Core v0 supports nonnegative weights"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class CoreCmp:
    threshold_raw: int


@dataclass(
    frozen=True,
    slots=True,
)
class CoreEmit:
    channel_out: int


@dataclass(
    frozen=True,
    slots=True,
)
class CoreReset:
    value_raw: int


CoreInstruction = (
    ShiftDecay
    | CoreAcc
    | CoreCmp
    | CoreEmit
    | CoreReset
)


@dataclass(
    frozen=True,
    slots=True,
)
class CoreProgram:
    instructions: tuple[
        CoreInstruction,
        ...,
    ]
