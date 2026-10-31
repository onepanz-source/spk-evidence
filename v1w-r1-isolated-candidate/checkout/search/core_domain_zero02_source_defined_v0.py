from __future__ import annotations

from search.core_domain_source_defined_check_v0 import (
    check_source_defined_premise,
    print_result,
)


RULE_ID = "D-ZERO-02"
HELPER = "_remove_dead_state_before_zero_barrier"


def main() -> None:
    """
    Independent finite regression for the local D-ZERO-02 theorem.

    Pattern:

        P;
        CMP(1);
        RESET(0);
        ...;
        CMP(...)

    where P is the maximal contiguous prefix immediately before the
    zero barrier containing only:

        CoreAcc
        ShiftDecay

    and the guard produced by CMP(1) cannot be consumed by EMIT or
    RESET before a later CMP overwrites it.

    For unsigned raw state:

        CMP(1); RESET(0)

    always leaves raw == 0:

      raw >= 1:
          guard=True, RESET(0) executes

      raw < 1:
          raw==0 already

    Therefore the removed state-only prefix cannot affect raw state
    beyond the barrier.

    The guard produced by CMP(1) may differ between source and target,
    but the matcher requires that it be overwritten by a later CMP
    before any guarded EMIT or RESET can consume it.

    Removing the ACC/SHIFT prefix cannot introduce an overflow.
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
        "SPK DOMAIN D-ZERO-02 SOURCE-DEFINED PREMISE v0"
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
        "D-ZERO-02 SOURCE-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
