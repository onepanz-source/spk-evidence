from search.corpus_v2 import (
    CEGAR_COUNTEREXAMPLES_V2,
    CORPUS_V2,
)


def test_corpus_v2_has_expected_size():
    assert len(CORPUS_V2) == 92


def test_cegar_v2_discovered_four_counterexamples():
    assert len(
        CEGAR_COUNTEREXAMPLES_V2
    ) == 4


def test_cegar_counterexamples_are_in_corpus_v2():
    assert all(
        sample in CORPUS_V2
        for sample in CEGAR_COUNTEREXAMPLES_V2
    )
