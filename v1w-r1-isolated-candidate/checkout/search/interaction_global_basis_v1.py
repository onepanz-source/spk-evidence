from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from search.equivalence import (
    normalize_signature_x,
)
from search.event_canonicalize import (
    evaluate_event_normal_form,
    event_normal_form,
    render_event_normal_form,
)
from search.event_enumerate import (
    enumerate_event_expressions,
)
from search.event_expr import (
    EventDelay,
    EventMerge,
    EventVar,
)
from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
)
from spk.program import Program
from spk.runner import run_program


ENVIRONMENT = {
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
class Probe:
    name: str
    program: Program
    initial_x: float


#
# Empirical minimum basis found on the <=5-node domain.
#
FINITE_V1_BASIS = (
    Probe(
        name="CH0_CMP1_EMIT_x1",
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
        initial_x=1.0,
    ),
    Probe(
        name="CH1_CMP1_EMIT_x0",
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
        initial_x=0.0,
    ),
    Probe(
        name="CH2_CMP1_EMIT_x0",
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
        initial_x=0.0,
    ),
)


#
# Structurally motivated candidate basis.
#
# Channel 0 carries x0=1, providing a q^T temporal anchor.
#
GLOBAL_CANDIDATE_BASIS = (
    Probe(
        name="DECAY_ACC_CH0_ANCHOR",
        program=Program(
            (
                Decay(
                    tau=1.0,
                ),
                Acc(
                    weight=1.0,
                    channel=0,
                ),
            )
        ),
        initial_x=1.0,
    ),
    Probe(
        name="DECAY_ACC_CH1",
        program=Program(
            (
                Decay(
                    tau=1.0,
                ),
                Acc(
                    weight=1.0,
                    channel=1,
                ),
            )
        ),
        initial_x=0.0,
    ),
    Probe(
        name="DECAY_ACC_CH2",
        program=Program(
            (
                Decay(
                    tau=1.0,
                ),
                Acc(
                    weight=1.0,
                    channel=2,
                ),
            )
        ),
        initial_x=0.0,
    ),
)


def observe(
    form,
    probe: Probe,
):
    train = evaluate_event_normal_form(
        form,
        ENVIRONMENT,
    )

    result = run_program(
        probe.program,
        train,
        initial_x=probe.initial_x,
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


def signature(
    form,
    basis,
):
    return tuple(
        observe(
            form,
            probe,
        )
        for probe in basis
    )


def forms_for_depth(
    max_nodes: int,
):
    expressions = (
        enumerate_event_expressions(
            max_nodes=max_nodes,
        )
    )

    forms = tuple(
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

    return (
        expressions,
        forms,
    )


def analyze_basis(
    forms,
    basis,
):
    clusters = defaultdict(
        list
    )

    for form in forms:
        clusters[
            signature(
                form,
                basis,
            )
        ].append(
            form
        )

    ambiguous = [
        members
        for members
        in clusters.values()
        if len(members) > 1
    ]

    return (
        clusters,
        ambiguous,
    )


def print_analysis(
    *,
    name,
    forms,
    basis,
):
    clusters, ambiguous = (
        analyze_basis(
            forms,
            basis,
        )
    )

    excess = sum(
        len(members) - 1
        for members in ambiguous
    )

    print(
        f"{name}:"
    )

    print(
        f"  classes: "
        f"{len(clusters)}"
    )

    print(
        f"  ambiguous classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"  excess forms: "
        f"{excess}"
    )

    if ambiguous:
        print(
            "  first ambiguous class:"
        )

        for form in ambiguous[0][
            :10
        ]:
            print(
                "    "
                + render_event_normal_form(
                    form
                )
            )

    print()


def explicit_counterexample():
    A = EventVar("A")
    B = EventVar("B")

    left = event_normal_form(
        EventMerge(
            B,
            EventMerge(
                EventDelay(
                    1,
                    A,
                ),
                EventDelay(
                    2,
                    B,
                ),
            ),
        )
    )

    right = event_normal_form(
        EventMerge(
            B,
            EventMerge(
                EventDelay(
                    1,
                    B,
                ),
                EventDelay(
                    2,
                    A,
                ),
            ),
        )
    )

    print(
        "EXPLICIT DEPTH-7 COUNTEREXAMPLE"
    )

    print(
        "  left: ",
        render_event_normal_form(
            left
        ),
    )

    print(
        "  right:",
        render_event_normal_form(
            right
        ),
    )

    finite_left = signature(
        left,
        FINITE_V1_BASIS,
    )

    finite_right = signature(
        right,
        FINITE_V1_BASIS,
    )

    global_left = signature(
        left,
        GLOBAL_CANDIDATE_BASIS,
    )

    global_right = signature(
        right,
        GLOBAL_CANDIDATE_BASIS,
    )

    print(
        "  finite basis equal:",
        finite_left == finite_right,
    )

    print(
        "  global candidate equal:",
        global_left == global_right,
    )

    print()


def main() -> None:
    explicit_counterexample()

    for max_nodes in (
        5,
        6,
        7,
    ):
        expressions, forms = (
            forms_for_depth(
                max_nodes
            )
        )

        print(
            "=" * 64
        )

        print(
            f"MAX NODES {max_nodes}"
        )

        print(
            f"syntactic expressions: "
            f"{len(expressions)}"
        )

        print(
            f"normal forms: "
            f"{len(forms)}"
        )

        print()

        print_analysis(
            name="FINITE_V1_BASIS",
            forms=forms,
            basis=FINITE_V1_BASIS,
        )

        print_analysis(
            name="GLOBAL_CANDIDATE_BASIS",
            forms=forms,
            basis=GLOBAL_CANDIDATE_BASIS,
        )


if __name__ == "__main__":
    main()
