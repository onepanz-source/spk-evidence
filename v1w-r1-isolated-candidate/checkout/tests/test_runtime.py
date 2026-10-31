import pytest

from spk.event import Event, EventBatch
from spk.runtime import ExecutionContext
from spk.state import State


def make_batch(timestamp=10):
    return EventBatch(
        timestamp=timestamp,
        events=(
            Event(timestamp, 0),
        ),
    )


def test_execution_context_accepts_valid_values():
    batch = make_batch(10)
    state = State()

    context = ExecutionContext(
        timestamp=10,
        delta_ticks=3,
        batch=batch,
        state=state,
    )

    assert context.timestamp == 10
    assert context.delta_ticks == 3
    assert context.batch is batch
    assert context.state is state
    assert context.output_events == []


def test_context_rejects_timestamp_mismatch():
    batch = make_batch(10)

    with pytest.raises(ValueError):
        ExecutionContext(
            timestamp=11,
            delta_ticks=1,
            batch=batch,
            state=State(),
        )


def test_context_rejects_negative_delta():
    batch = make_batch(10)

    with pytest.raises(ValueError):
        ExecutionContext(
            timestamp=10,
            delta_ticks=-1,
            batch=batch,
            state=State(),
        )
