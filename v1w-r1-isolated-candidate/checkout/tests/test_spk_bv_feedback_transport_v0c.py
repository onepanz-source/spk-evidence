"""BV v0c sidecar transport: causality, budget, deduplication and replay tests."""
import copy
import json
from pathlib import Path

import pytest

from spk_backvalidation_v0.contract_v0 import canonical, digest, validate_trace
from spk_backvalidation_v0.budgeted_feedback_v0c import (
    DEFAULT_BUDGET, FeedbackTransportRejected, transport_v0c,
)
from spk_backvalidation_v0 import simulator_feedback_v0c as b
from spk_backvalidation_v0.simulator_evidence_v0b import NEW, OLD, _run


@pytest.fixture(scope='module')
def evidence():
    return b.capture_v0c()


@pytest.fixture
def diamond():
    return json.loads((Path(__file__).resolve().parents[1] /
                      'examples/spk_bv_v0_distributed_feedback.json').read_text())


def test_genuine_engines_and_three_pe_layouts(evidence):
    assert evidence['pair_count'] == 16
    assert evidence['execution_count'] == 128
    for row in evidence['rows']:
        assert row['arms']['baseline']['terminal_count'] == 0
        assert row['arms']['candidate']['terminal_count'] == 1
        for arm in row['arms'].values():
            assert len(set(arm['placements_sha256'].values())) == 1


def test_source_trace_bound_to_actual_deliveries(evidence):
    for row in evidence['rows']:
        arm = row['arms']['candidate']
        trace = arm['trace']
        assert validate_trace(trace)['status'] == 'STRUCTURAL_PASS'
        assert len(trace['occurrences']) == 2
        assert trace['occurrences'][1]['parent_ids'] == ['r1']
        assert arm['feedback']['trace_sha256'] == digest(trace)
        assert len(arm['feedback']['packets']) == 2


def test_two_hop_feedback_has_strict_order_and_correct_actors(evidence):
    for row in evidence['rows']:
        p1, p2 = row['arms']['candidate']['feedback']['packets']
        assert (p1['sender'], p1['receiver'], p1['causal_route_ids']) == ('C', 'B', ['r2'])
        assert (p2['sender'], p2['receiver'], p2['causal_route_ids']) == ('B', 'A', ['r1'])
        assert p1['delivered_at'] <= p2['send_at']
        assert p1['send_at'] > row['tick']


def test_feedback_costs_are_explicit_and_not_frozen_hardware_costs(evidence):
    for row in evidence['rows']:
        assert row['arms']['baseline']['feedback']['resources']['feedback_messages'] == 0
        assert row['arms']['candidate']['feedback']['resources'] == {
            'feedback_messages': 2, 'feedback_operations': 7,
            'feedback_memory_accesses': 5, 'peak_inflight': 1, 'feedback_words': 8,
        }
        assert row['arms']['candidate']['frozen_spike_messages'] == 2
    assert 'integrated-A3d-transport' in evidence['excluded_claims']
    assert 'physical-resource-consumption' in evidence['excluded_claims']


def test_converging_paths_not_counted_as_independent_votes(diamond):
    result = transport_v0c(diamond)
    assert result['resources']['feedback_messages'] == 2
    assert result['unique_assessment_receiver_pairs'] == 2
    assert result['packets'][0]['sender'] == 'C'
    assert result['packets'][1]['causal_route_ids'] == ['r1', 'r2']
    assert result['packets'][1]['receiver'] == 'A'


def test_two_assessments_are_not_one_vote(diamond):
    diamond['assessments'].append({**diamond['assessments'][0], 'id': 'a2'})
    r = transport_v0c(diamond)
    assert r['unique_assessment_receiver_pairs'] == 4
    assert r['resources']['feedback_messages'] == 4
    assert r['packets'][1]['send_at'] > r['packets'][0]['send_at'] or any(
        p['send_at'] > diamond['assessments'][0]['observed_at'] for p in r['packets'])


@pytest.mark.parametrize('field,value', [
    ('max_messages', 1), ('max_paths', 1), ('max_hops', 1),
    ('max_elapsed_ticks', 1), ('max_feedback_operations', 4),
    ('max_memory_accesses', 2),
])
def test_insufficient_resources_fail_closed(diamond, field, value):
    budget = dict(DEFAULT_BUDGET, **{field: value})
    with pytest.raises(FeedbackTransportRejected):
        transport_v0c(diamond, budget)


def test_inflight_slot_exhaustion_fails_closed(diamond):
    diamond['assessments'].append({**diamond['assessments'][0], 'id': 'a2'})
    with pytest.raises(FeedbackTransportRejected, match='in-flight'):
        transport_v0c(diamond, dict(DEFAULT_BUDGET, max_inflight=1))


def test_reject_forged_receiver(diamond):
    diamond['assessments'][0]['observer'] = 'B'
    with pytest.raises(ValueError):
        transport_v0c(diamond)


def test_reject_fake_causal_parent(diamond):
    diamond['occurrences'][2]['parent_ids'] = ['r1', 'r-invalid']
    with pytest.raises(ValueError):
        transport_v0c(diamond)


def test_reject_duplicate_event_identity(diamond):
    diamond['occurrences'].append(copy.deepcopy(diamond['occurrences'][0]))
    with pytest.raises(ValueError):
        transport_v0c(diamond)


def test_reject_bad_budget_types(diamond):
    with pytest.raises(FeedbackTransportRejected):
        transport_v0c(diamond, dict(DEFAULT_BUDGET, max_messages=True))
    with pytest.raises(FeedbackTransportRejected):
        transport_v0c(diamond, {'max_messages': 10})


def test_unsupported_observer_traces_rejected():
    case = b._case(NEW, 1)
    r = _run(case)
    changed = copy.deepcopy(r)
    changed['projection']['observations']['routes'][1]['target_node'] = 'A'
    with pytest.raises(FeedbackTransportRejected, match='uniquely declared edge'):
        b.build_trace_v0c(case, changed)


def test_independent_replay_seal():
    result = b.verify_v0c(b.seal_v0c())
    assert result['status'] == 'SIMULATOR_ANCHORED_SIDECAR_REPLAY_PASS'
    assert result['pair_count'] == 16
    assert result['simulator_executions'] == 128
    assert result['sidecar_packets'] == 32


def test_rehashed_forgery_fails_independent_replay():
    doc = json.loads(b.seal_v0c())
    doc['payload']['rows'][0]['arms']['candidate']['feedback']['resources']['feedback_messages'] = 0
    doc['payload_sha256'] = digest(doc['payload'])
    with pytest.raises(FeedbackTransportRejected, match='independent frozen-engine replay'):
        b.verify_v0c(canonical(doc))


def test_noncanonical_and_duplicate_json_keys_fail():
    doc = b.seal_v0c()
    with pytest.raises(FeedbackTransportRejected, match='noncanonical'):
        b.verify_v0c(json.dumps(json.loads(doc), indent=2))
    with pytest.raises(ValueError):
        b.verify_v0c('{"payload":{},"payload":{},"payload_sha256":"0"}')


def test_no_runtime_or_adaptation_claims(evidence):
    assert evidence['sidecar_kind'] == 'causal-feedback-posthoc-separate-from-frozen-scheduler'
    assert 'autonomous-program-learning' in evidence['excluded_claims']
    assert 'true-causal-credit' in evidence['excluded_claims']
