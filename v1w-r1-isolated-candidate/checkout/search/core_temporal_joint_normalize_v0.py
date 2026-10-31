from __future__ import annotations

from collections import defaultdict

from spk_core.canonicalize import (
    canonicalize_core_program,
)

from spk_core.isa import (
    CoreCmp,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)

from search.core_temporal_normalize_v0 import (
    BATCHES,
    DELTAS,
    RAWS,
    normalize_temporal,
    observe,
    programs,
)

from search.core_temporal_core_interaction_v0 import (
    fixed_point,
    program_key,
    step_ct,
    step_tc,
)


MAX_ROUNDS = 32


def guarded_temporal_overwrite(
    program: CoreProgram,
) -> CoreProgram:
    """
    Exact local rule for unsigned Core state:

        CMP(0); SHIFT(k); RESET(v)
            -> CMP(0); RESET(v)

        CMP(1); SHIFT(k); RESET(v)
            -> CMP(1); RESET(v)

    Repeat because removing one shift can expose another redex.
    """

    instructions = list(
        program.instructions
    )

    while True:
        changed = False

        for index in range(
            len(instructions) - 2
        ):
            first = instructions[
                index
            ]

            second = instructions[
                index + 1
            ]

            third = instructions[
                index + 2
            ]

            if not isinstance(
                first,
                CoreCmp,
            ):
                continue

            if (
                first.threshold_raw
                not in (
                    0,
                    1,
                )
            ):
                continue

            if not isinstance(
                second,
                ShiftDecay,
            ):
                continue

            if not isinstance(
                third,
                CoreReset,
            ):
                continue

            del instructions[
                index + 1
            ]

            changed = True
            break

        if not changed:
            break

    return CoreProgram(
        tuple(
            instructions
        )
    )


def joint_step(
    program: CoreProgram,
) -> CoreProgram:
    """
    Deliberate global orientation:

        1. existing Core simplification
        2. exact guarded temporal overwrite
        3. temporal normalization last

    Temporal normalization therefore owns the orientation of
    commuting SHIFT pairs such as SHIFT/EMIT.
    """

    result = (
        canonicalize_core_program(
            program
        )
    )

    result = (
        guarded_temporal_overwrite(
            result
        )
    )

    result = (
        normalize_temporal(
            result
        )
    )

    return result


def joint_normalize(
    program: CoreProgram,
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
        target = joint_step(
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


def main():
    print(
        "SPK CORE + TEMPORAL "
        "JOINT NORMALIZATION v0"
    )

    source_count = 0

    normal_forms = {}

    max_rounds = 0

    cycles = 0
    idempotence_failures = 0

    observation_cases = 0
    observation_mismatches = 0

    first_failure = None

    #
    # Compare the new quotient against both old induced
    # partitions.
    #
    tc_to_joint = defaultdict(
        set
    )

    ct_to_joint = defaultdict(
        set
    )

    joint_to_tc = defaultdict(
        set
    )

    joint_to_ct = defaultdict(
        set
    )

    for source in programs():
        source_count += 1

        (
            joint,
            rounds,
            cycle,
        ) = joint_normalize(
            source
        )

        max_rounds = max(
            max_rounds,
            rounds,
        )

        if cycle is not None:
            cycles += 1

            if first_failure is None:
                first_failure = (
                    "cycle",
                    source,
                    joint,
                    cycle,
                )

        joint_key = program_key(
            joint
        )

        normal_forms[
            joint_key
        ] = joint

        #
        # Idempotence.
        #
        (
            joint_again,
            _,
            cycle_again,
        ) = joint_normalize(
            joint
        )

        if (
            cycle_again is not None
            or joint_again.instructions
            != joint.instructions
        ):
            idempotence_failures += 1

            if first_failure is None:
                first_failure = (
                    "idempotence",
                    source,
                    joint,
                    joint_again,
                    cycle_again,
                )

        #
        # Finite semantic bridge source -> joint NF.
        #
        for raw in RAWS:
            for delta in DELTAS:
                for channels in BATCHES:
                    left = observe(
                        source,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    right = observe(
                        joint,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    observation_cases += 1

                    if left == right:
                        continue

                    observation_mismatches += 1

                    if first_failure is None:
                        first_failure = (
                            "semantic",
                            source,
                            joint,
                            raw,
                            delta,
                            channels,
                            left,
                            right,
                        )

        #
        # Old T->C and C->T quotients.
        #
        (
            tc,
            _,
            tc_cycle,
        ) = fixed_point(
            source,
            step_tc,
        )

        (
            ct,
            _,
            ct_cycle,
        ) = fixed_point(
            source,
            step_ct,
        )

        if (
            tc_cycle is not None
            or ct_cycle is not None
        ):
            raise AssertionError(
                "unexpected old composite cycle"
            )

        tc_key = program_key(
            tc
        )

        ct_key = program_key(
            ct
        )

        tc_to_joint[
            tc_key
        ].add(
            joint_key
        )

        ct_to_joint[
            ct_key
        ].add(
            joint_key
        )

        joint_to_tc[
            joint_key
        ].add(
            tc_key
        )

        joint_to_ct[
            joint_key
        ].add(
            ct_key
        )

        if (
            source_count % 1000
            == 0
        ):
            print(
                f"programs="
                f"{source_count:5d} "
                f"joint_nf="
                f"{len(normal_forms):4d} "
                f"cycles="
                f"{cycles} "
                f"semantic_mismatch="
                f"{observation_mismatches}"
            )

    tc_splits = {
        key: values
        for key, values
        in tc_to_joint.items()
        if len(values) > 1
    }

    ct_splits = {
        key: values
        for key, values
        in ct_to_joint.items()
        if len(values) > 1
    }

    tc_merges = {
        key: values
        for key, values
        in joint_to_tc.items()
        if len(values) > 1
    }

    ct_merges = {
        key: values
        for key, values
        in joint_to_ct.items()
        if len(values) > 1
    }

    print()
    print(
        "=" * 88
    )
    print(
        "JOINT NORMAL FORM"
    )
    print(
        "=" * 88
    )

    print(
        f"source programs: "
        f"{source_count}"
    )

    print(
        f"joint normal-form classes: "
        f"{len(normal_forms)}"
    )

    print(
        f"class-count hypothesis 605: "
        f"{len(normal_forms) == 605}"
    )

    print(
        f"maximum rounds: "
        f"{max_rounds}"
    )

    print(
        f"cycles: "
        f"{cycles}"
    )

    print(
        f"idempotence failures: "
        f"{idempotence_failures}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "FINITE SEMANTIC BRIDGE"
    )
    print(
        "=" * 88
    )

    print(
        f"observation cases: "
        f"{observation_cases}"
    )

    print(
        f"observation mismatches: "
        f"{observation_mismatches}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "RELATION TO OLD QUOTIENTS"
    )
    print(
        "=" * 88
    )

    print(
        f"T->C classes split by joint: "
        f"{len(tc_splits)}"
    )

    print(
        f"C->T classes split by joint: "
        f"{len(ct_splits)}"
    )

    print(
        f"joint classes merging "
        f"multiple T->C classes: "
        f"{len(tc_merges)}"
    )

    print(
        f"joint classes merging "
        f"multiple C->T classes: "
        f"{len(ct_merges)}"
    )

    if tc_merges:
        print()
        print(
            "T->C merge sizes:"
        )

        for size in sorted(
            {
                len(values)
                for values
                in tc_merges.values()
            }
        ):
            count = sum(
                1
                for values
                in tc_merges.values()
                if len(values) == size
            )

            print(
                f"    {size}: "
                f"{count}"
            )

    if ct_merges:
        print()
        print(
            "C->T merge sizes:"
        )

        for size in sorted(
            {
                len(values)
                for values
                in ct_merges.values()
            }
        ):
            count = sum(
                1
                for values
                in ct_merges.values()
                if len(values) == size
            )

            print(
                f"    {size}: "
                f"{count}"
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

    if first_failure is not None:
        print(
            "FIRST FAILURE:"
        )

        print(
            first_failure
        )

        raise SystemExit(1)

    if tc_splits or ct_splits:
        print(
            "JOINT NORMALIZER SPLITS "
            "AN OLD QUOTIENT"
        )

        raise SystemExit(2)

    print(
        "joint cycles: 0"
    )

    print(
        "joint idempotence failures: 0"
    )

    print(
        "source/joint semantic mismatches: 0"
    )

    print(
        "old quotient splits: 0"
    )

    print()
    print(
        "JOINT CORE/TEMPORAL "
        "NORMALIZATION CHECKPOINT: PASS"
    )

    print()
    print(
        "Interpretation:"
    )

    print(
        "- temporal orientation owns "
        "SHIFT/EMIT"
    )

    print(
        "- guarded overwrite closes "
        "the discovered partition anomaly"
    )

    print(
        "- joint quotient may be a strict "
        "coarsening of both old quotients"
    )

    print(
        "- class count 605 remains a "
        "measured hypothesis until observed"
    )


if __name__ == "__main__":
    main()
