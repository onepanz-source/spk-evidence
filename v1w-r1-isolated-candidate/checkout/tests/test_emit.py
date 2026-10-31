import pytest

from spk.event import Event, EventBatch
from spk.operators import Emit
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    *,
    guard=False,
    x=0.0,
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


def test_emit_produces_event_when_guard_true():
    context = make_context(
        guard=True,
        timestamp=10,
    )

    Emit(channel_out=3)(context)

    assert context.output_events == [
        Event(10, 3)
    ]


def test_emit_produces_nothing_when_guard_false():
    context = make_context(
        guard=False,
    )

    Emit(channel_out=3)(context)

    assert context.output_events == []


def test_emit_preserves_state():
    context = make_context(
        guard=True,
        x=7.5,
    )

    Emit(channel_out=0)(context)

    assert context.state.x == 7.5


def test_emit_preserves_guard():
    context = make_context(
        guard=True,
    )

    Emit(channel_out=0)(context)

    assert context.state.guard is True


def test_multiple_emit_preserves_multiplicity():
    context = make_context(
        guard=True,
        timestamp=12,
    )

    emit = Emit(channel_out=2)

    emit(context)
    emit(context)

    assert context.output_events == [
        Event(12, 2),
        Event(12, 2),
    ]


def test_multiple_emit_can_use_different_channels():
    context = make_context(
        guard=True,
        timestamp=12,
    )

    Emit(channel_out=1)(context)
    Emit(channel_out=4)(context)

    assert context.output_events == [
        Event(12, 1),
        Event(12, 4),
    ]


def test_emit_rejects_negative_channel():
    with pytest.raises(ValueError):
        Emit(channel_out=-1)


def test_emit_rejects_boolean_channel():
    with pytest.raises(TypeError):
        Emit(channel_out=True)
