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
        if rewrite.rule_ids == (RULE_ID,)
    )

    if len(matches) != 1:
        raise AssertionError(
            f"{RULE_ID}: expected one rewrite, found {len(matches)}"
        )

    rewrite = matches[0]

    if rewrite.name != HELPER:
        raise AssertionError(
            f"{RULE_ID}: helper mismatch: {rewrite.name}"
        )

    return rewrite


def main() -> None:
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
        rewrite = find_rewrite()
        target = rewrite.apply(
            source
        )

    if target == source:
        raise AssertionError(
            "D-RESET-01 witness did not activate rewrite"
        )

    source_defined, source_obs = run_observation(
        source,
        train,
        1,
    )

    target_defined, target_obs = run_observation(
        target,
        train,
        1,
    )

    print(
        "SPK DOMAIN D-RESET-01 BIDIRECTIONAL WITNESS v0"
    )
    print()

    print(
        "source:",
        source,
    )
    print(
        "target:",
        target,
    )

    print()
    print(
        "initial_raw:",
        1,
    )
    print(
        "train:",
        tuple(
            train.as_pairs()
        ),
    )

    print()
    print(
        "source defined:",
        source_defined,
    )
    print(
        "target defined:",
        target_defined,
    )

    if source_defined:
        print(
            "source observation:",
            source_obs,
        )

    if target_defined:
        print(
            "target observation:",
            target_obs,
        )

    if source_defined:
        raise AssertionError(
            "expected source overflow"
        )

    if not target_defined:
        raise AssertionError(
            "expected target to be defined"
        )

    print()
    print(
        "witness:"
    )
    print(
        "  Overflow(source) and Def(target)"
    )

    print()
    print(
        "D-RESET-01 BIDIRECTIONAL WITNESS CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
