"""v1w queued PE sensory ingress bound to one durable C P learning epoch.

This is a VERSIONED cooperative coordinator: raw observations are queued without
context names, classified by the genuine frozen PE *when consumed*, then admitted
into the same durable native-learning v1u causal episode. Journaled admission and
closed-epoch PE reads enforce a single context binding across restart/replay.
The PE selection precedes BV ticks; it is NOT a BV-carried sensory message.
The v1u direct API is fenced on a v1w-owned database by a SQLite trigger, but
other databases, legacy APIs, and privileged SQLite writers are not constrained.
"""
from __future__ import annotations
import hashlib,json,sqlite3
from pathlib import Path
from spk_native_learning_v1 import sensed_context_v1v as sense
from spk_native_learning_v1 import contextual_durable_v1u as durable
from spk_native_learning_v1.generalized_serial_v1t import serialized_ownership
from spk_native_learning_v1 import generalized_durable_v1t as base

SCHEMA='spk-native-learning-v1w-queued-ingress/v1'
STAGES=('OBSERVED','PE_CLASSIFIED','P_SELECTED','BV_COMPLETED','CLOSED')
class IngressReject(RuntimeError):pass
class PowerCut(RuntimeError):pass


def canonical(obj):return base.canonical(obj)
def digest(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()

def _db(path):
    db=durable.open_db(path)
    # Reject a pre-existing direct-v1u database BEFORE creating any v1w
    # schema. An old history may never be certified retroactively.
    registered=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v1w_intake'").fetchone()
    if not registered and db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]:
        db.close()
        raise IngressReject('LEGACY_CONTEXT_HISTORY_WITHOUT_PE_INGRESS')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS v1w_intake(
       epoch INTEGER PRIMARY KEY,observations TEXT NOT NULL,choice INTEGER NOT NULL,
       goal INTEGER NOT NULL,second_tick INTEGER NOT NULL,request_sha TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS v1w_stages(
       epoch INTEGER NOT NULL,seq INTEGER NOT NULL,stage TEXT NOT NULL,
       payload TEXT NOT NULL,previous_sha TEXT NOT NULL,row_sha TEXT NOT NULL,
       PRIMARY KEY(epoch,seq),UNIQUE(epoch,stage));
      CREATE TABLE IF NOT EXISTS v1w_binding(
       signature TEXT PRIMARY KEY,context TEXT UNIQUE NOT NULL,first_epoch INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS v1w_permit(
       epoch INTEGER PRIMARY KEY, context TEXT NOT NULL,request_sha TEXT NOT NULL,
       signature TEXT NOT NULL);
      CREATE TRIGGER IF NOT EXISTS v1w_require_derived_context
       BEFORE INSERT ON ctx_epochs
       BEGIN
        SELECT CASE WHEN NOT EXISTS(
           SELECT 1 FROM v1w_permit AS p JOIN v1w_intake AS i ON i.epoch=p.epoch
           WHERE p.epoch=NEW.id AND p.context=NEW.context
              AND p.request_sha=i.request_sha AND
              EXISTS(SELECT 1 FROM v1w_stages AS s WHERE s.epoch=NEW.id
                  AND s.stage='P_SELECTED'))
          THEN RAISE(ABORT,'V1W_DIRECT_CONTEXT_BYPASS_DENIED') END;
       END;
    ''')
    # No retroactive attachment: old contextual epochs must never acquire a
    # PE ingress receipt after their P program has already been learned.
    prior=db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]
    queued=db.execute('SELECT COUNT(*) FROM v1w_intake').fetchone()[0]
    if prior>queued:
        db.close()
        raise IngressReject('LEGACY_CONTEXT_HISTORY_WITHOUT_PE_INGRESS')
    return db

def _intake(req):
    if type(req) not in (tuple,list) or len(req)!=4:raise IngressReject('INVALID_INGRESS_REQUEST')
    raw,choice,goal,tick=req
    if type(raw) not in (list,tuple):raise IngressReject('INVALID_RAW_OBSERVATION')
    # Intake validates only shape. The PE classifier runs when the queued event
    # is consumed, never at host submission time.
    if not 2<=len(raw)<=5 or any(type(x) is not int for x in raw):
        raise IngressReject('INVALID_RAW_OBSERVATION')
    durable.validate('ctx0',choice,goal,tick)
    return {'observations':list(raw),'choice':choice,'goal':goal,'second_tick':tick}

def _row(db,epoch):
    r=db.execute('SELECT observations,choice,goal,second_tick,request_sha FROM v1w_intake WHERE epoch=?',(epoch,)).fetchone()
    if r is None:raise IngressReject('INGRESS_NOT_QUEUED')
    obj={'observations':json.loads(r[0]),'choice':r[1],'goal':r[2],'second_tick':r[3]}
    if digest([SCHEMA,'REQUEST',epoch,obj])!=r[4] or canonical(obj['observations'])!=r[0]:
        raise IngressReject('INGRESS_REQUEST_DRIFT')
    return obj,r[4]

def _genesis(reqsha,epoch):return digest([SCHEMA,'JOURNAL',epoch,reqsha])
def _stages(db,epoch,reqsha):
    previous=_genesis(reqsha,epoch);recs=[]
    for seq,stage,content,prev,h in db.execute('SELECT seq,stage,payload,previous_sha,row_sha FROM v1w_stages WHERE epoch=? ORDER BY seq',(epoch,)):
        if seq!=len(recs) or seq>=len(STAGES) or STAGES[seq]!=stage or prev!=previous:
            raise IngressReject('STAGED_CAUSAL_ORDER_DRIFT')
        try:payload=json.loads(content)
        except (TypeError,ValueError) as exc:raise IngressReject('STAGE_PAYLOAD_MALFORMED') from exc
        if content!=canonical(payload) or h!=digest([prev,stage,payload]):
            raise IngressReject('STAGE_RECEIPT_DRIFT')
        previous=h;recs.append(payload)
    return recs,previous

def _put_stage(db,epoch,reqsha,stage,payload):
    records,head=_stages(db,epoch,reqsha)
    if stage not in STAGES:raise IngressReject('INVALID_STAGE')
    seq=STAGES.index(stage)
    if seq<len(records):
        if records[seq]!=payload:raise IngressReject('STAGE_REEXECUTION_DRIFT')
        return False
    if seq!=len(records):raise IngressReject('STAGE_SKIPPED')
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('INSERT INTO v1w_stages VALUES(?,?,?,?,?,?)',
                   (epoch,seq,stage,canonical(payload),head,digest([head,stage,payload])))
        db.commit()
    except BaseException:db.rollback();raise
    return True

def _pe_evidence(raw):
    try:return sense.classify(raw)
    except sense.SensorReject as exc:raise IngressReject('PE_SENSORY_DENIAL:'+str(exc)) from exc

def _selected(db,epoch,reqsha,raw,source_sha):
    evidence=_pe_evidence(raw)
    _put_stage(db,epoch,reqsha,'PE_CLASSIFIED',{'evidence':evidence,'source_sha':source_sha})
    sig=evidence['signature']
    rows=db.execute('SELECT signature,context,first_epoch FROM v1w_binding ORDER BY first_epoch').fetchall()
    mapping={k:v for k,v,_ in rows}
    if len(mapping)!=len(rows):raise IngressReject('DUPLICATE_PE_CONTEXT')
    ctx=mapping.get(sig,'ctx'+str(len(mapping)))
    selected={'context':ctx,'signature':sig,'source_sha':source_sha,'evidence_sha':digest(evidence)}
    # Atomic selected-token-and-binding commit; the v1u direct epoch trigger
    # will not accept a context that has not first passed this PE stage.
    records,_=_stages(db,epoch,reqsha)
    if len(records)>2:
        if records[2]!=selected:raise IngressReject('PREVIOUS_P_BINDING_DRIFT')
    elif len(records)==2:
        db.execute('BEGIN IMMEDIATE')
        try:
            if sig not in mapping:
                db.execute('INSERT INTO v1w_binding VALUES(?,?,?)',(sig,ctx,epoch))
            db.execute('INSERT INTO v1w_permit VALUES(?,?,?,?)',(epoch,ctx,reqsha,sig))
            records,head=_stages(db,epoch,reqsha)
            db.execute('INSERT INTO v1w_stages VALUES(?,?,?,?,?,?)',
                    (epoch,2,'P_SELECTED',canonical(selected),head,digest([head,'P_SELECTED',selected])))
            db.commit()
        except BaseException:db.rollback();raise
    else:raise IngressReject('PE_EVIDENCE_MISSING')
    permit=db.execute('SELECT context,request_sha,signature FROM v1w_permit WHERE epoch=?',(epoch,)).fetchone()
    if permit!=(ctx,reqsha,sig):raise IngressReject('PE_P_PERMIT_DRIFT')
    return selected

def _check_epoch(db,epoch,root,source_sha,allow_open=False):
    req,reqsha=_row(db,epoch)
    stages,head=_stages(db,epoch,reqsha)
    if not stages:raise IngressReject('OBSERVED_STAGE_MISSING')
    if stages[0]!={'request_sha':reqsha}:raise IngressReject('OBSERVED_INGRESS_DRIFT')
    if len(stages)>=2:
        evidence=_pe_evidence(req['observations'])
        if stages[1]!={'evidence':evidence,'source_sha':source_sha}:
            raise IngressReject('PE_CLASSIFICATION_DRIFT')
    if len(stages)>=3:
        sig=evidence['signature']
        rows=db.execute('SELECT signature,context,first_epoch FROM v1w_binding ORDER BY first_epoch').fetchall()
        matches={k:(v,first) for k,v,first in rows}
        if sig not in matches:raise IngressReject('PE_CONTEXT_BINDING_MISSING')
        ctx=matches[sig][0]
        if stages[2]!={'context':ctx,'signature':sig,'source_sha':source_sha,'evidence_sha':digest(evidence)}:
            raise IngressReject('SELECTOR_P_BINDING_DRIFT')
        permit=db.execute('SELECT context,request_sha,signature FROM v1w_permit WHERE epoch=?',(epoch,)).fetchone()
        if permit!=(ctx,reqsha,sig):raise IngressReject('PERMIT_WITHOUT_ORIGINAL_EVIDENCE')
        child=db.execute('SELECT context,status,request_json,initial_p,final_p,result_sha FROM ctx_epochs WHERE id=?',(epoch,)).fetchone()
        if child is not None:
            if child[0]!=ctx:raise IngressReject('BV_LEARNING_CONTEXT_DRIFT')
            cr=json.loads(child[2]);target={'context':ctx,'choice':req['choice'],'goal':req['goal'],'second_tick':req['second_tick']}
            if cr!=target:raise IngressReject('BV_REQUEST_NOT_SENSED')
            if len(stages)>=4:
                if child[1]!='CLOSED':raise IngressReject('BV_NOT_CLOSED')
                claimed=stages[3]
                if (claimed.get('result_sha')!=child[5] or claimed.get('context')!=ctx
                    or claimed.get('initial_P')!=json.loads(child[3])
                    or claimed.get('final_P')!=json.loads(child[4])):
                    raise IngressReject('BV_RESULT_DIGEST_DRIFT')
            elif not allow_open and child[1]=='CLOSED':
                raise IngressReject('BV_COMPLETED_STAGE_MISSING')
        elif len(stages)>=4:raise IngressReject('BV_STAGED_WITHOUT_EXECUTION')
    if len(stages)==5:
        if stages[4]!={'closed_sha':digest([reqsha,stages[3],ctx])}:
            raise IngressReject('TERMINAL_STAGE_DRIFT')
    elif not allow_open:raise IngressReject('UNCLOSED_INGRESS')
    return {'epoch':epoch,'stages':len(stages),'head_sha256':head,
            'context':stages[2]['context'] if len(stages)>=3 else None,
            'signature':stages[2]['signature'] if len(stages)>=3 else None,
            'request_sha':reqsha}

def enqueue(path,epoch,observations,choice,goal,*,second_tick=30,root='.',wait_seconds=5.0):
    """Store a raw observation event only: no precomputed context or PE verdict."""
    if type(epoch) is not int or epoch<0:raise IngressReject('INVALID_EPOCH')
    req=_intake((observations,choice,goal,second_tick))
    source=sense._source_check(root)[sense.SOURCE_REL]
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        db=_db(p)
        try:
            prior=db.execute('SELECT COUNT(*) FROM v1w_intake').fetchone()[0]
            if epoch>prior:raise IngressReject('NONSEQUENTIAL_INGRESS')
            if epoch==prior and epoch:
                try:previous=_check_epoch(db,epoch-1,root,source)
                except IngressReject as exc:
                    if str(exc)=='UNCLOSED_INGRESS':
                        raise IngressReject('PREVIOUS_INGRESS_PENDING') from exc
                    raise
                if previous['stages']!=5:raise IngressReject('PREVIOUS_INGRESS_PENDING')
            reqsha=digest([SCHEMA,'REQUEST',epoch,req])
            db.execute('BEGIN IMMEDIATE')
            try:
                if epoch==prior:
                    db.execute('INSERT INTO v1w_intake VALUES(?,?,?,?,?,?)',
                      (epoch,canonical(req['observations']),choice,goal,second_tick,reqsha))
                else:
                    existing,_=_row(db,epoch)
                    if existing!=req:raise IngressReject('QUEUED_INGRESS_REWRITE_DENIED')
                db.commit()
            except BaseException:db.rollback();raise
            _put_stage(db,epoch,reqsha,'OBSERVED',{'request_sha':reqsha})
            return {'schema':SCHEMA,'epoch':epoch,'queued':True,'context':None,'request_sha':reqsha}
        finally:db.close()

def advance(path,epoch,*,root='.',pause_after=None,crash_after_stage=None,wait_seconds=5.0):
    """Consume PE ingress and the native v1 BV episode under one lock.

    Crash simulation after any stage is idempotently recoverable. BV stages
    are the existing v1 scheduler; classification occurs in the ingress stage,
    not yet as a native BV neuron event.
    """
    source=sense._source_check(root)[sense.SOURCE_REL]
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        db=_db(p)
        try:
            req,reqsha=_row(db,epoch)
            if epoch:
                _check_epoch(db,epoch-1,root,source)
            _check_epoch(db,epoch,root,source,allow_open=True)
            evidence=_pe_evidence(req['observations'])
            if crash_after_stage=='OBSERVED':raise PowerCut('AFTER_OBSERVED')
            selected=_selected(db,epoch,reqsha,req['observations'],source)
            if crash_after_stage=='PE_CLASSIFIED':raise PowerCut('AFTER_PE_CLASSIFIED')
            if crash_after_stage=='P_SELECTED':raise PowerCut('AFTER_P_SELECTED')
        finally:db.close()
        ctx=selected['context']
        # Original native-v1 same-scheduler PE/BV/P execution, using only the
        # PE-derived context. No host context parameter on this public API.
        result=durable.run_epoch(p,epoch,ctx,req['choice'],req['goal'],
                second_tick=req['second_tick'],pause_after=pause_after,root=root)
        db=_db(p)
        try:
            row=db.execute('SELECT result_sha,status FROM ctx_epochs WHERE id=?',(epoch,)).fetchone()
            if row is None or row[1]!='CLOSED' or row[0]!=result['episode']['output_sha256']:
                raise IngressReject('REAL_BV_P_RESULT_NOT_CLOSED')
            bv={'context':ctx,'result_sha':row[0],
                'final_P':result['episode']['final_P'],'initial_P':result['episode']['initial_P'],
                'first_C_PE_read':result['episode']['C_PE_reads'][0]}
            _put_stage(db,epoch,reqsha,'BV_COMPLETED',bv)
            if crash_after_stage=='BV_COMPLETED':raise PowerCut('AFTER_BV_COMPLETED')
            _put_stage(db,epoch,reqsha,'CLOSED',{'closed_sha':digest([reqsha,bv,ctx])})
            _check_epoch(db,epoch,root,source)
            if bv['first_C_PE_read'][1]!=bv['initial_P']['version'] or bv['first_C_PE_read'][2]!=bv['initial_P']['choice']:
                raise IngressReject('ACTUAL_C_PE_NOT_REBOUND_TO_SENSED_CONTEXT')
            return {'schema':SCHEMA,'status':'V1W_SENSED_CONTEXT_BV_P_CLOSED',
                    'epoch':epoch,'signature':selected['signature'],'derived_context':ctx,
                    'P_from':bv['initial_P'],'P_to':bv['final_P'],
                    'first_C_PE_read':bv['first_C_PE_read'],
                    'P_grants':len(result['episode']['P_grants']),
                    'new_tick_rows':result['episode']['new_tick_rows']}
        finally:db.close()

def run_epoch(path,epoch,observations,choice,goal,*,second_tick=30,
              pause_after=None,crash_after_stage=None,root='.',wait_seconds=5.0):
    enqueue(path,epoch,observations,choice,goal,second_tick=second_tick,root=root,wait_seconds=wait_seconds)
    return advance(path,epoch,root=root,pause_after=pause_after,
                   crash_after_stage=crash_after_stage,wait_seconds=wait_seconds)

def audit(path,*,root='.',wait_seconds=5.0):
    source=sense._source_check(root)[sense.SOURCE_REL]
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        db=_db(p)
        try:
            count=db.execute('SELECT COUNT(*) FROM v1w_intake').fetchone()[0]
            episodes=[_check_epoch(db,epoch,root,source) for epoch in range(count)]
            if len(episodes)!=count or any(item['stages']!=5 for item in episodes):
                raise IngressReject('INCOMPLETE_INGRESS_CHAIN')
            mapping={r[0]:r[1] for r in db.execute('SELECT signature,context FROM v1w_binding ORDER BY first_epoch')}
            if len(mapping)!=len(set(x['signature'] for x in episodes)):
                raise IngressReject('ORPHAN_CONTEXT_BINDING')
            first={};
            for x in episodes:first.setdefault(x['signature'],x['epoch'])
            for sig,ctx,ep in db.execute('SELECT signature,context,first_epoch FROM v1w_binding'):
                if first.get(sig)!=ep:raise IngressReject('PE_CONTEXT_FIRST_EPOCH_DRIFT')
            for signature,context in mapping.items():
                if context!=next(x['context'] for x in episodes if x['signature']==signature):
                    raise IngressReject('SIGNATURE_P_CONTEXT_DRIFT')
        finally:db.close()
        result=durable.audit(p,root=root)
        if len(result['epochs'])!=len(episodes):raise IngressReject('INGRESS_BV_EPOCH_COUNT_DRIFT')
        for evidence,epoch in zip(episodes,result['epochs']):
            if evidence['context']!=epoch['context'] or evidence['epoch']!=epoch['epoch']:
                raise IngressReject('INGRESS_BV_P_REPLAY_DRIFT')
        return {'schema':SCHEMA,'status':'V1W_STAGED_INGRESS_CHAIN_VERIFIED',
                'episodes':episodes,'P_bank':result['bank'],'BV_chain_sha256':result['chain_sha256'],
                'signatures':mapping,'chain_sha256':digest([[r['head_sha256'] for r in episodes],result['chain_sha256']])}
