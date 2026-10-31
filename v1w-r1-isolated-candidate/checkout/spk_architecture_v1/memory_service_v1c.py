"""A2c deterministic service of *authorized aggregate logical* memory demands.

No runtime memory interposition, physical bank timing, causal backpressure or
mode-dependent priority is claimed. All aggregate demands are hypothetically
ready at service tick 0. Service time is a separate accounting domain.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_architecture_v1.memory_access_v1b import (
    derive_requests_v1b, issue_authority_v1b, authorize_requests_v1b,
    AccessAuthorityV1b, AccessRequestV1b,
)

SCHEMA = 'spk-architecture-memory-service/v1c'
DOMAINS = ('P', 'S', 'E', 'O')
DEFAULT_PRIORITY = ('E', 'S', 'P', 'O')


class MemoryServiceAdmissionV1c(ValueError):
    pass


class MemoryServiceExhaustedV1c(RuntimeError):
    """Explicit service-tick ceiling: no completed service verdict."""


@dataclass(frozen=True)
class MemoryServicePlanV1c:
    pe_slots: tuple[tuple[str, int], ...]
    fabric_slots_per_tick: int
    domain_slots: tuple[tuple[str, int], ...]
    priority_order: tuple[str, ...]
    max_service_ticks: int


def _positive(v):
    return type(v) is int and v > 0


def memory_service_plan_v1c(admission, *, pe_slots=2, fabric_slots_per_tick=3,
                             domain_slots_per_tick=2, priority_order=DEFAULT_PRIORITY,
                             max_service_ticks=65536):
    """Controller-side constructor; no access request may select a priority."""
    pe_ids = admission.get('pe_ids') if type(admission) is dict else None
    if type(pe_ids) is not list or not pe_ids:
        raise MemoryServiceAdmissionV1c('invalid admission PE list')
    return MemoryServicePlanV1c(
        tuple((pe, pe_slots) for pe in sorted(pe_ids)), fabric_slots_per_tick,
        tuple((domain, domain_slots_per_tick) for domain in DOMAINS),
        priority_order, max_service_ticks)


def _validate_plan(admission, plan):
    if type(plan) is not MemoryServicePlanV1c:
        raise MemoryServiceAdmissionV1c('invalid service plan type')
    pe_ids = admission.get('pe_ids')
    if (type(pe_ids) is not list or not pe_ids
            or any(type(pe) is not str or not pe for pe in pe_ids)
            or len(set(pe_ids)) != len(pe_ids)):
        raise MemoryServiceAdmissionV1c('invalid PE owner set')
    if (type(plan.pe_slots) is not tuple
            or any(type(item) is not tuple or len(item) != 2
                   or type(item[0]) is not str for item in plan.pe_slots)
            or plan.pe_slots != tuple(sorted(plan.pe_slots))
            or type(plan.domain_slots) is not tuple
            or any(type(item) is not tuple or len(item) != 2
                   or type(item[0]) is not str for item in plan.domain_slots)
            or type(plan.priority_order) is not tuple
            or any(type(domain) is not str for domain in plan.priority_order)
            or set(plan.priority_order) != set(DOMAINS)
            or len(plan.priority_order) != len(DOMAINS)
            or set(key for key, _ in plan.pe_slots) != set(pe_ids)
            or len(plan.pe_slots) != len(pe_ids)
            or tuple(key for key, _ in plan.domain_slots) != DOMAINS
            or not _positive(plan.fabric_slots_per_tick)
            or not _positive(plan.max_service_ticks)
            or any(not _positive(value) for _, value in plan.pe_slots)
            or any(not _positive(value) for _, value in plan.domain_slots)):
        raise MemoryServiceAdmissionV1c('noncanonical or invalid memory service plan')
    return dict(plan.pe_slots), dict(plan.domain_slots)


def serve_authorized_v1c(admission, projection, authority, requests, plan):
    """Grant finite *aggregate* units; no memory access is actually performed.

    Policy: static controller priority order by domain, then cyclic PE order
    per tick; within each PE+domain use canonical A2b request order. This
    scheduling policy is an experiment in A2c, not SPK algebra semantics.
    """
    authorized = authorize_requests_v1b(admission, projection, authority, requests)
    pe_caps, domain_caps = _validate_plan(admission, plan)
    pe_ids = sorted(pe_caps)
    remain = [request.quantity for request in requests]
    if any(type(req) is not AccessRequestV1b for req in requests):
        raise MemoryServiceAdmissionV1c('invalid access request type')
    total = sum(remain)
    if total != authorized['logical_units']:
        raise MemoryServiceAdmissionV1c('authorized quantity mismatch')
    by_domain = {domain: [0, 0] for domain in DOMAINS}  # units, weighted wait
    by_pe = {pe: [0, 0] for pe in pe_ids}
    entries = []
    ticks = 0
    outstanding = total
    while outstanding:
        if ticks >= plan.max_service_ticks:
            raise MemoryServiceExhaustedV1c('max_service_ticks: incomplete authorized demand')
        pe_used = {pe: 0 for pe in pe_ids}
        domain_used = {dom: 0 for dom in DOMAINS}
        fabric_used = 0
        rotating = pe_ids[ticks % len(pe_ids):] + pe_ids[:ticks % len(pe_ids)]
        for domain in plan.priority_order:
            for pe in rotating:
                for i, req in enumerate(requests):
                    if req.pe_id != pe or req.domain != domain or not remain[i]:
                        continue
                    quantity = min(remain[i], pe_caps[pe] - pe_used[pe],
                                   domain_caps[domain] - domain_used[domain],
                                   plan.fabric_slots_per_tick - fabric_used)
                    if quantity <= 0:
                        continue
                    remain[i] -= quantity
                    outstanding -= quantity
                    pe_used[pe] += quantity
                    domain_used[domain] += quantity
                    fabric_used += quantity
                    by_domain[domain][0] += quantity
                    by_domain[domain][1] += quantity * ticks
                    by_pe[pe][0] += quantity
                    by_pe[pe][1] += quantity * ticks
                    entries.append({'tick': ticks, 'pe_id': pe, 'domain': domain,
                                    'request_id': req.request_id, 'units': quantity})
        if not fabric_used:
            raise MemoryServiceAdmissionV1c('service plan made no progress')
        ticks += 1
    if (sum(x[0] for x in by_domain.values()) != total
            or sum(x[0] for x in by_pe.values()) != total
            or sum(item['units'] for item in entries) != total):
        raise AssertionError('memory service conservation failed')
    return {
        'schema': SCHEMA, 'status': 'SERVED', 'epoch_id': admission['epoch_id'],
        'execution_status': projection['status'], 'logical_units': total,
        'request_count': len(requests), 'service_ticks': ticks,
        'last_grant_tick': ticks - 1 if ticks else None,
        'weighted_wait_ticks': sum(item[1] for item in by_domain.values()),
        'units_and_wait_by_domain': {k: {'units': v[0], 'weighted_wait_ticks': v[1]}
                                     for k, v in by_domain.items()},
        'units_and_wait_by_pe': {k: {'units': v[0], 'weighted_wait_ticks': v[1]}
                                 for k, v in by_pe.items()},
        'ledger': entries,
        'policy': {'priority_order': list(plan.priority_order),
                   'pe_slots': [[k, v] for k, v in plan.pe_slots],
                   'domain_slots': [[k, v] for k, v in plan.domain_slots],
                   'fabric_slots_per_tick': plan.fabric_slots_per_tick,
                   'max_service_ticks': plan.max_service_ticks},
        'limitations': ['all aggregate logical demands notionally ready at tick zero',
                        'no live access interception or memory bank simulation',
                        'no causal delay, fairness bound or backpressure',
                        'service ticks do not alter spike logical timestamps'],
    }


def serve_projection_v1c(admission, projection, plan):
    authority = issue_authority_v1b(admission)
    requests = derive_requests_v1b(admission, projection)
    return serve_authorized_v1c(admission, projection, authority, requests, plan)
