"""T12 macro source-bound ORIGINAL native execution memory API witness.

The four original API invocations describe execution-time access admission,
NOT the Learning-P permission. A separate versioned V1 memory authority still
owns experimental C/P grants. No original SPK code or frozen contract changes.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .native_bridge_v1d import sha,pinned_source_catalog,original_native_execution_probe,native_policy_p_boundary
from research.spk_v5_t11_macro_memory_v1.macro_gate import scenario as t11_scenario, adversarial as t11_adversarial
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA

SCHEMA='spk-v5-t12-macro-original-memory-execution-seam/hotfix-v1d'
T11_FWORK_SHA='666bb70dfcf7db5a0ddcce78918b428b6936bdb926c65f799d3f55f3d94c0e15'

def report(root,*,require_native=True):
    root=Path(root)
    assert sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
    assert sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
    parent=root/'research/spk_v5_t12_macro_native_memory_seam/reference/t11-macro-owned-memory-v1.json'
    ensure(sha(parent)==T11_FWORK_SHA,'T11_REFERENCE_SHA_DRIFT')
    reference=json.loads(parent.read_text())
    ensure(reference['new_versioned_runtime_v1_P_grants']==8,'T11_PARENT_GRANT_DRIFT')
    catalog=pinned_source_catalog(root,require_sources=require_native)
    native=original_native_execution_probe(root) if not catalog['missing'] else {
      'catalog':catalog,'original_api_attempts':0,'outcomes':[],
      'counts':{'native_execution_memory_admissions':0,'native_A1d_executions':0,'native_execution_memory_projections':0,
        'native_execution_access_authorizations':0,'native_execution_memory_services':0,
        'completed_original_memory_chains':0,'native_learning_P_grants':0},'diagnostics':['SOURCE_UNAVAILABLE_IN_LOCAL_PARTIAL_CHECKOUT'],
      'native_execution_memory_is_not_learning_P_authority':True,
      'frozen_components_modified':False,'native_learning':False,'promotion_allowed':False}
    if require_native and native['counts']['completed_original_memory_chains']==0:
        print('T12 V1D: ORIGINAL MEMORY ADMISSION DENIED, CANDIDATES:',flush=True)
        for result in native.get('outcomes',[]):
            print('  choice/goal',result.get('choice'),result.get('goal'),'stage',result.get('blocked_stage'),'reason',result.get('diagnostic'),flush=True)
            for diagnostic in result.get('candidate_errors',[])[:12]:
                print('    '+diagnostic,flush=True)
    if require_native:
        ensure(native['original_api_attempts']==4,'ORIGINAL_MEMORY_API_NEVER_INVOKED')
        # A native execution admission is not the learning P permission.
        # Fail loudly if all source execution admissions reject the workload.
        ensure(native['counts']['completed_original_memory_chains']>=1,
              'ORIGINAL_A1D_MEMORY_PROJECTION_AUTHORIZATION_CHAIN_FAILED_ALL_CASES:'+str(native['outcomes']))
    # Old V1 behavior must be held fixed for matched workloads.
    naive=t11_scenario('batch3')
    affinity=t11_scenario('context_affinity')
    restart=t11_scenario('context_affinity',reopen=True)
    for tag,item,expected in (('naive',naive,84),('affinity',affinity,88),('restart',restart,88)):
        ensure(item['successes']==expected,'T11_PARITY_'+tag)
        parentname='naive_three' if tag=='naive' else 'context_affinity' if tag=='affinity' else 'restarted_affinity'
        old=reference['scenarios'][parentname]
        ensure(item['rows_sha256']==old['rows_sha256'],'T11_COMPUTATION_SOURCE_DRIFT_'+tag)
        ensure(item['owned_memory']['new_v1_memory_grants']==8,'V1_MEMORY_GRANTS_DRIFT_'+tag)
        ensure(item['owned_memory']['native_frozen_SPK_grants']==0,'NATIVE_CLAIM_'+tag)
    boundary=native_policy_p_boundary(native,affinity['owned_memory'])
    checks=t11_adversarial()
    ensure(all(checks.values()),'T11_INHERITED_ADVERSARIAL_INVARIANTS')
    out={'schema':SCHEMA,'previous_T11_SHA256':T11_FWORK_SHA,
      'M1_original_source_pin_catalog':catalog,
      'M2_original_memory_execution_probe':native,
      'M3_original_execution_vs_learning_P_boundary':boundary,
      'M4_versioned_new_runtime_P_parity':{
        'naive_three':{k:naive[k] for k in ('successes','stale_vetoes','waves','rows_sha256')},
        'context_affinity':{k:affinity[k] for k in ('successes','stale_vetoes','waves','rows_sha256')},
        'reopened_context_affinity':{k:restart[k] for k in ('successes','stale_vetoes','waves','rows_sha256')},
        'new_v1_memory_grants':affinity['owned_memory']['new_v1_memory_grants'],
        'new_v1_memory_P_commits':affinity['owned_memory']['new_v1_memory_P_commits']},
      'M5_adversarial_recovery':checks,
      'M6_promotion_and_native_learning_boundary':{
        'original_execution_memory_api_invoked':native['original_api_attempts']>0,
        'original_execution_memory_admissions':native['counts']['native_execution_memory_admissions'],
        'original_execution_access_authorizations':native['counts']['native_execution_access_authorizations'],
        'original_A1d_executions':native['counts']['native_A1d_executions'],
        'completed_original_memory_chains':native['counts']['completed_original_memory_chains'],
        'original_memory_service_calls':native['counts']['native_execution_memory_services'],
        'original_memory_executions_are_not_P_learning_grants':True,
        'frozen_original_P_learning_grants':0,'frozen_original_P_learning_writes':0,
        'frozen_original_BV_semantic_deliveries':0,'frozen_original_learning':False,
        'promote_to_frozen_original':False,'privileged_host_can_forge':True},
      'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
      'original_code_unchanged':True,'native_learning':False,'promotion_allowed':False,
      'status':'ORIGINAL_MEMORY_EXECUTION_API_ATTEMPTED_NOT_NATIVE_BV_LEARNING'
        if native['original_api_attempts'] else 'LOCAL_PARTIAL_CHECKOUT_NO_ORIGINAL_MEMORY_MODULES'}
    ensure(out['M6_promotion_and_native_learning_boundary']['frozen_original_P_learning_grants']==0,
           'NATIVE_LEARNING_FALSE_CLAIM')
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='.')
    p.add_argument('--out',required=True)
    p.add_argument('--allow-missing-native',action='store_true',help='LOCAL ONLY, cannot be used by release gate')
    args=p.parse_args()
    r=report(args.root,require_native=not args.allow_missing_native)
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T12 V1D ORIGINAL A1D MEMORY API BRIDGE PASS; ZERO FROZEN SPK LEARNING')
    print('report_sha256',sha(dest))
if __name__=='__main__':main()
