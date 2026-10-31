from __future__ import annotations

import math

from search.canonicalize import canonicalize
from search.corpus_v2 import CORPUS_V2
from search.enumerate import enumerate_programs
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)
from spk.runner import run_program


OPERATORS = (
    Acc(weight=0.0, channel=0),
    Acc(weight=1.0, channel=0),
    Acc(weight=2.0, channel=0),

    Decay(tau=2.0),

    Compare(threshold=1.0),
    Compare(threshold=2.0),

    Emit(channel_out=0),
    Reset(value=0.0),
)


REL_TOL = 1e-12
ABS_TOL = 1e-12


def main() -> None:
    programs = tuple(
        enumerate_programs(
            OPERATORS,
            min_length=0,
            max_length=4,
        )
    )

    violating_pairs = 0
    differing_samples = 0

    output_mismatches = 0
    guard_mismatches = 0
    x_only_mismatches = 0
    tolerance_failures = 0

    max_abs_diff = 0.0
    max_rel_diff = 0.0
    max_ulp_ratio = 0.0

    serious_examples = []

    for program in programs:
        canonical = canonicalize(program)

        if canonical == program:
            continue

        pair_differs = False

        for sample in CORPUS_V2:
            left = run_program(
                program,
                sample.train,
                initial_x=sample.initial_x,
            )

            right = run_program(
                canonical,
                sample.train,
                initial_x=sample.initial_x,
            )

            left_output = left.output.as_pairs()
            right_output = right.output.as_pairs()

            left_x, left_guard = left.final_state
            right_x, right_guard = right.final_state

            output_diff = (
                left_output != right_output
            )

            guard_diff = (
                left_guard != right_guard
            )

            x_diff = (
                left_x != right_x
            )

            if not (
                output_diff
                or guard_diff
                or x_diff
            ):
                continue

            pair_differs = True
            differing_samples += 1

            if output_diff:
                output_mismatches += 1

            if guard_diff:
                guard_mismatches += 1

            if (
                x_diff
                and not output_diff
                and not guard_diff
            ):
                x_only_mismatches += 1

            abs_diff = abs(
                left_x - right_x
            )

            scale = max(
                abs(left_x),
                abs(right_x),
                1.0,
            )

            rel_diff = (
                abs_diff / scale
            )

            max_abs_diff = max(
                max_abs_diff,
                abs_diff,
            )

            max_rel_diff = max(
                max_rel_diff,
                rel_diff,
            )

            ulp_scale = max(
                math.ulp(left_x),
                math.ulp(right_x),
            )

            if ulp_scale > 0.0:
                max_ulp_ratio = max(
                    max_ulp_ratio,
                    abs_diff / ulp_scale,
                )

            close = math.isclose(
                left_x,
                right_x,
                rel_tol=REL_TOL,
                abs_tol=ABS_TOL,
            )

            serious = (
                output_diff
                or guard_diff
                or not close
            )

            if serious:
                tolerance_failures += 1

                if len(serious_examples) < 10:
                    serious_examples.append(
                        (
                            program,
                            canonical,
                            sample,
                            left,
                            right,
                            abs_diff,
                        )
                    )

        if pair_differs:
            violating_pairs += 1

    print(
        f"syntactic programs: {len(programs)}"
    )

    print(
        f"violating program pairs: "
        f"{violating_pairs}"
    )

    print(
        f"differing samples: "
        f"{differing_samples}"
    )

    print(
        f"output mismatches: "
        f"{output_mismatches}"
    )

    print(
        f"guard mismatches: "
        f"{guard_mismatches}"
    )

    print(
        f"x-only mismatches: "
        f"{x_only_mismatches}"
    )

    print(
        f"failures at tol "
        f"{REL_TOL:g}/{ABS_TOL:g}: "
        f"{tolerance_failures}"
    )

    print(
        f"max abs x difference: "
        f"{max_abs_diff:.17g}"
    )

    print(
        f"max relative x difference: "
        f"{max_rel_diff:.17g}"
    )

    print(
        f"max approximate ULP distance: "
        f"{max_ulp_ratio:.3f}"
    )

    if serious_examples:
        print()
        print("SERIOUS EXAMPLES:")
        print()

        for (
            program,
            canonical,
            sample,
            left,
            right,
            abs_diff,
        ) in serious_examples:
            print(
                "program:  ",
                program,
            )

            print(
                "canonical:",
                canonical,
            )

            print(
                "initial_x:",
                sample.initial_x,
            )

            print(
                "train:",
                sample.train.as_pairs(),
            )

            print(
                "original result:",
                left,
            )

            print(
                "canonical result:",
                right,
            )

            print(
                "abs x difference:",
                repr(abs_diff),
            )

            print()


if __name__ == "__main__":
    main()
