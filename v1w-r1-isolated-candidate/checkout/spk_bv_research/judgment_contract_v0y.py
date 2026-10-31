"""BV v0y RESEARCH: strict, non-acting temporal judgment contract.

A semantic validation layer only. Nothing here generates native judgments,
changes a neuron, credits a cause, or certifies independent observers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re

SCHEMA = 'spk-bv-shadow-judgment-ledger/v0y'
STATUS = 'SHADOW_ONLY_NO_APPLIED_UPDATE'
OUTPUT_SCHEMA = 'spk-bv-judgment-contract-attestation/v0y'
OUTPUT_STATUS = 'FORMAL_CONTRACT_ONLY_NO_NATIVE_JUDGMENTS_OR_LEARNING'
IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_.:-]{0,127}$', re.ASCII)
HEX = re.compile(r'^[0-9a-f]{64}$', re.ASCII)
TOP_FIELDS = {'schema','status','criteria','decisions','judgments','proposals'}
CRITERION_FIELDS = {'criterion_id','objective_id','evaluator_id','registered_tick','direction'}
DECISION_FIELDS = {'decision_id','neuron_id','episode_id','decision_tick','predecision_state_sha256','context_sha256','admissible_operators','chosen_operator'}
JUDGMENT_FIELDS = {'judgment_id','decision_id','observer_id','receiver_id','criterion_id','sign','source_evidence','causal_origin_id','produced_tick','available_tick'}
PROPOSAL_FIELDS = {'proposal_id','target_decision_id','judgment_ids','proposed_operator','created_tick','eligibility_window','verdict'}

class JudgmentContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise JudgmentContractError(message)


def exact_fields(x, fields, label):
    require(type(x) is dict and set(x) == fields, label + ': unexpected or missing fields')


def ident(x, label):
    require(type(x) is str and IDENT.fullmatch(x) is not None, label + ': invalid identifier')
    return x


def tick(x, label):
    require(type(x) is int and x >= 0, label + ': expected nonnegative integer tick')
    return x


def sha(x, label):
    require(type(x) is str and HEX.fullmatch(x) is not None, label + ': invalid SHA256')
    return x


def unique_id_list(seq, label, min_len=1):
    require(type(seq) is list and len(seq) >= min_len, label + ': invalid list')
    result = [ident(x, label) for x in seq]
    require(len(set(result)) == len(result), label + ': duplicate references')
    return result


def ledger_template():
    """Native v0e has no judgments: default is empty, never synthetic native data."""
    return {'schema':SCHEMA,'status':STATUS,'criteria':[],'decisions':[],
            'judgments':[],'proposals':[]}


def validate_ledger(x):
    """Validate shadow records and availability, but never authorize a commit.

    The declared causal_origin_id is a bookkeeping key, not proof of independent
    causal ancestry or veracity. Future decisions are deliberately not judged.
    """
    exact_fields(x, TOP_FIELDS, 'ledger')
    require(x['schema'] == SCHEMA and x['status'] == STATUS, 'not a shadow ledger')
    criteria, decisions, judgments, proposals = {}, {}, {}, {}
    for category in ('criteria','decisions','judgments','proposals'):
        require(type(x[category]) is list, category + ': expected list')
    for c in x['criteria']:
        exact_fields(c, CRITERION_FIELDS,'criterion')
        k=ident(c['criterion_id'],'criterion_id')
        require(k not in criteria, 'duplicate criterion_id')
        ident(c['objective_id'],'objective_id'); ident(c['evaluator_id'],'evaluator_id')
        tick(c['registered_tick'],'registered_tick')
        require(c['direction'] in ('maximize','minimize') and type(c['direction']) is str,
                'unknown direction')
        criteria[k]=c
    for d in x['decisions']:
        exact_fields(d, DECISION_FIELDS,'decision')
        k=ident(d['decision_id'],'decision_id')
        require(k not in decisions,'duplicate decision_id')
        ident(d['neuron_id'],'neuron_id');ident(d['episode_id'],'episode_id')
        tick(d['decision_tick'],'decision_tick')
        sha(d['predecision_state_sha256'],'predecision_state_sha256')
        sha(d['context_sha256'],'context_sha256')
        ops=unique_id_list(d['admissible_operators'],'admissible_operators')
        require(ident(d['chosen_operator'],'chosen_operator') in ops,
                'chosen operator is not admitted')
        decisions[k]=d
    origin_groups=defaultdict(list)
    for j in x['judgments']:
        exact_fields(j,JUDGMENT_FIELDS,'judgment')
        k=ident(j['judgment_id'],'judgment_id')
        require(k not in judgments,'duplicate judgment_id')
        dk=ident(j['decision_id'],'decision_id')
        require(dk in decisions,'judgment references unknown decision')
        d=decisions[dk]
        cid=ident(j['criterion_id'],'criterion_id')
        require(cid in criteria,'judgment references unknown criterion')
        require(criteria[cid]['registered_tick']<d['decision_tick'],
                'criterion was not predeclared before decision')
        observer=ident(j['observer_id'],'observer_id')
        require(observer != d['neuron_id'], 'self-judgment not a neighbor judgment')
        require(ident(j['receiver_id'],'receiver_id')==d['neuron_id'],
                'judgment receiver is not decision neuron')
        require(type(j['sign']) is int and j['sign'] in (-1,0,1),
                'sign must be nominal -1,0,+1, not utility or score')
        unique_id_list(j['source_evidence'],'source_evidence')
        origin=ident(j['causal_origin_id'],'causal_origin_id')
        produced=tick(j['produced_tick'],'produced_tick')
        available=tick(j['available_tick'],'available_tick')
        require(produced > d['decision_tick'] and available>=produced,
                'noncausal or backdated judgment')
        judgments[k]=j
        origin_groups[(dk,cid,origin)].append(j)
    # A lineage may reach multiple observers; it is not independent votes.
    # Contradictory signs from the same declared causal origin fail closed.
    for key, group in origin_groups.items():
        require(len({j['sign'] for j in group})==1,
                'same declared causal origin has conflicting judgment signs')
    for p in x['proposals']:
        exact_fields(p,PROPOSAL_FIELDS,'proposal')
        k=ident(p['proposal_id'],'proposal_id')
        require(k not in proposals,'duplicate proposal_id')
        dk=ident(p['target_decision_id'],'target_decision_id')
        require(dk in decisions,'proposal references unknown decision')
        d=decisions[dk]
        ids=unique_id_list(p['judgment_ids'],'judgment_ids')
        require(all(jid in judgments for jid in ids),'proposal references unknown judgment')
        require(all(judgments[jid]['decision_id']==dk for jid in ids),
                'proposal mixes decisions')
        require(ident(p['proposed_operator'],'proposed_operator') in d['admissible_operators'],
                'proposed operator outside admissible set')
        at=tick(p['created_tick'],'created_tick')
        w=p['eligibility_window']
        require(type(w) is list and len(w)==2,'eligibility window must be [start,end]')
        start,end=tick(w[0],'window start'),tick(w[1],'window end')
        require(d['decision_tick'] < start <= at <= end,
                'proposal outside post-decision eligibility window')
        require(all(judgments[jid]['available_tick'] <= at and
                    judgments[jid]['available_tick'] <= start for jid in ids),
                'proposal uses feedback unavailable at eligibility start')
        require(p['verdict']=='noop' and type(p['verdict']) is str,
                'v0y forbids commit, apply, and learned updates')
        proposals[k]=p
    repeated_origins=sum(len(v)>1 for v in origin_groups.values())
    return {
        'criteria_declared':len(criteria), 'decisions_declared':len(decisions),
        'judgments_declared_shadow_only':len(judgments),
        'proposals_noop_only':len(proposals),
        'declared_causal_origin_groups':len(origin_groups),
        'declared_origin_groups_with_multiple_records':repeated_origins,
        'claimed_independent_votes':0,
        'applied_updates':0,'native_judgments_observed':0,
        'information_benefit_identified':False,
        'decision_operator_change_observed':False,
    }


def verify_cost_anchor(x, w, summarize):
    """Recompute entire v0x summary from v0w and compare exactly.

    Reexecution and cross-process statements remain those of the supplied v0x
    report; this function never reexecutes the native simulator itself.
    """
    require(type(x) is dict and type(w) is dict, 'cost anchor inputs must be objects')
    require(x.get('schema')=='spk-bv-workload-value-observability-boundary/v0x',
            'wrong v0x schema')
    require(x.get('status')=='SOURCE_RECOMPUTED_COST_ONLY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION',
            'v0x was not natively recomputed')
    require(x.get('native_workloads_reexecuted_and_equal') is True and
            x.get('source_sha256_reverified') is True,
            'native cost evidence not source recomputed')
    require(type(x.get('cross_process_payload_equality_verified')) is bool,
            'cross-process evidence flag must be boolean')
    expected=summarize(w)
    if type(expected) is not dict:
        raise JudgmentContractError('invalid reconstructed v0x summary')
    actual=dict(x)
    for name in ('source_sha256_reverified','native_workloads_reexecuted_and_equal',
                 'cross_process_payload_equality_verified'):
        actual.pop(name,None)
    actual['status']=expected['status']
    require(actual==expected,'v0x report does not reproduce from v0w fixture')
    return {
        'native_cells':x['native_cells'],
        'native_arms_reexecuted':x['native_arms_examined'],
        'feedback_first_positive_delay_cells':x['feedback_first_positive_delay_cells'],
        'forward_conserved_cells':x['forward_outcome_conservation_cells'],
        'cross_process_equality_verified':x['cross_process_payload_equality_verified'] is True,
        'source_hashes':x['input_source_sha256'],
        'fixture_sha256':x['input_fixture_sha256'],
    }
