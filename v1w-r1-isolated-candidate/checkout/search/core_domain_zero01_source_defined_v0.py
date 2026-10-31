from __future__ import annotations

from search.core_domain_source_defined_check_v0 import (
    check_source_defined_premise,
    print_result,
)


RULE_ID = "D-ZERO-01"
HELPER = "_strip_state_before_lsb_annihilator"


def main() -> None:
    """
    Independent finite regression for the local D-ZERO-01 theorem.

    Pattern:

        X; CMP(1); RESET(0); CMP(1)

    where X is one of:

        CoreAcc
        ShiftDecay
        CoreReset

    The rewrite removes X.

    For unsigned raw state, the suffix

        CMP(1); RESET(0); CMP(1)

    maps every defined incoming state to:

        raw   = 0
        guard = False

    Therefore X cannot affect the observable state beyond the suffix.

    Removing X also cannot introduce an overflow:
    ShiftDecay and removal itself do not overflow, removal of Reset
    removes execution, and removal of Acc can only remove a possible
    overflow.

    Hence locally:

        Def(source)
            =>
        Def(target)

    and:

        Def(source)
            =>
        Obs(source) == Obs(target)

    The finite census is an independent regression, not the proof.
    """

    result = check_source_defined_premise(
        rule_id=RULE_ID,
        helper=HELPER,
        require_od_witness=True,
    )

    print(
        "SPK DOMAIN D-ZERO-01 SOURCE-DEFINED PREMISE v0"
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
        "D-ZERO-01 SOURCE-DEFINED PREMISE CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
