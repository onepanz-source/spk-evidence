"""Cumulative acceptance of cooperative multi-process, continuous native-v1 P."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1.conformance_v1 import pin_sources,compare_frozen_when_learning_off
from spk_native_learning_v1 import serialized_runtime_v1s as s
from spk_native_learning_v1 import durable_runtime_v1 as d

SCHEMA='spk-native-learning-v1s-cooperative-serialized-conformance/v1'
DURABLE_STATUS='NATIVE_V1_DURABLE_P_INHERITANCE_AND_CAUSAL_REPLAY_PASS'

def insist(value,err):
    if not value:raise AssertionError(err)

def run(root,parent_report):
    root=Path(root)
    pins=pin_sources(root)
    prior=Path(parent_report)
    insist(prior.is_file() and not prior.is_symlink(),'DURABLE_PARENT_EVIDENCE_MISSING')
    old=json.loads(prior.read_text())
    insist(old['schema']=='spk-native-learning-v1-durable-macro-proof/v1'
           and old['status']==DURABLE_STATUS,'DURABLE_PARENT_NOT_SUCCESSFUL')
    insist(old['native_v1_intrinsic_learning'] and not old['old_frozen_original_native_learning'],
           'DURABLE_PARENT_MISREPRESENTED_NATIVE_SCOPE')
    insist(old['frozen_source_pins']==pins,'DURABLE_PARENT_ORIGINAL_SOURCE_DRIFT')
    parent_sha=hashlib.sha256(prior.read_bytes()).hexdigest()
    with TemporaryDirectory(prefix='spk-nlv1s-') as td:
        rootdb=Path(td)
        seq=((12,11),(12,11),(12,12))
        first=s.run_sequence(rootdb/'main.db',seq,root=root)
        second=s.run_sequence(rootdb/'main.db',seq,root=root)
        insist(first['new_tick_rows']>0 and second['new_tick_rows']==0,
               'REPLAY_REINSERTED_COMMITTED_TICKS')
        insist(first['chain']==second['chain'],'AUDITED_CHAIN_NOT_REPRODUCIBLE')
        c=first['C_PE_reads_by_epoch']
        insist(c==[
          [[10,0,12,[12]],[30,1,11,[11]]],
          [[10,1,11,[11]],[30,1,11,[11]]],
          [[10,1,11,[11]],[30,2,12,[12]]]],'GENUINE_PE_NOT_REBOUND_ACROSS_EPOCHS')
        recoveries=[]
        for cut in (1,9,13,14,15,22,24):
            db=rootdb/('crash-'+str(cut)+'.db')
            try:s.run_epoch(db,0,12,11,pause_after=cut,root=root)
            except d.SimulatedPowerLoss:pass
            else:raise AssertionError('CRASH_CUT_NOT_EXERCISED')
            recovery=s.run_epoch(db,0,12,11,root=root)
            insist(recovery['epoch']['new_tick_rows']+cut==recovery['epoch']['tick_count'],
                   'COMMITTED_TICKS_WERE_REPLAYED_AS_NEW')
            insist(recovery['epoch']['C_PE_reads']==c[0],'RECOVERED_PE_PROGRAM_DRIFT')
            recoveries.append({'cut':cut,'journal_sha256':recovery['epoch']['journal_head_sha256']})
        opposite=s.run_epoch(rootdb/'reverse.db',0,11,12,root=root)
        insist(opposite['epoch']['C_PE_reads']==[[10,0,11,[11]],[30,1,12,[12]]],
               'INVERSE_P_LEARNING_FAILED')
        frozen=compare_frozen_when_learning_off()
        insist(frozen['frozen_PE_forward_and_BV_resource_parity'],'FROZEN_SOURCE_PARITY_FAILED')
    return {'schema':SCHEMA,'status':'NATIVE_V1S_COOPERATIVE_SERIAL_DURABLE_CHAIN_PASS',
            'durable_predecessor_sha256':parent_sha,'original_frozen_pins':pins,
            'actual_same_scheduler_C_PE_reads':c,'causal_chain_sha256':first['chain']['chain_sha256'],
            'audited_epochs':first['chain']['epoch_count'],
            'original_v0e_learning':False,'versioned_v1s_learning':True,
            'continuous_P_versions':[e['P_to'] for e in first['chain']['epochs']],
            'committed_tick_rows':sum(x['tick_count'] for x in first['chain']['epochs']),
            'second_execution_new_rows':second['new_tick_rows'],
            'restart_cuts':recoveries,'reverse_learning_PE_reads':opposite['epoch']['C_PE_reads'],
            'frozen_disabled_learning_parity':frozen,
            'concurrency':'ADVISORY_POSIX_FLOCK_ACROSS_CAUSAL_REPLAY_AND_COMMIT',
            'security_scope':'COOPERATIVE_WRITERS_ONLY',
            'limitations':['v1s is versioned three-node binary learning, not frozen original BV-v0e',
                           'Lock is advisory: old v1r callers and privileged host can bypass it',
                           'Persistence is a verified deterministic genesis replay, not heap restoration',
                           'Batch of epochs commits a recoverable prefix; it is NOT multi-epoch atomic',
                           'No irreversible external effects, signed hardware source, or N-node proof',
                           'No generalizable semantic credit outside 11/12 and A 21/22']}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('output');ap.add_argument('--root',default='.')
    ap.add_argument('--parent',required=True)
    args=ap.parse_args()
    record=run(args.root,args.parent)
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(record,sort_keys=True,indent=2,ensure_ascii=True)+'\n')
    print(record['status'],'P_VERSIONS',record['continuous_P_versions'],'RESTART_CUTS',len(record['restart_cuts']))
