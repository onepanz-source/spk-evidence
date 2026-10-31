from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import product

from spk.program import Program, StateOperator


def _validate_length(
    name: str,
    value: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def normalize_operator_pool(
    operators: Iterable[StateOperator],
) -> tuple[StateOperator, ...]:
    """
    Convert an operator iterable into a deterministic tuple while
    removing exact duplicate operator instances by value equality.

    Ordering of first occurrence is preserved.
    """

    result: list[StateOperator] = []

    for operator in operators:
        if not callable(operator):
            raise TypeError(
                "operator pool may contain only callable operators"
            )

        if operator not in result:
            result.append(operator)

    return tuple(result)


def enumerate_programs(
    operators: Iterable[StateOperator],
    *,
    min_length: int = 0,
    max_length: int = 4,
) -> Iterator[Program]:
    """
    Exhaustively enumerate ordered SPK state programs.

    Parameter values are NOT generated here.

    The caller provides a finite pool of already-instantiated
    operators. This keeps the search domain explicit and reproducible.

    Example pool:

        (
            Acc(weight=1.0, channel=0),
            Compare(threshold=2.0),
            Emit(channel_out=0),
            Reset(value=0.0),
        )

    Programs are emitted deterministically by:

        increasing length,
        then itertools.product order.
    """

    _validate_length("min_length", min_length)
    _validate_length("max_length", max_length)

    if min_length > max_length:
        raise ValueError(
            "min_length must be <= max_length"
        )

    pool = normalize_operator_pool(operators)

    for length in range(
        min_length,
        max_length + 1,
    ):
        if length == 0:
            yield Program(())
            continue

        if not pool:
            continue

        for combination in product(
            pool,
            repeat=length,
        ):
            yield Program(combination)


def count_programs(
    operator_count: int,
    *,
    min_length: int = 0,
    max_length: int = 4,
) -> int:
    """
    Return the number of syntactic programs in an unrestricted
    exhaustive search space.

    For k operators:

        sum(k ** n)

    over the requested program lengths.
    """

    if (
        isinstance(operator_count, bool)
        or not isinstance(operator_count, int)
    ):
        raise TypeError(
            "operator_count must be an integer"
        )

    if operator_count < 0:
        raise ValueError(
            "operator_count must be >= 0"
        )

    _validate_length("min_length", min_length)
    _validate_length("max_length", max_length)

    if min_length > max_length:
        raise ValueError(
            "min_length must be <= max_length"
        )

    return sum(
        operator_count ** length
        for length in range(
            min_length,
            max_length + 1,
        )
    )
