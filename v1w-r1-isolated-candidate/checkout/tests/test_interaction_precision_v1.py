import pytest

from search.interaction_precision_v1 import (
    event_timestamps,
    fixed_rounder,
    identity,
    simulate_quantized,
    simulate_runtime_float64,
)


def test_event_history_forces_final_event():
    assert event_timestamps(
        0,
        3,
    ) == (3,)

    assert event_timestamps(
        0b101,
        3,
    ) == (
        0,
        2,
        3,
    )


@pytest.mark.parametrize(
    "timestamps",
    (
        (0,),
        (1,),
        (0, 1),
        (0, 2),
        (1, 3),
        (0, 2, 5),
    ),
)
def test_float64_model_matches_runtime(
    timestamps,
):
    assert simulate_quantized(
        timestamps,
        identity,
    ) == simulate_runtime_float64(
        timestamps
    )


def test_fixed_rounder_uses_requested_grid():
    round_value = fixed_rounder(
        4
    )

    assert round_value(
        1.0
    ) == 1.0

    assert (
        round_value(
            1.03
        )
        * 16
    ).is_integer()
