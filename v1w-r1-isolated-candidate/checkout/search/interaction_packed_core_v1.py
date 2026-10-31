from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product


@dataclass(
    frozen=True,
    slots=True,
)
class CoreConfig:
    channels: int
    max_multiplicity: int
    fractional_bits: int

    @property
    def bits_per_channel(self) -> int:
        return max(
            1,
            math.ceil(
                math.log2(
                    self.max_multiplicity
                    + 1
                )
            ),
        )

    @property
    def bits_per_tick(self) -> int:
        return (
            self.channels
            * self.bits_per_channel
        )

    @property
    def history_ticks(self) -> int:
        return (
            self.fractional_bits
            // self.bits_per_tick
        )

    @property
    def word_bits(self) -> int:
        #
        # Integer part stores the current temporal digit.
        #
        return (
            self.fractional_bits
            + self.bits_per_tick
        )


def channel_weight(
    config: CoreConfig,
    channel: int,
) -> int:
    if not (
        0 <= channel < config.channels
    ):
        raise ValueError(
            "invalid channel"
        )

    return (
        1
        << (
            channel
            * config.bits_per_channel
        )
    )


def pack_batch(
    config: CoreConfig,
    multiplicities: tuple[int, ...],
) -> int:
    if len(
        multiplicities
    ) != config.channels:
        raise ValueError(
            "wrong channel count"
        )

    digit = 0

    for channel, count in enumerate(
        multiplicities
    ):
        if not (
            0
            <= count
            <= config.max_multiplicity
        ):
            raise ValueError(
                "multiplicity out of range"
            )

        digit += (
            count
            * channel_weight(
                config,
                channel,
            )
        )

    return digit


def unpack_batch(
    config: CoreConfig,
    digit: int,
) -> tuple[int, ...]:
    mask = (
        (1 << config.bits_per_channel)
        - 1
    )

    return tuple(
        (
            digit
            >> (
                channel
                * config.bits_per_channel
            )
        )
        & mask
        for channel in range(
            config.channels
        )
    )


def encode_history(
    config: CoreConfig,
    history: tuple[
        tuple[int, ...],
        ...,
    ],
) -> int:
    """
    Exact integer model of the proposed packed SPK core.

    Each item in history is one tick, including empty ticks.

    Datapath per tick:

        state >>= bits_per_tick
        state += packed_batch << fractional_bits
    """

    state = 0

    maximum_state = (
        1 << config.word_bits
    )

    for batch in history:
        state >>= (
            config.bits_per_tick
        )

        digit = pack_batch(
            config,
            batch,
        )

        state += (
            digit
            << config.fractional_bits
        )

        if state >= maximum_state:
            raise AssertionError(
                "core word overflow"
            )

    return state


def decode_history(
    config: CoreConfig,
    state: int,
    ticks: int,
) -> tuple[
    tuple[int, ...],
    ...,
]:
    """
    Decode newest -> oldest internally, then return chronological
    order.

    Exact recovery is guaranteed only while the requested history
    fits inside the configured temporal window.
    """

    if ticks < 1:
        return ()

    if (
        ticks - 1
        > config.history_ticks
    ):
        raise ValueError(
            "requested history exceeds "
            "lossless temporal window"
        )

    digit_mask = (
        (1 << config.bits_per_tick)
        - 1
    )

    recovered = []

    for age in range(
        ticks
    ):
        shift = (
            config.fractional_bits
            - age
            * config.bits_per_tick
        )

        if shift < 0:
            raise ValueError(
                "history no longer representable"
            )

        digit = (
            state
            >> shift
        ) & digit_mask

        recovered.append(
            unpack_batch(
                config,
                digit,
            )
        )

    recovered.reverse()

    return tuple(
        recovered
    )


def zero_batch(
    config: CoreConfig,
) -> tuple[int, ...]:
    return (
        0,
    ) * config.channels


def one_event_batch(
    config: CoreConfig,
    channel: int = 0,
) -> tuple[int, ...]:
    values = [
        0
    ] * config.channels

    values[
        channel
    ] = 1

    return tuple(
        values
    )


def constructive_collision(
    config: CoreConfig,
):
    """
    Construct two histories differing only in the first tick, one
    tick beyond the lossless window.
    """

    final_tick = (
        config.history_ticks
        + 1
    )

    empty = zero_batch(
        config
    )

    history_a = [
        empty
        for _ in range(
            final_tick + 1
        )
    ]

    history_b = list(
        history_a
    )

    history_a[-1] = (
        one_event_batch(
            config,
            0,
        )
    )

    history_b[-1] = (
        one_event_batch(
            config,
            0,
        )
    )

    history_b[0] = (
        one_event_batch(
            config,
            0,
        )
    )

    return (
        tuple(history_a),
        tuple(history_b),
    )


def exhaustive_small_check(
    config: CoreConfig,
) -> bool | None:
    """
    Exhaustively verify injectivity for small configurations only.
    """

    ticks = (
        config.history_ticks
        + 1
    )

    per_channel_values = tuple(
        range(
            config.max_multiplicity
            + 1
        )
    )

    possible_batches = tuple(
        product(
            per_channel_values,
            repeat=config.channels,
        )
    )

    total_histories = (
        len(possible_batches)
        ** ticks
    )

    #
    # Avoid turning a proof-of-concept into a religious ceremony.
    #
    if total_histories > 1_000_000:
        return None

    seen = {}

    for history in product(
        possible_batches,
        repeat=ticks,
    ):
        encoded = encode_history(
            config,
            history,
        )

        previous = seen.get(
            encoded
        )

        if previous is not None:
            print(
                "UNEXPECTED COLLISION"
            )

            print(
                "  config:",
                config,
            )

            print(
                "  left: ",
                previous,
            )

            print(
                "  right:",
                history,
            )

            return False

        seen[
            encoded
        ] = history

    return True


CONFIGS = (
    CoreConfig(
        channels=1,
        max_multiplicity=1,
        fractional_bits=8,
    ),
    CoreConfig(
        channels=3,
        max_multiplicity=1,
        fractional_bits=12,
    ),
    CoreConfig(
        channels=3,
        max_multiplicity=1,
        fractional_bits=24,
    ),
    CoreConfig(
        channels=3,
        max_multiplicity=3,
        fractional_bits=24,
    ),
    CoreConfig(
        channels=4,
        max_multiplicity=1,
        fractional_bits=32,
    ),
    CoreConfig(
        channels=4,
        max_multiplicity=3,
        fractional_bits=32,
    ),
)


def main() -> None:
    print(
        "PACKED SPK CORE"
    )

    print()

    for config in CONFIGS:
        print(
            "=" * 72
        )

        print(
            f"channels={config.channels} "
            f"max_multiplicity="
            f"{config.max_multiplicity} "
            f"history_bits="
            f"{config.fractional_bits}"
        )

        print(
            f"bits/channel: "
            f"{config.bits_per_channel}"
        )

        print(
            f"bits/tick: "
            f"{config.bits_per_tick}"
        )

        print(
            f"register width: "
            f"{config.word_bits}"
        )

        print(
            f"lossless past ticks: "
            f"{config.history_ticks}"
        )

        print(
            f"lossless batches including current: "
            f"{config.history_ticks + 1}"
        )

        weights = tuple(
            channel_weight(
                config,
                channel,
            )
            for channel
            in range(
                config.channels
            )
        )

        print(
            f"ACC weights: "
            f"{weights}"
        )

        exhaustive_ok = (
            exhaustive_small_check(
                config
            )
        )

        if exhaustive_ok is None:
            exhaustive_text = "SKIPPED"
        else:
            exhaustive_text = str(
                exhaustive_ok
            )

        print(
            f"small exhaustive check: "
            f"{exhaustive_text}"
        )

        left, right = (
            constructive_collision(
                config
            )
        )

        left_value = encode_history(
            config,
            left,
        )

        right_value = encode_history(
            config,
            right,
        )

        print(
            "first-outside-window "
            "constructive collision: "
            f"{left_value == right_value}"
        )

        print()


if __name__ == "__main__":
    main()
