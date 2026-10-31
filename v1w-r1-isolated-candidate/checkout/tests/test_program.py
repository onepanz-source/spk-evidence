import pytest

from spk.event import Event, EventBatch
from spk.operators import Acc, Compare, Decay, Emit, Reset
from spk.program import Program
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    channels,
    *,
    timestamp=10,
    delta_ticks=1,
    x=0.0,
):
    batch = EventBatch(
        timestamp=timestamp,
        events=tuple(
            Event(timestamp, channel)
            for channel in channels
        ),
    )

    return ExecutionContext(
        timestamp=timestamp,
        delta_ticks=delta_ticks,
        batch=batch,
        state=State(x=x),
    )


def test_program_preserves_operator_order():
    program = Program(
        (
            Decay(tau=10.0),
            Acc(weight=1.0),
        )
    )

    context = make_context(
        [0],
        x=1.0,
        delta_ticks=10,
    )

    program(context)

    expected = (
        1.0 * 0.36787944117144233
    ) + 1.0

    assert context.state.x == pytest.approx(expected)


def test_reordered_program_has_different_semantics():
    decay_then_acc = Program(
        (
            Decay(tau=10.0),
            Acc(weight=1.0),
        )
    )

    acc_then_decay = Program(
        (
            Acc(weight=1.0),
            Decay(tau=10.0),
        )
    )

    left = make_context(
        [0],
        x=1.0,
        delta_ticks=10,
    )

    right = make_context(
        [0],
        x=1.0,
        delta_ticks=10,
    )

    decay_then_acc(left)
    acc_then_decay(right)

    assert left.state.x != pytest.approx(
        right.state.x
    )


def test_program_builds_integrate_fire_like_behavior():
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

    context = make_context(
        [0, 0, 0],
        timestamp=12,
        x=0.0,
    )

    program(context)

    assert context.output_events == [
        Event(12, 1)
    ]

    assert context.state.x == 0.0
    assert context.state.guard is True


def test_program_below_threshold_preserves_accumulation():
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

    context = make_context(
        [0, 0],
        timestamp=12,
        x=0.0,
    )

    program(context)

    assert context.output_events == []
    assert context.state.x == 2.0
    assert context.state.guard is False


def test_empty_program_is_identity():
    program = Program(())

    context = make_context(
        [0],
        x=5.0,
    )

    before_state = context.state.snapshot()
    before_output = list(context.output_events)

    program(context)

    assert context.state.snapshot() == before_state
    assert context.output_events == before_output


def test_program_length():
    program = Program(
        (
            Acc(),
            Compare(threshold=1.0),
            Emit(),
        )
    )

    assert len(program) == 3


def test_program_rejects_non_callable_element():
    with pytest.raises(TypeError):
        Program(
            (
                Acc(),
                "invalid",
            )
        )
