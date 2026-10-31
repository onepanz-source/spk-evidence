from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class State:
    """
    SPK/v0 execution state.

    x:
        Single persistent scalar register.

    guard:
        Transient Boolean register.

        The guard MUST be reset to False at the beginning
        of every event batch.

    Time is deliberately not stored here.
    Temporal progression belongs to the future runtime
    execution context.
    """

    x: float = 0.0
    guard: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.x, bool) or not isinstance(
            self.x,
            (int, float),
        ):
            raise TypeError("state x must be a real number")

        self.x = float(self.x)

        if not math.isfinite(self.x):
            raise ValueError("state x must be finite")

        if not isinstance(self.guard, bool):
            raise TypeError("guard must be Boolean")

    def begin_batch(self) -> None:
        """
        Start processing a new timestamp batch.

        Persistent state survives.
        The transient guard does not.
        """

        self.guard = False

    def snapshot(self) -> tuple[float, bool]:
        """
        Return a deterministic immutable representation of the state.

        Useful later for signatures and equivalence testing.
        """

        return self.x, self.guard
