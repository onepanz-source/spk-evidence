from search.interaction_packed_core_v1 import (
    CoreConfig,
    channel_weight,
    decode_history,
    encode_history,
    pack_batch,
    unpack_batch,
)


def test_binary_three_channel_weights():
    config = CoreConfig(
        channels=3,
        max_multiplicity=1,
        fractional_bits=12,
    )

    assert tuple(
        channel_weight(
            config,
            channel,
        )
        for channel in range(3)
    ) == (
        1,
        2,
        4,
    )


def test_two_bit_channel_weights():
    config = CoreConfig(
        channels=3,
        max_multiplicity=3,
        fractional_bits=12,
    )

    assert tuple(
        channel_weight(
            config,
            channel,
        )
        for channel in range(3)
    ) == (
        1,
        4,
        16,
    )


def test_batch_pack_roundtrip():
    config = CoreConfig(
        channels=3,
        max_multiplicity=3,
        fractional_bits=12,
    )

    batch = (
        3,
        2,
        1,
    )

    assert unpack_batch(
        config,
        pack_batch(
            config,
            batch,
        ),
    ) == batch


def test_history_roundtrip():
    config = CoreConfig(
        channels=3,
        max_multiplicity=1,
        fractional_bits=12,
    )

    history = (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 1, 1),
    )

    state = encode_history(
        config,
        history,
    )

    assert decode_history(
        config,
        state,
        len(history),
    ) == history


def test_three_binary_channels_use_three_bits_per_tick():
    config = CoreConfig(
        channels=3,
        max_multiplicity=1,
        fractional_bits=24,
    )

    assert (
        config.bits_per_tick
        == 3
    )

    assert (
        config.history_ticks
        == 8
    )

    assert (
        config.word_bits
        == 27
    )
