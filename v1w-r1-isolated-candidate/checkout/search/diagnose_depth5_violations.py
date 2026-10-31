from __future__ import annotations

import math

from search.corpus_multidecay_v1 import CORPUS_MULTIDECAY_V1
from search.equivalence import (
    observe,
    to_signature_observation,
)
from spk.operators import (
    Acc,
    Compare,
    Decay,
)
from spk.program import Program


PAIRS = (
    (
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=1.0, channel=0),
                Decay(tau=1.0),
                Decay(tau=2.0),
                Compare(threshold=2.0),
            )
        ),
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=1.0, channel=0),
                Decay(tau=2.0 / 3.0),
                Compare(threshold=2.0),
            )
        ),
    ),
    (
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=1.0, channel=0),
                Decay(tau=2.0),
                Decay(tau=1.0),
                Compare(threshold=2.0),
            )
        ),
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=1.0, channel=0),
                Decay(tau=2.0 / 3.0),
                Compare(threshold=2.0),
            )
        ),
    ),
    (
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=2.0, channel=0),
                Decay(tau=1.0),
                Decay(tau=2.0),
                Compare(threshold=2.0),
            )
        ),
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=2.0, channel=0),
                Decay(tau=2.0 / 3.0),
                Compare(threshold=2.0),
            )
        ),
    ),
    (
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=2.0, channel=0),
                Decay(tau=2.0),
                Decay(tau=1.0),
                Compare(threshold=2.0),
            )
        ),
        Program(
            (
                Decay(tau=2.0),
                Acc(weight=2.0, channel=0),
                Decay(tau=2.0 / 3.0),
                Compare(threshold=2.0),
            )
        ),
    ),
    (
        Program(
            (
                Decay(tau=2.0),
                Decay(tau=2.0),
                Decay(tau=2.0),
                Decay(tau=2.0),
                Compare(threshold=2.0),
            )
        ),
        Program(
            (
                Decay(tau=0.5),
                Compare(threshold=2.0),
            )
        ),
    ),
)


def format_program(program: Program) -> str:
    return " -> ".join(
        repr(operator)
        for operator in program.operators
    )


def main() -> None:
    total_differences = 0
    guard_differences = 0
    output_differences = 0

    for pair_index, (left, right) in enumerate(
        PAIRS,
        start=1,
    ):
        print()
        print("=" * 72)
        print(f"PAIR {pair_index}")
        print("left: ", format_program(left))
        print("right:", format_program(right))

        pair_differences = 0

        for sample in CORPUS_MULTIDECAY_V1:
            left_raw = observe(
                left,
                sample,
            )

            right_raw = observe(
                right,
                sample,
            )

            left_sig = to_signature_observation(
                left_raw
            )

            right_sig = to_signature_observation(
                right_raw
            )

            if left_sig == right_sig:
                continue

            pair_differences += 1
            total_differences += 1

            left_x, left_guard = (
                left_raw.final_state
            )

            right_x, right_guard = (
                right_raw.final_state
            )

            guard_diff = (
                left_guard != right_guard
            )

            output_diff = (
                left_raw.output
                != right_raw.output
            )

            guard_differences += int(
                guard_diff
            )

            output_differences += int(
                output_diff
            )

            abs_diff = abs(
                left_x - right_x
            )

            ulp = max(
                math.ulp(left_x),
                math.ulp(right_x),
            )

            ulp_distance = (
                abs_diff / ulp
                if ulp > 0.0
                else 0.0
            )

            print()
            print(
                "initial_x:",
                repr(sample.initial_x),
            )

            print(
                "train:",
                sample.train.as_pairs(),
            )

            print(
                "left raw: ",
                left_raw,
            )

            print(
                "right raw:",
                right_raw,
            )

            print(
                "left normalized: ",
                left_sig,
            )

            print(
                "right normalized:",
                right_sig,
            )

            print(
                "x difference:",
                repr(abs_diff),
            )

            print(
                "approx ULP distance:",
                ulp_distance,
            )

            print(
                "guard differs:",
                guard_diff,
            )

            print(
                "output differs:",
                output_diff,
            )

        print()
        print(
            f"pair differences: "
            f"{pair_differences}"
        )

    print()
    print("=" * 72)
    print("SUMMARY")

    print(
        f"signature differences: "
        f"{total_differences}"
    )

    print(
        f"guard differences: "
        f"{guard_differences}"
    )

    print(
        f"output differences: "
        f"{output_differences}"
    )


if __name__ == "__main__":
    main()
