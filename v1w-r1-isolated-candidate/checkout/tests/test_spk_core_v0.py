from search.interaction_packed_core_v1 import (
    CoreConfig as PackedConfig,
    encode_history,
)
from search.packed_core_spk_bridge_v1 import (
    history_to_train,
)
from spk_core.packed import (
    lower_packed_core,
)
from spk_core.runtime import (
    run_core_program,
)


PACKED = PackedConfig(
    channels=3,
    max_multiplicity=1,
    fractional_bits=24,
)


def test_lowering_shape():
    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    assert config.state_bits == 27
    assert config.fractional_bits == 24

    assert len(
        program.instructions
    ) == 4


def test_micro_isa_matches_packed_history():
    history = (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 1, 1),
    )

    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    train = history_to_train(
        PACKED,
        history,
    )

    result = run_core_program(
        config,
        program,
        train,
    )

    assert (
        result.final_raw
        == encode_history(
            PACKED,
            history,
        )
    )


def test_micro_isa_materializes_trailing_empty_tick():
    history = (
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 1),
        (0, 0, 0),
    )

    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    train = history_to_train(
        PACKED,
        history,
    )

    result = run_core_program(
        config,
        program,
        train,
    )

    assert (
        result.final_raw
        == encode_history(
            PACKED,
            history,
        )
    )


def test_channel_weights_are_encoded():
    history = (
        (1, 1, 1),
    )

    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    train = history_to_train(
        PACKED,
        history,
    )

    result = run_core_program(
        config,
        program,
        train,
    )

    assert result.final_value(
        config
    ) == 7.0


def test_oldest_tick_is_shifted_out_exactly():
    #
    # 24 fractional bits / 3 bits per tick = 8 past ticks.
    #
    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    left = (
        ((0, 0, 0),)
        * 9
        + (
            (1, 0, 0),
        )
    )

    right = list(
        left
    )

    right[0] = (
        1,
        0,
        0,
    )

    right = tuple(
        right
    )

    left_result = (
        run_core_program(
            config,
            program,
            history_to_train(
                PACKED,
                left,
            ),
        )
    )

    right_result = (
        run_core_program(
            config,
            program,
            history_to_train(
                PACKED,
                right,
            ),
        )
    )

    assert (
        left_result.final_raw
        == right_result.final_raw
    )
