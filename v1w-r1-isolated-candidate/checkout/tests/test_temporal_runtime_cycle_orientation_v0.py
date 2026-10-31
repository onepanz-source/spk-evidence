from __future__ import annotations

from spk_core.canonicalize import (
    _sink_known_false_compare_across_shift,
)
from spk_core.isa import (
    CoreCmp,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.semantic_canonicalize import (
    _normalize_temporal_guarded_reset_commute,
)


def no_emit_left_form():
    return CoreProgram(
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


def no_emit_right_form():
    return CoreProgram(
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


def test_ltime09_yields_empty_emit_overlap_to_ltime05():
    left = no_emit_left_form()

    assert (
        _normalize_temporal_guarded_reset_commute(
            left
        )
        == left
    )


def test_ltime05_orients_empty_emit_overlap_to_left_form():
    right = no_emit_right_form()

    result = (
        _sink_known_false_compare_across_shift(
            right.instructions
        )
    )

    assert CoreProgram(
        tuple(result)
    ) == no_emit_left_form()


def test_empty_emit_pair_no_longer_forms_two_cycle():
    right = no_emit_right_form()

    after_structural = CoreProgram(
        tuple(
            _sink_known_false_compare_across_shift(
                right.instructions
            )
        )
    )

    after_semantic = (
        _normalize_temporal_guarded_reset_commute(
            after_structural
        )
    )

    assert (
        after_structural
        == no_emit_left_form()
    )

    assert (
        after_semantic
        == after_structural
    )


def test_ltime09_still_normalizes_positive_emit_case():
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
        _normalize_temporal_guarded_reset_commute(
            source
        )
        == expected
    )
