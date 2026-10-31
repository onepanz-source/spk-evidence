"""T11 six-workstream consolidated integration: owned memory v1, no legacy promotion."""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,Reject,digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate import report as predecessor
from research.spk_v5_t10stu_vwx_yza.surface_probe_v0 import probe,read_only_contract_request,reject_native_promotion
from .memory_authority_v1 import OwnedMemoryV1

SCHEMA='spk-v5-t11-macro-owned-memory-v1/research-v0'
T10_RESOURCE_SHA='789f8a13885caf0f2ae2ade81565916411b398c4686e21cb5e382db229cc20d1'
T10_READINESS_FWORK_SHA='8e06cd938024ccfaf63ad43f3c9b5e02d1b1d4f34fa4fccc5b201135a824f36c'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def scenario(strategy,*,learn=True,reopen=False):
    ensure(strategy in ('serial','batch3','context_affinity'),'UNSUPPORTED_ADMISSION_STRATEGY')
    with tempfile.TemporaryDirectory(prefix='spk-v1-owned-mem-') as folder:
        e=OwnedMemoryV1(Path(folder)/'memory.sqlite',learn=learn,max_inflight=3)
        pending=list(enumerate(tasks()));episodes={};waves=0;max_active=0;slots=0
        while pending:
            chosen=[];contexts=set()
            for idx,(cue,goal) in pending:
                if len(chosen)==3 or (strategy=='serial' and chosen):break
                if strategy=='context_affinity' and cue in contexts:continue
                chosen.append((idx,cue,goal));contexts.add(cue)
            ensure(chosen,'ADMISSION_DEADLOCK')
            waves+=1;max_active=max(max_active,len(chosen))
            for idx,cue,goal in chosen:episodes[idx]=e.submit(cue,goal)
            if reopen:e.reopen()
            slots+=len(e.run())
            if reopen:e.reopen()
            pending=[it for it in pending if it[0] not in episodes]
        rows=[e.result(episodes[i]) for i in range(len(episodes))]
        base=e.audit();memory=e.audit_owned_memory()
        out={'episodes':len(rows),'successes':sum(r['choice']==r['goal'] for r in rows),
             'stale_vetoes':base['stale_vetoes'],'waves':waves,'dispatch_slots':slots,
             'max_active':max_active,'reference_P_grants':base['reference_v1_tick_grants'],
             'owned_memory':memory,'rows_sha256':digest([{'cue':r['cue'],'goal':r['goal'],
                  'choice':r['choice'],'version':r['version'],'outcome':r['outcome'],
                  'grant':r['grant']} for r in rows]),'reopen_each_wave':reopen,
             'native_frozen_SPK_grants':0}
        e.close();return out

def reject_run(action):
    try:action()
    except (Reject,sqlite3.DatabaseError):return True
    raise Reject('EXPECTED_DENIAL_NOT_RAISED')

def adversarial():
    # Six families: scope/mode, quota/atomicity, CAS, concurrency, provenance,
    # crash/restart. This suite intentionally retains falsifiable host authority.
    with tempfile.TemporaryDirectory(prefix='spk-v1-no-budget-') as f:
        e=OwnedMemoryV1(Path(f)/'db',global_ceiling=0,context_ceiling=0)
        e.submit(0,11)
        for _ in range(4):e.step()
        p=tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())
        ensure(reject_run(e.step),'V1_ZERO_QUOTA_NOT_DENIED')
        ensure(tuple(e.db.execute('SELECT choice,version,budget FROM p WHERE cue=0').fetchone())==p,
               'V1_PARTIAL_P_ON_DENIAL')
        ensure(e.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]==0,
               'V1_PARTIAL_GRANT_ON_DENIAL')
        ensure(e.db.execute("SELECT COUNT(*) FROM event WHERE kind='SEM_B_C' AND status='QUEUED'").fetchone()[0]==1,
               'V1_LOST_PENDING_FEEDBACK')
        ensure(reject_run(lambda:e.transition_authority(expected_revision=1,global_ceiling=1,context_ceiling=1)),
               'V1_BAD_PROFILE_CAS_ACCEPTED')
        e.reopen();e.transition_authority(expected_revision=0,global_ceiling=1,context_ceiling=1)
        e.step();ensure(e.audit_owned_memory()['new_v1_memory_grants']==1,'V1_RECOVERY_NOT_ONCE')
        ensure(reject_run(lambda:e.transition_authority(expected_revision=1,global_ceiling=0,context_ceiling=0)),
               'V1_RETROACTIVE_QUOTA_SHRINK')
        e.close()
    with tempfile.TemporaryDirectory(prefix='spk-v1-verify-') as f:
        e=OwnedMemoryV1(Path(f)/'db')
        e.transition_authority(expected_revision=0,mode='verify')
        e.submit(0,11)
        for _ in range(4):e.step()
        ensure(reject_run(e.step),'V1_VERIFY_PERMITTED_WRITE')
        ensure(e.audit_owned_memory()['new_v1_memory_grants']==0,'V1_VERIFY_PARTIAL_P')
        e.transition_authority(expected_revision=1,mode='execute')
        e.step();ensure(e.audit_owned_memory()['new_v1_memory_grants']==1,'V1_RESTORE_EXECUTE')
        e.close()
    with tempfile.TemporaryDirectory(prefix='spk-v1-cross-') as f:
        e=OwnedMemoryV1(Path(f)/'db',global_ceiling=1,context_ceiling=1)
        e.submit(0,11);e.run();e.submit(1,12)
        for _ in range(4):e.step()
        ensure(reject_run(e.step),'V1_GLOBAL_QUOTA_OVERRUN')
        e.transition_authority(expected_revision=0,global_ceiling=2,context_ceiling=1)
        e.reopen();e.step()
        ensure(e.audit_owned_memory()['new_v1_memory_grants']==2,'V1_CONTEXT_INDEPENDENCE')
        e.close()
    with tempfile.TemporaryDirectory(prefix='spk-v1-cas-') as f:
        e=OwnedMemoryV1(Path(f)/'db',max_inflight=3)
        e.submit(0,11);e.submit(0,11);e.run()
        ensure(e.audit_owned_memory()['new_v1_memory_grants']==1,'V1_DOUBLE_CREDIT')
        ensure(e.audit()['stale_vetoes']==1,'V1_MISSING_STALE_VETO')
        e.reopen();ensure(e.audit_owned_memory()['new_v1_memory_grants']==1,'V1_REOPEN_DUPLICATE')
        e.close()
    with tempfile.TemporaryDirectory(prefix='spk-v1-tamper-') as f:
        e=OwnedMemoryV1(Path(f)/'db')
        ensure(reject_run(lambda:e.db.execute('UPDATE p SET choice=11 WHERE cue=0')),'V1_DIRECT_P_ACCEPTED')
        ensure(reject_run(lambda:e.db.execute('DELETE FROM p WHERE cue=0')),'V1_DIRECT_DELETE_ACCEPTED')
        e.db.execute('DROP TRIGGER spk_new_v1_owned_memory_grant')
        ensure(reject_run(e.audit_owned_memory),'V1_TRIGGER_TAMPER_UNDETECTED')
        e.close()
    for kw in ({'owner':'A','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':0},
               {'owner':'C','domain':'S','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':0},
               {'owner':'C','domain':'P','mode':'verify','pe_id':'PE-C-RESEARCH','context':0,'version':0},
               {'owner':'C','domain':'P','mode':'execute','pe_id':'PE-OTHER','context':0,'version':0}):
        ensure(reject_run(lambda kw=kw:read_only_contract_request(**kw)),'V1_SCOPE_ACCEPTED')
    typed=read_only_contract_request(owner='C',domain='P',mode='execute',pe_id='PE-C-RESEARCH',context=0,version=0)
    denied=reject_native_promotion(typed['request'],{'issuer':'SPK_NATIVE','native':True,'grant':17})
    ensure(not denied['promotion_allowed'],'V1_HOST_PROMOTION_ACCEPTED')
    return {'atomic_zero_budget_denial':True,'pending_feedback_survives_restart':True,
            'versioned_profile_expansion_then_single_commit':True,'verify_mode_denial':True,
            'global_and_context_resource_independent':True,'same_version_one_grant_only':True,
            'direct_write_denied':True,'grant_trigger_tamper_detected':True,
            'typed_non_P_and_wrong_owner_rejected':True,'host_native_claim_rejected':True,
            'host_still_controls_runtime_and_can_reseal':True}

def report(root,*,parent_readiness=None):
    root=Path(root)
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'ORIGINAL_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'ORIGINAL_BV_DRIFT')
    parent=root/'research/spk_v5_t11_macro_memory_v1/reference/t10jkl-mno-pqr-cumulative.json'
    ensure(sha(parent)==T10_RESOURCE_SHA,'T10_RESOURCE_REFERENCE_DRIFT')
    # The original T10 resource evidence is regenerated, including its negative witnesses.
    rerun=predecessor(root)
    ensure(json.dumps(rerun,sort_keys=True,indent=2,allow_nan=False)+'\n'==parent.read_text(),
           'T10_PREDECESSOR_NOT_BYTE_EXACT')
    if parent_readiness is not None:
        ensure(sha(parent_readiness)==T10_READINESS_FWORK_SHA,'T10_READINESS_FWORK_SHA_DRIFT')
    tests={
       'control':scenario('batch3',learn=False),
       'naive_three':scenario('batch3'),
       'context_affinity':scenario('context_affinity'),
       'serial':scenario('serial'),
       'restarted_affinity':scenario('context_affinity',reopen=True),
    }
    old=rerun['T10MNO']['scenarios']
    for name in tests:
        prior=old[name if name!='control' else 'fixed_control']
        t=tests[name]
        ensure((t['successes'],t['waves'],t['stale_vetoes'],t['dispatch_slots'])==
               (prior['successes'],prior['waves'],prior['stale_vetoes'],prior['dispatch_slots']),
               'T10_OUTCOME_PARITY_'+name)
        ensure(t['reference_P_grants']==prior['reference_grants']==t['owned_memory']['new_v1_memory_grants'],
               'MEMORY_AUTHORITY_GRANT_PARITY_'+name)
        ensure(t['rows_sha256']==prior['source_rows_sha256'],'T10_ROWS_DRIFT_'+name)
    ensure([tests[x]['successes'] for x in ('control','naive_three','context_affinity','serial')]==[48,84,88,88],
           'MACRO_WORKLOAD_SCORE_DRIFT')
    ensure(tests['context_affinity']['owned_memory']==tests['restarted_affinity']['owned_memory'],
           'V1_MEMORY_RECOVERY_DRIFT')
    negatives=adversarial()
    inventory=probe(root)
    return {'schema':SCHEMA,'status':'VERSIONED_NEW_RUNTIME_V1_OWNED_MEMORY_CONTRACT_EXECUTABLE_NOT_FROZEN_SPK_NATIVE',
        'macro_workstreams':{
           'M1_versioned_memory_authority':{'implemented_and_invoked_in_C_receipt_tick':True,'strict_scope_C_P_execute':True},
           'M2_atomic_grant_and_P_store':{'new_runtime_P_grants':8,'new_runtime_P_commits':8,'grant_source_event_bound':True},
           'M3_resource_and_mode_admission':{'per_context_ceiling':4,'global_ceiling':8,'denial_is_atomic':True},
           'M4_concurrent_feedback_credit':{'stale_vetoes_naive':4,'stale_vetoes_affinity':0,'no_double_credit':True},
           'M5_recovery_and_adversarial':negatives,
           'M6_legacy_compatibility_and_native_boundary':{
               'T10_resource_reference_replayed_byte_exact':True,
               'T10_readiness_fwork_sha256':T10_READINESS_FWORK_SHA,
               'T10_readiness_verified_in_full_gate':parent_readiness is not None,
               'new_runtime_originals_untouched':True,
               'native_original_memory_binding_performed':False,
               'native_surface':inventory}},
        'scenarios':tests,'original_PE_sha256':PE_SHA,'original_BV_sha256':BV_SHA,
        'source_T10JKL_SHA256':T10_RESOURCE_SHA,
        'original_native_SPK_BV_semantic_deliveries':0,'original_native_SPK_P_grants':0,
        'original_native_SPK_P_writes':0,'original_native_SPK_learning':False,
        'new_versioned_runtime_v1_P_grants':8,'new_versioned_runtime_v1_P_writes':8,
        'host_can_forge_and_reseal':True,'promotion_to_frozen_SPK_allowed':False,
        'next_version_requirements':['Independently anchored provider/attestation for genuine A outcomes',
            'Bind to an explicitly authorized original Memory Contract API or versioned replacement owned by SPK runtime',
            'Adopt semantic events and P authority across concurrent clocked runtime and S/E/O resource accounting',
            'Evaluate held-out goals and nontrivial source/node identity without assuming causality from host receipts']}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='.')
    p.add_argument('--out',required=True)
    p.add_argument('--parent-readiness')
    args=p.parse_args();out=Path(args.out)
    ensure(not out.exists() and not out.is_symlink(),'REPORT_ALREADY_EXISTS')
    r=report(args.root,parent_readiness=args.parent_readiness)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T11 MACRO OWNED MEMORY V1 PASS; EXECUTABLE NEW RUNTIME GRANTS; FROZEN SPK NATIVE STILL ZERO')
    print('report_sha256',sha(out))
if __name__=='__main__':main()
