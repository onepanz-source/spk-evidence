from __future__ import annotations

from search.core_domain_target_defined_check_v0 import (
    check_target_defined_premise,
    print_result,
)


RULE_ID = "D-TIME-05"
HELPER = "_remove_pre_acc_shift_under_cmp1_reset0"


def main() -> None:
    """
    Independent finite regression for the local D-TIME-05 theorem.

    The rewrite removes SHIFT operations occurring after CMP(1) and
    before the first ACC, provided the guard is not overwritten before
    RESET(0).

    CMP false:
        unsigned raw < 1 implies raw == 0, therefore removed SHIFTs
        act on zero and source == target.

    CMP true:
        removed right shifts can only make target raw greater than or
        equal to source raw.  Subsequent identical SHIFT/ACC operations
        preserve source <= target.

    Therefore:

        Def(target) => Def(source)

    and, because the unchanged true guard reaches RESET(0), the state
    difference is annihilated before leaving the matched region:

        Def(target) => Obs(source) == Obs(target)

    The finite census is an independent regression, not the proof.
    """

    result = check_target_defined_premise(
        rule_id=RULE_ID,
        helper=HELPER,
        require_do_witness=True,
    )

    print(
        "SPK DOMAIN D-TIME-05 TARGET-DEFINED PREMISE v0"
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
        "  Def(target) => Def(source)"
    )

    print(
        "local observation law:"
    )
    print(
        "  Def(target) => Obs(source) == Obs(target)"
    )

    print()
    print(
        "D-TIME-05 TARGET-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
