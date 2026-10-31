"""Versioned native v1u: verified context-indexed P across BV-v1t episodes.

All program choices after context genesis come from replayed PE/BV outputs,
never an initial P override provided by the caller. Host declares context IDs.
No original SPK frozen module changes; no external side effects supported.
"""
from __future__ import annotations
import json,re,sqlite3
from pathlib import Path
from spk_native_learning_v1 import generalized_durable_v1t as base
from spk_native_learning_v1.generalized_case_v1t import setup,pin_sources
from spk_native_learning_v1.generalized_scheduler_v1t import execute_resume_learning_v1r,LiveBVPlanV0e,LearningPlanV1
SCHEMA='spk-native-learning-contextual-durable/v1u'
class ContextReject(RuntimeError): pass
class SimulatedPowerLoss(RuntimeError): pass

def validate(ctx,choice,goal,tick,pause=None):
    if type(ctx) is not str or not re.fullmatch(r'[a-z][a-z0-9_-]{0,23}',ctx,flags=re.ASCII):raise ContextReject('INVALID_CONTEXT')
    if type(choice) is not int or choice not in (11,12,15) or type(goal) is not int or goal not in (11,12,15):raise ContextReject('INVALID_CHOICE_OR_GOAL')
    if type(tick) is not int or not 20<=tick<=165:raise ContextReject('INVALID_TICK')
    if pause is not None and (type(pause) is not int or pause<1):raise ContextReject('INVALID_PAUSE')

def open_db(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10,isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS ctx_epochs(id INTEGER PRIMARY KEY, context TEXT NOT NULL,
       input_sha TEXT NOT NULL, request_json TEXT NOT NULL, initial_p TEXT NOT NULL,
       status TEXT NOT NULL CHECK(status IN ('RUNNING','CLOSED')), final_p TEXT, result_sha TEXT);
      CREATE TABLE IF NOT EXISTS ctx_ticks(epoch INTEGER NOT NULL, seq INTEGER NOT NULL,
       tick INTEGER NOT NULL, prev_sha TEXT NOT NULL, snapshot TEXT NOT NULL, row_sha TEXT NOT NULL,
       PRIMARY KEY(epoch,seq), UNIQUE(epoch,tick), FOREIGN KEY(epoch) REFERENCES ctx_epochs(id));
    ''');return db

def _one(db,epoch,req,bank,genesis,source_sha,pause=None):
    ctx,choice,goal,tick=req
    validate(ctx,choice,goal,tick,pause)
    if ctx in genesis and genesis[ctx]!=choice:raise ContextReject('CONTEXT_GENESIS_CHOICE_DRIFT')
    if ctx not in bank:
        initial={'owner':'C','domain':'P','choice':choice,'version':0,'grants':0};genesis[ctx]=choice
    else:initial=dict(bank[ctx])
    request={'context':ctx,'choice':choice,'goal':goal,'second_tick':tick}
    args=setup(choice,goal,second_tick=tick)
    bv=LiveBVPlanV0e(assessor='A',max_ticks=256)
    learn=LearningPlanV1(max_grants=8)
    fingerprint=base.sha(base.canonical({'schema':SCHEMA,'epoch':epoch,'request':request,'args':base.pure(args),
                                          'bv':base.pure(bv),'learn':base.pure(learn),'source':source_sha}))
    req_s=base.canonical(request);ini_s=base.canonical(initial)
    db.execute('BEGIN IMMEDIATE')
    try:
        old=db.execute('SELECT context,input_sha,request_json,initial_p,status,final_p,result_sha FROM ctx_epochs WHERE id=?',(epoch,)).fetchone()
        if old is None:
            last=db.execute('SELECT MAX(id) FROM ctx_epochs').fetchone()[0]
            if (last is None and epoch!=0) or (last is not None and epoch!=last+1):raise ContextReject('NON_SEQUENTIAL_EPOCH')
            db.execute('INSERT INTO ctx_epochs(id,context,input_sha,request_json,initial_p,status) VALUES(?,?,?,?,?,?)',
                       (epoch,ctx,fingerprint,req_s,ini_s,'RUNNING'))
            was_closed=False
        else:
            if old[:4]!=(ctx,fingerprint,req_s,ini_s):raise ContextReject('CONTEXT_REQUEST_OR_P_DRIFT')
            was_closed=old[4]=='CLOSED'
        db.commit()
    except BaseException:
        db.rollback();raise
    seq=0;added=0;prev=base.sha(base.canonical({'schema':SCHEMA,'epoch':epoch,'input':fingerprint,'initial':initial}))
    def sink(snap):
        nonlocal seq,added,prev
        enc=base.canonical(snap);h=base.sha(base.canonical([prev,enc]))
        old=db.execute('SELECT tick,prev_sha,snapshot,row_sha FROM ctx_ticks WHERE epoch=? AND seq=?',(epoch,seq)).fetchone()
        if old is not None:
            if old!=(snap['tick'],prev,enc,h):raise ContextReject('CAUSAL_PREFIX_DRIFT:'+str(seq))
        else:
            if was_closed:raise ContextReject('CLOSED_EPOCH_MISSING_TICK')
            db.execute('BEGIN IMMEDIATE')
            try:
                tail=db.execute('SELECT MAX(seq) FROM ctx_ticks WHERE epoch=?',(epoch,)).fetchone()[0]
                if tail is not None and tail!=seq-1:raise ContextReject('TICK_FORK')
                db.execute('INSERT INTO ctx_ticks VALUES(?,?,?,?,?,?)',(epoch,seq,snap['tick'],prev,enc,h))
                db.commit();added+=1
            except BaseException:db.rollback();raise
        seq+=1;prev=h
        if pause is not None and added>=pause:raise SimulatedPowerLoss('AFTER_COMMITTED_TICK:'+str(seq))
    result=execute_resume_learning_v1r(*args,bv=bv,learn=learn,initial_P=initial,tick_sink=sink)
    count=db.execute('SELECT COUNT(*) FROM ctx_ticks WHERE epoch=?',(epoch,)).fetchone()[0]
    if count!=seq:raise ContextReject('JOURNAL_SUFFIX_NOT_REPLAYED')
    reads=[x for x in result['forward']['batches'] if x['node']=='C']
    if not reads or reads[0]['P_version']!=initial['version'] or reads[0]['P_choice']!=initial['choice']:
        raise ContextReject('ACTUAL_PE_NOT_REBOUND_TO_CONTEXT_P')
    final=result['learning']['final']
    if final['version']!=initial['version']+len(result['learning']['grants']) or final['grants']!=final['version']:
        raise ContextReject('INVALID_P_VERSION_OR_CREDIT')
    digest=base.sha(base.canonical(result))
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT status,final_p,result_sha FROM ctx_epochs WHERE id=?',(epoch,)).fetchone()
        if row[0]=='CLOSED':
            if row[1]!=base.canonical(final) or row[2]!=digest:raise ContextReject('CLOSED_EPOCH_DRIFT')
        else:db.execute('UPDATE ctx_epochs SET status=?,final_p=?,result_sha=? WHERE id=?',
                        ('CLOSED',base.canonical(final),digest,epoch))
        db.commit()
    except BaseException:db.rollback();raise
    bank[ctx]=dict(final)
    return {'epoch':epoch,'context':ctx,'tick_count':seq,'new_tick_rows':added,'initial_P':initial,
            'final_P':final,'P_grants':result['learning']['grants'],
            'C_PE_reads':[[x['tick'],x['P_version'],x['P_choice'],x['outputs']] for x in reads],
            'A_PE_verdicts':[[x['tick'],x['A_PE_output'],x['verdict']] for x in result['feedback']['assessments']],
            'journal_head_sha256':prev,'output_sha256':digest}

def _replay(db,upto,root,source_sha):
    bank={};genesis={};hist=[]
    for i in range(upto):
        row=db.execute('SELECT status,request_json FROM ctx_epochs WHERE id=?',(i,)).fetchone()
        if row is None or row[0]!='CLOSED':raise ContextReject('PREDECESSOR_MISSING_OR_OPEN')
        req=json.loads(row[1])
        item=_one(db,i,(req['context'],req['choice'],req['goal'],req['second_tick']),bank,genesis,source_sha)
        if item['new_tick_rows']:raise ContextReject('REPLAY_MUST_NOT_APPEND')
        hist.append(item)
    return bank,genesis,hist

def _source_sha(root):
    pin_sources(root)
    return base.sha(Path(__file__).with_name('generalized_scheduler_v1t.py').read_bytes())

def run_epoch(path,epoch,context,choice,goal,*,second_tick=30,pause_after=None,root='.'):
    if type(epoch) is not int or epoch<0:raise ContextReject('INVALID_EPOCH')
    validate(context,choice,goal,second_tick,pause_after)
    source=_source_sha(root);db=open_db(path)
    try:
        bank,genesis,prior=_replay(db,epoch,root,source)
        item=_one(db,epoch,(context,choice,goal,second_tick),bank,genesis,source,pause_after)
        return {'schema':SCHEMA,'episode':item,'bank':{k:bank[k] for k in sorted(bank)},
                'verified_predecessors':len(prior),'source_sha256':source}
    finally:db.close()

def audit(path,*,root='.'):
    source=_source_sha(root);db=open_db(path)
    try:
        rows=db.execute('SELECT id,status FROM ctx_epochs ORDER BY id').fetchall()
        if any(i!=e or state!='CLOSED' for i,(e,state) in enumerate(rows)):raise ContextReject('UNCLOSED_OR_GAPPED_CHAIN')
        bank,genesis,hist=_replay(db,len(rows),root,source)
        chain=[{'epoch':x['epoch'],'context':x['context'],'P_from':x['initial_P']['version'],
                'P_to':x['final_P']['version'],'first_C_PE_read':x['C_PE_reads'][0],
                'journal_head_sha256':x['journal_head_sha256'],'output_sha256':x['output_sha256']} for x in hist]
        return {'schema':SCHEMA,'status':'CONTEXTUAL_P_CHAIN_VERIFIED','epochs':chain,
                'bank':{k:bank[k] for k in sorted(bank)},'genesis':genesis,'chain_sha256':base.sha(base.canonical(chain))}
    finally:db.close()
