"""T9JKL/MNO/PQR cumulative observer, adaptive admission tradeoff and stale-credit boundary.
Only reference V1 research. No frozen scheduler edits, no native P/BV credit.
"""
from __future__ import annotations
import argparse, hashlib, json, tempfile
from pathlib import Path
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import PE_SHA,BV_SHA
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import (MultiTickEngine, Reject, ensure, pe_step, digest)
from .stale_evidence_v1 import attestable_stale, HistoricalEvidence
from .admission_frontier_v1 import run_strategy

PARENT_SHA='3e664630227170e105aa945f550518a442ac8ee08086ee13ff721163527b8b92'
SCHEMA='spk-v5-t9jkl-mno-pqr-historical-credit-frontier/research-v0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stale_credit_counterexample():
    """Observe real double-pending failure; compute *uncommitted* unsafe alternative."""
    with tempfile.TemporaryDirectory(prefix='spk-t9-veto-') as tmp:
        e=MultiTickEngine(Path(tmp)/'runtime.sqlite',max_inflight=3)
        ids=[e.submit(0,11),e.submit(0,11)]
        e.run();rows=[e.result(i) for i in ids]
        state=e.audit();historical=attestable_stale(e)
        ensure(len(historical)==1 and state['stale_vetoes']==1 and
               state['P_policy'][0]==11 and state['P_versions'][0]==1,'STALE_TEST_SETUP')
        # Hypothetical application of second negative vote would reverse the
        # correct current action. Crucially, this is NOT written to P.
        action=state['P_policy'][0];unsafe=12 if action==11 else 11
        frozen_C_good=pe_step('C',action,11,10,[1]);frozen_C_bad=pe_step('C',unsafe,11,10,[1])
        frozen_A_good=pe_step('A',action,11,12,[3 if action==11 else 4]);
        frozen_A_bad=pe_step('A',unsafe,11,12,[3 if unsafe==11 else 4])
        ensure(frozen_C_good['emits']==[11] and frozen_C_bad['emits']==[12] and
               frozen_A_good['emits']==[21,7] and frozen_A_bad['emits']==[22,7],
               'HYPOTHETICAL_NO_HARM_WITNESS')
        ledger=HistoricalEvidence(Path(tmp)/'observer.sqlite')
        tip=ledger.append(historical[0]);ledger.reopen()
        ensure(ledger.audit()['historical_records']==1 and ledger.audit()['P_grants']==0,'EVIDENCE_RECOVERY')
        try:ledger.append(historical[0])
        except Reject as ex:ensure(str(ex)=='HISTORICAL_REPLAY','REPLAY_WRONG_REASON')
        else:raise AssertionError('HISTORICAL_DUPLICATE_ACCEPTED')
        ensure(e.audit()==state,'OBSERVER_MUTATED_ENGINE')
        ledger.close();e.close()
    return {'two_concurrent_same_version_receipts':2,'one_reference_grant':1,
        'one_stale_observed_without_credit':True,'historical_reopen_and_replay_denial':True,
        'correct_C_action':action,'unsafe_hypothetical_recredit_action':unsafe,
        'correct_A_PE_verdict':'IMPROVED','unsafe_A_PE_verdict':'WORSENED',
        'native_SPK_P_writes':0}

def report(root):
    root=Path(root)
    p=root/'research/spk_v5_t9jkl_mno_pqr/reference/t9abc-def-ghi-cumulative.json'
    ensure(sha(p)==PARENT_SHA,'PARENT_T9_SHA_DRIFT')
    ensure(sha(root/'spk_architecture_v1/pe_execution_v1b.py')==PE_SHA,'FROZEN_PE_DRIFT')
    ensure(sha(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'FROZEN_BV_DRIFT')
    prior=json.loads(p.read_bytes());t9=prior['T9ABC']
    serial=run_strategy('serial')
    naive=run_strategy('batch3')
    affinity=run_strategy('context_affinity')
    recovered=run_strategy('batch3',reopen_each_wave=True)
    recovered_affinity=run_strategy('context_affinity',reopen_each_wave=True)
    control=run_strategy('batch3',learn=False)
    ensure((serial['successes'],naive['successes'],affinity['successes'],control['successes'])==(88,84,88,48),'FRONTIER_OUTCOME_DRIFT')
    ensure((serial['waves'],naive['waves'],affinity['waves'])==(96,32,48),'FRONTIER_WAVE_DRIFT')
    ensure((naive['stale_vetoes'],affinity['stale_vetoes'])==(4,0) and
        (naive['P_grants'],affinity['P_grants'])==(8,8),'FRONTIER_CREDIT_DRIFT')
    for name,row in [('serial_t8_parity',serial),('three_epoch_adaptive',naive),('two_epoch_adaptive',affinity),('three_epoch_control',control)]:
        prior_row=t9[name]
        ensure(row['core_rows_digest']==prior_row['rows_sha256'] and
            row['successes']==prior_row['successes'] and row['P_grants']==prior_row['grants'],
            'EXACT_INHERITED_CASE_PARITY_'+name)
    ensure(naive['core_rows_digest']==recovered['core_rows_digest'] and
       naive['historical_evidence']==recovered['historical_evidence'] and
       affinity['core_rows_digest']==recovered_affinity['core_rows_digest'] and
       affinity['historical_evidence']==recovered_affinity['historical_evidence'],
       'RESTARTED_FRONTIER_DRIFT')
    witness=stale_credit_counterexample()
    return {'schema':SCHEMA,'status':'HISTORICAL_STALE_CREDIT_QUARANTINE_AND_CONTEXT_AWARE_ADMISSION_RESEARCH_ONLY',
       'T9JKL':{'historical_veto_receipts':naive['historical_evidence']['historical_records'],
           'historical_evidence_ledger':naive['historical_evidence'],
           'historical_feedback_P_grants':0,'source_event_chain_audited':True,
           'old_policy_evidence_remains_observable':True},
       'T9MNO':{'naive_three_inflight':naive,'context_affinity':affinity,'serial':serial,
           'fixed_control':control,'same_task_sequence':True,
           'affinity_avoided_stale_vetoes':naive['stale_vetoes']-affinity['stale_vetoes'],
           'affinity_success_delta':affinity['successes']-naive['successes'],
           'extra_admission_waves_for_affinity':affinity['waves']-naive['waves'],
           'physical_latency_or_energy_measured':False,
           'effective_max_inflight_affinity':affinity['max_inflight_admitted']},
       'T9PQR':{'stale_credit_harm_counterexample':witness,
           'restarted_naive':recovered,'restarted_affinity':recovered_affinity,
           'credit_reinterpretation_permitted':False,'causal_attribution_of_stale_verdict_to_current_P':False,
           'source_host_can_reseal':True},
       'source_T9_SHA256':PARENT_SHA,'frozen_PE_sha256':PE_SHA,'frozen_BV_sha256':BV_SHA,
       'original_source_pins':12,'new_frozen_scheduler_calls':0,
       'native_BV_semantic_deliveries':0,'native_SPK_P_grants':0,'native_learning':False,
       'host_can_forge':True,'promotion_allowed':False,
       'limits':['Stale feedback stays observational: never authorized for a different P version',
           'Context-affinity reduces overlap by admitting at most one in-flight decision per cue, max two in this two-cue workload',
           'Admission waves are scheduling batches, not wall time, physical cycles or throughput on a deployed PE',
           'The original PE _compute_local is used by the reference runtime; original frozen BV-v0e remains untouched',
           'The fixed goals and episode sequence are host authored; there is no generalization to new tasks or sensors',
           'Observer hashes, P ledgers, and synthetic source can be forged/resealed by a privileged host',
           'No original SPK Memory Contract grant, native semantic BV, or native learning']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--out',required=True)
    a=parser.parse_args();out=Path(a.out)
    ensure(not out.exists() and not out.is_symlink(),'REPORT_EXISTS')
    data=report(a.root);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T9JKL/MNO/PQR HISTORICAL STALE CREDIT & ADMISSION FRONTIER RESEARCH PASS; ZERO NATIVE BV OR LEARNING')
    print('reference_report_sha256',sha(out))
if __name__=='__main__':main()
