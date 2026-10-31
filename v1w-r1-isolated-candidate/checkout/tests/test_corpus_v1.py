from search.corpus_v1 import CORPUS_V1


def test_corpus_v1_has_expected_size():
    assert len(CORPUS_V1) == 88


def test_corpus_v1_contains_threshold_counterexample():
    matches = [
        sample
        for sample in CORPUS_V1
        if sample.initial_x == -0.5
        and sample.train.as_pairs() == ((1, 0),)
    ]

    assert len(matches) == 1
