"""One release gate for expanded three-choice native-v1 scheduler + durable P.

Fail closed if any original PE, BV, same-scheduler P lineage or state
continuity fails. Original BV-v0e is immutable and never called a learner.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1.generalized_case_v1t import setup,pin_sources
from spk_native_learning_v1.generalized_scheduler_v1t import (
  CHOICES_V1T,execute_resume_learning_v1r,LearningPlanV1,LiveBVPlanV0e)
from spk_native_learning_v1 import generalized_durable_v1t as d
from spk_native_learning_v1 import generalized_serial_v1t as s

SCHEMA='spk-native-learning-v1t-three-choice-macro-conformance/v1'
PARENT_SHA='af6c8323cc23f3eee8471751027532abd6919b6e7e6d325217acd3a03e679067'
PARENT_STATUS='NATIVE_V1S_COOPERATIVE_SERIAL_DURABLE_CHAIN_PASS'
CYCLE={11:12,12:15,15:11}

def check(value,code):
    if not value:raise AssertionError(code)

def baseline_frozen_parity():
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e as OldPlan
    args=setup(11,15)
    old=execute_live_v0e(*args,bv=OldPlan(assessor='A',max_ticks=256))
    new=execute_resume_learning_v1r(*args,bv=LiveBVPlanV0e(assessor='A',max_ticks=256),learn=LearningPlanV1(enabled=False))
    for field in ('states','emissions','terminal','processed_events','processed_batches','link_grants','occurrences'):
        check(old['forward'][field]==new['forward'][field], 'FROZEN_FORWARD_DRIFT_'+field)
    strip=lambda rows,fields:[{k:v for k,v in row.items() if k not in fields} for row in rows]
    check(old['forward']['batches']==strip(new['forward']['batches'],('P_choice','P_version')),'FROZEN_BATCH_DRIFT')
    for field in ('link_grants','unique_receiver_votes'):
        check(old['feedback'][field]==new['feedback'][field],'FROZEN_BV_DRIFT_'+field)
    check(old['feedback']['assessments']==strip(new['feedback']['assessments'],('A_PE_output','verdict')),'FROZEN_A_ASSESSMENTS_DRIFT')
    check(old['feedback']['deliveries']==strip(new['feedback']['deliveries'],('verdict',)),'FROZEN_BV_DELIVERIES_DRIFT')
    resources=dict(new['resources'])
    resources.pop('P_learning_service_units');resources.pop('P_learning_memory_units')
    resources['timeline']=[{k:v for k,v in row.items() if k!='P_learning_units'} for row in resources['timeline']]
    check(old['resources']==resources,'FROZEN_RESOURCE_PARITY_DRIFT')
    return {'frozen_3choice_PE_BV_parity':True,'original_batches':old['forward']['processed_batches'],'original_BV_deliveries':len(old['feedback']['deliveries'])}

def nine_pairs():
    results=[]
    for initial in CHOICES_V1T:
        for goal in CHOICES_V1T:
            args=setup(initial,goal)
            r=execute_resume_learning_v1r(*args,bv=LiveBVPlanV0e(assessor='A',max_ticks=256),learn=LearningPlanV1())
            reads=[(b['tick'],b['P_version'],b['P_choice'],b['outputs']) for b in r['forward']['batches'] if b['node']=='C']
            check(len(reads)==4 and reads[0][1:]==(0,initial,[initial]),'C_INITIAL_PE_MISMATCH')
            check(reads[-1][2]==goal and reads[-1][3]==[goal],'C_DID_NOT_LEARN_GOAL_PE')
            n=0;choice=initial
            while choice!=goal:
                choice=CYCLE[choice];n+=1
            check(r['learning']['final']['version']==n and len(r['learning']['grants'])==n,'P_GRANTS_NOT_VERSIONED')
            check(all(g['source_A_verdict']=='NEGATIVE' for g in r['learning']['grants']),'NON_NEGATIVE_P_GRANTED')
            verdicts=r['feedback']['assessments']
            check(len(verdicts)==4 and len(r['feedback']['deliveries'])==8,'A_PE_OR_BV_NOT_EXECUTED')
            check(all(x['A_PE_output']==(21 if reads[i][2]==goal else 22) for i,x in enumerate(verdicts)),'A_PE_COMPARATOR_NOT_USED')
            check(all(x['verdict']==('POSITIVE' if x['A_PE_output']==21 else 'NEGATIVE') for x in verdicts),'A_VERDICT_NOT_PE_DERIVED')
            check(r['resources']['P_learning_memory_units']==n and r['resources']['P_learning_service_units']==n,'P_RESOURCE_LEDGER_DRIFT')
            results.append({'initial':initial,'goal':goal,'C_PE_reads':[[t,v,c,outs] for t,v,c,outs in reads],
                            'PE_A_emissions':[x['A_PE_output'] for x in verdicts],
                            'P_grants':n,'BV_deliveries':len(r['feedback']['deliveries'])})
    return results

def durable_cross_epochs(root):
    with TemporaryDirectory(prefix='spk-nlv1t-') as td:
        path=Path(td)/'ledger.db'
        cases=((11,15),(11,15),(11,11))
        a=s.run_sequence(path,cases,root=root)
        b=s.run_sequence(path,cases,root=root)
        check(a['chain']==b['chain'] and b['new_tick_rows']==0,'NON_IDEMPOTENT_CHAIN')
        reads=a['C_PE_reads_by_epoch']
        check([r[0] for r in reads]==[[10,0,11,[11]],[10,2,15,[15]],[10,2,15,[15]]], 'C_PE_DID_NOT_INHERIT_P')
        check([x['P_to'] for x in a['chain']['epochs']]==[2,2,3],'CONTINUOUS_P_VERSION_MISMATCH')
        check(reads[0][-1]==[70,2,15,[15]] and reads[2][1]==[30,3,11,[11]],'PE_REAL_COMPUTE_UPDATED_PROGRAM_DRIFT')
        check(s.audit(path,root=root)==a['chain'],'CHAIN_AUDIT_NOT_DETERMINISTIC')
        recovery=[]
        for cut in (1,9,13,14,15,27,60):
            db=Path(td)/('cut-'+str(cut)+'.db')
            try:s.run_epoch(db,0,11,15,pause_after=cut,root=root)
            except d.SimulatedPowerLoss:pass
            else:raise AssertionError('CRASH_CUT_NOT_EXERCISED')
            r=s.run_epoch(db,0,11,15,root=root)
            check(r['epoch']['new_tick_rows']+cut==r['epoch']['tick_count'],'CRASH_REPLAY_DUPLICATION')
            check(r['epoch']['C_PE_reads']==reads[0],'CRASH_CHANGED_PE_PROGRAM')
            recovery.append({'cut':cut,'P_to':r['epoch']['final_P']['version'],'journal_sha256':r['epoch']['journal_head_sha256']})
        return {'epochs':len(cases),'versions':[x['P_to'] for x in a['chain']['epochs']],
                'committed_ticks':sum(e['tick_count'] for e in a['chain']['epochs']),
                'C_PE_reads_by_epoch':reads,'second_run_new_ticks':b['new_tick_rows'],
                'crash_recovery':recovery,'chain_sha256':a['chain']['chain_sha256']}

def report(root,parent):
    root=Path(root).resolve()
    source=Path(parent)
    check(source.is_file() and not source.is_symlink(),'V1S_PARENT_MISSING')
    check(hashlib.sha256(source.read_bytes()).hexdigest()==PARENT_SHA,'V1S_PARENT_SHA_DRIFT')
    prior=json.loads(source.read_text())
    check(prior['status']==PARENT_STATUS and prior['versioned_v1s_learning'] and not prior['original_v0e_learning'],'V1S_PARENT_INVALID')
    pins=pin_sources(root)
    check(prior['original_frozen_pins']==pins,'ORIGINAL_FROZEN_SOURCE_DRIFT')
    pairs=nine_pairs()
    parity=baseline_frozen_parity()
    durable=durable_cross_epochs(root)
    return {'schema':SCHEMA,'status':'NATIVE_V1T_THREE_CHOICE_SAME_SCHEDULER_DURABLE_LEARNING_PASS',
            'parent_v1s_sha256':PARENT_SHA,'frozen_original_source_pins':pins,
            'three_choice_pairs':pairs,'frozen_BV_disabled_learning_parity':parity,
            'durable_three_choice_chain':durable,'versioned_v1t_learning':True,
            'frozen_v0e_learning':False,'candidate_choices':list(CHOICES_V1T),
            'limitations':['bounded 3-node A/B/C and three enumerated C programs 11/12/15',
                           'negative feedback rotates through a PREDECLARED candidate set, no arbitrary program search',
                           'host-authored goal encoded in original A PE program; no independent goal issuer',
                           'A PE comparator is native primitive but semantic test environment remains synthetic',
                           'cooperative advisory flock, not privileged-host security or distributed consensus',
                           'persistence is original-event genesis replay, not heap restoration',
                           'no irreversible external actions, no physical sensing, no N-node topology proof',
                           'frozen v0e remains unchanged and DOES NOT natively learn']}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('output');ap.add_argument('--root',default='.')
    ap.add_argument('--parent',required=True)
    args=ap.parse_args()
    item=report(args.root,args.parent)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(item,indent=2,sort_keys=True,ensure_ascii=True)+'\n')
    print(item['status'],'PAIR_COUNT',len(item['three_choice_pairs']),
          'PE_P_VERSIONS',item['durable_three_choice_chain']['versions'])
