from __future__ import annotations

from search.event_expr import (
    EventDelay,
    EventEmpty,
    EventExpr,
    EventMerge,
    EventVar,
)


VARIABLES = (
    EventVar("A"),
    EventVar("B"),
    EventVar("C"),
)

EMPTY = EventEmpty()

DELAY_TICKS = (
    0,
    1,
    2,
)


def event_expr_key(
    expr: EventExpr,
) -> str:
    return repr(
        expr
    )


def enumerate_event_expressions(
    *,
    max_nodes: int,
) -> tuple[EventExpr, ...]:
    if (
        isinstance(max_nodes, bool)
        or not isinstance(max_nodes, int)
    ):
        raise TypeError(
            "max_nodes must be an integer"
        )

    if max_nodes < 1:
        raise ValueError(
            "max_nodes must be >= 1"
        )

    by_size: dict[
        int,
        tuple[EventExpr, ...],
    ] = {}

    by_size[1] = tuple(
        sorted(
            (
                EMPTY,
                *VARIABLES,
            ),
            key=event_expr_key,
        )
    )

    for size in range(
        2,
        max_nodes + 1,
    ):
        expressions: set[
            EventExpr
        ] = set()

        #
        # DELAY contributes one AST node.
        #
        for child in by_size[
            size - 1
        ]:
            for ticks in DELAY_TICKS:
                expressions.add(
                    EventDelay(
                        ticks=ticks,
                        child=child,
                    )
                )

        #
        # MERGE contributes one AST node.
        #
        # Keep left/right order syntactically distinct.
        # Commutativity must be discovered by semantics /
        # canonicalization, not baked into enumeration.
        #
        for left_size in range(
            1,
            size - 1,
        ):
            right_size = (
                size
                - 1
                - left_size
            )

            if right_size < 1:
                continue

            for left in by_size[
                left_size
            ]:
                for right in by_size[
                    right_size
                ]:
                    expressions.add(
                        EventMerge(
                            left=left,
                            right=right,
                        )
                    )

        by_size[size] = tuple(
            sorted(
                expressions,
                key=event_expr_key,
            )
        )

    return tuple(
        expr
        for size in range(
            1,
            max_nodes + 1,
        )
        for expr in by_size[size]
    )
