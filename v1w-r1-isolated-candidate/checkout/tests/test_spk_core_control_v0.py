from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Emit,
    Reset,
)
from spk.program import Program

from spk_core.compiler import (
    compile_spk_program,
)
from spk_core.isa import (
    CoreConfig,
)
from spk_core.runtime import (
    run_core_program,
)


CONFIG = CoreConfig(
    state_bits=24,
    fractional_bits=8,
)


def compile_and_run(
    program,
    pairs,
    *,
    initial_x=0,
):
    compilation = (
        compile_spk_program(
            program,
            CONFIG,
        )
    )

    return run_core_program(
        CONFIG,
        compilation.program,
        SpikeTrain.from_pairs(
            pairs
        ),
        initial_raw=(
            initial_x
            * CONFIG.scale
        ),
    )


def test_threshold_emit_reset():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=7,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    result = compile_and_run(
        program,
        [
            (0, 0),
            (2, 0),
        ],
    )

    assert result.output.as_pairs() == (
        (0, 7),
        (2, 7),
    )

    assert result.final_raw == 0


def test_state_persists_between_batches():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
            Emit(
                channel_out=7,
            ),
        )
    )

    result = compile_and_run(
        program,
        [
            (0, 0),
            (2, 0),
        ],
    )

    assert result.output.as_pairs() == (
        (2, 7),
    )

    assert (
        result.final_value(
            CONFIG
        )
        == 2.0
    )


def test_guard_is_recomputed_per_batch():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=7,
            ),
        )
    )

    result = compile_and_run(
        program,
        [
            (0, 0),
            (1, 1),
        ],
    )

    #
    # x remains >= 1, and CMP is executed again
    # on the second batch.
    #
    assert result.output.as_pairs() == (
        (0, 7),
        (1, 7),
    )


def test_reset_affects_following_compare_same_batch():
    program = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=8,
            ),
        )
    )

    result = compile_and_run(
        program,
        [
            (0, 0),
        ],
    )

    assert (
        result.output.as_pairs()
        == ()
    )

    assert result.final_guard is False


def test_multiple_emits_preserve_program_order_semantics():
    program = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=7,
            ),
            Compare(
                threshold=2.0,
            ),
            Emit(
                channel_out=8,
            ),
        )
    )

    result = compile_and_run(
        program,
        [
            (0, 0),
        ],
    )

    #
    # SpikeTrain canonicalizes coincident output
    # events by channel.
    #
    assert result.output.as_pairs() == (
        (0, 7),
        (0, 8),
    )
