from __future__ import annotations

from search.interaction_packed_core_v1 import (
    CoreConfig as PackedConfig,
)

from .isa import (
    CoreAcc,
    CoreConfig,
    CoreProgram,
    ShiftDecay,
)


def lower_packed_core(
    packed: PackedConfig,
) -> tuple[
    CoreConfig,
    CoreProgram,
]:
    config = CoreConfig(
        state_bits=(
            packed.word_bits
        ),
        fractional_bits=(
            packed.fractional_bits
        ),
    )

    instructions = [
        ShiftDecay(
            bits_per_tick=(
                packed.bits_per_tick
            )
        )
    ]

    for channel in range(
        packed.channels
    ):
        weight = (
            1
            << (
                channel
                * packed.bits_per_channel
            )
        )

        instructions.append(
            CoreAcc(
                weight=weight,
                channel=channel,
            )
        )

    return (
        config,
        CoreProgram(
            tuple(
                instructions
            )
        ),
    )
