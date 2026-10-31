"""SPK S3.7d/3b2b2k/1: bind internal service work to explicit effect obligations.

This is a fail-closed contract gate, NOT an authority for memory effects.
No completed request ID is minted. A service request (and even a service
completion claim) is not a program read, a state update, or an observation.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.memory_target_v0 import MemoryTargetV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0


# Binding requirements are architectural, not interpretations of EVENT_TIME.
_REQUIREMENTS = {
    Kind.PROGRAM_REFERENCE: ('PROGRAM', 'ACTIVE', 'PROGRAM_READ'),
    Kind.STATE_LOAD: ('STATE', 'ACTIVE', 'STATE_READ'),
    Kind.STATE_COMMIT: ('STATE', 'ACTIVE', 'STATE_WRITE_WITH_TRANSITION'),
    Kind.OBSERVATION_RECORD: ('OBSERVATION', 'ACTIVE', 'OBSERVATION_APPEND'),
    Kind.OBSERVATION_READ: ('OBSERVATION', 'ACTIVE', 'OBSERVATION_READ'),
    Kind.SNAPSHOT_READ: (None, 'SNAPSHOT', 'SNAPSHOT_READ'),
    Kind.CANDIDATE_PROGRAM_WRITE: ('PROGRAM', 'CANDIDATE', 'CANDIDATE_PROGRAM_WRITE'),
}


@dataclass(frozen=True, slots=True)
class InternalEffectObligationV0:
    request_id: int
    kind: Kind
    target_id: str
    pe_id: str
    epoch_id: str
    node_id: str | None
    event_time: int | None
    required_evidence: str
    lifecycle: str  # NOT_STARTED / PARTIAL / AWAITING_EFFECT / UNVERIFIED_CONFIRMED


@dataclass(frozen=True, slots=True)
class InternalEffectObligationPlanV0:
    epoch_id: str
    obligations: tuple[InternalEffectObligationV0, ...]
    awaiting_effect_request_ids: tuple[int, ...]
    unverified_confirmed_request_ids: tuple[int, ...]


def _unique(entries, key, label):
    result = {}
    for entry in entries:
        identity = key(entry)
        if identity in result:
            raise ValueError(f'duplicate {label}')
        result[identity] = entry
    return result


def bind_internal_effect_obligations_v0(
    plan: LogicalAccessPlanV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    service_state: ServiceQuantumStateV0,
) -> InternalEffectObligationPlanV0:
    """Check binding; expose unmet evidence without confirming ANY request.

    Precondition: the compiled access plan and service state come from the
    validated upstream pipeline. This gate additionally checks their matching
    identities and rejects malformed internal target mappings. Even a request
    in service_state.confirmed remains UNVERIFIED here until a separate owner
    supplies a genuine, replayable memory-effect witness.
    """
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError('invalid logical access plan')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    if type(service_state) is not ServiceQuantumStateV0:
        raise TypeError('invalid service state')
    if type(plan.epoch_id) is not str or not plan.epoch_id:
        raise ValueError('invalid access plan epoch')

    by_id = _unique(requests, lambda r: r.request_id, 'service request ID')
    by_target = _unique(plan.catalog.targets, lambda t: t.target_id, 'memory target')
    by_ref = _unique(plan.references, lambda ref: ref.intent.request_id, 'logical access reference')
    if any(type(t) is not MemoryTargetV0 for t in by_target.values()):
        raise TypeError('invalid catalog target')

    partial = _unique(service_state.partial, lambda w: w.request_id, 'partial service ID')
    waiting = _unique(service_state.awaiting_confirmation, lambda w: w.request_id, 'awaiting service ID')
    confirmed = _unique(service_state.confirmed, lambda w: w.request_id, 'confirmed service ID')
    if (set(partial) | set(waiting) | set(confirmed)) - set(by_id):
        raise ValueError('service state references unknown request')
    if set(partial) & set(waiting) or set(partial) & set(confirmed) or set(waiting) & set(confirmed):
        raise ValueError('conflicting service lifecycle states')

    obligations = []
    for rid, req in sorted(by_id.items()):
        requirement = _REQUIREMENTS.get(req.kind)
        if requirement is None:
            continue  # storage effects have a separate authority
        if req.epoch_id != plan.epoch_id:
            raise ValueError('request/plan epoch mismatch')
        ref = by_ref.get(rid)
        if ref is None:
            raise ValueError('unbound internal request')
        intent = ref.intent
        target = by_target.get(ref.target_id)
        if target is None:
            raise ValueError('internal target absent from catalog')
        if (intent.request_id != rid or intent.kind is not req.kind
                or intent.epoch_id != req.epoch_id
                or intent.activity is not req.activity
                or intent.pe_id != req.requester_pe_id
                or intent.event_time != req.event_time
                or intent.quantity != req.quantity
                or ref.target_id != req.target_id):
            raise ValueError('internal logical reference/service request mismatch')
        if (target.target_id != req.target_id
                or target.epoch_id != req.epoch_id
                or target.pe_id != req.target_pe_id
                or target.domain is not req.domain
                or intent.node_id != target.owner_node_id):
            raise ValueError('internal target ownership mismatch')
        expected_domain, expected_space, evidence = requirement
        if expected_domain is not None and req.domain.name != expected_domain:
            raise ValueError('internal memory domain/kind mismatch')
        if target.space.name != expected_space:
            raise ValueError('internal memory space/kind mismatch')
        if rid in confirmed:
            lifecycle = 'UNVERIFIED_CONFIRMED'
        elif rid in waiting:
            if waiting[rid].finish_boundary > service_state.next_service_tick:
                raise ValueError('internal service finished in the future')
            lifecycle = 'AWAITING_EFFECT'
        elif rid in partial:
            if not 0 < partial[rid].served_units < req.service_units:
                raise ValueError('invalid partial internal service')
            lifecycle = 'PARTIAL'
        else:
            lifecycle = 'NOT_STARTED'
        obligations.append(InternalEffectObligationV0(
            rid, req.kind, req.target_id, req.target_pe_id, req.epoch_id,
            intent.node_id, req.event_time, evidence, lifecycle,
        ))
    return InternalEffectObligationPlanV0(
        plan.epoch_id,
        tuple(obligations),
        tuple(x.request_id for x in obligations if x.lifecycle == 'AWAITING_EFFECT'),
        tuple(x.request_id for x in obligations if x.lifecycle == 'UNVERIFIED_CONFIRMED'),
    )
