from __future__ import annotations

from spk.event import SpikeTrain

from spk_core.canonicalize import (
    canonicalize_core_program,
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
    abstract_normalize_program,
    canonicalize_core_program_semantic,
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
    return CoreProgram(
        (
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
        )
    )


def time05_target():
    return CoreProgram(
        (
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
        )
    )


def acc03_source():
    return CoreProgram(
        (
            CoreAcc(
                weight=3,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )


def acc03_target():
    return CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )


def acc01_source():
    return CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )


def acc01_target():
    return CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )


def time01_source():
    return CoreProgram(
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


def time01_target():
    return CoreProgram(
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


def valid_domain():
    return domain(
        ExecutionCase(
            train=train(
                (1, 0),
            ),
            initial_raw=0,
        ),
    )


def test_public_core_default_remains_fail_closed():
    source = time05_source()

    assert (
        canonicalize_core_program(
            source
        )
        == source
    )


def test_public_core_accepts_valid_target_defined_rewrite():
    source = time05_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        result = canonicalize_core_program(
            source
        )

    assert result == time05_target()


def test_public_core_rejects_false_target_defined_premise():
    source = time05_source()

    #
    # D-TIME-05 DO witness:
    #
    # source remains defined because the shift reduces raw before ACC;
    # target overflows after removal of that shift.
    #
    invalid = domain(
        ExecutionCase(
            train=train(
                (1, 0),
                (1, 0),
            ),
            initial_raw=254,
        ),
    )

    with verified_finite_domain_rules(
        invalid
    ):
        result = canonicalize_core_program(
            source
        )

    assert result == source


def test_public_core_config_sensitive_domain_rule():
    source = acc03_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        result = canonicalize_core_program(
            source,
            config=CONFIG,
        )

    assert result == acc03_target()


def test_public_semantic_program_rule_uses_verified_domain():
    source = acc01_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        result = abstract_normalize_program(
            CONFIG,
            source,
        )

    assert result == acc01_target()


def test_public_abstract_bound_requires_explicit_verified_context():
    source = time01_source()

    #
    # DOMAIN remains fail-closed despite the matcher being able to prove
    # its own ABSTRACT_BOUND premise.
    #
    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == source
    )

    with verified_finite_domain_rules(
        valid_domain()
    ):
        result = abstract_normalize_program(
            CONFIG,
            source,
        )

    assert result == time01_target()


def test_runtime_profile_dominates_verified_domain_context():
    structural = time05_source()
    semantic = time01_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        with canonicalization_profile(
            CanonicalizationProfile.RUNTIME
        ):
            structural_result = (
                canonicalize_core_program(
                    structural
                )
            )

            semantic_result = (
                abstract_normalize_program(
                    CONFIG,
                    semantic,
                )
            )

    assert structural_result == structural
    assert semantic_result == semantic


def test_joint_public_fixed_point_preserves_verified_authorization():
    source = time01_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        result = (
            canonicalize_core_program_semantic(
                source,
                config=CONFIG,
            )
        )

    assert result == time01_target()


def test_verified_domain_context_does_not_leak():
    source = time05_source()

    with verified_finite_domain_rules(
        valid_domain()
    ):
        inside = canonicalize_core_program(
            source
        )

    outside = canonicalize_core_program(
        source
    )

    assert inside == time05_target()
    assert outside == source
