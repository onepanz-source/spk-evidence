"""Independent task-label, receiver-ACK and custody audit for v4y-v4aa."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.grant_rank_integration_v3tuv import ARMS, CAPACITIES, NEW_SCHEDULES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.native_ack_paid_consumer_v4stu import execute_paid_consumer_probe
from spk_bv_research.native_actor_candidate_boundary_v4vwx import _sha
from spk_bv_research.native_actor_objective_v4yzaa import (
    SCHEMA, STATUS, OBJECTIVE, VARIANTS, _set_cmp, _probe_case, evaluate_objective,
)
from spk_bv_research.off_on_v0t import snapshot

SIGNED_V3_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4VWX_SHA = '6451c65cc13cd1cb926f89547e25faa8871f69c09479bb16e320cf6e86a6492a'


def require(value, message):
    if not value:
        raise CausalProbeRejected(message)


def audit_objective(row, case, fabric, plans, bv):
    """Use direct executor observations, independently calculate the declared loss.

    This audits fixture consistency, not authenticity of the synthetic labels
    or mathematical soundness of the task specification outside this fixture.
    """
    require(type(row) is dict and row.get('variant') in VARIANTS,
            'objective audit unsupported variant')
    origin, base_t, proposed_t, owner, reviewer = VARIANTS[row['variant']]
    baseline = _set_cmp(case, 1, base_t)
    candidate = _set_cmp(baseline, base_t, proposed_t)
    def independent_score(current, *, late):
        fp = fn = 0
        proofs = []
        for channel, expectation in ((0, 1), (1, 0)):
            run = execute_live_v0e(_probe_case(current, channel, later=late),
                                  fabric, *plans, bv)
            observed = len(run['forward']['terminal'])
            require(observed in (0, 1), 'task classifier produced multiple terminals')
            fp += max(observed - expectation, 0)
            fn += max(expectation - observed, 0)
            proofs.append({'channel':channel, 'expected':expectation,
                           'observed':observed,
                           'terminal_sha256':_sha(run['forward']['terminal']),
                           'forward_sha256':_sha(run['forward'])})
        return {'false_negative':fn,'false_positive':fp,
                'declared_cost':5*fn+4*fp,'probe_evidence':proofs}

    old = independent_score(baseline, late=False)
    new = independent_score(candidate, late=False)
    late_old = independent_score(baseline, late=True)
    late_new = independent_score(candidate, late=True)
    advantage = old['declared_cost'] - new['declared_cost']
    pareto = new['false_negative'] <= old['false_negative'] and new['false_positive'] <= old['false_positive']
    stable = (old['declared_cost'] == late_old['declared_cost'] and
              new['declared_cost'] == late_new['declared_cost'])
    changed = base_t != proposed_t
    expected = ('VETO_UNAUTHENTICATED_RESEARCH_AUTHORITY' if not(owner and reviewer)
                else 'VETO_NO_OP' if not changed
                else 'VETO_NO_OBJECTIVE_IMPROVEMENT' if advantage <= 0
                else 'VETO_COMPONENT_REGRESSION' if not pareto
                else 'VETO_TEMPORAL_CHALLENGE' if not stable
                else 'ELIGIBLE_SHADOW_TRIAL_NOT_ADOPTED')
    paid = execute_paid_consumer_probe(_probe_case(baseline, 1), fabric,
                                       *plans, bv, consumer_policy='consumer-first')
    receipts = [r for r in paid['derived_actor']['applied_receipts']
                if r['actor']=='A' and r['response']==1]
    a = next(n for n in baseline.nodes if n.node_id=='A')
    b = next(n for n in candidate.nodes if n.node_id=='A')
    require(row['schema']==SCHEMA and row['status']==STATUS and row['origin']==origin and
            row['task_contract_sha256']==_sha(OBJECTIVE) and
            row['program']=={'owner_node':'A','base_derived_version':0,
                             'proposed_derived_version':1,
                             'base_threshold':base_t,'candidate_threshold':proposed_t,
                             'base_program_sha256':_sha(a.instructions),
                             'candidate_program_sha256':_sha(b.instructions),
                             'changed':changed} and
            row['owner_approval'] is owner and row['reviewer_approval'] is reviewer and
            row['old_task_score']==old and row['new_task_score']==new and
            row['old_temporal_challenge']==late_old and
            row['new_temporal_challenge']==late_new and
            row['objective_cost_improvement']==advantage and
            row['no_component_regression']==pareto and
            row['temporal_challenge_consistent']==stable and
            row['negative_task_label_positive_paid_ACKs']==len(receipts) and
            row['negative_task_label_paid_receipts_sha256']==_sha(receipts) and
            row['verdict']==expected and
            row['committed_derived_program_version']==0 and
            row['frozen_native_program_mutated'] is False and
            row['native_learning_implemented'] is False,
            'objective independent audit rejected evidence, decision or adoption')
    require((base_t == 0 and len(receipts)==1) or
            (base_t != 0 and len(receipts)==0),
            'signed false-task-positive ACK did not reproduce')


def evaluate(v3, raw3, v4vwx, raw4, *, fixture_fn=fixture,
             native_executor=execute_live_v0e):
    require(type(v3) is dict and type(v4vwx) is dict and
            type(raw3) is bytes and type(raw4) is bytes and
            canon(v3)==raw3 and canon(v4vwx)==raw4 and
            sha256(raw3).hexdigest()==SIGNED_V3_SHA and
            sha256(raw4).hexdigest()==SIGNED_V4VWX_SHA and
            v4vwx.get('signed_v3tuv_sha256')==SIGNED_V3_SHA and
            v4vwx['totals']['native_source_replays']==18 and
            v4vwx['totals']['candidate_shadow_episodes']==90 and
            v4vwx['applied_native_learning_updates']==0 and
            v4vwx['adopted_derived_algorithm_updates']==0,
            'objective signed predecessor custody mismatch')
    totals = Counter()
    rows = []
    signed_rows = 0
    for signed,(schedule,ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(signed['schedule']==schedule and
                signed['source_external_ticks']==list(ticks),
                'objective native schedule mismatch')
        case,fabric,plans=fixture_fn(ticks=ticks)
        for arm,(mode,enabled,priority) in zip(signed['modes'],ARMS):
            require(arm['mode']==mode, 'objective native arm mismatch')
            for entry,cap in zip(arm['capacities'],CAPACITIES):
                require(entry['native_PE_capacity']==cap,
                        'objective signed PE capacity mismatch')
                pp=replace(plans[1],fabric_slots_per_tick=cap)
                active=(plans[0],pp,plans[2],plans[3])
                bv=LiveBVPlanV0e(enabled=enabled,priority=priority)
                original=native_executor(case,fabric,*active,bv)
                require(snapshot(original)==entry['original_native_sha256'],
                        'objective original native executor drift')
                totals['signed_native_replays']+=1
                for variant in VARIANTS:
                    result=evaluate_objective(case,fabric,active,bv,variant)
                    audit_objective(result,case,fabric,active,bv)
                    totals['counterfactual_objective_trials']+=1
                    totals['verdict_'+result['verdict']]+=1
                    totals['positive_misleading_ACKs']+=result['negative_task_label_positive_paid_ACKs']
                    rows.append({'schedule':schedule,'mode':mode,
                                 'native_global_PE_capacity':cap,
                                 'result':result})
                signed_rows+=1
    require(len(v3['source_matrix'])==3 and signed_rows==18 and
            totals['signed_native_replays']==18 and
            totals['counterfactual_objective_trials']==126 and
            totals['verdict_ELIGIBLE_SHADOW_TRIAL_NOT_ADOPTED']==18 and
            totals['verdict_VETO_UNAUTHENTICATED_RESEARCH_AUTHORITY']==36 and
            totals['verdict_VETO_NO_OBJECTIVE_IMPROVEMENT']==54 and
            totals['verdict_VETO_NO_OP']==18 and
            totals['positive_misleading_ACKs']==72,
            'objective complete signed matrix incomplete')
    return {
        'schema':SCHEMA, 'status':STATUS,
        'signed_v3tuv_sha256':sha256(raw3).hexdigest(),
        'signed_v4vwx_sha256':sha256(raw4).hexdigest(),
        'external_objective':OBJECTIVE,
        'external_objective_sha256':_sha(OBJECTIVE),
        'source_native':'UNMODIFIED_PINNED_V0E',
        'source_evidence':'PINNED_V3TUV_AND_V4VWX',
        'correction_positive_control':'INTENTIONALLY_INJECTED_SHADOW_DEGRADATION_ONLY',
        'authority_model':'RESEARCH_FLAGS_NOT_AUTHENTICATION',
        'tested_variants':list(VARIANTS),
        'totals':dict(sorted(totals.items())),
        'scenarios':rows,
        'shadow_trial_eligibility_count':18,
        'actual_shadow_adoptions':0,
        'native_learning_implemented':False,
        'frozen_native_modified':False,
        'architecture_v1_modified':False,
        'claims_excluded':[
            'synthetic externally declared labels are not independent domain truth',
            'positive receiver ACK is not proof of desirable terminal behavior',
            'objective performance is demonstrated only for two channels and tested schedules',
            'candidate eligibility is neither installed native learning nor a program version commit',
            'boolean authority approvals are not cryptographically authenticated identities',
            'abstract service units are not measured energy or silicon timing',
        ],
        'next_gate':'INDEPENDENT_TASK_ORACLE_AND_PROVENANCE_BEFORE_OPTIMIZATION_OR_COMMIT',
    }
