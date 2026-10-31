import math

import pytest

from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Decay,
)
from spk.program import Program
from spk.runner import run_program


AT_T0 = SpikeTrain.from_pairs(
    [(0, 0)]
)

AT_T1 = SpikeTrain.from_pairs(
    [(1, 0)]
)


def test_acc_alone_ignores_single_event_timestamp():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=None,
            ),
        )
    )

    left = run_program(
        program,
        AT_T0,
        initial_x=3.0,
    )

    right = run_program(
        program,
        AT_T1,
        initial_x=3.0,
    )

    assert (
        left.final_state
        ==
        right.final_state
    )


def test_decay_then_acc_observes_timestamp_with_prior_state():
    program = Program(
        (
            Decay(
                tau=1.0,
            ),
            Acc(
                weight=1.0,
                channel=None,
            ),
        )
    )

    at_zero = run_program(
        program,
        AT_T0,
        initial_x=1.0,
    )

    at_one = run_program(
        program,
        AT_T1,
        initial_x=1.0,
    )

    assert (
        at_zero.final_state[0]
        ==
        pytest.approx(2.0)
    )

    assert (
        at_one.final_state[0]
        ==
        pytest.approx(
            1.0 + math.exp(-1.0)
        )
    )

    assert (
        at_zero.final_state[0]
        != at_one.final_state[0]
    )


def test_acc_then_decay_observes_timestamp_from_zero_state():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=None,
            ),
            Decay(
                tau=1.0,
            ),
        )
    )

    at_zero = run_program(
        program,
        AT_T0,
        initial_x=0.0,
    )

    at_one = run_program(
        program,
        AT_T1,
        initial_x=0.0,
    )

    assert (
        at_zero.final_state[0]
        ==
        pytest.approx(1.0)
    )

    assert (
        at_one.final_state[0]
        ==
        pytest.approx(
            math.exp(-1.0)
        )
    )


def test_acc_total_preserves_multiplicity():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=None,
            ),
        )
    )

    one = run_program(
        program,
        SpikeTrain.from_pairs(
            [(0, 0)]
        ),
    )

    two = run_program(
        program,
        SpikeTrain.from_pairs(
            [
                (0, 0),
                (0, 0),
            ]
        ),
    )

    assert one.final_state[0] == 1.0
    assert two.final_state[0] == 2.0
