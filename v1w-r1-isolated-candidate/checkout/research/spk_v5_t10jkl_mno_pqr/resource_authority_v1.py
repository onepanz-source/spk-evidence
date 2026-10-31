"""T10JKL/MNO/PQR: bounded C/P reference resource admission.

A new host-owned V1 reference, NOT a native Memory Contract implementation.
This module adds an independent resource ceiling on actual P-store commits,
not an after-the-fact ledger count. Profile mutations by a privileged host
remain outside the trust boundary. Untrusted A verdicts are not authenticated.
"""
from __future__ import annotations
import sqlite3
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, digest, Reject
from research.spk_v5_t10abc_def_ghi.provider_v1 import ProviderFencedTickEngine, native_gate_must_deny
from research.spk_v5_t9stu_vwx_yza.p_target_admission_port_v1 import target_for
from research.spk_v5_t9stu_vwx_yza.fenced_p_store_v1 import TRIGGERS
from research.spk_v5_t10abc_def_ghi.provider_v1 import PROVIDER_TRIGGERS

SCHEMA='spk-v1-reference-bounded-P-resource-provider/research-v1'
RESOURCE_SQL="""CREATE TABLE reference_p_resource (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  owner TEXT NOT NULL CHECK(owner='C'), domain TEXT NOT NULL CHECK(domain='P'),
  pe_id TEXT NOT NULL CHECK(pe_id='PE-C-RESEARCH'),
  mode TEXT NOT NULL CHECK(mode IN ('execute','verify')),
  grant_ceiling INTEGER NOT NULL CHECK(grant_ceiling BETWEEN 0 AND 48),
  cue0_ceiling INTEGER NOT NULL CHECK(cue0_ceiling BETWEEN 0 AND 48),
  cue1_ceiling INTEGER NOT NULL CHECK(cue1_ceiling BETWEEN 0 AND 48),
  revision INTEGER NOT NULL CHECK(revision >= 0)
)"""
RESOURCE_GUARD="""CREATE TRIGGER spk_ref_v3_resource_guard BEFORE UPDATE ON p BEGIN
 SELECT RAISE(ABORT,'P_REFERENCE_RESOURCE_DENIED') WHERE
  (SELECT COUNT(*) FROM reference_p_resource WHERE singleton=1
    AND owner='C' AND domain='P' AND pe_id='PE-C-RESEARCH' AND mode='execute') != 1
  OR (SELECT COUNT(*) FROM p_grant) > (SELECT grant_ceiling FROM reference_p_resource WHERE singleton=1)
  OR (SELECT COUNT(*) FROM p_grant WHERE cue=OLD.cue) > (
    SELECT CASE OLD.cue WHEN 0 THEN cue0_ceiling ELSE cue1_ceiling END
      FROM reference_p_resource WHERE singleton=1);
 END"""

class ResourceAdmittedEngine(ProviderFencedTickEngine):
    """A V1 resource manifest gates the original T10 P-store tick transaction."""
    def __init__(self,path,*,learn=True,budget=12,max_inflight=3,create=True,
                 grant_ceiling=8,context_ceiling=4):
        # The base T10 check is deliberately preserved, not overridden.
        self._resource_constructing=create
        super().__init__(path,learn=learn,budget=budget,max_inflight=max_inflight,create=create)
        self._resource_constructing=False
        if create:
            ensure(type(grant_ceiling) is int and 0<=grant_ceiling<=48,'RESOURCE_GLOBAL_DOMAIN')
            ensure(type(context_ceiling) is int and 0<=context_ceiling<=48,'RESOURCE_CONTEXT_DOMAIN')
            self.db.execute(RESOURCE_SQL)
            self.db.execute('INSERT INTO reference_p_resource VALUES(1,?,?,?,?,?,?,?,0)',
                ('C','P','PE-C-RESEARCH','execute',grant_ceiling,context_ceiling,context_ceiling))
            self.db.execute(RESOURCE_GUARD)
        try:self.audit_resource_contract()
        except BaseException:self.db.close();raise

    def assert_fence(self):
        # The T10 parent assumes exactly five triggers. Preserve it without edits;
        # this subclass recognizes its own additional resource guard by name.
        rows=self.db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='p'")
        found={r['name']:r['sql'] for r in rows}
        expected=dict(TRIGGERS)
        if not getattr(self,'_t10_initializing',False):
            expected.update(PROVIDER_TRIGGERS)
            if not getattr(self,'_resource_constructing',False):
                expected['spk_ref_v3_resource_guard']=RESOURCE_GUARD
        ensure(set(found)==set(expected),'RESOURCE_FENCE_SET_DRIFT')
        for name,statement in expected.items():
            if name=='spk_ref_v3_resource_guard':
                ensure(found[name]==statement,'RESOURCE_FENCE_SQL_DRIFT_'+name)
                continue
            d=sqlite3.connect(':memory:')
            try:
                d.execute('CREATE TABLE p(cue,choice,version,budget)')
                d.execute(statement)
                canonical=d.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
                ensure(found[name]==canonical,'RESOURCE_FENCE_SQL_DRIFT_'+name)
            finally:d.close()

    def resource(self):
        r=self.db.execute('SELECT * FROM reference_p_resource WHERE singleton=1').fetchone()
        ensure(r is not None,'REFERENCE_RESOURCE_MISSING')
        return dict(r)

    def audit_resource_contract(self):
        # Original T9 and T10 fences are checked by base; this is an additive gate.
        self.assert_fence();self.assert_provider()
        sql=self.db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='spk_ref_v3_resource_guard'").fetchone()
        ensure(sql is not None and sql[0]==RESOURCE_GUARD,'REFERENCE_RESOURCE_GUARD_DRIFT')
        table=self.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reference_p_resource'").fetchone()
        ensure(table is not None and table[0]==RESOURCE_SQL,'REFERENCE_RESOURCE_SCHEMA_DRIFT')
        r=self.resource()
        ensure(r['owner']=='C' and r['domain']=='P' and r['pe_id']=='PE-C-RESEARCH'
               and r['mode'] in ('execute','verify') and r['revision']>=0,'REFERENCE_RESOURCE_SCOPE_DRIFT')
        grants=list(self.db.execute('SELECT cue,expected_version FROM p_grant ORDER BY id'))
        n0=sum(x['cue']==0 for x in grants);n1=sum(x['cue']==1 for x in grants)
        ensure(len(grants)<=r['grant_ceiling'] and n0<=r['cue0_ceiling'] and n1<=r['cue1_ceiling'],
               'REFERENCE_RESOURCE_OVERRUN')
        expected_p=list(self.db.execute('SELECT cue,version FROM p ORDER BY cue'))
        ensure({x['cue']:x['version'] for x in expected_p}=={0:n0,1:n1},'REFERENCE_RESOURCE_P_CAS_DRIFT')
        return {'manifest':{k:r[k] for k in ('owner','domain','pe_id','mode','grant_ceiling','cue0_ceiling','cue1_ceiling','revision')},
                'total_consumed':len(grants),'per_context_consumed':{'0':n0,'1':n1},
                'native_SPK_memory_grants':0,
                'reference_resource_digest':digest({'manifest':r,'grants':[tuple(x) for x in grants]})}

    def transition_profile(self,*,expected_revision,mode=None,grant_ceiling=None,context_ceiling=None):
        """Reference-only administrative CAS. No native resource/profile authority."""
        ensure(type(expected_revision) is int and expected_revision>=0,'RESOURCE_REVISION_DOMAIN')
        r=self.resource()
        ensure(r['revision']==expected_revision,'RESOURCE_STALE_REVISION')
        m=r['mode'] if mode is None else mode
        g=r['grant_ceiling'] if grant_ceiling is None else grant_ceiling
        c=r['cue0_ceiling'] if context_ceiling is None else context_ceiling
        ensure(m in ('verify','execute') and type(g) is int and type(c) is int and
               0<=g<=48 and 0<=c<=48,'RESOURCE_PROFILE_INVALID')
        # Prevent an administrative reconfiguration from retroactively invalidating used credits.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            total=self.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0]
            count0=self.db.execute('SELECT COUNT(*) FROM p_grant WHERE cue=0').fetchone()[0]
            count1=total-count0
            ensure(total<=g and count0<=c and count1<=c,'RESOURCE_PROFILE_RETROACTIVE_OVERDRAW')
            ensure(self.db.execute("SELECT COUNT(*) FROM event WHERE status='QUEUED'").fetchone()[0] == 0 or
                   (m=='execute' and g>=r['grant_ceiling'] and c>=r['cue0_ceiling']),
                   'RESOURCE_PENDING_PROFILE_DOWNGRADE_DENIED')
            self.db.execute('UPDATE reference_p_resource SET mode=?,grant_ceiling=?,cue0_ceiling=?,cue1_ceiling=?,revision=revision+1 WHERE singleton=1 AND revision=?',
                            (m,g,c,c,expected_revision))
            ensure(self.db.execute('SELECT changes()').fetchone()[0]==1,'RESOURCE_PROFILE_CAS_FAILED')
            self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
        return self.audit_resource_contract()

    def audit_resource_custody(self):
        out=self.audit_resource_contract();p=self.audit_provider()
        ensure(out['total_consumed']==p['provider_v1_commits'],'RESOURCE_PROVIDER_LEDGER_DRIFT')
        out['provider_receipts_sha256']=p['provider_receipts_sha256']
        out['native_SPK_admission']='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'
        return out

    def reopen(self):
        self.close()
        # The manifest persists and is never reconstructed with caller-provided limits.
        self.__init__(self.path,learn=self.learn,budget=self.budget,max_inflight=self.max_inflight,create=False)

def native_seam_denial():
    return native_gate_must_deny(target_for(cue=0,version=0))
