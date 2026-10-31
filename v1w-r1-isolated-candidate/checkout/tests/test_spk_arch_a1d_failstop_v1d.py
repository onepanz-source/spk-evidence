"""Independent A1d fail-stop and prefix conformance, no frozen runtime."""
from dataclasses import replace

import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b, PELimitV1b
from spk_architecture_v1.pe_service_v1c import (
    uniform_service_plan_v1c, execute_with_service_v1c,
)
from spk_architecture_v1.pe_fault_v1d import (
    PEFaultPlanV1d, PEFaultAdmissionV1d, PEFaultNotReachedV1d,
    execute_failstop_v1d,
)

PIN = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
SCHEMES = ('single', 'split', 'spread')
REGIMES = ((1, 1), (4096, 4096))


def _base(case, scheme, pe_cap=1, fabric_cap=1):
    fabric = plan_v1a(case, scheme)
    plan = uniform_service_plan_v1c(fabric, pe_slots=pe_cap,
                                     fabric_slots_per_tick=fabric_cap)
    return fabric, plan


def _fault_for_ledger_row(ledger, k):
    target = ledger[k]
    prior = sum(row['pe_id'] == target['pe_id'] for row in ledger[:k])
    return PEFaultPlanV1d(target['pe_id'], prior)


def test_pinned_corpus_and_all_schemes():
    assert catalog_fingerprint_v0() == PIN
    assert len(catalog_v0()) == 216


@pytest.mark.parametrize('scheme', SCHEMES)
def test_no_fault_bitwise_equal_service_and_a1b(scheme):
    for case_id, case in catalog_v0():
        fab, plan = _base(case, scheme)
        baseline = execute_with_service_v1c(case, fab, plan)
        got = execute_failstop_v1d(case, fab, plan)
        assert got['status'] == 'CLOSED'
        assert {k: got[k] for k in ('result', 'transport', 'pe_snapshots', 'service')} == baseline, case_id
        assert got['result'] == execute_on_pes_v1b(case, fab)['result']


@pytest.mark.parametrize('scheme', SCHEMES)
def test_fault_at_second_batch_is_exact_committed_prefix_in_two_capacities(scheme):
    cases_with_two = 0
    for case_id, case in catalog_v0():
        for pe_cap, fabric_cap in REGIMES:
            fab, plan = _base(case, scheme, pe_cap, fabric_cap)
            full = execute_with_service_v1c(case, fab, plan)
            ledger = full['service']['ledger']
            if len(ledger) < 2:
                continue
            cases_with_two += 1
            fault = _fault_for_ledger_row(ledger, 1)
            outcome = execute_failstop_v1d(case, fab, plan, fault)
            assert outcome['schema'] == 'spk-architecture-pe-failstop/v1d'
            assert outcome['status'] == 'PE_FAULT'
            assert 'result' not in outcome and 'receipt' not in outcome
            assert outcome['fault']['stage'] == 'before_service_grant'
            assert outcome['fault']['node_id'] == ledger[1]['node_id']
            assert outcome['fault']['logical_timestamp'] == ledger[1]['logical_timestamp']
            prefix = outcome['committed_prefix']
            assert prefix['processed_batches'] == 1
            assert prefix['processed_events'] == ledger[0]['input_occurrences']
            assert prefix['service_ledger'] == ledger[:1]
            assert prefix['observations']['batches'] == full['result']['observations']['batches'][:1]
            assert prefix['emissions'] == [x for x in full['result']['emissions']
                                           if x['node_id'] == ledger[0]['node_id']
                                           and x['timestamp'] == ledger[0]['logical_timestamp']]
            assert sum(prefix['pending_event_occurrences_per_pe'].values()) >= 1
    assert cases_with_two > 200, 'insufficient two-batch fault coverage'


def test_fault_before_first_batch_leaves_state_unchanged():
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/interleaved')
    fab, plan = _base(case, 'spread')
    full = execute_with_service_v1c(case, fab, plan)
    first = full['service']['ledger'][0]
    got = execute_failstop_v1d(case, fab, plan, PEFaultPlanV1d(first['pe_id'], 0))
    assert got['status'] == 'PE_FAULT'
    p = got['committed_prefix']
    assert not p['service_ledger'] and not p['emissions'] and not p['observations']['routes']
    assert p['processed_events'] == p['processed_batches'] == 0
    assert all(n['last_timestamp'] == 0 for n in p['states'])


def test_requested_fault_must_actually_trigger():
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/interleaved')
    fab, plan = _base(case, 'spread')
    with pytest.raises(PEFaultNotReachedV1d, match='not reached'):
        execute_failstop_v1d(case, fab, plan, PEFaultPlanV1d('PE2', 2000))


def test_invalid_fault_plan_rejected_without_work():
    case = catalog_v0()[0][1]
    fab, plan = _base(case, 'spread')
    for fault in (PEFaultPlanV1d('PE99', 0), PEFaultPlanV1d('PE0', -1),
                  PEFaultPlanV1d('PE0', True), PEFaultPlanV1d('PE0', 1.0),
                  {'pe_id': 'PE0', 'after_local_batches': 0}):
        with pytest.raises(PEFaultAdmissionV1d):
            execute_failstop_v1d(case, fab, plan, fault)


def test_reordering_inputs_does_not_change_fault_witness():
    case = next(c for n, c in catalog_v0() if n == 'relays/diamond/interleaved')
    fab, plan = _base(case, 'split')
    ledger = execute_with_service_v1c(case, fab, plan)['service']['ledger']
    fault = _fault_for_ledger_row(ledger, 1)
    a = execute_failstop_v1d(case, fab, plan, fault)
    b = execute_failstop_v1d(replace(case, events=tuple(reversed(case.events))), fab, plan, fault)
    assert a == b


def test_fault_engine_does_not_call_frozen_or_reference_runtime():
    from pathlib import Path
    import spk_architecture_v1.pe_fault_v1d as m
    source = Path(m.__file__).read_text()
    for dependency in ('from spk_core', 'import spk_core',
                       'from spk_network', 'import spk_network',
                       'from spk_compiler', 'import spk_compiler',
                       'execute_with_service_v1c(', 'execute_on_pes_v1b('):
        assert dependency not in source


def test_execution_limits_take_precedence_over_pregrant_fault():
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/interleaved')
    fab, plan = _base(case, 'spread')
    completed = execute_with_service_v1c(case, fab, plan)
    ledger = completed['service']['ledger']
    assert len(ledger) >= 2
    fault = _fault_for_ledger_row(ledger, 1)
    with pytest.raises(PELimitV1b, match='max_batches'):
        execute_failstop_v1d(case, fab, plan, fault, max_batches=1)
    with pytest.raises(PELimitV1b, match='max_events'):
        execute_failstop_v1d(case, fab, plan, fault,
                             max_events=ledger[0]['input_occurrences'])


def test_pending_queues_keep_every_uncommitted_occurrence_at_fault():
    case = next(c for n, c in catalog_v0() if n == 'relays/parallel/at_zero')
    fab, plan = _base(case, 'spread')
    baseline = execute_with_service_v1c(case, fab, plan)
    ledger = baseline['service']['ledger']
    assert len(ledger) >= 2
    fault = _fault_for_ledger_row(ledger, 1)
    witness = execute_failstop_v1d(case, fab, plan, fault)['committed_prefix']
    assert witness['processed_batches'] == 1
    first = ledger[0]
    first_routes = [r for r in baseline['result']['observations']['routes']
                    if (r['source_node'], r['emission_timestamp']) ==
                    (first['node_id'], first['logical_timestamp'])]
    expected = len(case.events) - first['input_occurrences'] + len(first_routes)
    assert sum(witness['pending_event_occurrences_per_pe'].values()) == expected
