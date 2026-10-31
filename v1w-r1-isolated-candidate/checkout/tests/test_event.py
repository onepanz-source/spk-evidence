import pytest
from hypothesis import given
from hypothesis import strategies as st

from spk.event import Event, EventBatch, SpikeTrain


def test_event_accepts_valid_values():
    event = Event(timestamp=10, channel=3)

    assert event.timestamp == 10
    assert event.channel == 3


def test_event_rejects_negative_timestamp():
    with pytest.raises(ValueError):
        Event(timestamp=-1, channel=0)


def test_event_rejects_negative_channel():
    with pytest.raises(ValueError):
        Event(timestamp=0, channel=-1)


def test_event_rejects_boolean_as_integer():
    with pytest.raises(TypeError):
        Event(timestamp=True, channel=0)


def test_spike_train_is_canonicalized():
    train = SpikeTrain.from_pairs(
        [
            (10, 2),
            (3, 1),
            (10, 0),
            (3, 0),
        ]
    )

    assert train.as_pairs() == (
        (3, 0),
        (3, 1),
        (10, 0),
        (10, 2),
    )


def test_spike_train_preserves_multiplicity():
    train = SpikeTrain.from_pairs(
        [
            (10, 0),
            (10, 0),
        ]
    )

    assert len(train) == 2

    assert train.as_pairs() == (
        (10, 0),
        (10, 0),
    )


def test_batch_requires_same_timestamp():
    with pytest.raises(ValueError):
        EventBatch(
            timestamp=5,
            events=(
                Event(5, 0),
                Event(6, 1),
            ),
        )


def test_batches_group_simultaneous_events():
    train = SpikeTrain.from_pairs(
        [
            (5, 1),
            (9, 0),
            (5, 0),
            (5, 1),
        ]
    )

    batches = list(train.batches())

    assert len(batches) == 2

    assert batches[0].timestamp == 5

    assert tuple(
        event.channel
        for event in batches[0].events
    ) == (0, 1, 1)

    assert batches[1].timestamp == 9


def test_batch_counts_channels_with_multiplicity():
    batch = EventBatch(
        timestamp=10,
        events=(
            Event(10, 0),
            Event(10, 0),
            Event(10, 1),
        ),
    )

    assert batch.count_channel(0) == 2
    assert batch.count_channel(1) == 1
    assert batch.count_channel(2) == 0


@given(
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=100),
            st.integers(min_value=0, max_value=8),
        ),
        max_size=100,
    )
)
def test_input_order_does_not_change_canonical_train(pairs):
    forward = SpikeTrain.from_pairs(pairs)
    backward = SpikeTrain.from_pairs(reversed(pairs))

    assert forward == backward
