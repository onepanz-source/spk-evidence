from search.corpus_v2 import CORPUS_V2
from search.equivalence import (
    Observation,
    normalize_signature_x,
    signature,
    to_signature_observation,
)
from spk.operators import Acc, Decay
from spk.program import Program


def test_signature_normalization_removes_tiny_relative_noise():
    left = normalize_signature_x(
        1.0
    )

    right = normalize_signature_x(
        1.0 + 1e-15
    )

    assert left == right


def test_signature_normalization_preserves_meaningful_difference():
    left = normalize_signature_x(
        1.0
    )

    right = normalize_signature_x(
        1.0 + 1e-6
    )

    assert left != right


def test_signature_normalization_collapses_near_zero_noise():
    assert normalize_signature_x(
        1e-15
    ) == 0.0

    assert normalize_signature_x(
        -1e-15
    ) == 0.0


def test_raw_observation_is_not_modified():
    observation = Observation(
        output=(),
        final_state=(
            1.0 + 1e-15,
            False,
        ),
    )

    assert observation.final_state[0] == (
        1.0 + 1e-15
    )

    normalized = to_signature_observation(
        observation
    )

    assert normalized.final_x == 1.0


def test_decay_acc_fusion_has_same_empirical_signature():
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

    assert signature(
        expanded,
        CORPUS_V2,
    ) == signature(
        fused,
        CORPUS_V2,
    )
