from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from spk.event import SpikeTrain
from spk.operators import delay, merge


@dataclass(frozen=True, slots=True)
class EventVar:
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(
                "event variable name must be a string"
            )

        if not self.name:
            raise ValueError(
                "event variable name cannot be empty"
            )


@dataclass(frozen=True, slots=True)
class EventEmpty:
    pass


@dataclass(frozen=True, slots=True)
class EventDelay:
    ticks: int
    child: object

    def __post_init__(self) -> None:
        if (
            isinstance(self.ticks, bool)
            or not isinstance(self.ticks, int)
        ):
            raise TypeError(
                "event delay ticks must be an integer"
            )

        if self.ticks < 0:
            raise ValueError(
                "event delay ticks must be >= 0"
            )

        _require_expr(
            self.child
        )


@dataclass(frozen=True, slots=True)
class EventMerge:
    left: object
    right: object

    def __post_init__(self) -> None:
        _require_expr(
            self.left
        )

        _require_expr(
            self.right
        )


EventExpr = (
    EventVar
    | EventEmpty
    | EventDelay
    | EventMerge
)


def _require_expr(
    value: object,
) -> None:
    if not isinstance(
        value,
        (
            EventVar,
            EventEmpty,
            EventDelay,
            EventMerge,
        ),
    ):
        raise TypeError(
            "expected an event expression"
        )


def evaluate_event_expr(
    expr: EventExpr,
    environment: Mapping[str, SpikeTrain],
) -> SpikeTrain:
    if isinstance(
        expr,
        EventEmpty,
    ):
        return SpikeTrain()

    if isinstance(
        expr,
        EventVar,
    ):
        try:
            train = environment[
                expr.name
            ]
        except KeyError as error:
            raise KeyError(
                f"unbound event variable: {expr.name}"
            ) from error

        if not isinstance(
            train,
            SpikeTrain,
        ):
            raise TypeError(
                "event environment values "
                "must be SpikeTrain instances"
            )

        return train

    if isinstance(
        expr,
        EventDelay,
    ):
        return delay(
            evaluate_event_expr(
                expr.child,
                environment,
            ),
            expr.ticks,
        )

    if isinstance(
        expr,
        EventMerge,
    ):
        return merge(
            evaluate_event_expr(
                expr.left,
                environment,
            ),
            evaluate_event_expr(
                expr.right,
                environment,
            ),
        )

    raise TypeError(
        f"unsupported event expression: {expr!r}"
    )


def render_event_expr(
    expr: EventExpr,
) -> str:
    if isinstance(
        expr,
        EventEmpty,
    ):
        return "EMPTY"

    if isinstance(
        expr,
        EventVar,
    ):
        return expr.name

    if isinstance(
        expr,
        EventDelay,
    ):
        return (
            f"D{expr.ticks}("
            f"{render_event_expr(expr.child)}"
            f")"
        )

    if isinstance(
        expr,
        EventMerge,
    ):
        return (
            "("
            f"{render_event_expr(expr.left)}"
            " + "
            f"{render_event_expr(expr.right)}"
            ")"
        )

    raise TypeError(
        f"unsupported event expression: {expr!r}"
    )
