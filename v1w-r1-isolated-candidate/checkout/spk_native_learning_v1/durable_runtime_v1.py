"""Durable v1 research scheduler: bounded tick-level WAL + deterministic causal replay.

No checkpoint of Python heap is claimed. On restart the original inputs are
recomputed from genesis, every committed tick is compared byte-exact against
SQLite evidence, then NEW ticks are appended. Side effects are confined to the
local SQLite journal; this is not yet an external side-effect-safe runtime.
"""
from __future__ import annotations
import dataclasses
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from spk_native_learning_v1.conformance_v1 import setup, pin_sources
from spk_native_learning_v1.live_learning_scheduler_v1r import (
    execute_resume_learning_v1r, LearningPlanV1, LiveBVPlanV0e, LiveBVRejected)

SCHEMA='spk-native-learning-durable-tick-ledger/v1'

class DurableReject(RuntimeError):pass
class SimulatedPowerLoss(RuntimeError):pass

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def sha(x):return hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()

def pure(x):
    if dataclasses.is_dataclass(x):return pure(dataclasses.asdict(x))
    if isinstance(x,SimpleNamespace):return pure(vars(x))
    if isinstance(x,dict):return {str(k):pure(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [pure(v) for v in x]
    if x is None or type(x) in (str,int,bool,float):return x
    raise DurableReject('INPUT_NOT_CANONICAL:'+type(x).__name__)

def _open(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path),timeout=8,isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS epochs(
        id INTEGER PRIMARY KEY, input_sha TEXT NOT NULL, request_json TEXT NOT NULL, initial_p TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('RUNNING','CLOSED')),
        final_p TEXT, result_sha TEXT);
    CREATE TABLE IF NOT EXISTS ticks(
        epoch INTEGER NOT NULL, seq INTEGER NOT NULL,
        tick INTEGER NOT NULL, prev_sha TEXT NOT NULL,
        snapshot TEXT NOT NULL, row_sha TEXT NOT NULL,
        PRIMARY KEY(epoch,seq), UNIQUE(epoch,tick),
        FOREIGN KEY(epoch) REFERENCES epochs(id));
    ''')
    return db

def run_epoch(db_path, epoch, choice, goal, *, second_tick=30, pause_after=None,
              root='.'):
    """Execute or resume a bounded episode. A subsequent epoch inherits P.

    Frozen-source verification is mandatory. Unit tests may monkeypatch the
    source verifier in an isolated fixture, never in the release gate.
    """
    if type(epoch) is not int or epoch<0 or type(choice) is not int or choice not in (11,12) or type(goal) is not int or goal not in (11,12):
        raise DurableReject('INVALID_EPOCH_OR_BINARY_CASE')
    if pause_after is not None and (type(pause_after) is not int or pause_after<1):
        raise DurableReject('INVALID_PAUSE_BOUND')
    pin_sources(root)
    args=setup(choice,goal,second_tick=second_tick)
    bv=LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256)
    learn=LearningPlanV1(enabled=True,mode='execute',max_grants=8)
    src=Path(__file__).resolve().with_name('live_learning_scheduler_v1r.py')
    source_sha=sha(src.read_bytes())
    inputs={'schema':SCHEMA,'epoch':epoch,'arguments':pure(args),'bv':pure(bv),
            'learning':pure(learn),'runtime_sha256':source_sha}
    input_sha=sha(canonical(inputs))
    # An earlier CLOSED status is not itself trusted as authority for P.
    # Replay and verify the preceding episode before inheriting its final P.
    # This is intentionally bounded/expensive, rather than a forged cursor.
    if epoch>0:
        guard=_open(db_path)
        try:
            parent=guard.execute('SELECT status,request_json FROM epochs WHERE id=?',(epoch-1,)).fetchone()
        finally:guard.close()
        if parent is None or parent[0]!='CLOSED':
            raise DurableReject('PREVIOUS_EPOCH_NOT_CLOSED')
        prior=json.loads(parent[1])
        run_epoch(db_path,epoch-1,prior['choice'],prior['goal'],
                  second_tick=prior['second_tick'],root=root)
    db=_open(db_path)
    try:
        db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT input_sha,request_json,initial_p,status,final_p,result_sha FROM epochs WHERE id=?',(epoch,)).fetchone()
        if current is None:
            last=db.execute('SELECT MAX(id) FROM epochs').fetchone()[0]
            if last is None:
                if epoch!=0:raise DurableReject('FIRST_EPOCH_MUST_BE_ZERO')
                initial_P={'owner':'C','domain':'P','choice':choice,'version':0,'grants':0}
            else:
                if epoch!=last+1:raise DurableReject('EPOCH_ORDER_OR_REPLAY_VIOLATION')
                parent=db.execute('SELECT status,final_p FROM epochs WHERE id=?',(last,)).fetchone()
                if parent[0]!='CLOSED' or not parent[1]:raise DurableReject('PREVIOUS_EPOCH_NOT_CLOSED')
                initial_P=json.loads(parent[1])
            db.execute('INSERT INTO epochs(id,input_sha,request_json,initial_p,status) VALUES(?,?,?,?,?)',
                       (epoch,input_sha,canonical({'choice':choice,'goal':goal,'second_tick':second_tick}),
                        canonical(initial_P),'RUNNING'))
        else:
            initial_P=json.loads(current[2])
            request=canonical({'choice':choice,'goal':goal,'second_tick':second_tick})
            if current[0]!=input_sha or current[1]!=request:
                raise DurableReject('SOURCE_OR_INPUT_FINGERPRINT_CHANGED')
            if epoch>0:
                parent=db.execute('SELECT status,final_p FROM epochs WHERE id=?',(epoch-1,)).fetchone()
                if parent is None or parent[0]!='CLOSED' or parent[1]!=current[2]:
                    raise DurableReject('PREVIOUS_P_CONTINUITY_BROKEN')
        db.commit()
        header=sha(canonical({'schema':SCHEMA,'epoch':epoch,'input_sha':input_sha,'initial_p':initial_P}))
        seq=0
        previous=header
        appended=0
        def tick_sink(snapshot):
            nonlocal seq,previous,appended
            encoded=canonical(snapshot)
            row_sha=sha(canonical([previous,encoded]))
            old=db.execute('SELECT tick,prev_sha,snapshot,row_sha FROM ticks WHERE epoch=? AND seq=?',
                           (epoch,seq)).fetchone()
            if old is not None:
                if old!=(snapshot['tick'],previous,encoded,row_sha):
                    raise DurableReject('COMMITTED_CAUSAL_PREFIX_DRIFT:'+str(seq))
            else:
                db.execute('BEGIN IMMEDIATE')
                # Another writer cannot silently overtake this connection.
                row=db.execute('SELECT MAX(seq) FROM ticks WHERE epoch=?',(epoch,)).fetchone()[0]
                if row is not None and row!=seq-1:
                    db.rollback();raise DurableReject('TICK_SEQUENCE_FORK')
                db.execute('INSERT INTO ticks VALUES(?,?,?,?,?,?)',
                           (epoch,seq,snapshot['tick'],previous,encoded,row_sha))
                db.commit()
                appended+=1
            previous=row_sha
            seq+=1
            if pause_after is not None and appended>=pause_after:
                raise SimulatedPowerLoss('SIMULATED_PAUSE_AFTER_COMMITTED_TICK:'+str(seq))
        result=execute_resume_learning_v1r(*args,bv=bv,learn=learn,initial_P=initial_P,tick_sink=tick_sink)
        # Verify that every persisted tick was reproduced and no historical
        # suffix remains after a shorter altered execution.
        count=db.execute('SELECT COUNT(*) FROM ticks WHERE epoch=?',(epoch,)).fetchone()[0]
        if count!=seq:raise DurableReject('RECORDED_SUFFIX_NOT_REPLAYED')
        reads=[b for b in result['forward']['batches'] if b['node']=='C']
        if not reads or reads[0]['P_version']!=initial_P['version'] or reads[0]['P_choice']!=initial_P['choice']:
            raise DurableReject('ACTUAL_PE_DID_NOT_READ_INHERITED_P')
        final=result['learning']['final']
        if final['version']!=initial_P['version']+len(result['learning']['grants']):
            raise DurableReject('EPISODE_P_VERSION_NOT_MONOTONIC')
        output_sha=sha(canonical(result))
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT status,final_p,result_sha FROM epochs WHERE id=?',(epoch,)).fetchone()
        if old[0]=='CLOSED':
            if old[1]!=canonical(final) or old[2]!=output_sha:
                raise DurableReject('FINALIZED_EPOCH_REPLAY_DRIFT')
        else:
            db.execute('UPDATE epochs SET status=?,final_p=?,result_sha=? WHERE id=?',
                       ('CLOSED',canonical(final),output_sha,epoch))
        db.commit()
        return {'schema':SCHEMA,'epoch':epoch,'status':'CLOSED',
                'tick_count':seq,'new_tick_rows':appended,'final_P':final,
                'initial_P':initial_P,'P_grants':result['learning']['grants'],
                'C_PE_reads':[[b['tick'],b['P_version'],b['P_choice'],b['outputs']]
                              for b in reads],
                'A_PE_verdicts':[[a['tick'],a['A_PE_output'],a['verdict']]
                                for a in result['feedback']['assessments']],
                'source_runtime_sha256':source_sha,'output_sha256':output_sha,
                'journal_head_sha256':previous,'recovery':'DETERMINISTIC_GENESIS_REPLAY_NOT_HEAP_RESTORE'}
    except BaseException:
        if db.in_transaction:db.rollback()
        raise
    finally:db.close()

def ledger_inventory(path):
    db=_open(path)
    try:
        return {'epochs':[{'id':r[0],'status':r[1],'final_P':json.loads(r[2]) if r[2] else None}
                          for r in db.execute('SELECT id,status,final_p FROM epochs ORDER BY id')],
                'ticks':db.execute('SELECT COUNT(*) FROM ticks').fetchone()[0]}
    finally:db.close()
