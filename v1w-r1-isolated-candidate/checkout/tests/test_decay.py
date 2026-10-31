import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from spk.event import Event, EventBatch
from spk.operators import Acc, Decay
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    *,
    x=0.0,
    delta_ticks=1,
    timestamp=10,
    guard=False,
):
    batch = EventBatch(
        timestamp=timestamp,
        events=(
            Event(timestamp, 0),
        ),
    )

    return ExecutionContext(
        timestamp=timestamp,
        delta_ticks=delta_ticks,
        batch=batch,
        state=State(
            x=x,
            guard=guard,
        ),
    )


def test_decay_applies_exponential_decay():
    context = make_context(
        x=10.0,
        delta_ticks=5,
    )

    Decay(tau=10.0)(context)

    expected = 10.0 * math.exp(-0.5)

    assert context.state.x == pytest.approx(expected)


def test_decay_zero_elapsed_time_is_identity():
    context = make_context(
        x=7.5,
        delta_ticks=0,
    )

    Decay(tau=10.0)(context)

    assert context.state.x == pytest.approx(7.5)


def test_decay_zero_state_remains_zero():
    context = make_context(
        x=0.0,
        delta_ticks=100,
    )

    Decay(tau=1.0)(context)

    assert context.state.x == 0.0


def test_decay_preserves_guard():
    context = make_context(
        x=5.0,
        delta_ticks=3,
        guard=True,
    )

    Decay(tau=10.0)(context)

    assert context.state.guard is True


def test_decay_rejects_zero_tau():
    with pytest.raises(ValueError):
        Decay(tau=0.0)


def test_decay_rejects_negative_tau():
    with pytest.raises(ValueError):
        Decay(tau=-1.0)


def test_decay_rejects_non_finite_tau():
    with pytest.raises(ValueError):
        Decay(tau=float("nan"))

    with pytest.raises(ValueError):
        Decay(tau=float("inf"))


@given(
    st.floats(
        min_value=-1000.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    st.floats(
        min_value=0.001,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_decay_with_zero_delta_is_identity(x, tau):
    context = make_context(
        x=x,
        delta_ticks=0,
    )

    Decay(tau=tau)(context)

    assert context.state.x == pytest.approx(x)


@given(
    st.floats(
        min_value=-100.0,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=100),
    st.floats(
        min_value=1.0,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_decay_composes_over_elapsed_time(x, a, b, tau):
    sequential_state = State(x=x)

    first = make_context(
        x=x,
        delta_ticks=a,
    )
    first.state = sequential_state

    Decay(tau=tau)(first)

    second = make_context(
        x=sequential_state.x,
        delta_ticks=b,
    )
    second.state = sequential_state

    Decay(tau=tau)(second)

    direct = make_context(
        x=x,
        delta_ticks=a + b,
    )

    Decay(tau=tau)(direct)

    assert sequential_state.x == pytest.approx(
        direct.state.x
    )


def test_acc_and_decay_do_not_commute():
    #
    # Initial state:
    #
    #     x = 1
    #
    # one input spike, weight = 1,
    # delta = tau = 10.
    #
    # DECAY -> ACC:
    #
    #     e^-1 + 1
    #
    # ACC -> DECAY:
    #
    #     2e^-1
    #
    # These are not equal.
    #

    decay_then_acc = make_context(
        x=1.0,
        delta_ticks=10,
    )

    Decay(tau=10.0)(decay_then_acc)
    Acc(weight=1.0)(decay_then_acc)

    acc_then_decay = make_context(
        x=1.0,
        delta_ticks=10,
    )

    Acc(weight=1.0)(acc_then_decay)
    Decay(tau=10.0)(acc_then_decay)

    assert decay_then_acc.state.x != pytest.approx(
        acc_then_decay.state.x
    )
