from search.corpus_v2 import CORPUS_V2
from search.counterexample import find_counterexample
from spk.operators import Acc, Decay
from spk.program import Program


def test_rounding_noise_is_not_a_counterexample():
    expanded = Program(
        (
            Decay(
                tau=2.0,
            ),
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

    fused = Program(
        (
            Decay(
                tau=2.0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    assert (
        find_counterexample(
            expanded,
            fused,
            CORPUS_V2,
        )
        is None
    )
