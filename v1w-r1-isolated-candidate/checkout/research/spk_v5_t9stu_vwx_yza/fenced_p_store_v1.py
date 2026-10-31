"""T9STU: reference-v1 P-store enforcement using SQLite triggers.

This is host-owned research SQLite, NOT a SPK native Memory Contract grant.
A privileged host may drop the trigger or reseal the database.
"""
from __future__ import annotations
import json
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import MultiTickEngine, Reject, ensure, digest, pe_step

TRIGGER_SQL = """
CREATE TRIGGER spk_ref_p_fence BEFORE UPDATE ON p BEGIN
 SELECT RAISE(ABORT, 'P_REFERENCE_GRANT_REQUIRED') WHERE NOT EXISTS (
   SELECT 1 FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
   JOIN event ev ON ev.episode_id=ep.id AND ev.kind='SEM_B_C' AND ev.status='DONE'
   WHERE g.cue=OLD.cue AND g.expected_version=OLD.version AND g.consumed=1
     AND ep.cue=OLD.cue AND ep.version=OLD.version AND ep.choice=OLD.choice
     AND ep.status='RUNNING' AND ep.id=g.episode_id
     AND json_extract(ev.payload,'$.capsule.verdict')='WORSENED'
     AND json_extract(ev.payload,'$.capsule.version')=OLD.version
     AND json_extract(ev.payload,'$.capsule.decision')=ep.id
 );
 SELECT RAISE(ABORT, 'P_REFERENCE_TRANSITION_INVALID') WHERE
   NEW.cue != OLD.cue OR NEW.version != OLD.version+1
   OR NEW.budget != OLD.budget-1 OR OLD.budget <= 0
   OR NEW.choice != (CASE OLD.choice WHEN 11 THEN 12 WHEN 12 THEN 11 ELSE -1 END);
END
"""
INSERT_TRIGGER="CREATE TRIGGER spk_ref_p_no_insert BEFORE INSERT ON p BEGIN SELECT RAISE(ABORT,'P_INSERT_DENIED'); END"
DELETE_TRIGGER="CREATE TRIGGER spk_ref_p_no_delete BEFORE DELETE ON p BEGIN SELECT RAISE(ABORT,'P_DELETE_DENIED'); END"
TRIGGERS={'spk_ref_p_fence':TRIGGER_SQL,'spk_ref_p_no_insert':INSERT_TRIGGER,'spk_ref_p_no_delete':DELETE_TRIGGER}

class FencedMultiTickEngine(MultiTickEngine):
    def __init__(self,path,*,learn=True,budget=12,max_inflight=3,create=True):
        super().__init__(path,learn=learn,budget=budget,max_inflight=max_inflight,create=create)
        if create:
            for sql in TRIGGERS.values():self.db.execute(sql)
        try:self.assert_fence()
        except BaseException:
            self.db.close()
            raise

    def assert_fence(self):
        existing={r['name']:r['sql'] for r in self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='p'")}
        ensure(set(existing)==set(TRIGGERS),'REFERENCE_P_FENCE_MISSING_OR_EXTRA')
        for name,sql in TRIGGERS.items():
            # Compare SQLite's stored canonical trigger text against an independently
            # created template database, without claiming external host integrity.
            import sqlite3
            d=sqlite3.connect(':memory:')
            try:
                d.executescript('CREATE TABLE p(cue INTEGER,choice INTEGER,version INTEGER,budget INTEGER);')
                d.execute(sql)
                template=d.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
                ensure(existing[name]==template,'REFERENCE_P_FENCE_DRIFT')
            finally:d.close()

    def reopen(self):
        self.close();self.__init__(self.path,learn=self.learn,budget=self.budget,max_inflight=self.max_inflight,create=False)

def independent_grant_custody(engine):
    """Independently inspect persisted C-receipt/A-PE/relay/grant lineage.

    Checks claims for internal trace coherence only, not sender authentication.
    """
    rows=[]
    for grant in engine.db.execute('SELECT * FROM p_grant ORDER BY id').fetchall():
        e=engine.db.execute('SELECT * FROM episode WHERE id=?',(grant['episode_id'],)).fetchone()
        ensure(e is not None and e['status']=='SETTLED','GRANT_EPISODE_MISSING')
        sem=engine.db.execute("SELECT * FROM event WHERE episode_id=? AND kind='SEM_B_C' AND status='DONE'",(e['id'],)).fetchall()
        ensure(len(sem)==1,'GRANT_MISSING_C_TICK')
        sem=sem[0];sem_body=json.loads(sem['payload']);cap=sem_body['capsule']
        relay=engine.db.execute('SELECT * FROM event WHERE id=?',(sem_body['parent'],)).fetchone()
        ensure(relay is not None and relay['kind']=='SEM_A_B' and relay['status']=='DONE','RELAY_MISSING')
        relay_body=json.loads(relay['payload']);ensure(relay_body['capsule']==cap and sem_body['relay_digest']==relay['digest'],'RELAY_TAMPER')
        aa=engine.db.execute('SELECT * FROM event WHERE id=?',(cap['A_event'],)).fetchone()
        ensure(aa is not None and aa['kind']=='PE_A' and aa['status']=='DONE'
               and relay_body['parent']==aa['id'] and cap['A_event_digest']==aa['digest'],'A_EVENT_MISMATCH')
        recomputed=pe_step('A',e['choice'],e['goal'],12,[3 if e['choice']==11 else 4])
        ensure(cap['A_PE_digest']==digest(recomputed) and recomputed['emits']==[22,7]
               and cap['verdict']=='WORSENED','A_PE_VERDICT_NOT_CAUSAL_IN_MODEL')
        ensure(grant['cue']==e['cue'] and grant['expected_version']==e['version']
               and grant['verdict_digest']==digest(cap) and grant['consumed']==1
               and e['reference_grant']==grant['id'],'GRANT_SCOPE_MISMATCH')
        matches=[]
        for log in engine.db.execute("SELECT * FROM ledger WHERE kind='GRANT_P'"):
            obj=json.loads(log['payload'])
            if obj['grant']==grant['id']:matches.append(obj)
        ensure(len(matches)==1 and matches[0]['owner']=='C' and matches[0]['domain']=='P'
               and matches[0]['mode']=='execute' and matches[0]['expected_version']==e['version']
               and matches[0]['receipt_digest']==digest(cap),'GRANT_LEDGER_BINDING')
        rows.append({'episode':e['id'],'cue':e['cue'],'version':e['version'],
                     'A_event':aa['id'],'C_event':sem['id'],'grant':grant['id'],
                     'receipt_digest':grant['verdict_digest']})
    audit=engine.audit()
    ensure(len(rows)==audit['reference_v1_tick_grants'],'P_AUTHORITY_COUNT_DRIFT')
    return {'verified_reference_grants':len(rows),'grant_custody_sha256':digest(rows),
            'native_SPK_memory_grants':0,'authenticated_A_source':False}
