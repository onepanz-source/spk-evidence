from __future__ import annotations

from search.core_domain_premises_v0 import (
    PREMISES,
    PremiseKind,
    PremiseStatus,
)

from search.core_domain_source_defined_check_v0 import (
    check_source_defined_premise,
)


def main() -> None:
    candidates = tuple(
        premise
        for premise in PREMISES
        if premise.kind
        is PremiseKind.SOURCE_DEFINED_CANDIDATE
    )

    if candidates:
        raise AssertionError(
            "unresolved SOURCE_DEFINED candidates: "
            + ", ".join(
                premise.rule_id
                for premise in candidates
            )
        )

    proved = tuple(
        premise
        for premise in PREMISES
        if premise.kind
        is PremiseKind.SOURCE_DEFINED
    )

    if not proved:
        raise AssertionError(
            "SOURCE_DEFINED family is empty"
        )

    for premise in proved:
        if (
            premise.status
            is not PremiseStatus.PROVED_LOCAL
        ):
            raise AssertionError(
                f"{premise.rule_id}: SOURCE_DEFINED "
                f"without PROVED_LOCAL status"
            )

    totals = {
        "changed": 0,
        "cases": 0,
        "dd": 0,
        "do": 0,
        "od": 0,
        "oo": 0,
        "mismatch": 0,
    }

    print(
        "SPK DOMAIN SOURCE-DEFINED FAMILY v0"
    )
    print()

    for premise in proved:
        result = check_source_defined_premise(
            rule_id=premise.rule_id,
            helper=premise.helper,
            require_od_witness=True,
        )

        print(
            f"{result.rule_id:<11} "
            f"changed={result.changed_programs:<4} "
            f"cases={result.cases:<6} "
            f"DD={result.dd:<6} "
            f"DO={result.do:<4} "
            f"OD={result.od:<5} "
            f"OO={result.oo:<5} "
            f"mismatch={result.observation_mismatches}"
        )

        totals[
            "changed"
        ] += result.changed_programs

        totals[
            "cases"
        ] += result.cases

        totals[
            "dd"
        ] += result.dd

        totals[
            "do"
        ] += result.do

        totals[
            "od"
        ] += result.od

        totals[
            "oo"
        ] += result.oo

        totals[
            "mismatch"
        ] += result.observation_mismatches

    partition = (
        totals["dd"]
        + totals["do"]
        + totals["od"]
        + totals["oo"]
    )

    if partition != totals["cases"]:
        raise AssertionError(
            "SOURCE_DEFINED aggregate partition failure"
        )

    if totals["do"] != 0:
        raise AssertionError(
            "SOURCE_DEFINED family contains DO asymmetry"
        )

    if totals["mismatch"] != 0:
        raise AssertionError(
            "SOURCE_DEFINED family observation mismatch"
        )

    if totals["od"] == 0:
        raise AssertionError(
            "SOURCE_DEFINED family DOMAIN character "
            "was not exercised"
        )

    print()
    print(
        "rules:",
        len(proved),
    )
    print(
        "changed programs:",
        totals["changed"],
    )
    print(
        "cases:",
        totals["cases"],
    )
    print(
        "DD:",
        totals["dd"],
    )
    print(
        "DO:",
        totals["do"],
    )
    print(
        "OD:",
        totals["od"],
    )
    print(
        "OO:",
        totals["oo"],
    )
    print(
        "DD observation mismatches:",
        totals["mismatch"],
    )

    print()
    print(
        "SOURCE-DEFINED FAMILY CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
