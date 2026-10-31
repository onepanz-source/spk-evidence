from __future__ import annotations

from dataclasses import dataclass, field

from spk.event import Event, EventBatch
from spk.state import State


def _require_nonnegative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} must be >= 0")


@dataclass(slots=True)
class ExecutionContext:
    """
    SPK/v0 execution context for one event batch.

    timestamp:
        Timestamp currently being processed.

    delta_ticks:
        Elapsed ticks since the previously processed batch.

    batch:
        All simultaneous input events for this timestamp.

    state:
        Persistent scalar state + transient guard.

    output_events:
        Events emitted while processing this batch.
    """

    timestamp: int
    delta_ticks: int
    batch: EventBatch
    state: State
    output_events: list[Event] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_nonnegative_int("timestamp", self.timestamp)
        _require_nonnegative_int("delta_ticks", self.delta_ticks)

        if not isinstance(self.batch, EventBatch):
            raise TypeError("batch must be an EventBatch")

        if not isinstance(self.state, State):
            raise TypeError("state must be a State")

        if self.batch.timestamp != self.timestamp:
            raise ValueError(
                "execution context timestamp must match batch timestamp"
            )

        if not isinstance(self.output_events, list):
            raise TypeError("output_events must be a list")

        if not all(
            isinstance(event, Event)
            for event in self.output_events
        ):
            raise TypeError(
                "output_events must contain only Event instances"
            )
