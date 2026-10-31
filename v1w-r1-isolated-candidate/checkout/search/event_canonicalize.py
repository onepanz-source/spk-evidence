from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from search.event_expr import (
    EventDelay,
    EventEmpty,
    EventExpr,
    EventMerge,
    EventVar,
)
from spk.event import SpikeTrain
from spk.operators import delay, merge


@dataclass(
    frozen=True,
    order=True,
    slots=True,
)
class EventAtom:
    variable: str
    delay_ticks: int


@dataclass(
    frozen=True,
    slots=True,
)
class EventNormalForm:
    atoms: tuple[
        EventAtom,
        ...,
    ]


def event_normal_form(
    expr: EventExpr,
) -> EventNormalForm:
    atoms = _collect_atoms(
        expr,
        accumulated_delay=0,
    )

    return EventNormalForm(
        atoms=tuple(
            sorted(
                atoms
            )
        )
    )


def _collect_atoms(
    expr: EventExpr,
    *,
    accumulated_delay: int,
) -> tuple[EventAtom, ...]:
    if isinstance(
        expr,
        EventEmpty,
    ):
        return ()

    if isinstance(
        expr,
        EventVar,
    ):
        return (
            EventAtom(
                variable=expr.name,
                delay_ticks=(
                    accumulated_delay
                ),
            ),
        )

    if isinstance(
        expr,
        EventDelay,
    ):
        return _collect_atoms(
            expr.child,
            accumulated_delay=(
                accumulated_delay
                + expr.ticks
            ),
        )

    if isinstance(
        expr,
        EventMerge,
    ):
        return (
            _collect_atoms(
                expr.left,
                accumulated_delay=(
                    accumulated_delay
                ),
            )
            +
            _collect_atoms(
                expr.right,
                accumulated_delay=(
                    accumulated_delay
                ),
            )
        )

    raise TypeError(
        f"unsupported event expression: {expr!r}"
    )


def evaluate_event_normal_form(
    form: EventNormalForm,
    environment: Mapping[str, SpikeTrain],
) -> SpikeTrain:
    trains = []

    for atom in form.atoms:
        try:
            source = environment[
                atom.variable
            ]
        except KeyError as error:
            raise KeyError(
                "unbound event variable: "
                f"{atom.variable}"
            ) from error

        if not isinstance(
            source,
            SpikeTrain,
        ):
            raise TypeError(
                "event environment values "
                "must be SpikeTrain instances"
            )

        trains.append(
            delay(
                source,
                atom.delay_ticks,
            )
        )

    if not trains:
        return SpikeTrain()

    return merge(
        *trains
    )


def render_event_normal_form(
    form: EventNormalForm,
) -> str:
    if not form.atoms:
        return "EMPTY"

    return " + ".join(
        (
            atom.variable
            if atom.delay_ticks == 0
            else (
                f"D{atom.delay_ticks}"
                f"({atom.variable})"
            )
        )
        for atom in form.atoms
    )
