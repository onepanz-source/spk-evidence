"""Adversarial witnesses for read-only contextual credit EVIDENCE, not learning."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from spk_backvalidation_v0.contract_v0 import digest, strict_loads
from spk_backvalidation_v0.contextual_credit_v0a import (
    CreditEvidenceRejected, evaluate_credit, exact_sign_pvalue,
)

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/spk_bv_v0a_synthetic_paired_trials.json'


@pytest.fixture
def data():
    return strict_loads(EXAMPLE.read_text())


def fail(data, change, pattern=None):
    d = deepcopy(data)
    change(d)
    with pytest.raises(CreditEvidenceRejected, match=pattern):
        evaluate_credit(d)


def rows(data):
    return {r['context_id']: r for r in evaluate_credit(data)['context_results']}


def test_five_predeclared_outcomes(data):
    report = evaluate_credit(data)
    assert report['status'] == 'OFFLINE_PAIRED_EVIDENCE_ONLY'
    assert report['trial_pairs'] == 60
    assert {r['context_id']: r['decision'] for r in report['context_results']} == {
        'beneficial': 'EVIDENCE_FOR_FURTHER_VERIFICATION',
        'consensus-trap': 'LOCAL_GLOBAL_CONFLICT',
        'ambiguous': 'INCONCLUSIVE',
        'global-unavailable': 'GLOBAL_UNAVAILABLE',
        'resource-regression': 'COST_BLOCKED',
    }
    assert report['excluded_claims'][-2:] == ('promotion', 'hardware-energy')
    assert report['report_sha256'] == digest(data)


def test_no_side_effects_on_input(data):
    before = deepcopy(data)
    assert evaluate_credit(data) == evaluate_credit(strict_loads(json.dumps(data)))
    assert data == before


def test_positive_local_feedback_not_global_benefit(data):
    r = rows(data)['consensus-trap']
    assert r['local_direction'] == 'POSITIVE'
    assert r['global_direction'] == 'NEGATIVE'
    assert r['decision'] == 'LOCAL_GLOBAL_CONFLICT'


def test_no_global_information_not_zero_reward(data):
    r = rows(data)['global-unavailable']
    assert r['global_direction'] == 'UNAVAILABLE'
    assert r['mean_global_delta'] is None
    assert r['decision'] == 'GLOBAL_UNAVAILABLE'


def test_cost_can_block_positive_global_change(data):
    r = rows(data)['resource-regression']
    assert r['global_direction'] == 'POSITIVE'
    assert r['mean_extra_weighted_cost'] > data['policy']['max_mean_extra_cost']
    assert r['decision'] == 'COST_BLOCKED'


def test_sign_diagnostic_exact():
    assert exact_sign_pvalue(12, 0) == pytest.approx(2 / (2**12))
    assert exact_sign_pvalue(6, 6) == 1.0
    assert exact_sign_pvalue(0, 0) is None


def test_one_trial_per_seed_and_context(data):
    fail(data, lambda d: d['trial_pairs'][1].update(seed=d['trial_pairs'][0]['seed']))
    fail(data, lambda d: d['trial_pairs'][1].update(id=d['trial_pairs'][0]['id']))


def test_same_trace_reuse_across_trials_denied(data):
    fail(data, lambda d: d['trial_pairs'][1]['candidate'].update(trace_sha256=d['trial_pairs'][0]['candidate']['trace_sha256']))
    fail(data, lambda d: d['trial_pairs'][0]['candidate'].update(trace_sha256=d['trial_pairs'][0]['baseline']['trace_sha256']))


def test_program_arm_swap_or_change_denied(data):
    fail(data, lambda d: d['trial_pairs'][0]['candidate'].update(program_sha256=d['program']['baseline_sha256']))
    fail(data, lambda d: d['program'].update(candidate_sha256=d['program']['baseline_sha256']))


def test_bad_source_and_schema_pins_denied(data):
    fail(data, lambda d: d.update(baseline_commit='0'*40))
    fail(data, lambda d: d.update(baseline_tag='something-else'))
    fail(data, lambda d: d.update(schema='spk-other/v3'))


def test_unknown_context_or_post_treatment_field_denied(data):
    fail(data, lambda d: d['trial_pairs'][0].update(context_id='after'))
    fail(data, lambda d: d['contexts'][0].update(post_treatment_score=0.9))


def test_invalid_numbers_denied(data):
    for x in (float('nan'), float('inf'), True, 1.1, -1.1):
        fail(data, lambda d, v=x: d['trial_pairs'][0]['candidate'].update(global_score=v))
    fail(data, lambda d: d['trial_pairs'][0]['candidate']['cost'].update(operations=-1))
    fail(data, lambda d: d['trial_pairs'][0]['candidate']['cost'].update(memory_accesses=True))
    fail(data, lambda d: d['policy'].update(alpha_ppm=True))


def test_feedback_receiver_cannot_vote_twice(data):
    fail(data, lambda d: d['trial_pairs'][0]['candidate']['feedback'].append(
        dict(d['trial_pairs'][0]['candidate']['feedback'][0])))


def test_feedback_abstention_not_zero(data):
    d = deepcopy(data)
    for pair in d['trial_pairs']:
        if pair['context_id'] == 'beneficial':
            for arm in ('baseline', 'candidate'):
                for fb in pair[arm]['feedback']:
                    fb.update(status='ABSTAIN',score=None,reason='missing-measurement')
    result = rows(d)['beneficial']
    assert result['global_direction'] == 'POSITIVE'
    assert result['local_direction'] == 'UNAVAILABLE'
    assert result['local_complete'] == 0
    fail(data, lambda d: d['trial_pairs'][0]['candidate']['feedback'][0].update(status='ABSTAIN',score=0,reason='abstain'))


def test_missing_global_pairs_not_imputed(data):
    d = deepcopy(data)
    for pair in d['trial_pairs']:
        if pair['context_id'] == 'beneficial':
            pair['candidate']['global_score'] = None
    result = rows(d)['beneficial']
    assert result['decision'] == 'GLOBAL_UNAVAILABLE'


def test_insufficient_independent_trials_is_not_a_success(data):
    d = deepcopy(data)
    d['trial_pairs'] = [q for q in d['trial_pairs'] if q['context_id'] != 'beneficial' or q['seed'] < 6]
    assert rows(d)['beneficial']['decision'] == 'GLOBAL_UNAVAILABLE'


def test_cost_weight_and_resource_caps(data):
    fail(data, lambda d: d['policy']['cost_weights'].update(operations=-1.0))
    fail(data, lambda d: d['policy'].update(max_cost_per_arm=1))
    fail(data, lambda d: d['policy'].update(max_mean_extra_cost=-1))
    fail(data, lambda d: d['policy'].update(max_pairs=1))


def test_undisclosed_metric_policy_or_context_denied(data):
    fail(data, lambda d: d['policy'].update(global_metric_policy_sha256='bad'))
    fail(data, lambda d: d['contexts'][0].update(pre_treatment_features_sha256='bad'))
    fail(data, lambda d: d.update(topology_sha256='bad'))


def test_no_cross_context_pooling(data):
    out = rows(data)
    assert out['beneficial']['decision'] == 'EVIDENCE_FOR_FURTHER_VERIFICATION'
    assert out['consensus-trap']['decision'] == 'LOCAL_GLOBAL_CONFLICT'
    assert len(out) == len(data['contexts'])


def test_inconsistent_raw_receiver_magnitudes_do_not_overweight_receiver(data):
    d = deepcopy(data)
    for pair in d['trial_pairs']:
        if pair['context_id'] == 'beneficial':
            for fb in pair['candidate']['feedback']:
                fb['score'] = 0.001 if fb['observer'] != 'N3' else -0.999
    r = rows(d)['beneficial']
    assert r['local_direction'] == 'POSITIVE'  # 2 distinct receivers vs 1
    assert r['decision'] == 'EVIDENCE_FOR_FURTHER_VERIFICATION'


def test_optional_global_score_may_be_absent_but_schema_not_missing(data):
    fail(data, lambda d: d['trial_pairs'][0]['baseline'].pop('global_score'))


def test_no_hidden_approval_fields(data):
    fail(data, lambda d: d.update(promoted=True))
    fail(data, lambda d: d['trial_pairs'][0].update(approved=True))
