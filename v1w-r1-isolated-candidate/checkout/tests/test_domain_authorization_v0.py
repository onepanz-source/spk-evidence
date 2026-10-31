from __future__ import annotations

from spk.event import SpikeTrain

from spk_core.canonicalize import (
    _remove_pre_acc_shift_under_cmp1_reset0,
)
from spk_core.domain import (
    ExecutionCase,
    FiniteExecutionDomain,
    verified_finite_domain_rules,
)
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.rules import (
    CanonicalizationProfile,
    canonicalization_profile,
)
from spk_core.semantic_canonicalize import (
    _normalize_temporal_shift_width,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def train(*pairs):
    return SpikeTrain.from_pairs(
        pairs
    )


def domain(
    *cases: ExecutionCase,
):
    return FiniteExecutionDomain(
        config=CONFIG,
        cases=cases,
    )


def time05_source():
    return [
        CoreCmp(
            threshold_raw=1,
        ),
        ShiftDecay(
            bits_per_tick=1,
        ),
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreReset(
            value_raw=0,
        ),
    ]


def time05_target():
    return [
        CoreCmp(
            threshold_raw=1,
        ),
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreReset(
            value_raw=0,
        ),
    ]


def test_default_domain_rewrite_remains_fail_closed():
    source = time05_source()

    assert (
        _remove_pre_acc_shift_under_cmp1_reset0(
            source
        )
        == source
    )


def test_verified_finite_domain_enables_valid_candidate():
    source = time05_source()

    d = domain(
        ExecutionCase(
            train=train(
                (1, 0),
            ),
            initial_raw=0,
        ),
    )

    with verified_finite_domain_rules(d):
        result = (
            _remove_pre_acc_shift_under_cmp1_reset0(
                source
            )
        )

    assert result == time05_target()


def test_false_target_defined_premise_rejects_candidate():
    source = time05_source()

    #
    # Known D-TIME-05 DO witness:
    #
    # source:
    #   254 -> SHIFT(delta=1) -> 127 -> ACC(+2) -> 129
    #
    # target:
    #   254 -> ACC(+2) -> 256 -> overflow
    #
    d = domain(
        ExecutionCase(
            train=train(
                (1, 0),
                (1, 0),
            ),
            initial_raw=254,
        ),
    )

    with verified_finite_domain_rules(d):
        result = (
            _remove_pre_acc_shift_under_cmp1_reset0(
                source
            )
        )

    assert result == source


def test_runtime_profile_cannot_be_overridden_by_verified_domain():
    source = time05_source()

    d = domain(
        ExecutionCase(
            train=train(
                (1, 0),
            ),
            initial_raw=0,
        ),
    )

    with verified_finite_domain_rules(d):
        with canonicalization_profile(
            CanonicalizationProfile.RUNTIME
        ):
            result = (
                _remove_pre_acc_shift_under_cmp1_reset0(
                    source
                )
            )

    assert result == source


def test_abstract_bound_is_self_certified_only_inside_verified_context():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            ShiftDecay(
                bits_per_tick=2,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
        )
    )

    d = domain(
        ExecutionCase(
            train=train(
                (1, 0),
            ),
            initial_raw=0,
        ),
    )

    #
    # Still fail-closed by default.
    #
    assert (
        _normalize_temporal_shift_width(
            CONFIG,
            source,
        )
        == source
    )

    #
    # Explicit verified DOMAIN context lets the matcher use its own
    # already-proved ABSTRACT_BOUND certificate.
    #
    with verified_finite_domain_rules(d):
        assert (
            _normalize_temporal_shift_width(
                CONFIG,
                source,
            )
            == expected
        )

    #
    # Config-sensitive evidence must not cross configuration semantics.
    #
    other_config = CoreConfig(
        state_bits=16,
        fractional_bits=0,
    )

    with verified_finite_domain_rules(d):
        assert (
            _normalize_temporal_shift_width(
                other_config,
                source,
            )
            == source
        )
