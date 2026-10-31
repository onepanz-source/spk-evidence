"""Pure PE-local transport tests; no frozen Compiler or Network imported."""
from dataclasses import replace
import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_architecture_v1.temporal_transport_v1a import (
    TransportPlanV1a, TransportAdmissionV1a, TransportCapacityV1a,
    execute_temporal_v1a,
)
from search.spk_24n_differential_evidence_v0 import canonical, project_v0


def _project(result):
    return canonical(project_v0(result, result['observations']['batches'],
                                result['observations']['routes']))


def _sample(name):
    return next(case for cid, case in catalog_v0() if cid == name)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_full_216_case_zero_latency_exact_a1b_parity(scheme):
    for cid, case in catalog_v0():
        fabric = plan_v1a(case, scheme)
        actual = execute_temporal_v1a(case, fabric, TransportPlanV1a(0))
        baseline = execute_on_pes_v1b(case, fabric)
        assert _project(actual['result']) == _project(baseline['result']), cid
        assert actual['result']['processed_events'] == (
            len(case.events) + len(actual['transport']['transfers']))
        assert actual['transport']['remaining_inflight_occurrences'] == 0


@pytest.mark.parametrize('extra', (1, 3))
def test_all_corpus_positive_latency_causal_and_conserved(extra):
    for _, case in catalog_v0():
        for scheme in SCHEMES:
            actual = execute_temporal_v1a(case, plan_v1a(case, scheme),
                                          TransportPlanV1a(extra))
            trans = actual['transport']
            assert trans['delivered_cross_pe_occurrences'] == trans['cross_pe_occurrences']
            assert trans['remaining_inflight_occurrences'] == 0
            assert len(trans['delivery_log']) == trans['cross_pe_occurrences']
            assert actual['result']['processed_events'] == len(case.events) + len(trans['transfers'])
            for row in trans['transfers']:
                assert row['delivery_timestamp'] == row['emission_timestamp'] + (
                    row['declared_delay_ticks'] + (extra if row['cross_pe'] else 0))


def test_chain_analytical_per_placement_latency_two():
    case = _sample('relays/chain/at_zero')
    for scheme, expected in [('single', 3), ('split', 5), ('spread', 7)]:
        execution = execute_temporal_v1a(case, plan_v1a(case, scheme), TransportPlanV1a(2))
        assert execution['result']['terminal_outputs'] == [
            {'timestamp': expected, 'node_id': 'C', 'channel': 7}]


def test_remote_latency_leaves_single_pe_results_unchanged():
    for _, case in catalog_v0():
        fabric = plan_v1a(case, 'single')
        ref = _project(execute_temporal_v1a(case, fabric, TransportPlanV1a(0))['result'])
        assert _project(execute_temporal_v1a(case, fabric, TransportPlanV1a(10))['result']) == ref


def test_parallel_edges_retain_two_distinct_inflight_occurrences():
    case = _sample('relays/parallel/at_zero')
    result = execute_temporal_v1a(case, plan_v1a(case, 'spread'), TransportPlanV1a(2))
    a_to_b = [t for t in result['transport']['transfers'] if t['source_node'] == 'A']
    assert len(a_to_b) == 2
    assert all(t['delivery_timestamp'] == 4 for t in a_to_b)
    batch = [b for b in result['result']['observations']['batches'] if b['node_id'] == 'B']
    assert batch[0]['timestamp'] == 4 and batch[0]['channels'] == [0, 0]


@pytest.mark.parametrize('bad', [TransportPlanV1a(-1), TransportPlanV1a(True),
                                 TransportPlanV1a(0, 0), TransportPlanV1a(0, True)])
def test_invalid_transport_plan_rejected(bad):
    case = _sample('relays/chain/at_zero')
    with pytest.raises(TransportAdmissionV1a):
        execute_temporal_v1a(case, plan_v1a(case, 'spread'), bad)


def test_transport_capacity_overflow_has_no_completed_receipt():
    case = _sample('relays/fork/at_zero')
    with pytest.raises(TransportCapacityV1a, match='max_inflight'):
        execute_temporal_v1a(case, plan_v1a(case, 'spread'),
                             TransportPlanV1a(2, max_inflight_occurrences=1))


def test_input_event_bounds_enforced():
    case = _sample('relays/chain/at_zero')
    fabric = plan_v1a(case, 'spread')
    with pytest.raises(ValueError):
        execute_temporal_v1a(case, fabric, TransportPlanV1a(0), max_events=0)
