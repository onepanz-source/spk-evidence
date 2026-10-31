from __future__ import annotations

from spk_core.rules import unchecked_domain_rules

from dataclasses import dataclass
from itertools import product
from typing import Callable

from spk.event import SpikeTrain
from spk_core import canonicalize as structural
from spk_core import semantic_canonicalize as semantic
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.runtime import (
    run_core_program,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


#
# Same seven-instruction syntax basis used by the depth-5 closure,
# but NOT the same observational corpus.
#
PROGRAM_POOL = (
    ShiftDecay(1),
    CoreAcc(1, 0),
    CoreAcc(1, 1),
    CoreCmp(1),
    CoreCmp(2),
    CoreEmit(7),
    CoreReset(0),
)


INITIAL_RAWS = (
    0,
    1,
    2,
    3,
    4,
    7,
    8,
    15,
    16,
    31,
    32,
    63,
    64,
    127,
    128,
    240,
    248,
    254,
    255,
)


TRAIN_PAIRS = (
    ((0, 0),),
    ((0, 1),),
    ((0, 2),),

    ((0, 0), (0, 0)),
    ((0, 1), (0, 1)),
    ((0, 0), (0, 1)),
    ((0, 0), (0, 2)),
    ((0, 1), (0, 2)),
    ((0, 0), (0, 0), (0, 1)),

    ((1, 0),),
    ((1, 1),),
    ((1, 2),),
    ((1, 0), (1, 0)),
    ((1, 0), (1, 1)),

    ((0, 0), (1, 0)),
    ((0, 1), (1, 1)),
    ((0, 2), (1, 0)),
    ((0, 0), (2, 1)),
    ((1, 0), (3, 0)),
    ((0, 0), (0, 1), (2, 0)),
)


TRAINS = tuple(
    SpikeTrain.from_pairs(
        pairs
    )
    for pairs in TRAIN_PAIRS
)


@dataclass(frozen=True)
class Observation:
    output: tuple[tuple[int, int], ...]
    final_raw: int
    final_guard: bool
    last_timestamp: int


@dataclass
class RuleStats:
    source_programs: int = 0
    changed_programs: int = 0
    activation_fixtures: int = 0

    observation_cases: int = 0

    source_overflows: int = 0

    #
    # Runtime L-* laws must preserve overflow as an observable
    # outcome in both directions.
    #
    matched_runtime_overflows: int = 0
    runtime_source_overflow_removed: int = 0
    runtime_target_overflow_failures: int = 0

    #
    # D-* laws are valid only in their declared successful
    # bounded domain. These counters make exclusions explicit.
    #
    domain_source_overflow_exclusions: int = 0
    domain_target_overflow_escapes: int = 0

    value_mismatches: int = 0


@dataclass(frozen=True)
class Rewrite:
    name: str
    rule_ids: tuple[str, ...]
    apply: Callable[
        [CoreProgram],
        CoreProgram,
    ]


def structural_adapter(
    function,
    *,
    with_config: bool = False,
):
    def apply(
        program: CoreProgram,
    ) -> CoreProgram:
        instructions = list(
            program.instructions
        )

        if with_config:
            result = function(
                instructions,
                CONFIG,
            )
        else:
            result = function(
                instructions
            )

        if isinstance(
            result,
            CoreProgram,
        ):
            return result

        if result is None:
            result = instructions

        return CoreProgram(
            tuple(result)
        )

    return apply


def semantic_adapter(
    function,
    *,
    with_config: bool = False,
):
    def apply(
        program: CoreProgram,
    ) -> CoreProgram:
        if with_config:
            return function(
                CONFIG,
                program,
            )

        return function(
            program
        )

    return apply


REWRITES = (
    Rewrite(
        "_remove_zero_acc",
        ("L-ACC-01",),
        structural_adapter(
            structural._remove_zero_acc
        ),
    ),
    Rewrite(
        "_remove_false_guard_prefix",
        ("L-GUARD-02",),
        structural_adapter(
            structural._remove_false_guard_prefix
        ),
    ),
    Rewrite(
        "_remove_dead_compares",
        ("L-GUARD-01",),
        structural_adapter(
            structural._remove_dead_compares
        ),
    ),
    Rewrite(
        "_move_emit_left",
        ("L-EMIT-01",),
        structural_adapter(
            structural._move_emit_left
        ),
    ),
    Rewrite(
        "_collapse_adjacent_resets",
        ("L-RESET-01",),
        structural_adapter(
            structural._collapse_adjacent_resets
        ),
    ),
    Rewrite(
        "_commute_zero_reset_across_shift",
        ("L-TIME-01",),
        structural_adapter(
            structural._commute_zero_reset_across_shift
        ),
    ),
    Rewrite(
        "_remove_shift_between_cmp1_and_reset0",
        ("L-TIME-02",),
        structural_adapter(
            structural._remove_shift_between_cmp1_and_reset0
        ),
    ),
    Rewrite(
        "_remove_shift_when_state_known_zero",
        ("L-TIME-03",),
        structural_adapter(
            structural._remove_shift_when_state_known_zero
        ),
    ),
    Rewrite(
        "_remove_pre_acc_shift_under_cmp1_reset0",
        ("D-TIME-05",),
        structural_adapter(
            structural._remove_pre_acc_shift_under_cmp1_reset0
        ),
    ),
    Rewrite(
        "_sink_known_false_compare_across_shift",
        ("L-TIME-05",),
        structural_adapter(
            structural._sink_known_false_compare_across_shift
        ),
    ),
    Rewrite(
        "_cap_shift_before_zero_reset_from_compare_bound",
        ("L-TIME-07",),
        structural_adapter(
            structural._cap_shift_before_zero_reset_from_compare_bound
        ),
    ),
    Rewrite(
        "_normalize_shift_decay_runs",
        ("L-TIME-06",),
        structural_adapter(
            structural._normalize_shift_decay_runs
        ),
    ),
    Rewrite(
        "_normalize_acc_runs",
        (
            "L-ACC-02",
            "L-ACC-03",
        ),
        structural_adapter(
            structural._normalize_acc_runs
        ),
    ),
    Rewrite(
        "_sort_emit_runs",
        ("L-EMIT-02",),
        structural_adapter(
            structural._sort_emit_runs
        ),
    ),
    Rewrite(
        "_remove_redundant_repeated_compares",
        ("L-CMP-01",),
        structural_adapter(
            structural._remove_redundant_repeated_compares
        ),
    ),
    Rewrite(
        "_normalize_false_compare_after_reset",
        (
            "L-CMP-02",
            "L-GUARD-03",
        ),
        structural_adapter(
            structural._normalize_false_compare_after_reset
        ),
    ),
    Rewrite(
        "_remove_shadowed_resets",
        ("D-RESET-01",),
        structural_adapter(
            structural._remove_shadowed_resets
        ),
    ),
    Rewrite(
        "_pull_saturated_acc_across_compare",
        ("L-ACC-04",),
        structural_adapter(
            structural._pull_saturated_acc_across_compare,
            with_config=True,
        ),
    ),
    Rewrite(
        "_cap_saturated_acc_before_guarded_reset",
        ("D-ACC-03",),
        structural_adapter(
            structural._cap_saturated_acc_before_guarded_reset,
            with_config=True,
        ),
    ),
    Rewrite(
        "_strip_state_before_lsb_annihilator",
        ("D-ZERO-01",),
        structural_adapter(
            structural._strip_state_before_lsb_annihilator
        ),
    ),

    Rewrite(
        "_normalize_shared_count_cmp1_acc_commute",
        ("L-COUNT-01",),
        semantic_adapter(
            semantic._normalize_shared_count_cmp1_acc_commute
        ),
    ),
    Rewrite(
        "_normalize_shared_count_pre_shift_acc",
        ("D-COUNT-01",),
        semantic_adapter(
            semantic._normalize_shared_count_pre_shift_acc
        ),
    ),
    Rewrite(
        "_normalize_temporal_cmp2_barrier",
        ("L-TIME-08",),
        semantic_adapter(
            semantic._normalize_temporal_cmp2_barrier
        ),
    ),
    Rewrite(
        "_normalize_temporal_guarded_reset_commute",
        ("L-TIME-09",),
        semantic_adapter(
            semantic._normalize_temporal_guarded_reset_commute
        ),
    ),
    Rewrite(
        "_normalize_temporal_shift_width",
        ("D-TIME-01",),
        semantic_adapter(
            semantic._normalize_temporal_shift_width,
            with_config=True,
        ),
    ),
    Rewrite(
        "_normalize_positive_acc_before_cmp1_zero_reset",
        ("D-ACC-01",),
        semantic_adapter(
            semantic._normalize_positive_acc_before_cmp1_zero_reset
        ),
    ),
    Rewrite(
        "_normalize_emit_reset_partition",
        ("L-CTRL-02",),
        semantic_adapter(
            semantic._normalize_emit_reset_partition
        ),
    ),
    Rewrite(
        "_normalize_cmp_emit_runs",
        ("L-CTRL-01",),
        semantic_adapter(
            semantic._normalize_cmp_emit_runs
        ),
    ),
    Rewrite(
        "_remove_dead_state_before_zero_barrier",
        ("D-ZERO-02",),
        semantic_adapter(
            semantic._remove_dead_state_before_zero_barrier
        ),
    ),
)



#
# Targeted witnesses for rules that the original seven-instruction
# depth-5 closure pool cannot necessarily activate.
#
# These programs do not replace systematic enumeration. They ensure
# that every implementation rewrite is actually exercised at least
# once by this soundness gate.
#
ACTIVATION_PROGRAMS = {
    "_remove_zero_acc": (
        CoreProgram(
            (
                CoreAcc(0, 0),
            )
        ),
    ),

    "_cap_shift_before_zero_reset_from_compare_bound": (
        CoreProgram(
            (
                CoreCmp(8),
                ShiftDecay(7),
                CoreReset(0),
            )
        ),
        CoreProgram(
            (
                CoreCmp(4),
                ShiftDecay(5),
                CoreReset(0),
            )
        ),
    ),

    "_sort_emit_runs": (
        CoreProgram(
            (
                CoreEmit(8),
                CoreEmit(7),
            )
        ),
    ),

    "_cap_saturated_acc_before_guarded_reset": (
        CoreProgram(
            (
                CoreAcc(4, 0),
                CoreCmp(2),
                CoreEmit(7),
                CoreReset(0),
            )
        ),
        CoreProgram(
            (
                CoreAcc(8, 0),
                CoreCmp(2),
                CoreReset(0),
            )
        ),
    ),

    "_normalize_temporal_shift_width": (
        CoreProgram(
            (
                CoreCmp(2),
                CoreReset(0),
                ShiftDecay(2),
            )
        ),
        CoreProgram(
            (
                CoreCmp(2),
                CoreReset(0),
                ShiftDecay(4),
            )
        ),
    ),

    "_normalize_positive_acc_before_cmp1_zero_reset": (
        CoreProgram(
            (
                CoreAcc(2, 0),
                CoreCmp(1),
                CoreReset(0),
            )
        ),
        CoreProgram(
            (
                CoreAcc(4, 0),
                CoreCmp(1),
                CoreEmit(7),
                CoreReset(0),
            )
        ),
    ),
}


def programs_for_rewrite(
    rewrite: Rewrite,
):
    yield from programs()

    yield from ACTIVATION_PROGRAMS.get(
        rewrite.name,
        (),
    )


def programs():
    for depth in range(
        1,
        6,
    ):
        for instructions in product(
            PROGRAM_POOL,
            repeat=depth,
        ):
            yield CoreProgram(
                tuple(instructions)
            )


def observe(
    program: CoreProgram,
    train: SpikeTrain,
    initial_raw: int,
) -> Observation:
    result = run_core_program(
        CONFIG,
        program,
        train,
        initial_raw=initial_raw,
    )

    return Observation(
        output=tuple(
            result.output.as_pairs()
        ),
        final_raw=result.final_raw,
        final_guard=result.final_guard,
        last_timestamp=(
            result.last_timestamp
        ),
    )


def check_rewrite(
    rewrite: Rewrite,
) -> RuleStats:
    stats = RuleStats()

    fixtures = ACTIVATION_PROGRAMS.get(
        rewrite.name,
        (),
    )

    stats.activation_fixtures = len(
        fixtures
    )

    domain_rule = all(
        rule_id.startswith("D-")
        for rule_id in rewrite.rule_ids
    )

    first_failure = None

    for source in programs_for_rewrite(
        rewrite
    ):
        stats.source_programs += 1

        if domain_rule:
            with unchecked_domain_rules():
                target = rewrite.apply(
                    source
                )
        else:
            target = rewrite.apply(
                source
            )

        if target == source:
            continue

        stats.changed_programs += 1

        for initial_raw in INITIAL_RAWS:
            for train in TRAINS:
                stats.observation_cases += 1

                #
                # First evaluate the source.
                #
                try:
                    source_obs = observe(
                        source,
                        train,
                        initial_raw,
                    )

                    source_overflow = False

                except OverflowError:
                    source_obs = None
                    source_overflow = True

                    stats.source_overflows += 1

                #
                # A D-* rule only claims equivalence inside its
                # successful bounded domain.
                #
                if source_overflow and domain_rule:
                    stats.domain_source_overflow_exclusions += 1
                    continue

                #
                # For an L-* rule overflow itself is observable.
                # Therefore a source overflow must also occur in the
                # rewritten target.
                #
                if source_overflow:
                    try:
                        target_obs = observe(
                            target,
                            train,
                            initial_raw,
                        )

                    except OverflowError:
                        stats.matched_runtime_overflows += 1
                        continue

                    stats.runtime_source_overflow_removed += 1

                    first_failure = (
                        "SOURCE OVERFLOW REMOVED",
                        source,
                        target,
                        initial_raw,
                        tuple(
                            train.as_pairs()
                        ),
                        None,
                        target_obs,
                    )
                    break

                #
                # Source succeeded. The target must now either
                # succeed equivalently, or for a D-* rule explicitly
                # leave the declared bounded domain.
                #
                try:
                    target_obs = observe(
                        target,
                        train,
                        initial_raw,
                    )

                except OverflowError:
                    if domain_rule:
                        stats.domain_target_overflow_escapes += 1
                        continue

                    stats.runtime_target_overflow_failures += 1

                    first_failure = (
                        "TARGET OVERFLOW ESCAPE",
                        source,
                        target,
                        initial_raw,
                        tuple(
                            train.as_pairs()
                        ),
                        source_obs,
                        None,
                    )
                    break

                #
                # Whenever both executions are defined, every rule,
                # including D-*, must preserve the complete
                # observation.
                #
                if source_obs != target_obs:
                    stats.value_mismatches += 1

                    first_failure = (
                        "OBSERVATION MISMATCH",
                        source,
                        target,
                        initial_raw,
                        tuple(
                            train.as_pairs()
                        ),
                        source_obs,
                        target_obs,
                    )
                    break

            if first_failure:
                break

        if first_failure:
            break

    if first_failure:
        (
            kind,
            source,
            target,
            initial_raw,
            train,
            source_obs,
            target_obs,
        ) = first_failure

        raise AssertionError(
            "\n".join(
                (
                    f"RULE SOUNDNESS FAILURE: {kind}",
                    f"helper={rewrite.name}",
                    f"rules={rewrite.rule_ids}",
                    f"source={source}",
                    f"target={target}",
                    f"initial_raw={initial_raw}",
                    f"train={train}",
                    f"source_obs={source_obs}",
                    f"target_obs={target_obs}",
                )
            )
        )

    #
    # A rule that was never activated has not been tested.
    #
    if stats.changed_programs == 0:
        raise AssertionError(
            "\n".join(
                (
                    "RULE ACTIVATION FAILURE",
                    f"helper={rewrite.name}",
                    f"rules={rewrite.rule_ids}",
                    "changed_programs=0",
                    f"activation_fixtures={stats.activation_fixtures}",
                )
            )
        )

    return stats


def main() -> None:
    print(
        "SPK/CORE RULE SOUNDNESS v0"
    )

    print(
        f"config: "
        f"state_bits={CONFIG.state_bits} "
        f"fractional_bits={CONFIG.fractional_bits} "
        f"max_raw={CONFIG.max_raw}"
    )

    print(
        "base syntactic programs: 19607"
    )

    print(
        f"rewrite helpers: "
        f"{len(REWRITES)}"
    )

    print(
        f"initial states: "
        f"{len(INITIAL_RAWS)}"
    )

    print(
        f"probe trains: "
        f"{len(TRAINS)}"
    )

    print()

    grand_changed = 0
    grand_cases = 0

    grand_source_overflows = 0
    grand_matched_runtime_overflows = 0

    grand_runtime_source_removed = 0
    grand_runtime_target_failures = 0

    grand_domain_source_exclusions = 0
    grand_domain_target_escapes = 0

    grand_value_mismatches = 0

    for index, rewrite in enumerate(
        REWRITES,
        start=1,
    ):
        stats = check_rewrite(
            rewrite
        )

        grand_changed += (
            stats.changed_programs
        )

        grand_cases += (
            stats.observation_cases
        )

        grand_source_overflows += (
            stats.source_overflows
        )

        grand_matched_runtime_overflows += (
            stats.matched_runtime_overflows
        )

        grand_runtime_source_removed += (
            stats.runtime_source_overflow_removed
        )

        grand_runtime_target_failures += (
            stats.runtime_target_overflow_failures
        )

        grand_domain_source_exclusions += (
            stats.domain_source_overflow_exclusions
        )

        grand_domain_target_escapes += (
            stats.domain_target_overflow_escapes
        )

        grand_value_mismatches += (
            stats.value_mismatches
        )

        kind = (
            "DOMAIN"
            if all(
                rule_id.startswith("D-")
                for rule_id in rewrite.rule_ids
            )
            else "RUNTIME"
        )

        print(
            f"{index:02d}/"
            f"{len(REWRITES):02d} "
            f"{rewrite.name:52} "
            f"type={kind:7} "
            f"rules={','.join(rewrite.rule_ids):22} "
            f"changed={stats.changed_programs:5d} "
            f"fixtures={stats.activation_fixtures:2d} "
            f"cases={stats.observation_cases:8d} "
            f"src_ovf={stats.source_overflows:6d} "
            f"matched_ovf={stats.matched_runtime_overflows:6d} "
            f"D-src={stats.domain_source_overflow_exclusions:6d} "
            f"D-tgt={stats.domain_target_overflow_escapes:6d}"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "FINAL CHECKPOINT"
    )
    print(
        "=" * 88
    )

    print(
        f"rewrite helpers checked: "
        f"{len(REWRITES)}"
    )

    print(
        f"changed source programs: "
        f"{grand_changed}"
    )

    print(
        f"concrete observation cases: "
        f"{grand_cases}"
    )

    print(
        f"source overflow cases observed: "
        f"{grand_source_overflows}"
    )

    print(
        f"matched runtime overflow cases: "
        f"{grand_matched_runtime_overflows}"
    )

    print(
        f"runtime source-overflow removals: "
        f"{grand_runtime_source_removed}"
    )

    print(
        f"runtime target-overflow failures: "
        f"{grand_runtime_target_failures}"
    )

    print(
        f"declared domain source exclusions: "
        f"{grand_domain_source_exclusions}"
    )

    print(
        f"declared domain target escapes: "
        f"{grand_domain_target_escapes}"
    )

    print(
        f"observation mismatches: "
        f"{grand_value_mismatches}"
    )

    print()

    if (
        grand_runtime_source_removed
        or grand_runtime_target_failures
        or grand_value_mismatches
    ):
        print(
            "RULE SOUNDNESS CHECKPOINT: FAIL"
        )
        raise SystemExit(1)

    if (
        grand_domain_source_exclusions
        or grand_domain_target_escapes
    ):
        print(
            "RULE SOUNDNESS CHECKPOINT: "
            "PASS WITH DECLARED DOMAIN EXCLUSIONS"
        )
    else:
        print(
            "RULE SOUNDNESS CHECKPOINT: PASS"
        )


if __name__ == "__main__":
    main()
