from spk_core.rules import unchecked_domain_rules

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreEmit,
    CoreProgram,
    CoreReset,
)


def canonical(*instructions):
    return canonicalize_core_program(
        CoreProgram(
            tuple(
                instructions
            )
        )
    )


def test_false_guard_prefix_is_removed():
    assert canonical(
        CoreEmit(
            channel_out=7
        ),
        CoreReset(
            value_raw=0
        ),
        CoreCmp(
            threshold_raw=1
        ),
    ) == CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
        )
    )


def test_dead_compare_before_compare_is_removed():
    assert canonical(
        CoreCmp(
            threshold_raw=1
        ),
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2
        ),
    ) == CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2
            ),
        )
    )


def test_final_compare_is_preserved():
    assert canonical(
        CoreCmp(
            threshold_raw=1
        ),
    ) == CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
        )
    )


def test_adjacent_resets_collapse():
    assert canonical(
        CoreCmp(
            threshold_raw=1
        ),
        CoreReset(
            value_raw=1
        ),
        CoreReset(
            value_raw=0
        ),
    ) == CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreReset(
                value_raw=0
            ),
        )
    )


def test_emit_moves_before_reset():
    assert canonical(
        CoreCmp(
            threshold_raw=1
        ),
        CoreReset(
            value_raw=0
        ),
        CoreEmit(
            channel_out=7
        ),
    ) == CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreEmit(
                channel_out=7
            ),
            CoreReset(
                value_raw=0
            ),
        )
    )


def test_acc_same_channel_fuses():
    assert canonical(
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2
        ),
    ) == CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2
            ),
        )
    )


def test_acc_different_channels_are_sorted():
    assert canonical(
        CoreAcc(
            weight=1,
            channel=1,
        ),
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2
        ),
    ) == CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=2
            ),
        )
    )


def test_canonicalization_is_idempotent():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2
            ),
            CoreReset(
                value_raw=0
            ),
            CoreEmit(
                channel_out=7
            ),
        )
    )

    once = (
        canonicalize_core_program(
            source
        )
    )

    twice = (
        canonicalize_core_program(
            once
        )
    )

    assert once == twice


def test_repeated_compare_after_emit_is_removed():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreEmit(
                channel_out=7
            ),
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreEmit(
                channel_out=7
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_compare_is_not_reused_after_state_change():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreEmit(
                channel_out=7
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == source
    )


def test_false_compare_after_reset_is_normalized():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreReset(
                value_raw=0
            ),
            CoreCmp(
                threshold_raw=2
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreReset(
                value_raw=0
            ),
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_false_guard_effects_after_reset_compare_are_removed():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreReset(
                value_raw=0
            ),
            CoreCmp(
                threshold_raw=2
            ),
            CoreEmit(
                channel_out=7
            ),
            CoreReset(
                value_raw=0
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
            CoreReset(
                value_raw=0
            ),
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_reset_not_below_threshold_does_not_trigger_false_rule():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2
            ),
            CoreReset(
                value_raw=2
            ),
            CoreCmp(
                threshold_raw=2
            ),
            CoreEmit(
                channel_out=7
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == source
    )


def test_saturated_acc_moves_across_compare():
    from spk_core.isa import CoreConfig

    config = CoreConfig(
        state_bits=16,
        fractional_bits=0,
    )

    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=2,
                channel=0,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreAcc(
                weight=3,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source,
            config=config,
        )
        == expected
    )


def test_saturated_acc_moves_across_emit():
    from spk_core.isa import CoreConfig

    config = CoreConfig(
        state_bits=16,
        fractional_bits=0,
    )

    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source,
            config=config,
        )
        == expected
    )


@unchecked_domain_rules()
def test_guarded_reset_caps_saturated_weight():
    from spk_core.isa import CoreConfig

    config = CoreConfig(
        state_bits=16,
        fractional_bits=0,
    )

    source = CoreProgram(
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

    expected = CoreProgram(
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

    assert (
        canonicalize_core_program(
            source,
            config=config,
        )
        == expected
    )


@unchecked_domain_rules()
def test_shadowed_reset_is_removed():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
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

    expected = CoreProgram(
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

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


@unchecked_domain_rules()
def test_lsb_compare_reset_compare_annihilates_preceding_acc():
    source = CoreProgram(
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
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_saturated_acc_moves_from_later_in_post_compare_acc_run():
    from spk_core.isa import CoreConfig

    config = CoreConfig(
        state_bits=16,
        fractional_bits=0,
    )

    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source,
            config=config,
        )
        == expected
    )


def test_adjacent_shift_decay_fuses():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=1
            ),
            ShiftDecay(
                bits_per_tick=2
            ),
        )
    )

    expected = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=3
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_zero_shift_decay_is_identity():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=0
            ),
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_zero_reset_commutes_with_shift():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_shift_between_cmp1_and_reset0_is_dead():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


def test_shift_after_cmp1_reset0_is_dead():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
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

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        canonicalize_core_program(
            source
        )
        == expected
    )


@unchecked_domain_rules()
def test_cmp1_shift_acc0_reset_collapses():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
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

    expected = CoreProgram(
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

    assert (
        canonicalize_core_program(source)
        == expected
    )


@unchecked_domain_rules()
def test_cmp1_shift_acc1_reset_collapses():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            ShiftDecay(
                bits_per_tick=1,
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

    expected = CoreProgram(
        (
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

    assert (
        canonicalize_core_program(source)
        == expected
    )


def test_known_false_cmp_sinks_across_shift():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
        )
    )

    assert (
        canonicalize_core_program(source)
        == expected
    )


def test_guarded_shift_saturates_under_cmp2_bound():
    from spk_core.isa import ShiftDecay

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    assert (
        canonicalize_core_program(source)
        == expected
    )
