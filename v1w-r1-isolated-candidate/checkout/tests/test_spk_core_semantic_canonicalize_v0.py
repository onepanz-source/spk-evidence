from spk_core.rules import unchecked_domain_rules

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)

from spk_core.semantic_canonicalize import (
    abstract_normalize_program,
)


CONFIG = CoreConfig(
    state_bits=16,
    fractional_bits=0,
)


def test_semantic_pass_removes_emit_under_known_false_guard():
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
            CoreEmit(
                channel_out=7,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_pass_removes_reset_under_known_false_guard():
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
            CoreReset(
                value_raw=0,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_pass_removes_shift_of_known_zero():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
            ShiftDecay(
                bits_per_tick=3,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_pass_canonicalizes_equivalent_cmp_threshold():
    source = CoreProgram(
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
            CoreCmp(
                threshold_raw=2,
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
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


@unchecked_domain_rules()
def test_semantic_zero_barrier_removes_dead_acc_prefix():
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
            CoreAcc(
                weight=1,
                channel=1,
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
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


@unchecked_domain_rules()
def test_semantic_zero_barrier_removes_dead_shift_prefix():
    source = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=1,
            ),
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
            CoreCmp(
                threshold_raw=2,
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
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_zero_barrier_keeps_prefix_if_guard_is_emitted():
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
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert (
        normalized.instructions[0]
        == CoreAcc(
            weight=1,
            channel=0,
        )
    )


def test_semantic_zero_barrier_keeps_prefix_if_guard_is_final():
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
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert (
        normalized.instructions[0]
        == CoreAcc(
            weight=1,
            channel=0,
        )
    )


def test_semantic_control_trace_normalizes_emit_multiset_final_cmp1():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_control_trace_normalizes_emit_multiset_final_cmp2():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_control_trace_preserves_emit_multiplicity():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_emit_reset_partition_normalizes_residual():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=2,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_emit_reset_partition_general_thresholds():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=5,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=1,
            ),
            CoreCmp(
                threshold_raw=3,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=3,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreCmp(
                threshold_raw=5,
            ),
            CoreReset(
                value_raw=1,
            ),
            CoreCmp(
                threshold_raw=3,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_emit_reset_partition_requires_reset_below_a():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=5,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=3,
            ),
            CoreCmp(
                threshold_raw=3,
            ),
            CoreEmit(
                channel_out=7,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert normalized == source


def test_semantic_emit_reset_partition_requires_same_emit_channel():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreEmit(
                channel_out=8,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert normalized == source


@unchecked_domain_rules()
def test_semantic_acc_cmp1_zero_reset_saturates_weight_ch0():
    source = CoreProgram(
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

    expected = CoreProgram(
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

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


@unchecked_domain_rules()
def test_semantic_acc_cmp1_zero_reset_saturates_weight_ch1():
    source = CoreProgram(
        (
            CoreAcc(
                weight=7,
                channel=1,
            ),
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

    expected = CoreProgram(
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
            CoreReset(
                value_raw=0,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_semantic_acc_cmp1_saturation_requires_zero_reset():
    source = CoreProgram(
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
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == source
    )


def test_semantic_acc_cmp1_saturation_stops_at_next_cmp():
    source = CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    expected = CoreProgram(
        (
            CoreAcc(
                weight=2,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    assert normalized == expected

    assert (
        normalized.instructions[0]
        == CoreAcc(
            weight=2,
            channel=0,
        )
    )


def test_temporal_cmp2_barrier_removes_leading_shift():
    source = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=1,
            ),
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
                threshold_raw=1,
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
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_temporal_cmp2_barrier_removes_trailing_shift():
    source = CoreProgram(
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
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_temporal_guarded_reset_commutes_shift():
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
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

    expected = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
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

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


@unchecked_domain_rules()
def test_temporal_shift_width_saturates_on_state_bounded_by_one():
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

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_temporal_shift_width_does_not_cross_acc_before_true_branch_reset():
    """
    ACC cannot be treated as harmless merely because it preserves guard.

    Replacing SHIFT(k>1) by SHIFT(1) may increase the raw value seen by
    the following ACC and therefore introduce observable overflow before
    RESET(0).

    The guarded-reset temporal-width rule must consequently stop at ACC.
    """

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=2,
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
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == source
    )


def test_temporal_shift_width_not_saturated_without_bounded_or_reset_branch():
    source = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert (
        normalized.instructions[0]
        == ShiftDecay(
            bits_per_tick=2,
        )
    )


def test_shared_count_cmp1_commutes_across_same_channel_acc():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
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

    expected = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    assert (
        abstract_normalize_program(
            CONFIG,
            source,
        )
        == expected
    )


def test_shared_count_cmp1_does_not_commute_across_different_channel():
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
                weight=1,
                channel=1,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert (
        normalized.instructions[-2:]
        == (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
        )
    )


@unchecked_domain_rules()
def test_shared_count_pre_shift_acc_is_redundant_before_cmp1_reset():
    source = CoreProgram(
        (
            CoreAcc(
                weight=3,
                channel=1,
            ),
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreAcc(
                weight=2,
                channel=1,
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
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert normalized == expected

    #
    # The important property of this test:
    # the leading same-channel ACC has disappeared.
    #
    assert not (
        normalized.instructions
        and normalized.instructions[0]
        == CoreAcc(
            weight=3,
            channel=1,
        )
    )


def test_shared_count_pre_shift_acc_requires_same_channel():
    source = CoreProgram(
        (
            CoreAcc(
                weight=1,
                channel=0,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
            CoreAcc(
                weight=1,
                channel=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    normalized = (
        abstract_normalize_program(
            CONFIG,
            source,
        )
    )

    assert (
        normalized.instructions[0]
        == CoreAcc(
            weight=1,
            channel=0,
        )
    )
