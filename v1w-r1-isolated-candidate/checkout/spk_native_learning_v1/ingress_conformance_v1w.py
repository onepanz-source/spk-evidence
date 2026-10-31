"""Strict full-repository v1w queued/PE/BV/P conformance.

No test doubles in the release path. Exact parent v1v and frozen source pins.
"""
from __future__ import annotations
import argparse,hashlib,json,sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1 import ingress_scheduler_v1w as w
from spk_native_learning_v1 import contextual_durable_v1u as d
from spk_native_learning_v1 import sensed_context_v1v as sense
from spk_native_learning_v1.generalized_case_v1t import pin_sources

SCHEMA='spk-native-learning-v1w-durable-queued-ingress-conformance/v1'
PARENT_SHA='172b2a1c72a526ca3cc49d9792d4d765b606f7d4b346f43a46ddc2ef50fdd59c'
PARENT_STATUS='V1V_PE_SENSED_CONTEXT_P_RECALL_PASS'
CASES=(((40,42),11,15),((41,43),11,12),((40,42,99),11,15),
       ((41,43,99),11,12),((40,42),11,11))

def demand(ok,reason):
    if not ok:raise AssertionError(reason)

def report(root,parent):
    root=Path(root).resolve();parent=Path(parent)
    demand(parent.is_file() and not parent.is_symlink(),'V1V_PARENT_REQUIRED')
    demand(hashlib.sha256(parent.read_bytes()).hexdigest()==PARENT_SHA,'V1V_PARENT_SHA_DRIFT')
    old=json.loads(parent.read_text());pins=pin_sources(root)
    demand(old['status']==PARENT_STATUS and old['real_original_PE_classifier']
           and not old['frozen_original_BV_learning'] and old['frozen_source_pins']==pins,
           'V1V_PARENT_CONTRACT_OR_ORIGINAL_PIN_DRIFT')
    demand(sense._source_check(root)==pins,'ORIGINAL_PE_PROVENANCE_MISSING')
    with TemporaryDirectory(prefix='spk-native-v1w-') as tmp:
        tmp=Path(tmp);path=tmp/'queued.db'
        intake=w.enqueue(path,0,*CASES[0]);demand(intake['context'] is None,'CONTEXT_HOST_LEAKED_AT_QUEUE')
        first=[w.advance(path,0,root=root)]
        for epoch,case in enumerate(CASES[1:],1):first.append(w.run_epoch(path,epoch,*case,root=root))
        initial=w.audit(path,root=root)
        repeated=[w.run_epoch(path,epoch,*case,root=root) for epoch,case in enumerate(CASES)]
        final=w.audit(path,root=root)
        demand(initial==final,'STAGED_REPLAY_DRIFT')
        demand([x['new_tick_rows'] for x in first]==[65]*5,'MISSING_BV_TICK_EVENTS')
        demand([x['new_tick_rows'] for x in repeated]==[0]*5,'DUPLICATE_REPLAY_TICKS')
        demand([x['derived_context'] for x in first]==['ctx0','ctx1','ctx0','ctx1','ctx0'],
               'SENSED_CONTEXT_ORDER_WRONG')
        demand([x['signature'] for x in first]==['s71','s72','s71','s72','s71'],
               'PE_SIGNATURE_DRIFT')
        demand([x['P_to']['version'] for x in first]==[2,1,2,1,3],
               'CONTEXTUAL_P_VERSION_DRIFT')
        demand([x['P_grants'] for x in first]==[2,1,0,0,1],
               'CAUSAL_CREDIT_DRIFT')
        demand([x['first_C_PE_read'] for x in first]==[
               [10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],
               [10,1,12,[12]],[10,2,15,[15]]], 'C_NOT_READING_CONTEXTUAL_P')
        demand(initial['P_bank']=={'ctx0':{'owner':'C','domain':'P','choice':11,'version':3,'grants':3},
                                 'ctx1':{'owner':'C','domain':'P','choice':12,'version':1,'grants':1}},
               'CONTEXT_BANK_DRIFT')
        with sqlite3.connect(path) as db:
            ticks=db.execute('SELECT COUNT(*) FROM ctx_ticks').fetchone()[0]
            events=db.execute('SELECT COUNT(*) FROM v1w_stages').fetchone()[0]
        demand(ticks==325 and events==25,'LEDGER_ROW_COUNT_DRIFT')
        # Prove the original pre-existing context API cannot mint a fresh
        # contextual epoch in the v1w registered database.
        try:d.run_epoch(path,5,'ctx0',11,15,root=root)
        except sqlite3.IntegrityError as exc:
            demand('V1W_DIRECT_CONTEXT_BYPASS_DENIED' in str(exc),'DIRECT_BYPASS_WRONG_DENIAL')
            bypass_denied=True
        else:raise AssertionError('DIRECT_LEGACY_CONTEXT_BYPASS')
        demand(w.audit(path,root=root)==final,'LEGACY_BYPASS_MUTATED_P')
        reversed_path=tmp/'swapped.db'
        reverse=[w.run_epoch(reversed_path,i,*case,root=root) for i,case in enumerate((CASES[1],CASES[0]))]
        swapped=w.audit(reversed_path,root=root)
        demand(swapped['signatures']=={'s72':'ctx0','s71':'ctx1'},
               'CONTEXT_FIXED_BY_HOST_ORDER')
        cuts=[]
        for stage in ('OBSERVED','PE_CLASSIFIED','P_SELECTED','BV_COMPLETED'):
            p=tmp/('cut-'+stage+'.db')
            try:w.run_epoch(p,0,*CASES[0],root=root,crash_after_stage=stage)
            except w.PowerCut:pass
            else:raise AssertionError('MISSING_STAGE_POWER_CUT:'+stage)
            done=w.advance(p,0,root=root)
            demand(done['P_to']['version']==2 and w.advance(p,0,root=root)['new_tick_rows']==0,
                   'STAGE_RESTART_CAUSAL_P_DRIFT')
            cuts.append({'stage':stage,'head_sha256':w.audit(p,root=root)['chain_sha256']})
        bv_cuts=[]
        for cut in (1,9,13,14,15,27,60):
            p=tmp/('bv-'+str(cut)+'.db')
            try:w.run_epoch(p,0,*CASES[0],root=root,pause_after=cut)
            except d.SimulatedPowerLoss:pass
            else:raise AssertionError('MISSING_NATIVE_BV_PAUSE:'+str(cut))
            done=w.advance(p,0,root=root)
            demand(cut+done['new_tick_rows']==65,'BV_REPLAY_DUPLICATED_TICKS')
            bv_cuts.append({'cut':cut,'head_sha256':w.audit(p,root=root)['chain_sha256']})
        failures=[]
        for label,raw in (('mixed',(40,43)),('ambiguous',(40,41,42,43)),
                          ('duplicate',(40,40,42)),('unknown',(40,42,111))):
            p=tmp/('invalid-'+label+'.db')
            w.enqueue(p,0,raw,11,15,root=root)
            try:w.advance(p,0,root=root)
            except w.IngressReject:pass
            else:raise AssertionError('PE_SENSORY_DENIAL_NOT_ENFORCED:'+label)
            with sqlite3.connect(p) as db:
                demand(db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]==0,
                       'INVALID_SIGNAL_CREATED_P')
            failures.append(label)
        return {'schema':SCHEMA,'status':'V1W_QUEUED_PE_INGRESS_GATES_CONTEXTUAL_NATIVE_V1_P_PASS',
            'parent_v1v_SHA256':PARENT_SHA,'frozen_source_pins':pins,
            'host_supplies_context_name':False,'classification_on_queue':False,
            'original_PE_classification_at_ingress_consumption':True,
            'native_v1_BV_and_P_after_ingress':True,'legacy_context_api_fenced_on_v1w_db':bypass_denied,
            'episodes':len(first),'committed_BV_tick_rows':ticks,'staged_ingress_event_rows':events,
            'context_ids':[x['derived_context'] for x in first],
            'observed_PE_signatures':[x['signature'] for x in first],
            'P_versions':[x['P_to']['version'] for x in first],
            'P_grants':[x['P_grants'] for x in first],
            'C_actual_PE_first_reads':[x['first_C_PE_read'] for x in first],
            'journal_head_SHA256':final['chain_sha256'],
            'signature_context_binding':final['signatures'],
            'closed_P_bank':final['P_bank'],
            'second_run_new_BV_ticks':sum(x['new_tick_rows'] for x in repeated),
            'reverse_context_order_binding':swapped['signatures'],
            'stage_recovery':cuts,'BV_recovery':bv_cuts,'negative_inputs_denied':failures,
            'research_v1_native_learning':True,'frozen_BV_v0e_learning':False,
            'original_frozen_components_unchanged':True,'promotion_allowed':False,
            'limitations':[
             'PE classification occurs in a durable ingress stage BEFORE native-v1 BV ticks, not inside frozen BV scheduler',
             'Two predeclared cue classes; not discovery of arbitrary contexts',
             'v1w database trigger fences cooperative direct old API inserts only; a privileged host can bypass it',
             'Host still authors raw observations and goals; no authenticated sensor or independent goal issuer',
             'Replay re-executes original PE/BV logical computation, not irreversible external actions',
             'This proves versioned v1 native contextual learning, never learning in frozen original v0e']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output')
    parser.add_argument('--root',default='.')
    parser.add_argument('--parent',required=True)
    args=parser.parse_args();r=report(args.root,args.parent)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(r['status'],'EPISODES',r['episodes'],'TICKS',r['committed_BV_tick_rows'])
if __name__=='__main__':main()
