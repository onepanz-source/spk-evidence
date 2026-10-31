from search.rewrite_evidence import (
    AlgebraicStatus,
    DECAY_RUN_FUSION,
    RuntimeStatus,
)


def test_decay_fusion_is_algebraically_proven():
    assert (
        DECAY_RUN_FUSION.algebraic_status
        is AlgebraicStatus.PROVEN
    )


def test_decay_fusion_is_not_universally_ieee_safe():
    assert (
        DECAY_RUN_FUSION.runtime_status
        is RuntimeStatus.NOT_IEEE_SAFE
    )
