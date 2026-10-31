"""T13 macro: original execution memory access becomes a live research P prerequisite.

T12 demonstrated four original complete chains OUTSIDE the reference P clock.
T13 requires the original chain at each genuine reference negative C receipt
before its P transition. Neither chain represents native learning authority.
"""
from __future__ import annotations
import argparse, json, tempfile
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, digest
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from .access_guard_v1 import OriginalAccessGatedV1,original_execution_access_for_choice,ORIGINAL_A1D_SHA

SCHEMA='spk-v5-t13-macro-original-execution-access-on-live-C-P-ticks/research-v0'
PARENT_T12_SHA='af405aeef4e0c5a0de1279077b6e6c228527b3b229a22124b6bc372f45767475'


def run_scenario(root,*,strategy='context_affinity',test_callback=None,reopen=False):
    ensure(strategy in ('batch3','context_affinity','serial'),'T13_STRATEGY_DOMAIN')
    fake=test_callback is not None
    with tempfile.TemporaryDirectory(prefix='spk-t13-original-access-') as tmp:
        e=OriginalAccessGatedV1(Path(tmp)/'runtime.sqlite',root=root,learn=True,max_inflight=3,
                                test_witness=test_callback,test_only=fake)
        queue=list(enumerate(tasks()));indexes={};waves=0;slots=0;max_active=0
        while queue:
            chosen=[];contexts=set()
            for idx,(cue,goal) in queue:
                if len(chosen)>=3 or (strategy=='serial' and chosen):break
                if strategy=='context_affinity' and cue in contexts:continue
                chosen.append((idx,cue,goal));contexts.add(cue)
            ensure(chosen,'T13_ADMISSION_DEADLOCK')
            for idx,cue,goal in chosen:indexes[idx]=e.submit(cue,goal)
            waves+=1;max_active=max(max_active,len(chosen))
            if reopen:e.reopen()
            slots+=len(e.run())
            if reopen:e.reopen()
            queue=[item for item in queue if item[0] not in indexes]
        result=[e.result(indexes[i]) for i in range(len(indexes))]
        original=e.audit_original_access();memory=e.audit_owned_memory();base=e.audit()
        row_digest=digest([{'cue':r['cue'],'goal':r['goal'],'choice':r['choice'],
                            'version':r['version'],'outcome':r['outcome'],
                            'grant':r['grant']} for r in result])
        out={'episodes':len(result),'successes':sum(r['choice']==r['goal'] for r in result),
             'row_digest':row_digest,'waves':waves,'dispatcher_slots':slots,
             'max_active':max_active,'stale_vetoes':base['stale_vetoes'],
             'reference_P_grants':base['reference_v1_tick_grants'],
             'v1_owned_memory_P_commits':memory['new_v1_memory_P_commits'],
             'original_witness':original,'test_only':fake,
             'original_SPK_learning_P_grants':0,'original_SPK_learning':False}
        ensure(original['new_runtime_v1_P_grants']==out['reference_P_grants'] and
               original['same_tick_transaction'],'T13_WITNESS_GRANT_CUSTODY')
        e.close();return out


def report(root,*,strict=True):
    root=Path(root).resolve(strict=True)
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'T13_ORIGINAL_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'T13_ORIGINAL_BV_DRIFT')
    parent=root/'research/spk_v5_t13_macro_original_access_guard/reference/t12-complete-chain.json'
    ensure(sha(parent)==PARENT_T12_SHA,'T13_T12_PARENT_SOURCE_DRIFT')
    old=json.loads(parent.read_text())
    ensure(old['M2_original_memory_execution_probe']['counts']['completed_original_memory_chains']==4,
           'T13_PARENT_ORIGINAL_INCOMPLETE')
    # Genuine original sources are mandatory in release mode. No test-only
    # callback, host-supplied status, or fake native API is permitted.
    catalog=pinned_source_catalog(root,require_sources=strict)
    ensure(not strict or catalog['original_count']==5,'T13_MISSING_ORIGINAL_API')
    if strict:
        ensure(sha(root/'spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA,
               'T13_A1D_SOURCE_UNPINNED')
        affinity=run_scenario(root,strategy='context_affinity')
        ensure(not affinity['test_only'] and affinity['original_witness']['original_access_witnesses']==8,
               'T13_ORIGINAL_SOURCE_NOT_IN_C_TICK')
    else:
        def test_only_stub(choice,goal):
            return {'kind':'TEST_ONLY','choice':choice,'goal':goal,'original_learning_P_grants':0}
        affinity=run_scenario(root,strategy='context_affinity',test_callback=test_only_stub)
    old_affinity=old['M4_versioned_new_runtime_P_parity']['context_affinity']
    ensure(affinity['successes']==88 and affinity['waves']==48 and
           affinity['row_digest']==old_affinity['rows_sha256'] and
           affinity['reference_P_grants']==8 and affinity['v1_owned_memory_P_commits']==8 and
           affinity['original_witness']['original_learning_P_grants']==0,
           'T13_V1_ADAPTATION_PARITY_OR_ORIGINAL_CUSTODY_DRIFT')
    # Fail closed if a test-only witness appears in a release-bound report.
    ensure(not strict or affinity['original_witness']['witness_kind']=='ORIGINAL_A1D_EXECUTION_ACCESS',
           'T13_TEST_PROOF_PROMOTION')
    out={'schema':SCHEMA,'source_T12_SHA256':PARENT_T12_SHA,
         'frozen_BV_sha256':BV_SHA,'frozen_PE_sha256':PE_SHA,
         'original_A1d_sha256':ORIGINAL_A1D_SHA,
         'original_memory_catalog_sha256':catalog['catalog_sha256'],
         'M1_original_chain_completed_T12':4,
         'M2_original_access_gates_live_C_tick':{
             'required_for_each_reference_P_write':True,'actual_A1d_execution_during_provider_authorization':strict,
             'same_tick_SQL_transaction_and_rollback':True,
             'matching_choice_and_goal_required':True,'original_P_learning_authority':False},
         'M3_reference_v1_runtime':affinity,
         'M4_old_vs_new':{'old_successes':88,'new_successes':affinity['successes'],
                           'old_rows_digest':old_affinity['rows_sha256'],
                           'new_rows_digest':affinity['row_digest'],
                           'same_grants':True},
         'M5_boundary':{'test_only_release_forbidden':strict,'original_P_learning_grants':0,
                        'original_P_learning_writes':0,'original_BV_semantic_feedback':0,
                        'host_source_authenticated':False,'privileged_host_can_reseal':True,
                        'original_memory_access_not_equivalent_to_learning':True},
         'production_original_A1d_invoked_during_C_tick':strict,
         'original_learning':False,'native_learning':False,
         'promotion_allowed':False,
         'status':'T13_ORIGINAL_EXECUTION_ACCESS_ON_LIVE_REFERENCE_C_TICK_NOT_NATIVE_P_LEARNING'
                   if strict else 'T13_LOCAL_TEST_ONLY_NO_ORIGINAL_EXECUTION'}
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='.')
    ap.add_argument('--out',required=True)
    ap.add_argument('--local-test-only',action='store_true',help='NOT FOR RELEASE; test callback, zero original executions')
    args=ap.parse_args()
    out=Path(args.out);ensure(not out.exists() and not out.is_symlink(),'T13_REPORT_EXISTS')
    result=report(args.root,strict=not args.local_test_only)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print('T13 MACRO ORIGINAL A1D EXECUTION ACCESS GATES C-TICK REFERENCE P; NO ORIGINAL SPK LEARNING'
          if not args.local_test_only else 'T13 LOCAL TEST-ONLY PARITY PASS; NO ORIGINAL EXECUTION')
    print('report_sha256',sha(out))
if __name__=='__main__':main()
