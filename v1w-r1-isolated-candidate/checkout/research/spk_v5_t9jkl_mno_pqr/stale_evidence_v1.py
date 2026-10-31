"""T9JKL: isolate non-creditable historical verdicts from reference V1 P authority.

Research-only observer. Audits actual persisted engine events and CAS veto records;
never writes to the running engine database and never grants P authority.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, pack, digest, Reject

SCHEMA='spk-v1-reference-historical-verdict-evidence/v0'

def attestable_stale(engine):
    """Extract stable evidence from a *live locally audited* engine, not a pasted counter."""
    engine.audit()
    db=engine.db
    vetoes=[]
    for r in db.execute("SELECT * FROM ledger WHERE kind='VETO_STALE_POLICY' ORDER BY seq"):
        b=json.loads(r['payload'])
        ev=db.execute('SELECT * FROM event WHERE id=?',(b['feedback_event'],)).fetchone()
        ep=db.execute('SELECT * FROM episode WHERE id=?',(b['episode'],)).fetchone()
        ensure(ev is not None and ep is not None and ev['episode_id']==ep['id'] and
               ev['kind']=='SEM_B_C' and ev['status']=='DONE' and ep['status']=='SETTLED' and
               ep['reference_grant'] is None,'EVIDENCE_EVENT_NOT_SETTLED')
        payload=json.loads(ev['payload']);cap=payload['capsule']
        ensure(b['cue']==ep['cue']==cap['cue'] and b['issued_version']==ep['version']==cap['version'] and
               b['current_version']>b['issued_version'] and cap['decision']==ep['id'] and
               b['verdict']==cap['verdict']==ep['outcome'] and cap['issuer']=='A' and cap['receiver']=='C' and
               cap['authentication']=='UNATTESTED' and
               ev['digest']==digest({'id':ev['id'],'episode':ev['episode_id'],'tick':ev['tick'],'kind':ev['kind'],'payload':payload}),
               'EVIDENCE_PROVENANCE_OR_VERSION_DRIFT')
        parent=db.execute('SELECT * FROM event WHERE id=?',(payload['parent'],)).fetchone()
        ensure(parent is not None and parent['kind']=='SEM_A_B' and parent['status']=='DONE' and
               payload['relay_digest']==parent['digest'] and json.loads(parent['payload'])['capsule']==cap,
               'EVIDENCE_RELAY_DRIFT')
        vetoes.append({'episode':ep['id'],'cue':ep['cue'],'choice':ep['choice'],
            'issued_version':ep['version'],'observed_version':b['current_version'],
            'verdict':b['verdict'],'feedback_event':ev['id'],'feedback_digest':ev['digest'],
            'source_veto_ledger_seq':r['seq'],'source_veto_ledger_digest':r['digest'],
            'authority':'OBSERVATION_ONLY','P_grant_allowed':False,
            'sensor_authenticated':False})
    ensure(len(vetoes)==engine.audit()['stale_vetoes'],'EVIDENCE_VETO_COUNT_DRIFT')
    ensure(len({v['feedback_digest'] for v in vetoes})==len(vetoes),'DUPLICATE_SOURCE_EVIDENCE')
    return vetoes

class HistoricalEvidence:
    """Separate durable observer with replay rejection. Not a proof against privileged host."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path),isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS evidence (seq INTEGER PRIMARY KEY, source_digest TEXT UNIQUE NOT NULL, row TEXT NOT NULL, previous TEXT NOT NULL, tip TEXT NOT NULL)')
        self.audit()
    def close(self): self.db.close()
    def reopen(self):self.close();self.__init__(self.path)
    def append(self,row):
        ensure(type(row) is dict and row.get('authority')=='OBSERVATION_ONLY' and
               row.get('P_grant_allowed') is False and row.get('sensor_authenticated') is False and
               row.get('observed_version',0)>row.get('issued_version',0) and
               row.get('verdict') in ('IMPROVED','WORSENED'),'UNSAFE_HISTORICAL_RECORD')
        ensure(type(row.get('feedback_digest')) is str and len(row['feedback_digest'])==64,
               'SOURCE_DIGEST_INVALID')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prev=self.db.execute('SELECT seq,tip FROM evidence ORDER BY seq DESC LIMIT 1').fetchone()
            seq=(prev[0]+1) if prev else 0
            prior=prev[1] if prev else '0'*64
            tip=digest({'seq':seq,'source':row['feedback_digest'],'row':row,'previous':prior})
            ensure(self.db.execute('SELECT 1 FROM evidence WHERE source_digest=?',(row['feedback_digest'],)).fetchone() is None,'HISTORICAL_REPLAY')
            self.db.execute('INSERT INTO evidence VALUES(?,?,?,?,?)',(seq,row['feedback_digest'],pack(row),prior,tip))
            self.db.execute('COMMIT')
            return tip
        except BaseException:self.db.execute('ROLLBACK');raise
    def audit(self):
        previous='0'*64;rows=[]
        for seq,source,row,prev,tip in self.db.execute('SELECT * FROM evidence ORDER BY seq'):
            d=json.loads(row)
            ensure(seq==len(rows) and prev==previous and source==d['feedback_digest'] and
                   tip==digest({'seq':seq,'source':source,'row':d,'previous':prev}) and
                   d['authority']=='OBSERVATION_ONLY' and d['P_grant_allowed'] is False and
                   d['sensor_authenticated'] is False,'HISTORICAL_LEDGER_DRIFT')
            previous=tip;rows.append(d)
        return {'historical_records':len(rows),'tip':previous,'rows_digest':digest(rows),'P_grants':0}
