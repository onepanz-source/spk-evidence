"""Incremental T6STU/VWX/YZA actual SQLite/stateful-PE tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import LoopBoundary,digest
from research.spk_v5_t6jkl_mno_pqr.async_multi_v0 import make_votes,reseal,scenario
from research.spk_v5_t6stu_vwx_yza.owned_state_v0 import OwnedCState
from research.spk_v5_t6stu_vwx_yza.stateful_multi_v0 import scenario_owned

class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='spk-t6owned-unit-')
        self.path=Path(self.tmp.name)/'P.sqlite'
        self.p=OwnedCState(self.path)
    def tearDown(self):
        self.p.close();self.tmp.cleanup()
    def votes(self,cue=0,tick=0,phase=0):
        d=self.p.choose(cue,tick)
        return d,make_votes(d,phase)
    def test_schema_custody(self):
        self.assertEqual(self.p.meta('owner'),'C')
        self.assertEqual(self.p.meta('domain'),'P')
        self.assertEqual(self.p.meta('mode'),'execute')
        self.assertEqual(self.p.audit()['ledger_events'],1)
    def test_reinitialize_disallowed(self):
        with self.assertRaisesRegex(LoopBoundary,'REINITIALIZATION'):
            q=OwnedCState(self.path)
    def test_wrong_state_config_rejected(self):
        with self.assertRaisesRegex(LoopBoundary,'STATE_CONFIG_DRIFT'):
            q=OwnedCState(self.path,create=False,budget=7)
    def test_recovery_after_issued_decision(self):
        d,v=self.votes();self.p.reopen()
        self.assertEqual(self.p.submit(v[0],5),'RECEIVED')
        self.p.reopen()
        self.assertEqual(self.p.submit(v[1],6),'UPDATED')
        self.assertEqual(self.p.table[0],11)
        self.assertEqual(self.p.audit()['updates'],1)
    def test_no_duplicate_after_restart(self):
        d,v=self.votes();self.p.submit(v[0],5);self.p.submit(v[1],6)
        self.p.reopen()
        with self.assertRaisesRegex(LoopBoundary,'NO_PENDING_OR_REPLAY'):
            self.p.submit(v[1],6)
        self.assertEqual(self.p.audit()['updates'],1)
    def test_committed_vote_survives_reopen(self):
        d,v=self.votes();self.p.submit(v[0],5);self.p.reopen()
        self.assertEqual(self.p.accepted_votes,1)
        self.assertEqual(self.p.submit(v[1],6),'UPDATED')
    def test_atomic_rollback_of_manual_transaction(self):
        d,v=self.votes()
        before=self.p.audit()['ledger_tip']
        self.p.db.execute('BEGIN IMMEDIATE')
        self.p.db.execute('INSERT INTO votes VALUES (?,?,?,?)',(d['id'],'A','WORSENED',v[0]['vote_sha256']))
        self.p.db.execute('ROLLBACK')
        self.p.reopen()
        self.assertEqual(self.p.audit()['ledger_tip'],before)
        self.assertEqual(self.p.accepted_votes,0)
        self.assertEqual(self.p.submit(v[0],5),'RECEIVED')
    def test_second_connection_reopen(self):
        d,v=self.votes();self.p.submit(v[0],5)
        q=OwnedCState(self.path,create=False)
        try:self.assertEqual(q.submit(v[1],6),'UPDATED')
        finally:q.close()
        self.assertEqual(self.p.table[0],11)
        self.assertEqual(self.p.audit()['updates'],1)
    def test_wrong_vote_rejected_without_mutation(self):
        d,v=self.votes();before=self.p.audit()['ledger_tip']
        f=copy.deepcopy(v[0]);f['relay_sha256']='0'*64
        with self.assertRaisesRegex(LoopBoundary,'RELAY_DIGEST_DRIFT'):
            self.p.submit(f,5)
        self.assertEqual(self.p.audit()['ledger_tip'],before)
    def test_wrong_policy_version_after_other_commit(self):
        d0,v0=self.votes();d1,v1=self.votes()
        self.p.submit(v0[0],5);self.p.submit(v0[1],6)
        with self.assertRaisesRegex(LoopBoundary,'OBSOLETE_POLICY_VERSION'):
            self.p.submit(v1[0],5)
        self.assertEqual(self.p.audit()['updates'],1)
    def test_conflict_held(self):
        d,v=self.votes(0,0,0)
        f=reseal({**v[1]['vote'],'outcome':'IMPROVED'})
        self.p.submit(v[0],5)
        self.assertEqual(self.p.submit(f,6),'CONFLICT_HELD')
        self.assertEqual(self.p.table[0],12)
    def test_budget_limited(self):
        p=self.p
        p.db.execute('UPDATE policy SET budget=0 WHERE cue=0')
        with self.assertRaisesRegex(LoopBoundary,'MATERIALIZED_POLICY_DRIFT'):p.audit()
    def test_closure_persisted(self):
        d,v=self.votes();self.assertEqual(self.p.close_batch(),1)
        self.p.reopen()
        self.assertEqual(self.p.audit()['closed'],1)
        with self.assertRaisesRegex(LoopBoundary,'NO_PENDING_OR_REPLAY'):self.p.submit(v[0],5)
    def test_ledger_tamper_detected(self):
        d,v=self.votes();self.p.db.execute("UPDATE ledger SET body='{}' WHERE seq=1")
        with self.assertRaisesRegex(LoopBoundary,'LEDGER_SEAL_DRIFT'):
            self.p.audit()
    def test_policy_mutation_detected(self):
        self.p.db.execute('UPDATE policy SET choice=11 WHERE cue=0')
        with self.assertRaisesRegex(LoopBoundary,'MATERIALIZED_POLICY_DRIFT'):
            self.p.audit()
    def test_vote_mutation_detected(self):
        d,v=self.votes();self.p.submit(v[0],5)
        self.p.db.execute("UPDATE votes SET outcome='IMPROVED' WHERE decision_id=0")
        with self.assertRaisesRegex(LoopBoundary,'MATERIALIZED_VOTE_DRIFT'):self.p.audit()
    def test_event_removal_detected_by_replay(self):
        d,v=self.votes();self.p.db.execute('DELETE FROM ledger WHERE seq=1')
        with self.assertRaisesRegex(LoopBoundary,'MATERIALIZED_DECISION_COUNT'): 
            self.p.audit()
    def test_host_impersonates_receiver(self):
        d,v=self.votes();self.p.submit(v[0],5)
        forged=reseal({**v[0]['vote'],'receiver':'D'})
        self.assertEqual(self.p.submit(forged,6),'UPDATED')
        self.assertEqual(self.p.table[0],11)
    def test_separate_process_recovery(self):
        d,v=self.votes();self.p.submit(v[0],5)
        self.p.close()
        code='''import json,sys
from research.spk_v5_t6stu_vwx_yza.owned_state_v0 import OwnedCState
p=OwnedCState(sys.argv[1],create=False)
assert p.submit(json.loads(sys.argv[2]),6)=="UPDATED"
assert p.audit()["updates"]==1
p.close()
'''
        root=Path(__file__).resolve().parents[3]
        # PYTHONPATH supplied by normal gate, inherited by child.
        subprocess.run([sys.executable,'-c',code,str(self.path),json.dumps(v[1])],check=True,cwd=root)
        self.p=OwnedCState(self.path,create=False)
        self.assertEqual(self.p.table[0],11)
    def test_no_false_claim_native(self):
        self.assertNotIn('native_learning',self.p.meta('schema'))

class ParityTests(unittest.TestCase):
    examples=[{}, {'learn':False},{'mode':'reverse'},{'mode':'jitter','seed':42},
              {'mode':'jitter','seed':42,'drop_mod':7},{'conflict_contexts':(0,)},
              {'drop_mod':1},{'budget':1}]
    def test_full_parity_matrix(self):
        for kw in self.examples:
            with self.subTest(kw=kw):
                expected=scenario(**kw);got=scenario_owned(**kw)
                for k,v in expected.items():self.assertEqual(got[k],v,k)
                self.assertEqual(got['audit']['decisions'],expected['episodes'])
                self.assertEqual(got['audit']['updates'],expected['updates'])
    def test_restart_after_every_batch_parity(self):
        for kw in self.examples:
            with self.subTest(kw=kw):
                expected=scenario(**kw);got=scenario_owned(**kw,reopen_each_batch=True)
                for k,v in expected.items():self.assertEqual(got[k],v,k)
    def test_restarted_runs_deterministic_except_journal_tip(self):
        a=scenario_owned(reopen_each_batch=True)
        b=scenario_owned(reopen_each_batch=True)
        self.assertEqual(a,b)
    def test_alternating_goals_and_8_update_budget(self):
        x=scenario_owned()
        self.assertEqual((x['joint_successes'],x['updates'],x['stale_rejections']),(80,8,8))
        self.assertEqual(x['audit']['state_domain'],'P')
    def test_no_feedback_no_adaptation(self):
        x=scenario_owned(drop_mod=1)
        self.assertEqual((x['joint_successes'],x['updates']),(48,0))
    def test_conflicts_not_promoted(self):
        x=scenario_owned(conflict_contexts=(0,))
        self.assertEqual((x['joint_successes'],x['updates'],x['conflicts']),(40,4,48))
    def test_underbudget_worse_than_fixed(self):
        x=scenario_owned(budget=1)
        self.assertEqual((x['joint_successes'],x['updates']),(44,2))
        self.assertLess(x['joint_successes'],scenario(learn=False)['joint_successes'])

if __name__=='__main__':unittest.main()
