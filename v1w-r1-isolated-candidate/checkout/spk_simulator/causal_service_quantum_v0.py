"""SPK S3.7d/3b2b2d: single-owner, finite PE service quantum ledger.

Tracks *work*, never invents causal completion. A work-finished request
requires an explicit later confirmation before its dependents can start.
Confirmation authenticity (memory commit, consume or output publication)
remains the responsibility of the future Boundary/Service integration.
This is NOT a fully autonomous backpressure scheduler.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.causal_service_frontier_v0 import (
    CausalServiceFrontierV0, classify_causal_service_frontier_v0,
)


def _ids(label, values):
    if (type(values) is not tuple or
            any(type(rid) is not int or rid < 0 for rid in values) or
            values != tuple(sorted(set(values)))):
        raise ValueError(f'noncanonical {label}')


@dataclass(frozen=True, slots=True)
class ServiceWorkV0:
    request_id: int
    served_units: int


@dataclass(frozen=True, slots=True)
class ServiceFinishedV0:
    request_id: int
    finish_boundary: int


@dataclass(frozen=True, slots=True)
class ServiceConfirmedV0:
    request_id: int
    confirmation_boundary: int


@dataclass(frozen=True, slots=True)
class ServiceQuantumSliceV0:
    request_id: int
    pe_id: str
    service_tick: int
    units: int
    event_time: int


@dataclass(frozen=True, slots=True)
class ServiceQuantumStateV0:
    next_service_tick: int = 0
    partial: tuple[ServiceWorkV0, ...] = ()
    awaiting_confirmation: tuple[ServiceFinishedV0, ...] = ()
    confirmed: tuple[ServiceConfirmedV0, ...] = ()

    def __post_init__(self):
        if type(self.next_service_tick) is not int or self.next_service_tick < 0:
            raise ValueError('invalid next SERVICE_TIME')
        for name, element_type in (
            ('partial', ServiceWorkV0),
            ('awaiting_confirmation', ServiceFinishedV0),
            ('confirmed', ServiceConfirmedV0),
        ):
            entries = getattr(self, name)
            if type(entries) is not tuple or any(type(x) is not element_type for x in entries):
                raise TypeError(f'invalid {name}')
            _ids(name, tuple(item.request_id for item in entries))
            for entry in entries:
                field = ('served_units' if name == 'partial' else
                         'finish_boundary' if name == 'awaiting_confirmation' else
                         'confirmation_boundary')
                value = getattr(entry, field)
                if type(value) is not int or value < (1 if name == 'partial' else 0):
                    raise ValueError(f'invalid {name} quantity or boundary')
        identity_groups = (
            {x.request_id for x in self.partial},
            {x.request_id for x in self.awaiting_confirmation},
            {x.request_id for x in self.confirmed},
        )
        if len(set.union(*identity_groups)) != sum(len(x) for x in identity_groups):
            raise ValueError('request exists in multiple service lifecycle states')
        if any(x.finish_boundary > self.next_service_tick for x in self.awaiting_confirmation):
            raise ValueError('finished request is from the future')
        if any(x.confirmation_boundary > self.next_service_tick for x in self.confirmed):
            raise ValueError('confirmed request is from the future')


@dataclass(frozen=True, slots=True)
class ServiceQuantumStepV0:
    service_tick: int
    frontier: CausalServiceFrontierV0
    slices: tuple[ServiceQuantumSliceV0, ...]
    work_finished_request_ids: tuple[int, ...]
    confirmed_request_ids: tuple[int, ...]
    pe_units: tuple[tuple[str, int], ...]
    state: ServiceQuantumStateV0
    status: str  # PROGRESSED, WAITING, IDLE. Never implies deadlock.


def advance_service_quantum_v0(
    architecture: ArchitectureProfileV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: ServiceQuantumStateV0,
    *,
    confirmed_request_ids: tuple[int, ...] = (),
    granted_memory_request_ids: tuple[int, ...] = (),
    ingress: ExternalIngressBindingV0 | None = None,
    owned_service_request_ids: tuple[int, ...] | None = None,
) -> ServiceQuantumStepV0:
    """Spend at most per-PE service bandwidth in exactly one SERVICE_TIME tick.

    If owned_service_request_ids is supplied, only these requests may spend
    units in this tick; an in-progress partial request MUST be included.
    None preserves legacy unrestricted selection; () means no new work.
    This is an explicit dispatch policy, NOT a proof of physical ownership.
    Work finished at tick t gets finish_boundary=t+1, and MUST remain pending
    until caller confirms its external architectural effect at a later call.
    New causal dependents can start at the boundary of that confirmation.
    Memory grants and confirmations remain CALLER CLAIMS, not authenticated
    by this module; no ROUTE_ENQUEUE may be considered delivered merely due
    to work exhaustion.
    """
    if type(state) is not ServiceQuantumStateV0:
        raise TypeError('invalid service quantum state')
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    _ids('confirmed_request_ids', confirmed_request_ids)
    _ids('granted_memory_request_ids', granted_memory_request_ids)
    if owned_service_request_ids is not None:
        _ids('owned_service_request_ids', owned_service_request_ids)
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate service request')
    all_ids = set(by_id)
    admitted = all_ids if owned_service_request_ids is None else set(owned_service_request_ids)
    if admitted - all_ids:
        raise ValueError('unknown owned service request')
    if owned_service_request_ids is not None:
        if {x.request_id for x in state.partial} - admitted:
            raise ValueError('in-flight service lacks dispatch ownership')
        if set(granted_memory_request_ids) - admitted:
            raise ValueError('memory grant for unowned service request')
    for item in state.partial:
        request = by_id.get(item.request_id)
        if request is None or item.served_units >= request.service_units:
            raise ValueError('partial service exceeds request or unknown identity')
    if (set(x.request_id for x in state.awaiting_confirmation + state.confirmed) - all_ids):
        raise ValueError('unknown finished or confirmed request')
    outstanding = {x.request_id: x for x in state.awaiting_confirmation}
    if set(confirmed_request_ids) - set(outstanding):
        raise ValueError('cannot confirm non-finished request')
    if set(granted_memory_request_ids) & (
        set(x.request_id for x in state.partial) |
        set(outstanding) |
        set(x.request_id for x in state.confirmed)
    ):
        raise ValueError('grant cannot be replayed for an in-flight or completed request')
    # A confirmation at the beginning of tick t must concern work that
    # finished at or before the boundary t.
    if any(outstanding[rid].finish_boundary > state.next_service_tick for rid in confirmed_request_ids):
        raise ValueError('premature service confirmation')
    confirmed_now = tuple(ServiceConfirmedV0(rid, state.next_service_tick)
                          for rid in confirmed_request_ids)
    completed_ids = tuple(sorted(
        [x.request_id for x in state.confirmed] + list(confirmed_request_ids)
    ))
    running_ids = tuple(sorted(
        [x.request_id for x in state.partial] +
        [rid for rid in outstanding if rid not in confirmed_request_ids]
    ))
    frontier = classify_causal_service_frontier_v0(
        architecture, requests, graph,
        service_boundary=state.next_service_tick,
        completed_request_ids=completed_ids,
        in_flight_request_ids=running_ids,
        granted_memory_request_ids=granted_memory_request_ids,
        ingress=ingress,
    )
    # Persistent partial requests already own their start-of-service grant;
    # finished requests await external confirmation and may not consume units.
    part = {x.request_id: x.served_units for x in state.partial}
    per_pe = {pe.pe_id: [] for pe in architecture.pes}
    for rid in sorted(set(part) | (set(frontier.ready_request_ids) & admitted)):
        pe_id = by_id[rid].target_pe_id
        per_pe[pe_id].append(rid)
    spent = {pe.pe_id: 0 for pe in architecture.pes}
    slices, finished = [], []
    for pe in sorted(architecture.pes, key=lambda item: item.pe_id):
        budget = pe.accesses_per_service_tick
        if type(budget) is not int or budget < 1:
            raise ValueError('invalid PE service bandwidth')
        # A deterministic fair quantum: at most one service unit per
        # request per round. Requests already started precede new starts.
        priority = sorted(per_pe[pe.pe_id], key=lambda rid: (rid not in part, rid))
        while budget:
            eligible = [rid for rid in priority if part.get(rid, 0) < by_id[rid].service_units]
            if not eligible:
                break
            for rid in eligible:
                if budget == 0:
                    break
                part[rid] = part.get(rid, 0) + 1
                budget -= 1
                spent[pe.pe_id] += 1
                slices.append(ServiceQuantumSliceV0(
                    rid, pe.pe_id, state.next_service_tick, 1, by_id[rid].event_time,
                ))
        for rid in priority:
            if part.get(rid, 0) == by_id[rid].service_units:
                finished.append(ServiceFinishedV0(rid, state.next_service_tick + 1))
                del part[rid]
    waiting = tuple(sorted(
        [item for item in state.awaiting_confirmation
         if item.request_id not in confirmed_request_ids] + finished,
        key=lambda item: item.request_id,
    ))
    next_state = ServiceQuantumStateV0(
        next_service_tick=state.next_service_tick + 1,
        partial=tuple(ServiceWorkV0(rid, part[rid]) for rid in sorted(part)),
        awaiting_confirmation=waiting,
        confirmed=tuple(sorted(state.confirmed + confirmed_now,
                               key=lambda item: item.request_id)),
    )
    status = ('PROGRESSED' if slices or confirmed_request_ids else
              'IDLE' if len(next_state.confirmed) == len(requests) else 'WAITING')
    return ServiceQuantumStepV0(
        service_tick=state.next_service_tick,
        frontier=frontier,
        slices=tuple(slices),
        work_finished_request_ids=tuple(sorted(item.request_id for item in finished)),
        confirmed_request_ids=confirmed_request_ids,
        pe_units=tuple(sorted(spent.items())),
        state=next_state,
        status=status,
    )
