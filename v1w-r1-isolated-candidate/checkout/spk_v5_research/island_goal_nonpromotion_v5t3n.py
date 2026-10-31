"""V5-T3n explicit no-promotion interpretation of T3l+T3m evidence.

No invented credentials: SHA pins are local integrity only; an externally
independent outcome oracle, sensor source authority and native RL are absent.
"""
from __future__ import annotations
from pathlib import Path
from spk_v5_research.island_goal_identifiability_v5t3l import paired_worlds
from spk_v5_research.island_goal_audit_v5t3m import public_audit

SCHEMA='spk-v5-t3lmn-proxy-goal-identifiability-and-no-promotion/research-v0'
SEEDS=(11,29,47,83)


def nonpromotion_gate(pairs, public):
    if type(pairs) is not list or len(pairs)!=len(SEEDS) or any(type(p) is not dict for p in pairs):
        raise ValueError('missing independent paired-world evidence')
    if type(public) is not dict or len(public.get('files',[]))!=3 or public.get('blind') is True:
        raise ValueError('missing three original public audits')
    for seed,p in zip(SEEDS,pairs):
        if p.get('seed')!=seed or p.get('status')!='INDISTINGUISHABLE_FEEDBACK_OPPOSITE_OBJECTIVE':
            raise ValueError('invalid paired-world witness')
        x,y=p['aligned_world'],p['inverted_world']
        if any(x[k]!=y[k] for k in ('A_action_and_C_credit_digest',
                   'A_registry_head_sha256','A_registry_weights_sha256','C_credit_updates')):
            raise ValueError('goal worlds are distinguishable to A')
        if x['correct']+y['correct']!=x['total'] or not p['goal_is_auditor_only']:
            raise ValueError('inconsistent complementary objective')
    c=public.get('pooled',{})
    if c.get('episodes',0)<300 or (c.get('misleading_positive',0)+c.get('misleading_negative',0)
                                       !=c.get('proxy_mismatch_photo',-1)):
        raise ValueError('incomplete C vs photo disagreement accounting')
    return {'decision':'RESEARCH_VALID_GOAL_ALIGNMENT_NOT_IDENTIFIABLE_FROM_C_ONLY',
       'native_learning_promotion_allowed':False,
       'blind_generalization_claim_allowed':False,
       'C_credit_genuineness_implies_goal_truth':False,
       'source_sensor_identity_authenticated':False,
       'goal_label_used_to_choose_A':False,
       'why':'paired worlds have identical A inputs and C credits yet complementary hidden goals',
       'required_next_evidence':['external goal authority independent of proxy source',
          'fresh temporally separated goal observations with custody',
          'receiver-origin end-to-end native BV and native policy-update contract']}


def report(uci_dir:Path|None=None, per_regime=120, max_pairs=1200):
    pairs=[paired_worlds(seed,per_regime,stress=True) for seed in SEEDS]
    public=public_audit(uci_dir,max_pairs) if uci_dir is not None else None
    if public is None:
        return {'schema':SCHEMA,'status':'SYNTHETIC_IDENTIFIABILITY_ONLY_NO_PUBLIC_AUDIT',
                'paired_worlds':pairs,'public':None,'nonpromotion':None}
    decision=nonpromotion_gate(pairs,public)
    return {'schema':SCHEMA,'status':decision['decision'],'paired_worlds':pairs,
      'public':public,'nonpromotion':decision,
      'synthesis':{'worlds':2*len(pairs),'engineered_steps_per_world':per_regime*3,
                   'paired_goal_objective_not_observable_by_A':True,
                   'C_authored_credit_source_A1b_execution':True,
                   'host_owned_online_selector':True,
                   'research_only':True},
      'exclusions':['paired worlds engineered by harness; not independent physical environments',
         'public UCI already inspected and therefore not blind',
         'photographic goal used for posthoc audit only, not C, A or registry update',
         'CO2 sensor threshold and its custody implemented by host adapter',
         'hash digest not third-party signature or hardware attestation',
         'native BV receiver credit and native neuron program updates remain unimplemented',
         'observational indistinguishability result holds for the defined C-only information set']}
