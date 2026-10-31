"""v4y-v4aa: declared task objective for counterfactual actor programs.

This is a small *synthetic external task*, not an objective discovered from
positive actor ACKs. All programs are alternative *inputs* to the unmodified
v0e executor. Even an eligible repair is never committed or installed.
"""
from __future__ import annotations

from dataclasses import replace

from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e
from spk_bv_research.native_ack_paid_consumer_v4stu import (
    CausalProbeRejected, execute_paid_consumer_probe,
)
from spk_bv_research.native_actor_candidate_boundary_v4vwx import _sha

SCHEMA = 'spk-bv-external-task-objective/research-v4y-v4aa'
STATUS = 'SYNTHETIC_OBJECTIVE_SEPARATES_RECEIVER_ACK_FROM_TASK_IMPROVEMENT'
OBJECTIVE = {
    'type': 'DECLARED_SYNTHETIC_TASK_NOT_INFERRED_FROM_RECEIVER_ACK',
    'source': 'HYPOTHESIS_TEST_TWO_CHANNEL_EVENT_CLASSIFICATION',
    'target_actor': 'A',
    'probe_channels': [0, 1],
    'expected_terminal_counts': {'0': 1, '1': 0},
    'false_negative_cost': 5,
    'false_positive_cost': 4,
    'max_expected_terminal_per_probe': 1,
    'blind_external_ground_truth_available': False,
    'physical_energy_model_available': False,
}
VARIANTS = {
    # origin, original threshold, candidate threshold, owner, reviewer
    'source_overfire': ('SIGNED_SOURCE', 1, 0, True, True),
    'source_underfire': ('SIGNED_SOURCE', 1, 2, True, True),
    'source_no_op': ('SIGNED_SOURCE', 1, 1, True, True),
    'degraded_repair': ('INJECTED_DEGRADATION', 0, 1, True, True),
    'degraded_tradeoff': ('INJECTED_DEGRADATION', 0, 2, True, True),
    'degraded_owner_denied': ('INJECTED_DEGRADATION', 0, 1, False, True),
    'degraded_reviewer_denied': ('INJECTED_DEGRADATION', 0, 1, True, False),
}


def _set_cmp(case, expected, proposed):
    if any(type(v) is not int or v not in (0, 1, 2)
           for v in (expected, proposed)):
        raise CausalProbeRejected('unsupported task program threshold')
    changed = False
    nodes = []
    for node in case.nodes:
        if node.node_id != 'A':
            nodes.append(node)
            continue
        cmps = [arg for op, arg in node.instructions if op == 'CMP']
        if cmps != [expected]:
            raise CausalProbeRejected('task base algorithm not pinned')
        nodes.append(replace(node, instructions=tuple(
            (op, proposed if op == 'CMP' else arg)
            for op, arg in node.instructions)))
        changed = True
    if not changed:
        raise CausalProbeRejected('task owner node unavailable')
    return replace(case, nodes=tuple(nodes))


def _probe_case(case, channel, *, later=False):
    if (type(channel) is not int or channel not in (0, 1) or not case.events
            or case.events[0].node_id != 'A'):
        raise CausalProbeRejected('unsupported task probe')
    event = case.events[0]
    if later:
        event = replace(event, timestamp=event.timestamp + 7)
    return replace(case, events=(replace(event, channel=channel),))


def _score(case, fabric, plans, bv, *, later=False):
    evidence = []
    false_negative = false_positive = 0
    for channel in OBJECTIVE['probe_channels']:
        probe = _probe_case(case, channel, later=later)
        executed = execute_live_v0e(probe, fabric, *plans, bv)
        terminal = executed['forward']['terminal']
        count = len(terminal)
        if count > OBJECTIVE['max_expected_terminal_per_probe']:
            raise CausalProbeRejected('unbounded task terminal multiplicity')
        expected = OBJECTIVE['expected_terminal_counts'][str(channel)]
        false_negative += max(expected-count, 0)
        false_positive += max(count-expected, 0)
        evidence.append({
            'channel': channel, 'expected': expected, 'observed': count,
            'terminal_sha256': _sha(terminal),
            'forward_sha256': _sha(executed['forward']),
        })
    return {
        'false_negative': false_negative,
        'false_positive': false_positive,
        'declared_cost': (false_negative*OBJECTIVE['false_negative_cost']
                          + false_positive*OBJECTIVE['false_positive_cost']),
        'probe_evidence': evidence,
    }


def evaluate_objective(case, fabric, plans, bv, variant):
    if type(variant) is not str or variant not in VARIANTS:
        raise CausalProbeRejected('unsupported objective experiment variant')
    origin, base_threshold, candidate_threshold, owner, reviewer = VARIANTS[variant]
    if not any(n.node_id == 'A' for n in case.nodes):
        raise CausalProbeRejected('source owner unavailable')
    original_source = next(n for n in case.nodes if n.node_id == 'A')
    if [arg for op, arg in original_source.instructions if op == 'CMP'] != [1]:
        raise CausalProbeRejected('original signed program changed')
    base = _set_cmp(case, 1, base_threshold)
    candidate = _set_cmp(base, base_threshold, candidate_threshold)
    a = next(n for n in base.nodes if n.node_id == 'A')
    b = next(n for n in candidate.nodes if n.node_id == 'A')

    old_score = _score(base, fabric, plans, bv)
    new_score = _score(candidate, fabric, plans, bv)
    old_later = _score(base, fabric, plans, bv, later=True)
    new_later = _score(candidate, fabric, plans, bv, later=True)
    improvement = old_score['declared_cost']-new_score['declared_cost']
    changed = a.instructions != b.instructions
    no_component_regression = (
        new_score['false_negative'] <= old_score['false_negative'] and
        new_score['false_positive'] <= old_score['false_positive'])
    later_consistent = (
        old_score['declared_cost'] == old_later['declared_cost'] and
        new_score['declared_cost'] == new_later['declared_cost'])
    if not owner or not reviewer:
        verdict = 'VETO_UNAUTHENTICATED_RESEARCH_AUTHORITY'
    elif not changed:
        verdict = 'VETO_NO_OP'
    elif improvement <= 0:
        verdict = 'VETO_NO_OBJECTIVE_IMPROVEMENT'
    elif not no_component_regression:
        verdict = 'VETO_COMPONENT_REGRESSION'
    elif not later_consistent:
        verdict = 'VETO_TEMPORAL_CHALLENGE'
    else:
        verdict = 'ELIGIBLE_SHADOW_TRIAL_NOT_ADOPTED'

    # In the overfiring negative-label case, the receiver still computes and
    # returns a *positive* paid ACK. Its sign is not a task truth label.
    misleading_feedback = execute_paid_consumer_probe(
        _probe_case(base, 1), fabric, *plans, bv,
        consumer_policy='consumer-first')
    positive_receipts = [r for r in misleading_feedback['derived_actor']['applied_receipts']
                         if r['actor'] == 'A' and r['response'] == 1]
    if base_threshold == 0 and len(positive_receipts) != 1:
        raise CausalProbeRejected('positive task-wrong receiver evidence unavailable')
    if base_threshold == 1 and positive_receipts:
        raise CausalProbeRejected('fabricated signed source feedback')

    return {
        'schema': SCHEMA, 'status': STATUS, 'variant': variant, 'origin': origin,
        'task_contract_sha256': _sha(OBJECTIVE),
        'program': {
            'owner_node': 'A', 'base_derived_version': 0,
            'proposed_derived_version': 1,
            'base_threshold': base_threshold, 'candidate_threshold': candidate_threshold,
            'base_program_sha256': _sha(a.instructions),
            'candidate_program_sha256': _sha(b.instructions),
            'changed': changed,
        },
        'owner_approval': owner, 'reviewer_approval': reviewer,
        'old_task_score': old_score, 'new_task_score': new_score,
        'old_temporal_challenge': old_later, 'new_temporal_challenge': new_later,
        'objective_cost_improvement': improvement,
        'no_component_regression': no_component_regression,
        'temporal_challenge_consistent': later_consistent,
        'negative_task_label_positive_paid_ACKs': len(positive_receipts),
        'negative_task_label_paid_receipts_sha256': _sha(positive_receipts),
        'verdict': verdict,
        'committed_derived_program_version': 0,
        'native_learning_implemented': False,
        'frozen_native_program_mutated': False,
    }
