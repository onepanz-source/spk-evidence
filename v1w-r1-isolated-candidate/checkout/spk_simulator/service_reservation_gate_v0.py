"""SPK S3.7d/2: finite event-slot claims at SERVICE_TIME boundaries.

Conservative post-hoc gate over completed causal scheduling, NOT a scheduler,
not live backpressure, and not a concurrency primitive. Frozen Core/Network and
Compiler contracts are untouched.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0, _ingress_release_boundaries_v0
from spk_simulator.event_reservation_v0 import (
    EventReservationStateV0, EventSlotUnavailableV0,
    arrive_external_event_slot_v0, consume_external_event_slot_v0,
    reserve_routed_event_slot_v0, commit_routed_event_slot_v0,
    consume_reserved_routed_event_v0, event_reservation_usage_v0,
)
from spk_simulator.event_storage_v0 import RoutedStorageStateV0, routed_storage_usage_v0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.routed_service_replay_v0 import replay_routed_service_ownership_v0
from spk_simulator.routing_binding_v0 import (
    RoutedBindingManifestV0, offer_bound_routed_event_v0,
)


class ServiceReservationDeniedV0(RuntimeError):
    """Fail-closed infeasibility in the *provided* service schedule."""
    def __init__(self, reason: str, boundary: int, occurrence_id: int,
                 pe_id: str, claimed: int, capacity: int):
        self.code = reason
        self.service_boundary = boundary
        self.occurrence_id = occurrence_id
        self.pe_id = pe_id
        self.claimed = claimed
        self.capacity = capacity
        super().__init__(
            f'{reason} at SERVICE_TIME={boundary}, occurrence={occurrence_id}, '
            f'PE={pe_id}, claimed={claimed}, capacity={capacity}'
        )


@dataclass(frozen=True, slots=True)
class ServiceReservationTransitionV0:
    service_boundary: int
    operation: str
    occurrence_id: int
    pe_id: str
    claimed_after: int
    reserved_after: int
    pending_output_after: int


@dataclass(frozen=True, slots=True)
class ServiceReservationPEPeakV0:
    pe_id: str
    peak_claimed: int
    peak_reserved: int
    peak_pending_output: int


@dataclass(frozen=True, slots=True)
class ServiceReservationGateResultV0:
    transitions: tuple[ServiceReservationTransitionV0, ...]
    peaks: tuple[ServiceReservationPEPeakV0, ...]
    final_storage: RoutedStorageStateV0
    final_ledger: EventReservationStateV0


def gate_service_reservations_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    plan: LogicalAccessPlanV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    schedule: CausalScheduleResultV0,
    ingress: ExternalIngressBindingV0,
) -> ServiceReservationGateResultV0:
    """Validate claim/transfer/consumption timeline using completed service.

    Reservation starts at the FIRST service slice of ROUTE_ENQUEUE, and holds
    until its completion. Already-consumed events free slots first at the same
    SERVICE_TIME boundary, followed by completed route commits, external
    arrivals, offers, and new reservations. External arrivals have precedence
    over newly requested reservations at an equal boundary.

    Capacity denial is an explicit refusal of THIS schedule, not a proof that
    another schedule cannot satisfy the workload. No SERVICE_TIME is inferred
    from EVENT_TIME. A single state owner serializes all transitions.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing binding')
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError('invalid logical access plan')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    if type(schedule) is not CausalScheduleResultV0:
        raise TypeError('invalid service schedule')
    if type(ingress) is not ExternalIngressBindingV0:
        raise TypeError('an explicit, validated external ingress binding is required')

    # Existing independent replay verifies every service slice, completion,
    # temporal relation, routing provenance, and source/output capacity.
    routed = replay_routed_service_ownership_v0(
        architecture, manifest, plan, requests, schedule,
    )
    request_by_id = {req.request_id: req for req in requests}
    _ingress_release_boundaries_v0(ingress, request_by_id)
    completed = {x.request_id: x.completion_tick for x in schedule.completions}
    starts = {}
    for segment in schedule.slices:
        starts[segment.request_id] = min(
            starts.get(segment.request_id, segment.service_tick), segment.service_tick,
        )
    # The release-aware scheduler must never service an external-consuming
    # batch before all its external occurrences are available.
    for release in ingress.batch_releases:
        if (release.consume_request_id not in starts or
                starts[release.consume_request_id] < release.ready_boundary):
            raise ValueError('external batch starts before ingress release')

    # Boundary phases: consumed external/routed -> committed routing ->
    # external ingress -> newly offered routed events -> reservation start.
    # (boundary, phase, occurrence ID, operation, PE ID)
    actions = []
    for transition in routed.transitions:
        if transition.operation == 'OFFER':
            pe_id = manifest.get(transition.route_request_id).occurrence.source_pe_id
            actions.append((transition.service_boundary, 3,
                            transition.route_request_id, 'OFFER', pe_id))
        elif transition.operation == 'ADMIT':
            pe_id = manifest.get(transition.route_request_id).occurrence.target_pe_id
            actions.append((transition.service_boundary, 1,
                            transition.route_request_id, 'COMMIT', pe_id))
        else:
            pe_id = manifest.get(transition.route_request_id).occurrence.target_pe_id
            actions.append((transition.service_boundary, 0,
                            transition.route_request_id, 'CONSUME_ROUTE', pe_id))

    for route in manifest.routes:
        route_id = route.route_request_id
        if route_id not in starts:
            raise ValueError('route lacks service start')
        start = starts[route_id]
        # A route can start only after the source produces its output.
        offer_boundary = next(t.service_boundary for t in routed.transitions
                              if t.operation == 'OFFER' and t.route_request_id == route_id)
        if start < offer_boundary or start >= completed[route_id]:
            raise ValueError('noncausal route reservation start')
        actions.append((start, 4, route_id, 'RESERVE', route.occurrence.target_pe_id))

    for arrival in ingress.arrivals:
        if arrival.consume_request_id not in completed:
            raise ValueError('external input has no consuming completion')
        consumption = completed[arrival.consume_request_id]
        if arrival.arrival_boundary >= consumption:
            raise ValueError('external event consumed before arrival')
        actions.append((arrival.arrival_boundary, 2, arrival.input_index,
                        'ARRIVE_EXTERNAL', arrival.target_pe_id))
        actions.append((consumption, 0, arrival.input_index,
                        'CONSUME_EXTERNAL', arrival.target_pe_id))

    storage = RoutedStorageStateV0(manifest.profile_id, manifest.epoch_id)
    ledger = EventReservationStateV0(manifest.profile_id, manifest.epoch_id, ingress)
    pes = {pe.pe_id for pe in architecture.pes}
    peaks = {pe_id: [0, 0, 0] for pe_id in pes}
    transitions = []

    for boundary, _, occurrence_id, operation, pe_id in sorted(actions):
        try:
            if operation == 'OFFER':
                storage = offer_bound_routed_event_v0(
                    architecture, storage, manifest, occurrence_id)
            elif operation == 'RESERVE':
                ledger = reserve_routed_event_slot_v0(
                    architecture, storage, manifest, ledger, occurrence_id)
            elif operation == 'COMMIT':
                storage, ledger = commit_routed_event_slot_v0(
                    architecture, storage, manifest, ledger, occurrence_id)
            elif operation == 'CONSUME_ROUTE':
                storage = consume_reserved_routed_event_v0(
                    architecture, storage, manifest, ledger, occurrence_id,
                    consume_request_id=manifest.get(occurrence_id).consume_request_id)
            elif operation == 'ARRIVE_EXTERNAL':
                ledger = arrive_external_event_slot_v0(
                    architecture, storage, manifest, ledger, occurrence_id)
            else:
                consume_request_id = next(
                    a.consume_request_id for a in ingress.arrivals
                    if a.input_index == occurrence_id
                )
                ledger = consume_external_event_slot_v0(
                    architecture, storage, manifest, ledger, occurrence_id,
                    consume_request_id=consume_request_id)
        except EventSlotUnavailableV0 as error:
            reason = ('EXTERNAL_INGRESS_OVERFLOW' if operation == 'ARRIVE_EXTERNAL'
                      else 'ROUTE_RESERVATION_BLOCKED')
            raise ServiceReservationDeniedV0(
                reason, boundary, occurrence_id,
                error.pe_id, error.occupied, error.capacity,
            ) from error

        claims = {u.pe_id: u for u in event_reservation_usage_v0(
            architecture, storage, manifest, ledger,
        )}
        output = {u.pe_id: u.pending_output for u in routed_storage_usage_v0(
            architecture, storage,
        )}
        for pid in pes:
            peaks[pid][0] = max(peaks[pid][0], claims[pid].claimed)
            peaks[pid][1] = max(peaks[pid][1], claims[pid].reserved)
            peaks[pid][2] = max(peaks[pid][2], output[pid])
        transitions.append(ServiceReservationTransitionV0(
            boundary, operation, occurrence_id, pe_id,
            claims[pe_id].claimed, claims[pe_id].reserved, output[pe_id],
        ))

    if (storage.pending_output or storage.admitted_events
            or ledger.reserved_routes or ledger.external_resident
            or len(storage.consumed_ids) != len(manifest.routes)
            or len(ledger.external_consumed) != len(ingress.arrivals)):
        raise ValueError('unfinished event ownership or reservation claims')

    return ServiceReservationGateResultV0(
        tuple(transitions), tuple(ServiceReservationPEPeakV0(pid, *peaks[pid])
                                  for pid in sorted(pes)), storage, ledger,
    )
