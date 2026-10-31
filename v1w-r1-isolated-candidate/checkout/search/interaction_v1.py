from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from search.equivalence import (
    normalize_signature_x,
)
from search.event_canonicalize import (
    EventNormalForm,
    evaluate_event_normal_form,
    event_normal_form,
    render_event_normal_form,
)
from search.event_corpus_v1 import (
    EVENT_CORPUS_V1,
)
from search.event_enumerate import (
    enumerate_event_expressions,
)
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
)
from spk.program import Program
from spk.runner import run_program


MAX_EVENT_NODES = 5

INITIAL_STATES = (
    -1.0,
    0.0,
    0.5,
    1.0,
    2.0,
)


@dataclass(
    frozen=True,
    slots=True,
)
class InteractionProbe:
    name: str
    program: Program
    description: str


PROBES = (
    InteractionProbe(
        name="ACC_TOTAL",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=None,
                ),
            )
        ),
        description=(
            "Total multiplicity only; "
            "expected to ignore event timing."
        ),
    ),

    InteractionProbe(
        name="ACC_CH0",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
            )
        ),
        description=(
            "Multiplicity restricted to channel 0."
        ),
    ),

    InteractionProbe(
        name="ACC_CH1",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=1,
                ),
            )
        ),
        description=(
            "Multiplicity restricted to channel 1."
        ),
    ),

    InteractionProbe(
        name="DECAY_ONLY",
        program=Program(
            (
                Decay(
                    tau=1.0,
                ),
            )
        ),
        description=(
            "Temporal envelope probe. With nonzero state, "
            "observes elapsed time through decay."
        ),
    ),

    InteractionProbe(
        name="DECAY_THEN_ACC",
        program=Program(
            (
                Decay(
                    tau=1.0,
                ),
                Acc(
                    weight=1.0,
                    channel=None,
                ),
            )
        ),
        description=(
            "Decay before accumulation in every batch."
        ),
    ),

    InteractionProbe(
        name="ACC_THEN_DECAY",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=None,
                ),
                Decay(
                    tau=1.0,
                ),
            )
        ),
        description=(
            "Accumulation before decay in every batch."
        ),
    ),

    InteractionProbe(
        name="ACC_CMP1_EMIT",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=None,
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
            "Makes batch timestamps observable after accumulation."
        ),
    ),

    InteractionProbe(
        name="ACC_CMP2_EMIT",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=None,
                ),
                Compare(
                    threshold=2.0,
                ),
                Emit(
                    channel_out=0,
                ),
            )
        ),
        description=(
            "Observes cumulative multiplicity crossing threshold 2."
        ),
    ),

    InteractionProbe(
        name="CH0_CMP1_EMIT",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
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
            "Channel-sensitive batch observation."
        ),
    ),
)


def canonical_event_forms() -> tuple[
    EventNormalForm,
    ...,
]:
    expressions = (
        enumerate_event_expressions(
            max_nodes=MAX_EVENT_NODES,
        )
    )

    return tuple(
        sorted(
            {
                event_normal_form(
                    expression
                )
                for expression
                in expressions
            },
            key=repr,
        )
    )


def run_signature(
    form: EventNormalForm,
    probe: InteractionProbe,
) -> tuple:
    observations = []

    for environment in EVENT_CORPUS_V1:
        train = (
            evaluate_event_normal_form(
                form,
                environment,
            )
        )

        for initial_x in INITIAL_STATES:
            result = run_program(
                probe.program,
                train,
                initial_x=initial_x,
            )

            final_x, final_guard = (
                result.final_state
            )

            observations.append(
                (
                    result.output.as_pairs(),
                    normalize_signature_x(
                        final_x
                    ),
                    final_guard,
                )
            )

    return tuple(
        observations
    )


def direct_event_signature(
    form: EventNormalForm,
) -> tuple:
    return tuple(
        evaluate_event_normal_form(
            form,
            environment,
        ).as_pairs()
        for environment
        in EVENT_CORPUS_V1
    )


def cluster_forms(
    forms: tuple[
        EventNormalForm,
        ...,
    ],
    signature_function,
):
    clusters = defaultdict(
        list
    )

    for form in forms:
        clusters[
            signature_function(
                form
            )
        ].append(
            form
        )

    return clusters


def summarize_clusters(
    *,
    name: str,
    clusters,
    total_forms: int,
) -> None:
    sizes = sorted(
        (
            len(members)
            for members
            in clusters.values()
        ),
        reverse=True,
    )

    singleton_count = sum(
        size == 1
        for size in sizes
    )

    largest = (
        sizes[0]
        if sizes
        else 0
    )

    print(
        f"{name}:"
    )

    print(
        f"  classes: {len(clusters)}"
    )

    print(
        f"  singleton classes: "
        f"{singleton_count}"
    )

    print(
        f"  largest class: "
        f"{largest}"
    )

    print(
        f"  information ratio: "
        f"{len(clusters) / total_forms:.3f}"
    )


def main() -> None:
    forms = canonical_event_forms()

    print(
        f"event normal forms: "
        f"{len(forms)}"
    )

    print(
        f"event environments: "
        f"{len(EVENT_CORPUS_V1)}"
    )

    print(
        f"initial states: "
        f"{len(INITIAL_STATES)}"
    )

    print(
        f"interaction probes: "
        f"{len(PROBES)}"
    )

    print()

    direct_clusters = (
        cluster_forms(
            forms,
            direct_event_signature,
        )
    )

    summarize_clusters(
        name="DIRECT_EVENT_SEMANTICS",
        clusters=direct_clusters,
        total_forms=len(forms),
    )

    print()

    probe_clusters = {}

    for probe in PROBES:
        clusters = cluster_forms(
            forms,
            lambda form, probe=probe: (
                run_signature(
                    form,
                    probe,
                )
            ),
        )

        probe_clusters[
            probe.name
        ] = clusters

        summarize_clusters(
            name=probe.name,
            clusters=clusters,
            total_forms=len(forms),
        )

        print(
            f"  {probe.description}"
        )

        print()

    #
    # Combined observational signature:
    #
    # two event forms remain equivalent only if EVERY state probe
    # observes them identically.
    #
    combined_clusters = defaultdict(
        list
    )

    for form in forms:
        combined_signature = tuple(
            run_signature(
                form,
                probe,
            )
            for probe in PROBES
        )

        combined_clusters[
            combined_signature
        ].append(
            form
        )

    summarize_clusters(
        name="COMBINED_STATE_OBSERVATION",
        clusters=combined_clusters,
        total_forms=len(forms),
    )

    ambiguous = [
        members
        for members
        in combined_clusters.values()
        if len(members) > 1
    ]

    excess = sum(
        len(members) - 1
        for members
        in ambiguous
    )

    print(
        f"combined ambiguous classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"combined residual excess: "
        f"{excess}"
    )

    if ambiguous:
        print()
        print(
            "LARGEST STATE-INDISTINGUISHABLE "
            "EVENT CLASSES:"
        )

        ambiguous.sort(
            key=lambda members: (
                -len(members),
                repr(members),
            )
        )

        for index, members in enumerate(
            ambiguous[:20],
            start=1,
        ):
            print()

            print(
                f"class {index}: "
                f"{len(members)} forms"
            )

            for form in members:
                print(
                    "  "
                    + render_event_normal_form(
                        form
                    )
                )


if __name__ == "__main__":
    main()
