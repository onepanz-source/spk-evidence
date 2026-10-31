from __future__ import annotations

import inspect

from spk.event import SpikeTrain

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)

from spk_core.runtime import run_core_program

from spk_core.semantic_canonicalize import (
    _normalize_temporal_shift_width,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def raw_rule():
    return inspect.unwrap(
        _normalize_temporal_shift_width
    )


def test_temporal_shift_width_does_not_cross_acc_before_reset():
    """
    Regression for the D-TIME-01 overflow counterexample.

    Source:

        CMP(2); SHIFT(2); ACC(129,c0); RESET(0)

    with initial_raw=255, delta=1 and one c0 event is defined:

        255 >> 2 = 63
        63 + 129 = 192

    Replacing SHIFT(2) by SHIFT(1) would instead produce:

        255 >> 1 = 127
        127 + 129 = 256

    and therefore observable overflow.

    The rule must not rewrite this program.
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
                weight=129,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    target = raw_rule()(
        CONFIG,
        source,
    )

    assert target == source

    result = run_core_program(
        CONFIG,
        source,
        SpikeTrain.from_pairs(
            [
                (1, 0),
            ]
        ),
        initial_raw=255,
    )

    assert result.final_raw == 0
    assert result.final_guard is True


def test_temporal_shift_width_still_allows_emit_before_safe_reset():
    """
    The guarded-reset case remains valid when only EMIT instructions
    occur between SHIFT and RESET(0).
    """

    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=2,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    target = raw_rule()(
        CONFIG,
        source,
    )

    assert target == CoreProgram(
        (
            CoreCmp(
                threshold_raw=2,
            ),
            ShiftDecay(
                bits_per_tick=1,
            ),
            CoreEmit(
                channel_out=7,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )
