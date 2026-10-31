"""Finite ownership of routed spike occurrences, SPK S3.7a v0.

A *pure* state-transition model. It does not schedule memory service,
produce neuronal spikes, authenticate callers, or apply live backpressure.
"""

from dataclasses import dataclass, replace

from spk_architecture.profile_v0 import ArchitectureProfileV0


def _id(name: str, value: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class RoutedOccurrenceV0:
    """One routed spike, including its declared source and destination."""

    event_id: int
    epoch_id: str
    source_node_id: str
    source_pe_id: str
    source_channel: int
    target_node_id: str
    target_pe_id: str
    target_channel: int
    emission_event_time: int
    delivery_event_time: int

    def __post_init__(self) -> None:
        if type(self.event_id) is not int or self.event_id < 0:
            raise ValueError("invalid event_id")
        for name in (
            "epoch_id", "source_node_id", "source_pe_id",
            "target_node_id", "target_pe_id",
        ):
            _id(name, getattr(self, name))
        for name in (
            "source_channel", "target_channel",
            "emission_event_time", "delivery_event_time",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid {name}")
        if self.delivery_event_time <= self.emission_event_time:
            raise ValueError("nonpositive logical route delay")


@dataclass(frozen=True, slots=True)
class RoutedStorageStateV0:
    """Architectural occupants plus *host-side* consumed-ID tombstones.

    Tombstones are reconciliation metadata, NOT free physical event storage.
    They must eventually be bounded/retired under an epoch retention policy.
    """

    profile_id: str
    epoch_id: str
    pending_output: tuple[RoutedOccurrenceV0, ...] = ()
    admitted_events: tuple[RoutedOccurrenceV0, ...] = ()
    consumed_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _id("profile_id", self.profile_id)
        _id("epoch_id", self.epoch_id)
        for name in ("pending_output", "admitted_events", "consumed_ids"):
            if type(getattr(self, name)) is not tuple:
                raise TypeError(f"{name} must be tuple")
        occurrences = self.pending_output + self.admitted_events
        if any(type(event) is not RoutedOccurrenceV0 for event in occurrences):
            raise TypeError("invalid stored occurrence")
        if any(event.epoch_id != self.epoch_id for event in occurrences):
            raise ValueError("event epoch mismatch")
        if any(type(item) is not int or item < 0 for item in self.consumed_ids):
            raise ValueError("invalid consumed event identity")
        identities = tuple(event.event_id for event in occurrences) + self.consumed_ids
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate event identity")


@dataclass(frozen=True, slots=True)
class RoutedPEOccupancyV0:
    pe_id: str
    pending_output: int
    output_capacity: int
    admitted_events: int
    event_capacity: int


class RoutedStorageBlockedV0(RuntimeError):
    """Explicit failed capacity transition; the input state is unchanged."""

    code = "STORAGE_BLOCKED"

    def __init__(self, pe_id: str, domain: str, occupied: int, capacity: int):
        self.pe_id = pe_id
        self.domain = domain
        self.occupied = occupied
        self.capacity = capacity
        super().__init__(
            f"{domain} full on {pe_id}: occupied={occupied}, capacity={capacity}"
        )


def _validate(architecture: ArchitectureProfileV0, state: RoutedStorageStateV0):
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")
    if type(state) is not RoutedStorageStateV0:
        raise TypeError("invalid storage state")
    if architecture.profile_id != state.profile_id:
        raise ValueError("architecture/storage profile mismatch")

    pes = {pe.pe_id: pe for pe in architecture.pes}
    output = {pe_id: 0 for pe_id in pes}
    events = {pe_id: 0 for pe_id in pes}
    for occurrence in state.pending_output + state.admitted_events:
        if occurrence.source_pe_id not in pes or occurrence.target_pe_id not in pes:
            raise ValueError("stored event references unknown PE")
    for occurrence in state.pending_output:
        output[occurrence.source_pe_id] += 1
    for occurrence in state.admitted_events:
        events[occurrence.target_pe_id] += 1

    for pe_id, pe in pes.items():
        if output[pe_id] > pe.output_slots or events[pe_id] > pe.event_slots:
            raise ValueError("pre-existing storage exceeds capacity")
    return pes, output, events


def routed_storage_usage_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
) -> tuple[RoutedPEOccupancyV0, ...]:
    pes, outputs, events = _validate(architecture, state)
    return tuple(
        RoutedPEOccupancyV0(
            pe_id, outputs[pe_id], pes[pe_id].output_slots,
            events[pe_id], pes[pe_id].event_slots,
        )
        for pe_id in sorted(pes)
    )


def offer_routed_output_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    occurrence: RoutedOccurrenceV0,
) -> RoutedStorageStateV0:
    """Publish a routed occurrence only if its source can retain it."""
    pes, output, _ = _validate(architecture, state)
    if type(occurrence) is not RoutedOccurrenceV0:
        raise TypeError("invalid occurrence")
    if occurrence.epoch_id != state.epoch_id:
        raise ValueError("event epoch mismatch")
    if occurrence.source_pe_id not in pes or occurrence.target_pe_id not in pes:
        raise ValueError("unknown source or target PE")
    if occurrence.event_id in state.consumed_ids or any(
        event.event_id == occurrence.event_id
        for event in state.pending_output + state.admitted_events
    ):
        raise ValueError("reused event identity")
    pe = pes[occurrence.source_pe_id]
    if output[pe.pe_id] >= pe.output_slots:
        raise RoutedStorageBlockedV0(
            pe.pe_id, "OUTPUT", output[pe.pe_id], pe.output_slots
        )
    return replace(state, pending_output=state.pending_output + (occurrence,))


def admit_routed_event_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    event_id: int,
) -> RoutedStorageStateV0:
    """Atomically transfer one occurrence from output to destination buffer."""
    pes, _, events = _validate(architecture, state)
    if type(event_id) is not int or event_id < 0:
        raise ValueError("invalid event_id")
    matches = [event for event in state.pending_output if event.event_id == event_id]
    if not matches:
        raise ValueError("event not pending in source output")
    occurrence = matches[0]
    pe = pes[occurrence.target_pe_id]
    if events[pe.pe_id] >= pe.event_slots:
        raise RoutedStorageBlockedV0(
            pe.pe_id, "EVENT", events[pe.pe_id], pe.event_slots
        )
    return replace(
        state,
        pending_output=tuple(
            event for event in state.pending_output if event.event_id != event_id
        ),
        admitted_events=state.admitted_events + (occurrence,),
    )


def consume_routed_event_v0(
    architecture: ArchitectureProfileV0,
    state: RoutedStorageStateV0,
    event_id: int,
    *,
    target_pe_id: str,
) -> RoutedStorageStateV0:
    """Release one admitted destination slot after an authorized consume.

    Actual BATCH_CONSUME authorization/provenance is checked elsewhere.
    """
    _validate(architecture, state)
    if type(event_id) is not int or event_id < 0:
        raise ValueError("invalid event_id")
    _id("target_pe_id", target_pe_id)
    matches = [event for event in state.admitted_events if event.event_id == event_id]
    if not matches:
        raise ValueError("event not admitted to destination")
    if matches[0].target_pe_id != target_pe_id:
        raise ValueError("wrong consuming PE")
    return replace(
        state,
        admitted_events=tuple(
            event for event in state.admitted_events if event.event_id != event_id
        ),
        consumed_ids=state.consumed_ids + (event_id,),
    )
