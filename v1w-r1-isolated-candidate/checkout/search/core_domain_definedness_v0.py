from __future__ import annotations

from spk_core.rules import unchecked_domain_rules

from dataclasses import dataclass

from search.core_rule_soundness_v0 import (
    INITIAL_RAWS,
    TRAINS,
    REWRITES,
    observe,
    programs_for_rewrite,
)


@dataclass
class DefinednessStats:
    changed_programs: int = 0
    cases: int = 0

    both_defined: int = 0
    source_defined_target_overflow: int = 0
    source_overflow_target_defined: int = 0
    both_overflow: int = 0

    observation_mismatches: int = 0

    first_dd_mismatch: object | None = None
    first_do: object | None = None
    first_od: object | None = None


def run_observation(
    program,
    train,
    initial_raw,
):
    try:
        return (
            True,
            observe(
                program,
                train,
                initial_raw,
            ),
        )

    except OverflowError:
        return (
            False,
            None,
        )


def check_rule(
    rewrite,
):
    stats = DefinednessStats()

    for source in programs_for_rewrite(
        rewrite
    ):
        target = rewrite.apply(
            source
        )

        if target == source:
            continue

        stats.changed_programs += 1

        for initial_raw in INITIAL_RAWS:
            for train in TRAINS:
                stats.cases += 1

                (
                    source_defined,
                    source_obs,
                ) = run_observation(
                    source,
                    train,
                    initial_raw,
                )

                (
                    target_defined,
                    target_obs,
                ) = run_observation(
                    target,
                    train,
                    initial_raw,
                )

                if (
                    source_defined
                    and target_defined
                ):
                    stats.both_defined += 1

                    if (
                        source_obs
                        != target_obs
                    ):
                        stats.observation_mismatches += 1

                        if (
                            stats.first_dd_mismatch
                            is None
                        ):
                            stats.first_dd_mismatch = (
                                source,
                                target,
                                initial_raw,
                                tuple(
                                    train.as_pairs()
                                ),
                                source_obs,
                                target_obs,
                            )

                    continue

                if (
                    source_defined
                    and not target_defined
                ):
                    stats.source_defined_target_overflow += 1

                    if stats.first_do is None:
                        stats.first_do = (
                            source,
                            target,
                            initial_raw,
                            tuple(
                                train.as_pairs()
                            ),
                        )

                    continue

                if (
                    not source_defined
                    and target_defined
                ):
                    stats.source_overflow_target_defined += 1

                    if stats.first_od is None:
                        stats.first_od = (
                            source,
                            target,
                            initial_raw,
                            tuple(
                                train.as_pairs()
                            ),
                        )

                    continue

                stats.both_overflow += 1

    return stats


@unchecked_domain_rules()
def main():
    print(
        "SPK CORE DOMAIN DEFINEDNESS v0"
    )

    domain_rewrites = (
        rewrite
        for rewrite in REWRITES
        if all(
            rule_id.startswith("D-")
            for rule_id in rewrite.rule_ids
        )
    )

    total = DefinednessStats()

    rows = []

    for rewrite in domain_rewrites:
        stats = check_rule(
            rewrite
        )

        rows.append(
            (
                rewrite,
                stats,
            )
        )

        total.changed_programs += (
            stats.changed_programs
        )

        total.cases += stats.cases

        total.both_defined += (
            stats.both_defined
        )

        total.source_defined_target_overflow += (
            stats.source_defined_target_overflow
        )

        total.source_overflow_target_defined += (
            stats.source_overflow_target_defined
        )

        total.both_overflow += (
            stats.both_overflow
        )

        total.observation_mismatches += (
            stats.observation_mismatches
        )

    print()
    print(
        "=" * 112
    )
    print(
        "PER-RULE DEFINEDNESS"
    )
    print(
        "=" * 112
    )

    print(
        f"{'helper':52} "
        f"{'changed':>7} "
        f"{'cases':>9} "
        f"{'DD':>9} "
        f"{'DO':>7} "
        f"{'OD':>7} "
        f"{'OO':>9} "
        f"{'mismatch':>9}"
    )

    for rewrite, stats in rows:
        print(
            f"{rewrite.name:52} "
            f"{stats.changed_programs:7d} "
            f"{stats.cases:9d} "
            f"{stats.both_defined:9d} "
            f"{stats.source_defined_target_overflow:7d} "
            f"{stats.source_overflow_target_defined:7d} "
            f"{stats.both_overflow:9d} "
            f"{stats.observation_mismatches:9d}"
        )

    print()
    print(
        "=" * 112
    )
    print(
        "TOTAL"
    )
    print(
        "=" * 112
    )

    print(
        "changed programs:",
        total.changed_programs,
    )

    print(
        "cases:",
        total.cases,
    )

    print(
        "DD both defined:",
        total.both_defined,
    )

    print(
        "DO source defined / target overflow:",
        total.source_defined_target_overflow,
    )

    print(
        "OD source overflow / target defined:",
        total.source_overflow_target_defined,
    )

    print(
        "OO both overflow:",
        total.both_overflow,
    )

    print(
        "DD observation mismatches:",
        total.observation_mismatches,
    )

    print()
    print(
        "partition check:",
        (
            total.both_defined
            + total.source_defined_target_overflow
            + total.source_overflow_target_defined
            + total.both_overflow
        ),
        "==",
        total.cases,
    )

    #
    # Existing R0 quantities must be recoverable:
    #
    # source exclusions = OD + OO
    # target escapes    = DO
    #
    print()
    print(
        "R0 reconstructed source exclusions:",
        (
            total.source_overflow_target_defined
            + total.both_overflow
        ),
    )

    print(
        "R0 reconstructed target escapes:",
        total.source_defined_target_overflow,
    )

    print()
    print(
        "=" * 112
    )
    print(
        "FIRST ASYMMETRY WITNESSES"
    )
    print(
        "=" * 112
    )

    for rewrite, stats in rows:
        if (
            stats.first_do is None
            and stats.first_od is None
        ):
            continue

        print()
        print(
            rewrite.name,
            rewrite.rule_ids,
        )

        if stats.first_do is not None:
            print(
                "  DO:",
                stats.first_do,
            )

        if stats.first_od is not None:
            print(
                "  OD:",
                stats.first_od,
            )

    if (
        total.changed_programs == 0
        or total.cases == 0
    ):
        raise AssertionError(
            "DOMAIN DEFINEDNESS VACUOUS CHECK: "
            "no DOMAIN rewrite was exercised"
        )

    if (
        total.observation_mismatches
        != 0
    ):
        raise AssertionError(
            "defined/defined observation "
            "mismatch detected"
        )

    if (
        total.both_defined
        + total.source_defined_target_overflow
        + total.source_overflow_target_defined
        + total.both_overflow
        != total.cases
    ):
        raise AssertionError(
            "definedness partition failure"
        )

    print()
    print(
        "DOMAIN DEFINEDNESS CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
