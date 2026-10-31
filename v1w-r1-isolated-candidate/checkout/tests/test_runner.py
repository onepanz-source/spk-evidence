import math

import pytest

from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)
from spk.program import Program
from spk.runner import run_program


def test_runner_accumulates_state_across_timestamps():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=3.0,
            ),
            Emit(
                channel_out=1,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        [
            (1, 0),
            (2, 0),
            (3, 0),
        ]
    )

    result = run_program(
        program,
        train,
    )

    assert result.output.as_pairs() == (
        (3, 1),
    )

    assert result.final_state == (
        0.0,
        True,
    )


def test_runner_can_fire_repeatedly_after_reset():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=3.0,
            ),
            Emit(
                channel_out=1,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        [
            (1, 0),
            (2, 0),
            (3, 0),
            (4, 0),
            (5, 0),
            (6, 0),
        ]
    )

    result = run_program(
        program,
        train,
    )

    assert result.output.as_pairs() == (
        (3, 1),
        (6, 1),
    )

    assert result.final_state == (
        0.0,
        True,
    )


def test_runner_preserves_subthreshold_state():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=3.0,
            ),
            Emit(
                channel_out=1,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        [
            (1, 0),
            (2, 0),
        ]
    )

    result = run_program(
        program,
        train,
    )

    assert result.output.as_pairs() == ()

    assert result.final_state == (
        2.0,
        False,
    )


def test_runner_uses_elapsed_time_between_batches():
    program = Program(
        (
            Decay(
                tau=10.0,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        [
            (5, 0),
            (15, 0),
        ]
    )

    result = run_program(
        program,
        train,
        initial_x=1.0,
    )

    # t=0 -> t=5:
    #
    #     exp(-5/10)
    #
    # t=5 -> t=15:
    #
    #     exp(-10/10)
    #
    # total:
    #
    #     exp(-15/10)

    expected = math.exp(-1.5)

    assert result.final_state[0] == pytest.approx(
        expected
    )


def test_runner_preserves_output_multiplicity():
    program = Program(
        (
            Compare(
                threshold=0.0,
            ),
            Emit(
                channel_out=2,
            ),
            Emit(
                channel_out=2,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        [
            (7, 0),
        ]
    )

    result = run_program(
        program,
        train,
    )

    assert result.output.as_pairs() == (
        (7, 2),
        (7, 2),
    )


def test_empty_input_is_identity_on_initial_state():
    program = Program(
        (
            Acc(
                weight=1.0,
            ),
        )
    )

    result = run_program(
        program,
        SpikeTrain(),
        initial_x=5.0,
    )

    assert result.output.as_pairs() == ()

    assert result.final_state == (
        5.0,
        False,
    )


def test_runner_rejects_invalid_program():
    with pytest.raises(TypeError):
        run_program(
            "invalid",
            SpikeTrain(),
        )


def test_runner_rejects_invalid_spike_train():
    with pytest.raises(TypeError):
        run_program(
            Program(()),
            "invalid",
        )
