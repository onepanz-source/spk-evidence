from spk.event import SpikeTrain

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.runtime import (
    run_core_batch,
    run_core_program,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def test_batch_uses_previous_timestamp_for_delta():
    program = CoreProgram(
        (
            ShiftDecay(1),
        )
    )

    first = run_core_batch(
        CONFIG,
        program,
        timestamp=1,
        channels=(0,),
        initial_raw=8,
        previous_timestamp=0,
    )

    assert first.final_raw == 4

    second = run_core_batch(
        CONFIG,
        program,
        timestamp=3,
        channels=(0,),
        initial_raw=first.final_raw,
        previous_timestamp=first.last_timestamp,
    )

    assert second.final_raw == 1


def test_guard_is_transient_per_batch():
    program = CoreProgram(
        (
            CoreAcc(1, 0),
            CoreCmp(1),
            CoreEmit(7),
            CoreReset(0),
        )
    )

    first = run_core_batch(
        CONFIG,
        program,
        timestamp=1,
        channels=(0,),
    )

    assert tuple(
        first.output.as_pairs()
    ) == (
        (1, 7),
    )

    assert first.final_raw == 0
    assert first.final_guard is True

    second = run_core_batch(
        CONFIG,
        program,
        timestamp=2,
        channels=(1,),
        initial_raw=first.final_raw,
        previous_timestamp=first.last_timestamp,
    )

    assert tuple(
        second.output.as_pairs()
    ) == ()

    assert second.final_raw == 0
    assert second.final_guard is False


def test_shared_channel_count_inside_batch():
    program = CoreProgram(
        (
            CoreAcc(1, 0),
            CoreAcc(1, 0),
        )
    )

    result = run_core_batch(
        CONFIG,
        program,
        timestamp=0,
        channels=(
            0,
            0,
            1,
        ),
    )

    #
    # n_0 = 2 is shared by both ACC instructions.
    #
    assert result.final_raw == 4


def test_program_execution_equals_manual_batch_execution():
    program = CoreProgram(
        (
            ShiftDecay(1),
            CoreAcc(1, 0),
            CoreCmp(2),
            CoreEmit(7),
            CoreReset(0),
        )
    )

    train = SpikeTrain.from_pairs(
        (
            (1, 0),
            (3, 0),
            (3, 0),
            (5, 1),
        )
    )

    whole = run_core_program(
        CONFIG,
        program,
        train,
        initial_raw=8,
    )

    raw = 8
    previous_timestamp = 0
    outputs = []
    guard = False

    batches = (
        (
            1,
            (0,),
        ),
        (
            3,
            (
                0,
                0,
            ),
        ),
        (
            5,
            (1,),
        ),
    )

    for timestamp, channels in batches:
        result = run_core_batch(
            CONFIG,
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

    assert tuple(
        whole.output.as_pairs()
    ) == tuple(outputs)

    assert whole.final_raw == raw
    assert whole.final_guard == guard

    assert (
        whole.last_timestamp
        == previous_timestamp
    )


def test_empty_program_train_preserves_initial_state():
    program = CoreProgram(
        (
            ShiftDecay(1),
        )
    )

    result = run_core_program(
        CONFIG,
        program,
        SpikeTrain.from_pairs(()),
        initial_raw=17,
    )

    assert result.final_raw == 17
    assert result.final_guard is False
    assert result.last_timestamp == 0
    assert tuple(
        result.output.as_pairs()
    ) == ()


def test_empty_batch_is_rejected():
    program = CoreProgram(())

    try:
        run_core_batch(
            CONFIG,
            program,
            timestamp=1,
            channels=(),
        )

    except ValueError as exc:
        assert (
            "at least one event"
            in str(exc)
        )

    else:
        raise AssertionError(
            "empty batch was accepted"
        )
