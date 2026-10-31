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

from search.core_temporal_joint_normalize_v0 import (
    guarded_temporal_overwrite,
)


def compare(
    left,
    right,
):
    mismatches = 0
    overflow_asymmetry = 0
    successful_mismatch = 0
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
                    overflow_asymmetry += 1
                    kind = "overflow"
                else:
                    successful_mismatch += 1
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
        "overflow": overflow_asymmetry,
        "successful": successful_mismatch,
        "first": first,
    }


def main():
    print(
        "SPK CORE / TEMPORAL "
        "JOINT ATTRIBUTION v0"
    )

    totals = {
        "P->C": Counter(),
        "C->G": Counter(),
        "G->T": Counter(),
        "P->J": Counter(),
    }

    first_failures = {}

    affected_programs = Counter()

    source_count = 0

    for source in programs():
        source_count += 1

        core = (
            canonicalize_core_program(
                source
            )
        )

        guarded = (
            guarded_temporal_overwrite(
                core
            )
        )

        temporal = (
            normalize_temporal(
                guarded
            )
        )

        stages = (
            (
                "P->C",
                source,
                core,
            ),
            (
                "C->G",
                core,
                guarded,
            ),
            (
                "G->T",
                guarded,
                temporal,
            ),
            (
                "P->J",
                source,
                temporal,
            ),
        )

        source_affected = False

        for name, left, right in stages:
            result = compare(
                left,
                right,
            )

            totals[name][
                "mismatches"
            ] += result[
                "mismatches"
            ]

            totals[name][
                "overflow"
            ] += result[
                "overflow"
            ]

            totals[name][
                "successful"
            ] += result[
                "successful"
            ]

            if (
                result["mismatches"]
                and name
                not in first_failures
            ):
                first_failures[
                    name
                ] = (
                    source,
                    left,
                    right,
                    result["first"],
                )

            if (
                name == "P->C"
                and result["mismatches"]
            ):
                source_affected = True

        if source_affected:
            affected_programs[
                repr(
                    source.instructions
                )
            ] += 1

    print()
    print(
        "=" * 88
    )
    print(
        "STAGE ATTRIBUTION"
    )
    print(
        "=" * 88
    )

    print(
        f"source programs: "
        f"{source_count}"
    )

    for name in (
        "P->C",
        "C->G",
        "G->T",
        "P->J",
    ):
        data = totals[
            name
        ]

        print()
        print(name)

        print(
            f"    mismatches: "
            f"{data['mismatches']}"
        )

        print(
            f"    overflow asymmetries: "
            f"{data['overflow']}"
        )

        print(
            f"    successful mismatches: "
            f"{data['successful']}"
        )

        if name in first_failures:
            (
                source,
                left,
                right,
                witness,
            ) = first_failures[
                name
            ]

            print(
                "    first failure:"
            )

            print(
                f"        source="
                f"{source.instructions}"
            )

            print(
                f"        left="
                f"{left.instructions}"
            )

            print(
                f"        right="
                f"{right.instructions}"
            )

            print(
                f"        witness="
                f"{witness}"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "CORE-STAGE AFFECTED PROGRAMS"
    )
    print(
        "=" * 88
    )

    print(
        f"programs affected: "
        f"{len(affected_programs)}"
    )

    for index, program in enumerate(
        affected_programs,
        start=1,
    ):
        if index > 20:
            print(
                f"... "
                f"{len(affected_programs)-20} "
                f"more"
            )
            break

        print(
            f"    {program}"
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

    core_bad = (
        totals["P->C"][
            "mismatches"
        ]
        > 0
    )

    guarded_clean = (
        totals["C->G"][
            "mismatches"
        ]
        == 0
    )

    temporal_clean = (
        totals["G->T"][
            "mismatches"
        ]
        == 0
    )

    print(
        f"Core stage introduces "
        f"observational divergence: "
        f"{core_bad}"
    )

    print(
        f"guarded-overwrite stage "
        f"preserves observations: "
        f"{guarded_clean}"
    )

    print(
        f"temporal stage preserves "
        f"observations: "
        f"{temporal_clean}"
    )

    if not (
        core_bad
        and guarded_clean
        and temporal_clean
    ):
        raise SystemExit(1)

    print()
    print(
        "JOINT FAILURE ATTRIBUTED "
        "TO CORE DOMAIN RULES: PASS"
    )


if __name__ == "__main__":
    main()
