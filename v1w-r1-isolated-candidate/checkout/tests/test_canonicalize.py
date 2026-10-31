from spk.operators import Decay
from search.canonicalize import canonicalize
from spk.operators import (
    Acc,
    Compare,
    Emit,
    Reset,
)
from spk.program import Program


def test_zero_acc_is_removed():
    program = Program(
        (
            Acc(
                weight=0.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(())


def test_adjacent_accs_are_combined():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=3.0,
                channel=0,
            ),
        )
    )


def test_accs_on_different_channels_are_not_combined():
    program = Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=1,
            ),
        )
    )

    assert canonicalize(program) == program


def test_adjacent_compares_keep_only_last():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=2.0,
            ),
        )
    )


def test_adjacent_resets_keep_only_last():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=1.0,
            ),
            Reset(
                value=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=2.0,
            ),
        )
    )


def test_emit_before_compare_is_removed():
    program = Program(
        (
            Emit(
                channel_out=0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )


def test_reset_before_compare_is_removed():
    program = Program(
        (
            Reset(
                value=7.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
        )
    )


def test_emit_after_compare_is_preserved():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_reset_after_compare_is_preserved():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_rewriting_reaches_fixed_point():
    program = Program(
        (
            Acc(
                weight=0.0,
                channel=0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=3.0,
                channel=0,
            ),
        )
    )


def test_canonicalization_is_idempotent():
    program = Program(
        (
            Acc(
                weight=0.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=1.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    once = canonicalize(program)
    twice = canonicalize(once)

    assert once == twice


def test_compare_overwritten_before_use_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=3.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=3.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )


def test_compare_is_preserved_if_emit_reads_guard():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_compare_before_reset_is_preserved_and_later_compare_is_normalized():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_emit_commutes_left_across_acc():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Emit(
                channel_out=0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Acc(
                weight=3.0,
                channel=0,
            ),
        )
    )


def test_emit_commutes_left_across_reset():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )


def test_compare_overwritten_before_use_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=3.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=3.0,
                channel=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )


def test_compare_is_preserved_if_emit_reads_guard():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_emit_commutes_left_across_acc():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Emit(
                channel_out=0,
            ),
            Acc(
                weight=2.0,
                channel=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Acc(
                weight=3.0,
                channel=0,
            ),
        )
    )


def test_emit_commutes_left_across_reset():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )


def test_identical_compare_after_emit_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )


def test_identical_compare_after_multiple_emits_is_removed():
    program = Program(
        (
            Compare(
                threshold=2.0,
            ),
            Emit(
                channel_out=0,
            ),
            Emit(
                channel_out=0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=2.0,
            ),
            Emit(
                channel_out=0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )


def test_compare_before_acc_is_removed_when_later_compare_overwrites_it():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Acc(
                weight=1.0,
                channel=0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_compare_after_reset_is_not_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_guarded_reset_establishes_strict_upper_bound():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_emit_after_provably_false_compare_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=2.0,
            ),
            Emit(
                channel_out=0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_reset_after_provably_false_compare_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_shadowed_reset_is_removed():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )


def test_reset_is_not_shadowed_across_compare():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    canonical = canonicalize(program)

    assert canonical != Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )



def test_zero_reset_commutes_left_across_decay():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=2.0,
            ),
            Reset(
                value=0.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=2.0,
            ),
        )
    )


def test_nonzero_reset_does_not_commute_across_decay():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=2.0,
            ),
            Reset(
                value=1.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_positive_upper_bound_survives_decay():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=2.0,
            ),
            Compare(
                threshold=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=2.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_negative_upper_bound_is_not_assumed_to_survive_decay():
    program = Program(
        (
            Compare(
                threshold=-1.0,
            ),
            Reset(
                value=-2.0,
            ),
            Decay(
                tau=2.0,
            ),
            Compare(
                threshold=-1.0,
            ),
        )
    )

    canonical = canonicalize(program)

    assert canonical.operators[-1] == Compare(
        threshold=-1.0,
    )


def test_provably_false_compare_moves_right_across_decay():
    program = Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=1.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=2.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_negative_false_compare_does_not_move_across_decay():
    program = Program(
        (
            Compare(
                threshold=-1.0,
            ),
            Reset(
                value=-2.0,
            ),
            Compare(
                threshold=-1.0,
            ),
            Decay(
                tau=2.0,
            ),
        )
    )

    assert canonicalize(program) == program


def test_two_decay_two_fuse_to_decay_one():
    program = Program(
        (
            Decay(tau=2.0),
            Decay(tau=2.0),
        )
    )

    assert canonicalize(program) == Program(
        (
            Decay(tau=1.0),
        )
    )


def test_mixed_decay_order_has_same_canonical_form():
    left = Program(
        (
            Decay(tau=1.0),
            Decay(tau=2.0),
        )
    )

    right = Program(
        (
            Decay(tau=2.0),
            Decay(tau=1.0),
        )
    )

    assert (
        canonicalize(left)
        ==
        canonicalize(right)
    )


def test_three_decay_run_is_order_independent():
    first = Program(
        (
            Decay(tau=1.0),
            Decay(tau=2.0),
            Decay(tau=1.0),
        )
    )

    second = Program(
        (
            Decay(tau=1.0),
            Decay(tau=1.0),
            Decay(tau=2.0),
        )
    )

    assert (
        canonicalize(first)
        ==
        canonicalize(second)
    )


def test_decay_fusion_does_not_cross_acc():
    program = Program(
        (
            Decay(tau=2.0),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Decay(tau=2.0),
        )
    )

    assert canonicalize(program) == program


def test_emit_compare_cycle_is_reduced():
    program = Program(
        (
            Compare(threshold=2.0),
            Emit(channel_out=0),
            Compare(threshold=1.0),
            Emit(channel_out=0),
            Compare(threshold=2.0),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(threshold=1.0),
            Emit(channel_out=0),
            Compare(threshold=2.0),
            Emit(channel_out=0),
        )
    )


def test_subsumed_guarded_reset_chain_is_reduced():
    program = Program(
        (
            Compare(threshold=2.0),
            Reset(value=0.0),
            Compare(threshold=1.0),
            Reset(value=0.0),
            Compare(threshold=1.0),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(threshold=1.0),
            Reset(value=0.0),
            Compare(threshold=1.0),
        )
    )


def test_emit_reset_threshold_partition_is_normalized():
    program = Program(
        (
            Compare(threshold=2.0),
            Emit(channel_out=0),
            Reset(value=0.0),
            Compare(threshold=1.0),
            Emit(channel_out=0),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(threshold=1.0),
            Emit(channel_out=0),
            Compare(threshold=2.0),
            Reset(value=0.0),
            Compare(threshold=1.0),
        )
    )


def test_emit_compare_cycle_requires_same_emit():
    program = Program(
        (
            Compare(threshold=2.0),
            Emit(channel_out=0),
            Compare(threshold=1.0),
            Emit(channel_out=1),
            Compare(threshold=2.0),
        )
    )

    assert canonicalize(program) == program


def test_positive_tick_false_compare_sinks_across_decay():
    program = Program(
        (
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=1.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=1.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=0.5,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_positive_tick_false_compare_sinks_across_mixed_decay():
    program = Program(
        (
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=1.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=2.0,
            ),
        )
    )

    assert canonicalize(program) == Program(
        (
            Compare(
                threshold=2.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=2.0 / 3.0,
            ),
            Compare(
                threshold=1.0,
            ),
        )
    )


def test_compare_does_not_sink_when_decay_is_insufficient():
    program = Program(
        (
            Compare(
                threshold=3.0,
            ),
            Reset(
                value=0.0,
            ),
            Decay(
                tau=1.0,
            ),
            Compare(
                threshold=1.0,
            ),
            Decay(
                tau=1.0,
            ),
        )
    )

    canonical = canonicalize(
        program
    )

    #
    # 3/e > 1, so the intermediate CMP(1) can still be true.
    #
    assert canonical == program
