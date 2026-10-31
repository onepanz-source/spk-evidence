"""SPK v1u context bank release gate witness (no source pin bypass)."""
from __future__ import annotations
import hashlib,json,sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1 import contextual_serial_v1u as s,contextual_durable_v1u as d
from spk_native_learning_v1.generalized_case_v1t import pin_sources
SCHEMA='spk-native-learning-v1u-contextual-conformance/v1'
PARENT_SHA='6f11c639729d99c84907fa42e164714f014f93a8af3c0149ab6db40ae1788f8b'
PARENT_STATUS='NATIVE_V1T_THREE_CHOICE_SAME_SCHEDULER_DURABLE_LEARNING_PASS'
CASES=(('alpha',11,15),('beta',11,12),('alpha',11,15),('beta',11,12),('alpha',11,11))
def need(ok,tag):
    if not ok:raise AssertionError(tag)
def report(root,parent):
    parent=Path(parent)
    need(parent.is_file() and not parent.is_symlink(),'PARENT_ABSENT')
    need(hashlib.sha256(parent.read_bytes()).hexdigest()==PARENT_SHA,'PARENT_SHA_DRIFT')
    prior=json.loads(parent.read_text()); pins=pin_sources(root)
    need(prior['status']==PARENT_STATUS and prior['versioned_v1t_learning'] and not prior['frozen_v0e_learning'],'PARENT_STATUS_INVALID')
    need(prior['frozen_original_source_pins']==pins,'ORIGINAL_FROZEN_PIN_DRIFT')
    with TemporaryDirectory(prefix='spk-nlv1u-') as t:
        path=Path(t)/'causal.db'
        a=s.run_sequence(path,CASES,root=root);b=s.run_sequence(path,CASES,root=root)
        need(b['new_tick_rows']==0 and b['chain']==a['chain'],'NONDETERMINISTIC_CONTEXT_REPLAY')
        need([e['P_to'] for e in a['chain']['epochs']]==[2,1,2,1,3],'BAD_P_VERSIONS')
        need(a['P_grants_by_epoch']==[2,1,0,0,1],'CROSS_CONTEXT_P_LEAK')
        expected=[[10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],
                  [10,1,12,[12]],[10,2,15,[15]]]
        reads=[x[0] for x in a['C_PE_reads_by_epoch']]
        need(reads==expected,'ACTUAL_PE_DID_NOT_READ_CONTEXT_P')
        need(a['new_tick_rows']==325,'CAUSAL_TICK_COUNT_DRIFT')
        need(s.audit(path,root=root)==a['chain'],'AUDIT_DRIFT')
        reverse=s.run_sequence(Path(t)/'ba.db',(CASES[1],CASES[0]),root=root)
        left=s.run_sequence(Path(t)/'ab.db',CASES[:2],root=root)
        need(left['chain']['bank']==reverse['chain']['bank'],'CONTEXT_ORDER_INTERFERED_WITH_P')
        need(left['chain']['chain_sha256']!=reverse['chain']['chain_sha256'],'ORDER_NOT_COMMITTED')
        cuts=[]
        for cut in (1,9,13,14,15,27,60):
            p=Path(t)/f'cut-{cut}.db'
            try:s.run_epoch(p,0,'alpha',11,15,pause_after=cut,root=root)
            except d.SimulatedPowerLoss:pass
            else:raise AssertionError('CUT_NOT_EXERCISED')
            recovered=s.run_epoch(p,0,'alpha',11,15,root=root)
            need(recovered['episode']['new_tick_rows']+cut==65,'CRASH_DUPLICATION')
            need(recovered['episode']['final_P']['version']==2,'RECOVERY_P_DRIFT')
            cuts.append({'cut':cut,'head_sha256':recovered['episode']['journal_head_sha256']})
        corrupt=Path(t)/'tamper.db';s.run_epoch(corrupt,0,'alpha',11,15,root=root)
        with sqlite3.connect(corrupt) as db:db.execute("UPDATE ctx_ticks SET snapshot='{}' WHERE epoch=0 AND seq=10")
        try:s.run_epoch(corrupt,1,'beta',11,12,root=root)
        except d.ContextReject:denial='REJECTED'
        else:raise AssertionError('TAMPER_ACCEPTED')
        return {'schema':SCHEMA,'status':'NATIVE_V1U_CONTEXTUAL_P_SAME_SCHEDULER_CAUSAL_PASS',
                'parent_v1t_sha256':PARENT_SHA,'original_frozen_pins':pins,
                'contextual_epoch_count':5,'committed_tick_rows':a['new_tick_rows'],
                'contextual_versions':[e['P_to'] for e in a['chain']['epochs']],
                'contextual_grants':a['P_grants_by_epoch'],
                'actual_original_PE_reads':reads,'bank':a['chain']['bank'],
                'second_run_new_tick_rows':b['new_tick_rows'],
                'chain_sha256':a['chain']['chain_sha256'],
                'context_order_independent_P_bank':True,
                'context_order_not_erased_from_ledger':True,
                'restart_cuts':cuts,'prior_tamper':denial,
                'native_v1_research_learning':True,'frozen_original_BV_learning':False,
                'host_controls_context_labels':True,'promotion_allowed':False,
                'limitations':['Three predeclared PE programs and A/B/C corpus only',
                 'Context identity and A target remain host-authored and unauthenticated',
                 'No arbitrary programs, N-node topology or physical validation',
                 'Deterministic genesis replay only, no irreversible outside effects',
                 'Cooperative advisory locking, no resistance to privileged host',
                 'Frozen original BV-v0e stays unchanged and learning-free']}
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('output');ap.add_argument('--root',default='.')
 ap.add_argument('--parent',required=True);args=ap.parse_args()
 r=report(args.root,args.parent);p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
 print(r['status'],'EPOCHS',r['contextual_epoch_count'],'TICKS',r['committed_tick_rows'])
