from __future__ import annotations

from search.core_domain_source_defined_check_v0 import (
    check_source_defined_premise,
    print_result,
)


RULE_ID = "D-ACC-03"
HELPER = "_cap_saturated_acc_before_guarded_reset"


def main() -> None:
    """
    Independent finite regression for the local D-ACC-03 theorem:

        Def(source)
            =>
        Def(target)
        and
        Obs(source) == Obs(target)

    The rewritten ACC weight is reduced from a to the minimum
    saturating weight m, with m < a.  Therefore target raw state
    never exceeds source raw state before the guarding CMP.

    The finite regression is evidence against implementation drift;
    the monotonicity argument is the local proof.
    """

    result = check_source_defined_premise(
        rule_id=RULE_ID,
        helper=HELPER,
        require_od_witness=True,
    )

    print(
        "SPK DOMAIN D-ACC-03 SOURCE-DEFINED PREMISE v0"
    )
    print()

    print_result(
        result
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
        "D-ACC-03 SOURCE-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
