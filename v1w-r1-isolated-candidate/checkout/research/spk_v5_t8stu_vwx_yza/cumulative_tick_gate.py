"""T8STU/VWX/YZA cumulative V1 tick-runtime research gate.

New scheduler actually performs PE C,B,A at tick 10,11,12 and carries
semantic A->B->C at later ticks; native frozen BV-v0e is only an independent
read-only oracle run AFTER the new runtime has settled the episode. The
v1-reference grants are not native SPK Memory Contract grants.
"""
from __future__ import annotations
import argparse,hashlib,json,tempfile
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import check
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from .tick_engine_v1 import TickEngine

SCHEMA='spk-v5-t8stu-vwx-yza-integrated-reference-ticks/research-v0'
PREVIOUS_SHA='17902ac0d830bdbe93387bb9b8db75ead268ae69c2b290924c65bf14df61f585'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def scenario(*,learn,phases=4,drop_forward=False,drop_feedback=False,feedback_delay=0,
             recover_every=12,oracle=False,source_executor=None):
    # The real v1 event runner never inspects the oracle output; the oracle
    # is a separate parity check, invoked only AFTER each settled episode.
    with tempfile.TemporaryDirectory(prefix='spk-v1tick-') as tmp:
        owner=TickEngine(Path(tmp)/'tick.sqlite',learn=learn)
        records=[];sources=[];oracle_calls=0;events=0
        for phase in range(phases):
            for n in range(24):
                cue=n%2
                goal=(11 if cue==0 else 12) if phase%2==0 else (12 if cue==0 else 11)
                eid=owner.submit(cue,goal,drop_forward=drop_forward,drop_feedback=drop_feedback,
                    feedback_delay=feedback_delay)
                timeline=owner.run();events+=len(timeline)
                result=owner.result(eid)
                record={**result,'steps':len(timeline),'ticks':[ev['tick'] for ev in timeline]}
                if oracle:
                    if source_executor is None:
                        from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
                        raw,evidence=execute_raw(result['choice'],goal,drop_forward=drop_forward)
                    else:raw,evidence=source_executor(result['choice'],goal,drop_forward=drop_forward)
                    oracle_calls+=1
                    expected=('ABSENT' if drop_forward else 'IMPROVED' if result['choice']==goal else 'WORSENED')
                    check(evidence['A_outcome']==expected,'ORACLE_PE_VERDICT_PARITY')
                    check(evidence['reverse_A_B_C']==(not drop_forward),'ORACLE_BV_ROUTE_PARITY')
                    check(result['outcome']==expected,'INTEGRATED_PE_V1_DRIFT')
                    sources.append(digest(raw))
                records.append(record)
                if recover_every and len(records)%recover_every==0:owner.reopen()
        audit=owner.audit();owner.close()
    return {'episodes':len(records),'successes':sum(r['outcome']=='IMPROVED' for r in records),
        'failures':sum(r['outcome']=='WORSENED' for r in records),
        'reference_tick_events_executed':events,
        'semantic_receipts':sum('SEM_B_C' in r['semantic_events'] for r in records),
        'reference_tick_P_grants':audit['reference_v1_tick_grants'],
        'reference_tick_P_commits':audit['P_writes'],
        'source_oracle_calls':oracle_calls,
        'source_oracle_rows_sha256':digest(sources) if oracle else None,
        'rows_sha256':digest(records),'audit':audit}

def crash_resume_witness():
    with tempfile.TemporaryDirectory(prefix='spk-v1tick-crash-') as tmp:
        state=TickEngine(Path(tmp)/'P.sqlite')
        eid=state.submit(0,11)
        first=[state.step() for _ in range(3)]
        check([x['kind'] for x in first]==['PE_C','PE_B','PE_A'],'PAUSE_AFTER_A_PE')
        before=state.audit();check(before['pending_events']==1 and before['reference_v1_tick_grants']==0,'PENDING_SEMANTIC_EVENT')
        state.reopen();second=state.run();result=state.result(eid)
        state.reopen();check(state.step() is None,'EVENT_APPLIED_TWICE')
        after=state.audit();state.close()
    check(len(second)==2 and result['grant']==0 and after['reference_v1_tick_grants']==1,'CRASH_RECOVERY_COMMIT')
    return {'three_PE_steps_before_restart':3,'feedback_ticks_after_restart':2,'pending_semantic_event_durable':True,
        'one_P_grant_after_restart':True,'replay_did_not_reapply':True}

def delay_witness():
    with tempfile.TemporaryDirectory(prefix='spk-v1tick-deadline-') as tmp:
        state=TickEngine(Path(tmp)/'P.sqlite')
        i=state.submit(0,11,feedback_delay=4);rows=state.run();a=state.result(i)
        j=state.submit(1,12,feedback_delay=5);rows2=state.run();b=state.result(j)
        audit=state.audit();state.close()
    check(a['grant']==0 and b['grant'] is None and audit['reference_v1_tick_grants']==1,'FEEDBACK_DEADLINE')
    return {'deadline_tick_18_accepted':True,'tick_19_denied_P':True,'late_semantic_verdict_observed':True}

def host_control_witness():
    # Identical policy and same C decision, but host controls synthetic A goal.
    # This is a real non-authenticity counterexample, not a native grant proof.
    with tempfile.TemporaryDirectory(prefix='spk-v1tick-host-') as tmp:
        a=TickEngine(Path(tmp)/'a.sqlite');i=a.submit(0,11);a.run();v=a.result(i);aa=a.audit();a.close()
        b=TickEngine(Path(tmp)/'b.sqlite');j=b.submit(0,12);b.run();w=b.result(j);bb=b.audit();b.close()
    check(v['choice']==w['choice'] and v['outcome']!=w['outcome'] and
        aa['reference_v1_tick_grants']==1 and bb['reference_v1_tick_grants']==0,'HOST_GOAL_CONTROL')
    return {'same_C_choice':True,'host_changed_only_unattested_A_goal':True,
        'opposite_A_verdicts':True,'host_can_drive_reference_grant':True,
        'native_SPK_grant':False}

def report(root,*,oracle=True,source_executor=None):
    root=Path(root)
    reference=root/'research/spk_v5_t8stu_vwx_yza/reference/t8jkl-mno-pqr.json'
    check(sha(reference)==PREVIOUS_SHA,'PARENT_REPORT_SHA_DRIFT')
    check(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'ORIGINAL_PE_SOURCE_DRIFT')
    check(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'ORIGINAL_BV_SOURCE_DRIFT')
    previous=json.loads(reference.read_bytes())
    baseline=scenario(learn=False,oracle=oracle,source_executor=source_executor)
    adaptive=scenario(learn=True,oracle=oracle,source_executor=source_executor)
    lost=scenario(learn=True,phases=1,drop_forward=True,oracle=oracle,source_executor=source_executor)
    crash=crash_resume_witness();deadline=delay_witness();host=host_control_witness()
    check((baseline['successes'],adaptive['successes'],lost['successes'])==(48,88,0),'SUCCESS_PARITY')
    check((baseline['reference_tick_P_grants'],adaptive['reference_tick_P_grants'],lost['reference_tick_P_grants'])==(0,8,0),'GRANT_PARITY')
    check((baseline['semantic_receipts'],adaptive['semantic_receipts'],lost['semantic_receipts'])==(96,96,0),'TICK_BUS_DELIVERY')
    if oracle:
        check((baseline['source_oracle_calls'],adaptive['source_oracle_calls'],lost['source_oracle_calls'])==(96,96,24),'ORACLE_COUNT')
        for actual,expected in (
            (baseline,previous['T8PQR']['baseline_96']),
            (adaptive,previous['T8PQR']['adaptive_96']),
            (lost,previous['T8PQR']['lost_forward_24'])):
            check(actual['source_oracle_rows_sha256']==expected['source_rows_sha256'],'FROZEN_BV_ORACLE_SOURCE_SHA_MISMATCH')
    return {'schema':SCHEMA,'status':'V1_REFERENCE_INTEGRATED_TICK_EVENT_SEMANTIC_AND_P_COMMIT_NOT_NATIVE_SPK',
        'T8STU':{'reference_integrated_tick_scheduler':True,'separate_tick_events':['PE_C','PE_B','PE_A','SEM_A_B','SEM_B_C'],
            'original_PE_compute_used':True,'semantic_feedback_during_tick':True,'native_v0e_code_unchanged':True,
            'baseline_96':baseline,'adaptive_96':adaptive,'lost_forward_24':lost},
        'T8VWX':{'P_reference_grants_from_C_receipt_tick':adaptive['reference_tick_P_grants'],
            'P_reference_commits_in_same_tick_transaction':adaptive['reference_tick_P_commits'],
            'recovery':crash,'deadline':deadline,
            'oracle_read_only':True,'original_scheduler_oracle_calls':216 if oracle else 0,
            'parity_to_T8_full_frozen_source_sha':oracle},
        'T8YZA':{'host_goal_control_counterexample':host,
            'no_signer_or_attestation':True,'native_P_grants':0,'native_BV_semantic_events':0},
        'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'source_T8JKL_MNO_PQR_sha256':PREVIOUS_SHA,'original_source_pins':12,
        'host_can_forge':True,'A_sensor_authenticated':False,'C_source_authenticated':False,
        'native_SPK_P_grants':0,'native_SPK_P_writes':0,'native_BV_semantic_deliveries':0,
        'native_learning':False,'promotion_allowed':False,
        'limits':['This NEW V1 research tick engine is not the frozen SPK BV scheduler, and does not grant SPK native P access',
        'V1 forwards semantic feedback and commits P in tick transactions rather than interpreting an after-the-fact source report',
        'The original frozen BV-v0e is run independently after each episode solely as a parity oracle, NOT as an authority for the v1 tick engine',
        'All tasks, goals, C source choices and A sensor semantics remain synthetic and controlled by the privileged host',
        'Episodes are sequential and three-node only, with idealized ticks; this proves neither asynchronous full scheduler integration nor general learning']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args();p=Path(args.out)
    check(not p.exists() and not p.is_symlink(),'OUTPUT_EXISTS')
    r=report(args.root)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T8STU/VWX/YZA V1 INTEGRATED TICK REFERENCE PASS; 8 REFERENCE TICK GRANTS; ZERO NATIVE SPK BV OR LEARNING')
    print('reference_report_sha256',sha(p))
if __name__=='__main__':main()
