from __future__ import annotations

from collections import defaultdict
from spk_core.canonicalize import (
    canonicalize_core_program_runtime,
)

from search.core_temporal_normalize_v0 import (
    BATCHES,
    CONFIG,
    DELTAS,
    RAWS,
    normalize_temporal,
    observe,
    programs,
)

from search.core_temporal_joint_normalize_v0 import (
    guarded_temporal_overwrite,
)

from search.core_temporal_core_interaction_v0 import (
    program_key,
)


MAX_ROUNDS = 32


#
# These helpers were independently identified by provenance as
# introducing runtime-observable divergence on the declared finite
# corpus when applied without their domain preconditions.
#
def runtime_core_normalize(
    program,
):
    return canonicalize_core_program_runtime(
        program,
        CONFIG,
    )


def joint_step(
    program,
):
    #
    # C_L:
    # Core canonicalization with the currently identified
    # domain-conditioned helpers disabled.
    #
    result = runtime_core_normalize(
        program
    )

    #
    # G:
    # exact guarded temporal overwrite.
    #
    result = guarded_temporal_overwrite(
        result
    )

    #
    # T:
    # temporal orientation owns commuting SHIFT placement.
    #
    result = normalize_temporal(
        result
    )

    return result


def joint_normalize(
    program,
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
        "runtime joint normalization "
        "did not terminate"
    )


def compare(
    left,
    right,
):
    mismatches = 0
    overflow_asymmetries = 0
    successful_mismatches = 0
    first = None

    for raw in RAWS:
        for delta in DELTAS:
            for channels in BATCHES:
                a = observe(
                    left,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                b = observe(
                    right,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                if a == b:
                    continue

                mismatches += 1

                if a.status != b.status:
                    overflow_asymmetries += 1
                    kind = "overflow"
                else:
                    successful_mismatches += 1
                    kind = "successful"

                if first is None:
                    first = (
                        kind,
                        raw,
                        delta,
                        channels,
                        a,
                        b,
                    )

    return {
        "mismatches": mismatches,
        "overflow": overflow_asymmetries,
        "successful": successful_mismatches,
        "first": first,
    }


def main():
    print(
        "SPK RUNTIME CORE + TEMPORAL "
        "JOINT NORMALIZATION v0"
    )

    source_count = 0

    core_forms = {}
    joint_forms = {}

    cycles = 0
    idempotence_failures = 0

    max_rounds = 0

    core_cases = 0
    core_mismatches = 0
    core_overflow = 0
    core_successful = 0

    joint_cases = 0
    joint_mismatches = 0
    joint_overflow = 0
    joint_successful = 0

    first_failure = None

    core_to_joint = defaultdict(
        set
    )

    joint_to_core = defaultdict(
        set
    )

    for source in programs():
        source_count += 1

        core = runtime_core_normalize(
            source
        )

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
                    cycle,
                )

        core_key = program_key(
            core
        )

        joint_key = program_key(
            joint
        )

        core_forms[
            core_key
        ] = core

        joint_forms[
            joint_key
        ] = joint

        core_to_joint[
            core_key
        ].add(
            joint_key
        )

        joint_to_core[
            joint_key
        ].add(
            core_key
        )

        #
        # Runtime Core alone must preserve all declared
        # observations.
        #
        core_result = compare(
            source,
            core,
        )

        core_cases += (
            len(RAWS)
            * len(DELTAS)
            * len(BATCHES)
        )

        core_mismatches += (
            core_result[
                "mismatches"
            ]
        )

        core_overflow += (
            core_result[
                "overflow"
            ]
        )

        core_successful += (
            core_result[
                "successful"
            ]
        )

        if (
            core_result["first"]
            is not None
            and first_failure
            is None
        ):
            first_failure = (
                "runtime-core-semantic",
                source,
                core,
                core_result[
                    "first"
                ],
            )

        #
        # Full joint normal form must also preserve them.
        #
        joint_result = compare(
            source,
            joint,
        )

        joint_cases += (
            len(RAWS)
            * len(DELTAS)
            * len(BATCHES)
        )

        joint_mismatches += (
            joint_result[
                "mismatches"
            ]
        )

        joint_overflow += (
            joint_result[
                "overflow"
            ]
        )

        joint_successful += (
            joint_result[
                "successful"
            ]
        )

        if (
            joint_result["first"]
            is not None
            and first_failure
            is None
        ):
            first_failure = (
                "joint-semantic",
                source,
                joint,
                joint_result[
                    "first"
                ],
            )

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

        if (
            source_count % 1000
            == 0
        ):
            print(
                f"programs="
                f"{source_count:5d} "
                f"core_nf="
                f"{len(core_forms):4d} "
                f"joint_nf="
                f"{len(joint_forms):4d} "
                f"cycles="
                f"{cycles} "
                f"core_mismatch="
                f"{core_mismatches} "
                f"joint_mismatch="
                f"{joint_mismatches}"
            )

    core_splits = {
        key: values
        for key, values
        in core_to_joint.items()
        if len(values) > 1
    }

    joint_merges = {
        key: values
        for key, values
        in joint_to_core.items()
        if len(values) > 1
    }

    print()
    print(
        "=" * 88
    )
    print(
        "RUNTIME CORE NORMAL FORM"
    )
    print(
        "=" * 88
    )

    print(
        f"source programs: "
        f"{source_count}"
    )

    print(
        f"runtime Core classes: "
        f"{len(core_forms)}"
    )

    print(
        f"observation cases: "
        f"{core_cases}"
    )

    print(
        f"observation mismatches: "
        f"{core_mismatches}"
    )

    print(
        f"overflow asymmetries: "
        f"{core_overflow}"
    )

    print(
        f"successful mismatches: "
        f"{core_successful}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "RUNTIME CORE + TEMPORAL "
        "JOINT NORMAL FORM"
    )
    print(
        "=" * 88
    )

    print(
        f"joint classes: "
        f"{len(joint_forms)}"
    )

    print(
        f"additional collapse vs "
        f"runtime Core: "
        f"{len(core_forms) - len(joint_forms)}"
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

    print(
        f"observation cases: "
        f"{joint_cases}"
    )

    print(
        f"observation mismatches: "
        f"{joint_mismatches}"
    )

    print(
        f"overflow asymmetries: "
        f"{joint_overflow}"
    )

    print(
        f"successful mismatches: "
        f"{joint_successful}"
    )

    print()
    print(
        "=" * 88
    )
    print(
        "QUOTIENT RELATION"
    )
    print(
        "=" * 88
    )

    print(
        f"runtime Core classes "
        f"split by joint: "
        f"{len(core_splits)}"
    )

    print(
        f"joint classes merging "
        f"runtime Core classes: "
        f"{len(joint_merges)}"
    )

    if joint_merges:
        print()
        print(
            "merge-size distribution:"
        )

        sizes = defaultdict(int)

        for values in (
            joint_merges.values()
        ):
            sizes[
                len(values)
            ] += 1

        for size, count in sorted(
            sizes.items()
        ):
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

    if core_splits:
        print(
            "JOINT NORMALIZER SPLITS "
            "A RUNTIME CORE CLASS"
        )

        raise SystemExit(2)

    print(
        "runtime Core mismatches: 0"
    )

    print(
        "joint semantic mismatches: 0"
    )

    print(
        "joint cycles: 0"
    )

    print(
        "joint idempotence failures: 0"
    )

    print(
        "runtime Core quotient splits: 0"
    )

    print()
    print(
        "RUNTIME CORE/TEMPORAL "
        "JOINT CHECKPOINT: PASS"
    )

    print()
    print(
        "Core runtime normalization uses "
        "canonicalize_core_program_runtime."
    )

    print(
        "DOMAIN rules are structurally "
        "disabled by the runtime profile."
    )


if __name__ == "__main__":
    main()
