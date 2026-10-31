from search.corpus_decay_v1 import (
    CORPUS_DECAY_V1,
    DECAY_COUNTEREXAMPLES_V1,
)


def test_decay_corpus_has_expected_size():
    assert len(CORPUS_DECAY_V1) == 98


def test_decay_cegar_contributed_six_samples():
    assert len(
        DECAY_COUNTEREXAMPLES_V1
    ) == 6


def test_decay_counterexamples_are_persisted():
    assert all(
        sample in CORPUS_DECAY_V1
        for sample in DECAY_COUNTEREXAMPLES_V1
    )
