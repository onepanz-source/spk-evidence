"""A2d bounded memory resource failure adjudication over A2a/A2b/A2c.

Memory admission is checked before invoking the supplied execution callback.
Service exhaustion is assessed on *post-execution aggregate logical demand*;
it neither rolls back PE work nor claims live RAM interposition.
"""
from __future__ import annotations
from dataclasses import replace
import hashlib
import json

from spk_architecture_v1.memory_projection_v1a import (
    MemoryAdmissionV1a, admit_memory_v1a, MemoryPlanV1a,
)
from spk_architecture_v1.memory_access_v1b import authorize_projection_v1b
from spk_architecture_v1.memory_service_v1c import (
    MemoryServicePlanV1c, MemoryServiceExhaustedV1c,
    serve_projection_v1c,
)

SCHEMA = 'spk-architecture-memory-exhaustion/v1d'


class MemoryProjectionMismatchV1d(ValueError):
    pass


def projection_digest_v1d(projection):
    return hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
CAP_FIELDS = {'P': 'program_units', 'S': 'state_units',
              'E': 'event_units', 'O': 'observation_units'}


def preflight_memory_v1d(case, fabric, pe_service_plan, memory_plan):
    """Admission only. No PE execution, service grant or memory mutation."""
    try:
        admission = admit_memory_v1a(case, fabric, pe_service_plan, memory_plan)
    except MemoryAdmissionV1a as exc:
        return {'schema': SCHEMA, 'status': 'ADMISSION_REJECTED',
                'reason': 'memory_admission', 'detail': str(exc),
                'admission': None}
    return {'schema': SCHEMA, 'status': 'ADMITTED', 'reason': None,
            'detail': None, 'admission': admission}


def execute_after_admission_v1d(case, fabric, pe_service_plan, memory_plan,
                                execute):
    """Reference sequencing only: never invokes execute on rejected admission.

    The supplied callback is trusted in-process test/runtime code, not sandboxed.
    """
    if not callable(execute):
        raise TypeError('execution callback must be callable')
    preflight = preflight_memory_v1d(case, fabric, pe_service_plan, memory_plan)
    if preflight['status'] != 'ADMITTED':
        return {'schema': SCHEMA, 'status': 'ADMISSION_REJECTED',
                'reason': preflight['reason'], 'detail': preflight['detail'],
                'admission': None, 'execution': None}
    execution = execute()
    if not isinstance(execution, dict) or execution.get('status') not in ('CLOSED', 'PE_FAULT'):
        raise ValueError('unrecognized PE execution outcome')
    return {'schema': SCHEMA, 'status': 'EXECUTED', 'reason': None,
            'detail': None, 'admission': preflight['admission'],
            'execution': execution}


def shortfall_plan_v1d(admission, memory_plan, domain):
    """One-unit-under-reservation negative witness, on one owned PE.

    Not all theoretical plans have positive demand in every domain; reject
    unprovable witnesses instead of inventing a capacity shortage.
    """
    if (type(memory_plan) is not MemoryPlanV1a or domain not in CAP_FIELDS
            or admission.get('schema') != 'spk-architecture-memory-projection/v1a'):
        raise ValueError('invalid memory shortfall witness inputs')
    field = CAP_FIELDS[domain]
    pe = next((pe for pe in admission['pe_ids']
               if admission['reservations'][pe]['reservation'][domain] > 0), None)
    if pe is None:
        raise ValueError('no positive reservation for domain ' + domain)
    need = admission['reservations'][pe]['reservation'][domain]
    return replace(memory_plan, capacities=tuple(
        replace(c, **{field: need - 1}) if c.pe_id == pe else c
        for c in memory_plan.capacities))


def service_verdict_v1d(admission, projection, plan, *, expected_projection_sha256):
    """Fail-closed status for A2c posthoc service of authorized aggregates.

    No complete service receipt is published on service-tick exhaustion.
    A prior PE_FAULT remains distinct from service success or failure.
    Invalid grants, epochs and plans raise their original exceptions.
    """
    if (type(expected_projection_sha256) is not str or len(expected_projection_sha256) != 64
            or projection_digest_v1d(projection) != expected_projection_sha256):
        raise MemoryProjectionMismatchV1d('projection does not match controller-pinned trace')
    authorization = authorize_projection_v1b(admission, projection)
    try:
        result = serve_projection_v1c(admission, projection, plan)
    except MemoryServiceExhaustedV1c:
        return {'schema': SCHEMA, 'status': 'MEMORY_SERVICE_EXHAUSTED',
                'reason': 'max_service_ticks',
                'projection_sha256': expected_projection_sha256,
                'execution_status': projection['status'],
                'logical_units': authorization['logical_units'],
                'max_service_ticks': plan.max_service_ticks,
                'complete_service': None,
                'limitations': ['no completed memory-service receipt',
                                'aggregate service occurs after PE execution',
                                'no rollback of earlier PE work']}
    if result['status'] != 'SERVED' or result['logical_units'] != authorization['logical_units']:
        raise AssertionError('A2c inconsistent complete memory service')
    return {'schema': SCHEMA, 'status': 'SERVED', 'reason': None,
            'projection_sha256': expected_projection_sha256,
            'execution_status': projection['status'],
            'logical_units': authorization['logical_units'],
            'max_service_ticks': plan.max_service_ticks,
            'complete_service': result,
            'limitations': ['aggregate service occurs after PE execution',
                            'no live interposition or causal memory timing']}


def exact_and_short_v1d(admission, projection, plan, *, expected_projection_sha256):
    """Construct exact-completion and 1-tick-short *positive* budget probes.

    Returns short=None when a positive one-short budget cannot be formed.
    Uses A2c full service to locate the exact boundary; this is conformance,
    not an independent timing oracle.
    """
    if type(plan) is not MemoryServicePlanV1c:
        raise TypeError('A2c service plan required')
    authorization = authorize_projection_v1b(admission, projection)
    adequate = replace(plan, max_service_ticks=max(1, authorization['logical_units'] + 1))
    reference = service_verdict_v1d(admission, projection, adequate,
                                   expected_projection_sha256=expected_projection_sha256)
    if reference['status'] != 'SERVED':
        raise AssertionError('adequate service bound failed')
    ticks = reference['complete_service']['service_ticks']
    # Empty demand consumes no ticks; max_service_ticks remains strictly > 0.
    exact = service_verdict_v1d(admission, projection,
                                replace(plan, max_service_ticks=max(1, ticks)),
                                expected_projection_sha256=expected_projection_sha256)
    if exact['status'] != 'SERVED' or exact['complete_service']['service_ticks'] != ticks:
        raise AssertionError('exact service boundary unexpectedly rejected')
    short = None
    if ticks >= 2:
        short = service_verdict_v1d(admission, projection,
                                   replace(plan, max_service_ticks=ticks - 1),
                                   expected_projection_sha256=expected_projection_sha256)
        if short['status'] != 'MEMORY_SERVICE_EXHAUSTED':
            raise AssertionError('short service boundary incorrectly completed')
    return {'schema': SCHEMA, 'required_service_ticks': ticks,
            'exact': exact, 'short': short}
