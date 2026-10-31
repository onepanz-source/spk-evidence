import math

from search.packed_core_spk_bridge_v1 import (
    CONFIG,
    compare_history,
    spk_tau,
)


def test_three_channel_binary_tau():
    expected = (
        1.0
        /
        (
            3.0
            * math.log(2.0)
        )
    )

    assert (
        spk_tau(CONFIG)
        == expected
    )


def test_simple_history_matches_packed_model():
    history = (
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 1, 1),
    )

    spk_value, packed_value = (
        compare_history(
            CONFIG,
            history,
        )
    )

    assert math.isclose(
        spk_value,
        packed_value,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def test_trailing_empty_tick_is_materialized_at_observation_horizon():
    history = (
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 1),
        (0, 0, 0),
    )

    spk_value, packed_value = (
        compare_history(
            CONFIG,
            history,
        )
    )

    assert packed_value == 0.5

    assert math.isclose(
        spk_value,
        packed_value,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )
