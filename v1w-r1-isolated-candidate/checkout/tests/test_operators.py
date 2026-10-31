import pytest
from hypothesis import given
from hypothesis import strategies as st

from spk.event import SpikeTrain
from spk.operators import Delay, delay, merge


SPIKE_TRAINS = st.lists(
    st.tuples(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=8),
    ),
    max_size=50,
).map(SpikeTrain.from_pairs)


def test_merge_preserves_all_events():
    a = SpikeTrain.from_pairs(
        [
            (2, 0),
            (5, 0),
        ]
    )

    b = SpikeTrain.from_pairs(
        [
            (5, 0),
            (7, 1),
        ]
    )

    result = merge(a, b)

    assert result.as_pairs() == (
        (2, 0),
        (5, 0),
        (5, 0),
        (7, 1),
    )


def test_merge_rejects_empty_argument_list():
    with pytest.raises(ValueError):
        merge()


def test_merge_rejects_non_spike_train():
    train = SpikeTrain()

    with pytest.raises(TypeError):
        merge(train, "not-a-spike-train")


def test_delay_shifts_timestamps():
    train = SpikeTrain.from_pairs(
        [
            (2, 0),
            (5, 1),
        ]
    )

    result = delay(train, 3)

    assert result.as_pairs() == (
        (5, 0),
        (8, 1),
    )


def test_delay_preserves_channels_and_multiplicity():
    train = SpikeTrain.from_pairs(
        [
            (2, 1),
            (2, 1),
            (3, 2),
        ]
    )

    result = delay(train, 4)

    assert result.as_pairs() == (
        (6, 1),
        (6, 1),
        (7, 2),
    )


def test_delay_rejects_negative_ticks():
    with pytest.raises(ValueError):
        Delay(-1)


def test_delay_rejects_boolean_ticks():
    with pytest.raises(TypeError):
        Delay(True)


@given(SPIKE_TRAINS)
def test_delay_zero_is_identity(train):
    assert delay(train, 0) == train


@given(
    SPIKE_TRAINS,
    st.integers(min_value=0, max_value=50),
    st.integers(min_value=0, max_value=50),
)
def test_delay_composition(train, a, b):
    left = delay(
        delay(train, b),
        a,
    )

    right = delay(
        train,
        a + b,
    )

    assert left == right


@given(
    SPIKE_TRAINS,
    SPIKE_TRAINS,
)
def test_merge_is_commutative(a, b):
    assert merge(a, b) == merge(b, a)


@given(
    SPIKE_TRAINS,
    SPIKE_TRAINS,
    SPIKE_TRAINS,
)
def test_merge_is_associative(a, b, c):
    left = merge(
        merge(a, b),
        c,
    )

    right = merge(
        a,
        merge(b, c),
    )

    assert left == right


@given(SPIKE_TRAINS)
def test_merge_empty_train_is_identity(train):
    empty = SpikeTrain()

    assert merge(train, empty) == train
    assert merge(empty, train) == train


@given(
    SPIKE_TRAINS,
    SPIKE_TRAINS,
    st.integers(min_value=0, max_value=50),
)
def test_delay_distributes_over_merge(a, b, ticks):
    left = delay(
        merge(a, b),
        ticks,
    )

    right = merge(
        delay(a, ticks),
        delay(b, ticks),
    )

    assert left == right
