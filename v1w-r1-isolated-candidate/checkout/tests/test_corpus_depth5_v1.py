from search.corpus_depth5_v1 import (
    CORPUS_DEPTH5_V1,
    DEPTH5_COUNTEREXAMPLES_V1,
)


def test_depth5_corpus_has_expected_size():
    assert len(CORPUS_DEPTH5_V1) == 113


def test_depth5_cegar_added_eleven_samples():
    assert len(
        DEPTH5_COUNTEREXAMPLES_V1
    ) == 11


def test_depth5_counterexamples_are_persisted():
    assert all(
        sample in CORPUS_DEPTH5_V1
        for sample in DEPTH5_COUNTEREXAMPLES_V1
    )
