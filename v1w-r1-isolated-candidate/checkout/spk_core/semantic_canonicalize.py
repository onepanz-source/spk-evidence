from __future__ import annotations

from .rules import (
    CanonicalizationProfile,
    canonicalization_profile,
    domain_config_program_rule,
    domain_program_rule,
)

from .abstract import (
    analyze_program,
    equivalent_threshold_interval,
)
from .canonicalize import (
    canonicalize_core_program,
)
from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)








def _normalize_shared_count_cmp1_acc_commute(
    program: CoreProgram,
) -> CoreProgram:
    """
    Shared-batch-count law.

    Suppose a positive ACC on channel c has already contributed the
    batch count n_c to the current state, with no RESET or SHIFT since.

        state = x + w*n_c + other_nonnegative_terms
        w > 0

    Then:

        state >= 1
            iff
        state + v*n_c >= 1

    for every v > 0.

    Hence:

        ... ACC(w,c) ... CMP(1); ACC(v,c)

    may normalize to:

        ... ACC(w,c) ... ACC(v,c); CMP(1)

    when the region between the anchor ACC and CMP contains only
    nonnegative ACCs and state-preserving CMP/EMIT instructions.

    The essential fact is that both ACC instructions consume the same
    batch count n_c.
    """

    instructions = list(
        program.instructions
    )

    for cmp_index in range(
        len(instructions) - 1
    ):
        compare = instructions[
            cmp_index
        ]

        trailing_acc = instructions[
            cmp_index + 1
        ]

        if not (
            isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 1
            and isinstance(
                trailing_acc,
                CoreAcc,
            )
            and trailing_acc.weight > 0
        ):
            continue

        channel = (
            trailing_acc.channel
        )

        cursor = (
            cmp_index - 1
        )

        anchor_found = False

        while cursor >= 0:
            current = instructions[
                cursor
            ]

            if isinstance(
                current,
                (
                    CoreReset,
                    ShiftDecay,
                ),
            ):
                break

            if isinstance(
                current,
                CoreAcc,
            ):
                if (
                    current.weight > 0
                    and current.channel == channel
                ):
                    anchor_found = True
                    break

                cursor -= 1
                continue

            if isinstance(
                current,
                (
                    CoreCmp,
                    CoreEmit,
                ),
            ):
                cursor -= 1
                continue

            break

        if not anchor_found:
            continue

        instructions[
            cmp_index
        ] = trailing_acc

        instructions[
            cmp_index + 1
        ] = compare

        return CoreProgram(
            tuple(instructions)
        )

    return program


@domain_program_rule
def _normalize_shared_count_pre_shift_acc(
    program: CoreProgram,
) -> CoreProgram:
    """
    Shared-count / shared-delta identity.

    For nonnegative x and batch count n_c:

        ((x + w*n_c) >> (k*delta)) + v*n_c > 0

    iff

        (x >> (k*delta)) + v*n_c > 0

    whenever:

        w > 0
        v > 0
        k > 0

    Proof by cases:

      n_c > 0:
          the final +v*n_c makes both sides positive.

      n_c == 0:
          both expressions reduce to x >> (k*delta).

    Therefore the leading ACC can be removed in:

        ACC(w,c);
        SHIFT(k);
        ACC(v,c);
        CMP(1);
        RESET(r)

    because both programs take the same CMP branch and consequently
    reach the same final state and guard.

    As elsewhere in the current semantic canonicalizer, this law is
    interpreted over the declared non-overflowing synthesis domain.
    """

    instructions = list(
        program.instructions
    )

    for index in range(
        len(instructions) - 4
    ):
        first_acc = instructions[
            index
        ]

        shift = instructions[
            index + 1
        ]

        second_acc = instructions[
            index + 2
        ]

        compare = instructions[
            index + 3
        ]

        reset = instructions[
            index + 4
        ]

        if not (
            isinstance(
                first_acc,
                CoreAcc,
            )
            and first_acc.weight > 0
            and isinstance(
                shift,
                ShiftDecay,
            )
            and shift.bits_per_tick > 0
            and isinstance(
                second_acc,
                CoreAcc,
            )
            and second_acc.weight > 0
            and first_acc.channel
                == second_acc.channel
            and isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 1
            and isinstance(
                reset,
                CoreReset,
            )
        ):
            continue

        del instructions[
            index
        ]

        return CoreProgram(
            tuple(instructions)
        )

    return program


def _normalize_temporal_cmp2_barrier(
    program: CoreProgram,
) -> CoreProgram:
    """
    Shared-delta temporal identities for unsigned Core.

    With positive ShiftDecay widths, all shifts executed in a batch
    use the same delta.

    Two useful CMP(2)/RESET(0) barrier laws follow.

    1)

        SHIFT(p); CMP(2); SHIFT(q); RESET(0); CMP(t)

    is equivalent to

        CMP(2); SHIFT(q); RESET(0); CMP(t)

    for p,q > 0.

    If delta == 0 both shifts are identities.

    If delta > 0, any state which falls below threshold 2 after the
    first shift is in {0,1}; the second positive shift maps it to 0.
    States still >=2 are reset to 0.

    The trailing CMP overwrites the possibly different guard produced
    by the first CMP.

    2)

        CMP(2); SHIFT(q); RESET(0); CMP(t); SHIFT(p)

    is equivalent to

        CMP(2); SHIFT(q); RESET(0); CMP(t)

    because after the reset barrier the state is:
      * at most 1 when delta == 0;
      * exactly 0 when delta > 0.

    Hence the final shift is an identity in both delta cases.
    """

    instructions = list(
        program.instructions
    )

    #
    # Leading shift before the CMP(2) temporal barrier.
    #
    for index in range(
        len(instructions) - 4
    ):
        first_shift = instructions[
            index
        ]

        compare = instructions[
            index + 1
        ]

        second_shift = instructions[
            index + 2
        ]

        reset = instructions[
            index + 3
        ]

        final_cmp = instructions[
            index + 4
        ]

        if (
            isinstance(
                first_shift,
                ShiftDecay,
            )
            and first_shift.bits_per_tick > 0
            and isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 2
            and isinstance(
                second_shift,
                ShiftDecay,
            )
            and second_shift.bits_per_tick > 0
            and isinstance(
                reset,
                CoreReset,
            )
            and reset.value_raw == 0
            and isinstance(
                final_cmp,
                CoreCmp,
            )
        ):
            del instructions[
                index
            ]

            return CoreProgram(
                tuple(instructions)
            )

    #
    # Trailing shift after the same barrier.
    #
    for index in range(
        len(instructions) - 4
    ):
        compare = instructions[
            index
        ]

        shift = instructions[
            index + 1
        ]

        reset = instructions[
            index + 2
        ]

        final_cmp = instructions[
            index + 3
        ]

        trailing_shift = instructions[
            index + 4
        ]

        if (
            isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 2
            and isinstance(
                shift,
                ShiftDecay,
            )
            and shift.bits_per_tick > 0
            and isinstance(
                reset,
                CoreReset,
            )
            and reset.value_raw == 0
            and isinstance(
                final_cmp,
                CoreCmp,
            )
            and isinstance(
                trailing_shift,
                ShiftDecay,
            )
            and trailing_shift.bits_per_tick > 0
        ):
            del instructions[
                index + 4
            ]

            return CoreProgram(
                tuple(instructions)
            )

    return program


def _normalize_temporal_guarded_reset_commute(
    program: CoreProgram,
) -> CoreProgram:
    """
    Canonicalize:

        CMP(2); EMIT+; SHIFT(k); RESET(0); CMP(2)

    to:

        CMP(2); EMIT+; RESET(0); CMP(2); SHIFT(k)

    for k > 0.

    At least one EMIT is required.

    The empty-EMIT case overlaps with L-TIME-05:

        CMP(2); SHIFT(k); RESET(0); CMP(2)
            <->
        CMP(2); RESET(0); CMP(2); SHIFT(k)

    and would create a two-cycle between the structural and semantic
    normalizers.  Canonical orientation leaves that case to L-TIME-05.

    On the true branch RESET(0) destroys the shifted state.

    On the false branch the incoming state is in {0,1}; ShiftDecay is
    non-increasing, so the second CMP(2) is false on either side.

    EMIT instructions are allowed between the first CMP and SHIFT:
    they observe the same unchanged guard and do not alter state.
    """

    instructions = list(
        program.instructions
    )

    for start in range(
        len(instructions)
    ):
        first_cmp = instructions[
            start
        ]

        if not (
            isinstance(
                first_cmp,
                CoreCmp,
            )
            and first_cmp.threshold_raw == 2
        ):
            continue

        cursor = (
            start + 1
        )

        while (
            cursor < len(instructions)
            and isinstance(
                instructions[
                    cursor
                ],
                CoreEmit,
            )
        ):
            cursor += 1

        #
        # L-TIME-09 owns only the EMIT+ form.
        #
        # With no intervening EMIT, moving SHIFT to the right creates
        # exactly the redex that L-TIME-05 moves back to the left,
        # producing a structural/semantic two-cycle.
        #
        if cursor == start + 1:
            continue

        if (
            cursor + 2
            >= len(instructions)
        ):
            continue

        shift = instructions[
            cursor
        ]

        reset = instructions[
            cursor + 1
        ]

        second_cmp = instructions[
            cursor + 2
        ]

        if not (
            isinstance(
                shift,
                ShiftDecay,
            )
            and shift.bits_per_tick > 0
            and isinstance(
                reset,
                CoreReset,
            )
            and reset.value_raw == 0
            and isinstance(
                second_cmp,
                CoreCmp,
            )
            and second_cmp.threshold_raw == 2
        ):
            continue

        del instructions[
            cursor
        ]

        instructions.insert(
            cursor + 2,
            shift,
        )

        return CoreProgram(
            tuple(instructions)
        )

    return program


@domain_config_program_rule
def _normalize_temporal_shift_width(
    config: CoreConfig,
    program: CoreProgram,
) -> CoreProgram:
    """
    Normalize ShiftDecay(k), k>1, to ShiftDecay(1) when abstract state
    proves that all live values affected by the shift are in {0,1}.

    For x in {0,1}:

        delta == 0  -> every positive-width shift is identity
        delta > 0   -> every positive-width shift produces zero

    A second safe case exists when only the FALSE guard branch is
    bounded by 1 and the TRUE branch is guaranteed to encounter
    RESET(0) before its guard can be overwritten.
    """

    steps = analyze_program(
        config,
        program,
    )

    instructions = list(
        program.instructions
    )

    for step in steps:
        instruction = (
            step.instruction
        )

        if not (
            isinstance(
                instruction,
                ShiftDecay,
            )
            and instruction.bits_per_tick > 1
        ):
            continue

        before = (
            step.before
        )

        merged = (
            before.merged
        )

        #
        # Globally bounded state.
        #
        if (
            merged is not None
            and merged.upper <= 1
        ):
            instructions[
                step.index
            ] = ShiftDecay(
                bits_per_tick=1
            )

            return CoreProgram(
                tuple(instructions)
            )

        #
        # Guard-partitioned state:
        #
        # FALSE branch is {0,1}; TRUE branch will be destroyed by
        # RESET(0) before another CMP replaces the guard.
        #
        false_raw = (
            before.false
        )

        if (
            false_raw is None
            or false_raw.upper > 1
        ):
            continue

        cursor = (
            step.index + 1
        )

        safe_reset = False

        while cursor < len(
            instructions
        ):
            current = instructions[
                cursor
            ]

            if isinstance(
                current,
                CoreCmp,
            ):
                break

            if isinstance(
                current,
                CoreReset,
            ):
                if (
                    current.value_raw
                    == 0
                ):
                    safe_reset = True

                break

            #
            # EMIT preserves both raw state and guard.
            #
            # ACC is deliberately NOT allowed here: although it does
            # not overwrite the guard, changing SHIFT(k>1) to SHIFT(1)
            # can change the raw value seen by ACC and therefore alter
            # observable overflow before the later RESET(0).
            #
            if not isinstance(
                current,
                CoreEmit,
            ):
                break

            cursor += 1

        if safe_reset:
            instructions[
                step.index
            ] = ShiftDecay(
                bits_per_tick=1
            )

            return CoreProgram(
                tuple(instructions)
            )

    return program


@domain_program_rule
def _normalize_positive_acc_before_cmp1_zero_reset(
    program: CoreProgram,
) -> CoreProgram:
    """
    Finite-domain Core normalization.

    For unsigned state and positive ACC weight:

        x + w*n >= 1
            iff
        x + n >= 1

    for every w > 0.

    Therefore:

        ACC(w,c); CMP(1); ...; RESET(0)

    may normalize ACC weight to 1 when the CMP guard reaches RESET(0)
    before being overwritten by another CMP.

    If the guard is false, unsigned semantics imply x=0 and n=0,
    so both ACC weights also leave the same state.

    If the guard is true, RESET(0) erases the state difference.

    This rule is used under the declared non-overflowing synthesis
    domain; overflow behaviour is intentionally not generalized here.
    """

    instructions = list(
        program.instructions
    )

    for index in range(
        len(instructions) - 2
    ):
        acc = instructions[
            index
        ]

        compare = instructions[
            index + 1
        ]

        if not (
            isinstance(
                acc,
                CoreAcc,
            )
            and acc.weight > 1
            and isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 1
        ):
            continue

        cursor = (
            index + 2
        )

        found_zero_reset = False

        while cursor < len(
            instructions
        ):
            current = instructions[
                cursor
            ]

            #
            # A new CMP overwrites the guard.  Beyond this point the
            # original CMP(1) cannot justify the saturation rewrite.
            #
            if isinstance(
                current,
                CoreCmp,
            ):
                break

            if (
                isinstance(
                    current,
                    CoreReset,
                )
                and current.value_raw == 0
            ):
                found_zero_reset = True
                break

            cursor += 1

        if not found_zero_reset:
            continue

        instructions[
            index
        ] = CoreAcc(
            weight=1,
            channel=acc.channel,
        )

        return CoreProgram(
            tuple(instructions)
        )

    return program


def _normalize_emit_reset_partition(
    program: CoreProgram,
) -> CoreProgram:
    """
    Normalize the exact unsigned-Core identity:

        CMP(b); EMIT(c); RESET(r); CMP(a); EMIT(c)

    to:

        CMP(a); EMIT(c); CMP(b); RESET(r); CMP(a)

    whenever:

        r < a <= b

    The first form partitions the unsigned state into:

        x < a
        a <= x < b
        x >= b

    and emits exactly once for x >= a.

    The second form expresses that partition canonically:
    emit for x >= a, then preserve the b-threshold reset and
    reconstruct the final guard after the reset.
    """

    instructions = list(
        program.instructions
    )

    for index in range(
        len(instructions) - 4
    ):
        first_cmp = instructions[
            index
        ]

        first_emit = instructions[
            index + 1
        ]

        reset = instructions[
            index + 2
        ]

        second_cmp = instructions[
            index + 3
        ]

        second_emit = instructions[
            index + 4
        ]

        if not (
            isinstance(
                first_cmp,
                CoreCmp,
            )
            and isinstance(
                first_emit,
                CoreEmit,
            )
            and isinstance(
                reset,
                CoreReset,
            )
            and isinstance(
                second_cmp,
                CoreCmp,
            )
            and isinstance(
                second_emit,
                CoreEmit,
            )
        ):
            continue

        if (
            first_emit.channel_out
            != second_emit.channel_out
        ):
            continue

        a = (
            second_cmp.threshold_raw
        )

        b = (
            first_cmp.threshold_raw
        )

        r = (
            reset.value_raw
        )

        if not (
            r < a <= b
        ):
            continue

        channel = (
            first_emit.channel_out
        )

        replacement = (
            CoreCmp(
                threshold_raw=a,
            ),
            CoreEmit(
                channel_out=channel,
            ),
            CoreCmp(
                threshold_raw=b,
            ),
            CoreReset(
                value_raw=r,
            ),
            CoreCmp(
                threshold_raw=a,
            ),
        )

        instructions[
            index:index + 5
        ] = replacement

        return CoreProgram(
            tuple(instructions)
        )

    return program


def _normalize_cmp_emit_runs(
    program: CoreProgram,
) -> CoreProgram:
    """
    Normalize maximal state-invariant CMP/EMIT runs.

    Within such a run the raw state never changes.

    Therefore its observable semantics is determined by:

      * the multiset of emitted channels, each paired with the CMP
        threshold whose guard controls that emission;
      * the threshold of the final CMP, which determines final guard.

    Event order within a batch is not observable in SPK/Core output,
    so emission groups may be sorted canonically.
    """

    instructions = list(
        program.instructions
    )

    index = 0

    while index < len(
        instructions
    ):
        if not isinstance(
            instructions[index],
            CoreCmp,
        ):
            index += 1
            continue

        start = index
        end = start

        while (
            end < len(instructions)
            and isinstance(
                instructions[end],
                (
                    CoreCmp,
                    CoreEmit,
                ),
            )
        ):
            end += 1

        segment = instructions[
            start:end
        ]

        current_threshold = None

        emissions = []

        for instruction in segment:
            if isinstance(
                instruction,
                CoreCmp,
            ):
                current_threshold = (
                    instruction.threshold_raw
                )

                continue

            if isinstance(
                instruction,
                CoreEmit,
            ):
                if current_threshold is None:
                    break

                emissions.append(
                    (
                        current_threshold,
                        instruction.channel_out,
                    )
                )

        if current_threshold is None:
            index = end
            continue

        final_threshold = (
            current_threshold
        )

        #
        # No emitted event means the whole run is equivalent to its
        # final CMP.  Structural normalization usually catches this,
        # but keeping the rule here makes the trace semantics explicit.
        #
        if not emissions:
            normalized = [
                CoreCmp(
                    threshold_raw=(
                        final_threshold
                    )
                )
            ]

        else:
            normalized = []

            grouped = {}

            for threshold, channel in emissions:
                grouped.setdefault(
                    threshold,
                    [],
                ).append(
                    channel
                )

            for threshold in sorted(
                grouped
            ):
                normalized.append(
                    CoreCmp(
                        threshold_raw=threshold
                    )
                )

                for channel in sorted(
                    grouped[
                        threshold
                    ]
                ):
                    normalized.append(
                        CoreEmit(
                            channel_out=channel
                        )
                    )

            #
            # The last emission group may leave a different guard from
            # the original run. Restore the original final guard.
            #
            last_emission_threshold = max(
                grouped
            )

            if (
                last_emission_threshold
                != final_threshold
            ):
                normalized.append(
                    CoreCmp(
                        threshold_raw=(
                            final_threshold
                        )
                    )
                )

        if normalized != segment:
            instructions[
                start:end
            ] = normalized

            return CoreProgram(
                tuple(instructions)
            )

        index = end

    return program


@domain_program_rule
def _remove_dead_state_before_zero_barrier(
    program: CoreProgram,
) -> CoreProgram:
    """
    Exact unsigned-Core law.

    A sequence

        CMP(1); RESET(0)

    maps every incoming raw state to zero.

    Its resulting guard may still depend on the incoming state, so
    preceding state transformations may be removed only when that
    guard is dead: there must be a later CMP before any EMIT or RESET
    can observe/use it.

    Under that condition, immediately preceding ACC/SHIFT operations
    feed only a state value that is annihilated by the zero barrier.
    """

    instructions = list(
        program.instructions
    )

    for cmp_index in range(
        len(instructions) - 1
    ):
        compare = instructions[
            cmp_index
        ]

        reset = instructions[
            cmp_index + 1
        ]

        if not (
            isinstance(
                compare,
                CoreCmp,
            )
            and compare.threshold_raw == 1
            and isinstance(
                reset,
                CoreReset,
            )
            and reset.value_raw == 0
        ):
            continue

        #
        # The guard created by CMP(1) must become dead before any
        # guarded action can consume it.
        #
        cursor = (
            cmp_index + 2
        )

        overwritten = False

        while cursor < len(
            instructions
        ):
            current = instructions[
                cursor
            ]

            if isinstance(
                current,
                CoreCmp,
            ):
                overwritten = True
                break

            if isinstance(
                current,
                (
                    CoreEmit,
                    CoreReset,
                ),
            ):
                break

            cursor += 1

        if not overwritten:
            continue

        #
        # Remove the maximal contiguous state-only prefix immediately
        # before the zero barrier.
        #
        start = cmp_index

        while (
            start > 0
            and isinstance(
                instructions[
                    start - 1
                ],
                (
                    CoreAcc,
                    ShiftDecay,
                ),
            )
        ):
            start -= 1

        if start == cmp_index:
            continue

        del instructions[
            start:cmp_index
        ]

        return CoreProgram(
            tuple(instructions)
        )

    return program


def abstract_normalize_once(
    config: CoreConfig,
    program: CoreProgram,
) -> CoreProgram:
    """
    Apply at most one rewrite justified by abstract interpretation.

    Recomputing analysis after every rewrite avoids using stale facts.
    """

    shared_count_commute = (
        _normalize_shared_count_cmp1_acc_commute(
            program
        )
    )

    if shared_count_commute != program:
        return shared_count_commute

    shared_count_shift = (
        _normalize_shared_count_pre_shift_acc(
            program
        )
    )

    if shared_count_shift != program:
        return shared_count_shift

    temporal_barrier = (
        _normalize_temporal_cmp2_barrier(
            program
        )
    )

    if temporal_barrier != program:
        return temporal_barrier

    temporal_commute = (
        _normalize_temporal_guarded_reset_commute(
            program
        )
    )

    if temporal_commute != program:
        return temporal_commute

    temporal_width = (
        _normalize_temporal_shift_width(
            config,
            program,
        )
    )

    if temporal_width != program:
        return temporal_width

    acc_normalized = (
        _normalize_positive_acc_before_cmp1_zero_reset(
            program
        )
    )

    if acc_normalized != program:
        return acc_normalized

    partition_normalized = (
        _normalize_emit_reset_partition(
            program
        )
    )

    if partition_normalized != program:
        return partition_normalized

    control_normalized = (
        _normalize_cmp_emit_runs(
            program
        )
    )

    if control_normalized != program:
        return control_normalized

    barrier_normalized = (
        _remove_dead_state_before_zero_barrier(
            program
        )
    )

    if barrier_normalized != program:
        return barrier_normalized

    instructions = list(
        program.instructions
    )

    steps = analyze_program(
        config,
        program,
    )

    for step in steps:
        index = step.index
        instruction = step.instruction
        before = step.before

        #
        # A guard known FALSE makes guarded actions inert.
        #
        if (
            before.guard_status == "FALSE"
            and isinstance(
                instruction,
                (
                    CoreEmit,
                    CoreReset,
                ),
            )
        ):
            del instructions[
                index
            ]

            return CoreProgram(
                tuple(instructions)
            )

        #
        # Shifting exact zero cannot change state.
        #
        if isinstance(
            instruction,
            ShiftDecay,
        ):
            raw = before.merged

            if (
                raw is not None
                and raw.is_exact
                and raw.exact_value == 0
            ):
                del instructions[
                    index
                ]

                return CoreProgram(
                    tuple(instructions)
                )

        #
        # Canonicalize CMP to the lowest threshold that induces
        # exactly the same partition over the abstract reachable set.
        #
        if isinstance(
            instruction,
            CoreCmp,
        ):
            raw = before.merged

            if raw is None:
                continue

            low, high = (
                equivalent_threshold_interval(
                    raw,
                    instruction.threshold_raw,
                )
            )

            if (
                low <= instruction.threshold_raw <= high
                and low != instruction.threshold_raw
            ):
                instructions[
                    index
                ] = CoreCmp(
                    threshold_raw=low
                )

                return CoreProgram(
                    tuple(instructions)
                )

    return program


def abstract_normalize_program(
    config: CoreConfig,
    program: CoreProgram,
) -> CoreProgram:
    """
    Semantic normalization to fixed point.

    Only one rewrite is performed before analysis is recomputed.
    """

    current = program

    while True:
        updated = (
            abstract_normalize_once(
                config,
                current,
            )
        )

        if updated == current:
            return current

        current = updated


def canonicalize_core_program_semantic(
    program: CoreProgram,
    *,
    config: CoreConfig,
) -> CoreProgram:
    """
    Experimental composition:

        structural canonicalization
        -> abstract normalization
        -> structural canonicalization
        -> ...

    Kept separate from canonicalize_core_program until preservation
    has been demonstrated over the complete finite domain.
    """

    current = (
        canonicalize_core_program(
            program,
            config=config,
        )
    )

    while True:
        semantic = (
            abstract_normalize_program(
                config,
                current,
            )
        )

        updated = (
            canonicalize_core_program(
                semantic,
                config=config,
            )
        )

        if updated == current:
            return current

        current = updated


def canonicalize_core_program_semantic_runtime(
    program: CoreProgram,
    *,
    config: CoreConfig,
) -> CoreProgram:
    """
    Canonicalize using only rules classified RUNTIME across
    both the Core and semantic normalization layers.

    The shared canonicalization profile also disables Core
    DOMAIN rules reached through canonicalize_core_program.
    """

    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return canonicalize_core_program_semantic(
            program,
            config=config,
        )
