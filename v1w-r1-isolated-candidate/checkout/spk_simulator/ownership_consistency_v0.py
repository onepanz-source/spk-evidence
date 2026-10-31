"""S3.7c/2: cross-audit routed ownership and complete PE event occupancy.

Post-hoc only. The existing Event Buffer Audit already accounts for external
and routed events together; this gate ensures the independently validated
routing/ownership timeline agrees with that complete occupancy ledger.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.model_v0 import NetworkV0
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0
from spk_simulator.event_buffer_audit_v0 import (
    EventBufferAuditV0, audit_event_buffers_v0,
)
from spk_simulator.event_provenance_v0 import EventProvenanceV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.functional_trace_v0 import ObservedExecutionV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.routing_binding_v0 import (
    RoutedBindingManifestV0, bind_network_routes_v0,
)
from spk_simulator.routed_service_replay_v0 import (
    RoutedServiceReplayV0, replay_routed_service_ownership_v0,
)
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0


@dataclass(frozen=True, slots=True)
class UnifiedPEOccupancyV0:
    pe_id: str
    output_capacity: int
    event_capacity: int
    peak_pending_output: int
    peak_routed_events: int
    peak_total_events: int
    final_total_events: int


@dataclass(frozen=True, slots=True)
class OwnershipConsistencyAuditV0:
    routing_binding: RoutedBindingManifestV0
    ownership_replay: RoutedServiceReplayV0
    event_buffer_audit: EventBufferAuditV0
    pe_usage: tuple[UnifiedPEOccupancyV0, ...]


def audit_ownership_consistency_v0(
    network: NetworkV0,
    observed: ObservedExecutionV0,
    placement: PEAdmissionManifestV0,
    architecture: ArchitectureProfileV0,
    plan: LogicalAccessPlanV0,
    provenance: EventProvenanceV0,
    initial_events: tuple[NetworkEventV0, ...],
    requests: tuple[MemoryServiceRequestV0, ...],
    schedule: CausalScheduleResultV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> OwnershipConsistencyAuditV0:
    """Run authoritative audits and independently compare per-PE boundaries.

    Does not reschedule or stall a request. All observed events must already
    have valid frozen-Network provenance and a completed causal service trace.
    """
    binding = bind_network_routes_v0(
        network, observed, placement, plan, provenance, initial_events, architecture,
    )
    replay = replay_routed_service_ownership_v0(
        architecture, binding, plan, requests, schedule,
    )
    buffers = audit_event_buffers_v0(
        architecture, plan, provenance, requests, schedule, initial_events,
        ingress=ingress,
    )

    pes = {pe.pe_id: pe for pe in architecture.pes}
    if len(pes) != len(architecture.pes):
        raise ValueError('duplicate PE identity')
    refs = {r.intent.request_id: r for r in plan.references}
    done = {c.request_id: c.completion_tick for c in schedule.completions}
    if len(refs) != len(plan.references) or len(done) != len(schedule.completions):
        raise ValueError('duplicate service identity')
    batch_by_key = {}
    for ref in plan.references:
        if ref.intent.kind is Kind.BATCH_CONSUME:
            key = (ref.intent.event_time, ref.intent.node_id)
            if key in batch_by_key:
                raise ValueError('duplicate batch identity')
            batch_by_key[key] = (ref.intent.request_id, ref.intent.pe_id)

    # Independent reconciliation of expected boundary deltas against the
    # complete EventBufferAudit (which counts both external and routed spikes).
    # Value order: [external arrivals, route enqueues, batch consumptions].
    expected = defaultdict(lambda: [0, 0, 0])
    for batch in provenance.batches:
        key = (batch.timestamp, batch.node_id)
        if key not in batch_by_key:
            raise ValueError('unmapped consumption batch')
        request_id, pe_id = batch_by_key[key]
        expected[(done[request_id], pe_id)][2] += len(batch.channels)

    for route in binding.routes:
        expected[(done[route.route_request_id], route.occurrence.target_pe_id)][1] += 1

    if ingress is None:
        for ev in initial_events:
            key = (ev.timestamp, ev.node_id)
            if key not in batch_by_key:
                raise ValueError('unmapped initial occurrence')
            expected[(0, batch_by_key[key][1])][0] += 1
    else:
        for arrival in ingress.arrivals:
            expected[(arrival.arrival_boundary, arrival.target_pe_id)][0] += 1

    # Only nonzero boundaries are present in the audit. Zero-slot PEs with no
    # traffic still appear in the final per-PE usage summary.
    expected = {key: tuple(value) for key, value in expected.items()
                if any(value)}
    actual = {}
    for boundary in buffers.boundaries:
        key = (boundary.service_tick, boundary.pe_id)
        if key in actual:
            raise ValueError('duplicate occupancy boundary')
        actual[key] = (
            boundary.external_enqueued,
            boundary.routed_enqueued,
            boundary.consumed,
        )
    if actual != expected:
        raise ValueError('routing, ingress and occupancy boundary mismatch')

    # Recalculate peaks and final occupancy independently from the boundary
    # deltas, then compare against both the full audit and ownership replay.
    balance = {pe_id: 0 for pe_id in pes}
    peaks = balance.copy()
    boundaries_by_key = {(b.service_tick, b.pe_id): b for b in buffers.boundaries}
    for (tick, pe_id), (external, routed, consumed) in sorted(expected.items()):
        if pe_id not in pes:
            raise ValueError('unknown PE at event boundary')
        if consumed > balance[pe_id]:
            raise ValueError('consumption before resident event')
        balance[pe_id] += external + routed - consumed
        if not 0 <= balance[pe_id] <= pes[pe_id].event_slots:
            raise ValueError('event capacity inconsistency')
        boundary = boundaries_by_key[(tick, pe_id)]
        if (boundary.occupied_after != balance[pe_id]
                or boundary.capacity != pes[pe_id].event_slots):
            raise ValueError('occupancy boundary accounting mismatch')
        peaks[pe_id] = max(peaks[pe_id], balance[pe_id])

    route_ids = {route.route_request_id for route in binding.routes}
    operations = {'OFFER': Counter(), 'ADMIT': Counter(), 'CONSUME': Counter()}
    for item in replay.transitions:
        if item.operation not in operations or item.route_request_id not in route_ids:
            raise ValueError('unknown routed ownership transition')
        operations[item.operation][item.route_request_id] += 1
        route = binding.get(item.route_request_id)
        if item.operation == 'ADMIT' and item.service_boundary != done[route.route_request_id]:
            raise ValueError('route completion/ownership mismatch')
        if item.operation == 'CONSUME' and item.service_boundary != done[route.consume_request_id]:
            raise ValueError('consumption/ownership mismatch')
    if any(ops != Counter({rid: 1 for rid in route_ids}) for ops in operations.values()):
        raise ValueError('missing or duplicate routed ownership transition')

    output_peaks = dict(replay.peak_output_by_pe)
    routed_peaks = dict(replay.peak_routed_events_by_pe)
    audit_pe_usage = {usage.pe_id: usage for usage in buffers.pe_usage}
    if (set(output_peaks) != set(pes) or set(routed_peaks) != set(pes)
            or set(audit_pe_usage) != set(pes) or any(balance.values())):
        raise ValueError('incomplete PE occupancy conservation')

    usage = []
    for pe_id in sorted(pes):
        full = audit_pe_usage[pe_id]
        if (full.peak_occupied != peaks[pe_id]
                or full.final_occupied != balance[pe_id]
                or full.capacity != pes[pe_id].event_slots
                or routed_peaks[pe_id] > peaks[pe_id]
                or output_peaks[pe_id] > pes[pe_id].output_slots):
            raise ValueError('routed and complete occupancy disagreement')
        usage.append(UnifiedPEOccupancyV0(
            pe_id, pes[pe_id].output_slots, pes[pe_id].event_slots,
            output_peaks[pe_id], routed_peaks[pe_id], peaks[pe_id], balance[pe_id],
        ))

    return OwnershipConsistencyAuditV0(binding, replay, buffers, tuple(usage))
