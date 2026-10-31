import pytest
from hypothesis import given
from hypothesis import strategies as st

from spk.event import Event, EventBatch
from spk.operators import Compare
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    *,
    x=0.0,
    guard=False,
    timestamp=10,
):
    batch = EventBatch(
        timestamp=timestamp,
        events=(
            Event(timestamp, 0),
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


def test_cmp_sets_guard_true_above_threshold():
    context = make_context(x=5.0)

    Compare(threshold=3.0)(context)

    assert context.state.guard is True


def test_cmp_sets_guard_true_at_threshold():
    context = make_context(x=3.0)

    Compare(threshold=3.0)(context)

    assert context.state.guard is True


def test_cmp_sets_guard_false_below_threshold():
    context = make_context(
        x=2.999,
        guard=True,
    )

    Compare(threshold=3.0)(context)

    assert context.state.guard is False


def test_cmp_preserves_persistent_state():
    context = make_context(x=7.25)

    Compare(threshold=3.0)(context)

    assert context.state.x == 7.25


def test_cmp_overwrites_previous_guard():
    context = make_context(
        x=1.0,
        guard=True,
    )

    Compare(threshold=2.0)(context)

    assert context.state.guard is False


def test_cmp_accepts_negative_threshold():
    context = make_context(x=-2.0)

    Compare(threshold=-3.0)(context)

    assert context.state.guard is True


def test_cmp_rejects_nan_threshold():
    with pytest.raises(ValueError):
        Compare(threshold=float("nan"))


def test_cmp_rejects_infinite_threshold():
    with pytest.raises(ValueError):
        Compare(threshold=float("inf"))


@given(
    st.floats(
        min_value=-1000.0,
        max_value=1000.0,
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
def test_cmp_matches_greater_equal_relation(x, threshold):
    context = make_context(x=x)

    Compare(threshold=threshold)(context)

    assert context.state.guard == (x >= threshold)
