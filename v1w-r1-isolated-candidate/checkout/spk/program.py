from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from spk.runtime import ExecutionContext


@runtime_checkable
class StateOperator(Protocol):
    """
    Structural interface for SPK state-side operators.

    Any operator implementing:

        __call__(ExecutionContext) -> None

    can participate in a Program.
    """

    def __call__(self, context: ExecutionContext) -> None:
        ...


@dataclass(frozen=True, slots=True)
class Program:
    """
    Ordered SPK/v0 state program.

    A Program is a finite ordered sequence of state operators.

    Operator order is semantically significant.
    """

    operators: tuple[StateOperator, ...]

    def __post_init__(self) -> None:
        operators = tuple(self.operators)

        for operator in operators:
            if not callable(operator):
                raise TypeError(
                    "all program elements must be callable state operators"
                )

        object.__setattr__(
            self,
            "operators",
            operators,
        )

    def __len__(self) -> int:
        return len(self.operators)

    def execute(
        self,
        context: ExecutionContext,
    ) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "Program.execute requires an ExecutionContext"
            )

        for operator in self.operators:
            operator(context)

    def __call__(
        self,
        context: ExecutionContext,
    ) -> None:
        self.execute(context)
