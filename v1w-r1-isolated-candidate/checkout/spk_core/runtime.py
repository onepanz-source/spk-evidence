from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from spk.event import SpikeTrain

from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


@dataclass(
    frozen=True,
    slots=True,
)
class CoreResult:
    output: SpikeTrain
    final_raw: int
    final_guard: bool
    last_timestamp: int

    def final_value(
        self,
        config: CoreConfig,
    ) -> float:
        return (
            self.final_raw
            / config.scale
        )


def _batches(
    train: SpikeTrain,
):
    current_timestamp = None
    channels = []

    for timestamp, channel in train.as_pairs():
        if (
            current_timestamp is not None
            and timestamp
            != current_timestamp
        ):
            yield (
                current_timestamp,
                tuple(channels),
            )

            channels = []

        current_timestamp = timestamp

        channels.append(
            channel
        )

    if current_timestamp is not None:
        yield (
            current_timestamp,
            tuple(channels),
        )


def _check_state(
    config: CoreConfig,
    raw: int,
) -> None:
    if not (
        0 <= raw <= config.max_raw
    ):
        raise OverflowError(
            f"core state overflow: "
            f"{raw} not in "
            f"[0,{config.max_raw}]"
        )


def run_core_batch(
    config: CoreConfig,
    program: CoreProgram,
    *,
    timestamp: int,
    channels: Iterable[int],
    initial_raw: int = 0,
    previous_timestamp: int = 0,
) -> CoreResult:
    """
    Execute exactly one non-empty event batch.

    The batch uses one shared temporal delta and one shared
    channel-count map for every instruction in the program.

    Guard is transient and therefore starts false for each batch.
    """

    _check_state(
        config,
        initial_raw,
    )

    if timestamp < previous_timestamp:
        raise ValueError(
            "non-monotonic timestamp"
        )

    channels = tuple(
        channels
    )

    if not channels:
        raise ValueError(
            "core batch must contain at least one event"
        )

    raw = initial_raw
    guard = False

    delta_ticks = (
        timestamp
        - previous_timestamp
    )

    counts = Counter(
        channels
    )

    total_count = len(
        channels
    )

    outputs = []

    for instruction in (
        program.instructions
    ):
        if isinstance(
            instruction,
            ShiftDecay,
        ):
            shift = (
                instruction.bits_per_tick
                * delta_ticks
            )

            raw >>= shift

        elif isinstance(
            instruction,
            CoreAcc,
        ):
            if instruction.channel is None:
                count = total_count
            else:
                count = counts[
                    instruction.channel
                ]

            raw += (
                count
                * instruction.weight
                * config.scale
            )

            _check_state(
                config,
                raw,
            )

        elif isinstance(
            instruction,
            CoreCmp,
        ):
            guard = (
                raw
                >= instruction.threshold_raw
            )

        elif isinstance(
            instruction,
            CoreEmit,
        ):
            if guard:
                outputs.append(
                    (
                        timestamp,
                        instruction.channel_out,
                    )
                )

        elif isinstance(
            instruction,
            CoreReset,
        ):
            if guard:
                raw = (
                    instruction.value_raw
                )

                _check_state(
                    config,
                    raw,
                )

        else:
            raise TypeError(
                f"unknown core instruction: "
                f"{instruction!r}"
            )

    return CoreResult(
        output=SpikeTrain.from_pairs(
            outputs
        ),
        final_raw=raw,
        final_guard=guard,
        last_timestamp=timestamp,
    )


def run_core_program(
    config: CoreConfig,
    program: CoreProgram,
    train: SpikeTrain,
    *,
    initial_raw: int = 0,
) -> CoreResult:
    _check_state(
        config,
        initial_raw,
    )

    raw = initial_raw
    guard = False
    previous_timestamp = 0

    outputs = []

    for (
        timestamp,
        channels,
    ) in _batches(train):
        result = run_core_batch(
            config,
            program,
            timestamp=timestamp,
            channels=channels,
            initial_raw=raw,
            previous_timestamp=previous_timestamp,
        )

        raw = result.final_raw
        guard = result.final_guard
        previous_timestamp = (
            result.last_timestamp
        )

        outputs.extend(
            result.output.as_pairs()
        )

    return CoreResult(
        output=SpikeTrain.from_pairs(
            outputs
        ),
        final_raw=raw,
        final_guard=guard,
        last_timestamp=previous_timestamp,
    )
