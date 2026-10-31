from __future__ import annotations

from decimal import (
    Decimal,
    localcontext,
)
from fractions import Fraction


def _fraction_to_decimal(
    value: Fraction,
) -> Decimal:
    return (
        Decimal(value.numerator)
        /
        Decimal(value.denominator)
    )


def positive_tick_decay_bound_below(
    *,
    upper_bound: float,
    accumulated_rate: Fraction,
    threshold: float,
) -> bool:
    """
    Decide the sufficient condition:

        U * exp(-lambda) < theta

    for discrete time delta >= 1.

    Assumptions used by this abstraction:

      * time is an integer number of ticks;
      * delta == 0 is handled separately by the rewrite;
      * U > 0;
      * theta > 0;
      * lambda > 0.

    If the inequality holds at delta=1, it also holds for every
    positive integer delta because exponential decay is monotone.

    Decimal is used only for this canonicalization-side proof test.
    It does not change SPK runtime arithmetic.
    """

    if upper_bound <= 0.0:
        return False

    if threshold <= 0.0:
        return False

    if accumulated_rate <= 0:
        return False

    with localcontext() as context:
        context.prec = 80

        upper = Decimal(
            str(upper_bound)
        )

        target = Decimal(
            str(threshold)
        )

        rate = _fraction_to_decimal(
            accumulated_rate
        )

        decayed_upper = (
            upper
            * (-rate).exp()
        )

        return decayed_upper < target
