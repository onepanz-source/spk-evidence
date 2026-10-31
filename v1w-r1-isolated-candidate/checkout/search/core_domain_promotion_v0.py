from __future__ import annotations

from spk_core.rules import unchecked_domain_rules

from dataclasses import dataclass

from spk.event import SpikeTrain

from search.core_rule_soundness_v0 import (
    CONFIG,
    REWRITES,
    observe,
    programs_for_rewrite,
)


CANDIDATES = frozenset(
    (
        "_cap_shift_before_zero_reset_from_compare_bound",
        "_pull_saturated_acc_across_compare",
        "_normalize_temporal_cmp2_barrier",
        "_normalize_temporal_guarded_reset_commute",
        "_normalize_temporal_shift_width",
    )
)


def train_from_batches(
    batches,
):
    pairs = []

    for timestamp, channels in batches:
        for channel in channels:
            pairs.append(
                (
                    timestamp,
                    channel,
                )
            )

    return SpikeTrain.from_pairs(
        pairs
    )


def stress_trains():
    by_pairs = {}

    def add(train):
        key = tuple(
            train.as_pairs()
        )
        by_pairs[key] = train

    #
    # Single batches:
    # stress count/multiplicity and several first deltas.
    #
    patterns = (
        (0,),
        (0, 0),
        (0, 0, 0),
        (0, 0, 0, 0),
        (1,),
        (0, 1),
        (0, 0, 1),
        (0, 1, 2),
    )

    for timestamp in (
        0,
        1,
        2,
        4,
        8,
    ):
        for channels in patterns:
            add(
                train_from_batches(
                    (
                        (
                            timestamp,
                            channels,
                        ),
                    )
                )
            )

    #
    # Two batches:
    # stress temporal distance as well as count.
    #
    batch_patterns = (
        (0,),
        (0, 0),
        (0, 1),
    )

    for start in (
        0,
        1,
    ):
        for gap in (
            1,
            2,
            4,
            8,
        ):
            for left in batch_patterns:
                for right in batch_patterns:
                    add(
                        train_from_batches(
                            (
                                (
                                    start,
                                    left,
                                ),
                                (
                                    start + gap,
                                    right,
                                ),
                            )
                        )
                    )

    return tuple(
        by_pairs.values()
    )


@dataclass
class Stats:
    changed: int = 0
    cases: int = 0

    dd: int = 0
    do: int = 0
    od: int = 0
    oo: int = 0

    observation_mismatches: int = 0

    first_failure: object | None = None


def execute(
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


def check(
    rewrite,
    trains,
):
    stats = Stats()

    for source in programs_for_rewrite(
        rewrite
    ):
        target = rewrite.apply(
            source
        )

        if target == source:
            continue

        stats.changed += 1

        for initial_raw in range(
            CONFIG.max_raw + 1
        ):
            for train in trains:
                stats.cases += 1

                (
                    source_defined,
                    source_obs,
                ) = execute(
                    source,
                    train,
                    initial_raw,
                )

                (
                    target_defined,
                    target_obs,
                ) = execute(
                    target,
                    train,
                    initial_raw,
                )

                if (
                    source_defined
                    and target_defined
                ):
                    stats.dd += 1

                    if source_obs != target_obs:
                        stats.observation_mismatches += 1

                        if stats.first_failure is None:
                            stats.first_failure = (
                                "DD OBSERVATION",
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
                    stats.do += 1

                    if stats.first_failure is None:
                        stats.first_failure = (
                            "DO",
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
                    stats.od += 1

                    if stats.first_failure is None:
                        stats.first_failure = (
                            "OD",
                            source,
                            target,
                            initial_raw,
                            tuple(
                                train.as_pairs()
                            ),
                        )

                    continue

                stats.oo += 1

    return stats


@unchecked_domain_rules()
def main():
    print(
        "SPK CORE DOMAIN PROMOTION SEARCH v0"
    )

    trains = stress_trains()

    print(
        "initial raws:",
        CONFIG.max_raw + 1,
    )

    print(
        "stress trains:",
        len(trains),
    )

    candidates = [
        rewrite
        for rewrite in REWRITES
        if rewrite.name in CANDIDATES
    ]

    if len(candidates) != len(CANDIDATES):
        found = {
            rewrite.name
            for rewrite in candidates
        }

        raise AssertionError(
            "missing candidates: "
            f"{sorted(CANDIDATES - found)}"
        )

    supported = []
    refuted = []
    untested = []

    for rewrite in candidates:
        stats = check(
            rewrite,
            trains,
        )

        exercised = (
            stats.changed > 0
            and stats.cases > 0
        )

        exact = (
            exercised
            and stats.do == 0
            and stats.od == 0
            and stats.observation_mismatches == 0
        )

        print()
        print(
            rewrite.name,
            rewrite.rule_ids,
        )

        print(
            "  changed:",
            stats.changed,
        )

        print(
            "  cases:",
            stats.cases,
        )

        print(
            "  DD:",
            stats.dd,
        )

        print(
            "  DO:",
            stats.do,
        )

        print(
            "  OD:",
            stats.od,
        )

        print(
            "  OO:",
            stats.oo,
        )

        print(
            "  observation mismatches:",
            stats.observation_mismatches,
        )

        if not exercised:
            status = "NOT EXERCISED"
        elif exact:
            status = "FINITE STRESS SUPPORTED"
        else:
            status = "FINITE STRESS REFUTED"

        print(
            "  status:",
            status,
        )

        if not exercised:
            untested.append(
                rewrite.name
            )

        elif exact:
            supported.append(
                rewrite.name
            )

        else:
            refuted.append(
                rewrite.name
            )

            print(
                "  first failure:",
                stats.first_failure,
            )

    print()
    print(
        "=" * 88
    )
    print(
        "SUMMARY"
    )
    print(
        "=" * 88
    )

    print(
        "supported:",
        len(supported),
    )

    for name in supported:
        print(
            "   ",
            name,
        )

    print(
        "refuted:",
        len(refuted),
    )

    for name in refuted:
        print(
            "   ",
            name,
        )

    print(
        "not exercised:",
        len(untested),
    )

    for name in untested:
        print(
            "   ",
            name,
        )

    if untested:
        raise AssertionError(
            "DOMAIN CANDIDATE STRESS VACUOUS CHECK: "
            f"{len(untested)} candidate(s) were not exercised"
        )

    print()
    print(
        "DOMAIN CANDIDATE STRESS SEARCH COMPLETE"
    )


if __name__ == "__main__":
    main()
