"""Independent A2d A2a admission-first and A2c exact-service boundary tests."""
from dataclasses import replace
from copy import deepcopy
import pytest
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.memory_projection_v1a import (
    uniform_memory_plan_v1a, project_execution_memory_v1a,
)
from spk_architecture_v1.memory_service_v1c import (
    memory_service_plan_v1c, MemoryServiceAdmissionV1c,
)
from spk_architecture_v1.memory_access_v1b import MemoryAccessDeniedV1b
from spk_architecture_v1.memory_exhaustion_v1d import (
    CAP_FIELDS, SCHEMA, preflight_memory_v1d, execute_after_admission_v1d,
    shortfall_plan_v1d, exact_and_short_v1d, service_verdict_v1d,
    projection_digest_v1d, MemoryProjectionMismatchV1d,
)

CASES = checked_catalog_v0()


def setup(index=7, scheme='spread'):
    _, case = CASES[index]
    fabric = plan_v1a(case, scheme)
    pe_plan = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    memory = uniform_memory_plan_v1a(fabric)
    admission = preflight_memory_v1d(case, fabric, pe_plan, memory)
    assert admission['status'] == 'ADMITTED'
    outcome = execute_failstop_v1d(case, fabric, pe_plan)
    projection = project_execution_memory_v1a(case, fabric, admission['admission'], outcome)
    service_plan = memory_service_plan_v1c(admission['admission'], pe_slots=2,
                                 fabric_slots_per_tick=3, domain_slots_per_tick=2)
    return case, fabric, pe_plan, memory, admission['admission'], outcome, projection, service_plan


def test_all_648_nominal_and_504_fault_exact_service_boundaries():
    nominal = faults = too_short = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            pe_plan = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                                fabric_slots_per_tick=4096)
            admission = preflight_memory_v1d(case, fabric, pe_plan,
                                             uniform_memory_plan_v1a(fabric))
            assert admission['status'] == 'ADMITTED'
            output = execute_failstop_v1d(case, fabric, pe_plan)
            proj = project_execution_memory_v1a(case, fabric, admission['admission'], output)
            plan = memory_service_plan_v1c(admission['admission'], pe_slots=2,
                                 fabric_slots_per_tick=3, domain_slots_per_tick=2)
            exact = exact_and_short_v1d(admission['admission'], proj, plan,
                         expected_projection_sha256=projection_digest_v1d(proj))
            assert exact['exact']['status'] == 'SERVED'
            assert exact['exact']['execution_status'] == 'CLOSED'
            if exact['short'] is not None:
                assert exact['short']['status'] == 'MEMORY_SERVICE_EXHAUSTED'
                assert exact['short']['complete_service'] is None
                too_short += 1
            nominal += 1
            ledger = output['service']['ledger']
            if len(ledger) >= 2:
                second = ledger[1]
                prior = sum(row['pe_id'] == second['pe_id'] for row in ledger[:1])
                output_fault = execute_failstop_v1d(case, fabric, pe_plan,
                                  PEFaultPlanV1d(second['pe_id'], prior))
                fault_proj = project_execution_memory_v1a(case, fabric,
                                                           admission['admission'], output_fault)
                boundary = exact_and_short_v1d(admission['admission'], fault_proj, plan,
                         expected_projection_sha256=projection_digest_v1d(fault_proj))
                assert boundary['exact']['status'] == 'SERVED'
                assert boundary['exact']['execution_status'] == 'PE_FAULT'
                if boundary['short'] is not None:
                    assert boundary['short']['execution_status'] == 'PE_FAULT'
                    assert boundary['short']['status'] == 'MEMORY_SERVICE_EXHAUSTED'
                faults += 1
    assert (nominal, faults) == (648, 504)
    assert too_short > 0


def test_all_2592_one_unit_capacity_shortfalls_rejected_pre_execution():
    count = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            pe_plan = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                               fabric_slots_per_tick=4096)
            memory = uniform_memory_plan_v1a(fabric)
            nominal = preflight_memory_v1d(case, fabric, pe_plan, memory)
            assert nominal['status'] == 'ADMITTED'
            for domain in CAP_FIELDS:
                invalid = shortfall_plan_v1d(nominal['admission'], memory, domain)
                def forbidden():
                    raise AssertionError('PE execution invoked after memory rejection')
                result = execute_after_admission_v1d(case, fabric, pe_plan,
                                                     invalid, forbidden)
                assert result['status'] == 'ADMISSION_REJECTED'
                assert f'/{domain}:' in result['detail']
                assert result['execution'] is None
                count += 1
    assert count == 2592


def test_admitted_executes_once_and_keeps_original_PE_status():
    case, fabric, pe_plan, memory, _, _, _, _ = setup()
    observed = []
    def execute():
        observed.append('called')
        return execute_failstop_v1d(case, fabric, pe_plan)
    result = execute_after_admission_v1d(case, fabric, pe_plan, memory, execute)
    assert observed == ['called']
    assert result['status'] == 'EXECUTED'
    assert result['execution']['status'] == 'CLOSED'


@pytest.mark.parametrize('domain', tuple(CAP_FIELDS))
def test_admission_rejects_each_domain_before_side_effect(domain):
    case, fabric, pe_plan, memory, admission, _, _, _ = setup()
    mutated = shortfall_plan_v1d(admission, memory, domain)
    callbacks = []
    result = execute_after_admission_v1d(case, fabric, pe_plan, mutated,
                                         lambda: callbacks.append('executed'))
    assert callbacks == []
    assert result['status'] == 'ADMISSION_REJECTED'
    assert result['execution'] is None


def test_service_exhaustion_does_not_masquerade_as_PE_closed():
    _, _, _, _, admission, _, projection, plan = setup()
    full = exact_and_short_v1d(admission, projection, plan,
                         expected_projection_sha256=projection_digest_v1d(projection))
    assert full['short'] is not None
    assert full['exact']['complete_service']['status'] == 'SERVED'
    assert full['short']['complete_service'] is None
    assert full['short']['reason'] == 'max_service_ticks'
    assert full['short']['execution_status'] == 'CLOSED'


def test_invalid_service_plan_not_classified_as_exhaustion():
    _, _, _, _, admission, _, projection, plan = setup()
    with pytest.raises(MemoryServiceAdmissionV1c):
        service_verdict_v1d(admission, projection, replace(plan, fabric_slots_per_tick=0),
                 expected_projection_sha256=projection_digest_v1d(projection))


def test_forged_projection_not_classified_as_resource_exhaustion():
    _, _, _, _, admission, _, projection, plan = setup()
    forged = deepcopy(projection)
    forged['logical_accesses'][0]['quantity'] += 100
    with pytest.raises(MemoryProjectionMismatchV1d):
        service_verdict_v1d(admission, forged, replace(plan, max_service_ticks=1),
                 expected_projection_sha256=projection_digest_v1d(projection))


def test_no_positive_short_budget_for_one_tick_or_empty_demand():
    _, _, _, _, admission, _, projection, plan = setup()
    fast = replace(plan, pe_slots=tuple((pe,65536) for pe,_ in plan.pe_slots),
                   fabric_slots_per_tick=65536,
                   domain_slots=tuple((k,65536) for k,v in plan.domain_slots))
    bound = exact_and_short_v1d(admission, projection, fast,
                         expected_projection_sha256=projection_digest_v1d(projection))
    assert bound['required_service_ticks'] <= 1
    assert bound['short'] is None


def test_schema_and_no_rollback_contract_is_explicit():
    _, _, _, _, admission, _, projection, plan = setup()
    bound = exact_and_short_v1d(admission, projection, plan,
                         expected_projection_sha256=projection_digest_v1d(projection))
    assert bound['schema'] == SCHEMA
    assert 'no rollback' in ' '.join(bound['short']['limitations'])


def test_unknown_exec_status_is_not_accepted():
    case, fabric, pe_plan, memory, _, _, _, _ = setup()
    with pytest.raises(ValueError, match='unrecognized'):
        execute_after_admission_v1d(case, fabric, pe_plan, memory,
                                   lambda: {'status':'FAKE_CLOSED'})
