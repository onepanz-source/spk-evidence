"""SPK explicit external-ingress availability v0.

Binds initial spike occurrences to SERVICE_TIME boundaries.
This is a finite, post-hoc readiness contract, not a live scheduler.
"""

from collections import Counter
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.access_v0 import MemoryDomainV0 as Domain
from spk_architecture.memory_target_v0 import MemorySpaceV0 as Space
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.event_provenance_v0 import EventProvenanceV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0


@dataclass(frozen=True, slots=True)
class ExternalArrivalV0:
    """Availability boundary for one occurrence in initial_events."""

    input_index: int
    arrival_boundary: int

    def __post_init__(self):
        if type(self.input_index) is not int or self.input_index < 0:
            raise ValueError("invalid input_index")
        if type(self.arrival_boundary) is not int or self.arrival_boundary < 0:
            raise ValueError("invalid arrival_boundary")


@dataclass(frozen=True, slots=True)
class ExternalIngressPlanV0:
    arrivals: tuple[ExternalArrivalV0, ...]

    def __post_init__(self):
        if type(self.arrivals) is not tuple:
            raise TypeError("arrivals must be a tuple")
        if any(type(item) is not ExternalArrivalV0 for item in self.arrivals):
            raise TypeError("invalid external arrival")
        indices = tuple(item.input_index for item in self.arrivals)
        if indices != tuple(sorted(set(indices))):
            raise ValueError("noncanonical input indices")


@dataclass(frozen=True, slots=True)
class BoundExternalArrivalV0:
    input_index: int
    event_time: int
    node_id: str
    channel: int
    target_pe_id: str
    arrival_boundary: int
    consume_request_id: int


@dataclass(frozen=True, slots=True)
class BatchIngressReleaseV0:
    consume_request_id: int
    ready_boundary: int
    input_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ExternalIngressBindingV0:
    arrivals: tuple[BoundExternalArrivalV0, ...]
    batch_releases: tuple[BatchIngressReleaseV0, ...]


def bind_external_ingress_v0(
    plan: LogicalAccessPlanV0,
    provenance: EventProvenanceV0,
    initial_events: tuple[NetworkEventV0, ...],
    ingress: ExternalIngressPlanV0,
) -> ExternalIngressBindingV0:
    """Resolve each initial occurrence to a batch and resident PE.

    Every initial occurrence must have one explicit arrival boundary.
    This does not schedule the corresponding BATCH_CONSUME transaction.
    """
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError("invalid access plan")
    if type(provenance) is not EventProvenanceV0:
        raise TypeError("invalid event provenance")
    if type(initial_events) is not tuple or any(
        type(item) is not NetworkEventV0 for item in initial_events
    ):
        raise TypeError("invalid initial events")
    if type(ingress) is not ExternalIngressPlanV0:
        raise TypeError("invalid external ingress plan")

    indices = tuple(item.input_index for item in ingress.arrivals)
    if indices != tuple(range(len(initial_events))):
        raise ValueError("ingress must bind every initial occurrence exactly once")

    if provenance.initial_count != len(initial_events):
        raise ValueError("initial event/provenance count mismatch")

    by_batch = {}
    for reference in plan.references:
        intent = reference.intent
        if intent.kind is not Kind.BATCH_CONSUME:
            continue
        key = (intent.event_time, intent.node_id)
        if key in by_batch:
            raise ValueError("duplicate batch consume identity")
        target = plan.catalog.get(reference.target_id)
        if not (
            reference.target_id == f"events:{intent.node_id}"
            and target.domain is Domain.EVENT
            and target.space is Space.ACTIVE
            and target.owner_node_id == intent.node_id
            and target.epoch_id == plan.epoch_id
            and intent.epoch_id == plan.epoch_id
        ):
            raise ValueError("invalid batch event target")
        by_batch[key] = (intent.request_id, target.pe_id, intent.quantity)

    provenance_by_batch = {}
    for batch in provenance.batches:
        key = (batch.timestamp, batch.node_id)
        if key in provenance_by_batch:
            raise ValueError("duplicate provenance batch identity")
        if batch.initial_count < 0 or batch.routed_count < 0:
            raise ValueError("invalid provenance multiplicity")
        if len(batch.channels) != batch.initial_count + batch.routed_count:
            raise ValueError("inconsistent provenance multiplicity")
        provenance_by_batch[key] = batch

    if set(provenance_by_batch) != set(by_batch):
        raise ValueError("batch/provenance identity mismatch")

    event_counts = Counter((ev.timestamp, ev.node_id) for ev in initial_events)
    for key, batch in provenance_by_batch.items():
        if event_counts[key] != batch.initial_count:
            raise ValueError("batch external multiplicity mismatch")
        if by_batch[key][2] != len(batch.channels):
            raise ValueError("batch consume quantity mismatch")
    if set(event_counts) - set(by_batch):
        raise ValueError("external event without batch")

    bound = []
    grouped = {request_id: [] for request_id, _, _ in by_batch.values()}

    for arrival in ingress.arrivals:
        event = initial_events[arrival.input_index]
        request_id, pe_id, _ = by_batch[(event.timestamp, event.node_id)]
        bound.append(BoundExternalArrivalV0(
            input_index=arrival.input_index,
            event_time=event.timestamp,
            node_id=event.node_id,
            channel=event.channel,
            target_pe_id=pe_id,
            arrival_boundary=arrival.arrival_boundary,
            consume_request_id=request_id,
        ))
        grouped[request_id].append(arrival)

    releases = tuple(
        BatchIngressReleaseV0(
            consume_request_id=request_id,
            ready_boundary=max(
                (entry.arrival_boundary for entry in grouped[request_id]),
                default=0,
            ),
            input_indices=tuple(entry.input_index for entry in grouped[request_id]),
        )
        for request_id in sorted(grouped)
    )

    return ExternalIngressBindingV0(tuple(bound), releases)
