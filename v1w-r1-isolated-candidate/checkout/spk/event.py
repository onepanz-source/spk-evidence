from __future__ import annotations

from dataclasses import dataclass, field
from itertools import groupby
from typing import Iterable, Iterator


def _require_nonnegative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")

    if value < 0:
        raise ValueError(f"{name} must be >= 0")


@dataclass(frozen=True, order=True, slots=True)
class Event:
    """
    Elementary SPK/v0 event.

    An event is defined exclusively by:
        - timestamp: discrete time in ticks
        - channel: input/output channel identifier

    Events have no amplitude in SPK/v0.
    """

    timestamp: int
    channel: int

    def __post_init__(self) -> None:
        _require_nonnegative_int("timestamp", self.timestamp)
        _require_nonnegative_int("channel", self.channel)


@dataclass(frozen=True, slots=True)
class EventBatch:
    """
    All events occurring at exactly the same timestamp.

    Event order inside a batch has no semantic meaning.
    The tuple is sorted only to obtain a deterministic canonical
    representation.
    """

    timestamp: int
    events: tuple[Event, ...]

    def __post_init__(self) -> None:
        _require_nonnegative_int("timestamp", self.timestamp)

        events = tuple(self.events)

        if not events:
            raise ValueError("an EventBatch cannot be empty")

        if not all(isinstance(event, Event) for event in events):
            raise TypeError("all batch items must be Event instances")

        if any(event.timestamp != self.timestamp for event in events):
            raise ValueError(
                "all events in an EventBatch must share the batch timestamp"
            )

        canonical = tuple(
            sorted(
                events,
                key=lambda event: event.channel,
            )
        )

        object.__setattr__(self, "events", canonical)

    def __len__(self) -> int:
        return len(self.events)

    def count_channel(self, channel: int) -> int:
        _require_nonnegative_int("channel", channel)

        return sum(
            1
            for event in self.events
            if event.channel == channel
        )


@dataclass(frozen=True, slots=True)
class SpikeTrain:
    """
    Canonical finite multiset of SPK events.

    Multiplicity is preserved.

    Events are represented canonically in increasing order of:

        timestamp
        channel

    Sorting does NOT imply an execution order among simultaneous
    events. Events sharing a timestamp are processed as one EventBatch.
    """

    events: tuple[Event, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        events = tuple(self.events)

        if not all(isinstance(event, Event) for event in events):
            raise TypeError("all spike train items must be Event instances")

        canonical = tuple(
            sorted(
                events,
                key=lambda event: (
                    event.timestamp,
                    event.channel,
                ),
            )
        )

        object.__setattr__(self, "events", canonical)

    @classmethod
    def from_pairs(
        cls,
        pairs: Iterable[tuple[int, int]],
    ) -> "SpikeTrain":
        return cls(
            tuple(
                Event(timestamp, channel)
                for timestamp, channel in pairs
            )
        )

    def __iter__(self) -> Iterator[Event]:
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __bool__(self) -> bool:
        return bool(self.events)

    def as_pairs(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (event.timestamp, event.channel)
            for event in self.events
        )

    def batches(self) -> Iterator[EventBatch]:
        """
        Yield timestamp batches in increasing temporal order.
        """

        for timestamp, grouped in groupby(
            self.events,
            key=lambda event: event.timestamp,
        ):
            yield EventBatch(
                timestamp=timestamp,
                events=tuple(grouped),
            )
