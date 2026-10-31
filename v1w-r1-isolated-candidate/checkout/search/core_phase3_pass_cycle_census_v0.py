from __future__ import annotations

from collections import Counter
from itertools import product

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import CoreProgram
from spk_core.rules import (
    CanonicalizationProfile,
    canonicalization_profile,
)
from spk_core.semantic_canonicalize import (
    abstract_normalize_program,
    canonicalize_core_program_semantic_runtime,
)

from search.core_rule_soundness_v0 import (
    CONFIG,
    PROGRAM_POOL,
)


MAX_DEPTH = 5
MAX_PASS_STEPS = 64


def programs():
    for depth in range(
        1,
        MAX_DEPTH + 1,
    ):
        for instructions in product(
            PROGRAM_POOL,
            repeat=depth,
        ):
            yield CoreProgram(
                tuple(instructions)
            )


def structural(
    program: CoreProgram,
) -> CoreProgram:
    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return canonicalize_core_program(
            program,
            config=CONFIG,
        )


def semantic(
    program: CoreProgram,
) -> CoreProgram:
    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return abstract_normalize_program(
            CONFIG,
            program,
        )


def official(
    program: CoreProgram,
) -> CoreProgram:
    return (
        canonicalize_core_program_semantic_runtime(
            program,
            config=CONFIG,
        )
    )


def analyze_pass_alternation(
    start: CoreProgram,
):
    program = start
    phase = "S"

    #
    # State includes the next pass to execute.  Otherwise
    #
    #     P --S--> Q --A--> P
    #
    # would be mistaken for an ordinary fixed point.
    #
    seen = {
        (program, phase): 0
    }

    consecutive_noops = 0

    for step in range(
        1,
        MAX_PASS_STEPS + 1,
    ):
        if phase == "S":
            candidate = structural(
                program
            )
            next_phase = "A"
        else:
            candidate = semantic(
                program
            )
            next_phase = "S"

        if candidate == program:
            consecutive_noops += 1
        else:
            consecutive_noops = 0

        program = candidate
        phase = next_phase

        #
        # Both structural and semantic passes have now independently
        # observed a no-op.
        #
        if consecutive_noops >= 2:
            return (
                "converged",
                program,
                step,
                None,
            )

        key = (
            program,
            phase,
        )

        previous = seen.get(
            key
        )

        if previous is not None:
            return (
                "cycle",
                program,
                step,
                step - previous,
            )

        seen[key] = step

    return (
        "limit",
        program,
        MAX_PASS_STEPS,
        None,
    )


def main():
    total = 0

    converged = 0
    cycles = 0
    limits = 0

    official_mismatches = 0

    max_steps = 0

    cycle_lengths = Counter()

    first_cycle = None
    first_limit = None
    first_official_mismatch = None

    for program in programs():
        total += 1

        (
            status,
            result,
            steps,
            cycle_length,
        ) = analyze_pass_alternation(
            program
        )

        max_steps = max(
            max_steps,
            steps,
        )

        expected = official(
            program
        )

        if status == "converged":
            converged += 1

            if result != expected:
                official_mismatches += 1

                if (
                    first_official_mismatch
                    is None
                ):
                    first_official_mismatch = (
                        program,
                        result,
                        expected,
                    )

        elif status == "cycle":
            cycles += 1

            cycle_lengths[
                cycle_length
            ] += 1

            if first_cycle is None:
                first_cycle = (
                    program,
                    result,
                    steps,
                    cycle_length,
                    expected,
                )

        else:
            limits += 1

            if first_limit is None:
                first_limit = (
                    program,
                    result,
                    expected,
                )

    print(
        "SPK PHASE 3B PASS-CYCLE CENSUS v0"
    )
    print()

    print(
        "max depth:",
        MAX_DEPTH,
    )
    print(
        "syntactic programs:",
        total,
    )

    print()

    print(
        "naive alternation converged:",
        converged,
    )
    print(
        "cycles:",
        cycles,
    )
    print(
        "step-limit cases:",
        limits,
    )
    print(
        "max pass steps observed:",
        max_steps,
    )

    print(
        "cycle lengths:",
        dict(
            sorted(
                cycle_lengths.items()
            )
        ),
    )

    print()

    print(
        "converged/official mismatches:",
        official_mismatches,
    )

    if first_cycle is not None:
        print()
        print(
            "FIRST CYCLE:"
        )

        (
            source,
            repeated,
            steps,
            length,
            expected,
        ) = first_cycle

        print(
            "  source:",
            source,
        )
        print(
            "  repeated state:",
            repeated,
        )
        print(
            "  detected at pass step:",
            steps,
        )
        print(
            "  cycle length:",
            length,
        )
        print(
            "  official runtime NF:",
            expected,
        )

    if first_limit is not None:
        print()
        print(
            "FIRST STEP-LIMIT CASE:"
        )
        print(
            first_limit
        )

    if first_official_mismatch is not None:
        print()
        print(
            "FIRST CONVERGED/OFFICIAL MISMATCH:"
        )
        print(
            first_official_mismatch
        )

    if total != 19607:
        raise AssertionError(
            f"unexpected corpus size: "
            f"{total}"
        )

    if limits:
        raise SystemExit(
            "PHASE 3B FAIL: pass-step limit"
        )

    if official_mismatches:
        raise SystemExit(
            "PHASE 3B FAIL: converged alternation "
            "disagrees with official runtime NF"
        )

    #
    # Cycles are deliberately reported, not yet treated as a script
    # failure.  This census determines whether Phase 3 must eliminate
    # residual cross-pass cycles or prove them irrelevant to the
    # official canonicalizer.
    #
    print()

    if cycles:
        print(
            "PHASE 3B CYCLE CENSUS: "
            "RESIDUAL CYCLES FOUND"
        )
    else:
        print(
            "PHASE 3B PASS-CYCLE "
            "CHECKPOINT: PASS"
        )


if __name__ == "__main__":
    main()
