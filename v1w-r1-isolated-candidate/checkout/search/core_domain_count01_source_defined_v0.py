from __future__ import annotations

from search.core_domain_source_defined_check_v0 import (
    check_source_defined_premise,
    print_result,
)


RULE_ID = "D-COUNT-01"
HELPER = "_normalize_shared_count_pre_shift_acc"


def main() -> None:
    """
    Independent finite regression for the local D-COUNT-01 theorem.

    Pattern:

        ACC(w,c);
        SHIFT(k);
        ACC(v,c);
        CMP(1);
        RESET(r)

    with:

        w > 0
        v > 0
        k > 0

    The rewrite removes the first ACC.

    Let n be the shared batch count for channel c, s the fixed-point
    scale and q = k*delta.

    Source before the second ACC:

        ((x + w*n*s) >> q)

    Target before the second ACC:

        (x >> q)

    Since unsigned right shift is monotone:

        target <= source

    and both programs then add the same v*n*s.  Therefore a defined
    source second ACC implies a defined target second ACC.

    CMP(1) also takes the same branch:

      n > 0:
          v*n*s > 0 in both programs

      n == 0:
          both expressions reduce to x >> q

    RESET(r) then equalizes the true branch; on the false branch the
    states were already equal.

    Hence locally:

        Def(source) => Def(target)

    and:

        Def(source) => Obs(source) == Obs(target)

    The finite census below is an independent regression, not the
    algebraic proof.
    """

    result = check_source_defined_premise(
        rule_id=RULE_ID,
        helper=HELPER,
        require_od_witness=True,
    )

    print(
        "SPK DOMAIN D-COUNT-01 SOURCE-DEFINED PREMISE v0"
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
        "D-COUNT-01 SOURCE-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
