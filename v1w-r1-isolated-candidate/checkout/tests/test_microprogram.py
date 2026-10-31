from spk.event import Event, EventBatch
from spk.operators import Acc, Compare, Emit
from spk.runtime import ExecutionContext
from spk.state import State


def make_context(
    channels,
    *,
    timestamp=10,
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
        delta_ticks=1,
        batch=batch,
        state=State(x=x),
    )


def test_acc_cmp_emit_forms_first_complete_spk_path():
    context = make_context(
        [0, 0, 0],
        timestamp=10,
    )

    Acc(
        weight=1.0,
        channel=0,
    )(context)

    Compare(
        threshold=3.0,
    )(context)

    Emit(
        channel_out=1,
    )(context)

    assert context.state.x == 3.0
    assert context.state.guard is True

    assert context.output_events == [
        Event(10, 1)
    ]


def test_acc_cmp_emit_does_not_emit_below_threshold():
    context = make_context(
        [0, 0],
        timestamp=10,
    )

    Acc(
        weight=1.0,
        channel=0,
    )(context)

    Compare(
        threshold=3.0,
    )(context)

    Emit(
        channel_out=1,
    )(context)

    assert context.state.x == 2.0
    assert context.state.guard is False
    assert context.output_events == []


def test_acc_cmp_emit_reset_forms_integrate_fire_cycle():
    from spk.operators import Reset

    context = make_context(
        [0, 0, 0],
        timestamp=10,
        x=0.0,
    )

    Acc(
        weight=1.0,
        channel=0,
    )(context)

    Compare(
        threshold=3.0,
    )(context)

    Emit(
        channel_out=1,
    )(context)

    Reset(
        value=0.0,
    )(context)

    assert context.output_events == [
        Event(10, 1)
    ]

    assert context.state.x == 0.0
    assert context.state.guard is True


def test_reset_is_conditional_on_cmp_result():
    from spk.operators import Reset

    context = make_context(
        [0, 0],
        timestamp=10,
        x=0.0,
    )

    Acc(
        weight=1.0,
        channel=0,
    )(context)

    Compare(
        threshold=3.0,
    )(context)

    Reset(
        value=0.0,
    )(context)

    assert context.state.x == 2.0
    assert context.state.guard is False
