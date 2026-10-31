"""Pure A2b permission and provenance tests; no frozen Compiler needed."""
from dataclasses import replace
from copy import deepcopy
import pytest

from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.memory_projection_v1a import (
    uniform_memory_plan_v1a, admit_memory_v1a, project_execution_memory_v1a,
)
from spk_architecture_v1.memory_access_v1b import (
    MemoryAccessDeniedV1b, issue_authority_v1b, derive_requests_v1b,
    authorize_requests_v1b, authorize_projection_v1b,
)

CASES = checked_catalog_v0()


def fixture(scheme='spread'):
    case = next(c for _, c in CASES if c.events and c.edges)
    fabric = plan_v1a(case, scheme)
    service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
    admit = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
    trace = execute_failstop_v1d(case, fabric, service)
    projection = project_execution_memory_v1a(case, fabric, admit, trace)
    return case, fabric, service, admit, projection


def test_all_648_nominal_access_authorizations():
    count = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
            admit = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
            trace = execute_failstop_v1d(case, fabric, service)
            proj = project_execution_memory_v1a(case, fabric, admit, trace)
            verdict = authorize_projection_v1b(admit, proj)
            assert verdict['status'] == 'AUTHORIZED'
            assert verdict['logical_units'] == sum(row['quantity'] for row in proj['logical_accesses'])
            assert sum(verdict['units_by_activity'].values()) == verdict['logical_units']
            count += 1
    assert count == 648


def test_all_504_fault_prefix_authorizations():
    count = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
            admit = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
            base = execute_failstop_v1d(case, fabric, service)
            ledger = base['service']['ledger']
            if len(ledger) < 2:
                continue
            second = ledger[1]
            prior = sum(x['pe_id'] == second['pe_id'] for x in ledger[:1])
            prefix = execute_failstop_v1d(case, fabric, service, PEFaultPlanV1d(second['pe_id'], prior))
            proj = project_execution_memory_v1a(case, fabric, admit, prefix)
            assert proj['status'] == 'PE_FAULT'
            assert authorize_projection_v1b(admit, proj)['status'] == 'AUTHORIZED'
            count += 1
    assert count == 504


def test_wrong_epoch_in_grant_rejected():
    *_, admit, projection = fixture()
    authority = issue_authority_v1b(admit)
    forged = replace(authority, epoch_id='E1')
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, projection, forged, derive_requests_v1b(admit, projection))


def test_wrong_pe_in_grant_rejected():
    *_, admit, projection = fixture()
    authority = issue_authority_v1b(admit)
    forged = replace(authority, grants=(replace(authority.grants[0], pe_id='OTHER'),) + authority.grants[1:])
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, projection, forged, derive_requests_v1b(admit, projection))


def test_grant_cannot_self_add_permission():
    *_, admit, proj = fixture()
    auth = issue_authority_v1b(admit)
    first = auth.grants[0]
    forged = replace(auth, grants=(replace(first, allowed_intents=first.allowed_intents + ('STATE_COMMIT',)),) + auth.grants[1:])
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, proj, forged, derive_requests_v1b(admit, proj))


def test_request_cannot_self_elevate_activity():
    *_, admit, proj = fixture()
    auth = issue_authority_v1b(admit)
    requests = derive_requests_v1b(admit, proj)
    assert requests
    forged = (replace(requests[0], activity='EXECUTE', principal_id='spk/execute/'+requests[0].pe_id),) + requests[1:]
    # If this first request was already EXECUTE, mutate epoch to guarantee a changed request.
    if forged == requests:
        forged = (replace(requests[0], epoch_id='unauthorized'),) + requests[1:]
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, proj, auth, forged)


def test_requested_domain_swap_denied():
    *_, admit, proj = fixture()
    requests = derive_requests_v1b(admit, proj)
    forged = (replace(requests[0], domain='O' if requests[0].domain != 'O' else 'S'),) + requests[1:]
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, proj, issue_authority_v1b(admit), forged)


def test_request_omission_and_insertion_denied():
    *_, admit, proj = fixture()
    req = derive_requests_v1b(admit, proj)
    auth = issue_authority_v1b(admit)
    assert len(req) >= 2
    for invalid in (req[:-1], req + (req[-1],)):
        with pytest.raises(MemoryAccessDeniedV1b):
            authorize_requests_v1b(admit, proj, auth, invalid)


def test_fake_priority_does_not_grant_access():
    *_, admit, proj = fixture()
    req = derive_requests_v1b(admit, proj)
    assert not hasattr(req[0], 'priority')
    forged = deepcopy(proj)
    forged['logical_accesses'][0]['priority'] = 0
    with pytest.raises(MemoryAccessDeniedV1b):
        derive_requests_v1b(admit, forged)


def test_wrong_domain_intent_and_unknown_intent_denied():
    *_, admit, proj = fixture()
    for domain, intent in [('O', 'PROGRAM_REFERENCE'), ('E', 'OBSERVER_HACK')]:
        forged = deepcopy(proj)
        forged['logical_accesses'][0]['domain'] = domain
        forged['logical_accesses'][0]['intent'] = intent
        with pytest.raises(MemoryAccessDeniedV1b):
            derive_requests_v1b(admit, forged)


def test_duplicate_and_noncanonical_ledger_denied():
    *_, admit, proj = fixture()
    assert len(proj['logical_accesses']) >= 2
    for mutation in ('duplicate', 'reverse'):
        forged = deepcopy(proj)
        if mutation == 'duplicate':
            forged['logical_accesses'].append(forged['logical_accesses'][0])
        else:
            forged['logical_accesses'].reverse()
        with pytest.raises(MemoryAccessDeniedV1b):
            derive_requests_v1b(admit, forged)


def test_invalid_quantities_and_boolean_denied():
    *_, admit, proj = fixture()
    for quantity in (0, -1, True, '1'):
        forged = deepcopy(proj)
        forged['logical_accesses'][0]['quantity'] = quantity
        with pytest.raises(MemoryAccessDeniedV1b):
            derive_requests_v1b(admit, forged)


def test_wrong_projection_epoch_denied():
    *_, admit, proj = fixture()
    forged = deepcopy(proj)
    forged['epoch_id'] = 'E1'
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_projection_v1b(admit, forged)


def test_unknown_pe_and_fake_empty_grant_denied():
    *_, admit, proj = fixture()
    forged = deepcopy(proj)
    forged['logical_accesses'][0]['pe_id'] = 'PE-999'
    with pytest.raises(MemoryAccessDeniedV1b):
        derive_requests_v1b(admit, forged)
    with pytest.raises(MemoryAccessDeniedV1b):
        authorize_requests_v1b(admit, proj, None, derive_requests_v1b(admit, proj))


def test_observer_only_projection_cannot_claim_execution_grants():
    *_, admit, proj = fixture()
    req = derive_requests_v1b(admit, proj)
    observer = next((x for x in req if x.activity == 'OBSERVER'), None)
    if observer is not None:
        forged = tuple(replace(x, activity='EXECUTE', principal_id='spk/execute/'+x.pe_id)
                       if x == observer else x for x in req)
        with pytest.raises(MemoryAccessDeniedV1b):
            authorize_requests_v1b(admit, proj, issue_authority_v1b(admit), forged)
