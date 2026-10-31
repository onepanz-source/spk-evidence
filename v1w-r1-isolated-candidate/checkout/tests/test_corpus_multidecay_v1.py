from search.corpus_multidecay_v1 import (
    CORPUS_MULTIDECAY_V1,
    MULTIDECAY_COUNTEREXAMPLES_V1,
)


def test_multidecay_corpus_has_expected_size():
    assert len(
        CORPUS_MULTIDECAY_V1
    ) == 102


def test_multidecay_cegar_added_four_samples():
    assert len(
        MULTIDECAY_COUNTEREXAMPLES_V1
    ) == 4


def test_multidecay_counterexamples_are_persisted():
    assert all(
        sample in CORPUS_MULTIDECAY_V1
        for sample in MULTIDECAY_COUNTEREXAMPLES_V1
    )
