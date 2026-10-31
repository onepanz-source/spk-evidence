"""SPK bounded event-buffer replay v0.

Audits a completed causal schedule, not live execution.
Legacy mode preloads external events at SERVICE_TIME boundary 0.
Optional ingress mode audits each explicit external arrival boundary.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import (
    AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain,
)
from spk_architecture.memory_target_v0 import MemorySpaceV0 as Space
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.event_provenance_v0 import EventProvenanceV0
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0
from spk_simulator.external_ingress_v0 import (
    ExternalArrivalV0, ExternalIngressPlanV0, ExternalIngressBindingV0,
    bind_external_ingress_v0,
)


class EventBufferOverflowV0(RuntimeError):
    code = "EVENT_BUFFER_OVERFLOW"

    def __init__(self, pe_id, service_tick, required, capacity):
        self.pe_id = pe_id
        self.service_tick = service_tick
        self.required = required
        self.capacity = capacity
        super().__init__(
            f"event buffer overflow: {pe_id}, tick={service_tick}, "
            f"required={required}, capacity={capacity}"
        )


@dataclass(frozen=True, slots=True)
class EventBufferBoundaryV0:
    service_tick: int
    pe_id: str
    external_enqueued: int
    routed_enqueued: int
    consumed: int
    occupied_after: int
    capacity: int


@dataclass(frozen=True, slots=True)
class EventBufferPEUsageV0:
    pe_id: str
    capacity: int
    peak_occupied: int
    final_occupied: int


@dataclass(frozen=True, slots=True)
class EventBufferAuditV0:
    boundaries: tuple[EventBufferBoundaryV0, ...]
    pe_usage: tuple[EventBufferPEUsageV0, ...]
    initial_count: int
    routed_count: int
    consumed_count: int


def audit_event_buffers_v0(
    architecture: ArchitectureProfileV0,
    plan: LogicalAccessPlanV0,
    provenance: EventProvenanceV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    schedule: CausalScheduleResultV0,
    initial_events: tuple[NetworkEventV0, ...],
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> EventBufferAuditV0:
    """Audit event slots per PE; reject overflows without dropping spikes.

    At a completion boundary, consumes release slots before routed
    enqueues occupy them. This is an explicit v0 accounting convention.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError("invalid access plan")
    if type(provenance) is not EventProvenanceV0:
        raise TypeError("invalid provenance")
    if type(schedule) is not CausalScheduleResultV0:
        raise TypeError("invalid schedule")
    if type(requests) is not tuple or any(
        type(r) is not MemoryServiceRequestV0 for r in requests
    ):
        raise TypeError("invalid requests")
    if type(initial_events) is not tuple or any(
        type(e) is not NetworkEventV0 for e in initial_events
    ):
        raise TypeError("invalid initial events")

    # Rebind the supplied occurrence boundaries against the exact
    # original inputs, access plan, and event provenance.
    # Do not trust arbitrary forged binding objects.
    if ingress is not None:
        if type(ingress) is not ExternalIngressBindingV0:
            raise TypeError("invalid ingress binding")
        expected = bind_external_ingress_v0(
            plan, provenance, initial_events,
            ExternalIngressPlanV0(tuple(
                ExternalArrivalV0(entry.input_index, entry.arrival_boundary)
                for entry in ingress.arrivals
            )),
        )
        if ingress != expected:
            raise ValueError("ingress/plan/provenance mismatch")

    pes = {pe.pe_id: pe for pe in architecture.pes}
    refs = {ref.intent.request_id: ref for ref in plan.references}
    reqs = {req.request_id: req for req in requests}
    done = {c.request_id: c for c in schedule.completions}
    if (
        len(refs) != len(plan.references)
        or len(reqs) != len(requests)
        or len(done) != len(schedule.completions)
    ):
        raise ValueError("request/completion identity mismatch")
    if set(refs) != set(reqs) or set(reqs) != set(done):
        raise ValueError("request/completion identity mismatch")

    def event_target(node_id):
        try:
            target = plan.catalog.get(f"events:{node_id}")
        except KeyError as exc:
            raise ValueError("unknown event node") from exc
        if (
            target.space is not Space.ACTIVE
            or target.domain is not Domain.EVENT
            or target.owner_node_id != node_id
            or target.epoch_id != plan.epoch_id
            or target.pe_id not in pes
        ):
            raise ValueError("invalid event target")
        return target

    for request_id, ref in refs.items():
        intent = ref.intent
        req = reqs[request_id]
        completion = done[request_id]
        try:
            target = plan.catalog.get(ref.target_id)
        except KeyError as exc:
            raise ValueError("unknown request target") from exc
        if (
            req.kind is not intent.kind
            or req.activity is not intent.activity
            or req.epoch_id != intent.epoch_id
            or req.event_time != intent.event_time
            or req.quantity != intent.quantity
            or req.requester_pe_id != intent.pe_id
            or req.target_pe_id != target.pe_id
            or req.target_id != ref.target_id
            or req.domain is not target.domain
            or completion.principal_id != req.principal_id
            or completion.target_pe_id != req.target_pe_id
            or type(completion.completion_tick) is not int
            or not 1 <= completion.completion_tick <= schedule.total_service_ticks
        ):
            raise ValueError("request/plan/schedule mismatch")

    batches = {}
    routes = {}
    for request_id, ref in refs.items():
        intent = ref.intent
        if intent.kind in (Kind.ROUTE_ENQUEUE, Kind.BATCH_CONSUME):
            target = event_target(intent.node_id)
            if ref.target_id != target.target_id:
                raise ValueError("event target mismatch")
            if intent.kind is Kind.ROUTE_ENQUEUE:
                if intent.quantity != 1:
                    raise ValueError("route multiplicity mismatch")
                routes[request_id] = intent.node_id
            else:
                key = (intent.event_time, intent.node_id)
                if key in batches:
                    raise ValueError("duplicate batch consumption")
                batches[key] = request_id

    externals = Counter((e.timestamp, e.node_id) for e in initial_events)
    observed_routes = []
    used_batches = set()
    # boundary -> [consumed, routed enqueued, external arrived]
    actions = defaultdict(lambda: [Counter(), Counter(), Counter()])
    consumed_total = 0
    for batch in provenance.batches:
        key = (batch.timestamp, batch.node_id)
        request_id = batches.get(key)
        if (
            request_id is None
            or request_id in used_batches
            or externals[key] != batch.initial_count
            or len(batch.channels) != batch.initial_count + batch.routed_count
            or refs[request_id].intent.quantity != len(batch.channels)
        ):
            raise ValueError("batch/provenance mismatch")
        used_batches.add(request_id)
        consume_tick = done[request_id].completion_tick
        target = event_target(batch.node_id)
        actions[consume_tick][0][(target.pe_id, batch.node_id)] += len(batch.channels)
        consumed_total += len(batch.channels)
        for route_id in batch.routed_request_ids:
            if (
                routes.get(route_id) != batch.node_id
                or done[route_id].completion_tick >= consume_tick
            ):
                raise ValueError("routed event not ready for batch")
            observed_routes.append(route_id)

    if (
        used_batches != set(batches.values())
        or set(observed_routes) != set(routes)
        or len(observed_routes) != len(set(observed_routes))
        or provenance.initial_count != len(initial_events)
        or provenance.routed_count != len(routes)
        or provenance.processed_count != consumed_total
        or consumed_total != len(initial_events) + len(routes)
        or set(externals) != {
            (b.timestamp, b.node_id)
            for b in provenance.batches if b.initial_count
        }
    ):
        raise ValueError("event conservation mismatch")

    for request_id, node_id in routes.items():
        target = event_target(node_id)
        actions[done[request_id].completion_tick][1][
            (target.pe_id, node_id)
        ] += 1

    inventory = Counter()
    if ingress is None:
        for event in initial_events:
            target = event_target(event.node_id)
            inventory[(target.pe_id, event.node_id)] += 1
    else:
        first_service_tick = {}
        for item in schedule.slices:
            if item.request_id in reqs:
                first_service_tick[item.request_id] = min(
                    item.service_tick,
                    first_service_tick.get(item.request_id, item.service_tick),
                )
        for arrival in ingress.arrivals:
            target = event_target(arrival.node_id)
            if first_service_tick.get(arrival.consume_request_id, -1) < arrival.arrival_boundary:
                raise ValueError("batch consumed before external arrival")
            actions[arrival.arrival_boundary][2][(
                target.pe_id, arrival.node_id
            )] += 1

    def occupied(pe_id):
        return sum(count for (pe, _), count in inventory.items() if pe == pe_id)

    def assert_capacity(pe_id, tick):
        count = occupied(pe_id)
        capacity = pes[pe_id].event_slots
        if count > capacity:
            raise EventBufferOverflowV0(pe_id, tick, count, capacity)
        return count

    peak = {}
    boundaries = []
    for pe_id in sorted(pes):
        count = assert_capacity(pe_id, 0)
        peak[pe_id] = count
        if count:
            boundaries.append(EventBufferBoundaryV0(
                0, pe_id, count, 0, 0, count, pes[pe_id].event_slots,
            ))

    for tick in sorted(actions):
        consumed, routed, external = actions[tick]
        # Boundary semantics: free completed consumptions before enqueues.
        for key, count in consumed.items():
            if inventory[key] < count:
                raise ValueError("nonresident event consumption")
            inventory[key] -= count
        for key, count in routed.items():
            inventory[key] += count
        for key, count in external.items():
            inventory[key] += count
        for pe_id in sorted(pes):
            deq = sum(n for (pe, _), n in consumed.items() if pe == pe_id)
            enq = sum(n for (pe, _), n in routed.items() if pe == pe_id)
            ext = sum(n for (pe, _), n in external.items() if pe == pe_id)
            if not (deq or enq or ext):
                continue
            count = assert_capacity(pe_id, tick)
            peak[pe_id] = max(peak[pe_id], count)
            boundaries.append(EventBufferBoundaryV0(
                tick, pe_id, ext, enq, deq, count,
                pes[pe_id].event_slots,
            ))

    if any(inventory.values()):
        raise ValueError("unconsumed events in buffers")
    return EventBufferAuditV0(
        boundaries=tuple(boundaries),
        pe_usage=tuple(
            EventBufferPEUsageV0(pe_id, pe.event_slots, peak[pe_id], 0)
            for pe_id, pe in sorted(pes.items())
        ),
        initial_count=len(initial_events),
        routed_count=len(routes),
        consumed_count=consumed_total,
    )
