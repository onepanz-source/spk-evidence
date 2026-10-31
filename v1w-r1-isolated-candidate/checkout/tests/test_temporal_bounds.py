from fractions import Fraction

from search.temporal_bounds import (
    positive_tick_decay_bound_below,
)


def test_two_decayed_at_rate_one_is_below_one():
    assert positive_tick_decay_bound_below(
        upper_bound=2.0,
        accumulated_rate=Fraction(1, 1),
        threshold=1.0,
    )


def test_three_decayed_at_rate_one_is_not_below_one():
    assert not positive_tick_decay_bound_below(
        upper_bound=3.0,
        accumulated_rate=Fraction(1, 1),
        threshold=1.0,
    )


def test_zero_rate_cannot_prove_positive_tick_decay():
    assert not positive_tick_decay_bound_below(
        upper_bound=2.0,
        accumulated_rate=Fraction(0, 1),
        threshold=1.0,
    )


def test_negative_threshold_is_rejected_conservatively():
    assert not positive_tick_decay_bound_below(
        upper_bound=2.0,
        accumulated_rate=Fraction(1, 1),
        threshold=-1.0,
    )
