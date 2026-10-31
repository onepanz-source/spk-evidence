from search.counterexample import find_counterexample
from search.equivalence import Sample
from spk.event import SpikeTrain
from spk.operators import Acc, Compare
from spk.program import Program


def test_counterexample_distinguishes_thresholds():
    left = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )

    right = Program(
        (
            Acc(
                weight=2.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    corpus = (
        Sample(
            SpikeTrain.from_pairs(
                [(1, 0)]
            ),
            initial_x=-0.5,
        ),
    )

    counterexample = find_counterexample(
        left,
        right,
        corpus,
    )

    assert counterexample is not None

    assert counterexample.left.final_state == (
        1.5,
        True,
    )

    assert counterexample.right.final_state == (
        1.5,
        False,
    )


def test_equivalent_acc_compositions_have_no_counterexample():
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
                weight=3.0,
                channel=0,
            ),
        )
    )

    corpus = (
        Sample(
            SpikeTrain.from_pairs([]),
            initial_x=-1.5,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [(1, 0)]
            ),
            initial_x=-0.5,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (1, 0),
                ]
            ),
            initial_x=0.25,
        ),
        Sample(
            SpikeTrain.from_pairs(
                [
                    (1, 0),
                    (3, 0),
                    (8, 0),
                ]
            ),
            initial_x=2.5,
        ),
    )

    assert (
        find_counterexample(
            left,
            right,
            corpus,
        )
        is None
    )


def test_identical_program_has_no_counterexample():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    corpus = (
        Sample(
            SpikeTrain.from_pairs(
                [(1, 0)]
            ),
            initial_x=0.0,
        ),
    )

    assert (
        find_counterexample(
            program,
            program,
            corpus,
        )
        is None
    )
