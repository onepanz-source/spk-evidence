"""T9STU/VWX/YZA: fenced reference P + independent grant lineage.

Does not write to SPK native memory, does not change frozen source.
"""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest,Reject
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from .fenced_p_store_v1 import FencedMultiTickEngine, independent_grant_custody
from .p_target_admission_port_v1 import project_grant,native_authorize,NativeUnavailable

PARENT='55d433477111f2e820b60074d206e449a5af7cd9d44fd6e2ad7411964fe56ae8'
SCHEMA='spk-v5-t9stu-vwx-yza-reference-P-fence-and-native-seam/research-v0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run_fenced(strategy,*,restart=False,learn=True):
    ensure(strategy in ('serial','batch3','context_affinity'),'STRATEGY')
    ordered=list(enumerate(tasks()))
    with tempfile.TemporaryDirectory(prefix='spk-t9-fence-') as tmp:
        e=FencedMultiTickEngine(Path(tmp)/'engine.db',max_inflight=3,learn=learn)
        pending=ordered[:]; assigned={};waves=0;slots=0;max_active=0
        while pending:
            selection=[];used=set()
            for idx,(cue,goal) in pending:
                if len(selection)>=3 or (strategy=='serial' and selection):break
                if strategy=='context_affinity' and cue in used:continue
                selection.append((idx,cue,goal));used.add(cue)
            ensure(selection,'NO_ADMISSION_PROGRESS');waves+=1
            max_active=max(max_active,len(selection))
            for idx,cue,goal in selection:assigned[idx]=e.submit(cue,goal)
            if restart:e.reopen()
            slots+=len(e.run())
            if restart:e.reopen()
            pending=[x for x in pending if x[0] not in assigned]
        audit=e.audit();custody=independent_grant_custody(e)
        e.assert_fence()
        r=[e.result(assigned[i]) for i in range(len(ordered))]
        successes=sum(x['outcome']=='IMPROVED' for x in r)
        ensure(slots==audit['dispatcher_slots'],'SLOT_COUNT_DRIFT')
        ensure(custody['verified_reference_grants']==audit['reference_v1_tick_grants'],'CUSTODY_DRIFT')
        grants=[project_grant(e,x) for x in range(audit['reference_v1_tick_grants'])]
        ensure(all(g['native_admission'].startswith('DENIED_') and not g['target']['native_memory_grant'] for g in grants),'SPK_NATIVE_PROMOTION')
        result={'strategy':strategy,'successes':successes,'episodes':len(r),
            'waves':waves,'max_active':max_active,'dispatcher_slots':slots,
            'reference_P_grants':audit['reference_v1_tick_grants'],'reference_P_writes':audit['P_writes'],
            'stale_vetoes':audit['stale_vetoes'],'core_rows_sha256':digest([{k:row[k] for k in ('id','cue','goal','choice','version','outcome','grant')} for row in r]),
            'custody':custody,'native_P_grants':0,'native_P_writes':0,
            'target_projection_sha256':digest(grants),'restart_every_wave':restart}
        e.close();return result

def negative_witness():
    with tempfile.TemporaryDirectory(prefix='spk-p-negative-') as tmp:
        p=Path(tmp)/'p.db';e=FencedMultiTickEngine(p)
        failures=[]
        for statement in ('UPDATE p SET choice=11 WHERE cue=0',
                          'UPDATE p SET version=version+1 WHERE cue=1',
                          'DELETE FROM p WHERE cue=0',
                          'INSERT INTO p VALUES(2,11,0,12)'):
            try:e.db.execute(statement)
            except sqlite3.IntegrityError:failures.append(statement.split()[0])
            else:raise AssertionError('DIRECT_P_WRITE_WAS_PERMITTED')
        ensure(len(failures)==4,'REFERENCE_FENCE_DIRECT_MUTATION')
        # The real reference scheduler passes the additional storage-level gate.
        a=e.submit(0,11);b=e.submit(0,11);e.run()
        audit=e.audit();custody=independent_grant_custody(e)
        ensure(audit['P_writes']==1 and audit['stale_vetoes']==1 and
               custody['verified_reference_grants']==1,'SAME_VERSION_DOUBLE_GRANT')
        try:e.db.execute('UPDATE p SET choice=12,version=version+1,budget=budget-1 WHERE cue=0')
        except sqlite3.IntegrityError:after_grant_blocked=True
        else:raise AssertionError('SECOND_CAS_PERMITTED')
        before=e.audit();e.reopen();ensure(e.audit()==before,'REOPEN_DRIFT')
        ensure(independent_grant_custody(e)==custody,'REOPEN_CUSTODY_DRIFT')
        projection=project_grant(e,0)
        try:native_authorize(projection)
        except NativeUnavailable:unavailable=True
        else:raise AssertionError('FAKE_NATIVE_AUTHORIZATION')
        # A privileged host can DROP the SQL trigger and write state; the normal
        # audit detects this unreconciled mutation, but host reseal remains possible.
        e.db.execute('DROP TRIGGER spk_ref_p_fence')
        e.db.execute('UPDATE p SET choice=12 WHERE cue=0')
        try:e.assert_fence()
        except Reject:fence_drop_detected=True
        else:raise AssertionError('TRIGGER_DROP_NOT_DETECTED')
        try:e.audit()
        except Reject:db_material_drift_detected=True
        else:raise AssertionError('P_MATERIAL_TAMPER_ACCEPTED')
        e.close()
    return {'direct_P_attempts_denied':failures,'second_direct_CAS_denied':after_grant_blocked,
       'replay_and_restart_safe':True,'one_reference_grant_two_same_version_verdicts':True,
       'independent_grant_lineage':custody,'native_port_unavailable':unavailable,
       'direct_trigger_drop_detected':fence_drop_detected,'unreconciled_P_tamper_detected':db_material_drift_detected,
       'privileged_host_can_reseal':True,'native_admission_granted':False}

def report(root):
    root=Path(root)
    p=root/'research/spk_v5_t9stu_vwx_yza/reference/t9jkl-mno-pqr-cumulative.json'
    ensure(sha(p)==PARENT,'T9_PARENT_REPORT_DRIFT')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    parent=json.loads(p.read_bytes())['T9MNO']
    naive=run_fenced('batch3');affinity=run_fenced('context_affinity');serial=run_fenced('serial')
    rest=run_fenced('context_affinity',restart=True)
    control=run_fenced('batch3',learn=False)
    ensure((naive['successes'],affinity['successes'],serial['successes'],control['successes'])==(84,88,88,48),'FENCED_OUTCOME_DRIFT')
    ensure((naive['waves'],affinity['waves'],serial['waves'])==(32,48,96),'FENCED_ADMISSION_DRIFT')
    for name,row in [('naive_three_inflight',naive),('context_affinity',affinity),('serial',serial),('fixed_control',control)]:
        expected=parent[name]
        ensure(row['core_rows_sha256']==expected['core_rows_digest'] and
            row['successes']==expected['successes'] and
            row['reference_P_grants']==expected['P_grants'] and
            row['stale_vetoes']==expected['stale_vetoes'],'P_BOUNDARY_PARITY_'+name)
    ensure(all(affinity[k]==rest[k] for k in ('core_rows_sha256','successes','reference_P_grants','reference_P_writes','custody','target_projection_sha256')),'RESTARTED_AUTHORITY_DRIFT')
    witness=negative_witness()
    return {'schema':SCHEMA,'status':'REFERENCE_P_STORE_FENCE_GRANT_LINEAGE_AND_NATIVE_ADMISSION_SEAM_RESEARCH_ONLY',
            'T9STU':{'fenced_naive':naive,'fenced_affinity':affinity,'fenced_serial':serial,'reference_P_CAS_enforced_by_SQL_trigger':True},
            'T9VWX':{'native_target_admission':'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT',
                      'native_memory_contract_port_implemented':False,
                      'reference_target_maps_exact_C_P_version':True,
                      'reference_grant_lineage_independently_verified':True,
                      'authenticated_host_authority':False},
            'T9YZA':{'fixed_control':control,'restarted_affinity':rest,'negative_witness':witness,
                     'performance_cost_waves':affinity['waves']-naive['waves'],
                     'benefit_successes':affinity['successes']-naive['successes']},
            'source_T9JKL_SHA256':PARENT,'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
            'original_source_pins':12,'new_frozen_scheduler_calls':0,
            'native_SPK_P_grants':0,'native_SPK_P_writes':0,'native_BV_semantic_deliveries':0,
            'native_learning':False,'host_can_forge':True,'promotion_allowed':False,
            'limits':['A reference-v1 P UPDATE is now fenced by an independent SQLite trigger requiring an existing grant and completed C semantic event',
                      'SQLite is still fully controlled by the privileged host; trigger removal/reseal is possible, not independent authority',
                      'Versioned C/P memory target is a typed research projection, NOT the frozen SPK Memory Contract admission',
                      'Reference-v1 events are epoch-local ticks; not a physical PE clock or native resource admission',
                      'Goals and A observations remain synthetic and host-authored; no real-world causal learning',
                      'SPK frozen PE/BV and Memory Contract unchanged; zero native learning']}

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',default='.');a.add_argument('--out',required=True)
    args=a.parse_args();path=Path(args.out)
    ensure(not path.exists() and not path.is_symlink(),'REPORT_EXISTS')
    output=report(args.root);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print('T9STU/VWX/YZA REFERENCE P STORE FENCE / CUSTODY / NATIVE SEAM RESEARCH PASS; ZERO NATIVE SPK LEARNING')
    print('reference_report_sha256',sha(path))
if __name__=='__main__':main()
