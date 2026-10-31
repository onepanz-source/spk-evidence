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


RULE_ID = "D-ACC-01"
HELPER = "_normalize_positive_acc_before_cmp1_zero_reset"


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
    Finite independent regression for the local D-ACC-01 premise.

    Local proof obligation:

        Def(source)
            =>
        Def(target)
        and
        Obs(source) == Obs(target)

    Pattern:

        ACC(w,c); CMP(1); ...; RESET(0)

    with w > 1, rewritten to weight 1.

    Algebraically, for unsigned raw x, count n >= 0 and scale s > 0:

        target_raw = x + n*s
        source_raw = x + w*n*s

    therefore:

        target_raw <= source_raw.

    Hence source-definedness implies target-definedness at the rewritten
    ACC.  Subsequent same-path nonnegative ACC operations preserve that
    order, SHIFT is monotone, EMIT does not change raw state, and the
    guarded RESET(0) annihilates the true-branch state difference.

    The finite census below is not the proof.  It is an independent
    executable regression of the theorem over the declared corpus.
    """

    rewrite = find_rewrite()

    with unchecked_domain_rules():
        stats = check_rule(
            rewrite
        )

    print(
        "SPK DOMAIN D-ACC-01 SOURCE-DEFINED PREMISE v0"
    )
    print()

    print(
        "rule:",
        RULE_ID,
    )

    print(
        "helper:",
        HELPER,
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

    partition = (
        stats.both_defined
        + stats.source_defined_target_overflow
        + stats.source_overflow_target_defined
        + stats.both_overflow
    )

    if stats.changed_programs == 0:
        raise AssertionError(
            "D-ACC-01 was not activated"
        )

    if stats.cases == 0:
        raise AssertionError(
            "D-ACC-01 exercised zero concrete cases"
        )

    if partition != stats.cases:
        raise AssertionError(
            "D-ACC-01 definedness partition failure"
        )

    #
    # Executable consequence of:
    #
    #     Def(source) => Def(target)
    #
    if (
        stats.source_defined_target_overflow
        != 0
    ):
        raise AssertionError(
            "D-ACC-01 source-definedness premise refuted: "
            f"DO={stats.source_defined_target_overflow} "
            f"first={stats.first_do}"
        )

    if stats.observation_mismatches != 0:
        raise AssertionError(
            "D-ACC-01 observation preservation refuted: "
            f"mismatches={stats.observation_mismatches} "
            f"first={stats.first_dd_mismatch}"
        )

    #
    # We deliberately require an OD witness in the finite corpus.
    #
    # This is not part of the theorem; it demonstrates that the
    # rewrite genuinely changes the overflow-definedness domain and
    # therefore must not silently become a RUNTIME law.
    #
    if (
        stats.source_overflow_target_defined
        == 0
    ):
        raise AssertionError(
            "D-ACC-01 DOMAIN character was not exercised: "
            "expected at least one OD witness"
        )

    print()
    print(
        "local premise:"
    )
    print(
        "  Def(source) => Def(target)"
    )

    print(
        "local observation law:"
    )
    print(
        "  Def(source) => Obs(source) == Obs(target)"
    )

    print()
    print(
        "D-ACC-01 SOURCE-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
