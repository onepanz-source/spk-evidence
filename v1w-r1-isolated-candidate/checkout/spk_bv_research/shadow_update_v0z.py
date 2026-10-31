"""SPK/* BV v0z RESEARCH: prospective-only, non-acting operator-hypothesis contract.

Never create native judgments, issue commits, or infer improvement. The paired
input/budget hashes are *declarations*, not observed run or equality evidence.
"""
from __future__ import annotations

from collections import Counter
from spk_bv_research.judgment_contract_v0y import (
    JudgmentContractError, ident, tick, sha, validate_ledger,
)

SCHEMA='spk-bv-shadow-update-hypotheses/v0z'
STATUS='PURE_SHADOW_HYPOTHESES_NO_COMMIT'
OUTPUT_SCHEMA='spk-bv-shadow-update-admissibility-attestation/v0z'
OUTPUT_STATUS='PROSPECTIVE_FORMAL_ADMISSIBILITY_ONLY_NO_LEARNING'
FIELDS={'schema','status','hypotheses'}
HYP_FIELDS={
    'hypothesis_id','proposal_id','criterion_id','planning_tick',
    'future_episode_id','holdout_start_tick','holdout_end_tick',
    'baseline_operator','candidate_operator','max_local_changes',
    'control_input_sha256','candidate_input_sha256',
    'control_budget_sha256','candidate_budget_sha256',
    'evaluation_objective_id','evaluation_evaluator_id',
    'evaluation_mode',
}

def need(b,message):
    if not b: raise JudgmentContractError(message)

def template():
    return {'schema':SCHEMA,'status':STATUS,'hypotheses':[]}

def validate_hypotheses(plan, ledger):
    """Validate prospective hypotheses; never mutate either input.

    Eligibility checks imply only syntactic/temporal hypothetical admission,
    not executable semantics, truth, causal independence, or measured benefit.
    """
    validate_ledger(ledger)
    need(type(plan) is dict and set(plan)==FIELDS, 'invalid hypothesis envelope fields')
    need(plan['schema']==SCHEMA and plan['status']==STATUS,'invalid shadow hypothesis envelope')
    need(type(plan['hypotheses']) is list,'hypotheses must be list')
    dmap={d['decision_id']:d for d in ledger['decisions']}
    pmap={p['proposal_id']:p for p in ledger['proposals']}
    jmap={j['judgment_id']:j for j in ledger['judgments']}
    cmap={c['criterion_id']:c for c in ledger['criteria']}
    results=[];hid_seen=set();target_seen=set();future_seen=set()
    for h in plan['hypotheses']:
        need(type(h) is dict and set(h)==HYP_FIELDS,'invalid hypothesis fields')
        hid=ident(h['hypothesis_id'],'hypothesis_id')
        need(hid not in hid_seen,'duplicate hypothesis ID');hid_seen.add(hid)
        pid=ident(h['proposal_id'],'proposal_id')
        need(pid in pmap,'unknown proposal');p=pmap[pid]
        did=p['target_decision_id'];d=dmap[did]
        need(did not in target_seen, 'multiple hypotheses for one decision')
        target_seen.add(did)
        cid=ident(h['criterion_id'],'criterion_id')
        need(cid in cmap,'unknown criterion')
        c=cmap[cid]
        need(all(jmap[j]['criterion_id']==cid for j in p['judgment_ids']),
             'mixed or unrelated criteria')
        need(c['registered_tick']<d['decision_tick'],'criterion not preregistered')
        baseline=ident(h['baseline_operator'],'baseline_operator')
        candidate=ident(h['candidate_operator'],'candidate_operator')
        need(baseline==d['chosen_operator'],'baseline not decision operator')
        need(candidate==p['proposed_operator'] and candidate in d['admissible_operators'],
             'candidate not proposal/admissible operator')
        need(candidate!=baseline,'candidate must differ from baseline')
        need(type(h['max_local_changes']) is int and h['max_local_changes']==1,
             'shadow bound must be exactly one discrete local operator choice')
        at=tick(h['planning_tick'],'planning_tick')
        lo,hi=p['eligibility_window']
        need(lo<=at<=hi and at>=p['created_tick'],
             'planning outside proposal eligibility window')
        need(all(jmap[j]['available_tick']<=at for j in p['judgment_ids']),
             'judgment not available at planning')
        episode=ident(h['future_episode_id'],'future_episode_id')
        need(episode!=d['episode_id'],'holdout is not a future episode')
        # Same neuron+future episode cannot receive separate competing plans.
        future_key=(d['neuron_id'],episode)
        need(future_key not in future_seen,'multiple plans for same neuron/episode')
        future_seen.add(future_key)
        start=tick(h['holdout_start_tick'],'holdout_start_tick')
        end=tick(h['holdout_end_tick'],'holdout_end_tick')
        need(at<start<=end,'future-only holdout window violated')
        for name in ('control_input_sha256','candidate_input_sha256',
                     'control_budget_sha256','candidate_budget_sha256'):
            sha(h[name],name)
        need(h['control_input_sha256']==h['candidate_input_sha256'],
             'declared paired inputs differ')
        need(h['control_budget_sha256']==h['candidate_budget_sha256'],
             'declared paired budgets differ')
        need(ident(h['evaluation_objective_id'],'evaluation_objective_id')==c['objective_id']
             and ident(h['evaluation_evaluator_id'],'evaluation_evaluator_id')==c['evaluator_id'],
             'evaluation criterion not identical to preregistration')
        need(type(h['evaluation_mode']) is str and
             h['evaluation_mode']=='declared-paired-external-holdout',
             'external held-out evaluation protocol required')
        origins={jmap[j]['causal_origin_id'] for j in p['judgment_ids']}
        results.append({
            'hypothesis_id':hid,'target_decision_id':did,'proposal_id':pid,
            'criterion_id':cid,'baseline_operator':baseline,
            'candidate_operator':candidate,
            'judgments_referenced':len(p['judgment_ids']),
            'declared_origin_groups':len(origins),
            'candidate_changes_from_baseline':1,
            'planning_tick':at,'holdout_start_tick':start,
            'holdout_end_tick':end,'future_episode_id':episode,
            'declared_paired_input_sha256':h['control_input_sha256'],
            'declared_paired_budget_sha256':h['control_budget_sha256'],
            'paired_input_or_budget_proven_by_runtime':False,
            'scores_observed':0,'commit_applied':False,
        })
    return {
        'hypotheses_admitted_shadow_only':len(results),
        'distinct_decisions_targeted':len(target_seen),
        'plans':results,
        'applied_updates':0,'observed_native_judgments':0,
        'external_evaluations_completed':0,
        'independent_causal_votes_proven':0,
        'informativeness_or_improvement_identified':False,
    }
