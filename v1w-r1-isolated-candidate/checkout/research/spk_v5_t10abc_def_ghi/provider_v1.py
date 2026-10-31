"""T10ABC/DEF: independent *reference* v1 P admission provider, invoked
synchronously by the actual C-receipt-tick P-store UPDATE.

This is NOT the frozen/native SPK Memory Contract. A privileged host controls
both the provider callback and SQLite; sender evidence is NOT authenticated.
"""
from __future__ import annotations
import json, sqlite3
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject, ensure, digest, pe_step
from research.spk_v5_t9stu_vwx_yza.fenced_p_store_v1 import FencedMultiTickEngine, independent_grant_custody, TRIGGERS
from research.spk_v5_t9stu_vwx_yza.p_target_admission_port_v1 import target_for, native_authorize, NativeUnavailable

SCHEMA='spk-v1-reference-P-admission-provider/research-v1'

ADMISSION_SQL="""
CREATE TABLE reference_provider_receipt (
 cue INTEGER NOT NULL, expected_version INTEGER NOT NULL,
 grant_id INTEGER NOT NULL UNIQUE, event_id INTEGER NOT NULL UNIQUE,
 event_digest TEXT NOT NULL, reference_authority TEXT NOT NULL,
 PRIMARY KEY (cue,expected_version)
);
"""
GUARD_SQL="""CREATE TRIGGER spk_ref_v2_provider_guard BEFORE UPDATE ON p BEGIN
 SELECT RAISE(ABORT, 'P_REFERENCE_PROVIDER_DENIED') WHERE
 spk_ref_v2_provider_authorize(OLD.cue,OLD.choice,OLD.version,OLD.budget,
                               NEW.choice,NEW.version,NEW.budget)!=1;
 END"""
RECEIPT_SQL="""CREATE TRIGGER spk_ref_v2_provider_receipt AFTER UPDATE ON p BEGIN
 INSERT INTO reference_provider_receipt
 SELECT OLD.cue,OLD.version,g.id,ev.id,ev.digest,'REFERENCE_PROVIDER_V1'
 FROM p_grant g
 JOIN episode ep ON ep.id=g.episode_id
 JOIN event ev ON ev.episode_id=ep.id AND ev.kind='SEM_B_C' AND ev.status='DONE'
 WHERE g.cue=OLD.cue AND g.expected_version=OLD.version AND g.consumed=1
   AND ep.cue=OLD.cue AND ep.version=OLD.version AND ep.status='RUNNING'
   AND json_extract(ev.payload,'$.capsule.verdict')='WORSENED';
 SELECT RAISE(ABORT,'P_REFERENCE_PROVIDER_RECEIPT_REQUIRED')
 WHERE NOT EXISTS(SELECT 1 FROM reference_provider_receipt
   WHERE cue=OLD.cue AND expected_version=OLD.version);
 END"""
PROVIDER_TRIGGERS={'spk_ref_v2_provider_guard':GUARD_SQL,
                   'spk_ref_v2_provider_receipt':RECEIPT_SQL}

class ProviderFencedTickEngine(FencedMultiTickEngine):
    """Add a logically independent admission veto at actual C tick store write."""
    def __init__(self,path,*,learn=True,budget=12,max_inflight=3,create=True):
        self._t10_initializing=create
        super().__init__(path,learn=learn,budget=budget,max_inflight=max_inflight,create=create)
        self._t10_initializing=False
        self.provider_enabled=True
        self.db.create_function('spk_ref_v2_provider_authorize',7,self._authorize)
        if create:
            self.db.executescript(ADMISSION_SQL)
            for sql in PROVIDER_TRIGGERS.values():self.db.execute(sql)
        try:self.assert_provider()
        except BaseException:self.db.close();raise

    def assert_fence(self):
        # T9 requires exactly three original triggers. A V1 provider *additively*
        # owns two extra trigger names, without changing the frozen T9 source.
        found={r['name']:r['sql'] for r in self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='p'")}
        expected=dict(TRIGGERS)
        if not getattr(self,'_t10_initializing',False):expected.update(PROVIDER_TRIGGERS)
        ensure(set(found)==set(expected),'P_PROVIDER_FENCE_SET_DRIFT')
        for name,statement in expected.items():
            # Compare against canonical SQL stored in SQLite (the same rule
            # used in the original T9 store, but with additive v1 triggers).
            d=sqlite3.connect(':memory:')
            try:
                d.execute('CREATE TABLE p(cue,choice,version,budget)')
                d.execute(statement)
                canonical=d.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
                ensure(found[name]==canonical,'P_PROVIDER_FENCE_SQL_DRIFT_'+name)
            finally:d.close()

    def _authorize(self,cue,old_choice,version,budget,new_choice,new_version,new_budget):
        """Read-only provider decision. NEVER mints native SPK Memory grants."""
        if not self.provider_enabled:return 0
        try:
            scope=target_for(cue=cue,version=version)
            if scope['owner']!='C' or scope['domain']!='P' or scope['mode']!='execute' or scope['pe_id']!='PE-C-RESEARCH':return 0
            if (old_choice,new_choice) not in ((11,12),(12,11)) or new_version!=version+1 or new_budget!=budget-1 or budget<=0:return 0
            matching=self.db.execute('''
               SELECT g.id AS grant_id,g.consumed,g.verdict_digest,
                ep.id AS ep_id,ep.goal,ep.choice,ep.version AS ep_version,ep.status,ep.reference_grant,
                ev.id AS event_id,ev.payload AS semantic_payload,ev.digest AS event_digest,ev.tick,
                ev.episode_id AS event_episode,ev.status AS event_status
               FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
               JOIN event ev ON ev.episode_id=ep.id AND ev.kind='SEM_B_C' AND ev.status='DONE'
               WHERE g.cue=? AND g.expected_version=? AND ep.cue=? AND ep.version=? AND ep.choice=?
                 AND ep.status='RUNNING' AND ep.reference_grant IS NULL AND g.consumed=1''',
                (cue,version,cue,version,old_choice)).fetchall()
            if len(matching)!=1:return 0
            m=matching[0];sem=json.loads(m['semantic_payload']);cap=sem['capsule']
            if not (cap['decision']==m['ep_id'] and cap['cue']==cue and cap['choice']==old_choice and
                    cap['version']==version and cap['issuer']=='A' and cap['receiver']=='C' and
                    cap['verdict']=='WORSENED' and cap['authentication']=='UNATTESTED' and
                    m['goal']!=old_choice and m['tick']<=18 and
                    digest(cap)==m['verdict_digest'] and
                    m['event_digest']==digest({'id':m['event_id'],'episode':m['event_episode'],
                       'tick':m['tick'],'kind':'SEM_B_C','payload':sem})):return 0
            relay=self.db.execute('SELECT * FROM event WHERE id=?',(sem['parent'],)).fetchone()
            if relay is None or relay['episode_id']!=m['ep_id'] or relay['kind']!='SEM_A_B' or relay['status']!='DONE':return 0
            if json.loads(relay['payload'])['capsule']!=cap or sem['relay_digest']!=relay['digest']:return 0
            a=self.db.execute('SELECT * FROM event WHERE id=?',(cap['A_event'],)).fetchone()
            if a is None or a['episode_id']!=m['ep_id'] or a['kind']!='PE_A' or a['status']!='DONE':return 0
            if json.loads(relay['payload'])['parent']!=a['id'] or cap['A_event_digest']!=a['digest']:return 0
            ap=pe_step('A',old_choice,m['goal'],12,[3 if old_choice==11 else 4])
            if cap['A_PE_digest']!=digest(ap) or ap['emits']!=[22,7]:return 0
            return 1
        except (ValueError,KeyError,TypeError,IndexError,sqlite3.Error):return 0

    def assert_provider(self):
        names={r['name']:r['sql'] for r in self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='p'")}
        ensure(set(PROVIDER_TRIGGERS).issubset(names),'PROVIDER_MISSING_TRIGGER')
        for n,sql in PROVIDER_TRIGGERS.items():
            ensure(names[n]==sql,'PROVIDER_TRIGGER_DRIFT_'+n)
        table=self.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reference_provider_receipt'").fetchone()
        ensure(table is not None,'PROVIDER_MISSING_RECEIPT_STORE')

    def audit_provider(self):
        self.assert_provider()
        base=self.audit();custody=independent_grant_custody(self)
        grants=list(self.db.execute('SELECT * FROM p_grant ORDER BY id'))
        receipts=list(self.db.execute('SELECT * FROM reference_provider_receipt ORDER BY cue,expected_version'))
        ensure(len(grants)==len(receipts)==base['reference_v1_tick_grants'],'PROVIDER_GRANT_COMMIT_CARDINALITY')
        result=[]
        for r in receipts:
            g=self.db.execute('SELECT * FROM p_grant WHERE id=?',(r['grant_id'],)).fetchone()
            ev=self.db.execute('SELECT * FROM event WHERE id=?',(r['event_id'],)).fetchone()
            ensure(g is not None and ev is not None and g['cue']==r['cue'] and
                   g['expected_version']==r['expected_version'] and
                   ev['episode_id']==g['episode_id'] and ev['kind']=='SEM_B_C' and ev['status']=='DONE' and
                   ev['digest']==r['event_digest'] and r['reference_authority']=='REFERENCE_PROVIDER_V1',
                   'PROVIDER_RECEIPT_LINEAGE_DRIFT')
            result.append({'cue':r['cue'],'version':r['expected_version'],
                           'grant':r['grant_id'],'event':r['event_id'],'digest':r['event_digest']})
        return {'provider_v1_authorizations':len(result),'provider_v1_commits':len(result),
                'provider_receipts_sha256':digest(result),'independent_reference_custody':custody,
                'native_SPK_Memory_Contract_grants':0,'provider_origin_authenticated':False}

    def reopen(self):
        self.close()
        self.__init__(self.path,learn=self.learn,budget=self.budget,max_inflight=self.max_inflight,create=False)


def native_gate_must_deny(target):
    try:native_authorize(target)
    except NativeUnavailable:return 'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'
    raise Reject('UNEXPECTED_NATIVE_MEMORY_ADMISSION')
