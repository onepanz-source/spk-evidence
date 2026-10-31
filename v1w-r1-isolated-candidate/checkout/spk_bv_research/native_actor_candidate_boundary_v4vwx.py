"""v4v-v4x: research-only, two-episode derived actor program-choice boundary.

An ACK-derived actor credit is *evidence for a proposal*, never authority to
change a frozen neuron's program. A candidate is independently reexecuted as
an alternative episode input and vetoed on authority, signed-workload parity,
off-matrix counterexamples or lack of a genuine program change.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_paid_consumer_v4stu import (
    CausalProbeRejected, execute_paid_consumer_probe,
)
from spk_bv_research.native_ack_paid_consumer_audit_v4stu import conservation

SCHEMA = 'spk-bv-derived-actor-candidate-veto/research-v4v-v4x'
STATUS = 'ACK_CREDIT_PROPOSES_BUT_CANNOT_SELF_AUTHORIZE_COMPUTATIONAL_ADOPTION'
VARIANTS = {
    # variant -> (CMP threshold, owner authority, independent review authority)
    'owner_denied': (0, False, True),
    'reviewer_denied': (0, True, False),
    'signed_unsafe': (2, True, True),
    'holdout_unsafe': (0, True, True),
    'no_op': (1, True, True),
}


def _sha(data):
    return sha256(canon(data)).hexdigest()


def _change_cmp(case, value):
    if type(value) is not int or value not in (0, 1, 2):
        raise CausalProbeRejected('unsupported candidate threshold')
    nodes = []
    for node in case.nodes:
        if node.node_id != 'A':
            nodes.append(node)
            continue
        if (sum(op == 'CMP' for op, _ in node.instructions) != 1 or
                next(v for op, v in node.instructions if op == 'CMP') != 1):
            raise CausalProbeRejected('candidate source algorithm is not pinned')
        nodes.append(replace(node, instructions=tuple(
            (op, value if op == 'CMP' else arg)
            for op, arg in node.instructions)))
    if len(nodes) != len(case.nodes) or not any(n.node_id == 'A' for n in nodes):
        raise CausalProbeRejected('candidate source neuron unavailable')
    return replace(case, nodes=tuple(nodes))


def _challenge(case):
    """Off-matrix channel challenge: the same tick, unsupported input channel.

    The source recipes only exercise channel 0; channel 1 is a legal input
    channel for this test fixture and exposes a potential CMP=0 false output.
    """
    if not case.events or case.events[0].node_id != 'A':
        raise CausalProbeRejected('unsupported off-matrix challenge source')
    events = (replace(case.events[0], channel=1),) + case.events[1:]
    return replace(case, events=events)


def evaluate_candidate(case, fabric, tplan, pplan, mplan, lplan, bv,
                       original_paid, variant):
    if type(variant) is not str or variant not in VARIANTS:
        raise CausalProbeRejected('unsupported candidate/authority variant')
    conservation(original_paid, case, fabric, pplan, mplan)
    original = original_paid['derived_actor']
    if (original['consumer_policy'] != 'consumer-first' or
            not original['feedback_enabled'] or
            original_paid['native_learning_implemented'] is not False or
            original_paid['native_actor_credit_applied'] is not False):
        raise CausalProbeRejected('candidate lacks bounded paid-ACK source custody')
    a_receipts = [r for r in original['applied_receipts'] if r['actor'] == 'A']
    if (len(a_receipts) < 2 or any(r['response'] != 1 or
            r['owner_pe'] != 'PE0' for r in a_receipts) or
            original['applied_credit_by_actor']['A'] < 2):
        raise CausalProbeRejected('insufficient source receiver positive judgments')
    credits_digest = _sha(a_receipts)
    value, owner_allowed, reviewer_allowed = VARIANTS[variant]
    candidate_case = _change_cmp(case, value)
    base_node = next(n for n in case.nodes if n.node_id == 'A')
    candidate_node = next(n for n in candidate_case.nodes if n.node_id == 'A')
    proposal = {
        'actor':'A', 'owner_pe':'PE0', 'base_derived_program_version':0,
        'candidate_derived_program_version':1,
        'base_program_sha256':_sha(base_node.instructions),
        'candidate_program_sha256':_sha(candidate_node.instructions),
        'threshold_before':1, 'threshold_proposed':value,
        'positive_paid_ACK_receipts':len(a_receipts),
        'source_actor_credit':original['applied_credit_by_actor']['A'],
        'source_receipts_sha256':credits_digest,
        'receipts_root_A':original['receipt_roots']['A'],
        'proposal_id':_sha([variant, credits_digest,
                            candidate_node.instructions]),
    }
    # Both the source and the candidate are separately executed by the same
    # frozen native code; no module, neuron object or state is mutated in place.
    candidate_paid = execute_paid_consumer_probe(
        candidate_case, fabric, tplan, pplan, mplan, lplan, bv,
        consumer_policy='consumer-first')
    conservation(candidate_paid, candidate_case, fabric, pplan, mplan)
    signed_equal = (
        original_paid['native']['forward'] == candidate_paid['native']['forward'] and
        original_paid['native']['feedback'] == candidate_paid['native']['feedback'] and
        original_paid['derived_actor_ack'] == candidate_paid['derived_actor_ack'] and
        original_paid['derived_actor'] == candidate_paid['derived_actor'])
    old_holdout = execute_live_v0e(_challenge(case), fabric,
                                   tplan,pplan,mplan,lplan,bv)
    new_holdout = execute_live_v0e(_challenge(candidate_case), fabric,
                                   tplan,pplan,mplan,lplan,bv)
    holdout_equal = (
        old_holdout['forward']['emissions'] == new_holdout['forward']['emissions'] and
        old_holdout['forward']['terminal'] == new_holdout['forward']['terminal'])
    changed = proposal['base_program_sha256'] != proposal['candidate_program_sha256']
    if not (owner_allowed and reviewer_allowed):
        verdict = 'VETO_AUTHORITY'
    elif not signed_equal:
        verdict = 'VETO_SIGNED_SOURCE_SEMANTICS'
    elif not holdout_equal:
        verdict = 'VETO_OFF_MATRIX_COUNTEREXAMPLE'
    elif not changed:
        verdict = 'VETO_NO_OP_NOT_LEARNING'
    else:
        # Even exhaustive finite checks cannot establish global safety or
        # learning benefit. A new native learner authority contract is absent.
        verdict = 'VETO_NO_NATIVE_LEARNER_AUTHORITY'
    return {
        'schema':SCHEMA,'status':STATUS,'variant':variant,
        'proposal':proposal,
        'authority':{'owner_approval':owner_allowed,
                     'independent_reviewer_approval':reviewer_allowed,
                     'cryptographic_authentication_implemented':False},
        'counterfactual':{
            'signed_workload_exact_parity':signed_equal,
            'off_matrix_channel_challenge_parity':holdout_equal,
            'program_changed':changed,
            'source_native_forward_sha256':_sha(original_paid['native']['forward']),
            'candidate_native_forward_sha256':_sha(candidate_paid['native']['forward']),
            'source_holdout_emissions':len(old_holdout['forward']['emissions']),
            'candidate_holdout_emissions':len(new_holdout['forward']['emissions']),
            'source_holdout_terminal':len(old_holdout['forward']['terminal']),
            'candidate_holdout_terminal':len(new_holdout['forward']['terminal']),
            'candidate_paid_ACK_receipts':len(candidate_paid['derived_actor']['applied_receipts']),
        },
        'verdict':verdict,
        'committed_derived_program_version':0,
        'frozen_native_program_mutated':False,
        'native_learning_implemented':False,
    }
