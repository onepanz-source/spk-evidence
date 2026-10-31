from __future__ import annotations

from .rules import (
    CanonicalizationProfile,
    canonicalization_profile,
    domain_rule,
)

from collections import defaultdict

from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


def _acc_channel_key(
    channel: int | None,
):
    if channel is None:
        return (
            -1,
        )

    return (
        channel,
    )


def _remove_zero_acc(
    instructions,
):
    return [
        instruction
        for instruction in instructions
        if not (
            isinstance(
                instruction,
                CoreAcc,
            )
            and instruction.weight == 0
        )
    ]


def _remove_false_guard_prefix(
    instructions,
):
    """
    At the beginning of every batch the guard is False.

    Therefore EMIT and RESET occurring before the first CMP can never
    have an effect.
    """

    output = []

    guard_defined = False

    for instruction in instructions:
        if isinstance(
            instruction,
            CoreCmp,
        ):
            guard_defined = True
            output.append(
                instruction
            )

            continue

        if (
            not guard_defined
            and isinstance(
                instruction,
                (
                    CoreEmit,
                    CoreReset,
                ),
            )
        ):
            continue

        output.append(
            instruction
        )

    return output


def _remove_dead_compares(
    instructions,
):
    """
    A CMP is dead if its guard is overwritten by a later CMP before
    anything observes it.

    final_guard is part of CoreResult, so the guard is considered live
    at program exit.
    """

    reversed_output = []

    guard_needed = True

    for instruction in reversed(
        instructions
    ):
        if isinstance(
            instruction,
            (
                CoreEmit,
                CoreReset,
            ),
        ):
            guard_needed = True

            reversed_output.append(
                instruction
            )

            continue

        if isinstance(
            instruction,
            CoreCmp,
        ):
            if guard_needed:
                reversed_output.append(
                    instruction
                )

            guard_needed = False

            continue

        reversed_output.append(
            instruction
        )

    reversed_output.reverse()

    return reversed_output


def _move_emit_left(
    instructions,
):
    """
    EMIT reads guard and does not inspect or modify state.

    ACC, RESET and SHIFT_DECAY do not modify guard.

    Therefore EMIT commutes left across those instructions, but never
    across CMP.

    Canonical orientation places EMIT as close as possible to the CMP
    that produced its guard.
    """

    result = list(
        instructions
    )

    changed = True

    while changed:
        changed = False

        for index in range(
            1,
            len(result),
        ):
            current = result[
                index
            ]

            previous = result[
                index - 1
            ]

            if (
                isinstance(
                    current,
                    CoreEmit,
                )
                and isinstance(
                    previous,
                    (
                        CoreAcc,
                        CoreReset,
                        ShiftDecay,
                    ),
                )
            ):
                result[
                    index - 1
                ], result[
                    index
                ] = (
                    current,
                    previous,
                )

                changed = True

    return result


def _collapse_adjacent_resets(
    instructions,
):
    """
    RESET(a); RESET(b) -> RESET(b)

    RESET does not alter guard, so when guard is true the second reset
    overwrites the first; when false neither executes.
    """

    result = []

    for instruction in instructions:
        if (
            isinstance(
                instruction,
                CoreReset,
            )
            and result
            and isinstance(
                result[-1],
                CoreReset,
            )
        ):
            result[-1] = (
                instruction
            )

            continue

        result.append(
            instruction
        )

    return result




def _commute_zero_reset_across_shift(
    instructions,
):
    """
    Exact Core law:

        RESET(0); SHIFT(k)
            ->
        SHIFT(k); RESET(0)

    RESET and SHIFT observe the same guard.

    guard=True:
        reset->shift = 0
        shift->reset = 0

    guard=False:
        RESET is inactive and both forms execute the same SHIFT.

    Canonical orientation places SHIFT before RESET.
    """

    result = list(
        instructions
    )

    for index in range(
        len(result) - 1
    ):
        left = result[
            index
        ]

        right = result[
            index + 1
        ]

        if (
            isinstance(
                left,
                CoreReset,
            )
            and left.value_raw == 0
            and isinstance(
                right,
                ShiftDecay,
            )
        ):
            result[
                index
            ], result[
                index + 1
            ] = (
                right,
                left,
            )

            return result

    return result


def _remove_shift_between_cmp1_and_reset0(
    instructions,
):
    """
    Unsigned Core law:

        CMP(1); [EMIT|SHIFT]*; RESET(0)

    permits removal of every SHIFT between CMP and RESET.

    CMP false:
        unsigned raw < 1 => raw == 0
        therefore SHIFT preserves zero.

    CMP true:
        RESET(0) eventually overwrites the shifted state.

    EMIT is allowed because it observes guard only.
    """

    result = list(
        instructions
    )

    for index, instruction in enumerate(
        result
    ):
        if not (
            isinstance(
                instruction,
                CoreCmp,
            )
            and instruction.threshold_raw == 1
        ):
            continue

        cursor = index + 1

        while cursor < len(
            result
        ):
            current = result[
                cursor
            ]

            if isinstance(
                current,
                CoreReset,
            ):
                if (
                    current.value_raw
                    == 0
                ):
                    #
                    # Remove all SHIFTs in the window.
                    #
                    result = (
                        result[:index + 1]
                        + [
                            item
                            for item
                            in result[
                                index + 1:
                                cursor
                            ]
                            if not isinstance(
                                item,
                                ShiftDecay,
                            )
                        ]
                        + result[
                            cursor:
                        ]
                    )

                    return result

                break

            if not isinstance(
                current,
                (
                    CoreEmit,
                    ShiftDecay,
                ),
            ):
                break

            cursor += 1

    return result


def _remove_shift_when_state_known_zero(
    instructions,
):
    """
    Abstract interpretation for the exact fact:

        raw == 0

    The key establishing pattern is:

        CMP(1); [EMIT|SHIFT]*; RESET(0)

    After that RESET the unsigned state is zero on both branches.

    While state remains known zero:
      * SHIFT is identity and is removed
      * CMP and EMIT preserve zero
      * RESET(0) preserves zero
      * ACC destroys the fact

    A different RESET value is handled conservatively.
    """

    result = []

    known_zero = False

    cmp1_candidate = False

    for instruction in instructions:
        if isinstance(
            instruction,
            CoreCmp,
        ):
            result.append(
                instruction
            )

            if known_zero:
                #
                # CMP does not change state.
                #
                cmp1_candidate = False
                continue

            cmp1_candidate = (
                instruction.threshold_raw
                == 1
            )

            continue

        if isinstance(
            instruction,
            CoreEmit,
        ):
            result.append(
                instruction
            )

            #
            # EMIT changes neither state nor guard.
            #
            continue

        if isinstance(
            instruction,
            ShiftDecay,
        ):
            if known_zero:
                #
                # 0 >> n == 0.
                #
                continue

            result.append(
                instruction
            )

            #
            # A SHIFT after CMP(1) preserves the fact needed to prove
            # zero once RESET(0) is reached.
            #
            continue

        if isinstance(
            instruction,
            CoreReset,
        ):
            result.append(
                instruction
            )

            if (
                instruction.value_raw
                == 0
                and (
                    known_zero
                    or cmp1_candidate
                )
            ):
                known_zero = True
            else:
                known_zero = False

            cmp1_candidate = False

            continue

        if isinstance(
            instruction,
            CoreAcc,
        ):
            result.append(
                instruction
            )

            known_zero = False
            cmp1_candidate = False

            continue

        result.append(
            instruction
        )

        known_zero = False
        cmp1_candidate = False

    return result



@domain_rule
def _remove_pre_acc_shift_under_cmp1_reset0(
    instructions,
):
    """
    Exact unsigned-Core law.

        CMP(1); SHIFT*; ... ACC ...; RESET(0)
            ->
        CMP(1);        ... ACC ...; RESET(0)

    for SHIFTs occurring before the first ACC, provided no intervening
    CMP changes guard before RESET(0).

    Proof:

      CMP false:
          unsigned raw < 1 => raw == 0.
          Any leading SHIFT therefore acts on zero.

      CMP true:
          the eventual RESET(0), controlled by the unchanged guard,
          destroys every state change before it.

    EMIT is harmless because it observes guard only.
    """

    result = list(instructions)

    for cmp_index, instruction in enumerate(result):
        if not (
            isinstance(instruction, CoreCmp)
            and instruction.threshold_raw == 1
        ):
            continue

        cursor = cmp_index + 1
        removable = []
        seen_acc = False

        while cursor < len(result):
            current = result[cursor]

            if isinstance(current, CoreCmp):
                break

            if isinstance(current, CoreReset):
                if (
                    current.value_raw == 0
                    and removable
                ):
                    for index in reversed(removable):
                        del result[index]

                    return result

                break

            if isinstance(current, CoreAcc):
                seen_acc = True

            elif isinstance(current, ShiftDecay):
                if not seen_acc:
                    removable.append(cursor)

            elif not isinstance(current, CoreEmit):
                break

            cursor += 1

    return result


def _sink_known_false_compare_across_shift(
    instructions,
):
    """
    Exact law:

        CMP(t); RESET(0); CMP(t); SHIFT(k)
            ->
        CMP(t); SHIFT(k); RESET(0); CMP(t)

    After CMP(t); RESET(0), the state is always < t:

      first CMP true  -> state becomes 0
      first CMP false -> state was already < t

    Therefore the second CMP(t) is certainly False.

    SHIFT preserves the relation state < t because it can only decrease
    an unsigned integer state.  Moving it before RESET therefore
    preserves both final state and final guard.
    """

    result = list(instructions)

    for index in range(len(result) - 3):
        first = result[index]
        reset = result[index + 1]
        second = result[index + 2]
        shift = result[index + 3]

        if not (
            isinstance(first, CoreCmp)
            and isinstance(reset, CoreReset)
            and reset.value_raw == 0
            and isinstance(second, CoreCmp)
            and second.threshold_raw == first.threshold_raw
            and isinstance(shift, ShiftDecay)
        ):
            continue

        result[index:index + 4] = (
            first,
            shift,
            reset,
            second,
        )

        return result

    return result


def _cap_shift_before_zero_reset_from_compare_bound(
    instructions,
):
    """
    Ordered temporal law.

        CMP(t); SHIFT(k); RESET(0)

    establishes on the false branch:

        0 <= raw < t

    Let:

        m = bit_length(t - 1)

    Every SHIFT(k) with k >= m maps the complete false-branch state
    interval to zero whenever delta > 0.  For delta == 0 all shifts are
    identity.  On the true branch RESET(0) destroys the shifted value.

    Therefore all k >= m are equivalent and canonicalize to m.

    CMP(1) gives m=0 and is handled by the stronger zero-state rules.
    """

    result = list(instructions)

    for cmp_index, instruction in enumerate(result):
        if not isinstance(instruction, CoreCmp):
            continue

        threshold = instruction.threshold_raw

        if threshold <= 1:
            continue

        minimum_bits = (
            threshold - 1
        ).bit_length()

        cursor = cmp_index + 1

        while (
            cursor < len(result)
            and isinstance(
                result[cursor],
                CoreEmit,
            )
        ):
            cursor += 1

        if (
            cursor >= len(result)
            or not isinstance(
                result[cursor],
                ShiftDecay,
            )
        ):
            continue

        shift_index = cursor
        shift = result[shift_index]

        cursor += 1

        while (
            cursor < len(result)
            and isinstance(
                result[cursor],
                CoreEmit,
            )
        ):
            cursor += 1

        if (
            cursor >= len(result)
            or not isinstance(
                result[cursor],
                CoreReset,
            )
            or result[cursor].value_raw != 0
        ):
            continue

        if shift.bits_per_tick > minimum_bits:
            result[shift_index] = ShiftDecay(
                bits_per_tick=minimum_bits
            )

            return result

    return result


def _normalize_shift_decay_runs(
    instructions,
):
    """
    Exact integer Core law:

        SHIFT_DECAY(a); SHIFT_DECAY(b)
            ->
        SHIFT_DECAY(a+b)

    because for nonnegative integers:

        (x >> (a*dt)) >> (b*dt)
            ==
        x >> ((a+b)*dt)

    SHIFT_DECAY(0) is identity.
    """

    result = []

    index = 0

    while index < len(
        instructions
    ):
        instruction = instructions[
            index
        ]

        if not isinstance(
            instruction,
            ShiftDecay,
        ):
            result.append(
                instruction
            )

            index += 1
            continue

        total = 0

        while (
            index < len(instructions)
            and isinstance(
                instructions[index],
                ShiftDecay,
            )
        ):
            total += (
                instructions[
                    index
                ].bits_per_tick
            )

            index += 1

        if total != 0:
            result.append(
                ShiftDecay(
                    bits_per_tick=total
                )
            )

    return result


def _normalize_acc_runs(
    instructions,
):
    """
    Consecutive ACC instructions are pure additive updates.

    They commute and same-channel weights can be fused:

        ACC(a,c); ACC(b,c)
          ->
        ACC(a+b,c)

    Canonical runs are ordered by channel.
    """

    result = []

    index = 0

    while index < len(
        instructions
    ):
        instruction = instructions[
            index
        ]

        if not isinstance(
            instruction,
            CoreAcc,
        ):
            result.append(
                instruction
            )

            index += 1
            continue

        totals = defaultdict(
            int
        )

        while (
            index
            < len(instructions)
            and isinstance(
                instructions[index],
                CoreAcc,
            )
        ):
            current = instructions[
                index
            ]

            totals[
                current.channel
            ] += current.weight

            index += 1

        for channel in sorted(
            totals,
            key=_acc_channel_key,
        ):
            weight = totals[
                channel
            ]

            if weight == 0:
                continue

            result.append(
                CoreAcc(
                    weight=weight,
                    channel=channel,
                )
            )

    return result


def _sort_emit_runs(
    instructions,
):
    """
    Coincident EMIT outputs form a SpikeTrain multiset, therefore the
    order of adjacent EMIT instructions has no semantic meaning.
    """

    result = []

    index = 0

    while index < len(
        instructions
    ):
        instruction = instructions[
            index
        ]

        if not isinstance(
            instruction,
            CoreEmit,
        ):
            result.append(
                instruction
            )

            index += 1
            continue

        emits = []

        while (
            index
            < len(instructions)
            and isinstance(
                instructions[index],
                CoreEmit,
            )
        ):
            emits.append(
                instructions[index]
            )

            index += 1

        emits.sort(
            key=lambda emit: (
                emit.channel_out
            )
        )

        result.extend(
            emits
        )

    return result



def _remove_redundant_repeated_compares(
    instructions,
):
    """
    If state has not changed since the last CMP, repeating the same
    comparison cannot change guard.

        CMP(t); ...guard-neutral...; CMP(t)
            ->
        CMP(t); ...guard-neutral...

    EMIT is guard-neutral and state-neutral.

    ACC, RESET and SHIFT_DECAY may change state, therefore they break
    the proof context.
    """

    result = []

    last_compare = None

    for instruction in instructions:
        if isinstance(
            instruction,
            CoreCmp,
        ):
            if (
                last_compare
                == instruction.threshold_raw
            ):
                continue

            result.append(
                instruction
            )

            last_compare = (
                instruction.threshold_raw
            )

            continue

        result.append(
            instruction
        )

        if isinstance(
            instruction,
            (
                CoreAcc,
                CoreReset,
                ShiftDecay,
            ),
        ):
            last_compare = None

    return result


def _normalize_false_compare_after_reset(
    instructions,
):
    """
    Proven law:

        CMP(a); EMIT*; RESET(r); CMP(b)

    with:

        r < a
        b >= a

    establishes that the second comparison is always False.

    Proof:

      first CMP true:
          RESET executes and state becomes r < a

      first CMP false:
          state < a

    Therefore CMP(a) is false on both paths, and every CMP(b) with
    b >= a is false as well.

    Canonical form uses CMP(a).

    Since that final guard is provably False, immediately following
    EMIT/RESET instructions are dead and may be removed.

    The final CMP itself must remain because final_guard is observable.
    """

    result = list(
        instructions
    )

    index = 0

    while index < len(
        result
    ):
        first = result[
            index
        ]

        if not isinstance(
            first,
            CoreCmp,
        ):
            index += 1
            continue

        cursor = (
            index + 1
        )

        #
        # EMIT does not alter state or guard.
        #
        while (
            cursor
            < len(result)
            and isinstance(
                result[cursor],
                CoreEmit,
            )
        ):
            cursor += 1

        if (
            cursor >= len(result)
            or not isinstance(
                result[cursor],
                CoreReset,
            )
        ):
            index += 1
            continue

        reset = result[
            cursor
        ]

        compare_index = (
            cursor + 1
        )

        if (
            compare_index
            >= len(result)
            or not isinstance(
                result[
                    compare_index
                ],
                CoreCmp,
            )
        ):
            index += 1
            continue

        second = result[
            compare_index
        ]

        a = first.threshold_raw
        r = reset.value_raw
        b = second.threshold_raw

        if (
            r < a
            and b >= a
        ):
            #
            # Normalize all provably-false thresholds to a.
            #
            result[
                compare_index
            ] = CoreCmp(
                threshold_raw=a
            )

            #
            # Guard is now known False. Consecutive conditional
            # effects are dead.
            #
            tail = (
                compare_index + 1
            )

            while (
                tail
                < len(result)
                and isinstance(
                    result[tail],
                    (
                        CoreEmit,
                        CoreReset,
                    ),
                )
            ):
                del result[
                    tail
                ]

        index += 1

    return result



@domain_rule
def _remove_shadowed_resets(
    instructions,
):
    """
    Proven law:

        RESET(a); X; RESET(b)
            ->
        X; RESET(b)

    if X contains no CMP.

    ACC and SHIFT_DECAY may change state, but their result is
    overwritten by the later RESET when guard=True.

    EMIT observes guard only.

    When guard=False neither RESET executes.
    """

    result = list(
        instructions
    )

    changed = True

    while changed:
        changed = False

        for index, instruction in enumerate(
            result
        ):
            if not isinstance(
                instruction,
                CoreReset,
            ):
                continue

            cursor = index + 1

            while cursor < len(
                result
            ):
                current = result[
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
                    del result[
                        index
                    ]

                    changed = True
                    break

                cursor += 1

            if changed:
                break

    return result


def _pull_saturated_acc_across_compare(
    instructions,
    config: CoreConfig,
):
    """
    Ordered unsigned-state law.

    Suppose the ACC run immediately before CMP(theta) contains:

        ACC(a, c)

    with:

        a * scale >= theta > 0.

    Then any ACC(b, c) in the contiguous ACC run following the CMP
    may be pulled before the comparison and fused with ACC(a,c).

    EMIT instructions are also allowed immediately after CMP and before
    that post-CMP ACC run.

    Proof:

      count(c) == 0:
          both moved contributions are zero.

      count(c) > 0:
          ACC(a,c) alone already guarantees CMP=True because state is
          unsigned and a*scale >= theta.

    Therefore moving ACC(b,c) cannot change the guard or any EMIT
    output. ACC updates are additive, so final state is unchanged.

    Canonical orientation moves the same-channel contribution left and
    fuses it into the saturating witness.
    """

    result = list(
        instructions
    )

    for compare_index, instruction in enumerate(
        result
    ):
        if not isinstance(
            instruction,
            CoreCmp,
        ):
            continue

        theta = (
            instruction.threshold_raw
        )

        if theta <= 0:
            continue

        #
        # Find the complete ACC run immediately before CMP.
        #
        run_start = compare_index

        while (
            run_start > 0
            and isinstance(
                result[
                    run_start - 1
                ],
                CoreAcc,
            )
        ):
            run_start -= 1

        witnesses = {}

        for index in range(
            run_start,
            compare_index,
        ):
            acc = result[
                index
            ]

            if (
                acc.weight
                * config.scale
                >= theta
            ):
                witnesses[
                    acc.channel
                ] = index

        if not witnesses:
            continue

        #
        # EMITs may occur after CMP. They observe only guard, whose
        # value is preserved by this rewrite.
        #
        post_start = (
            compare_index + 1
        )

        while (
            post_start
            < len(result)
            and isinstance(
                result[
                    post_start
                ],
                CoreEmit,
            )
        ):
            post_start += 1

        #
        # Search the ENTIRE following ACC run, not just its first
        # instruction.
        #
        post_end = post_start

        while (
            post_end
            < len(result)
            and isinstance(
                result[
                    post_end
                ],
                CoreAcc,
            )
        ):
            post_end += 1

        for trailing_index in range(
            post_start,
            post_end,
        ):
            trailing = result[
                trailing_index
            ]

            witness_index = (
                witnesses.get(
                    trailing.channel
                )
            )

            if witness_index is None:
                continue

            witness = result[
                witness_index
            ]

            result[
                witness_index
            ] = CoreAcc(
                weight=(
                    witness.weight
                    + trailing.weight
                ),
                channel=(
                    witness.channel
                ),
            )

            del result[
                trailing_index
            ]

            #
            # One rewrite per pass. The outer fixed-point loop will
            # continue until no further saturated ACC can move.
            #
            return result

    return result


@domain_rule
def _cap_saturated_acc_before_guarded_reset(
    instructions,
    config: CoreConfig,
):
    """
    If ACC(a,c) immediately belongs to the ACC run before CMP(theta),
    a single event on c already guarantees the comparison, and the
    comparison is followed only by EMITs and then RESET, weight above
    the minimum saturating value is unobservable.

    True branch:
        RESET overwrites accumulated state.

    False branch:
        count(c) must be zero for every individually saturating ACC.
    """

    result = list(
        instructions
    )

    for compare_index, instruction in enumerate(
        result
    ):
        if not isinstance(
            instruction,
            CoreCmp,
        ):
            continue

        theta = (
            instruction.threshold_raw
        )

        if theta <= 0:
            continue

        cursor = (
            compare_index + 1
        )

        while (
            cursor < len(result)
            and isinstance(
                result[cursor],
                CoreEmit,
            )
        ):
            cursor += 1

        if (
            cursor >= len(result)
            or not isinstance(
                result[cursor],
                CoreReset,
            )
        ):
            continue

        minimum_weight = (
            theta
            + config.scale
            - 1
        ) // config.scale

        run_start = compare_index

        while (
            run_start > 0
            and isinstance(
                result[
                    run_start - 1
                ],
                CoreAcc,
            )
        ):
            run_start -= 1

        for index in range(
            run_start,
            compare_index,
        ):
            acc = result[
                index
            ]

            if (
                acc.weight
                * config.scale
                >= theta
                and acc.weight
                > minimum_weight
            ):
                result[
                    index
                ] = CoreAcc(
                    weight=minimum_weight,
                    channel=acc.channel,
                )

                return result

    return result


@domain_rule
def _strip_state_before_lsb_annihilator(
    instructions,
):
    """
    Core raw state is an unsigned integer.

        CMP(1); RESET(0); CMP(1)

    therefore always terminates with:

        raw   = 0
        guard = False

    because:
      raw >= 1  -> RESET(0) -> CMP(1)=False
      raw <  1  -> raw==0   -> CMP(1)=False

    Consequently an immediately preceding state-only update is dead.
    """

    result = list(
        instructions
    )

    for index in range(
        len(result) - 2
    ):
        first = result[
            index
        ]

        second = result[
            index + 1
        ]

        third = result[
            index + 2
        ]

        if not (
            isinstance(
                first,
                CoreCmp,
            )
            and first.threshold_raw == 1
            and isinstance(
                second,
                CoreReset,
            )
            and second.value_raw == 0
            and isinstance(
                third,
                CoreCmp,
            )
            and third.threshold_raw == 1
        ):
            continue

        if (
            index > 0
            and isinstance(
                result[
                    index - 1
                ],
                (
                    CoreAcc,
                    ShiftDecay,
                    CoreReset,
                ),
            )
        ):
            del result[
                index - 1
            ]

            return result

    return result


def canonicalize_core_program(
    program: CoreProgram,
    config: CoreConfig | None = None,
) -> CoreProgram:
    """
    Core v0 structural canonicalizer.

    The rules preserve successful Core executions. Overflow timing is
    not treated as an observable semantic value.

    The fixed-point loop is deliberate: one rewrite can expose another.
    """

    instructions = list(
        program.instructions
    )

    while True:
        before = tuple(
            instructions
        )

        instructions = (
            _remove_zero_acc(
                instructions
            )
        )

        instructions = (
            _remove_false_guard_prefix(
                instructions
            )
        )

        instructions = (
            _remove_dead_compares(
                instructions
            )
        )

        instructions = (
            _move_emit_left(
                instructions
            )
        )

        instructions = (
            _collapse_adjacent_resets(
                instructions
            )
        )

        instructions = (
            _remove_redundant_repeated_compares(
                instructions
            )
        )

        instructions = (
            _normalize_false_compare_after_reset(
                instructions
            )
        )

        instructions = (
            _commute_zero_reset_across_shift(
                instructions
            )
        )

        instructions = (
            _remove_shift_between_cmp1_and_reset0(
                instructions
            )
        )

        instructions = (
            _remove_shift_when_state_known_zero(
                instructions
            )
        )

        instructions = (
            _remove_pre_acc_shift_under_cmp1_reset0(
                instructions
            )
        )

        instructions = (
            _sink_known_false_compare_across_shift(
                instructions
            )
        )

        instructions = (
            _cap_shift_before_zero_reset_from_compare_bound(
                instructions
            )
        )

        instructions = (
            _normalize_shift_decay_runs(
                instructions
            )
        )

        instructions = (
            _normalize_acc_runs(
                instructions
            )
        )

        instructions = (
            _remove_shadowed_resets(
                instructions
            )
        )

        instructions = (
            _strip_state_before_lsb_annihilator(
                instructions
            )
        )

        if config is not None:
            instructions = (
                _pull_saturated_acc_across_compare(
                    instructions,
                    config,
                )
            )

            instructions = (
                _cap_saturated_acc_before_guarded_reset(
                    instructions,
                    config,
                )
            )

        instructions = (
            _sort_emit_runs(
                instructions
            )
        )

        after = tuple(
            instructions
        )

        if after == before:
            return CoreProgram(
                after
            )


def canonicalize_core_program_runtime(
    program: CoreProgram,
    config: CoreConfig | None = None,
) -> CoreProgram:
    """
    Canonicalize using only rules classified RUNTIME.

    DOMAIN rules remain present in the normal orchestrator but are
    identity transformations while this profile is active. This
    deliberately preserves the existing rewrite order and fixed-point
    structure.
    """

    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return canonicalize_core_program(
            program,
            config,
        )
