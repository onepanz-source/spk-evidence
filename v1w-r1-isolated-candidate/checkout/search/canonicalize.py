from __future__ import annotations

from fractions import Fraction
from search.decay_algebra import tau_to_rate
from search.temporal_bounds import positive_tick_decay_bound_below

import math
from search.decay_algebra import combine_decay_taus
from enum import Enum, auto

from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)
from spk.program import Program


class GuardKnowledge(Enum):
    FALSE = auto()
    UNKNOWN = auto()


def _rewrite_local(
    operators: tuple,
) -> tuple:
    """
    Exact local rewrite rules.
    """

    result = []
    index = 0

    while index < len(operators):
        current = operators[index]

        #
        # ACC(0) -> identity
        #
        if (
            isinstance(current, Acc)
            and current.weight == 0.0
        ):
            index += 1
            continue

        #
        # ACC(a,c) ACC(b,c)
        # ->
        # ACC(a+b,c)
        #
        if (
            isinstance(current, Acc)
            and index + 1 < len(operators)
            and isinstance(
                operators[index + 1],
                Acc,
            )
            and current.channel
            == operators[index + 1].channel
        ):
            following = operators[index + 1]

            weight = (
                current.weight
                + following.weight
            )

            if weight != 0.0:
                result.append(
                    Acc(
                        weight=weight,
                        channel=current.channel,
                    )
                )

            index += 2
            continue

        #
        # CMP(a) CMP(b)
        # ->
        # CMP(b)
        #
        if (
            isinstance(current, Compare)
            and index + 1 < len(operators)
            and isinstance(
                operators[index + 1],
                Compare,
            )
        ):
            result.append(
                operators[index + 1]
            )

            index += 2
            continue

        #
        # RESET(a) RESET(b)
        # ->
        # RESET(b)
        #
        if (
            isinstance(current, Reset)
            and index + 1 < len(operators)
            and isinstance(
                operators[index + 1],
                Reset,
            )
        ):
            result.append(
                operators[index + 1]
            )

            index += 2
            continue

        result.append(current)
        index += 1

    return tuple(result)


def _remove_guard_dead_operations(
    operators: tuple,
) -> tuple:
    """
    Remove EMIT/RESET operations that are provably inert because
    the guard is definitely false.

    At batch entry:

        guard = false

    ACC and DECAY preserve guard.

    CMP makes the guard data-dependent.
    """

    knowledge = GuardKnowledge.FALSE
    result = []

    for operator in operators:
        if isinstance(operator, Compare):
            result.append(operator)
            knowledge = GuardKnowledge.UNKNOWN
            continue

        if isinstance(operator, (Acc, Decay)):
            result.append(operator)
            continue

        if isinstance(operator, (Emit, Reset)):
            if knowledge is GuardKnowledge.FALSE:
                continue

            result.append(operator)
            continue

        result.append(operator)
        knowledge = GuardKnowledge.UNKNOWN

    return tuple(result)


def _eliminate_dead_compares(
    operators: tuple,
) -> tuple:
    """
    Backward guard-liveness analysis.

    A CMP writes the transient guard.

    If that value is overwritten by another CMP before:
        - EMIT reads it,
        - RESET reads it,
        - or program termination observes it,

    then the earlier CMP is dead.

    Final guard state is observable, therefore the guard is live
    at program exit.
    """

    guard_live = True
    reversed_result = []

    for operator in reversed(operators):

        if isinstance(operator, Compare):
            if guard_live:
                reversed_result.append(operator)

            #
            # CMP overwrites the previous guard value.
            #
            guard_live = False
            continue

        if isinstance(operator, (Emit, Reset)):
            #
            # Both operators read guard.
            #
            reversed_result.append(operator)
            guard_live = True
            continue

        if isinstance(operator, (Acc, Decay)):
            #
            # These neither read nor write guard.
            #
            reversed_result.append(operator)
            continue

        #
        # Unknown future operator:
        # preserve conservatively and assume it may read guard.
        #
        reversed_result.append(operator)
        guard_live = True

    return tuple(
        reversed(reversed_result)
    )

def _eliminate_redundant_recompares(
    operators: tuple,
) -> tuple:
    """
    Remove a repeated CMP when the current guard already contains
    exactly the same predicate evaluated on the same persistent
    state.

    Example:

        CMP(1) EMIT CMP(1)
        ->
        CMP(1) EMIT

    EMIT changes neither x nor guard.

    ACC, DECAY and RESET may change x, therefore they invalidate
    the cached comparison result.
    """

    result = []

    current_comparison = None

    for operator in operators:
        if isinstance(operator, Compare):
            comparison = (
                operator.threshold,
            )

            if comparison == current_comparison:
                continue

            result.append(operator)

            current_comparison = comparison
            continue

        if isinstance(operator, Emit):
            #
            # EMIT preserves both x and guard.
            #
            result.append(operator)
            continue

        if isinstance(
            operator,
            (
                Acc,
                Decay,
                Reset,
            ),
        ):
            #
            # Persistent state may change.
            #
            result.append(operator)
            current_comparison = None
            continue

        #
        # Unknown future operator:
        # preserve conservatively and forget cached knowledge.
        #
        result.append(operator)
        current_comparison = None

    return tuple(result)


def _commute_emit_left(
    operators: tuple,
) -> tuple:
    """
    Move EMIT left across operators that commute with it.

    Exact SPK/v0 commutations currently used:

        ACC   EMIT == EMIT ACC
        DECAY EMIT == EMIT DECAY
        RESET EMIT == EMIT RESET

    Rationale:

    EMIT reads guard and appends output.

    ACC/DECAY modify only persistent state and preserve guard.

    RESET reads guard and modifies persistent state.

    None of these transformations changes the value consumed by
    EMIT, and EMIT does not modify persistent state.

    CMP is a barrier because it writes guard.
    """

    result = list(operators)

    changed = True

    while changed:
        changed = False

        for index in range(
            1,
            len(result),
        ):
            current = result[index]
            previous = result[index - 1]

            if (
                isinstance(current, Emit)
                and isinstance(
                    previous,
                    (
                        Acc,
                        Decay,
                        Reset,
                    ),
                )
            ):
                result[index - 1], result[index] = (
                    current,
                    previous,
                )

                changed = True

    return tuple(result)



def _eliminate_shadowed_resets(
    operators: tuple,
) -> tuple:
    """
    Remove RESET operations shadowed by a later RESET while the
    guard cannot change.

    Within a region containing no CMP:

        RESET(a) Q RESET(b)
        ->
        Q RESET(b)

    where Q contains only operators that preserve guard and do not
    branch on persistent state.

    If guard is true, the later RESET erases any state effect that
    depended on the earlier RESET.

    If guard is false, both RESET operations are inert.
    """

    result = list(operators)

    index = 0

    while index < len(result):
        if not isinstance(
            result[index],
            Reset,
        ):
            index += 1
            continue

        later_reset = None
        cursor = index + 1

        while cursor < len(result):
            operator = result[cursor]

            if isinstance(operator, Compare):
                break

            if isinstance(operator, Reset):
                later_reset = cursor

            elif not isinstance(
                operator,
                (
                    Acc,
                    Decay,
                    Emit,
                ),
            ):
                break

            cursor += 1

        if later_reset is not None:
            del result[index]
            continue

        index += 1

    return tuple(result)


def _refine_guard_and_state_facts(
    operators: tuple,
) -> tuple:
    """
    Small forward abstract interpretation for SPK/v0.

    It tracks:

      * whether guard is definitely FALSE;
      * whether guard came from a CMP evaluated on the current state;
      * a strict upper bound x < U obtained from guarded RESET.

    Core deduction:

        CMP(theta)
        RESET(r)

    with:

        r < theta

    implies afterwards:

        x < theta

    Therefore any subsequent:

        CMP(phi)

    with:

        phi >= theta

    is guaranteed FALSE.

    Such equivalent false comparisons are normalized to CMP(theta).
    """

    result = []

    guard_false = True

    guard_threshold = None
    state_matches_guard_source = False

    strict_upper_bound = None

    for operator in operators:

        if isinstance(operator, Compare):
            threshold = operator.threshold

            if (
                strict_upper_bound is not None
                and threshold >= strict_upper_bound
            ):
                #
                # x < strict_upper_bound, therefore this
                # comparison is certainly false.
                #
                operator = Compare(
                    threshold=strict_upper_bound
                )

                guard_false = True

            else:
                guard_false = False

            result.append(operator)

            guard_threshold = operator.threshold
            state_matches_guard_source = True

            continue

        if isinstance(operator, Emit):
            if guard_false:
                continue

            result.append(operator)
            continue

        if isinstance(operator, Reset):
            if guard_false:
                continue

            result.append(operator)

            if (
                state_matches_guard_source
                and guard_threshold is not None
                and operator.value < guard_threshold
            ):
                #
                # true branch:
                #
                #     x := value < threshold
                #
                # false branch:
                #
                #     x < threshold
                #
                # Therefore both branches satisfy:
                #
                #     x < threshold
                #
                strict_upper_bound = guard_threshold

            else:
                strict_upper_bound = None

            state_matches_guard_source = False

            continue

        if isinstance(operator, Decay):
            result.append(operator)

            #
            # DECAY multiplies x by:
            #
            #     exp(-delta/tau)
            #
            # which is in (0, 1].
            #
            # Therefore a strict positive upper bound:
            #
            #     x < U, U > 0
            #
            # remains valid after decay.
            #
            # The exact relation between guard and the current x is
            # nevertheless lost because x itself changed.
            #
            if (
                strict_upper_bound is not None
                and strict_upper_bound <= 0.0
            ):
                strict_upper_bound = None

            state_matches_guard_source = False

            continue

        if isinstance(operator, Acc):
            result.append(operator)

            #
            # ACC may move x across the known bound, depending on
            # event multiplicity and weight.
            #
            strict_upper_bound = None
            state_matches_guard_source = False

            continue

        #
        # Unknown future operator: remain conservative.
        #
        result.append(operator)

        guard_false = False
        guard_threshold = None
        state_matches_guard_source = False
        strict_upper_bound = None

    return tuple(result)



def _commute_zero_reset_left_across_decay(
    operators: tuple,
) -> tuple:
    """
    Canonicalize:

        DECAY(tau) RESET(0)
        ->
        RESET(0) DECAY(tau)

    This is exact while guard is unchanged.

    If guard is false, RESET is inert.

    If guard is true:

        DECAY; RESET(0)

    finishes at zero, while:

        RESET(0); DECAY

    also finishes at zero because exponential decay preserves zero.

    Only RESET(0) is covered. A non-zero reset does not generally
    commute with DECAY.
    """

    result = list(operators)

    changed = True

    while changed:
        changed = False

        for index in range(
            1,
            len(result),
        ):
            current = result[index]
            previous = result[index - 1]

            if (
                isinstance(current, Reset)
                and current.value == 0.0
                and isinstance(
                    previous,
                    Decay,
                )
            ):
                result[index - 1], result[index] = (
                    current,
                    previous,
                )

                changed = True

    return tuple(result)



def _commute_provably_false_compare_right_across_decay(
    operators: tuple,
) -> tuple:
    """
    Canonicalize a comparison known to be FALSE across DECAY:

        CMP(theta); DECAY(tau)
        ->
        DECAY(tau); CMP(theta)

    but only when an already established non-negative strict upper
    bound proves:

        x < U <= theta

    before the CMP.

    Since DECAY multiplies x by alpha in (0, 1]:

        x < U
        and U >= 0

    imply:

        alpha*x < U <= theta

    Therefore the comparison is FALSE on both sides of DECAY.

    This is deliberately NOT a general CMP/DECAY commutation rule.
    """

    result = list(operators)

    strict_upper_bound = None
    guard_threshold = None
    state_matches_guard_source = False

    for index, operator in enumerate(result):

        if isinstance(operator, Compare):
            provably_false = (
                strict_upper_bound is not None
                and strict_upper_bound >= 0.0
                and operator.threshold
                >= strict_upper_bound
            )

            if (
                provably_false
                and index + 1 < len(result)
                and isinstance(
                    result[index + 1],
                    Decay,
                )
            ):
                result[index], result[index + 1] = (
                    result[index + 1],
                    result[index],
                )

                #
                # One rewrite per fixed-point iteration keeps this
                # pass simple and deterministic.
                #
                return tuple(result)

            guard_threshold = operator.threshold
            state_matches_guard_source = True

            continue

        if isinstance(operator, Reset):
            if (
                state_matches_guard_source
                and guard_threshold is not None
                and operator.value
                < guard_threshold
            ):
                strict_upper_bound = (
                    guard_threshold
                )
            else:
                #
                # Conservative fallback.
                #
                strict_upper_bound = None

            state_matches_guard_source = False

            continue

        if isinstance(operator, Decay):
            #
            # A non-negative strict upper bound survives decay.
            #
            if (
                strict_upper_bound is not None
                and strict_upper_bound < 0.0
            ):
                strict_upper_bound = None

            state_matches_guard_source = False

            continue

        if isinstance(operator, Acc):
            strict_upper_bound = None
            state_matches_guard_source = False

            continue

        if isinstance(operator, Emit):
            #
            # EMIT does not change x.
            #
            continue

        #
        # Unknown operator: discard abstract facts.
        #
        strict_upper_bound = None
        guard_threshold = None
        state_matches_guard_source = False

    return tuple(result)




def _fuse_adjacent_decay_runs(
    operators: tuple,
) -> tuple:
    """
    Fuse every maximal consecutive run of DECAY operators.

    Algebraic parameterization:

        lambda = 1 / tau

    Composition:

        lambda_eff = sum(lambda_i)

    The rate summation is performed exactly with Fraction in
    search.decay_algebra.

    The resulting tau is converted back to float only at the boundary
    of the current runtime representation.

    IMPORTANT:

    This rewrite is exact over the mathematical reals, but it is not
    universally bit-exact under IEEE-754 evaluation. A downstream CMP
    can make a sub-ULP rounding difference observationally visible.
    """

    result = []
    index = 0

    while index < len(operators):
        operator = operators[index]

        if not isinstance(
            operator,
            Decay,
        ):
            result.append(
                operator
            )

            index += 1
            continue

        decays = []

        while (
            index < len(operators)
            and isinstance(
                operators[index],
                Decay,
            )
        ):
            decays.append(
                operators[index]
            )

            index += 1

        if len(decays) == 1:
            result.append(
                decays[0]
            )

            continue

        effective_tau = (
            combine_decay_taus(
                decay.tau
                for decay in decays
            )
        )

        result.append(
            Decay(
                tau=effective_tau,
            )
        )

    return tuple(result)



def _rewrite_threshold_control_patterns(
    operators: tuple,
) -> tuple:
    """
    Exact control-flow identities involving CMP, EMIT and RESET.

    These transformations perform no floating-point arithmetic and
    are therefore IEEE-safe as well as exact over the mathematical
    semantics.
    """

    result = list(operators)

    changed = True

    while changed:
        changed = False

        #
        # ----------------------------------------------------------
        # Rule 1
        #
        #   CMP(a) EMIT CMP(b) EMIT CMP(a)
        #
        #       ->
        #
        #   CMP(b) EMIT CMP(a) EMIT
        #
        # x is unchanged throughout the fragment.
        #
        # Both programs emit:
        #
        #   I[x >= a] + I[x >= b]
        #
        # events, and finish with guard:
        #
        #   x >= a
        #
        # We currently require identical EMIT operators.
        # ----------------------------------------------------------
        #
        index = 0

        while index + 4 < len(result):
            first = result[index:index + 5]

            if (
                isinstance(first[0], Compare)
                and isinstance(first[1], Emit)
                and isinstance(first[2], Compare)
                and isinstance(first[3], Emit)
                and isinstance(first[4], Compare)
                and first[0].threshold
                == first[4].threshold
                and first[1] == first[3]
            ):
                result[index:index + 5] = (
                    first[2],
                    first[3],
                    first[4],
                    first[1],
                )

                changed = True
                break

            index += 1

        if changed:
            continue

        #
        # ----------------------------------------------------------
        # Rule 2
        #
        # For:
        #
        #   low <= high
        #   reset_value < low
        #
        # normalize:
        #
        #   CMP(high)
        #   RESET(r)
        #   CMP(low)
        #   RESET(r)
        #   CMP(low)
        #
        #       ->
        #
        #   CMP(low)
        #   RESET(r)
        #   CMP(low)
        #
        # The trailing CMP is essential because final guard is part
        # of the current observation semantics.
        # ----------------------------------------------------------
        #
        index = 0

        while index + 4 < len(result):
            fragment = result[index:index + 5]

            if not (
                isinstance(fragment[0], Compare)
                and isinstance(fragment[1], Reset)
                and isinstance(fragment[2], Compare)
                and isinstance(fragment[3], Reset)
                and isinstance(fragment[4], Compare)
            ):
                index += 1
                continue

            high = fragment[0]
            reset1 = fragment[1]
            low = fragment[2]
            reset2 = fragment[3]
            final = fragment[4]

            if (
                reset1 == reset2
                and low.threshold
                == final.threshold
                and low.threshold
                <= high.threshold
                and reset1.value
                < low.threshold
            ):
                result[index:index + 5] = (
                    low,
                    reset2,
                    final,
                )

                changed = True
                break

            index += 1

        if changed:
            continue

        #
        # ----------------------------------------------------------
        # Rule 3
        #
        # For:
        #
        #   low < high
        #   reset_value < low
        #
        # and identical EMIT operators:
        #
        #   CMP(high) EMIT RESET(r) CMP(low) EMIT
        #
        #       ->
        #
        #   CMP(low) EMIT CMP(high) RESET(r) CMP(low)
        #
        # Piecewise:
        #
        #   x < low:
        #       no emit, no reset, final guard false
        #
        #   low <= x < high:
        #       one emit, no reset, final guard true
        #
        #   x >= high:
        #       one emit, reset to r, final guard false
        # ----------------------------------------------------------
        #
        index = 0

        while index + 4 < len(result):
            fragment = result[index:index + 5]

            if not (
                isinstance(fragment[0], Compare)
                and isinstance(fragment[1], Emit)
                and isinstance(fragment[2], Reset)
                and isinstance(fragment[3], Compare)
                and isinstance(fragment[4], Emit)
            ):
                index += 1
                continue

            high = fragment[0]
            emit1 = fragment[1]
            reset = fragment[2]
            low = fragment[3]
            emit2 = fragment[4]

            if (
                emit1 == emit2
                and low.threshold
                < high.threshold
                and reset.value
                < low.threshold
            ):
                result[index:index + 5] = (
                    low,
                    emit2,
                    high,
                    reset,
                    low,
                )

                changed = True
                break

            index += 1

    return tuple(result)



def _sink_positive_tick_false_compare_across_decay(
    operators: tuple,
) -> tuple:
    """
    Move a comparison to the right across DECAY when it is known to
    be FALSE for every positive tick.

    Suppose an earlier guarded RESET establishes:

        x < U

    and intervening DECAY operators accumulate rate:

        lambda

    If:

        U * exp(-lambda) < theta

    then for every integer delta >= 1:

        CMP(theta)

    is certainly FALSE.

    For delta == 0 every DECAY is the identity, so moving CMP across
    another DECAY leaves the comparison unchanged.

    Therefore, under these conditions:

        ... D ... CMP(theta) D2 ...

    may be normalized to:

        ... D ... D2 CMP(theta) ...

    This is a context-sensitive discrete-time identity, not a general
    CMP/DECAY commutation rule.
    """

    result = list(
        operators
    )

    strict_upper_bound = None
    rate_since_bound = Fraction(
        0,
        1,
    )

    guard_threshold = None
    state_matches_guard_source = False

    for index, operator in enumerate(
        result
    ):
        if isinstance(
            operator,
            Compare,
        ):
            if (
                index + 1 < len(result)
                and isinstance(
                    result[index + 1],
                    Decay,
                )
                and strict_upper_bound
                is not None
                and positive_tick_decay_bound_below(
                    upper_bound=(
                        strict_upper_bound
                    ),
                    accumulated_rate=(
                        rate_since_bound
                    ),
                    threshold=(
                        operator.threshold
                    ),
                )
            ):
                result[index], result[index + 1] = (
                    result[index + 1],
                    result[index],
                )

                #
                # Let the fixed-point loop recompute all abstract
                # facts from the beginning after one exact rewrite.
                #
                return tuple(
                    result
                )

            guard_threshold = (
                operator.threshold
            )

            state_matches_guard_source = True

            #
            # CMP does not modify x, so state bounds and accumulated
            # decay rate remain valid.
            #
            continue

        if isinstance(
            operator,
            Reset,
        ):
            if (
                state_matches_guard_source
                and guard_threshold is not None
                and operator.value
                < guard_threshold
            ):
                #
                # Whether the preceding guard was true or false:
                #
                #   true  -> x := value < threshold
                #   false -> x < threshold
                #
                # therefore:
                #
                #   x < threshold
                #
                strict_upper_bound = (
                    guard_threshold
                )

                rate_since_bound = Fraction(
                    0,
                    1,
                )

            else:
                #
                # Conservative fallback. A conditional reset not tied
                # to a usable comparison may invalidate our bound.
                #
                strict_upper_bound = None

                rate_since_bound = Fraction(
                    0,
                    1,
                )

            state_matches_guard_source = False
            continue

        if isinstance(
            operator,
            Decay,
        ):
            if strict_upper_bound is not None:
                rate_since_bound += (
                    tau_to_rate(
                        operator.tau
                    )
                )

            state_matches_guard_source = False
            continue

        if isinstance(
            operator,
            Acc,
        ):
            #
            # ACC can cross the state bound.
            #
            strict_upper_bound = None

            rate_since_bound = Fraction(
                0,
                1,
            )

            state_matches_guard_source = False
            continue

        if isinstance(
            operator,
            Emit,
        ):
            #
            # EMIT changes neither x nor the guard.
            #
            continue

        #
        # Unknown operator: discard abstract information.
        #
        strict_upper_bound = None

        rate_since_bound = Fraction(
            0,
            1,
        )

        guard_threshold = None
        state_matches_guard_source = False

    return tuple(
        result
    )


def canonicalize(
    program: Program,
) -> Program:
    """
    Reduce a Program using exact SPK/v0 rewrite rules.

    Rewriting continues until a fixed point is reached.
    """

    if not isinstance(program, Program):
        raise TypeError(
            "canonicalize requires a Program"
        )

    operators = program.operators

    while True:
        rewritten = _rewrite_local(
            operators
        )

        rewritten = _rewrite_threshold_control_patterns(
            rewritten
        )

        rewritten = _sink_positive_tick_false_compare_across_decay(
            rewritten
        )

        rewritten = _fuse_adjacent_decay_runs(
            rewritten
        )

        rewritten = _remove_guard_dead_operations(
            rewritten
        )

        rewritten = _eliminate_dead_compares(
            rewritten
        )

        rewritten = _eliminate_redundant_recompares(
            rewritten
        )

        rewritten = _eliminate_shadowed_resets(
            rewritten
        )

        rewritten = _commute_zero_reset_left_across_decay(
            rewritten
        )

        rewritten = _refine_guard_and_state_facts(
            rewritten
        )

        rewritten = _commute_provably_false_compare_right_across_decay(
            rewritten
        )

        rewritten = _commute_emit_left(
            rewritten
        )

        rewritten = _rewrite_local(
            rewritten
        )

        if rewritten == operators:
            return Program(rewritten)

        operators = rewritten
