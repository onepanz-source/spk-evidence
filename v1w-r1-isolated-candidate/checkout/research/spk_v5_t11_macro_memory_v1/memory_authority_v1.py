"""Versioned SPK V1 *new-runtime* Memory Authority, actually invoked in C ticks.

This is executable owned memory-admission logic for the NEW research runtime.
It is NOT an adoption of the frozen SPK Memory Contract, an authenticated
sender, or a grant executed by the legacy SPK runtime. Host controls SQLite.

Six design invariants: explicit scope, native-denial, single-use P credit,
resource quotas, same-transaction grant/P CAS, fail-closed crash recovery.
"""
from __future__ import annotations
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure,digest,Reject
from research.spk_v5_t10jkl_mno_pqr.resource_authority_v1 import ResourceAdmittedEngine
from research.spk_v5_t10stu_vwx_yza.surface_probe_v0 import read_only_contract_request,reject_native_promotion

CONTRACT_SCHEMA="""CREATE TABLE v1_owned_memory_authority (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  owner TEXT NOT NULL CHECK(owner='C'),domain TEXT NOT NULL CHECK(domain='P'),
  pe_id TEXT NOT NULL CHECK(pe_id='PE-C-RESEARCH'),
  mode TEXT NOT NULL CHECK(mode IN ('execute','verify')),
  global_ceiling INTEGER NOT NULL CHECK(global_ceiling BETWEEN 0 AND 48),
  context0_ceiling INTEGER NOT NULL CHECK(context0_ceiling BETWEEN 0 AND 48),
  context1_ceiling INTEGER NOT NULL CHECK(context1_ceiling BETWEEN 0 AND 48),
  revision INTEGER NOT NULL CHECK(revision>=0)
)"""
GRANT_SCHEMA="""CREATE TABLE v1_owned_memory_grant (
  grant_id INTEGER PRIMARY KEY,
  cue INTEGER NOT NULL CHECK(cue IN (0,1)),
  expected_version INTEGER NOT NULL CHECK(expected_version>=0),
  event_id INTEGER NOT NULL UNIQUE,
  event_digest TEXT NOT NULL,
  authority_revision INTEGER NOT NULL,
  owner TEXT NOT NULL CHECK(owner='C'),
  domain TEXT NOT NULL CHECK(domain='P'),
  mode TEXT NOT NULL CHECK(mode='execute'),
  pe_id TEXT NOT NULL CHECK(pe_id='PE-C-RESEARCH'),
  UNIQUE(cue,expected_version)
)"""
GRANT_TRIGGER="""CREATE TRIGGER spk_new_v1_owned_memory_grant
AFTER INSERT ON reference_provider_receipt BEGIN
 SELECT RAISE(ABORT,'V1_MEMORY_NO_EXECUTE_AUTHORITY') WHERE NOT EXISTS (
   SELECT 1 FROM v1_owned_memory_authority WHERE singleton=1 AND
   owner='C' AND domain='P' AND pe_id='PE-C-RESEARCH' AND mode='execute');
 SELECT RAISE(ABORT,'V1_MEMORY_CAPACITY_EXHAUSTED') WHERE
   (SELECT COUNT(*) FROM v1_owned_memory_grant) >=
       (SELECT global_ceiling FROM v1_owned_memory_authority WHERE singleton=1)
   OR (SELECT COUNT(*) FROM v1_owned_memory_grant WHERE cue=NEW.cue) >=
       (SELECT CASE NEW.cue WHEN 0 THEN context0_ceiling ELSE context1_ceiling END
        FROM v1_owned_memory_authority WHERE singleton=1);
 INSERT INTO v1_owned_memory_grant
 SELECT NEW.grant_id, NEW.cue, NEW.expected_version, NEW.event_id,
   NEW.event_digest, revision, owner, domain, mode, pe_id
   FROM v1_owned_memory_authority WHERE singleton=1;
END"""

class OwnedMemoryV1(ResourceAdmittedEngine):
    """Owns admission AND P grant accounting during the real research C tick."""
    def __init__(self,path,*,learn=True,budget=12,max_inflight=3,create=True,
                 global_ceiling=8,context_ceiling=4):
        self.authority_enabled=True
        self._memory_ready=not create
        super().__init__(path,learn=learn,budget=budget,max_inflight=max_inflight,
                         create=create,grant_ceiling=8,context_ceiling=4)
        if create:
            ensure(type(global_ceiling) is int and 0<=global_ceiling<=48,'V1_GLOBAL_BUDGET_INVALID')
            ensure(type(context_ceiling) is int and 0<=context_ceiling<=48,'V1_CONTEXT_BUDGET_INVALID')
            self.db.execute(CONTRACT_SCHEMA)
            self.db.execute(GRANT_SCHEMA)
            self.db.execute('INSERT INTO v1_owned_memory_authority VALUES(1,?,?,?,?,?,?,?,0)',
                            ('C','P','PE-C-RESEARCH','execute',global_ceiling,context_ceiling,context_ceiling))
            self.db.execute(GRANT_TRIGGER)
            self._memory_ready=True
        try:self.audit_owned_memory()
        except BaseException:self.db.close();raise

    def _authorize(self,cue,old_choice,version,budget,new_choice,new_version,new_budget):
        if not self.authority_enabled or not self._memory_ready:return 0
        r=self.db.execute('SELECT * FROM v1_owned_memory_authority WHERE singleton=1').fetchone()
        if r is None or (r['owner'],r['domain'],r['pe_id'],r['mode'])!=('C','P','PE-C-RESEARCH','execute'):
            return 0
        if self.db.execute('SELECT COUNT(*) FROM v1_owned_memory_grant').fetchone()[0]>=r['global_ceiling']:
            return 0
        if self.db.execute('SELECT COUNT(*) FROM v1_owned_memory_grant WHERE cue=?',(cue,)).fetchone()[0]>=r['context0_ceiling' if cue==0 else 'context1_ceiling']:
            return 0
        return super()._authorize(cue,old_choice,version,budget,new_choice,new_version,new_budget)

    def policy(self):
        r=self.db.execute('SELECT * FROM v1_owned_memory_authority WHERE singleton=1').fetchone()
        ensure(r is not None,'V1_AUTHORITY_MISSING')
        return dict(r)

    def audit_owned_memory(self):
        self.assert_fence()
        tables={x[0]:x[1] for x in self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
        ensure(tables.get('v1_owned_memory_authority')==CONTRACT_SCHEMA,'V1_AUTHORITY_SCHEMA_DRIFT')
        ensure(tables.get('v1_owned_memory_grant')==GRANT_SCHEMA,'V1_GRANT_SCHEMA_DRIFT')
        trig=self.db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='spk_new_v1_owned_memory_grant'").fetchone()
        ensure(trig is not None and trig[0]==GRANT_TRIGGER,'V1_MEMORY_TRIGGER_DRIFT')
        policy=self.policy()
        ensure((policy['owner'],policy['domain'],policy['pe_id'])==('C','P','PE-C-RESEARCH'),'V1_SCOPE_DRIFT')
        resource=self.audit_resource_custody()
        entries=[dict(x) for x in self.db.execute('SELECT * FROM v1_owned_memory_grant ORDER BY grant_id')]
        p_receipts=[dict(x) for x in self.db.execute('SELECT * FROM reference_provider_receipt ORDER BY grant_id')]
        ensure(len(entries)==len(p_receipts)==resource['total_consumed'],'V1_MEMORY_RECEIPT_CARDINALITY')
        count={0:0,1:0}
        for e,r in zip(entries,p_receipts):
            ensure((e['grant_id'],e['cue'],e['expected_version'],e['event_id'],e['event_digest'])==
                   (r['grant_id'],r['cue'],r['expected_version'],r['event_id'],r['event_digest']),
                   'V1_MEMORY_ORIGIN_DRIFT')
            ensure((e['owner'],e['domain'],e['mode'],e['pe_id'])==('C','P','execute','PE-C-RESEARCH') and
                   0<=e['authority_revision']<=policy['revision'],'V1_MEMORY_GRANT_SCOPE_DRIFT')
            count[e['cue']]+=1
        ensure(len(entries)<=policy['global_ceiling'] and count[0]<=policy['context0_ceiling'] and
               count[1]<=policy['context1_ceiling'],'V1_MEMORY_QUOTA_BROKEN')
        proof=read_only_contract_request(owner='C',domain='P',mode='execute',pe_id='PE-C-RESEARCH',context=0,version=0)
        native=reject_native_promotion(proof['request'],{'issuer':'NEW_VERSIONED_V1','claim':'native'})
        ensure(not native['promotion_allowed'],'V1_NATIVE_PROMOTION_UNSAFE')
        return {'new_v1_memory_grants':len(entries),'new_v1_memory_P_commits':len(entries),
                'new_v1_memory_grant_rows_sha256':digest(entries),
                'new_v1_memory_policy':{k:policy[k] for k in ('owner','domain','pe_id','mode','global_ceiling','context0_ceiling','context1_ceiling','revision')},
                'reference_provider_receipts_sha256':resource['provider_receipts_sha256'],
                'native_frozen_SPK_grants':0,'native_frozen_SPK_P_writes':0,
                'original_memory_contract_called':False,'A_sender_authenticated':False,
                'native_promotion_denied':not native['promotion_allowed']}

    def transition_authority(self,*,expected_revision,mode=None,global_ceiling=None,context_ceiling=None):
        ensure(type(expected_revision) is int and expected_revision>=0,'V1_PROFILE_REVISION_INVALID')
        r=self.policy();ensure(r['revision']==expected_revision,'V1_PROFILE_STALE_REVISION')
        m=r['mode'] if mode is None else mode
        g=r['global_ceiling'] if global_ceiling is None else global_ceiling
        c=r['context0_ceiling'] if context_ceiling is None else context_ceiling
        ensure(m in ('execute','verify') and type(g) is int and type(c) is int and
               0<=g<=48 and 0<=c<=48,'V1_PROFILE_INVALID')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            used=self.db.execute('SELECT COUNT(*) FROM v1_owned_memory_grant').fetchone()[0]
            n0=self.db.execute('SELECT COUNT(*) FROM v1_owned_memory_grant WHERE cue=0').fetchone()[0]
            n1=used-n0
            ensure(used<=g and n0<=c and n1<=c,'V1_PROFILE_RETROACTIVE_OVERDRAW')
            pending=self.db.execute("SELECT COUNT(*) FROM event WHERE status='QUEUED'").fetchone()[0]
            ensure(not pending or (m=='execute' and g>=r['global_ceiling'] and c>=r['context0_ceiling']),
                   'V1_PENDING_PROFILE_DOWNGRADE_DENIED')
            self.db.execute('UPDATE v1_owned_memory_authority SET mode=?,global_ceiling=?,context0_ceiling=?,context1_ceiling=?,revision=revision+1 WHERE singleton=1 AND revision=?',
                            (m,g,c,c,expected_revision))
            ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'V1_PROFILE_CAS_REJECT')
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK');raise
        return self.audit_owned_memory()

    def reopen(self):
        self.close()
        self.__init__(self.path,learn=self.learn,budget=self.budget,max_inflight=self.max_inflight,create=False)
