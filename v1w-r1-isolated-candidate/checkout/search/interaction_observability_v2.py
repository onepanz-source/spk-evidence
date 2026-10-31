from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from search.equivalence import (
    normalize_signature_x,
)
from search.event_canonicalize import (
    evaluate_event_normal_form,
    render_event_normal_form,
)
from search.interaction_v1 import (
    INITIAL_STATES,
    PROBES,
    canonical_event_forms,
)
from spk.event import SpikeTrain
from spk.runner import run_program


CANONICAL_ENVIRONMENT = {
    "A": SpikeTrain.from_pairs(
        [(0, 0)]
    ),
    "B": SpikeTrain.from_pairs(
        [(0, 1)]
    ),
    "C": SpikeTrain.from_pairs(
        [(0, 2)]
    ),
}


@dataclass(
    frozen=True,
    slots=True,
)
class ObservationTest:
    probe_name: str
    probe_index: int
    initial_x: float


def observation(
    form,
    test: ObservationTest,
):
    probe = PROBES[
        test.probe_index
    ]

    train = evaluate_event_normal_form(
        form,
        CANONICAL_ENVIRONMENT,
    )

    result = run_program(
        probe.program,
        train,
        initial_x=test.initial_x,
    )

    final_x, final_guard = (
        result.final_state
    )

    return (
        result.output.as_pairs(),
        normalize_signature_x(
            final_x
        ),
        final_guard,
    )


def class_count(
    forms,
    tests,
) -> int:
    signatures = {
        tuple(
            observation(
                form,
                test,
            )
            for test in tests
        )
        for form in forms
    }

    return len(
        signatures
    )


def separated_pairs(
    forms,
    test: ObservationTest,
):
    result = set()

    observations = [
        observation(
            form,
            test,
        )
        for form in forms
    ]

    for left, right in combinations(
        range(len(forms)),
        2,
    ):
        if (
            observations[left]
            != observations[right]
        ):
            result.add(
                (
                    left,
                    right,
                )
            )

    return result


def main() -> None:
    forms = canonical_event_forms()

    tests = tuple(
        ObservationTest(
            probe_name=probe.name,
            probe_index=index,
            initial_x=initial_x,
        )
        for index, probe
        in enumerate(PROBES)
        for initial_x
        in INITIAL_STATES
    )

    all_pairs = set(
        combinations(
            range(len(forms)),
            2,
        )
    )

    print(
        f"event normal forms: "
        f"{len(forms)}"
    )

    print(
        f"candidate observation tests: "
        f"{len(tests)}"
    )

    print(
        f"form pairs to separate: "
        f"{len(all_pairs)}"
    )

    print()
    print(
        "BEST SINGLE OBSERVATIONS"
    )

    ranked = []

    separation_cache = {}

    for test in tests:
        separated = separated_pairs(
            forms,
            test,
        )

        separation_cache[
            test
        ] = separated

        classes = class_count(
            forms,
            (
                test,
            ),
        )

        ranked.append(
            (
                classes,
                len(separated),
                test,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            item[2].probe_name,
            item[2].initial_x,
        )
    )

    for (
        classes,
        pair_count,
        test,
    ) in ranked[:20]:
        print(
            f"  {test.probe_name:20s} "
            f"x0={test.initial_x:5.1f} "
            f"classes={classes:3d} "
            f"pairs={pair_count:5d}"
        )

    #
    # Greedy separating basis.
    #
    remaining = set(
        all_pairs
    )

    selected = []

    available = set(
        tests
    )

    while remaining:
        best_test = None
        best_gain = 0

        for test in available:
            gain = len(
                remaining
                & separation_cache[test]
            )

            if gain > best_gain:
                best_gain = gain
                best_test = test

        if (
            best_test is None
            or best_gain == 0
        ):
            break

        selected.append(
            best_test
        )

        remaining -= (
            separation_cache[
                best_test
            ]
        )

        available.remove(
            best_test
        )

        print()
        print(
            f"GREEDY STEP {len(selected)}"
        )

        print(
            f"  probe: "
            f"{best_test.probe_name}"
        )

        print(
            f"  initial_x: "
            f"{best_test.initial_x}"
        )

        print(
            f"  newly separated pairs: "
            f"{best_gain}"
        )

        print(
            f"  remaining pairs: "
            f"{len(remaining)}"
        )

        print(
            f"  resulting classes: "
            f"{class_count(forms, selected)}"
        )

    print()
    print(
        "FINAL GREEDY BASIS"
    )

    for index, test in enumerate(
        selected,
        start=1,
    ):
        print(
            f"  {index}. "
            f"{test.probe_name}, "
            f"x0={test.initial_x}"
        )

    print()

    print(
        f"basis size: "
        f"{len(selected)}"
    )

    print(
        f"classes induced by basis: "
        f"{class_count(forms, selected)}"
    )

    print(
        f"unseparated pairs: "
        f"{len(remaining)}"
    )

    if remaining:
        print()
        print(
            "FIRST UNSEPARATED PAIRS"
        )

        for left, right in sorted(
            remaining
        )[:20]:
            print()

            print(
                "  left: ",
                render_event_normal_form(
                    forms[left]
                ),
            )

            print(
                "  right:",
                render_event_normal_form(
                    forms[right]
                ),
            )


if __name__ == "__main__":
    main()
