"""Cumulative functional feedback test with frozen PE computation and fair ablation.

Attestation is explicitly NOT a goal of this research-only experiment.
"""
from __future__ import annotations
import argparse,copy,hashlib,json
from pathlib import Path
from .loop_v0 import CPolicy,LoopBoundary,GOALS,INITIAL,trial,episode,forward,a_measure,backward,compare_interventions,digest,require
from research.spk_v5_t5pqr_stu_vwx.cumulative_gate_v0 import run as replay_ancestry
from research.spk_v5_t5mno import t5mno

SCHEMA='spk-v5-t6abc-def-ghi-functional-closed-loop/research-v0'
HISTORY_SHA='7928c3726eff1f9aef7a4cc2424bc230b7751673adedb081e8f893880996059d'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
BV_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'

def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(root,strict=True):
    root=Path(root)
    archive=root/'research/spk_v5_t6abc_def_ghi/reference/t5pqr-stu-vwx-cumulative.json'
    require(archive.is_file() and not archive.is_symlink() and sha_file(archive)==HISTORY_SHA,'ANCESTRY_REPORT_DRIFT')
    old=json.loads(archive.read_bytes())
    require(old['status']=='THREE_RESEARCH_GATES_CAUSAL_IDENTIFIABILITY_SIMULATED_INTERVENTION_SHADOW_FEEDBACK' and
            old['promotion_allowed'] is False and old['native_BV_credit']==0 and old['native_learning'] is False,'ANCESTRY_PROMOTION_CONFLICT')
    frozen_pe=root/'spk_architecture_v1/pe_execution_v1b.py'
    frozen_bv=root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
    require(sha_file(frozen_pe)==PE_SHA and sha_file(frozen_bv)==BV_SHA,'FROZEN_MODULE_DRIFT')
    before=(sha_file(frozen_pe),sha_file(frozen_bv))
    custody=t5mno.t5jkl.custody(root,strict)
    require(custody['original_source_pins']==12,'ORIGINAL_12_PINS_REQUIRED')
    if strict:
        # The previous complete research pipeline is regenerated from the
        # identical archived inputs, with independently verified original pins.
        regenerated=replay_ancestry(root,True)
        serialized=(json.dumps(regenerated,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
        require(hashlib.sha256(serialized).hexdigest()==HISTORY_SHA,'CUMULATIVE_ANCESTRY_REEXECUTION_DRIFT')
    sequence=tuple(i%2 for i in range(48))
    baseline=trial(False,sequence)
    trained=trial(True,sequence)
    require(baseline['successes']==0 and baseline['updates']==0 and baseline['final_policy']==INITIAL,'BASELINE_DRIFT')
    require(trained['successes']==46 and trained['updates']==2 and trained['final_policy']=={0:11,1:12},'CLOSED_LOOP_FAILED')
    require(baseline['episodes']==trained['episodes']==48 and baseline['emitted']==trained['emitted']==48,'FEEDBACK_NOT_IDENTICAL')
    require([r['cue'] for r in baseline['records']]==[r['cue'] for r in trained['records']]==list(sequence),'NOT_MATCHED_CASES')
    require(all(r['A_raw'] in (5,11) and r['A_goal']==GOALS[r['cue']] for r in trained['records']),'A_PE_MEASUREMENT_INVALID')
    require(all(x['absent_outcome']=='UNCHANGED' and x['absent_raw']==0 for x in trained['interventions']),'NO_C_ABLATION_DRIFT')
    # The causal intervention is within this deterministic, host-authored
    # computational plant: force the alternate C output and recompute B/A.
    require(sum(x['outcome_delta'] for x in trained['interventions'])==44,'TRAINED_INTERVENTIONS_DIFFERENCE')
    require(sum(x['outcome_delta'] for x in baseline['interventions'])==-48,'BASELINE_INTERVENTIONS_DIFFERENCE')
    # Absence: no update despite failed goal, next C decision remains unchanged.
    missing=CPolicy(True)
    first=episode(missing,0,feedback=False)
    next_decision,_=missing.choose(0)
    require(first['A_outcome']=='WORSENED' and next_decision['choice']==12 and missing.updates==0,'MISSING_FEEDBACK_CHANGED_POLICY')
    # Negative feedback delayed until deadline is still consumable.
    delayed=CPolicy(True)
    dec,_=delayed.choose(0);packet,_=a_measure(0,forward(dec)['emissions'][0],dec)
    relay,_,_=backward(packet)
    require(delayed.apply(relay,current_tick=7)['policy_updated'],'BOUNDED_DELAY_REJECTED')
    # Stale, corrupted, replay and contradiction MUST fail closed.
    rejections={}
    for label,edit,late in [
        ('stale',lambda x:None,8),
        ('A_tamper',lambda x:x['payload'].update(outcome='IMPROVED'),4),
        ('B_tamper',lambda x:x.update(b_sha256='0'*64),4),
        ('wrong_decision',lambda x:x['payload'].update(decision_id=1000),4),
        ('wrong_context',lambda x:x['payload'].update(cue=1),4),
    ]:
        policy=CPolicy(True);d,_=policy.choose(0);p,_=a_measure(0,forward(d)['emissions'][0],d)
        msg,_,_=backward(p);edit(msg)
        rejected=False
        try:policy.apply(msg,current_tick=late)
        except LoopBoundary:rejected=True
        require(rejected and policy.updates==0,'ATTACK_NOT_REJECTED_'+label)
        rejections[label]='REJECTED'
    policy=CPolicy(True);d,_=policy.choose(0);p,_=a_measure(0,forward(d)['emissions'][0],d);msg,_,_=backward(p)
    policy.apply(msg)
    for label in ('replay','conflicting_second_feedback'):
        m=copy.deepcopy(msg)
        if label=='conflicting_second_feedback':m['payload']['outcome']='IMPROVED'
        rejected=False
        try:policy.apply(m)
        except LoopBoundary:rejected=True
        require(rejected,'ATTACK_NOT_REJECTED_'+label);rejections[label]='REJECTED'
    # Concurrent old-version feedback cannot undo an intervening adaptation.
    concurrent=CPolicy(True)
    d1,_=concurrent.choose(0);d2,_=concurrent.choose(0)
    p1,_=a_measure(0,forward(d1)['emissions'][0],d1)
    p2,_=a_measure(0,forward(d2)['emissions'][0],d2)
    r1,_,_=backward(p1);r2,_,_=backward(p2)
    require(concurrent.apply(r1)['policy_updated'],'CONCURRENT_FIRST_UPDATE_MISSING')
    stale_rejected=False
    try:concurrent.apply(r2)
    except LoopBoundary:stale_rejected=True
    require(stale_rejected and concurrent.table[0]==11,'CONCURRENT_STALE_UPDATE_ACCEPTED')
    rejections['stale_policy_version']='REJECTED'
    # This forge succeeds, intentionally and necessarily in a host-controlled
    # runtime.  Unlike tampering, host recomputes all packet ledger digests.
    forged=CPolicy(True);d,_=forged.choose(0)
    evidence,_=a_measure(0,forward(d)['emissions'][0],d)
    require(evidence['outcome']=='WORSENED','FORGERY_SETUP_BAD')
    counterfeit=dict(evidence);counterfeit['outcome']='IMPROVED';counterfeit['a_feedback_ch']=41
    reissued,_,_=backward(counterfeit)
    accepted=forged.apply(reissued)
    require(not accepted['policy_updated'] and forged.table==INITIAL,'HOST_FORGERY_COUNTEREXAMPLE_FAILED')
    # And a forged negative can destabilize a previously correct policy.
    unstable=CPolicy(True);episode(unstable,0)
    d,_=unstable.choose(0);pkt,_=a_measure(0,forward(d)['emissions'][0],d)
    require(pkt['outcome']=='IMPROVED','FORGE_NEG_SETUP')
    pkt['outcome']='WORSENED';pkt['a_feedback_ch']=42
    malicious,_,_=backward(pkt)
    require(unstable.apply(malicious)['policy_updated'] and unstable.table[0]==12,'HOST_DESTABILIZATION_NOT_OBSERVED')
    require((sha_file(frozen_pe),sha_file(frozen_bv))==before,'FROZEN_MUTATED')
    return {
        'schema':SCHEMA,'status':'EXECUTABLE_SHADOW_PE_FRAGMENT_CAUSAL_ADAPTATION_ONLY',
        'source_T5PQR_STU_VWX_sha256':HISTORY_SHA,
        'ancestry_replay_byte_exact':bool(strict),
        'original_source_pins':custody['original_source_pins'],
        'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'T6ABC':{'real_frozen_PE_compute_function_reused':True,
                 'source_execution_path':'_compute_local called for C,B,A,A-return,B-return,C-return',
                 'full_frozen_BV_scheduler_used':False,
                 'same_task_sequence':True,'cases':48,
                 'C_B_A_hops_per_trial':48,'A_B_C_feedback_round_trips_per_trial':48,
                 'frozen_opcodes_used':['ACC','CMP','EMIT','RESET'],
                 'context_goal_count':2},
        'T6DEF':{'baseline_successes':baseline['successes'],
                 'learning_successes':trained['successes'],
                 'success_improvement':trained['successes']-baseline['successes'],
                 'baseline_policy_updates':baseline['updates'],
                 'learning_policy_updates':trained['updates'],
                 'final_policy':{str(k):v for k,v in trained['final_policy'].items()},
                 'first_change_after_feedback':trained['records'][2]['C_action']!=baseline['records'][2]['C_action'],
                 'matched_control_trace_sha256':digest(baseline['records']),
                 'matched_learning_trace_sha256':digest(trained['records']),
                 'learning_trace':trained['records']},
        'T6GHI':{'model_only_forced_alternative_trials':48,
                 'learning_counterfactual_total_difference':sum(x['outcome_delta'] for x in trained['interventions']),
                 'baseline_counterfactual_total_difference':sum(x['outcome_delta'] for x in baseline['interventions']),
                 'no_C_signal_in_control_world':all(x['absent_raw']==0 for x in trained['interventions']),
                 'feedback_absence_maintains_policy':True,
                 'feedback_delay_at_deadline_accepted':True,
                 'invalid_feedback_rejected':rejections,
                 'host_forged_fresh_A_ledger_accepted':True,
                 'host_can_destabilize_learning_by_fake_negative':True},
        'experimental_shadow_C_policy_updated':True,
        'native_C_policy_modified':False,
        'native_BV_credit':0,'native_learning':False,
        'real_world_causal_identifiability':False,
        'C_source_authenticated':False,'A_sensor_authenticated':False,
        'host_can_forge':True,'promotion_allowed':False,
        'limits':[
            'Functional adaptation is shown only in a small two-context host-controlled experimental PE fragment, not the frozen scheduler',
            'PE compute function is original, but selected instruction programs and experiment graph are host-authored',
            'The experiment has no source-authenticated A measurement and does not generalize to unseen task distributions',
            'Matched counterfactual outcomes establish model-internal effects only; no physical or native C causal conclusion',
            'Native SPK frozen Core, Network, PE, scheduler and learning contracts remain untouched',
            'A privileged host can rebind a fresh A receipt and reverse the correct local policy']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    try:
        require(not args.out.exists() and not args.out.is_symlink(),'OUTPUT_ALREADY_EXISTS')
        report=run(args.root,True)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes((json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        print('T6ABC/DEF/GHI',report['status'])
        print('paired',report['T6ABC']['cases'],'trained',report['T6DEF']['learning_successes'],
              'baseline',report['T6DEF']['baseline_successes'],'C policy updates',report['T6DEF']['learning_policy_updates'])
        print('sha256',sha_file(args.out))
    except (LoopBoundary,AssertionError,ValueError,KeyError,TypeError,OSError,ImportError) as ex:
        raise SystemExit('T6 ABC DEF GHI FAIL CLOSED: '+str(ex))
if __name__=='__main__':main()
