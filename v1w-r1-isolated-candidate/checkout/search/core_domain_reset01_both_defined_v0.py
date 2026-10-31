from __future__ import annotations

from spk_core import (
    CoreAcc,
    CoreCmp,
    CoreProgram,
    CoreReset,
)

from spk.event import (
    SpikeTrain,
)

from spk_core.rules import (
    unchecked_domain_rules,
)

from search.core_domain_definedness_v0 import (
    check_rule,
    run_observation,
)

from search.core_rule_soundness_v0 import (
    REWRITES,
)


RULE_ID = "D-RESET-01"
HELPER = "_remove_shadowed_resets"


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
    Local D-RESET-01 law:

        RESET(a); X; RESET(b)
            ->
        X; RESET(b)

    provided X contains no CMP.

    Guard false:
        neither reset executes, so both programs execute the same X.

    Guard true:
        X may see different raw state, but any EMIT sees the same guard
        and the final RESET(b) equalizes raw state.

    Therefore, whenever both executions are defined:

        Obs(source) == Obs(target)

    Neither source-definedness nor target-definedness alone is enough.
    The finite census contains DO witnesses and the explicit witness
    below establishes OD.
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
            "D-RESET-01 was not activated"
        )

    if stats.cases == 0:
        raise AssertionError(
            "D-RESET-01 exercised zero cases"
        )

    if partition != stats.cases:
        raise AssertionError(
            "D-RESET-01 definedness partition failure"
        )

    if stats.observation_mismatches != 0:
        raise AssertionError(
            "D-RESET-01 DD observation law refuted: "
            f"mismatches={stats.observation_mismatches} "
            f"first={stats.first_dd_mismatch}"
        )

    #
    # Source-definedness alone must be known insufficient.
    #
    if (
        stats.source_defined_target_overflow
        == 0
    ):
        raise AssertionError(
            "D-RESET-01 expected at least one DO witness"
        )

    #
    # Explicit reverse witness:
    #
    #     CMP(1);
    #     RESET(255);
    #     ACC(1,0);
    #     RESET(0)
    #
    # initial_raw=1 and count(0)=1.
    #
    # Source:
    #     RESET(255); ACC(+1) => overflow.
    #
    # Target:
    #     ACC from raw=1 => defined.
    #
    source = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreReset(
                value_raw=255,
            ),
            CoreAcc(
                weight=1,
                channel=0,
            ),
            CoreReset(
                value_raw=0,
            ),
        )
    )

    train = SpikeTrain.from_pairs(
        (
            (0, 0),
        )
    )

    with unchecked_domain_rules():
        target = rewrite.apply(
            source
        )

    if target == source:
        raise AssertionError(
            "D-RESET-01 OD witness did not activate rewrite"
        )

    (
        source_defined,
        source_obs,
    ) = run_observation(
        source,
        train,
        1,
    )

    (
        target_defined,
        target_obs,
    ) = run_observation(
        target,
        train,
        1,
    )

    if source_defined:
        raise AssertionError(
            "D-RESET-01 OD witness expected source overflow"
        )

    if not target_defined:
        raise AssertionError(
            "D-RESET-01 OD witness expected target defined"
        )

    print(
        "SPK DOMAIN D-RESET-01 BOTH-DEFINED PREMISE v0"
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
        "OD in census:",
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
        "explicit reverse witness:"
    )
    print(
        "  source defined:",
        source_defined,
    )
    print(
        "  target defined:",
        target_defined,
    )

    if source_defined:
        print(
            "  source observation:",
            source_obs,
        )

    if target_defined:
        print(
            "  target observation:",
            target_obs,
        )

    print()
    print(
        "local premise:"
    )
    print(
        "  Def(source) and Def(target)"
    )

    print(
        "local observation law:"
    )
    print(
        "  Def(source) and Def(target)"
        " => Obs(source) == Obs(target)"
    )

    print()
    print(
        "D-RESET-01 BOTH-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
