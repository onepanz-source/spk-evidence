"""T16 direct integration and adversarial tests; no original-native claims."""
import json, sqlite3, tempfile, unittest
from pathlib import Path
from research.spk_v5_t16_macro_runtime.staged_runtime_v1 import StagedCell,STAGES
from research.spk_v5_t16_macro_runtime.macro_gate import scenario
from research.spk_v5_t15_macro_causal_learning.prospective_gate import one_cell

class StageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'run.sqlite'
 def cell(self,**k):
  c=StagedCell(self.path,setpoint=k.pop('setpoint',4),**k)
  self.addCleanup(c.close);return c
 def advance(self,c,num):
  return [c.dispatch() for _ in range(num)]
 def test_five_distinct_transactions(self):
  c=self.cell();ep=c.submit(6)
  seen=self.advance(c,5)
  self.assertEqual([x['kind'] for x in seen],list(STAGES))
  self.assertEqual(len({x['pending_id'] for x in seen}),5)
  self.assertEqual(c.result(ep)['credit'],1)
  self.assertEqual(c.audit()['P_grants'],1)
 def test_cannot_supply_host_verdict(self):
  c=self.cell()
  with self.assertRaises(TypeError):c.submit(6,verdict='WORSENED')
 def test_resume_between_every_event(self):
  c=self.cell();ep=c.submit(6)
  for expected in STAGES:
   self.assertEqual(c.dispatch()['kind'],expected)
   c.audit();c.reopen()
  self.assertEqual(c.result(ep)['credit'],1);self.assertIsNone(c.dispatch())
 def test_evaluation_freezes_P(self):
  c=self.cell();c.trial(6)
  previous=c.state()
  for t in range(16):c.trial(t,learning=False)
  self.assertEqual(c.state(),previous)
  self.assertEqual(c.audit()['settled'],17)
 def test_per_episode_A_verdict_generated(self):
  c=self.cell();ep=c.submit(6)
  self.advance(c,3)
  self.assertEqual(c.db.execute('SELECT verdict FROM episode').fetchone()[0],'WORSENED')
  self.assertIn('PE_digest',json.loads(c.db.execute("SELECT body FROM event WHERE kind='A_PE'").fetchone()[0]))
  c.drain();c.audit()
 def test_missing_feedback_denied(self):
  c=self.cell();r=c.trial(6,feedback='missing')
  self.assertEqual(r['reason'],'MISSING');self.assertEqual(c.state()['version'],0)
  c.audit()
 def test_altered_feedback_denied(self):
  c=self.cell();r=c.trial(6,feedback='altered')
  self.assertEqual(r['reason'],'B_LINEAGE_OR_VERDICT_MISMATCH');c.audit()
 def test_wrong_lineage_denied(self):
  c=self.cell();r=c.trial(6,feedback='wrong_lineage')
  self.assertEqual(r['credit'],0);c.audit()
 def test_negative_A_does_not_commit_when_not_learning(self):
  c=self.cell();r=c.trial(6,learning=False)
  self.assertEqual(r['credit'],0);self.assertEqual(c.state()['theta'],12)
 def test_good_A_leaves_P_alone(self):
  c=self.cell();r=c.trial(0)
  self.assertEqual(r['verdict'],'IMPROVED');self.assertEqual(r['credit'],0)
 def test_direct_P_update_denied(self):
  c=self.cell()
  with self.assertRaises(sqlite3.IntegrityError):c.db.execute('UPDATE p SET theta=3,version=1,commits=1')
  self.assertEqual(c.state()['version'],0)
 def test_verify_mode_blocks_and_preserves_feedback(self):
  c=self.cell();c.set_policy(expected_revision=0,mode='verify')
  ep=c.submit(6);c.drain()
  self.assertEqual(c.db.execute("SELECT count(*) FROM pending WHERE status='QUEUED'").fetchone()[0],1)
  self.assertEqual(c.db.execute('SELECT count(*) FROM p_grant').fetchone()[0],0)
  self.assertEqual(c.db.execute('SELECT stage FROM episode').fetchone()[0],'C_CREDIT')
  c.reopen();c.set_policy(expected_revision=1,mode='execute');c.drain()
  self.assertEqual(c.result(ep)['credit'],1);c.audit()
 def test_budget_exhaustion_block_and_resume(self):
  c=self.cell(ceiling=0)
  ep=c.submit(6);c.drain();self.assertEqual(c.state()['version'],0)
  self.assertEqual(c.audit()['pending'],1)
  c.reopen();c.set_policy(expected_revision=0,ceiling=1);c.drain()
  self.assertEqual(c.result(ep)['credit'],1);self.assertEqual(c.audit()['pending'],0)
 def test_budget_retroactive_reduction_denied(self):
  c=self.cell();c.trial(6)
  with self.assertRaises(ValueError):c.set_policy(expected_revision=0,ceiling=0)
 def test_revision_CAS(self):
  c=self.cell();c.set_policy(expected_revision=0,ceiling=12)
  with self.assertRaises(ValueError):c.set_policy(expected_revision=0,ceiling=12)
 def test_wrong_mode(self):
  c=self.cell()
  with self.assertRaises(ValueError):c.set_policy(expected_revision=0,mode='training')
 def test_invalid_inputs(self):
  c=self.cell()
  for t in (-1,16,1.2,True):
   with self.subTest(t=t),self.assertRaises(ValueError):c.submit(t)
 def test_capacity_enforced(self):
  c=self.cell(max_active=2)
  c.submit(6);c.submit(7)
  with self.assertRaises(ValueError):c.submit(8)
 def test_concurrent_stale_P_credit(self):
  c=self.cell(max_active=2);e0=c.submit(6);e1=c.submit(7)
  c.drain();self.assertEqual(c.result(e0)['credit'],1)
  self.assertEqual(c.result(e1)['credit'],0)
  self.assertEqual(c.result(e1)['reason'],'STALE_P_VERSION')
  self.assertEqual(c.state()['version'],1);c.audit()
 def test_recovery_concurrent(self):
  c=self.cell(max_active=2);c.submit(6);c.submit(7)
  self.advance(c,4);c.reopen();c.drain()
  self.assertEqual(c.audit()['settled'],2)
 def test_no_replay_grant(self):
  c=self.cell();c.trial(6);before=c.audit()
  c.reopen();self.assertIsNone(c.dispatch());self.assertEqual(c.audit(),before)
 def test_A_digest_tampering_detected(self):
  c=self.cell();c.submit(6);self.advance(c,3)
  c.db.execute("UPDATE episode SET A_digest='BAD' WHERE id=0")
  with self.assertRaises(ValueError):c.audit()
 def test_event_digest_tampering_detected(self):
  c=self.cell();c.trial(6)
  c.db.execute("UPDATE event SET digest='BAD' WHERE id=1")
  with self.assertRaises(ValueError):c.audit()
 def test_resealed_A_message_rejected_by_PE(self):
  c=self.cell();c.submit(6);self.advance(c,4)
  a=json.loads(c.db.execute('SELECT A_json FROM episode').fetchone()[0]);a['verdict']='IMPROVED'
  c.db.execute('UPDATE episode SET A_json=?',(json.dumps(a,sort_keys=True,separators=(',',':')),))
  with self.assertRaises(ValueError):c.dispatch()
  self.assertEqual(c.state()['version'],0)
  self.assertEqual(c.db.execute("SELECT count(*) FROM pending WHERE status='QUEUED'").fetchone()[0],1)
 def test_P_tampering_detected(self):
  c=self.cell();c.trial(6)
  c.db.execute('DROP TRIGGER p_update_guard')
  c.db.execute('UPDATE p SET theta=3')
  with self.assertRaises(ValueError):c.audit()
 def test_P_fence_trigger_removed_detected(self):
  c=self.cell();c.db.execute('DROP TRIGGER p_update_guard')
  with self.assertRaises(ValueError):c.audit()
 def test_duplicate_credit_row_denied(self):
  c=self.cell();c.trial(6)
  with self.assertRaises(sqlite3.IntegrityError):
   c.db.execute('INSERT INTO p_grant SELECT * FROM p_grant')
 def test_cross_domain_P_bypass_denied(self):
  c=self.cell()
  with self.assertRaises(sqlite3.IntegrityError):c.db.execute("UPDATE policy SET owner='A'")
 def test_readonly_A_environment_cannot_submit_reward(self):
  c=self.cell();ep=c.submit(6)
  self.assertEqual(c.db.execute('SELECT verdict FROM episode').fetchone()[0],None)
 def test_config_mismatch_denied_after_restart(self):
  c=self.cell();c.close()
  with self.assertRaises(ValueError):StagedCell(self.path,setpoint=6,create=False)
 def test_no_nativism_in_audit(self):
  c=self.cell();c.trial(6);d=c.audit()
  self.assertFalse(d['original_SPK_native_BV']);self.assertFalse(d['original_SPK_native_learning'])
 def test_status_query_nonsettled_denied(self):
  c=self.cell();ep=c.submit(6)
  with self.assertRaises(ValueError):c.result(ep)
 def test_audit_partial_stages(self):
  c=self.cell();c.submit(6)
  for _ in range(4):c.audit();c.dispatch()
  c.audit()

class ParityTests(unittest.TestCase):
 def test_worlds_single_seeds(self):
  for world,seed in ((3,17),(7,29),(12,43)):
   with self.subTest(world=world,seed=seed),tempfile.TemporaryDirectory() as td:
    staged=scenario(Path(td)/'a',world,seed,'adaptive')
    original=one_cell(Path(td)/'b',world,seed,'adaptive')
    self.assertEqual(staged['eval_choices'],original['heldout_choices'])
    self.assertEqual(staged['eval_scores'],original['heldout_score'])
    self.assertEqual(staged['P_version'],original['P_version'])
 def test_all_controls_small_sample(self):
  for mode in ('frozen','no_feedback','altered','wrong_lineage'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
    v=scenario(td,5,17,mode)
    self.assertEqual(v['train_grants'],0)
    self.assertTrue(v['heldout_P_frozen'])
 def test_inverted_dynamics_is_not_solved(self):
  with tempfile.TemporaryDirectory() as td:
   x=scenario(td,4,17,'adaptive',True)
   self.assertLess(x['eval_hits'],x['eval_cases'])
 def test_research_memory_owned_not_A1d(self):
  from research.spk_v5_t16_macro_runtime.macro_gate import SCHEMA
  self.assertIn('research-v0',SCHEMA)

if __name__=='__main__':unittest.main()
