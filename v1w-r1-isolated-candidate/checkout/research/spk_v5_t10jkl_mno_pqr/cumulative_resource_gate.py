"""Cumulative T10JKL/MNO/PQR resource manifest, tick-time budget and native denial."""
from __future__ import annotations
import argparse,json,hashlib,sqlite3,tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,Reject,digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from .resource_authority_v1 import ResourceAdmittedEngine,native_seam_denial
PARENT='68285626ba06cc63f108176eb2176d26e6954f349de3ffde0f3d45c4325f1eac'
SCHEMA='spk-v5-t10jkl-mno-pqr-bounded-P-resource-admission/research-v0'
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()

def scenario(strategy,*,learn=True,reopen=False):
    ensure(strategy in ('serial','batch3','context_affinity'),'STRATEGY')
    with tempfile.TemporaryDirectory(prefix='spk-t10-resources-') as folder:
        e=ResourceAdmittedEngine(Path(folder)/'store.sqlite',learn=learn,max_inflight=3)
        pending=list(enumerate(tasks()));assigned={};waves=0;max_active=0;slots=0
        while pending:
            select=[];used=set()
            for ix,(cue,goal) in pending:
                if len(select)==3 or (strategy=='serial' and len(select)) :break
                if strategy=='context_affinity' and cue in used:continue
                select.append((ix,cue,goal));used.add(cue)
            ensure(select,'DEADLOCK')
            waves+=1;max_active=max(max_active,len(select))
            for ix,cue,goal in select:assigned[ix]=e.submit(cue,goal)
            if reopen:e.reopen()
            slots+=len(e.run())
            if reopen:e.reopen()
            pending=[r for r in pending if r[0] not in assigned]
        rows=[e.result(assigned[i]) for i in range(len(assigned))]
        audit=e.audit();resource=e.audit_resource_custody()
        result={'episodes':len(rows),'successes':sum(x['choice']==x['goal'] for x in rows),
                'stale_vetoes':audit['stale_vetoes'],'waves':waves,'max_active':max_active,
                'dispatch_slots':slots,'reference_grants':audit['reference_v1_tick_grants'],
                'reference_P_writes':audit['P_writes'],'resource':resource,
                'native_SPK_grants':0,'native_learning':False,
                'reopened_each_wave':reopen,'source_rows_sha256':digest([{'cue':r['cue'],
                     'goal':r['goal'],'choice':r['choice'],'version':r['version'],
                     'outcome':r['outcome'],'grant':r['grant']} for r in rows])}
        e.close();return result

def expect_failure(fn, exc=(Reject,sqlite3.IntegrityError,sqlite3.OperationalError)):
    try:fn()
    except exc:return True
    raise Reject('EXPECTED_RESOURCE_DENIAL_DID_NOT_HAPPEN')

def negative_witness():
    # Quota=0: C has a negative feedback, and the real tick's P store rejects
    # BOTH new grant and P CAS in the same SQLite transaction.
    with tempfile.TemporaryDirectory(prefix='spk-resource-zero-') as folder:
        e=ResourceAdmittedEngine(Path(folder)/'db',grant_ceiling=0,context_ceiling=0)
        e.submit(0,11)
        for _ in range(4):e.step()
        before=tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())
        assert expect_failure(e.step)
        ensure(tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())==before,'QUOTA_PARTIAL_P')
        ensure(e.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]==0,'QUOTA_PARTIAL_GRANT')
        ensure(e.db.execute("SELECT COUNT(*) FROM event WHERE kind='SEM_B_C' AND status='QUEUED'").fetchone()[0]==1,'QUOTA_LOST_EVENT')
        e.reopen();ensure(e.audit_resource_custody()['total_consumed']==0,'QUOTA_RECOVERY_DRIFT')
        assert expect_failure(lambda:e.transition_profile(expected_revision=1,grant_ceiling=1,context_ceiling=1))
        e.transition_profile(expected_revision=0,grant_ceiling=1,context_ceiling=1)
        e.reopen();e.step()
        ensure(e.audit_resource_custody()['total_consumed']==1,'QUOTA_RECOVER_COMMIT')
        ensure(tuple(e.db.execute('SELECT choice,version FROM p WHERE cue=0').fetchone())==(11,1),'QUOTA_POLICY_RECOVERY')
        assert expect_failure(lambda:e.transition_profile(expected_revision=1,grant_ceiling=0,context_ceiling=0))
        e.close()
    # Global capacity and context capacity are distinct. Recovery allows a
    # later C context, but cannot retroactively authorize before the quota bump.
    with tempfile.TemporaryDirectory(prefix='spk-resource-cross-') as folder:
        e=ResourceAdmittedEngine(Path(folder)/'db',grant_ceiling=1,context_ceiling=1)
        e.submit(0,11);e.run()
        e.submit(1,12)
        for _ in range(4):e.step()
        assert expect_failure(e.step)
        ensure(e.audit_resource_custody()['per_context_consumed']=={'0':1,'1':0},'CROSS_QUOTA_CORRUPT')
        e.transition_profile(expected_revision=0,grant_ceiling=2,context_ceiling=1)
        e.reopen();e.step()
        ensure(e.audit_resource_custody()['per_context_consumed']=={'0':1,'1':1},'CROSS_CONTEXT_LOST')
        e.close()
    # A run in verify mode never receives a P grant; no partial grant or P.
    with tempfile.TemporaryDirectory(prefix='spk-resource-verify-') as folder:
        e=ResourceAdmittedEngine(Path(folder)/'db')
        e.transition_profile(expected_revision=0,mode='verify')
        e.submit(0,11)
        for _ in range(4):e.step()
        assert expect_failure(e.step)
        ensure(e.audit_resource_custody()['total_consumed']==0,'VERIFY_UNAUTHORIZED_GRANT')
        e.transition_profile(expected_revision=1,mode='execute')
        e.step();ensure(e.audit_resource_custody()['total_consumed']==1,'EXECUTE_NOT_RESTORED')
        e.close()
    # Mutation of the resource guard or scope must not be accepted on reopen.
    with tempfile.TemporaryDirectory(prefix='spk-resource-drift-') as folder:
        e=ResourceAdmittedEngine(Path(folder)/'db')
        e.db.execute('DROP TRIGGER spk_ref_v3_resource_guard')
        assert expect_failure(e.audit_resource_contract)
        e.close()
        assert expect_failure(lambda:ResourceAdmittedEngine(Path(folder)/'db',create=False))
    ensure(native_seam_denial()=='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT','NATIVE_SEAM_PROMOTION')
    return {'zero_quota_rollback_grant_and_P':True,'pending_feedback_survived_restart':True,
            'quota_expand_CAS_recovered_once':True,'stale_profile_revision_rejected':True,
            'retrospective_budget_rollback_denied':True,'global_vs_context_quota_independent':True,
            'verify_mode_denied_P':True,'execute_mode_restored_once':True,
            'resource_guard_tamper_detected':True,'native_Memory_Contract_unavailable_denied':True,
            'host_can_rewrite_reference_manifest':True}

def report(root):
    root=Path(root)
    ensure(sha(root/'research/spk_v5_t10jkl_mno_pqr/reference/t10abc-def-ghi-cumulative.json')==PARENT,'PARENT_PIN_DRIFT')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'PE_FREEZE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'BV_FREEZE_DRIFT')
    previous=json.loads((root/'research/spk_v5_t10jkl_mno_pqr/reference/t10abc-def-ghi-cumulative.json').read_text())
    original=previous['T10DEF']['reference_provider_scenarios']
    serial=scenario('serial');naive=scenario('batch3');affinity=scenario('context_affinity')
    control=scenario('batch3',learn=False);restarted=scenario('context_affinity',reopen=True)
    for name,cur in (('serial',serial),('naive_three',naive),('context_affinity',affinity),('fixed_control',control),('restarted_affinity',restarted)):
        old=original[name]
        for new_name,old_name in (('successes','successes'),('stale_vetoes','stale_vetoes'),('waves','waves'),('dispatch_slots','dispatch_slots'),('reference_grants','reference_grants'),('reference_P_writes','reference_P_writes')):
            ensure(cur[new_name]==old[old_name],'T10_PARITY_'+name+'_'+new_name)
        ensure(cur['resource']['total_consumed']==cur['reference_grants'],'RESOURCE_PROVIDER_PARITY_'+name)
        ensure(cur['resource']['per_context_consumed']=={'0':cur['reference_grants']//2,'1':cur['reference_grants']//2},'RESOURCE_CONTEXT_CUSTODY_'+name)
    ensure((control['successes'],naive['successes'],affinity['successes'],serial['successes'])==(48,84,88,88),'SUCCESS_SEQUENCE_DRIFT')
    ensure((naive['waves'],affinity['waves'],serial['waves'])==(32,48,96),'WAVE_DRIFT')
    ensure(affinity['resource']==restarted['resource'] and affinity['source_rows_sha256']==restarted['source_rows_sha256'],'RESOURCE_RESTART_DRIFT')
    w=negative_witness()
    return {'schema':SCHEMA,'status':'REFERENCE_V1_RESOURCE_MANIFEST_TICK_ADMISSION_NOT_NATIVE_SPK',
        'T10JKL':{'typed_reference_manifest':affinity['resource']['manifest'],
                  'manifest_mode_execute_and_exact_C_P_scope':True,'original_memory_contract_source_loaded':False,
                  'frozen_originals_unchanged':True},
        'T10MNO':{'scenarios':{'serial':serial,'naive_three':naive,'context_affinity':affinity,
                              'fixed_control':control,'restarted_affinity':restarted},
                  'actual_C_receipt_tick_P_write_resource_gated':True,
                  'resource_counted_from_same_transaction_p_grant':True,
                  'reference_success_delta_affinity_vs_naive':4,'native_SPK_grants':0},
        'T10PQR':{'negative_witness':w,'resource_does_not_authenticate_A':True,
                  'reference_host_remains_privileged':True,'native_seam_status':native_seam_denial()},
        'source_T10ABC_DEF_GHI_SHA256':PARENT,'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'original_source_pins':12,'native_SPK_P_grants':0,'native_SPK_P_writes':0,
        'native_BV_semantic_deliveries':0,'native_learning':False,
        'promotion_allowed':False,'host_can_forge':True,
        'limits':['Resource profile and quota are implemented in host-owned research SQLite only',
                  'Only C/P execute-mode tick updates are modeled; S/E/O domain budgeting and original Memory Contract provider are not implemented',
                  'A privileged host can rewrite resource, provider, or source observations',
                  'Global/individual quotas are reference limits, not genuine PE memory capacity or physical timing',
                  'The eight reference commits reproduce a synthetic two-context task, without native learning or authenticated input']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--out',required=True)
    args=ap.parse_args();out=Path(args.out)
    ensure(not out.exists() and not out.is_symlink(),'REPORT_EXISTS')
    result=report(args.root)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T10JKL/MNO/PQR REFERENCE V1 BOUNDED P RESOURCE ADMISSION PASS; ZERO NATIVE SPK BV OR LEARNING')
    print('reference_report_sha256',sha(out))
if __name__=='__main__':main()
