import pytest

from spk.state import State


def test_default_state():
    state = State()

    assert state.x == 0.0
    assert state.guard is False


def test_state_accepts_initial_value():
    state = State(x=3)

    assert state.x == 3.0


def test_state_rejects_nan():
    with pytest.raises(ValueError):
        State(x=float("nan"))


def test_state_rejects_infinity():
    with pytest.raises(ValueError):
        State(x=float("inf"))


def test_begin_batch_resets_guard():
    state = State(
        x=7.5,
        guard=True,
    )

    state.begin_batch()

    assert state.guard is False


def test_begin_batch_preserves_persistent_state():
    state = State(
        x=7.5,
        guard=True,
    )

    state.begin_batch()

    assert state.x == 7.5


def test_snapshot():
    state = State(
        x=2.5,
        guard=True,
    )

    assert state.snapshot() == (
        2.5,
        True,
    )
