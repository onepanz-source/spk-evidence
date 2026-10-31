from __future__ import annotations

from collections import Counter

from spk_core.canonicalize import (
    canonicalize_core_program,
)

from search.core_temporal_normalize_v0 import (
    BATCHES,
    DELTAS,
    RAWS,
    normalize_temporal,
    observe,
    programs,
)


MAX_ROUNDS = 64


def program_key(program):
    return repr(
        program.instructions
    )


def step_tc(program):
    """
    Temporal normalization, then Core canonicalization.
    """
    return canonicalize_core_program(
        normalize_temporal(
            program
        )
    )


def step_ct(program):
    """
    Core canonicalization, then temporal normalization.
    """
    return normalize_temporal(
        canonicalize_core_program(
            program
        )
    )


def fixed_point(
    program,
    step,
):
    current = program

    seen = {
        program_key(
            current
        ): 0
    }

    for round_index in range(
        1,
        MAX_ROUNDS + 1,
    ):
        target = step(
            current
        )

        if (
            target.instructions
            == current.instructions
        ):
            return (
                target,
                round_index,
                None,
            )

        key = program_key(
            target
        )

        if key in seen:
            return (
                target,
                round_index,
                (
                    seen[key],
                    round_index,
                ),
            )

        seen[
            key
        ] = round_index

        current = target

    raise RuntimeError(
        "joint normalization exceeded "
        f"{MAX_ROUNDS} rounds"
    )


def compare_behavior(
    left,
    right,
):
    cases = 0

    equal_cases = 0

    both_overflow = 0

    overflow_asymmetry = 0

    successful_mismatch = 0

    first_failure = None

    for raw in RAWS:
        for delta in DELTAS:
            for channels in BATCHES:
                left_obs = observe(
                    left,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                right_obs = observe(
                    right,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                cases += 1

                if left_obs == right_obs:
                    equal_cases += 1

                    if (
                        left_obs.status
                        == "overflow"
                    ):
                        both_overflow += 1

                    continue

                if (
                    left_obs.status
                    != right_obs.status
                ):
                    overflow_asymmetry += 1

                    kind = (
                        "overflow-asymmetry"
                    )

                else:
                    successful_mismatch += 1

                    kind = (
                        "successful-observation"
                    )

                if first_failure is None:
                    first_failure = (
                        kind,
                        raw,
                        delta,
                        channels,
                        left_obs,
                        right_obs,
                    )

    return {
        "cases": cases,
        "equal_cases": (
            equal_cases
        ),
        "both_overflow": (
            both_overflow
        ),
        "overflow_asymmetry": (
            overflow_asymmetry
        ),
        "successful_mismatch": (
            successful_mismatch
        ),
        "first_failure": (
            first_failure
        ),
    }


def main():
    print(
        "SPK CORE / TEMPORAL "
        "NORMALIZER INTERACTION v0"
    )

    print()

    syntactic = 0

    one_pass_disagreements = 0

    fixed_point_disagreements = 0

    tc_cycles = 0
    ct_cycles = 0

    max_tc_rounds = 0
    max_ct_rounds = 0

    tc_normal_forms = set()
    ct_normal_forms = set()

    behavior_cases = 0
    behavior_equal = 0
    behavior_both_overflow = 0
    behavior_overflow_asymmetry = 0
    behavior_successful_mismatch = 0

    first_one_pass = None
    first_fixed_point = None
    first_behavior_failure = None

    disagreement_shapes = Counter()

    for program in programs():
        syntactic += 1

        temporal_then_core = (
            step_tc(
                program
            )
        )

        core_then_temporal = (
            step_ct(
                program
            )
        )

        if (
            temporal_then_core.instructions
            != core_then_temporal.instructions
        ):
            one_pass_disagreements += 1

            if first_one_pass is None:
                first_one_pass = (
                    program,
                    temporal_then_core,
                    core_then_temporal,
                )

        (
            tc_fixed,
            tc_rounds,
            tc_cycle,
        ) = fixed_point(
            program,
            step_tc,
        )

        (
            ct_fixed,
            ct_rounds,
            ct_cycle,
        ) = fixed_point(
            program,
            step_ct,
        )

        max_tc_rounds = max(
            max_tc_rounds,
            tc_rounds,
        )

        max_ct_rounds = max(
            max_ct_rounds,
            ct_rounds,
        )

        if tc_cycle is not None:
            tc_cycles += 1

        if ct_cycle is not None:
            ct_cycles += 1

        tc_normal_forms.add(
            program_key(
                tc_fixed
            )
        )

        ct_normal_forms.add(
            program_key(
                ct_fixed
            )
        )

        if (
            tc_fixed.instructions
            == ct_fixed.instructions
        ):
            continue

        fixed_point_disagreements += 1

        disagreement_shapes[
            (
                len(
                    tc_fixed.instructions
                ),
                len(
                    ct_fixed.instructions
                ),
            )
        ] += 1

        if first_fixed_point is None:
            first_fixed_point = (
                program,
                tc_fixed,
                ct_fixed,
            )

        behavior = compare_behavior(
            tc_fixed,
            ct_fixed,
        )

        behavior_cases += (
            behavior[
                "cases"
            ]
        )

        behavior_equal += (
            behavior[
                "equal_cases"
            ]
        )

        behavior_both_overflow += (
            behavior[
                "both_overflow"
            ]
        )

        behavior_overflow_asymmetry += (
            behavior[
                "overflow_asymmetry"
            ]
        )

        behavior_successful_mismatch += (
            behavior[
                "successful_mismatch"
            ]
        )

        if (
            first_behavior_failure
            is None
            and behavior[
                "first_failure"
            ]
            is not None
        ):
            first_behavior_failure = (
                program,
                tc_fixed,
                ct_fixed,
                behavior[
                    "first_failure"
                ],
            )

        if (
            syntactic % 1000
            == 0
        ):
            print(
                f"programs={syntactic:5d} "
                f"one_pass_diff="
                f"{one_pass_disagreements:5d} "
                f"fixed_diff="
                f"{fixed_point_disagreements:5d} "
                f"tc_nf="
                f"{len(tc_normal_forms):5d} "
                f"ct_nf="
                f"{len(ct_normal_forms):5d}"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "ONE-PASS INTERACTION"
    )
    print(
        "=" * 88
    )

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"C(T(P)) != T(C(P)): "
        f"{one_pass_disagreements}"
    )

    if first_one_pass is not None:
        (
            source,
            tc,
            ct,
        ) = first_one_pass

        print()
        print(
            "first one-pass disagreement:"
        )

        print(
            f"    P  = "
            f"{source.instructions}"
        )

        print(
            f"    CT = "
            f"{tc.instructions}"
        )

        print(
            f"    TC = "
            f"{ct.instructions}"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "JOINT FIXED POINTS"
    )
    print(
        "=" * 88
    )

    print(
        f"TC fixed-point classes: "
        f"{len(tc_normal_forms)}"
    )

    print(
        f"CT fixed-point classes: "
        f"{len(ct_normal_forms)}"
    )

    print(
        f"fixed-point disagreements: "
        f"{fixed_point_disagreements}"
    )

    print(
        f"TC cycles: "
        f"{tc_cycles}"
    )

    print(
        f"CT cycles: "
        f"{ct_cycles}"
    )

    print(
        f"maximum TC rounds: "
        f"{max_tc_rounds}"
    )

    print(
        f"maximum CT rounds: "
        f"{max_ct_rounds}"
    )

    if disagreement_shapes:
        print()
        print(
            "fixed-point length pairs:"
        )

        for (
            lengths,
            count,
        ) in sorted(
            disagreement_shapes.items()
        ):
            print(
                f"    "
                f"{lengths[0]} vs "
                f"{lengths[1]}: "
                f"{count}"
            )

    if first_fixed_point is not None:
        (
            source,
            tc_fixed,
            ct_fixed,
        ) = first_fixed_point

        print()
        print(
            "first fixed-point disagreement:"
        )

        print(
            f"    P="
            f"{source.instructions}"
        )

        print(
            f"    NF_TC="
            f"{tc_fixed.instructions}"
        )

        print(
            f"    NF_CT="
            f"{ct_fixed.instructions}"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "BEHAVIOR OF DISTINCT FIXED POINTS"
    )
    print(
        "=" * 88
    )

    print(
        f"observation cases: "
        f"{behavior_cases}"
    )

    print(
        f"equal observations: "
        f"{behavior_equal}"
    )

    print(
        f"both overflow: "
        f"{behavior_both_overflow}"
    )

    print(
        f"overflow asymmetries: "
        f"{behavior_overflow_asymmetry}"
    )

    print(
        f"successful observation mismatches: "
        f"{behavior_successful_mismatch}"
    )

    if first_behavior_failure is not None:
        (
            source,
            tc_fixed,
            ct_fixed,
            failure,
        ) = first_behavior_failure

        print()
        print(
            "first behavioral disagreement:"
        )

        print(
            f"    source="
            f"{source.instructions}"
        )

        print(
            f"    NF_TC="
            f"{tc_fixed.instructions}"
        )

        print(
            f"    NF_CT="
            f"{ct_fixed.instructions}"
        )

        print(
            f"    witness="
            f"{failure}"
        )

    print()
    print(
        "=" * 88
    )
    print(
        "CHECKPOINT"
    )
    print(
        "=" * 88
    )

    if (
        tc_cycles
        or ct_cycles
    ):
        print(
            "JOINT NORMALIZATION CYCLE "
            "DETECTED"
        )

        raise SystemExit(1)

    if (
        fixed_point_disagreements
        == 0
    ):
        print(
            "JOINT NORMALIZERS CONVERGE "
            "SYNTACTICALLY"
        )

    elif (
        behavior_overflow_asymmetry
        == 0
        and behavior_successful_mismatch
        == 0
    ):
        print(
            "JOINT NORMALIZERS DO NOT "
            "CONVERGE SYNTACTICALLY"
        )

        print(
            "BUT DISTINCT FIXED POINTS "
            "ARE BEHAVIORALLY EQUIVALENT "
            "ON THE DECLARED CORPUS"
        )

    else:
        print(
            "NORMALIZER ORDER HAS "
            "OBSERVABLE CONSEQUENCES"
        )

    print()
    print(
        "CORE/TEMPORAL INTERACTION "
        "CENSUS COMPLETE"
    )

    print(
        "No confluence claim beyond "
        "the declared finite domain."
    )


if __name__ == "__main__":
    main()
