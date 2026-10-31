from spk_core.abstract import (
    analyze_program,
    equivalent_threshold_interval,
)
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreProgram,
    CoreReset,
)


CONFIG = CoreConfig(
    state_bits=16,
    fractional_bits=0,
)


def test_cmp1_reset0_proves_exact_zero_state():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    steps = analyze_program(
        CONFIG,
        program,
    )

    final_raw = (
        steps[-1]
        .after
        .merged
    )

    assert final_raw.is_exact
    assert final_raw.exact_value == 0


def test_acc2_after_known_zero_tracks_even_states():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreAcc(
                weight=2,
                channel=0,
            ),
        )
    )

    steps = analyze_program(
        CONFIG,
        program,
    )

    raw = (
        steps[-1]
        .after
        .merged
    )

    assert raw.lower == 0
    assert raw.modulus == 2
    assert raw.residue == 0


def test_cmp1_and_cmp2_are_equivalent_over_even_states():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreAcc(
                weight=2,
                channel=0,
            ),
        )
    )

    steps = analyze_program(
        CONFIG,
        program,
    )

    raw = (
        steps[-1]
        .after
        .merged
    )

    assert (
        equivalent_threshold_interval(
            raw,
            2,
        )
        == (
            1,
            2,
        )
    )


def test_join_exact_zero_with_even_domain_preserves_evenness():
    from spk_core.abstract import (
        RawSet,
        join_raw,
    )

    exact_zero = RawSet.exact(
        0
    )

    even = RawSet(
        lower=0,
        upper=100,
        modulus=2,
        residue=0,
    )

    joined = join_raw(
        exact_zero,
        even,
    )

    assert joined.modulus == 2
    assert joined.residue == 0


def test_conditional_reset_join_preserves_even_states():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    steps = analyze_program(
        CONFIG,
        program,
    )

    raw = (
        steps[-1]
        .after
        .merged
    )

    assert raw.modulus == 2
    assert raw.residue == 0


def test_thresholds_one_and_two_equivalent_after_conditional_even_reset():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    steps = analyze_program(
        CONFIG,
        program,
    )

    raw = (
        steps[-1]
        .after
        .merged
    )

    assert (
        equivalent_threshold_interval(
            raw,
            2,
        )
        == (
            1,
            2,
        )
    )
