from fractions import Fraction

from search.decay_algebra import (
    combine_decay_taus,
    effective_rate,
    tau_to_fraction,
    tau_to_rate,
)


def test_tau_two_has_rate_one_half():
    assert tau_to_rate(
        2.0
    ) == Fraction(1, 2)


def test_tau_one_has_rate_one():
    assert tau_to_rate(
        1.0
    ) == Fraction(1, 1)


def test_generated_two_thirds_is_recovered_exactly():
    assert tau_to_fraction(
        0.6666666666666666
    ) == Fraction(2, 3)

    assert tau_to_rate(
        0.6666666666666666
    ) == Fraction(3, 2)


def test_generated_one_third_is_recovered_exactly():
    assert tau_to_fraction(
        0.3333333333333333
    ) == Fraction(1, 3)

    assert tau_to_rate(
        0.3333333333333333
    ) == Fraction(3, 1)


def test_generated_two_sevenths_is_recovered_exactly():
    assert tau_to_fraction(
        0.2857142857142857
    ) == Fraction(2, 7)

    assert tau_to_rate(
        0.2857142857142857
    ) == Fraction(7, 2)


def test_two_decay_two_fuse_to_tau_one():
    assert combine_decay_taus(
        (
            2.0,
            2.0,
        )
    ) == 1.0


def test_decay_one_and_two_fuse_to_two_thirds():
    assert combine_decay_taus(
        (
            1.0,
            2.0,
        )
    ) == float(
        Fraction(2, 3)
    )


def test_decay_fusion_is_order_independent_algebraically():
    assert effective_rate(
        (
            1.0,
            2.0,
            2.0,
        )
    ) == effective_rate(
        (
            2.0,
            1.0,
            2.0,
        )
    )


def test_four_decay_two_have_rate_two():
    assert effective_rate(
        (
            2.0,
            2.0,
            2.0,
            2.0,
        )
    ) == Fraction(2, 1)

    assert combine_decay_taus(
        (
            2.0,
            2.0,
            2.0,
            2.0,
        )
    ) == 0.5
