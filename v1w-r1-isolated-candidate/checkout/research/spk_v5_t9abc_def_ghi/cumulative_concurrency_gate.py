"""T9ABC/DEF/GHI: bounded multi-epoch scheduler, serializable P-CAS and fairness.
Research V1 reference ONLY; not an SPK native scheduler or physical PE clock.
"""
from __future__ import annotations
import argparse, hashlib, json, tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA, BV_SHA
from .concurrent_engine_v1 import MultiTickEngine, Reject, ensure

SCHEMA='spk-v5-t9abc-def-ghi-bounded-multi-epoch-reference/research-v0'
PARENT_SHA='da9339781f6425a45f5e4d271811960d6cd12de44cd38870ab371c41fcc92799'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def tasks():
    return [(n%2, (11 if n%2==0 else 12) if phase%2==0 else (12 if n%2==0 else 11))
      for phase in range(4) for n in range(24)]

def execute(*,inflight=3,learn=True,drop_feedback=False,reopen_each_batch=False):
    ordered=tasks()
    with tempfile.TemporaryDirectory(prefix='spk-t9-bounded-') as tmp:
        e=MultiTickEngine(Path(tmp)/'p.sqlite',learn=learn,max_inflight=inflight)
        results=[];steps=0;versions=[]
        for start in range(0,len(ordered),inflight):
            admitted=[]
            for cue,goal in ordered[start:start+inflight]:
                admitted.append(e.submit(cue,goal,drop_feedback=drop_feedback))
            if reopen_each_batch:e.reopen()
            seq=e.run();steps+=len(seq)
            if reopen_each_batch:e.reopen()
            for idx in admitted:
                r=e.result(idx)
                results.append({k:r[k] for k in ('id','cue','goal','choice','version','outcome','grant')})
            versions.append(dict(e.audit()['P_versions']))
        audit=e.audit();e.close()
    return {'inflight_budget':inflight,'learn':learn,'episodes':len(results),
        'successes':sum(r['outcome']=='IMPROVED' for r in results),
        'vetoes':audit['stale_vetoes'],'grants':audit['reference_v1_tick_grants'],
        'P_writes':audit['P_writes'],'dispatcher_slots':audit['dispatcher_slots'],
        'batch_versions_sha256':digest(versions),'rows_sha256':digest(results),'audit':audit}

def concurrent_conflict():
    with tempfile.TemporaryDirectory(prefix='spk-t9-conflict-') as tmp:
        e=MultiTickEngine(Path(tmp)/'p.sqlite',max_inflight=3)
        ids=[e.submit(*x) for x in [(0,11),(0,11),(1,12)]]
        steps=e.run()
        results=[e.result(i) for i in ids];audit=e.audit()
        ensure([r['grant'] for r in results]==[0,None,1],'CAS_NO_DUPLICATE_GRANT')
        ensure(audit['stale_vetoes']==1 and audit['P_versions']=={0:1,1:1},'CAS_VETO_OR_CONTEXT_INDEPENDENCE')
        ensure([s['slot'] for s in steps]==list(range(15)),'DISPATCH_SERIAL')
        e.reopen();ensure(e.audit()==audit,'CAS_RECOVERY_DRIFT');ensure(e.step() is None,'REPLAY_AFTER_RECOVERY')
        e.close()
    return {'two_same_version_negative_votes_one_grant':True,
            'other_context_independent_grant':True,'late_same_version_vote_settled_without_P':True,
            'stale_veto_count':audit['stale_vetoes'],'serialized_dispatch_slots':len(steps),
            'recovery_byte_exact':True}

def fairness_witness():
    """Late local tick cannot starve behind infinitely renewed local tick=10.
    After every new completed epoch, another is admitted. FIFO event ids
    guarantee progress for the old late-episode feedback.
    """
    with tempfile.TemporaryDirectory(prefix='spk-t9-fair-') as tmp:
        e=MultiTickEngine(Path(tmp)/'p.sqlite',max_inflight=2)
        old=e.submit(0,11,feedback_delay=12) # semantic receipt at tick 26
        e.submit(1,12)
        ep0_seen=None;submitted=2
        all_steps=[]
        for i in range(120):
            x=e.step()
            if x is None:break
            all_steps.append(x)
            if x['episode']==old and x['kind']=='SEM_B_C' and ep0_seen is None:ep0_seen=len(all_steps)
            if submitted<12 and e.audit()['running']<2:
                e.submit(submitted%2,12 if submitted%2==0 else 11)
                submitted+=1
        while e.audit()['running']:
            x=e.step();ensure(x is not None,'FAIRNESS_QUEUE_DEAD');all_steps.append(x)
        ensure(ep0_seen is not None and ep0_seen<=20,'FAIRNESS_STARVATION')
        ensure(e.result(old)['outcome']=='WORSENED' and e.result(old)['grant'] is None,'LATE_FEEDBACK_NOT_OBSERVED')
        audit=e.audit();e.close()
    return {'late_episode_settled':True,'late_episode_dispatch_position':ep0_seen,
            'local_tick_26_not_global_time':True,'bounded_active_episodes':2,
            'late_veto_due_to_deadline':True,'total_dispatch_slots':audit['dispatcher_slots']}

def crash_witness():
    with tempfile.TemporaryDirectory(prefix='spk-t9-crash-') as tmp:
        e=MultiTickEngine(Path(tmp)/'p.sqlite',max_inflight=3)
        ids=[e.submit(0,11),e.submit(0,11),e.submit(1,12)]
        before=[e.step() for _ in range(9)]
        ensure([x['kind'] for x in before[-3:]]==['PE_A']*3,'CRASH_AFTER_ALL_A')
        pending=e.audit()['pending_events'];ensure(pending==3,'CRASH_FEEDBACK_PENDING')
        e.reopen();rest=e.run();res=[e.result(x) for x in ids]
        audit=e.audit();ensure((audit['P_writes'],audit['stale_vetoes'],audit['pending_events'])==(2,1,0),'RECOVERY_CAS_PARITY')
        e.reopen();ensure(e.audit()==audit and e.step() is None,'RECOVERY_REAPPLY')
        e.close()
    return {'pending_semantic_events_before_restart':pending,
        'first_dispatch_slots':len(before),'remaining_dispatch_slots':len(rest),
        'one_grant_per_version_after_restart':True,'stale_vote_veto_after_restart':True,
        'replay_safe':True}

def denial_witness():
    with tempfile.TemporaryDirectory(prefix='spk-t9-deny-') as tmp:
        e=MultiTickEngine(Path(tmp)/'p.sqlite',max_inflight=2)
        ids=[e.submit(0,11),e.submit(1,12)]
        try:e.submit(0,11)
        except Reject as ex:ensure(str(ex)=='INFLIGHT_RESOURCE_BUDGET','WRONG_RESOURCE_VETO')
        else:raise AssertionError('CAPACITY_NOT_ENFORCED')
        e.run();e.submit(0,11,feedback_delay=5);e.run();a=e.audit()
        ensure(a['reference_v1_tick_grants']==2 and a['pending_events']==0,'LATE_GRANT')
        e.close()
    return {'active_epoch_capacity_denied':True,'slot_budget_one_event_per_dispatch':True,
        'deadline_rejects_P_even_when_semantic_verdict_delivered':True}

def report(root):
    root=Path(root)
    p=root/'research/spk_v5_t9abc_def_ghi/reference/t8stu-vwx-yza.json'
    ensure(sha(p)==PARENT_SHA,'PARENT_T8_SHA_MISMATCH')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_SHA_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_SHA_DRIFT')
    old=json.loads(p.read_bytes())
    serial=execute(inflight=1)
    control=execute(inflight=3,learn=False)
    paired=execute(inflight=2)
    triple=execute(inflight=3)
    reopened=execute(inflight=3,reopen_each_batch=True)
    no_feedback=execute(inflight=3,drop_feedback=True)
    ensure((serial['successes'],serial['grants'])==(88,8),'SERIAL_T8_PARITY')
    ensure((control['successes'],control['grants'])==(48,0),'CONTROL_T8_PARITY')
    ensure((no_feedback['successes'],no_feedback['grants'])==(48,0),'NO_FEEDBACK_BOUNDARY')
    ensure((triple['successes'],triple['grants'],triple['vetoes'])==
        (reopened['successes'],reopened['grants'],reopened['vetoes']),'REOPEN_PARITY')
    ensure(serial['successes']==old['T8STU']['adaptive_96']['successes'] and
        control['successes']==old['T8STU']['baseline_96']['successes'],'PRIOR_T8_EXPECTED')
    return {'schema':SCHEMA,'status':'CONCURRENT_REFERENCE_EPOCHS_P_CAS_AND_FIFO_ADMISSION_NOT_NATIVE_SPK',
       'T9ABC':{'concurrent_scheduler_reference':True,'serial_t8_parity':serial,
           'three_epoch_adaptive':triple,'two_epoch_adaptive':paired,
           'three_epoch_control':control,'three_epoch_no_feedback':no_feedback,
           'epoch_local_ticks_not_global_physical_clock':True,'one_dispatch_slot_per_processed_event':True},
       'T9DEF':{'same_version_CAS_and_context_independence':concurrent_conflict(),
           'crash_resume':crash_witness(),'reopened_three_epoch_adaptive':reopened},
       'T9GHI':{'resource_admission':denial_witness(),'fifo_fairness':fairness_witness(),
           'original_scheduler_is_not_concurrent':True},
       'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,'source_T8STU_SHA256':PARENT_SHA,
       'new_original_BV_scheduler_calls':0,'native_SPK_P_grants':0,'native_BV_semantic_deliveries':0,
       'native_learning':False,'host_can_forge':True,'promotion_allowed':False,
       'original_source_pins':12,'limits':[
           'Concurrent episodes run on a NEW RESEARCH V1 scheduler, not frozen SPK BV-v0e',
           'Local tick values 10..26 are episode-relative; a serialized dispatch slot is not a physical PE clock or real occupancy',
           'In-flight admission is a reference quota, not native PE/Memory Contract admission',
           'Stale-version judgments are observed but cannot produce P grants; no inference of authentic receiver identity',
           'All goals and A observations are synthetic and host-authored; host forgery still succeeds',
           'No native SPK semantic BV credit, original Memory Contract P authorization, or learning']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--out',required=True)
    a=ap.parse_args();p=Path(a.out);ensure(not p.exists() and not p.is_symlink(),'REPORT_EXISTS')
    data=report(a.root);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T9ABC/DEF/GHI CONCURRENT V1 REFERENCE CAS/FAIRNESS PASS; RESEARCH ONLY; ZERO NATIVE SPK LEARNING')
    print('reference_report_sha256',sha(p))
if __name__=='__main__':main()
