from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
)

from search.event_canonicalize import (
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
from search.event_expr import (
    evaluate_event_expr,
    render_event_expr,
)


MAX_NODES = 5


def expression_signature(
    expr,
):
    return tuple(
        evaluate_event_expr(
            expr,
            environment,
        ).as_pairs()
        for environment
        in EVENT_CORPUS_V1
    )


def normal_form_signature(
    form,
):
    return tuple(
        evaluate_event_normal_form(
            form,
            environment,
        ).as_pairs()
        for environment
        in EVENT_CORPUS_V1
    )


def main() -> None:
    expressions = (
        enumerate_event_expressions(
            max_nodes=MAX_NODES,
        )
    )

    raw_classes = defaultdict(
        list
    )

    forms = {}

    preservation_violations = []

    node_histogram = Counter()

    for expr in expressions:
        signature = (
            expression_signature(
                expr
            )
        )

        raw_classes[
            signature
        ].append(
            expr
        )

        form = event_normal_form(
            expr
        )

        forms[
            form
        ] = form

        if (
            signature
            != normal_form_signature(
                form
            )
        ):
            preservation_violations.append(
                (
                    expr,
                    form,
                )
            )

        #
        # Recover AST node count only for reporting.
        #
        node_histogram[
            _node_count(expr)
        ] += 1

    canonical_forms = tuple(
        forms
    )

    canonical_classes = defaultdict(
        list
    )

    for form in canonical_forms:
        canonical_classes[
            normal_form_signature(
                form
            )
        ].append(
            form
        )

    ambiguous = [
        members
        for members
        in canonical_classes.values()
        if len(members) > 1
    ]

    excess = sum(
        len(members) - 1
        for members in ambiguous
    )

    print(
        f"corpus environments: "
        f"{len(EVENT_CORPUS_V1)}"
    )

    print(
        f"max AST nodes: "
        f"{MAX_NODES}"
    )

    print(
        f"syntactic expressions: "
        f"{len(expressions)}"
    )

    print(
        "behavioral classes before normalization: "
        f"{len(raw_classes)}"
    )

    print(
        f"canonical normal forms: "
        f"{len(canonical_forms)}"
    )

    print(
        "behavioral classes after normalization: "
        f"{len(canonical_classes)}"
    )

    print(
        "canonical/behavior ratio: "
        f"{len(canonical_forms) / len(canonical_classes):.3f}"
    )

    print(
        "semantic preservation violations: "
        f"{len(preservation_violations)}"
    )

    print(
        "ambiguous canonical classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"residual excess forms: "
        f"{excess}"
    )

    print()
    print(
        "Syntactic node-count distribution:"
    )

    for size in sorted(
        node_histogram
    ):
        print(
            f"  N={size}: "
            f"{node_histogram[size]}"
        )

    if preservation_violations:
        print()
        print(
            "FIRST PRESERVATION VIOLATIONS:"
        )

        for expr, form in (
            preservation_violations[:10]
        ):
            print()
            print(
                "expr: ",
                render_event_expr(
                    expr
                ),
            )
            print(
                "form: ",
                render_event_normal_form(
                    form
                ),
            )

    if ambiguous:
        print()
        print(
            "AMBIGUOUS CANONICAL CLASSES:"
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


def _node_count(
    expr,
) -> int:
    from search.event_expr import (
        EventDelay,
        EventEmpty,
        EventMerge,
        EventVar,
    )

    if isinstance(
        expr,
        (
            EventEmpty,
            EventVar,
        ),
    ):
        return 1

    if isinstance(
        expr,
        EventDelay,
    ):
        return (
            1
            + _node_count(
                expr.child
            )
        )

    if isinstance(
        expr,
        EventMerge,
    ):
        return (
            1
            + _node_count(
                expr.left
            )
            + _node_count(
                expr.right
            )
        )

    raise TypeError(
        expr
    )


if __name__ == "__main__":
    main()
