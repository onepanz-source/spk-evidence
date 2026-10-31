"""Cumulative T6JKL+T6MNO+T6PQR strict architecture research gate.

Validates pinned T6 ancestral report and original PE/BV source; does not
promote native BV, native state updates, trusted sensor authority or HW.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from .async_multi_v0 import (scenario, MultiPolicy,make_votes,reseal,LoopBoundary,require,digest)
from research.spk_v5_t6abc_def_ghi.cumulative_gate_v0 import run as replay_t6,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno

SCHEMA='spk-v5-t6jkl-mno-pqr-async-multireceiver-plasticity/research-v0'
HISTORY_SHA='21ee3b772801d2b3618022ffd9a1ff715231765e181ce8025dbc2518ce1e0e14'

def sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def host_counterexample():
    # A and D outcomes were WORSENED, but host writes a new coherent fake
    # positive pair; C accepts, preserving its objectively wrong decision.
    p=MultiPolicy();d=p.choose(0,0);votes=make_votes(d,0)
    require(all(v['vote']['outcome']=='WORSENED' for v in votes),'BAD_HOST_POSITIVE_SETUP')
    counterfeit=[reseal({**v['vote'],'outcome':'IMPROVED'}) for v in votes]
    p.submit(counterfeit[0],5);status=p.submit(counterfeit[1],6)
    require(status=='IMPROVED_HELD' and p.table[0]==12,'HOST_FALSE_POSITIVE_NOT_ACCEPTED')
    # Host can impersonate D by changing source label and recalculating digest.
    q=MultiPolicy();d=q.choose(0,0);votes=make_votes(d,0)
    q.submit(votes[0],5)
    impersonated=reseal({**votes[0]['vote'],'receiver':'D'})
    require(q.submit(impersonated,6)=='UPDATED','HOST_RECEIVER_IMPERSONATION_COUNTEREXAMPLE')
    # After good adaptation host can forge both negatives to move policy away.
    r=MultiPolicy();d=r.choose(0,0);vv=make_votes(d,0)
    r.submit(vv[0],5);r.submit(vv[1],6)
    good=r.choose(0,10);vv=make_votes(good,0)
    require(all(x['vote']['outcome']=='IMPROVED' for x in vv),'HOST_NEGATIVE_SETUP')
    false=[reseal({**v['vote'],'outcome':'WORSENED'}) for v in vv]
    r.submit(false[0],15)
    require(r.submit(false[1],16)=='UPDATED' and r.table[0]==12,'HOST_FALSE_NEGATIVE_NOT_ACCEPTED')
    return {'privileged_host_false_positive_pair_accepted':True,
        'privileged_host_impersonated_D_accepted':True,
        'privileged_host_false_negative_pair_destabilized_C':True,
        'native_source_authentication':False}

def run(root='.',strict=True):
    root=Path(root)
    p=root/'research/spk_v5_t6jkl_mno_pqr/reference/t6abc-def-ghi-functional-loop.json'
    require(p.is_file() and not p.is_symlink() and sha_file(p)==HISTORY_SHA,'T6_ANCESTRY_PIN_DRIFT')
    old=json.loads(p.read_bytes())
    require(old['status']=='EXECUTABLE_SHADOW_PE_FRAGMENT_CAUSAL_ADAPTATION_ONLY' and
        old['T6DEF']['learning_successes']==46 and old['T6DEF']['baseline_successes']==0 and
        old['native_learning'] is False and old['promotion_allowed'] is False,'T6_ANCESTRY_CONTRACT')
    pe=root/'spk_architecture_v1/pe_execution_v1b.py'
    bv=root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
    require(sha_file(pe)==PE_SHA and sha_file(bv)==BV_SHA,'FROZEN_SOURCE_DRIFT')
    before=(sha_file(pe),sha_file(bv))
    if strict:
        custody=t5mno.t5jkl.custody(root,True)
        require(custody['original_source_pins']==12,'FROZEN_12_SOURCE_PINS')
        original=replay_t6(root,True)
        blob=(json.dumps(original,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
        require(hashlib.sha256(blob).hexdigest()==HISTORY_SHA,'T6_REEXECUTION_DRIFT')
    control=scenario(learn=False)
    trained=scenario(learn=True)
    reverse=scenario(mode='reverse')
    jitter=scenario(mode='jitter',seed=42)
    jitter_control=scenario(learn=False,mode='jitter',seed=42)
    loss=scenario(mode='jitter',drop_mod=7,seed=42)
    loss_control=scenario(learn=False,mode='jitter',drop_mod=7,seed=42)
    conflict=scenario(mode='reverse',conflict_contexts=(0,))
    no_feedback=scenario(drop_mod=1)
    underbudget=scenario(budget=1)
    multi_seed=[scenario(mode='jitter',seed=s)['joint_successes'] for s in range(10)]
    require(control['joint_successes']==48 and trained['joint_successes']==80 and
            trained['updates']==8 and trained['stale_rejections']==8 and
            trained['judgments']==88 and trained['abandoned']==8,
            'MULTI_RECEIVER_LEARNING_DRIFT')
    require(trained['episodes']==control['episodes']==96 and
            [r['cue'] for r in control['rows']]==[r['cue'] for r in trained['rows']] and
            [r['A_goal'] for r in control['rows']]==[r['A_goal'] for r in trained['rows']],
            'CONTROL_UNMATCHED')
    phase_scores=[sum(r['joint_success'] for r in trained['rows'] if r['phase']==i) for i in range(4)]
    require(phase_scores==[20,20,20,20] and
            trained['final_policy']==control['final_policy']=={0:12,1:11},
            'DRIFT_RECOVERY_FAILED')
    require(reverse['joint_successes']==jitter['joint_successes']==80 and
            jitter_control['joint_successes']==48 and all(x==80 for x in multi_seed),
            'ASYNC_ORDER_INSTABILITY')
    require(loss['joint_successes']==80 and loss_control['joint_successes']==48 and
            loss['dropped']==loss_control['dropped']==27 and loss['updates']==8,
            'BOUNDED_LOSS_DRIFT')
    require(conflict['joint_successes']==40 and conflict['updates']==4 and
            conflict['conflicts']==48 and sum(r['joint_success'] for r in conflict['rows'] if r['cue']==0)==0,
            'CONFLICT_INCORRECTLY_CREDITED')
    require(no_feedback['updates']==0 and no_feedback['joint_successes']==48 and
            underbudget['joint_successes']==44 and underbudget['updates']==2,
            'NEGATIVE_STRESS_NOT_OBSERVED')
    forged=host_counterexample()
    require((sha_file(pe),sha_file(bv))==before,'FROZEN_MUTATION')
    return {'schema':SCHEMA,'status':'MULTI_RECEIVER_ASYNC_MODEL_PLASTICITY_ONLY',
      'source_T6ABC_DEF_GHI_sha256':HISTORY_SHA,
      'ancestry_replayed_byte_exact':bool(strict),
      'original_source_pins':12 if strict else 0,
      'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
      'T6JKL':{'PE_compute_used_at':['C','B','A','D','A-return','D-return','B-return','C-return'],
        'full_frozen_BV_scheduler_used':False,'receiver_nodes':2,'phases':4,
        'trials':96,'control_joint_successes':control['joint_successes'],
        'trained_joint_successes':trained['joint_successes'],
        'trained_success_delta':trained['joint_successes']-control['joint_successes'],
        'per_phase_trained_successes':phase_scores,
        'policy_updates':trained['updates'],
        'matched_task_cues_and_goals':True,
        'control_rows_sha256':control['rows_sha256'],
        'trained_rows_sha256':trained['rows_sha256'],
        'trained_transcripts_sha256':trained['transcripts_sha256']},
      'T6MNO':{'reverse_order_successes':reverse['joint_successes'],
        'jitter_successes':jitter['joint_successes'],
        'jitter_control_successes':jitter_control['joint_successes'],
        'jitter_seeds_0_through_9_joint_successes':multi_seed,
        'stale_policy_messages_rejected':trained['stale_rejections'],
        'nonfinalized_pending_decisions_closed':trained['abandoned'],
        'judgments_accepted':trained['judgments'],
        'bounded_loss_dropped_votes':loss['dropped'],
        'bounded_loss_successes':loss['joint_successes'],
        'bounded_loss_control_successes':loss_control['joint_successes'],
        'bounded_loss_updates':loss['updates']},
      'T6PQR':{'conflicting_goal_contexts':[0],
        'conflicting_receiver_judgments':conflict['conflicts'],
        'conflict_scenario_joint_successes':conflict['joint_successes'],
        'conflict_scenario_updates':conflict['updates'],
        'no_feedback_updates':no_feedback['updates'],
        'no_feedback_joint_successes':no_feedback['joint_successes'],
        'overconstrained_budget_joint_successes':underbudget['joint_successes'],
        'overconstrained_budget_policy_updates':underbudget['updates'],
        **forged},
      'A_sensor_authenticated':False,'C_source_authenticated':False,
      'D_sensor_authenticated':False,'host_can_forge':True,
      'full_native_BV_scheduler_used':False,
      'native_BV_credit':0,'native_C_policy_modified':False,'native_learning':False,
      'promotion_allowed':False,
      'limits':[
        'Model-only two-receiver synthetic goals, not independently sensed physical outcomes',
        'Frozen _compute_local used for PE steps; network topology, delay and goal changes are host-authored research code',
        'Four predefined phase regimes with three switches are model-only, not unseen tasks or real-world generalization',
        'Two logical receiver names do not authenticate either receiver against privileged host impersonation',
        'Equal-vote quorum can abstain on conflict but privileged host can impersonate both A and D',
        'Dropout and feedback budget can prevent adaptation or make it worse than fixed control',
        'No native BV scheduler, source-authenticated measurement, native policy update or native learning']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out)
    require(not out.exists() and not out.is_symlink(),'REPORT_EXISTS')
    result=run(a.root,True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')

if __name__=='__main__':main()
