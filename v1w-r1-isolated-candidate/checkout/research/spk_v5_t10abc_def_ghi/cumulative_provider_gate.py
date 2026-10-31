"""T10ABC/DEF/GHI cumulative reference P admission provider milestone."""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,Reject,digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from research.spk_v5_t9stu_vwx_yza.p_target_admission_port_v1 import target_for
from .provider_v1 import ProviderFencedTickEngine,native_gate_must_deny
PARENT='d4660c5e744a7e43346e72f39018483cbd9bd12474ad0f27196c40d90ffc382d'
SCHEMA='spk-v5-t10abc-def-ghi-reference-provider-C-tick-contract/research-v0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def scenario(strategy,*,learn=True,restart=False):
    ensure(strategy in ('serial','batch3','context_affinity'),'STRATEGY')
    with tempfile.TemporaryDirectory(prefix='spk-t10-p-admit-') as folder:
        e=ProviderFencedTickEngine(Path(folder)/'engine.sqlite',learn=learn,max_inflight=3)
        pending=list(enumerate(tasks()));assigned={};waves=0;max_active=0;slots=0
        while pending:
            select=[];used=set()
            for idx,(cue,goal) in pending:
                if len(select)==3 or (strategy=='serial' and select):break
                if strategy=='context_affinity' and cue in used:continue
                select.append((idx,cue,goal));used.add(cue)
            ensure(bool(select),'PROVIDER_ADMISSION_DEADLOCK')
            waves+=1;max_active=max(max_active,len(select))
            for idx,cue,goal in select:assigned[idx]=e.submit(cue,goal)
            if restart:e.reopen()
            slots+=len(e.run())
            if restart:e.reopen()
            pending=[x for x in pending if x[0] not in assigned]
        rows=[e.result(assigned[i]) for i in range(len(assigned))]
        success=sum(r['choice']==r['goal'] for r in rows)
        audit=e.audit();provider=e.audit_provider()
        out={'episodes':len(rows),'successes':success,'waves':waves,'max_active':max_active,
             'dispatch_slots':slots,'stale_vetoes':audit['stale_vetoes'],
             'reference_grants':audit['reference_v1_tick_grants'],'reference_P_writes':audit['P_writes'],
             'provider':provider,'core_rows_sha256':digest([{'cue':r['cue'],'goal':r['goal'],
                 'choice':r['choice'],'version':r['version'],'outcome':r['outcome'],
                 'grant':r['grant']} for r in rows]),
             'native_P_grants':0,'native_P_writes':0,'reopened_each_wave':restart}
        e.close();return out

def negative_witness():
    with tempfile.TemporaryDirectory(prefix='spk-t10-provider-denial-') as tmp:
        e=ProviderFencedTickEngine(Path(tmp)/'db.sqlite')
        ep=e.submit(0,11)
        pre=[e.step() for _ in range(4)]
        ensure([x['kind'] for x in pre]==['PE_C','PE_B','PE_A','SEM_A_B'],'EXPECTED_C_PRECURSORS')
        before=e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone()
        before=tuple(before);cnt=e.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]
        e.provider_enabled=False
        denied=False
        try:e.step()
        except (sqlite3.IntegrityError,sqlite3.OperationalError):denied=True
        ensure(denied,'PROVIDER_DENIAL_BYPASSED')
        after=tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())
        ensure(after==before and e.db.execute('SELECT count(*) FROM p_grant').fetchone()[0]==cnt,
               'PROVIDER_DENIAL_NON_ATOMIC')
        ensure(e.db.execute("SELECT count(*) FROM event WHERE status='QUEUED' AND kind='SEM_B_C'").fetchone()[0]==1,
               'DENIED_EVENT_NOT_RECOVERABLE')
        e.reopen()   # provider re-attaches on process restart
        success=e.step();ensure(success['kind']=='SEM_B_C','C_TICK_NOT_RECOVERED')
        audit=e.audit_provider()
        ensure(audit['provider_v1_authorizations']==1,'RECOVERED_PROVIDER_MISSING_GRANT')
        state=tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())
        ensure(state==(11,1,11),'RECOVERY_WRONG_POLICY')
        before_audit=e.audit();e.reopen()
        ensure(e.audit()==before_audit and e.audit_provider()==audit,'REOPEN_PROVIDER_DRIFT')
        # Direct UPDATE fails despite a valid prior but already committed grant.
        direct_rejected=False
        try:e.db.execute('UPDATE p SET choice=12,version=2,budget=10 WHERE cue=0')
        except sqlite3.IntegrityError:direct_rejected=True
        ensure(direct_rejected,'DIRECT_P_WRITE_BYPASSED_PROVIDER')
        ensure(native_gate_must_deny(target_for(cue=0,version=1))=='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT',
               'NATIVE_GRANT_FAKE')
        e.close()
    # Real duplicate same-version issue; only one provider approval allowed.
    with tempfile.TemporaryDirectory(prefix='spk-t10-provider-cas-') as tmp:
        e=ProviderFencedTickEngine(Path(tmp)/'db.sqlite')
        x=e.submit(0,11);y=e.submit(0,11)
        e.run();p=e.audit_provider();b=e.audit()
        ensure(p['provider_v1_authorizations']==1 and b['stale_vetoes']==1,
               'DOUBLE_PROVIDER_COMMIT')
        e.reopen();ensure(e.audit_provider()==p,'CONCURRENT_RESTART_DRIFT');e.close()
    with tempfile.TemporaryDirectory(prefix='spk-t10-provider-late-') as tmp:
        e=ProviderFencedTickEngine(Path(tmp)/'db.sqlite')
        e.submit(0,11,feedback_delay=5)
        e.run();late=e.audit_provider();ensure(late['provider_v1_authorizations']==0,'LATE_GRANT');e.close()
    return {'provider_denial_rollback_atomic':True,
            'C_semantic_event_queued_after_denial':True,
            'grant_and_P_absent_when_denied':True,
            'reopen_restored_provider_and_single_commit':True,
            'direct_P_mutation_rejected':True,
            'two_same_version_negative_votes_one_grant':True,
            'replay_and_restart_safe':True,
            'late_C_receipt_observed_without_grant':True,
            'native_port_denied':True,
            'privileged_host_can_rewrite_provider_and_database':True}

def report(root):
    root=Path(root)
    ensure(sha(root/'research/spk_v5_t10abc_def_ghi/reference/t9stu-vwx-yza-cumulative.json')==PARENT,'T9_PARENT_SHA_DRIFT')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    old=json.loads((root/'research/spk_v5_t10abc_def_ghi/reference/t9stu-vwx-yza-cumulative.json').read_text())
    serial=scenario('serial');naive=scenario('batch3');affinity=scenario('context_affinity')
    restart=scenario('context_affinity',restart=True)
    baseline=scenario('batch3',learn=False)
    for x,label in ((serial,'fenced_serial'),(naive,'fenced_naive'),
                    (affinity,'fenced_affinity'),(restart,'restarted_affinity'),
                    (baseline,'fixed_control')):
        prior=old['T9STU'].get(label) if label in old['T9STU'] else old['T9YZA'][label]
        ensure(x['successes']==prior['successes'] and x['waves']==prior['waves'] and
               x['stale_vetoes']==prior['stale_vetoes'] and x['reference_grants']==prior['reference_P_grants']
               and x['reference_P_writes']==prior['reference_P_writes'] and
               x['dispatch_slots']==prior['dispatcher_slots'], 'PROVIDER_PARITY_'+label)
        ensure(x['provider']['provider_v1_authorizations']==x['reference_grants'] and
               x['provider']['provider_v1_commits']==x['reference_P_writes'],'PROVIDER_AUTHORITY_COUNTS_'+label)
    ensure((naive['successes'],affinity['successes'],serial['successes'],baseline['successes'])==(84,88,88,48),'PROVIDER_OUTCOME_DRIFT')
    ensure((naive['waves'],affinity['waves'],serial['waves'])==(32,48,96),'PROVIDER_WAVE_DRIFT')
    ensure(affinity['provider']==restart['provider'] and affinity['core_rows_sha256']==restart['core_rows_sha256'],'PROVIDER_RESTART_DRIFT')
    witness=negative_witness()
    return {'schema':SCHEMA,'status':'REFERENCE_TICK_P_PROVIDER_ADMISSION_NO_NATIVE_MEMORY_ADOPTION',
        'T10ABC':{'provider_called_in_actual_C_semantic_tick_store_write':True,
                 'provider_veto_enforced_by_sqlite_UDF_trigger':True,
                 'provider_retains_independent_C_P_version_ledger':True,
                 'runtime_scheduler_source':'research.spk_v5_t9abc_def_ghi.concurrent_engine_v1',
                 'original_PE_compute_used':True,'admission_native_SPK':False},
        'T10DEF':{'reference_provider_scenarios':{'serial':serial,'naive_three':naive,
                                                'context_affinity':affinity,'fixed_control':baseline,
                                                'restarted_affinity':restart},
                  'outcome_parity_to_T9':True,'provider_v1_authorizations_in_affinity':8,
                  'grant_scope':'C/P/execute/exact-version/single-use',
                  'native_SPK_Memory_Contract_port':'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'},
        'T10GHI':{'negative_witness':witness,'reference_only_trust_boundary':True,
                  'independent_sender_authentication':False,
                  'privileged_host_can_forge':True},
        'source_T9STU_SHA256':PARENT,'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
        'original_source_pins':12,'new_frozen_scheduler_calls':0,
        'native_SPK_P_grants':0,'native_SPK_P_writes':0,'native_BV_semantic_deliveries':0,
        'native_learning':False,'host_can_forge':True,'promotion_allowed':False,
        'limits':['Provider is implemented and exercised only in new host-controlled research v1, not frozen SPK Memory Contract',
                  'Actual C receipt tick invokes separate provider via P-store trigger; it cannot grant outside this host context',
                  'Original PE _compute_local executes model semantics; episodes and A goals remain synthetic',
                  'Separate callback and SQLite constraints prevent ordinary unapproved writes, not malicious privileged host modification',
                  'Original SPK memory grant/writes, native semantic BV and native learning remain zero']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--out',required=True)
    a=ap.parse_args();p=Path(a.out);ensure(not p.exists() and not p.is_symlink(),'REPORT_EXISTS')
    result=report(a.root);p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T10ABC/DEF/GHI REFERENCE P ADMISSION PROVIDER PASS; ZERO NATIVE SPK LEARNING')
    print('reference_report_sha256',sha(p))
if __name__=='__main__':main()
