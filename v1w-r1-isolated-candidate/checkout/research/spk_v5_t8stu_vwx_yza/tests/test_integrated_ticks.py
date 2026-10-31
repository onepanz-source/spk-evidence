from __future__ import annotations
import tempfile,unittest,sqlite3,json
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t8stu_vwx_yza.tick_engine_v1 import TickEngine,Reject,pe_step
from research.spk_v5_t8stu_vwx_yza.cumulative_tick_gate import (
    scenario,crash_resume_witness,delay_witness,host_control_witness)

class TickTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'research.sqlite'
        self.state=TickEngine(self.path)
    def tearDown(self):
        self.state.close();self.tmp.cleanup()
    def issue(self,cue=0,goal=11,**kw):return self.state.submit(cue,goal,**kw)
    def test_pe_code_C(self):self.assertEqual(pe_step('C',12,11,10,[1])['emits'],[12])
    def test_pe_code_B11(self):self.assertEqual(pe_step('B',11,11,11,[1])['emits'],[13])
    def test_pe_code_B12(self):self.assertEqual(pe_step('B',12,11,11,[2])['emits'],[14])
    def test_pe_code_A_negative(self):self.assertEqual(pe_step('A',12,11,12,[4])['emits'],[22,7])
    def test_pe_code_A_positive(self):self.assertEqual(pe_step('A',11,11,12,[3])['emits'],[21,7])
    def test_one_tick_C(self):
        self.issue();self.assertEqual(self.state.step()['kind'],'PE_C')
        self.assertEqual(self.state.audit()['reference_v1_tick_grants'],0)
    def test_one_tick_B(self):
        self.issue();self.state.step();self.assertEqual(self.state.step()['kind'],'PE_B')
    def test_one_tick_A(self):
        self.issue();[self.state.step() for _ in range(2)]
        self.assertEqual(self.state.step()['kind'],'PE_A')
        self.assertEqual(self.state.audit()['reference_v1_tick_grants'],0)
    def test_semantic_hops(self):
        self.issue();k=[x['kind'] for x in self.state.run()]
        self.assertEqual(k,['PE_C','PE_B','PE_A','SEM_A_B','SEM_B_C'])
    def test_tick_order(self):
        self.issue();t=[x['tick'] for x in self.state.run()]
        self.assertEqual(t,[10,11,12,13,14])
    def test_negative_grant_same_tick(self):
        self.issue();[self.state.step() for _ in range(4)]
        self.assertEqual(self.state.audit()['reference_v1_tick_grants'],0)
        self.state.step();self.assertEqual(self.state.audit()['reference_v1_tick_grants'],1)
    def test_first_policy_change(self):
        i=self.issue();self.state.run();self.assertEqual(self.state.result(i)['grant'],0)
        self.assertEqual(self.state.audit()['P_policy'][0],11)
    def test_new_emission_after_change(self):
        i=self.issue();self.state.run();j=self.issue();self.state.run()
        self.assertNotEqual(self.state.result(i)['choice'],self.state.result(j)['choice'])
    def test_positive_no_grant(self):
        i=self.issue(0,12);self.state.run();self.assertEqual(self.state.result(i)['outcome'],'IMPROVED')
        self.assertIsNone(self.state.result(i)['grant'])
    def test_disabled_learning(self):
        self.state.close();self.state=TickEngine(Path(self.tmp.name)/'control.sqlite',learn=False)
        i=self.issue();self.state.run();self.assertIsNone(self.state.result(i)['grant'])
    def test_budget_zero(self):
        self.state.close();self.state=TickEngine(Path(self.tmp.name)/'no_budget.sqlite',budget=0)
        i=self.issue();self.state.run();self.assertIsNone(self.state.result(i)['grant'])
    def test_budget_one(self):
        self.state.close();self.state=TickEngine(Path(self.tmp.name)/'budget.sqlite',budget=1)
        self.issue();self.state.run();self.issue(1,12);self.state.run()
        self.assertEqual(self.state.audit()['P_writes'],2)
        self.issue(0,12);self.state.run();self.assertEqual(self.state.audit()['P_writes'],2)
    def test_drop_forward(self):
        i=self.issue(drop_forward=True);seq=self.state.run()
        self.assertEqual([x['kind'] for x in seq],['PE_C','QUIESCE'])
        self.assertEqual(self.state.result(i)['outcome'],'ABSENT')
    def test_drop_feedback(self):
        i=self.issue(drop_feedback=True);seq=self.state.run()
        self.assertEqual([x['kind'] for x in seq],['PE_C','PE_B','PE_A','QUIESCE'])
        self.assertEqual(self.state.result(i)['outcome'],'WORSENED')
        self.assertIsNone(self.state.result(i)['grant'])
    def test_delay_accepted(self):
        i=self.issue(feedback_delay=4);seq=self.state.run();self.assertEqual(seq[-1]['tick'],18)
        self.assertEqual(self.state.result(i)['grant'],0)
    def test_delay_rejected(self):
        i=self.issue(feedback_delay=5);seq=self.state.run();self.assertEqual(seq[-1]['tick'],19)
        self.assertIsNone(self.state.result(i)['grant'])
    def test_delay_12(self):
        i=self.issue(feedback_delay=12);self.state.run();self.assertIsNone(self.state.result(i)['grant'])
    def test_bad_delay(self):
        for v in (-1,13,True,1.0):
            with self.subTest(v=v),self.assertRaises(Reject):self.issue(feedback_delay=v)
    def test_bad_domain(self):
        for cue,goal in [(2,11),(0,13),('0',11),(False,11),(0,None)]:
            with self.subTest(cue=cue,goal=goal),self.assertRaises(Reject):self.issue(cue,goal)
    def test_second_open_rejected(self):
        self.issue()
        with self.assertRaisesRegex(Reject,'ONE_EPOCH_AT_A_TIME'):self.issue()
    def test_replay_settle_rejected(self):
        self.issue();self.state.run();self.assertIsNone(self.state.step())
        self.assertEqual(self.state.audit()['P_writes'],1)
    def test_recovery_after_each_stage(self):
        for steps in range(1,6):
            with self.subTest(steps=steps):
                s=TickEngine(Path(self.tmp.name)/f'reopen{steps}.sqlite')
                s.submit(0,11)
                for _ in range(steps):s.step()
                before=s.audit();s.reopen();s.run()
                self.assertEqual(s.audit()['reference_v1_tick_grants'],1)
                self.assertEqual(s.audit()['pending_events'],0)
                self.assertIsNone(s.step());s.close()
    def test_consistent_ledger_after_restart(self):
        i=self.issue();self.state.step();a=self.state.audit();self.state.reopen()
        self.assertEqual(self.state.audit(),a)
        self.state.run();self.assertEqual(self.state.result(i)['outcome'],'WORSENED')
    def test_foreign_event_kind_rejected(self):
        self.issue();self.state.db.execute("UPDATE event SET kind='IMPOSSIBLE'")
        with self.assertRaisesRegex(Reject,'EVENT_DIGEST_DRIFT'):self.state.step()
    def test_event_payload_tamper_rejected(self):
        self.issue();self.state.db.execute("UPDATE event SET payload='{}'")
        with self.assertRaisesRegex(Reject,'EVENT_DIGEST_DRIFT'):self.state.step()
    def test_event_digest_tamper_rejected(self):
        self.issue();self.state.db.execute("UPDATE event SET digest=?",('a'*64,))
        with self.assertRaisesRegex(Reject,'EVENT_DIGEST_DRIFT'):self.state.step()
    def test_resealed_wrong_event_payload_rejected(self):
        self.issue();r=self.state.db.execute('SELECT * FROM event').fetchone()
        body={'input':[9]};h=digest({'id':r['id'],'episode':r['episode_id'],'tick':r['tick'],'kind':r['kind'],'payload':body})
        self.state.db.execute('UPDATE event SET payload=?,digest=? WHERE id=?',(json.dumps(body),h,r['id']))
        with self.assertRaisesRegex(Reject,'C_EVENT_INVALID'):self.state.step()
    def test_resealed_wrong_semantic_capsule_rejected(self):
        self.issue();[self.state.step() for _ in range(3)]
        r=self.state.db.execute("SELECT * FROM event WHERE status='QUEUED'").fetchone()
        body=json.loads(r['payload']);body['capsule']['verdict']='IMPROVED'
        h=digest({'id':r['id'],'episode':r['episode_id'],'tick':r['tick'],'kind':r['kind'],'payload':body})
        self.state.db.execute('UPDATE event SET payload=?,digest=? WHERE id=?',(json.dumps(body),h,r['id']))
        with self.assertRaisesRegex(Reject,'SEMANTIC_A_BINDING'):self.state.step()
    def test_rollback_preserves_event(self):
        self.issue();self.state.db.execute("UPDATE event SET digest=?",('b'*64,))
        with self.assertRaises(Reject):self.state.step()
        self.assertEqual(self.state.db.execute('SELECT status FROM event').fetchone()[0],'QUEUED')
    def test_ledger_tamper_detected(self):
        self.issue();self.state.run();self.state.db.execute('UPDATE ledger SET digest=? WHERE seq=0',('f'*64,))
        with self.assertRaisesRegex(Reject,'LEDGER_CHAIN_DRIFT'):self.state.audit()
    def test_P_state_tamper_detected(self):
        self.issue();self.state.run();self.state.db.execute('UPDATE p SET choice=12 WHERE cue=0')
        with self.assertRaisesRegex(Reject,'P_STATE_DRIFT'):self.state.audit()
    def test_grant_duplicate_prevented(self):
        self.issue();self.state.run()
        with self.assertRaises(sqlite3.IntegrityError):self.state.db.execute("INSERT INTO p_grant VALUES(2,0,0,0,'fake',1)")
    def test_one_new_issue_after_settle(self):
        self.issue();self.state.run();i=self.issue(1,12)
        self.assertEqual(i,1)
    def test_frozen_native_grant_absent(self):
        self.issue();self.state.run();self.assertTrue(self.state.audit()['reference_v1_tick_grants']==1)
        self.assertFalse(hasattr(self.state,'native_spk_memory_contract'))
    def test_no_oracle_in_live_tick(self):
        self.issue();self.state.run();self.assertTrue(self.state.audit()['P_writes']==1)
    def test_issued_state_is_C_owned(self):
        metadata=dict(self.state.db.execute('SELECT k,v FROM meta'))
        self.assertEqual((metadata['owner'],metadata['domain'],metadata['mode']),('C','P','execute'))
    def test_audit_closed_but_pending_ledger(self):
        self.issue();self.state.step();self.assertEqual(self.state.audit()['pending_events'],1)
    def test_atomic_reference_grant_and_p_commit(self):
        self.issue();self.state.run();self.assertEqual(self.state.audit()['P_writes'],self.state.audit()['reference_v1_tick_grants'])

class ScenarioTests(unittest.TestCase):
    def test_baseline(self):
        r=scenario(learn=False,oracle=False);self.assertEqual((r['successes'],r['reference_tick_P_grants']), (48,0))
    def test_adapted(self):
        r=scenario(learn=True,oracle=False);self.assertEqual((r['successes'],r['reference_tick_P_grants']),(88,8))
    def test_parity_determinism(self):
        a=scenario(learn=True,oracle=False);b=scenario(learn=True,oracle=False)
        self.assertEqual(a,b)
    def test_reopen_each_episode(self):
        a=scenario(learn=True,recover_every=1,oracle=False)
        b=scenario(learn=True,recover_every=0,oracle=False)
        self.assertEqual(a,b)
    def test_lost_forward(self):
        r=scenario(learn=True,phases=1,drop_forward=True,oracle=False)
        self.assertEqual((r['successes'],r['semantic_receipts'],r['reference_tick_P_grants']),(0,0,0))
    def test_all_feedback_lost(self):
        r=scenario(learn=True,phases=1,drop_feedback=True,oracle=False)
        self.assertEqual(r['reference_tick_P_grants'],0)
    def test_all_late(self):
        r=scenario(learn=True,phases=1,feedback_delay=5,oracle=False)
        self.assertEqual(r['reference_tick_P_grants'],0)
    def test_bounded_delay(self):
        r=scenario(learn=True,feedback_delay=4,oracle=False)
        self.assertEqual((r['successes'],r['reference_tick_P_grants']),(88,8))
    def test_reopen_feedback_midtick(self):self.assertTrue(crash_resume_witness()['replay_did_not_reapply'])
    def test_deadline_control(self):self.assertTrue(delay_witness()['tick_19_denied_P'])
    def test_host_goal_control(self):self.assertTrue(host_control_witness()['host_can_drive_reference_grant'])
    def test_oracle_optional(self):
        r=scenario(learn=True,phases=1,oracle=False)
        self.assertIsNone(r['source_oracle_rows_sha256'])
        self.assertEqual(r['source_oracle_calls'],0)

if __name__=='__main__':unittest.main()
