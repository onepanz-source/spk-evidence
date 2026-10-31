"""SPK V5/T13: original A1d execution-memory access GATES research P commits.

Runs authentic frozen A1d→projection→authorization→service on the matching
(choice, goal) episode before a host-owned V1 C-receipt UPDATE P is allowed.
Original access is NOT an original grant to learn. All feedback is still
synthetic, and the privileged host can rewrite the SQLite store.

The optional test callback exists only for controlled negative unit tests.
Production and the release gate reject test mode entirely.
"""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import ensure, digest, Reject
from research.spk_v5_t11_macro_memory_v1.memory_authority_v1 import OwnedMemoryV1

WITNESS_SCHEMA="""CREATE TABLE original_access_witness (
  grant_id INTEGER PRIMARY KEY,
  cue INTEGER NOT NULL CHECK(cue IN (0,1)),
  expected_version INTEGER NOT NULL CHECK(expected_version>=0),
  event_id INTEGER NOT NULL UNIQUE,
  event_digest TEXT NOT NULL,
  episode_id INTEGER NOT NULL UNIQUE,
  choice INTEGER NOT NULL CHECK(choice IN (11,12)),
  goal INTEGER NOT NULL CHECK(goal IN (11,12)),
  access_proof_digest TEXT NOT NULL,
  proof_kind TEXT NOT NULL CHECK(proof_kind IN ('ORIGINAL_A1D_EXECUTION_ACCESS','TEST_ONLY')),
  UNIQUE(cue,expected_version)
)"""
WITNESS_TRIGGER="""CREATE TRIGGER spk_t13_original_access_witness
AFTER INSERT ON reference_provider_receipt BEGIN
 INSERT INTO original_access_witness
 SELECT NEW.grant_id,NEW.cue,NEW.expected_version,NEW.event_id,
  NEW.event_digest, ep.id, ep.choice, ep.goal,
  spk_t13_access_proof(NEW.grant_id,NEW.cue,NEW.expected_version,
                       NEW.event_id,NEW.event_digest),
  (SELECT proof_kind FROM original_access_policy WHERE singleton=1)
 FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
 WHERE g.id=NEW.grant_id AND g.cue=NEW.cue
   AND g.expected_version=NEW.expected_version AND ep.status='RUNNING';
 SELECT RAISE(ABORT,'T13_ORIGINAL_ACCESS_PROOF_MISSING')
 WHERE NOT EXISTS(SELECT 1 FROM original_access_witness
                  WHERE grant_id=NEW.grant_id AND event_id=NEW.event_id);
END"""
POLICY_SCHEMA="""CREATE TABLE original_access_policy (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 proof_kind TEXT NOT NULL CHECK(proof_kind IN ('ORIGINAL_A1D_EXECUTION_ACCESS','TEST_ONLY'))
)"""
ORIGINAL_A1D_SHA='efe461bdaf1c6dfe902407fef6f4dfe6ec31cf1e771fd66c2a075eedf2eeb8c8'


def original_execution_access_for_choice(root, choice:int, goal:int):
    """Actually call original T12 admitted A1d source chain; never invent an access grant.

    T12 already passed on fwork for each of the 4 choice-goal combinations.
    Require success of *all* stages of the matching case, not a different case.
    """
    from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import original_native_execution_probe,sha
    root=Path(root).resolve(strict=True)
    ensure(sha(root/'spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA,'T13_A1D_SOURCE_DRIFT')
    proof=original_native_execution_probe(root)
    ensure(proof['counts']['completed_original_memory_chains']==4 and
           proof['counts']['native_execution_memory_services']==4 and
           proof['counts']['native_execution_access_authorizations']==4,
           'T13_ORIGINAL_MEMORY_CHAIN_INCOMPLETE')
    matching=[r for r in proof['outcomes'] if (r['choice'],r['goal'])==(choice,goal)]
    ensure(len(matching)==1 and matching[0].get('original_memory_access_executed') is True,
           'T13_ORIGINAL_MEMORY_ACCESS_NOT_AUTHORIZED_FOR_DECISION')
    m=matching[0];origin=m['A1d_provenance']
    ensure(origin['producer']=='spk_architecture_v1.pe_fault_v1d.execute_failstop_v1d'
           and origin['source_sha256']==ORIGINAL_A1D_SHA
           and origin['status']=='CLOSED' and m['projection_status']=='CLOSED'
           and m['projection_schema']=='spk-architecture-memory-projection/v1a',
           'T13_ORIGINAL_EXECUTION_PROVENANCE_INVALID')
    return {'kind':'ORIGINAL_A1D_EXECUTION_ACCESS','choice':choice,'goal':goal,
            'source_sha256':ORIGINAL_A1D_SHA,'producer':origin['producer'],
            'projection_schema':m['projection_schema'],
            'catalog_digest':proof['catalog']['catalog_sha256'],
            'processed_events':origin['processed_events'],
            'processed_batches':origin['processed_batches'],
            'execution_access_only':True,'original_learning_P_grants':0}


class OriginalAccessGatedV1(OwnedMemoryV1):
    """Add a proven original-execution-access prerequisite to reference P commits.

    The SQL transaction that invokes the provider also persists the matching
    evidence digest. No original SPK P learning is claimed or granted.
    """
    def __init__(self,path,*,root=None,learn=True,budget=12,max_inflight=3,
                 create=True,global_ceiling=8,context_ceiling=4,
                 test_witness=None,test_only=False):
        ensure((test_witness is None and not test_only) or
               (test_only is True and callable(test_witness)),
               'T13_INVALID_TEST_CONFIGURATION')
        self.source_root=Path(root if root is not None else '.').resolve()
        self.test_only=test_only
        self.test_witness=test_witness
        self._pending_original_proof=None
        self.last_original_denial=None
        super().__init__(path,learn=learn,budget=budget,max_inflight=max_inflight,
                         create=create,global_ceiling=global_ceiling,
                         context_ceiling=context_ceiling)
        self.db.create_function('spk_t13_access_proof',5,self._proof_for_sql)
        if create:
            self.db.execute(POLICY_SCHEMA)
            self.db.execute('INSERT INTO original_access_policy VALUES(1,?)',
                            ('TEST_ONLY' if test_only else 'ORIGINAL_A1D_EXECUTION_ACCESS',))
            self.db.execute(WITNESS_SCHEMA)
            self.db.execute(WITNESS_TRIGGER)
        self.audit_original_access()

    def reopen(self):
        self.close()
        self.__init__(self.path,root=self.source_root,learn=self.learn,budget=self.budget,
                      max_inflight=self.max_inflight,create=False,
                      test_witness=self.test_witness,test_only=self.test_only)

    def _proof_for_sql(self,grant_id,cue,version,event_id,event_digest):
        p=self._pending_original_proof
        if p is None or (grant_id,cue,version,event_id,event_digest)!=p['binding']:
            return None
        return p['proof_digest']

    def _authorize(self,cue,old_choice,version,budget,new_choice,new_version,new_budget):
        self._pending_original_proof=None
        if super()._authorize(cue,old_choice,version,budget,new_choice,new_version,new_budget)!=1:
            return 0
        # Source bound to the very C semantic receipt triggering this P write.
        rows=self.db.execute('''SELECT g.id AS grant_id,ep.id AS ep_id,ep.goal,
                        ev.id AS event_id,ev.digest AS event_digest
              FROM p_grant g JOIN episode ep ON ep.id=g.episode_id
              JOIN event ev ON ev.episode_id=ep.id AND ev.kind='SEM_B_C' AND ev.status='DONE'
              WHERE g.cue=? AND g.expected_version=? AND ep.choice=?
                AND ep.status='RUNNING' ''',(cue,version,old_choice)).fetchall()
        if len(rows)!=1:return 0
        r=rows[0]
        try:
            w=(self.test_witness(old_choice,r['goal']) if self.test_only else
               original_execution_access_for_choice(self.source_root,old_choice,r['goal']))
            ensure(isinstance(w,dict) and
                   w.get('kind')==('TEST_ONLY' if self.test_only else 'ORIGINAL_A1D_EXECUTION_ACCESS')
                   and (w['choice'],w['goal'])==(old_choice,r['goal']) and
                   w.get('original_learning_P_grants')==0,'T13_UNMATCHED_ORIGINAL_ACCESS_WITNESS')
            bind=(r['grant_id'],cue,version,r['event_id'],r['event_digest'])
            self._pending_original_proof={'binding':bind,'proof_digest':digest({'binding':bind,'witness':w})}
            self.last_original_denial=None
            return 1
        except (ValueError,TypeError,KeyError,AttributeError,RuntimeError,OSError) as exc:
            self.last_original_denial=type(exc).__name__+':'+str(exc)[:300]
            return 0

    def audit_original_access(self):
        r=self.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='original_access_witness'").fetchone()
        ensure(r is not None and r[0]==WITNESS_SCHEMA,'T13_WITNESS_SCHEMA_DRIFT')
        r=self.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='original_access_policy'").fetchone()
        ensure(r is not None and r[0]==POLICY_SCHEMA,'T13_POLICY_SCHEMA_DRIFT')
        r=self.db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='spk_t13_original_access_witness'").fetchone()
        ensure(r is not None and r[0]==WITNESS_TRIGGER,'T13_WITNESS_TRIGGER_DRIFT')
        mode=self.db.execute('SELECT proof_kind FROM original_access_policy WHERE singleton=1').fetchone()
        ensure(mode is not None and mode[0]==('TEST_ONLY' if self.test_only else 'ORIGINAL_A1D_EXECUTION_ACCESS'),
               'T13_ORIGINAL_MODE_MISMATCH')
        rows=[dict(x) for x in self.db.execute('SELECT * FROM original_access_witness ORDER BY grant_id')]
        grants=[dict(x) for x in self.db.execute('SELECT * FROM p_grant ORDER BY id')]
        receipts=[dict(x) for x in self.db.execute('SELECT * FROM reference_provider_receipt ORDER BY grant_id')]
        ensure(len(rows)==len(grants)==len(receipts),'T13_ORIGINAL_WITNESS_GRANT_COUNT_DRIFT')
        for w,g,p in zip(rows,grants,receipts):
            ep=self.db.execute('SELECT * FROM episode WHERE id=?',(g['episode_id'],)).fetchone()
            ensure(ep is not None and
                   (w['grant_id'],w['cue'],w['expected_version'],w['event_id'],w['event_digest'],w['episode_id'],w['choice'],w['goal'])==
                   (g['id'],g['cue'],g['expected_version'],p['event_id'],p['event_digest'],g['episode_id'],ep['choice'],ep['goal']) and
                   w['proof_kind']==mode[0] and len(w['access_proof_digest'])==64,
                   'T13_ORIGINAL_ACCESS_LINEAGE_DRIFT')
        return {'original_access_witnesses':len(rows) if not self.test_only else 0,
                'test_only_witnesses':len(rows) if self.test_only else 0,
                'original_access_witness_rows_sha256':digest(rows),
                'original_A1d_executions_for_witnesses':len(rows)*4 if not self.test_only else 0,
                'same_tick_transaction':True,'original_learning_P_grants':0,
                'new_runtime_v1_P_grants':len(grants),
                'host_can_forge':True,'source_authenticated':False,
                'witness_kind':mode[0]}
