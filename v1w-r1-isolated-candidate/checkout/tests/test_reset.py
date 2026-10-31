import pytest

from spk.event import Event, EventBatch
from spk.operators import Reset
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


def test_reset_changes_state_when_guard_true():
    context = make_context(
        x=7.5,
        guard=True,
    )

    Reset(value=0.0)(context)

    assert context.state.x == 0.0


def test_reset_does_nothing_when_guard_false():
    context = make_context(
        x=7.5,
        guard=False,
    )

    Reset(value=0.0)(context)

    assert context.state.x == 7.5


def test_reset_can_use_nonzero_value():
    context = make_context(
        x=7.5,
        guard=True,
    )

    Reset(value=-2.0)(context)

    assert context.state.x == -2.0


def test_reset_preserves_true_guard():
    context = make_context(
        x=7.5,
        guard=True,
    )

    Reset(value=0.0)(context)

    assert context.state.guard is True


def test_reset_preserves_false_guard():
    context = make_context(
        x=7.5,
        guard=False,
    )

    Reset(value=0.0)(context)

    assert context.state.guard is False


def test_reset_does_not_emit():
    context = make_context(
        x=7.5,
        guard=True,
    )

    Reset(value=0.0)(context)

    assert context.output_events == []


def test_reset_rejects_nan():
    with pytest.raises(ValueError):
        Reset(value=float("nan"))


def test_reset_rejects_infinity():
    with pytest.raises(ValueError):
        Reset(value=float("inf"))
