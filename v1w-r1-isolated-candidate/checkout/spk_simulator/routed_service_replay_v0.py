"""S3.7c/1: post-hoc ownership replay using causal service completions.

Not live execution or backpressure. Routed event-slot accounting is a lower
bound: external arrivals require the independent full Event Buffer Audit.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0, routed_storage_usage_v0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.routing_binding_v0 import (
    RoutedBindingManifestV0,
    offer_bound_routed_event_v0, admit_bound_routed_event_v0,
    consume_bound_routed_event_v0,
)


@dataclass(frozen=True, slots=True)
class RoutedServiceTransitionV0:
    service_boundary: int
    operation: str
    route_request_id: int
    pending_output: int
    admitted_events: int
    consumed: int


@dataclass(frozen=True, slots=True)
class RoutedServiceReplayV0:
    transitions: tuple[RoutedServiceTransitionV0, ...]
    peak_output_by_pe: tuple[tuple[str, int], ...]
    peak_routed_events_by_pe: tuple[tuple[str, int], ...]
    final_state: RoutedStorageStateV0


def replay_routed_service_ownership_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    plan: LogicalAccessPlanV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    schedule: CausalScheduleResultV0,
) -> RoutedServiceReplayV0:
    """Reconcile OFFER/ADMIT/CONSUME against real SERVICE_TIME completions.

    The existing scheduler is not modified. Fail-closed on impossible replay.
    Does not account for external-event occupancy: this successful replay is
    NOT a substitute for audit_event_buffers_v0(..., ingress=...).
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing binding')
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError('invalid logical plan')
    if type(requests) is not tuple or any(
        type(req) is not MemoryServiceRequestV0 for req in requests
    ):
        raise TypeError('invalid request sequence')
    if type(schedule) is not CausalScheduleResultV0:
        raise TypeError('invalid causal schedule')
    if architecture.profile_id != manifest.profile_id or plan.epoch_id != manifest.epoch_id:
        raise ValueError('architecture, binding and epoch mismatch')

    reqs = {req.request_id: req for req in requests}
    refs = {ref.intent.request_id: ref for ref in plan.references}
    done = {item.request_id: item for item in schedule.completions}
    if (len(reqs) != len(requests) or len(refs) != len(plan.references)
            or len(done) != len(schedule.completions)
            or set(reqs) != set(refs) or set(reqs) != set(done)):
        raise ValueError('request/reference/completion coverage mismatch')

    # Verify recorded service work and completion times for every request.
    slices = defaultdict(list)
    for item in schedule.slices:
        req = reqs.get(item.request_id)
        if (req is None or item.target_pe_id != req.target_pe_id
                or item.target_id != req.target_id
                or item.principal_id != req.principal_id
                or item.domain != req.domain
                or item.activity != req.activity
                or item.event_time != req.event_time
                or type(item.service_tick) is not int or item.service_tick < 0
                or type(item.granted_units) is not int or item.granted_units <= 0):
            raise ValueError('invalid service slice')
        slices[item.request_id].append(item)
    if set(slices) != set(reqs):
        raise ValueError('missing service slices')

    for request_id, req in reqs.items():
        ref = refs[request_id]
        completion = done[request_id]
        if (req.kind is not ref.intent.kind
                or req.activity is not ref.intent.activity
                or req.epoch_id != manifest.epoch_id
                or req.epoch_id != ref.intent.epoch_id
                or req.requester_pe_id != ref.intent.pe_id
                or req.event_time != ref.intent.event_time
                or req.quantity != ref.intent.quantity
                or req.target_id != ref.target_id
                or completion.principal_id != req.principal_id
                or completion.target_pe_id != req.target_pe_id
                or type(completion.completion_tick) is not int
                or not 1 <= completion.completion_tick <= schedule.total_service_ticks):
            raise ValueError('request/plan/completion mismatch')
        work = sorted(slices[request_id], key=lambda s: s.service_tick)
        if (sum(item.granted_units for item in work) != req.service_units
                or any(a.service_tick == b.service_tick for a, b in zip(work, work[1:]))
                or work[-1].service_tick + 1 != completion.completion_tick
                or work[-1].remaining_units != 0):
            raise ValueError('service conservation/completion mismatch')
        remaining = req.service_units
        for item in work:
            remaining -= item.granted_units
            if remaining < 0 or item.remaining_units != remaining:
                raise ValueError('service work accounting mismatch')

    # One EMISSION_RECORD per observed source batch, regardless of fan-out.
    emissions = {}
    for ref in plan.references:
        if ref.intent.kind is Kind.EMISSION_RECORD:
            key = (ref.intent.node_id, ref.intent.event_time)
            if key in emissions:
                raise ValueError('duplicate source emission record')
            emissions[key] = ref

    # (boundary, phase, route ID, operation): process consumes before
    # admissions before newly offered outputs at the same boundary.
    actions = []
    for route in manifest.routes:
        occurrence = route.occurrence
        route_id = route.route_request_id
        emit = emissions.get((occurrence.source_node_id, occurrence.emission_event_time))
        route_ref = refs.get(route_id)
        consume_ref = refs.get(route.consume_request_id)
        if (emit is None or route_ref is None or consume_ref is None
                or emit.intent.pe_id != occurrence.source_pe_id
                or route_ref.intent.kind is not Kind.ROUTE_ENQUEUE
                or route_ref.intent.node_id != occurrence.target_node_id
                or route_ref.intent.pe_id != occurrence.source_pe_id
                or route_ref.intent.event_time != occurrence.emission_event_time
                or reqs[route_id].target_pe_id != occurrence.target_pe_id
                or reqs[route_id].requester_pe_id != occurrence.source_pe_id
                or consume_ref.intent.kind is not Kind.BATCH_CONSUME
                or consume_ref.intent.node_id != occurrence.target_node_id
                or consume_ref.intent.event_time != occurrence.delivery_event_time
                or consume_ref.intent.pe_id != occurrence.target_pe_id):
            raise ValueError('route/emission/consumption identity mismatch')
        offer_tick = done[emit.intent.request_id].completion_tick
        admit_tick = done[route_id].completion_tick
        consume_tick = done[route.consume_request_id].completion_tick
        if not (offer_tick < admit_tick < consume_tick):
            raise ValueError('noncausal ownership service timeline')
        actions.extend((
            (offer_tick, 2, route_id, 'OFFER'),
            (admit_tick, 1, route_id, 'ADMIT'),
            (consume_tick, 0, route_id, 'CONSUME'),
        ))

    state = RoutedStorageStateV0(manifest.profile_id, manifest.epoch_id)
    peak_output = {pe.pe_id: 0 for pe in architecture.pes}
    peak_event = {pe.pe_id: 0 for pe in architecture.pes}
    transitions = []
    for tick, _, route_id, operation in sorted(actions):
        if operation == 'OFFER':
            state = offer_bound_routed_event_v0(architecture, state, manifest, route_id)
        elif operation == 'ADMIT':
            state = admit_bound_routed_event_v0(architecture, state, manifest, route_id)
        else:
            state = consume_bound_routed_event_v0(
                architecture, state, manifest, route_id,
                consume_request_id=manifest.get(route_id).consume_request_id,
            )
        for usage in routed_storage_usage_v0(architecture, state):
            peak_output[usage.pe_id] = max(peak_output[usage.pe_id], usage.pending_output)
            peak_event[usage.pe_id] = max(peak_event[usage.pe_id], usage.admitted_events)
        transitions.append(RoutedServiceTransitionV0(
            tick, operation, route_id, len(state.pending_output),
            len(state.admitted_events), len(state.consumed_ids),
        ))

    if (state.pending_output or state.admitted_events
            or set(state.consumed_ids) != {r.route_request_id for r in manifest.routes}):
        raise ValueError('incomplete routed occurrence conservation')
    return RoutedServiceReplayV0(
        tuple(transitions), tuple(sorted(peak_output.items())),
        tuple(sorted(peak_event.items())), state,
    )
