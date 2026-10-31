from __future__ import annotations

from spk_core.rules import (
    unchecked_domain_rules,
)

from search.core_domain_definedness_v0 import (
    check_rule,
)

from search.core_rule_soundness_v0 import (
    REWRITES,
)


RULE_ID = "D-TIME-01"
HELPER = "_normalize_temporal_shift_width"


def find_rewrite():
    matches = tuple(
        rewrite
        for rewrite in REWRITES
        if rewrite.rule_ids == (
            RULE_ID,
        )
    )

    if len(matches) != 1:
        raise AssertionError(
            f"{RULE_ID}: expected exactly one rewrite, "
            f"found {len(matches)}"
        )

    rewrite = matches[0]

    if rewrite.name != HELPER:
        raise AssertionError(
            f"{RULE_ID}: helper mismatch: "
            f"{rewrite.name}"
        )

    return rewrite


def main() -> None:
    """
    Independent finite regression for the local D-TIME-01 proof.

    Abstract interpretation invariant:

        concrete defined reachable states
            subseteq
        abstract states

    The transfer functions for ACC, SHIFT, CMP, EMIT and RESET are
    conservative, and GuardPartition.merged uses a conservative join.

    Therefore:

        merged.upper <= 1

    soundly implies that every concrete defined raw state at that
    program point lies in {0,1}.

    Likewise:

        false.upper <= 1

    soundly bounds the concrete FALSE branch.

    For raw in {0,1}, every positive-width ShiftDecay has identical
    behavior:

        delta == 0:
            identity

        delta > 0:
            raw becomes zero

    In the partitioned matcher case, the TRUE branch may differ in raw
    after replacing ShiftDecay(k>1) with ShiftDecay(1), but only EMIT
    instructions are permitted before RESET(0).  EMIT observes guard
    only and RESET(0) annihilates the raw-state difference.

    ACC is deliberately forbidden in that interval because it could
    expose the raw difference through observable overflow.

    This finite census is an independent regression of the matcher,
    not the proof of abstract soundness.
    """

    rewrite = find_rewrite()

    with unchecked_domain_rules():
        stats = check_rule(
            rewrite
        )

    partition = (
        stats.both_defined
        + stats.source_defined_target_overflow
        + stats.source_overflow_target_defined
        + stats.both_overflow
    )

    if stats.changed_programs == 0:
        raise AssertionError(
            "D-TIME-01 was not activated"
        )

    if stats.cases == 0:
        raise AssertionError(
            "D-TIME-01 exercised zero concrete cases"
        )

    if partition != stats.cases:
        raise AssertionError(
            "D-TIME-01 definedness partition failure"
        )

    if (
        stats.source_defined_target_overflow
        != 0
        or stats.source_overflow_target_defined
        != 0
    ):
        raise AssertionError(
            "D-TIME-01 finite regression found "
            "definedness asymmetry: "
            f"DO={stats.source_defined_target_overflow} "
            f"OD={stats.source_overflow_target_defined}"
        )

    if stats.observation_mismatches != 0:
        raise AssertionError(
            "D-TIME-01 observation preservation refuted: "
            f"mismatches={stats.observation_mismatches} "
            f"first={stats.first_dd_mismatch}"
        )

    print(
        "SPK DOMAIN D-TIME-01 ABSTRACT-BOUND PREMISE v0"
    )
    print()

    print(
        "changed programs:",
        stats.changed_programs,
    )
    print(
        "cases:",
        stats.cases,
    )
    print(
        "DD:",
        stats.both_defined,
    )
    print(
        "DO:",
        stats.source_defined_target_overflow,
    )
    print(
        "OD:",
        stats.source_overflow_target_defined,
    )
    print(
        "OO:",
        stats.both_overflow,
    )
    print(
        "DD observation mismatches:",
        stats.observation_mismatches,
    )

    print()
    print(
        "abstract premise:"
    )
    print(
        "  reachable defined raw states are contained "
        "in the analyzer RawSet"
    )

    print(
        "matcher consequence:"
    )
    print(
        "  upper <= 1 => concrete raw in {0,1}"
    )

    print()
    print(
        "D-TIME-01 ABSTRACT-BOUND PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
