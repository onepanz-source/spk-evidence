"""Source-signed audit of feedback-conditioned next-episode candidate vetoes."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.grant_rank_integration_v3tuv import ARMS, CAPACITIES, NEW_SCHEDULES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.native_ack_paid_consumer_v4stu import (
    CausalProbeRejected, execute_paid_consumer_probe,
)
from spk_bv_research.native_ack_paid_consumer_audit_v4stu import conservation
from spk_bv_research.native_actor_candidate_boundary_v4vwx import (
    SCHEMA,STATUS,VARIANTS,_change_cmp,_challenge,_sha,evaluate_candidate,
)

SIGNED_V3TUV_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4STU_SHA = 'ba0396540e3347114c27a9c26af69b12741f2cf86cc1a8845fca60ffccb0b20c'


def require(ok,why):
    if not ok:
        raise CausalProbeRejected(why)


def audit_candidate(result, case, fabric, plans, bv, source):
    """Rebuild candidate, signed comparison and OOD challenge independently."""
    variant=result['variant']
    require(variant in VARIANTS,'candidate audit invalid scenario')
    threshold,owner,reviewer=VARIANTS[variant]
    prop=result['proposal']
    real_a=next(n for n in case.nodes if n.node_id=='A')
    candidate=_change_cmp(case,threshold)
    new_a=next(n for n in candidate.nodes if n.node_id=='A')
    a_receipts=[x for x in source['derived_actor']['applied_receipts']
                if x['actor']=='A']
    require(prop['actor']=='A' and prop['owner_pe']=='PE0' and
            prop['base_derived_program_version']==0 and
            prop['candidate_derived_program_version']==1 and
            prop['base_program_sha256']==_sha(real_a.instructions) and
            prop['candidate_program_sha256']==_sha(new_a.instructions) and
            prop['threshold_before']==1 and prop['threshold_proposed']==threshold and
            prop['positive_paid_ACK_receipts']==len(a_receipts) and
            prop['source_actor_credit']==source['derived_actor']['applied_credit_by_actor']['A'] and
            prop['source_receipts_sha256']==_sha(a_receipts) and
            prop['receipts_root_A']==source['derived_actor']['receipt_roots']['A'] and
            prop['proposal_id']==_sha([variant,_sha(a_receipts),new_a.instructions]),
            'candidate typed proposal or ACK evidence forged')
    approvals=result['authority']
    require(approvals=={'owner_approval':owner,
                        'independent_reviewer_approval':reviewer,
                        'cryptographic_authentication_implemented':False},
            'candidate authority forged')
    # Audit recomputes the candidate from an independently constructed case
    # and explicitly re-executes native transport and paid actor consumption.
    cpaid=execute_paid_consumer_probe(candidate,fabric,*plans,bv,
                                      consumer_policy='consumer-first')
    conservation(cpaid,candidate,fabric,plans[1],plans[2])
    signed_equal=(source['native']['forward']==cpaid['native']['forward'] and
                  source['native']['feedback']==cpaid['native']['feedback'] and
                  source['derived_actor_ack']==cpaid['derived_actor_ack'] and
                  source['derived_actor']==cpaid['derived_actor'])
    old=execute_live_v0e(_challenge(case),fabric,*plans,bv)
    new=execute_live_v0e(_challenge(candidate),fabric,*plans,bv)
    holdout_equal=(old['forward']['emissions']==new['forward']['emissions'] and
                   old['forward']['terminal']==new['forward']['terminal'])
    cf=result['counterfactual']
    require(cf['signed_workload_exact_parity']==signed_equal and
            cf['off_matrix_channel_challenge_parity']==holdout_equal and
            cf['program_changed']==(threshold!=1) and
            cf['source_native_forward_sha256']==_sha(source['native']['forward']) and
            cf['candidate_native_forward_sha256']==_sha(cpaid['native']['forward']) and
            cf['source_holdout_emissions']==len(old['forward']['emissions']) and
            cf['candidate_holdout_emissions']==len(new['forward']['emissions']) and
            cf['source_holdout_terminal']==len(old['forward']['terminal']) and
            cf['candidate_holdout_terminal']==len(new['forward']['terminal']) and
            cf['candidate_paid_ACK_receipts']==len(cpaid['derived_actor']['applied_receipts']),
            'candidate episode native parity or counterexample witness forged')
    expected = ('VETO_AUTHORITY' if not owner or not reviewer else
                'VETO_SIGNED_SOURCE_SEMANTICS' if not signed_equal else
                'VETO_OFF_MATRIX_COUNTEREXAMPLE' if not holdout_equal else
                'VETO_NO_OP_NOT_LEARNING' if threshold==1 else
                'VETO_NO_NATIVE_LEARNER_AUTHORITY')
    require(result['schema']==SCHEMA and result['status']==STATUS and
            result['verdict']==expected and
            result['committed_derived_program_version']==0 and
            result['frozen_native_program_mutated'] is False and
            result['native_learning_implemented'] is False,
            'candidate claimed unsupported learning/adoption')


def evaluate(v3,raw3,v4stu,raw4stu,*,fixture_fn=fixture,
             native_executor=execute_live_v0e,
             paid_executor=execute_paid_consumer_probe):
    require(type(v3) is dict and type(raw3) is bytes and
            canon(v3)==raw3 and sha256(raw3).hexdigest()==SIGNED_V3TUV_SHA and
            type(v4stu) is dict and type(raw4stu) is bytes and
            canon(v4stu)==raw4stu and sha256(raw4stu).hexdigest()==SIGNED_V4STU_SHA and
            v4stu['signed_v3tuv_sha256']==SIGNED_V3TUV_SHA and
            v4stu['totals']['original_native_replays']==18 and
            v4stu['totals']['derived_scenarios']==90 and
            v4stu['totals']['paid_consumer_services']==576 and
            v4stu['native_learning_implemented'] is False,
            'candidate signed predecessor/canonical SHA invalid')
    totals=Counter()
    scenarios=[]
    for source,(schedule,ticks) in zip(v3['source_matrix'],NEW_SCHEDULES):
        require(source['schedule']==schedule and
                source['source_external_ticks']==list(ticks),
                'candidate signed source schedule mismatch')
        case,fabric,plans=fixture_fn(ticks=ticks)
        for mode,(name,enabled,priority) in zip(source['modes'],ARMS):
            require(mode['mode']==name,'candidate signed source mode drift')
            for capacity,cap in zip(mode['capacities'],CAPACITIES):
                require(capacity['native_PE_capacity']==cap,
                        'candidate signed source capacity drift')
                pp=replace(plans[1],fabric_slots_per_tick=cap)
                use_plans=(plans[0],pp,plans[2],plans[3])
                bv=LiveBVPlanV0e(enabled=enabled,priority=priority)
                native=native_executor(case,fabric,*use_plans,bv)
                require(snapshot(native)==capacity['original_native_sha256'],
                        'candidate source original native executor drift')
                paid=paid_executor(case,fabric,*use_plans,bv,
                                   consumer_policy='consumer-first')
                conservation(paid,case,fabric,pp,plans[2])
                require(paid['derived_actor_ack']['requests']==16 and
                        len(paid['derived_actor']['applied_receipts'])==16 and
                        paid['derived_actor']['applied_credit_by_actor']['A']==8,
                        'candidate source paid actor evidence unavailable')
                totals['native_source_replays']+=1
                totals['paid_source_actor_reexecutions']+=1
                for variant in VARIANTS:
                    res=evaluate_candidate(case,fabric,*use_plans,bv,paid,variant)
                    audit_candidate(res,case,fabric,use_plans,bv,paid)
                    verdict=res['verdict']
                    require(verdict.startswith('VETO_'),
                            'candidate program silently promoted')
                    totals['candidate_shadow_episodes']+=1
                    totals['verdict_'+verdict]+=1
                    totals['signed_parity_cases']+=int(
                        res['counterfactual']['signed_workload_exact_parity'])
                    totals['off_matrix_parity_cases']+=int(
                        res['counterfactual']['off_matrix_channel_challenge_parity'])
                    scenarios.append({
                        'schedule':schedule,'mode':name,'native_global_PE_capacity':cap,
                        'variant':variant,'verdict':verdict,
                        'proposal':res['proposal'], 'authority':res['authority'],
                        'counterfactual':res['counterfactual'],
                        'committed_derived_program_version':0,
                    })
    require(len(v3['source_matrix'])==3 and
            totals['native_source_replays']==18 and
            totals['paid_source_actor_reexecutions']==18 and
            totals['candidate_shadow_episodes']==18*len(VARIANTS) and
            totals['verdict_VETO_AUTHORITY']==36 and
            totals['verdict_VETO_SIGNED_SOURCE_SEMANTICS']==18 and
            totals['verdict_VETO_OFF_MATRIX_COUNTEREXAMPLE']==18 and
            totals['verdict_VETO_NO_OP_NOT_LEARNING']==18 and
            totals['signed_parity_cases']==72 and
            totals['off_matrix_parity_cases']==18,
            'candidate full source research matrix incomplete')
    return {
        'schema':SCHEMA,'status':STATUS,
        'signed_v3tuv_sha256':sha256(raw3).hexdigest(),
        'signed_v4stu_sha256':sha256(raw4stu).hexdigest(),
        'source_native':'UNMODIFIED_PINNED_V0E',
        'source_feedback':'REEXECUTED_PAID_DERIVED_ACTOR_ACK',
        'candidate_execution':'SEPARATE_NEXT_EPISODE_INPUT_NOT_IN_PLACE_NATIVE_MUTATION',
        'authority_model':'EXPLICIT_OWNER_AND_REVIEWER_RESEARCH_FLAGS_NOT_AUTHENTICATION',
        'tested_variants':list(VARIANTS),
        'totals':dict(sorted(totals.items())),
        'scenarios':scenarios,
        'applied_native_learning_updates':0,
        'adopted_derived_algorithm_updates':0,
        'native_v0e_modified':False,
        'native_Architecture_v1_modified':False,
        'claims_excluded':[
            'feedback sign is not a global training loss or an optimization target',
            'equality on signed native episodes does not imply global equivalence',
            'a signed report and boolean research role flags are not remote identity authentication',
            'no native learning authority, program promotion or parameter optimization was implemented',
            'no source-specific spike weighting, network topology or physical hardware model',
        ],
        'next_gate':'FORMAL_LEARNER_OBJECTIVE_AND_AUTHORITY_BEFORE_ANY_NATIVE_COMPUTATIONAL_ADOPTION',
    }
