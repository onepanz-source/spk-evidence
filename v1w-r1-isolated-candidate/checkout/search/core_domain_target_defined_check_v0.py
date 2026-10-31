from __future__ import annotations

from dataclasses import dataclass

from spk_core.rules import (
    unchecked_domain_rules,
)

from search.core_domain_definedness_v0 import (
    check_rule,
)

from search.core_rule_soundness_v0 import (
    REWRITES,
)


@dataclass(
    frozen=True,
    slots=True,
)
class TargetDefinedResult:
    rule_id: str
    helper: str
    changed_programs: int
    cases: int
    dd: int
    do: int
    od: int
    oo: int
    observation_mismatches: int


def find_rewrite(
    rule_id: str,
    helper: str,
):
    matches = tuple(
        rewrite
        for rewrite in REWRITES
        if rewrite.rule_ids == (
            rule_id,
        )
    )

    if len(matches) != 1:
        raise AssertionError(
            f"{rule_id}: expected exactly one rewrite, "
            f"found {len(matches)}"
        )

    rewrite = matches[0]

    if rewrite.name != helper:
        raise AssertionError(
            f"{rule_id}: helper mismatch: "
            f"{rewrite.name} != {helper}"
        )

    return rewrite


def check_target_defined_premise(
    *,
    rule_id: str,
    helper: str,
    require_do_witness: bool = True,
) -> TargetDefinedResult:
    rewrite = find_rewrite(
        rule_id,
        helper,
    )

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
            f"{rule_id}: rewrite was not activated"
        )

    if stats.cases == 0:
        raise AssertionError(
            f"{rule_id}: zero concrete cases"
        )

    if partition != stats.cases:
        raise AssertionError(
            f"{rule_id}: definedness partition failure"
        )

    #
    # Executable consequence of:
    #
    #     Def(target) => Def(source)
    #
    if (
        stats.source_overflow_target_defined
        != 0
    ):
        raise AssertionError(
            f"{rule_id}: Def(target) => Def(source) "
            f"refuted: OD="
            f"{stats.source_overflow_target_defined}, "
            f"first={stats.first_od}"
        )

    if stats.observation_mismatches != 0:
        raise AssertionError(
            f"{rule_id}: observation law refuted: "
            f"mismatches={stats.observation_mismatches}, "
            f"first={stats.first_dd_mismatch}"
        )

    if (
        require_do_witness
        and stats.source_defined_target_overflow == 0
    ):
        raise AssertionError(
            f"{rule_id}: DOMAIN character not exercised; "
            "expected at least one DO witness"
        )

    return TargetDefinedResult(
        rule_id=rule_id,
        helper=helper,
        changed_programs=stats.changed_programs,
        cases=stats.cases,
        dd=stats.both_defined,
        do=stats.source_defined_target_overflow,
        od=stats.source_overflow_target_defined,
        oo=stats.both_overflow,
        observation_mismatches=(
            stats.observation_mismatches
        ),
    )


def print_result(
    result: TargetDefinedResult,
) -> None:
    print(
        "rule:",
        result.rule_id,
    )
    print(
        "helper:",
        result.helper,
    )

    print()
    print(
        "changed programs:",
        result.changed_programs,
    )
    print(
        "cases:",
        result.cases,
    )
    print(
        "DD:",
        result.dd,
    )
    print(
        "DO:",
        result.do,
    )
    print(
        "OD:",
        result.od,
    )
    print(
        "OO:",
        result.oo,
    )
    print(
        "DD observation mismatches:",
        result.observation_mismatches,
    )
