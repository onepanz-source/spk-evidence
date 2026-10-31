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
    InteractionProbe,
    canonical_event_forms,
)
from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Emit,
)
from spk.program import Program
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


EXTRA_PROBES = (
    InteractionProbe(
        name="ACC_CH2",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=2,
                ),
            )
        ),
        description=(
            "Multiplicity restricted to channel 2."
        ),
    ),

    InteractionProbe(
        name="CH1_CMP1_EMIT",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=1,
                ),
                Compare(
                    threshold=1.0,
                ),
                Emit(
                    channel_out=0,
                ),
            )
        ),
        description=(
            "Channel-1-sensitive temporal observation."
        ),
    ),

    InteractionProbe(
        name="CH2_CMP1_EMIT",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=2,
                ),
                Compare(
                    threshold=1.0,
                ),
                Emit(
                    channel_out=0,
                ),
            )
        ),
        description=(
            "Channel-2-sensitive temporal observation."
        ),
    ),
)


PROBES_V3 = (
    PROBES
    + EXTRA_PROBES
)


@dataclass(
    frozen=True,
    slots=True,
)
class ObservationTest:
    probe_index: int
    probe_name: str
    initial_x: float


def observation(
    train: SpikeTrain,
    test: ObservationTest,
):
    probe = PROBES_V3[
        test.probe_index
    ]

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


def test_key(
    test: ObservationTest,
):
    return (
        test.probe_name,
        test.initial_x,
    )


def class_count(
    observation_matrix,
    selected_tests,
    form_count: int,
) -> int:
    return len(
        {
            tuple(
                observation_matrix[
                    test_index
                ][form_index]
                for test_index
                in selected_tests
            )
            for form_index
            in range(form_count)
        }
    )


def build_pair_mask(
    observations,
    pairs,
) -> int:
    mask = 0

    for bit, (
        left,
        right,
    ) in enumerate(pairs):
        if (
            observations[left]
            != observations[right]
        ):
            mask |= (
                1 << bit
            )

    return mask


def main() -> None:
    forms = canonical_event_forms()

    trains = tuple(
        evaluate_event_normal_form(
            form,
            CANONICAL_ENVIRONMENT,
        )
        for form in forms
    )

    tests = tuple(
        ObservationTest(
            probe_index=probe_index,
            probe_name=probe.name,
            initial_x=initial_x,
        )
        for probe_index, probe
        in enumerate(PROBES_V3)
        for initial_x
        in INITIAL_STATES
    )

    pairs = tuple(
        combinations(
            range(len(forms)),
            2,
        )
    )

    full_mask = (
        (1 << len(pairs))
        - 1
    )

    print(
        f"event normal forms: "
        f"{len(forms)}"
    )

    print(
        f"probes: "
        f"{len(PROBES_V3)}"
    )

    print(
        f"candidate observation tests: "
        f"{len(tests)}"
    )

    print(
        f"form pairs to separate: "
        f"{len(pairs)}"
    )

    print()

    #
    # Precompute every observation.
    #
    observation_matrix = []

    for test in tests:
        observation_matrix.append(
            tuple(
                observation(
                    train,
                    test,
                )
                for train in trains
            )
        )

    #
    # Convert each test into a bit mask over the 9730 unordered
    # pairs of event forms.
    #
    masks = tuple(
        build_pair_mask(
            observations,
            pairs,
        )
        for observations
        in observation_matrix
    )

    print(
        "BEST SINGLE OBSERVATIONS"
    )

    ranking = []

    for index, test in enumerate(
        tests
    ):
        classes = class_count(
            observation_matrix,
            (index,),
            len(forms),
        )

        separated = (
            masks[index].bit_count()
        )

        ranking.append(
            (
                classes,
                separated,
                index,
                test,
            )
        )

    ranking.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            test_key(
                item[3]
            ),
        )
    )

    for (
        classes,
        separated,
        _,
        test,
    ) in ranking[:25]:
        print(
            f"  {test.probe_name:20s} "
            f"x0={test.initial_x:5.1f} "
            f"classes={classes:3d} "
            f"pairs={separated:5d}"
        )

    #
    # Greedy basis first. This gives us an upper bound on the
    # minimum basis size.
    #
    remaining_mask = full_mask

    selected_greedy = []

    available = set(
        range(len(tests))
    )

    while remaining_mask:
        best_index = None
        best_gain = 0

        for index in available:
            gain = (
                masks[index]
                & remaining_mask
            ).bit_count()

            if gain > best_gain:
                best_gain = gain
                best_index = index

        if (
            best_index is None
            or best_gain == 0
        ):
            break

        selected_greedy.append(
            best_index
        )

        remaining_mask &= ~masks[
            best_index
        ]

        available.remove(
            best_index
        )

        print()
        print(
            f"GREEDY STEP "
            f"{len(selected_greedy)}"
        )

        print(
            f"  test: "
            f"{tests[best_index].probe_name}, "
            f"x0="
            f"{tests[best_index].initial_x}"
        )

        print(
            f"  newly separated pairs: "
            f"{best_gain}"
        )

        print(
            f"  remaining pairs: "
            f"{remaining_mask.bit_count()}"
        )

        print(
            f"  resulting classes: "
            f"{class_count(
                observation_matrix,
                selected_greedy,
                len(forms),
            )}"
        )

    print()
    print(
        "GREEDY BASIS"
    )

    for position, index in enumerate(
        selected_greedy,
        start=1,
    ):
        test = tests[index]

        print(
            f"  {position}. "
            f"{test.probe_name}, "
            f"x0={test.initial_x}"
        )

    print(
        f"greedy size: "
        f"{len(selected_greedy)}"
    )

    print(
        f"greedy unseparated pairs: "
        f"{remaining_mask.bit_count()}"
    )

    #
    # Deduplicate tests with identical separation masks.
    #
    mask_representatives = {}

    for index, mask in enumerate(
        masks
    ):
        if mask == 0:
            continue

        current = (
            mask_representatives.get(
                mask
            )
        )

        if (
            current is None
            or test_key(
                tests[index]
            )
            < test_key(
                tests[current]
            )
        ):
            mask_representatives[
                mask
            ] = index

    candidates = tuple(
        sorted(
            mask_representatives.values(),
            key=lambda index: (
                -masks[index].bit_count(),
                test_key(
                    tests[index]
                ),
            ),
        )
    )

    #
    # Remove tests whose separated-pair set is a strict subset of
    # another candidate's set. With uniform test cost they can never
    # be needed in a minimum-cardinality separating basis.
    #
    nondominated = []

    for index in candidates:
        mask = masks[index]

        dominated = False

        for other in candidates:
            if other == index:
                continue

            other_mask = masks[
                other
            ]

            if (
                mask != other_mask
                and (
                    mask
                    | other_mask
                ) == other_mask
            ):
                dominated = True
                break

        if not dominated:
            nondominated.append(
                index
            )

    candidates = tuple(
        nondominated
    )

    print()
    print(
        f"unique nondominated tests: "
        f"{len(candidates)}"
    )

    #
    # Exact minimum-cardinality search.
    #
    exact_basis = None

    max_size = (
        len(selected_greedy)
        if not remaining_mask
        else min(
            6,
            len(candidates),
        )
    )

    for size in range(
        1,
        max_size + 1,
    ):
        print(
            f"exact search: size={size}"
        )

        for combination in combinations(
            candidates,
            size,
        ):
            combined = 0

            for index in combination:
                combined |= masks[
                    index
                ]

            if combined == full_mask:
                exact_basis = (
                    combination
                )
                break

        if exact_basis is not None:
            break

    print()
    print(
        "EXACT MINIMUM BASIS"
    )

    if exact_basis is None:
        print(
            "  not found within search bound"
        )
    else:
        for position, index in enumerate(
            exact_basis,
            start=1,
        ):
            test = tests[index]

            print(
                f"  {position}. "
                f"{test.probe_name}, "
                f"x0={test.initial_x}"
            )

        print(
            f"minimum basis size: "
            f"{len(exact_basis)}"
        )

        print(
            f"classes induced: "
            f"{class_count(
                observation_matrix,
                exact_basis,
                len(forms),
            )}"
        )

    #
    # If even the full candidate family is not separating,
    # show the surviving pairs.
    #
    combined_all = 0

    for mask in masks:
        combined_all |= mask

    unresolved_mask = (
        full_mask
        & ~combined_all
    )

    print()
    print(
        f"all-probe unseparated pairs: "
        f"{unresolved_mask.bit_count()}"
    )

    if unresolved_mask:
        print()
        print(
            "UNRESOLVED PAIRS"
        )

        shown = 0

        for bit, (
            left,
            right,
        ) in enumerate(
            pairs
        ):
            if not (
                unresolved_mask
                & (1 << bit)
            ):
                continue

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

            shown += 1

            if shown >= 20:
                break


if __name__ == "__main__":
    main()
