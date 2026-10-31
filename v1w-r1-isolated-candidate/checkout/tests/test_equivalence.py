from search.equivalence import (
    Sample,
    cluster_by_signature,
    empirically_equivalent,
    observe,
    signature,
)
from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Emit,
    Reset,
)
from spk.program import Program


def corpus():
    return (
        Sample(
            SpikeTrain.from_pairs([]),
            initial_x=0.0,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [(1, 0)]
            ),
            initial_x=0.0,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (2, 0),
                ]
            ),
            initial_x=0.0,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (2, 0),
                    (3, 0),
                ]
            ),
            initial_x=0.0,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [
                    (1, 1),
                    (2, 1),
                ]
            ),
            initial_x=0.0,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [(1, 0)]
            ),
            initial_x=2.0,
        ),
    )


def test_observation_is_deterministic():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    sample = Sample(
        SpikeTrain.from_pairs(
            [
                (1, 0),
                (2, 0),
            ]
        )
    )

    assert observe(
        program,
        sample,
    ) == observe(
        program,
        sample,
    )


def test_identical_programs_have_same_signature():
    left = Program(
        (
            Acc(weight=1.0),
        )
    )

    right = Program(
        (
            Acc(weight=1.0),
        )
    )

    assert signature(
        left,
        corpus(),
    ) == signature(
        right,
        corpus(),
    )


def test_empty_program_equivalent_to_zero_acc():
    empty = Program(())

    zero_acc = Program(
        (
            Acc(weight=0.0),
        )
    )

    assert empirically_equivalent(
        empty,
        zero_acc,
        corpus(),
    )


def test_two_accs_equal_one_double_weight_acc():
    double_acc = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    weight_two = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    assert empirically_equivalent(
        double_acc,
        weight_two,
        corpus(),
    )


def test_acc_order_can_be_empirically_equivalent():
    left = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    right = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    assert empirically_equivalent(
        left,
        right,
        corpus(),
    )


def test_threshold_program_is_not_equivalent_to_empty():
    empty = Program(())

    threshold = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert not empirically_equivalent(
        empty,
        threshold,
        corpus(),
    )


def test_reset_changes_equivalence_class():
    without_reset = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    with_reset = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    assert not empirically_equivalent(
        without_reset,
        with_reset,
        corpus(),
    )


def test_clustering_groups_equivalent_programs():
    empty = Program(())

    zero_acc = Program(
        (
            Acc(weight=0.0),
        )
    )

    active = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    clusters = cluster_by_signature(
        (
            empty,
            zero_acc,
            active,
        ),
        corpus(),
    )

    sizes = sorted(
        len(group)
        for group in clusters.values()
    )

    assert sizes == [1, 2]
