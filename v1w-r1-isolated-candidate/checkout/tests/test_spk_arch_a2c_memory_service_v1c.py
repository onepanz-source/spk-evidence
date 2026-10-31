"""Independent A2c policy, finite service, priority and conservation tests."""
from dataclasses import replace
from copy import deepcopy
import pytest
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.memory_projection_v1a import (
    admit_memory_v1a, project_execution_memory_v1a, uniform_memory_plan_v1a,
)
from spk_architecture_v1.memory_access_v1b import (
    issue_authority_v1b, derive_requests_v1b, AccessRequestV1b,
    MemoryAccessDeniedV1b,
)
from spk_architecture_v1.memory_service_v1c import (
    SCHEMA, DOMAINS, DEFAULT_PRIORITY, memory_service_plan_v1c,
    serve_projection_v1c, serve_authorized_v1c, MemoryServiceAdmissionV1c,
    MemoryServiceExhaustedV1c,
)

CASES = checked_catalog_v0()


def fixture(scheme='spread'):
    case = next(c for _, c in CASES if c.events and c.edges)
    fabric = plan_v1a(case, scheme)
    service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    admission = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
    execution = execute_failstop_v1d(case, fabric, service)
    projection = project_execution_memory_v1a(case, fabric, admission, execution)
    return admission, projection


def test_full_648_placement_nominal_and_504_fault_prefix_service():
    closed = faults = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                                fabric_slots_per_tick=4096)
            admission = admit_memory_v1a(case, fabric, service,
                                         uniform_memory_plan_v1a(fabric))
            nominal = execute_failstop_v1d(case, fabric, service)
            projection = project_execution_memory_v1a(case, fabric, admission, nominal)
            plan = memory_service_plan_v1c(admission, pe_slots=3,
                                            fabric_slots_per_tick=4,
                                            domain_slots_per_tick=2)
            served = serve_projection_v1c(admission, projection, plan)
            assert served['status'] == 'SERVED'
            assert served['execution_status'] == 'CLOSED'
            assert served['logical_units'] == sum(x['units'] for x in served['ledger'])
            assert set(served['units_and_wait_by_domain']) == set(DOMAINS)
            closed += 1
            ledger = nominal['service']['ledger']
            if len(ledger) >= 2:
                second = ledger[1]
                prior = sum(row['pe_id'] == second['pe_id'] for row in ledger[:1])
                fault = execute_failstop_v1d(case, fabric, service,
                                            PEFaultPlanV1d(second['pe_id'], prior))
                fault_proj = project_execution_memory_v1a(case, fabric, admission, fault)
                limited = serve_projection_v1c(admission, fault_proj, plan)
                assert limited['execution_status'] == 'PE_FAULT'
                assert limited['status'] == 'SERVED'  # ledger served, NOT a CLOSED computation
                faults += 1
    assert (closed, faults) == (648, 504)


def test_unconstrained_vs_constrained_ledger_preserves_authorized_counts():
    admission, projection = fixture()
    fast = serve_projection_v1c(admission, projection,
                                memory_service_plan_v1c(admission, pe_slots=65536,
                                    fabric_slots_per_tick=65536, domain_slots_per_tick=65536))
    slow = serve_projection_v1c(admission, projection,
                                memory_service_plan_v1c(admission, pe_slots=1,
                                    fabric_slots_per_tick=1, domain_slots_per_tick=1))
    assert fast['logical_units'] == slow['logical_units']
    assert fast['units_and_wait_by_domain'] != slow['units_and_wait_by_domain']
    assert fast['service_ticks'] <= 1
    assert slow['service_ticks'] == slow['logical_units']
    assert sum(v['units'] for v in slow['units_and_wait_by_pe'].values()) == slow['logical_units']


def test_domain_priority_is_controller_policy_not_request_claim():
    admission, projection = fixture()
    plan = memory_service_plan_v1c(admission, pe_slots=1, fabric_slots_per_tick=1,
                                    domain_slots_per_tick=1)
    result = serve_projection_v1c(admission, projection, plan)
    domains_with_requests = {x['domain'] for x in projection['logical_accesses'] if x['quantity']}
    if domains_with_requests:
        assert result['ledger'][0]['domain'] == next(x for x in DEFAULT_PRIORITY if x in domains_with_requests)
    reversed_plan = replace(plan, priority_order=tuple(reversed(DEFAULT_PRIORITY)))
    alternative = serve_projection_v1c(admission, projection, reversed_plan)
    assert alternative['logical_units'] == result['logical_units']
    assert alternative['ledger'][0]['domain'] != result['ledger'][0]['domain']


def test_rotating_pe_order_and_fabric_limit_are_enforced():
    admission, projection = fixture('spread')
    plan = memory_service_plan_v1c(admission, pe_slots=1, fabric_slots_per_tick=1,
                                    domain_slots_per_tick=1)
    served = serve_projection_v1c(admission, projection, plan)
    assert all(x['units'] == 1 for x in served['ledger'])
    assert all(a['tick'] != b['tick'] for a,b in zip(served['ledger'], served['ledger'][1:]))


@pytest.mark.parametrize('change', ['pe_zero','pe_bool','fabric_zero','domain_zero',
                                     'domain_duplicate','priority_duplicate','priority_list',
                                     'too_short','pe_missing','pe_extra','wrong_type'])
def test_invalid_service_plan_fails_closed(change):
    admission, projection = fixture()
    plan = memory_service_plan_v1c(admission)
    if change == 'pe_zero': plan = replace(plan, pe_slots=((plan.pe_slots[0][0],0),)+plan.pe_slots[1:])
    if change == 'pe_bool': plan = replace(plan, pe_slots=((plan.pe_slots[0][0],True),)+plan.pe_slots[1:])
    if change == 'fabric_zero': plan = replace(plan, fabric_slots_per_tick=0)
    if change == 'domain_zero': plan = replace(plan, domain_slots=(('P',0),)+plan.domain_slots[1:])
    if change == 'domain_duplicate': plan = replace(plan, domain_slots=(('P',1),('P',1))+plan.domain_slots[2:])
    if change == 'priority_duplicate': plan = replace(plan, priority_order=('E','E','P','O'))
    if change == 'priority_list': plan = replace(plan, priority_order=list(DEFAULT_PRIORITY))
    if change == 'too_short': plan = replace(plan, max_service_ticks=0)
    if change == 'pe_missing': plan = replace(plan, pe_slots=plan.pe_slots[:-1])
    if change == 'pe_extra': plan = replace(plan, pe_slots=plan.pe_slots+(('PE-999',1),))
    if change == 'wrong_type': plan = {'pe_slots': 2}
    with pytest.raises(MemoryServiceAdmissionV1c):
        serve_projection_v1c(admission, projection, plan)


def test_exhaustion_is_explicit_and_never_returns_completed_receipt():
    admission, projection = fixture()
    plan = memory_service_plan_v1c(admission, pe_slots=1, fabric_slots_per_tick=1,
                                    domain_slots_per_tick=1, max_service_ticks=1)
    with pytest.raises(MemoryServiceExhaustedV1c, match='max_service_ticks'):
        serve_projection_v1c(admission, projection, plan)


def test_forged_A2b_request_or_projection_cannot_get_grants():
    admission, projection = fixture()
    authority = issue_authority_v1b(admission)
    requests = derive_requests_v1b(admission, projection)
    plan = memory_service_plan_v1c(admission)
    assert requests
    forged = (replace(requests[0], quantity=requests[0].quantity + 1),) + requests[1:]
    with pytest.raises(MemoryAccessDeniedV1b):
        serve_authorized_v1c(admission, projection, authority, forged, plan)
    modified = deepcopy(projection)
    modified['logical_accesses'][0]['priority'] = -100
    with pytest.raises(MemoryAccessDeniedV1b):
        serve_projection_v1c(admission, modified, plan)


def test_zero_emission_accounting_does_not_grant_unit():
    admission, projection = fixture()
    zero = [x for x in projection['logical_accesses']
            if x['intent'] == 'EMISSION_RECORD' and x['quantity'] == 0]
    if zero:
        requests = derive_requests_v1b(admission, projection)
        assert all(x.quantity > 0 for x in requests)
    assert serve_projection_v1c(admission, projection,
                                memory_service_plan_v1c(admission))['status'] == 'SERVED'
