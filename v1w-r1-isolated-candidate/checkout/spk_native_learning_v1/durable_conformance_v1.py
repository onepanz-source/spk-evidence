"""Single macro acceptance: restart, deterministic replay, inherited live P."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1.conformance_v1 import pin_sources,compare_frozen_when_learning_off
from spk_native_learning_v1 import durable_runtime_v1 as d

SCHEMA='spk-native-learning-v1-durable-macro-proof/v1'
PARENT_SHA='b3ed1b68bacd15643523a89d65777369ed4cce7ab61e48132d90d9dde0d3de4e'

def demand(b,code):
    if not b:raise AssertionError(code)

def evidence(root):
    root=Path(root)
    pins=pin_sources(root)
    parent=root/'spk_native_learning_v1/reference/native-v1-first-fwork.json'
    demand(parent.is_file() and d.sha(parent.read_bytes())==PARENT_SHA,'PARENT_NATIVE_V1_REPORT_DRIFT')
    pv=json.loads(parent.read_text())
    demand(pv['C_recomputes_on_updated_P_same_scheduler'] and pv['native_v1_research_learning'],'INVALID_FIRST_V1_PROOF')
    with TemporaryDirectory(prefix='spk-nlv1r-restart-') as td:
        td=Path(td)
        clean=d.run_epoch(td/'clean.db',0,12,11,root=root)
        demand(clean['C_PE_reads']==[[10,0,12,[12]],[30,1,11,[11]]],'NO_ACTUAL_PE_RECOMPUTATION')
        recoveries=[]
        for cut in (1,9,13,14,15,22,24):
            db=td/f'pause-{cut}.db'
            try:d.run_epoch(db,0,12,11,root=root,pause_after=cut)
            except d.SimulatedPowerLoss:pass
            else:raise AssertionError('PAUSE_NOT_EXERCISED')
            before=d.ledger_inventory(db)
            demand(before['ticks']==cut and before['epochs'][0]['status']=='RUNNING','PAUSE_NOT_DURABLE')
            res=d.run_epoch(db,0,12,11,root=root)
            demand(res['output_sha256']==clean['output_sha256'],'REPLAY_COUNTERFACTUAL_DRIFT')
            demand(res['new_tick_rows']==res['tick_count']-cut,'REPLAY_DUPLICATED_TICKS')
            demand(d.run_epoch(db,0,12,11,root=root)['new_tick_rows']==0,'CLOSED_REPLAY_RECOMMIT')
            recoveries.append({'cut':cut,'verified_prefix_ticks':cut,'completed_ticks':res['tick_count'],
               'P_version':res['final_P']['version'],'output_sha256':res['output_sha256']})
        db=td/'epochs.db'
        e0=d.run_epoch(db,0,12,11,root=root)
        e1=d.run_epoch(db,1,12,11,root=root)
        e2=d.run_epoch(db,2,12,12,root=root)
        demand(e0['final_P']==e1['initial_P'] and e1['final_P']==e2['initial_P'],'CROSS_EPOCH_P_OWNERSHIP_DRIFT')
        demand(e0['final_P']['version']==1 and e1['final_P']['version']==1 and e2['final_P']['version']==2,'P_VERSION_SEQUENCE_WRONG')
        demand(e1['C_PE_reads'][0]==[10,1,11,[11]] and e2['C_PE_reads'][1]==[30,2,12,[12]], 'ACTUAL_PE_PROGRAM_NOT_RELOADED')
        # A first-episode continuation from an already committed terminal state
        # must not generate a second P grant or alter previous epochs.
        demand(d.run_epoch(db,0,12,11,root=root)['new_tick_rows']==0,'OLD_EPOCH_REPLAY_DUPLICATE')
        inventory=d.ledger_inventory(db)
        demand(len(inventory['epochs'])==3 and all(x['status']=='CLOSED' for x in inventory['epochs']),'EPOCHS_NOT_COMMITTED')
        backward=d.run_epoch(td/'other-choice.db',0,11,12,root=root)
        demand(backward['C_PE_reads']==[[10,0,11,[11]],[30,1,12,[12]]],'OPPOSITE_CHOICE_DID_NOT_LEARN')
        parity=compare_frozen_when_learning_off()
    return {'schema':SCHEMA,'status':'NATIVE_V1_DURABLE_P_INHERITANCE_AND_CAUSAL_REPLAY_PASS',
            'parent_first_runtime_sha256':PARENT_SHA,'frozen_source_pins':pins,
            'frozen_original_BV_unchanged':True,'native_v1_intrinsic_learning':True,
            'old_frozen_original_native_learning':False,
            'durability':'SQLITE_TICK_WAL_PLUS_VERIFIED_GENESIS_REPLAY',
            'crash_cut_recovery':recoveries,
            'clean':{'output_sha256':clean['output_sha256'],'C_PE_reads':clean['C_PE_reads'],
                     'P_grants':len(clean['P_grants'])},
            'cross_epoch_P':{'epochs':[
                 {'id':i,'initial_P':x['initial_P'],'final_P':x['final_P'],
                  'C_PE_reads':x['C_PE_reads'],'P_grants':len(x['P_grants'])}
                 for i,x in enumerate((e0,e1,e2))],
                 'total_committed_ticks':inventory['ticks']},
            'reverse_choice_PE_reads':backward['C_PE_reads'],
            'frozen_v0e_disabled_learning_parity':parity,
            'limitations':['Experimental three-neuron binary v1 scheduler, not original frozen BV-v0e',
              'Recovery reexecutes the bounded episode from genesis, verifying committed ticks; NOT instantaneous heap restore',
              'No independent IO effects occur during replay; NOT safe to replay external irreversible effects',
              'SQLite evidence is not tamper-proof against a privileged host that can alter code and ledger',
              'A program encodes a host-authored target; no generalizable credit assignment',
              'No hardware sensor, arbitrary topology, remote consensus or signed BV source',
              'Original frozen BV-v0e remains unchanged and does not natively learn']}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('out');parser.add_argument('--root',default='.')
    args=parser.parse_args()
    report=evidence(args.root)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=True)+'\n')
    print(report['status'],'RECOVERY_CUTS',len(report['crash_cut_recovery']),
          'EPISODES',len(report['cross_epoch_P']['epochs']))
