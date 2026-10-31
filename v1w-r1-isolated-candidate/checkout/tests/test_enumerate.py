import pytest

from search.enumerate import (
    count_programs,
    enumerate_programs,
    normalize_operator_pool,
)
from spk.operators import Acc, Compare, Emit
from spk.program import Program


def test_normalize_operator_pool_preserves_order():
    a = Acc(weight=1.0)
    b = Compare(threshold=2.0)

    pool = normalize_operator_pool(
        (
            a,
            b,
        )
    )

    assert pool == (
        a,
        b,
    )


def test_normalize_operator_pool_removes_duplicates():
    a = Acc(weight=1.0)

    pool = normalize_operator_pool(
        (
            a,
            Acc(weight=1.0),
        )
    )

    assert pool == (
        a,
    )


def test_enumerator_includes_empty_program():
    programs = list(
        enumerate_programs(
            (
                Acc(weight=1.0),
            ),
            min_length=0,
            max_length=0,
        )
    )

    assert programs == [
        Program(())
    ]


def test_enumerator_generates_length_one_programs():
    a = Acc(weight=1.0)
    b = Emit(channel_out=0)

    programs = list(
        enumerate_programs(
            (a, b),
            min_length=1,
            max_length=1,
        )
    )

    assert programs == [
        Program((a,)),
        Program((b,)),
    ]


def test_enumerator_preserves_operator_order():
    a = Acc(weight=1.0)
    b = Compare(threshold=2.0)

    programs = list(
        enumerate_programs(
            (a, b),
            min_length=2,
            max_length=2,
        )
    )

    assert programs == [
        Program((a, a)),
        Program((a, b)),
        Program((b, a)),
        Program((b, b)),
    ]


def test_duplicate_pool_entries_do_not_expand_space():
    programs = list(
        enumerate_programs(
            (
                Acc(weight=1.0),
                Acc(weight=1.0),
            ),
            min_length=1,
            max_length=1,
        )
    )

    assert len(programs) == 1


def test_empty_pool_can_only_generate_empty_program():
    programs = list(
        enumerate_programs(
            (),
            min_length=0,
            max_length=3,
        )
    )

    assert programs == [
        Program(())
    ]


def test_count_programs_single_length():
    assert count_programs(
        5,
        min_length=4,
        max_length=4,
    ) == 625


def test_count_programs_range():
    assert count_programs(
        3,
        min_length=0,
        max_length=3,
    ) == (
        1
        + 3
        + 9
        + 27
    )


def test_count_matches_actual_enumeration():
    operators = (
        Acc(weight=1.0),
        Compare(threshold=2.0),
        Emit(channel_out=0),
    )

    programs = list(
        enumerate_programs(
            operators,
            min_length=0,
            max_length=4,
        )
    )

    assert len(programs) == count_programs(
        len(operators),
        min_length=0,
        max_length=4,
    )


def test_invalid_length_range_is_rejected():
    with pytest.raises(ValueError):
        list(
            enumerate_programs(
                (Acc(),),
                min_length=3,
                max_length=2,
            )
        )


def test_negative_length_is_rejected():
    with pytest.raises(ValueError):
        list(
            enumerate_programs(
                (Acc(),),
                min_length=-1,
                max_length=2,
            )
        )


def test_non_callable_pool_item_is_rejected():
    with pytest.raises(TypeError):
        list(
            enumerate_programs(
                (
                    Acc(),
                    "invalid",
                ),
                min_length=1,
                max_length=1,
            )
        )
