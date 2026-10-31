from dataclasses import replace
from copy import deepcopy
import pytest

from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.memory_projection_v1a import (
    MemoryAdmissionV1a, MemoryInvariantV1a, MemoryPlanV1a,
    MemoryCapV1a, admit_memory_v1a, uniform_memory_plan_v1a,
    project_execution_memory_v1a,
)

CASES = checked_catalog_v0()


def setup(cid=0, scheme='spread'):
    _, case = CASES[cid]
    fabric = plan_v1a(case, scheme)
    service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    memory = uniform_memory_plan_v1a(fabric)
    admit = admit_memory_v1a(case, fabric, service, memory)
    return case, fabric, service, memory, admit


def test_all_648_closed_projections():
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                                fabric_slots_per_tick=4096)
            memory = uniform_memory_plan_v1a(fabric)
            admission = admit_memory_v1a(case, fabric, service, memory)
            output = execute_failstop_v1d(case, fabric, service)
            proj = project_execution_memory_v1a(case, fabric, admission, output)
            assert proj['status'] == 'CLOSED'
            assert proj['conservation']['pending_occurrences'] == 0
            assert proj['conservation']['routed_occurrences'] == len(output['result']['observations']['routes'])
            assert proj['conservation']['consumed_occurrences'] == output['result']['processed_events']
            assert sum(x['O_records'] for x in proj['pe_usage'].values()) == (
                len(output['result']['observations']['batches']) +
                len(output['result']['observations']['routes']))
            for pid in fabric.pe_ids:
                assert proj['pe_usage'][pid]['S'] == sum(p.pe_id == pid for p in fabric.placement)


def test_all_504_fault_prefixes():
    n = 0
    for _, case in CASES:
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                                fabric_slots_per_tick=4096)
            admission = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
            base = execute_failstop_v1d(case, fabric, service)
            ledger = base['service']['ledger']
            if len(ledger) < 2:
                continue
            second = ledger[1]
            prior = sum(x['pe_id'] == second['pe_id'] for x in ledger[:1])
            fault = execute_failstop_v1d(case, fabric, service, PEFaultPlanV1d(second['pe_id'], prior))
            projection = project_execution_memory_v1a(case, fabric, admission, fault)
            assert projection['status'] == 'PE_FAULT'
            assert projection['conservation']['pending_occurrences'] == sum(
                fault['committed_prefix']['pending_event_occurrences_per_pe'].values())
            n += 1
    assert n == 504


def test_duplicate_routes_are_not_deduplicated():
    target = next((c for _, c in CASES if len(c.edges) != len(set((e.source_node, e.source_channel, e.target_node, e.target_channel, e.delay_ticks) for e in c.edges)) and c.events), None)
    assert target is not None
    fabric = plan_v1a(target, 'split')
    service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
    admission = admit_memory_v1a(target, fabric, service, uniform_memory_plan_v1a(fabric))
    output = execute_failstop_v1d(target, fabric, service)
    projected = project_execution_memory_v1a(target, fabric, admission, output)
    assert projected['conservation']['routed_occurrences'] == len(output['result']['observations']['routes'])


@pytest.mark.parametrize('domain,field', [('P','program_units'), ('S','state_units'),
                                            ('E','event_units'), ('O','observation_units')])
def test_insufficient_capacity_rejected_pre_execution(domain, field):
    case, fabric, service, memory, _ = setup(12)
    c = memory.capacities[0]
    new = replace(c, **{field: 0})
    changed = replace(memory, capacities=(new,) + memory.capacities[1:])
    with pytest.raises(MemoryAdmissionV1a, match=domain):
        admit_memory_v1a(case, fabric, service, changed)


def test_unrecognized_and_duplicate_pe_capacity_rejected():
    case, fabric, service, memory, _ = setup(12, 'split')
    with pytest.raises(MemoryAdmissionV1a):
        admit_memory_v1a(case, fabric, service, replace(memory, capacities=(memory.capacities[0],)*2))
    with pytest.raises(MemoryAdmissionV1a):
        admit_memory_v1a(case, fabric, service, replace(memory, capacities=(replace(memory.capacities[0], pe_id='UNKNOWN'),)+memory.capacities[1:]))


def test_epoch_and_capacity_types_rejected():
    case, fabric, service, memory, _ = setup(12)
    with pytest.raises(MemoryAdmissionV1a):
        admit_memory_v1a(case, fabric, service, replace(memory, epoch_id=''))
    with pytest.raises(MemoryAdmissionV1a):
        admit_memory_v1a(case, fabric, service, replace(memory, capacities=(replace(memory.capacities[0], event_units=True),)+memory.capacities[1:]))


def test_missing_batch_event_detected():
    case = next(c for _, c in CASES if c.events)
    fabric = plan_v1a(case, 'spread')
    service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
    admission = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
    output = execute_failstop_v1d(case, fabric, service)
    assert output['result']['observations']['batches']
    tampered = deepcopy(output)
    tampered['result']['observations']['batches'][0]['channels'][0] = 10**9
    with pytest.raises(MemoryInvariantV1a):
        project_execution_memory_v1a(case, fabric, admission, tampered)


def test_forged_route_detected():
    for _, case in CASES:
        fabric = plan_v1a(case, 'spread')
        service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
        output = execute_failstop_v1d(case, fabric, service)
        if output['result']['observations']['routes']:
            admission = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
            tampered = deepcopy(output)
            tampered['result']['observations']['routes'][0]['target_channel'] = 10**9
            with pytest.raises(MemoryInvariantV1a):
                project_execution_memory_v1a(case, fabric, admission, tampered)
            return
    pytest.fail('expected at least one routed case')


def test_forged_fault_pending_detected():
    for _, case in CASES:
        fabric = plan_v1a(case, 'split')
        service = uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
        out = execute_failstop_v1d(case, fabric, service)
        ledger = out['service']['ledger']
        if len(ledger) < 2:
            continue
        second = ledger[1]
        prior = sum(x['pe_id'] == second['pe_id'] for x in ledger[:1])
        fault = execute_failstop_v1d(case,fabric,service,PEFaultPlanV1d(second['pe_id'],prior))
        admission=admit_memory_v1a(case,fabric,service,uniform_memory_plan_v1a(fabric))
        tampered=deepcopy(fault)
        tampered['committed_prefix']['pending_event_occurrences_per_pe'][fabric.pe_ids[0]]+=1
        with pytest.raises(MemoryInvariantV1a):
            project_execution_memory_v1a(case,fabric,admission,tampered)
        return
    pytest.fail('expected a reachable failure')
