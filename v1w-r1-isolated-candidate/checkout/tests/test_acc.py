import pytest
from hypothesis import given
from hypothesis import strategies as st

from spk.event import Event, EventBatch
from spk.operators import Acc
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    pairs,
    *,
    timestamp=10,
    x=0.0,
    guard=False,
):
    batch = EventBatch(
        timestamp=timestamp,
        events=tuple(
            Event(timestamp, channel)
            for channel in pairs
        ),
    )

    return ExecutionContext(
        timestamp=timestamp,
        delta_ticks=1,
        batch=batch,
        state=State(
            x=x,
            guard=guard,
        ),
    )


def test_acc_accumulates_all_events():
    context = make_context(
        [0, 1, 1],
        x=2.0,
    )

    Acc(weight=0.5)(context)

    assert context.state.x == 3.5


def test_acc_filters_by_channel():
    context = make_context(
        [0, 0, 1],
        x=2.0,
    )

    Acc(
        weight=0.5,
        channel=0,
    )(context)

    assert context.state.x == 3.0


def test_acc_preserves_event_multiplicity():
    context = make_context(
        [0, 0, 0],
    )

    Acc(
        weight=1.0,
        channel=0,
    )(context)

    assert context.state.x == 3.0


def test_acc_with_missing_channel_changes_nothing():
    context = make_context(
        [0, 1],
        x=7.0,
    )

    Acc(
        weight=5.0,
        channel=2,
    )(context)

    assert context.state.x == 7.0


def test_acc_does_not_modify_guard():
    context = make_context(
        [0],
        guard=True,
    )

    Acc(weight=1.0)(context)

    assert context.state.guard is True


def test_acc_accepts_negative_weight():
    context = make_context(
        [0, 0],
        x=5.0,
    )

    Acc(weight=-1.5)(context)

    assert context.state.x == 2.0


def test_acc_rejects_non_finite_weight():
    with pytest.raises(ValueError):
        Acc(weight=float("nan"))

    with pytest.raises(ValueError):
        Acc(weight=float("inf"))


def test_acc_rejects_negative_channel():
    with pytest.raises(ValueError):
        Acc(
            weight=1.0,
            channel=-1,
        )


@given(
    st.integers(min_value=1, max_value=50),
    st.floats(
        min_value=-100.0,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    st.floats(
        min_value=-1000.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_acc_obeys_linear_multiplicity(count, weight, initial):
    context = make_context(
        [0] * count,
        x=initial,
    )

    Acc(
        weight=weight,
        channel=0,
    )(context)

    expected = initial + weight * count

    assert context.state.x == pytest.approx(expected)
