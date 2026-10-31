"""A3c causal memory permits; no compiled host or frozen Network is invoked."""
from dataclasses import replace
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, EventV0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import (
    execute_causal_service_v1b, uniform_causal_service_plan_v1b,
)
from spk_architecture_v1.causal_memory_v1c import (
    CausalMemoryAdmissionV1c, CausalMemoryHorizonV1c,
    CausalMemoryPlanV1c, uniform_causal_memory_plan_v1c,
    execute_causal_memory_v1c,
)


def example(cid='relays/isolated/idle'):
    return next(case for ident, case in catalog_v0() if ident == cid)


def run(case, scheme='spread', *, pe=128, shared=128, mem=1024, latency=0, span=4096):
    fabric = plan_v1a(case, scheme)
    p = uniform_causal_service_plan_v1b(fabric, pe_slots=pe, fabric_slots_per_tick=shared)
    m = uniform_causal_memory_plan_v1c(fabric, pe_slots=mem, domain_slots=mem,
                                       fabric_slots_per_tick=mem,
                                       max_service_span_ticks=span)
    return execute_causal_memory_v1c(case, fabric, TransportPlanV1a(latency), p, m)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_full_corpus_ideal_memory_exactly_matches_causal_a3b(scheme):
    for _, case in catalog_v0():
        f = plan_v1a(case, scheme)
        for latency in (0, 2):
            for capacity in (1, 128):
                p = uniform_causal_service_plan_v1b(
                    f, pe_slots=capacity, fabric_slots_per_tick=capacity)
                actual = execute_causal_memory_v1c(
                    case, f, TransportPlanV1a(latency), p,
                    uniform_causal_memory_plan_v1c(f))
                expected = execute_causal_service_v1b(case, f, TransportPlanV1a(latency), p)
                assert canonical(actual['result']) == canonical(expected['result'])
                assert actual['transport']['transfers'] == expected['transport']['transfers']
                assert actual['memory']['reserved_units'] >= actual['memory']['actual_units']


@pytest.mark.parametrize('scheme', SCHEMES)
def test_all_limited_memory_grants_conserve_counts_and_limit_per_tick(scheme):
    changed = 0
    for _, case in catalog_v0():
        f = plan_v1a(case, scheme)
        p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
        for latency in (0, 2):
            obj = execute_causal_memory_v1c(
                case, f, TransportPlanV1a(latency), p,
                uniform_causal_memory_plan_v1c(
                    f, pe_slots=1, domain_slots=1, fabric_slots_per_tick=1))
            changed += obj['service']['event_weighted_wait_ticks'] > 0
            assert obj['memory']['reserved_units'] >= obj['memory']['actual_units']
            assert obj['result']['processed_events'] == (
                len(case.events) + len(obj['transport']['transfers']))
            assert obj['transport']['remaining_inflight_occurrences'] == 0
            assert len(obj['service']['grants']) == obj['result']['processed_batches']
            assert all(t['fabric_units'] <= 1 for t in obj['memory']['timeline'])
            assert all(all(n <= 1 for _, n in t['pe_units'])
                       for t in obj['memory']['timeline'])
            assert all(all(n <= 1 for _, n in t['domain_units'])
                       for t in obj['memory']['timeline'])
    assert changed > 0


def test_memory_stall_changes_real_neuron_timestamp():
    case = example()
    case = replace(case, events=(EventV0(0, 'A', 0), EventV0(0, 'B', 0),
                                 EventV0(0, 'C', 0)))
    ideal = run(case)
    finite = run(case, mem=1)
    assert [x['timestamp'] for x in ideal['result']['terminal_outputs']] == [0, 0, 0]
    assert max(x['timestamp'] for x in finite['result']['terminal_outputs']) > 0
    assert finite['memory']['reserved_units'] >= finite['memory']['actual_units']


def test_parallel_target_pe_receives_separate_event_per_route():
    case = example('relays/parallel/at_zero')
    actual = run(case, mem=1, latency=2)
    assert actual['result']['processed_events'] == (
        len(case.events) + len(actual['transport']['transfers']))
    assert actual['transport']['delivered_cross_pe_occurrences'] == (
        actual['transport']['cross_pe_occurrences'])
    assert any(row['intent'] == 'ROUTE_ENQUEUE' for row in actual['memory']['actual_accesses'])


def test_horizon_cannot_produce_false_completion():
    with pytest.raises(CausalMemoryHorizonV1c, match='max_service_span'):
        run(example('relays/chain/at_zero'), mem=1, span=1)


@pytest.mark.parametrize('invalid', [(0,1,1), (1,0,1), (1,1,0),
                                      (True,1,1), (1,True,1), (1,1,True)])
def test_invalid_positive_quotas_rejected(invalid):
    case = example('relays/chain/at_zero')
    f = plan_v1a(case, 'spread')
    p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
    m = uniform_causal_memory_plan_v1c(f, pe_slots=invalid[0],
                                      domain_slots=invalid[1],
                                      fabric_slots_per_tick=invalid[2])
    with pytest.raises(CausalMemoryAdmissionV1c):
        execute_causal_memory_v1c(case, f, TransportPlanV1a(0), p, m)


def test_duplicate_domain_or_unknown_PE_rejected():
    case = example()
    f = plan_v1a(case, 'spread')
    p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
    for wrong in (
        CausalMemoryPlanV1c((('PE0',1), ('PE0',1)), tuple((d,1) for d in ('P','S','E','O')), 1),
        CausalMemoryPlanV1c(tuple((x,1) for x in f.pe_ids), (('E',1),('E',1)),1),
        CausalMemoryPlanV1c(tuple((x,1) for x in f.pe_ids), tuple((d,1) for d in ('P','S','E','O')),1,('E','E','P','O')),
    ):
        with pytest.raises(CausalMemoryAdmissionV1c):
            execute_causal_memory_v1c(case, f, TransportPlanV1a(0), p, wrong)


def test_no_inputs_requires_no_memory_grants():
    obj = run(example(), mem=1)
    assert obj['result']['processed_events'] == 0
    assert obj['memory']['reservation_ledger'] == []
    assert obj['service']['grants'] == []


def test_pe_queue_wait_is_not_misclassified_as_memory_wait():
    # Finite PE grants can delay a queued batch after memory service has
    # already completed; the memory ledger must not inherit that PE stall.
    for _, case in catalog_v0():
        f = plan_v1a(case, 'single')
        p = uniform_causal_service_plan_v1b(f, pe_slots=1, fabric_slots_per_tick=1)
        actual = execute_causal_memory_v1c(
            case, f, TransportPlanV1a(2), p,
            uniform_causal_memory_plan_v1c(f))
        assert actual['memory']['batch_memory_wait_ticks'] == 0

def test_target_pe_memory_reservation_records_parallel_route_occurrences():
    actual = run(example('relays/parallel/at_zero'), mem=1, latency=2)
    grants = [x for x in actual['memory']['reservation_ledger']
              if x['intent'] == 'ROUTE_ENQUEUE']
    used = [x for x in actual['memory']['actual_accesses']
            if x['intent'] == 'ROUTE_ENQUEUE']
    assert sum(x['units'] for x in grants) >= sum(x['units'] for x in used)
    assert all(x['domain'] == 'E' for x in grants)
    assert any(x['pe_id'] != x['source_pe'] for x in grants)
