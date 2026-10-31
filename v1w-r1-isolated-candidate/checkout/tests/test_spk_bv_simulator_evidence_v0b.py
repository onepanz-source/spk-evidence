"""BV v0b: paired real frozen engines, replay boundaries, and counterexamples."""
import copy
import json
from dataclasses import replace

import pytest

from spk_backvalidation_v0.contract_v0 import canonical, digest
from spk_backvalidation_v0 import simulator_evidence_v0b as b


@pytest.fixture(scope='module')
def evidence():
    return b.capture_v0b()


def test_pair_count_uses_actual_frozen_executors(evidence):
    assert evidence['pair_count'] == 16
    assert evidence['simulator_executions'] == 128
    assert len(evidence['traces']) == 16
    assert len(evidence['credit']['trial_pairs']) == 16
    assert evidence['experiment_kind'] == 'deterministic-fixture-not-independent-sampled-trials'


def test_different_operator_compositions_same_instruction_multiset():
    assert b.OLD != b.NEW
    assert sorted(map(str, b.OLD)) == sorted(map(str, b.NEW))
    assert b.OLD[0][0] == 'ACC' and b.NEW[0][0] == 'SHIFT'


@pytest.mark.parametrize('context,expected', [
    ('beneficial', 'EVIDENCE_FOR_FURTHER_VERIFICATION'),
    ('consensus-trap', 'LOCAL_GLOBAL_CONFLICT'),
])
def test_contextual_counterfactual_decisions(evidence, context, expected):
    row = next(x for x in evidence['credit_summary']['context_results']
               if x['context_id'] == context)
    assert row['pairs'] == 8
    assert row['global_direction'] == ('POSITIVE' if context == 'beneficial' else 'NEGATIVE')
    assert row['local_direction'] == 'POSITIVE'
    assert row['decision'] == expected


def test_all_pairs_share_initial_state_and_inputs_within_pair(evidence):
    seen = set()
    for pair in evidence['credit']['trial_pairs']:
        assert pair['id'] not in seen
        seen.add(pair['id'])
        assert pair['initial_state_sha256'] == digest([('A', 0, 0), ('B', 0, 0), ('C', 0, 0)])
        assert pair['baseline']['program_sha256'] == digest(b.OLD)
        assert pair['candidate']['program_sha256'] == digest(b.NEW)
        assert pair['baseline']['trace_sha256'] != pair['candidate']['trace_sha256']


def test_three_PE_layouts_match_network_on_each_arm(evidence):
    for trace in evidence['traces']:
        assert len(set(trace['placement_digests']['baseline'].values())) == 1
        assert len(set(trace['placement_digests']['candidate'].values())) == 1
        assert trace['baseline_terminal_count'] == 0
        assert trace['candidate_terminal_count'] == 2


def test_runtime_cost_not_imaginary_feedback(evidence):
    for pair in evidence['credit']['trial_pairs']:
        assert pair['baseline']['cost']['feedback_messages'] == 0
        assert pair['candidate']['cost']['feedback_messages'] == 0
        assert pair['baseline']['cost']['candidate_eval_operations'] == 0
        assert pair['candidate']['cost']['candidate_eval_operations'] == 0
        assert pair['candidate']['cost']['operations'] > pair['baseline']['cost']['operations']


def test_no_inference_of_learning_promotion_or_significance(evidence):
    assert 'statistical-significance' in evidence['excluded_claims']
    assert 'autonomous-program-learning' in evidence['excluded_claims']
    assert 'promoted-program' in evidence['excluded_claims']


def test_canonical_replay_roundtrip():
    doc = b.seal_v0b()
    result = b.verify_v0b(doc)
    assert result['status'] == 'REAL_SIMULATOR_PAIRED_REPLAY_PASS'
    assert result['pair_count'] == 16
    assert result['simulator_executions'] == 128
    assert result['evidence_sha256'] == digest(json.loads(doc))


def test_direct_tampering_rejected():
    doc = json.loads(b.seal_v0b())
    doc['payload']['credit']['trial_pairs'][0]['candidate']['global_score'] = -1
    with pytest.raises(b.SimulatorEvidenceRejected, match='invalid or noncanonical'):
        b.verify_v0b(canonical(doc))


def test_rehashed_forgery_rejected():
    doc = json.loads(b.seal_v0b())
    doc['payload']['credit']['trial_pairs'][0]['candidate']['global_score'] = 0.0
    doc['payload']['credit_summary']['context_results'][0]['decision'] = 'INCONCLUSIVE'
    doc['payload_sha256'] = digest(doc['payload'])
    with pytest.raises(b.SimulatorEvidenceRejected, match='does not match independently rerun'):
        b.verify_v0b(canonical(doc))


def test_extra_fields_and_noncanonical_rejected():
    doc = json.loads(b.seal_v0b())
    doc['unauthorized'] = True
    with pytest.raises(b.SimulatorEvidenceRejected):
        b.verify_v0b(canonical(doc))
    with pytest.raises(b.SimulatorEvidenceRejected):
        b.verify_v0b(json.dumps(json.loads(b.seal_v0b()), indent=2))


def test_unknown_program_and_unbounded_tick_rejected():
    with pytest.raises(b.SimulatorEvidenceRejected):
        b._case((('RESET', 8),), 1)
    with pytest.raises(b.SimulatorEvidenceRejected):
        b._case(b.OLD, 0)
    with pytest.raises(b.SimulatorEvidenceRejected):
        b._case(b.NEW, 17)


def test_execution_crosscheck_rejects_corrupted_pe(monkeypatch):
    original = b.execute_on_pes_v1b
    def corrupted(*args, **kwargs):
        r = copy.deepcopy(original(*args, **kwargs))
        r['result']['processed_events'] += 1
        return r
    monkeypatch.setattr(b, 'execute_on_pes_v1b', corrupted)
    with pytest.raises(b.SimulatorEvidenceRejected, match='Network/PE observational mismatch'):
        b._run(b._case(b.NEW, 1))


def test_not_relying_on_fabric_for_global_score(evidence):
    for pair in evidence['credit']['trial_pairs']:
        positive = pair['context_id'] == 'beneficial'
        assert pair['baseline']['global_score'] == (0.0 if positive else 1.0)
        assert pair['candidate']['global_score'] == (1.0 if positive else 0.0)
        assert [o['score'] for o in pair['candidate']['feedback']] == [1.0, 1.0]
