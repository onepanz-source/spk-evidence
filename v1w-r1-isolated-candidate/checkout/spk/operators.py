from __future__ import annotations

from dataclasses import dataclass
import math

from spk.event import Event, SpikeTrain
from spk.runtime import ExecutionContext


def _require_real(name: str, value: int | float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")

    return value


def _require_optional_channel(channel: int | None) -> None:
    if channel is None:
        return

    if isinstance(channel, bool) or not isinstance(channel, int):
        raise TypeError("channel must be an integer or None")

    if channel < 0:
        raise ValueError("channel must be >= 0")


def merge(*trains: SpikeTrain) -> SpikeTrain:
    """
    SPK/MERGE

    Multiset union of one or more spike trains.
    Multiplicity is preserved.
    """

    if not trains:
        raise ValueError("MERGE requires at least one SpikeTrain")

    if not all(isinstance(train, SpikeTrain) for train in trains):
        raise TypeError("MERGE accepts only SpikeTrain instances")

    events: list[Event] = []

    for train in trains:
        events.extend(train.events)

    return SpikeTrain(tuple(events))


@dataclass(frozen=True, slots=True)
class Delay:
    """
    SPK/DELAY

    Shift every event by a non-negative integer number of ticks.
    """

    ticks: int

    def __post_init__(self) -> None:
        if isinstance(self.ticks, bool) or not isinstance(self.ticks, int):
            raise TypeError("delay ticks must be an integer")

        if self.ticks < 0:
            raise ValueError("delay ticks must be >= 0")

    def __call__(self, train: SpikeTrain) -> SpikeTrain:
        if not isinstance(train, SpikeTrain):
            raise TypeError("DELAY accepts only a SpikeTrain")

        return SpikeTrain(
            tuple(
                Event(
                    timestamp=event.timestamp + self.ticks,
                    channel=event.channel,
                )
                for event in train
            )
        )


def delay(train: SpikeTrain, ticks: int) -> SpikeTrain:
    """
    Functional convenience form of SPK/DELAY.
    """

    return Delay(ticks)(train)


@dataclass(frozen=True, slots=True)
class Acc:
    """
    SPK/ACC

    Add:

        weight * number_of_matching_events

    to the persistent scalar state.

    If channel is None, every event in the current batch contributes.

    ACC does not modify the transient guard.
    """

    weight: float = 1.0
    channel: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "weight",
            _require_real("weight", self.weight),
        )

        _require_optional_channel(self.channel)

    def __call__(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "ACC accepts only an ExecutionContext"
            )

        if self.channel is None:
            count = len(context.batch)
        else:
            count = context.batch.count_channel(self.channel)

        result = context.state.x + self.weight * count

        if not math.isfinite(result):
            raise ValueError(
                "ACC produced a non-finite state value"
            )

        context.state.x = result


@dataclass(frozen=True, slots=True)
class Decay:
    """
    SPK/DECAY

    Apply exponential decay to the persistent scalar state:

        x' = x * exp(-delta_ticks / tau)

    DECAY:
        - uses elapsed time from the ExecutionContext;
        - does not inspect event multiplicity;
        - does not modify the transient guard.
    """

    tau: float

    def __post_init__(self) -> None:
        tau = _require_real("tau", self.tau)

        if tau <= 0.0:
            raise ValueError("tau must be > 0")

        object.__setattr__(self, "tau", tau)

    def __call__(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "DECAY accepts only an ExecutionContext"
            )

        factor = math.exp(
            -context.delta_ticks / self.tau
        )

        result = context.state.x * factor

        if not math.isfinite(result):
            raise ValueError(
                "DECAY produced a non-finite state value"
            )

        context.state.x = result


@dataclass(frozen=True, slots=True)
class Compare:
    """
    SPK/CMP

    Compare the current persistent scalar state against a threshold.

        guard = (x >= threshold)

    CMP:
        - does not modify persistent state;
        - overwrites the transient guard.
    """

    threshold: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "threshold",
            _require_real("threshold", self.threshold),
        )

    def __call__(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "CMP accepts only an ExecutionContext"
            )

        context.state.guard = (
            context.state.x >= self.threshold
        )


@dataclass(frozen=True, slots=True)
class Emit:
    """
    SPK/EMIT

    If the transient guard is true, emit one event at the
    current execution timestamp on channel_out.

    EMIT:
        - does not modify persistent state;
        - does not modify the guard;
        - may therefore be executed multiple times and produce
          coincident output events.
    """

    channel_out: int = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.channel_out, bool)
            or not isinstance(self.channel_out, int)
        ):
            raise TypeError(
                "channel_out must be an integer"
            )

        if self.channel_out < 0:
            raise ValueError(
                "channel_out must be >= 0"
            )

    def __call__(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "EMIT accepts only an ExecutionContext"
            )

        if context.state.guard:
            context.output_events.append(
                Event(
                    timestamp=context.timestamp,
                    channel=self.channel_out,
                )
            )


@dataclass(frozen=True, slots=True)
class Reset:
    """
    SPK/RESET

    If the transient guard is true, replace the persistent
    scalar state with the configured reset value.

    RESET:
        - does nothing when the guard is false;
        - does not modify the guard;
        - does not emit events.
    """

    value: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _require_real("value", self.value),
        )

    def __call__(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError(
                "RESET accepts only an ExecutionContext"
            )

        if context.state.guard:
            context.state.x = self.value
