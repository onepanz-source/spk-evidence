from __future__ import annotations

from spk_core.canonicalize import (
    canonicalize_core_program,
    canonicalize_core_program_runtime,
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
    unchecked_domain_rules,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def domain_fixture() -> CoreProgram:
    #
    # D-TIME-05 can remove SHIFT(1):
    #
    #   CMP(1); SHIFT(1); ACC(1,c0); RESET(0)
    #
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


def test_default_canonicalization_is_domain_fail_closed():
    source = domain_fixture()

    default = canonicalize_core_program(
        source,
        config=CONFIG,
    )

    runtime = canonicalize_core_program_runtime(
        source,
        config=CONFIG,
    )

    #
    # Merely using the historical FULL profile must no longer be
    # sufficient to activate DOMAIN rules.
    #
    assert default == runtime


def test_unchecked_domain_rules_requires_explicit_opt_in():
    source = domain_fixture()

    runtime = canonicalize_core_program_runtime(
        source,
        config=CONFIG,
    )

    with canonicalization_profile(
        CanonicalizationProfile.FULL
    ):
        with unchecked_domain_rules():
            unchecked = canonicalize_core_program(
                source,
                config=CONFIG,
            )

    #
    # The historical DOMAIN rewrite remains reachable for proof/search
    # purposes, but only through an explicit unsafe capability.
    #
    assert unchecked != runtime

    assert ShiftDecay(
        bits_per_tick=1
    ) not in unchecked.instructions


def test_runtime_profile_cannot_be_overridden_by_unchecked_domain_scope():
    source = domain_fixture()

    expected = canonicalize_core_program_runtime(
        source,
        config=CONFIG,
    )

    with unchecked_domain_rules():
        actual = canonicalize_core_program_runtime(
            source,
            config=CONFIG,
        )

    assert actual == expected
