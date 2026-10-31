from search.event_canonicalize import (
    event_normal_form,
)
from search.event_expr import (
    EventDelay,
    EventEmpty,
    EventMerge,
    EventVar,
)


A = EventVar("A")
B = EventVar("B")
C = EventVar("C")
EMPTY = EventEmpty()


def test_empty_is_merge_identity():
    assert event_normal_form(
        EventMerge(
            A,
            EMPTY,
        )
    ) == event_normal_form(
        A
    )


def test_merge_is_commutative():
    assert event_normal_form(
        EventMerge(
            A,
            B,
        )
    ) == event_normal_form(
        EventMerge(
            B,
            A,
        )
    )


def test_merge_is_associative():
    left = EventMerge(
        EventMerge(
            A,
            B,
        ),
        C,
    )

    right = EventMerge(
        A,
        EventMerge(
            B,
            C,
        ),
    )

    assert (
        event_normal_form(left)
        ==
        event_normal_form(right)
    )


def test_delay_zero_is_identity():
    assert event_normal_form(
        EventDelay(
            0,
            A,
        )
    ) == event_normal_form(
        A
    )


def test_delay_composition_adds_ticks():
    left = EventDelay(
        2,
        EventDelay(
            3,
            A,
        ),
    )

    right = EventDelay(
        5,
        A,
    )

    assert (
        event_normal_form(left)
        ==
        event_normal_form(right)
    )


def test_delay_distributes_over_merge():
    left = EventDelay(
        2,
        EventMerge(
            A,
            B,
        ),
    )

    right = EventMerge(
        EventDelay(
            2,
            A,
        ),
        EventDelay(
            2,
            B,
        ),
    )

    assert (
        event_normal_form(left)
        ==
        event_normal_form(right)
    )


def test_merge_preserves_multiplicity():
    form = event_normal_form(
        EventMerge(
            A,
            A,
        )
    )

    assert len(
        form.atoms
    ) == 2

    assert (
        form.atoms[0]
        ==
        form.atoms[1]
    )


def test_normal_form_combines_distribution_and_delay_composition():
    left = EventDelay(
        2,
        EventMerge(
            A,
            EventDelay(
                1,
                B,
            ),
        ),
    )

    right = EventMerge(
        EventDelay(
            2,
            A,
        ),
        EventDelay(
            3,
            B,
        ),
    )

    assert (
        event_normal_form(left)
        ==
        event_normal_form(right)
    )
