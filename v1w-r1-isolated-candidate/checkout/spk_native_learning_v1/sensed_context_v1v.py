"""v1v: original-PE observation classifier and durable context bindings.

This is a bounded pre-episode PE sensory admission port; the original BV-v0e
and v1u scheduler are unchanged.  The host chooses raw sensor channels,
world and goal; there is NO authenticated independent sensor, autonomous goal
inference, or general context discovery.  The PE output, not a host label,
selects the P bank before the normal same-scheduler v1u learning episode.
"""
from __future__ import annotations
import hashlib,json,sqlite3
from dataclasses import replace
from pathlib import Path
from spk_native_learning_v1 import contextual_durable_v1u as d
from spk_native_learning_v1.generalized_serial_v1t import serialized_ownership
from spk_native_learning_v1.generalized_case_v1t import build_case,pin_sources
from spk_native_learning_v1 import generalized_durable_v1t as canonical_base

SCHEMA='spk-native-learning-sensed-context/v1v'
ALPHA=(40,42)
BETA=(41,43)
NOISE=99
SIGNAL_PROGRAMS={
  71:(('ACC',(1,40)),('ACC',(1,42)),('CMP',2),('EMIT',71),('RESET',0)),
  72:(('ACC',(1,41)),('ACC',(1,43)),('CMP',2),('EMIT',72),('RESET',0)),
}

SIGNALS={71:'s71',72:'s72'}
SOURCE_REL='spk_architecture_v1/pe_execution_v1b.py'
class SensorReject(RuntimeError):pass

def _hash(data):return hashlib.sha256(canonical_base.canonical(data).encode('utf-8')).hexdigest()

def _source_check(root):
    # The frozen custody check is authoritative. Only its precise PE import
    # identity mismatch is normalized to the public sensor-admission error.
    # File drift, missing frozen code, and memory identity failures propagate.
    try:
        pins=pin_sources(root)
    except AssertionError as exc:
        if str(exc) != 'FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH':
            raise
        raise SensorReject('ORIGINAL_PE_PROVENANCE_DENIED') from exc
    from spk_architecture_v1 import pe_execution_v1b as original
    from spk_native_learning_v1 import generalized_scheduler_v1t as runtime
    if runtime._compute_local is not original._compute_local or runtime._admit is not original._admit:
        raise SensorReject('ORIGINAL_PE_PROVENANCE_DENIED')
    if not Path(original.__file__).resolve()==(Path(root).resolve()/SOURCE_REL):
        raise SensorReject('ORIGINAL_PE_MODULE_PATH_DENIED')
    return pins

def _channels(observations):
    if type(observations) not in (tuple,list) or not 2<=len(observations)<=5:
        raise SensorReject('INVALID_OBSERVATION_BATCH')
    if any(type(x) is not int or x not in (40,41,42,43,99) for x in observations):
        raise SensorReject('UNKNOWN_SENSOR_CHANNEL')
    if len(set(observations))!=len(observations):raise SensorReject('DUPLICATED_SENSOR_OCCURRENCE')
    if tuple(observations)!=tuple(sorted(observations)):
        raise SensorReject('NONCANONICAL_SENSOR_BATCH')
    return tuple(observations)

def classify(observations):
    """Compute exact class using frozen _compute_local, reject absence/ambiguity."""
    ch=_channels(observations)
    from spk_architecture_v1.pe_execution_v1b import _compute_local
    # Reuse an originally typed node, not a stand-in pseudo-PE.
    c=next(n for n in build_case(11,11).nodes if n.node_id=='C')
    # Separate PE invocations keep candidate accumulator states disjoint.
    # Joining the instructions would make a partial match from one candidate
    # leak into the next (RESET is conditional in original PE semantics).
    matched=[];final_states=[]
    for candidate,program in SIGNAL_PROGRAMS.items():
        neuron=replace(c,instructions=program,initial_raw=0)
        state,guard,emitted=_compute_local(neuron,(0,0),1,ch)
        final_states.append([candidate,state,bool(guard)])
        matched.extend(emitted)
    outputs=tuple(matched)

    if len(outputs)!=1 or outputs[0] not in SIGNALS:
        raise SensorReject('UNKNOWN_OR_AMBIGUOUS_PE_CONTEXT')
    # Missing component of a pair is never sufficient. PE itself carries
    # the conjunction; protocol also rejects duplicate sensor occurrences.
    return {'schema':'spk-pe-sensed-context-evidence/v1v','raw_channels':list(ch),
            'pe_emissions':list(outputs),'signature':SIGNALS[outputs[0]],
            'pe_candidate_states':final_states,
            'original_pe_source':SOURCE_REL}

def _db(path):
    db=d.open_db(path)
    db.executescript('''
     CREATE TABLE IF NOT EXISTS sensed_bindings(
       signature TEXT PRIMARY KEY, context TEXT NOT NULL UNIQUE, first_epoch INTEGER NOT NULL,
       pe_emission INTEGER NOT NULL, source_sha TEXT NOT NULL);
     CREATE TABLE IF NOT EXISTS sensed_epoch(
       epoch INTEGER PRIMARY KEY, raw_json TEXT NOT NULL, evidence_json TEXT NOT NULL,
       context TEXT NOT NULL, signature TEXT NOT NULL, source_sha TEXT NOT NULL,
       previous_sha TEXT NOT NULL, record_sha TEXT NOT NULL);
    ''')
    return db

def _verified_selector_chain(db,source_sha,allow_pending=False):
    rows=db.execute('SELECT epoch,raw_json,evidence_json,context,signature,source_sha,previous_sha,record_sha FROM sensed_epoch ORDER BY epoch').fetchall()
    assigned={};previous=_hash([SCHEMA,'GENESIS',source_sha]);ledger=[]
    for seq,row in enumerate(rows):
        epoch,raw_s,ev_s,ctx,sig,src,prev,stored=row
        if epoch!=seq or prev!=previous or src!=source_sha:
            raise SensorReject('SENSOR_CHAIN_ORDER_OR_SOURCE_DRIFT')
        try:raw=json.loads(raw_s)
        except (ValueError,TypeError):raise SensorReject('MALFORMED_OBSERVATION_RECORD')
        evidence=classify(raw)
        if ev_s!=canonical_base.canonical(evidence) or sig!=evidence['signature']:
            raise SensorReject('PE_OBSERVATION_EVIDENCE_DRIFT')
        if sig not in assigned:assigned[sig]=(f'ctx{len(assigned)}',seq,evidence['pe_emissions'][0])
        expected_ctx,first_epoch,emission=assigned[sig]
        if ctx!=expected_ctx:raise SensorReject('CONTEXT_BINDING_DRIFT')
        record={'schema':SCHEMA,'epoch':epoch,'observations':raw,
                'evidence':evidence,'signature':sig,'context':ctx,'source_sha':src}
        digest=_hash([previous,record])
        if stored!=digest:raise SensorReject('SENSOR_EPOCH_RECORD_DRIFT')
        companion=db.execute('SELECT context,status,request_json FROM ctx_epochs WHERE id=?',(epoch,)).fetchone()
        if companion is None and allow_pending and seq==len(rows)-1:
            state='PENDING_SENSOR_ONLY'
        else:
            if companion is None or companion[0]!=ctx:
                raise SensorReject('SELECTED_CONTEXT_NOT_USED_BY_P_EPOCH')
            try:request=json.loads(companion[2])
            except (ValueError,TypeError):raise SensorReject('MALFORMED_CONTEXT_EPOCH_REQUEST')
            if request.get('context')!=ctx:raise SensorReject('CONTEXT_REQUEST_DIVERGENCE')
            state=companion[1]
        previous=digest;ledger.append({'epoch':epoch,'context':ctx,'signature':sig,'record_sha':digest,
                                        'status':state})
    bindings=db.execute('SELECT signature,context,first_epoch,pe_emission,source_sha FROM sensed_bindings ORDER BY first_epoch').fetchall()
    expected=sorted(((sig,ctx,tick,emission,source_sha) for sig,(ctx,tick,emission) in assigned.items()),key=lambda x:x[2])
    if bindings!=expected:raise SensorReject('PERSISTENT_PE_BINDING_DRIFT')
    return {'head_sha256':previous,'ledger':ledger,'bindings':{sig:ctx for sig,(ctx,_,_) in assigned.items()}}

def _add_selector(db,epoch,channels,evidence,source_sha):
    raw_s=canonical_base.canonical(list(channels));ev_s=canonical_base.canonical(evidence)
    db.execute('BEGIN IMMEDIATE')
    try:
        pre=_pending_selector_check(db,source_sha)
        rows=pre['ledger'];head=pre['head_sha256']
        if epoch<len(rows):
            row=db.execute('SELECT raw_json,evidence_json,context,signature,source_sha FROM sensed_epoch WHERE epoch=?',(epoch,)).fetchone()
            if row[0]!=raw_s or row[1]!=ev_s or row[3]!=evidence['signature'] or row[4]!=source_sha:
                raise SensorReject('PREVIOUS_EPISODE_SENSOR_CHANGE')
            chosen=row[2]
        elif epoch==len(rows):
            sig=evidence['signature'];chosen=pre['bindings'].get(sig,f'ctx{len(pre["bindings"])}')
            if sig not in pre['bindings']:
                db.execute('INSERT INTO sensed_bindings VALUES(?,?,?,?,?)',
                    (sig,chosen,epoch,evidence['pe_emissions'][0],source_sha))
            record={'schema':SCHEMA,'epoch':epoch,'observations':list(channels),
                    'evidence':evidence,'signature':sig,'context':chosen,'source_sha':source_sha}
            digest=_hash([head,record])
            db.execute('INSERT INTO sensed_epoch VALUES(?,?,?,?,?,?,?,?)',
                (epoch,raw_s,ev_s,chosen,sig,source_sha,head,digest))
        else:raise SensorReject('NONSEQUENTIAL_SENSOR_EPOCH')
        db.commit()
        return chosen
    except BaseException:db.rollback();raise

def _complete_selector_check(db,source_sha):
    """Check stored signal ownership AFTER corresponding contextual epoch exists."""
    return _verified_selector_chain(db,source_sha)

def _pending_selector_check(db,source_sha):
    """Permit only the latest PE selection to precede its episodic journal."""
    sel=db.execute('SELECT COUNT(*) FROM sensed_epoch').fetchone()[0]
    ctx=db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]
    if sel not in (ctx,ctx+1):raise SensorReject('SELECTOR_CONTEXT_PREFIX_MISMATCH')
    return _verified_selector_chain(db,source_sha,allow_pending=(sel==ctx+1))

def run_epoch(path,epoch,observations,choice,goal,*,second_tick=30,pause_after=None,root='.',wait_seconds=5.0):
    if type(epoch) is not int or epoch<0:raise SensorReject('INVALID_EPOCH')
    pins=_source_check(root);source_sha=pins[SOURCE_REL]
    evidence=classify(observations);channels=tuple(evidence['raw_channels'])
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        db=_db(p)
        try:
            _pending_selector_check(db,source_sha)
            context=_add_selector(db,epoch,channels,evidence,source_sha)
        finally:db.close()
        result=d.run_epoch(p,epoch,context,choice,goal,second_tick=second_tick,pause_after=pause_after,root=root)
        db=_db(p)
        try:
            complete=_complete_selector_check(db,source_sha)
        finally:db.close()
        return {'schema':SCHEMA,'derived_context':context,'PE_signature':evidence['signature'],
                'PE_emissions':evidence['pe_emissions'],'episode':result['episode'],
                'bank':result['bank'],'selector_chain_sha256':complete['head_sha256']}

def audit(path,*,root='.',wait_seconds=5.0):
    pins=_source_check(root);source_sha=pins[SOURCE_REL]
    with serialized_ownership(path,wait_seconds=wait_seconds) as p:
        db=_db(p)
        try:selection=_verified_selector_chain(db,source_sha)
        finally:db.close()
        chain=d.audit(p,root=root)
        if len(selection['ledger'])!=len(chain['epochs']):raise SensorReject('LEDGER_LENGTH_DRIFT')
        for row,record in zip(selection['ledger'],chain['epochs']):
            if row['context']!=record['context'] or row['epoch']!=record['epoch']:
                raise SensorReject('SENSOR_P_LEDGER_CROSS_CONTEXT_DRIFT')
        return {'schema':SCHEMA,'status':'SENSED_PE_CONTEXT_BINDINGS_VERIFIED',
                'selector':selection,'contextual':chain,
                'chain_sha256':_hash([selection['head_sha256'],chain['chain_sha256']])}

def run_sequence(path,cases,*,root='.',wait_seconds=5.0,stop_after=None):
    if type(cases) not in (list,tuple) or not cases:raise SensorReject('INVALID_CASES')
    out=[]
    for epoch,case in enumerate(cases):
        if type(case) not in (list,tuple) or len(case)!=3:raise SensorReject('INVALID_CASE')
        receipt=run_epoch(path,epoch,*case,root=root,wait_seconds=wait_seconds)
        out.append(receipt)
        if stop_after==epoch:raise d.SimulatedPowerLoss('AFTER_CLOSED_EPOCH:'+str(epoch))
    return {'schema':SCHEMA,'episodes':out,'audit':audit(path,root=root,wait_seconds=wait_seconds),
            'new_tick_rows':sum(r['episode']['new_tick_rows'] for r in out)}
