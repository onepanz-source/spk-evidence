"""Research-v1 concurrency only. Tests do not assert native SPK grants."""
from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import MultiTickEngine,Reject,pe_step
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import (
    execute,concurrent_conflict,fairness_witness,crash_witness,denial_witness,report,tasks,PARENT_SHA,sha)

class ConcurrentEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'p.sqlite'
        self.e=MultiTickEngine(self.path,max_inflight=3)
    def tearDown(self):
        self.e.close();self.tmp.cleanup()
    def pair(self):
        a=self.e.submit(0,11);b=self.e.submit(0,11);return a,b
    def test_schema_is_distinct_from_t8(self):self.assertIn('concurrent',dict(self.e.db.execute('SELECT k,v FROM meta'))['schema'])
    def test_three_active_allowed(self):
        self.e.submit(0,11);self.e.submit(1,12);self.e.submit(0,11)
        self.assertEqual(self.e.audit()['running'],3)
    def test_fourth_active_denied(self):
        [self.e.submit(0,11) for _ in range(3)]
        with self.assertRaisesRegex(Reject,'INFLIGHT_RESOURCE_BUDGET'):self.e.submit(1,12)
    def test_resource_denial_is_atomic(self):
        [self.e.submit(0,11) for _ in range(3)]
        count=self.e.audit()['ledger_events']
        with self.assertRaises(Reject):self.e.submit(1,12)
        self.assertEqual(self.e.audit()['ledger_events'],count)
    def test_capacity_released_after_settlement(self):
        [self.e.submit(0,11) for _ in range(3)];self.e.run()
        self.e.submit(1,12);self.assertEqual(self.e.audit()['running'],1)
    def test_capacity_persists_reopen(self):
        self.e.submit(0,11);self.e.reopen();self.assertEqual(self.e.max_inflight,3)
    def test_reopen_wrong_budget_denied(self):
        with self.assertRaisesRegex(Reject,'META_DRIFT'):
            x=MultiTickEngine(self.path,max_inflight=2,create=False);x.close()
    def test_reopen_wrong_learning_mode_denied(self):
        with self.assertRaisesRegex(Reject,'META_DRIFT'):
            x=MultiTickEngine(self.path,learn=False,max_inflight=3,create=False);x.close()
    def test_bad_capacity_zero_denied(self):
        with self.assertRaisesRegex(Reject,'CONFIG'):MultiTickEngine(Path(self.tmp.name)/'bad.sqlite',max_inflight=0)
    def test_bad_capacity_float_denied(self):
        with self.assertRaisesRegex(Reject,'CONFIG'):MultiTickEngine(Path(self.tmp.name)/'bad.sqlite',max_inflight=2.0)
    def test_bad_capacity_bool_denied(self):
        with self.assertRaisesRegex(Reject,'CONFIG'):MultiTickEngine(Path(self.tmp.name)/'bad.sqlite',max_inflight=True)
    def test_bad_capacity_excess_denied(self):
        with self.assertRaisesRegex(Reject,'CONFIG'):MultiTickEngine(Path(self.tmp.name)/'bad.sqlite',max_inflight=9)
    def test_single_still_five_semantic_ticks(self):
        self.e.submit(0,11);self.assertEqual([x['kind'] for x in self.e.run()],
            ['PE_C','PE_B','PE_A','SEM_A_B','SEM_B_C'])
    def test_three_interleaved_five_stages(self):
        [self.e.submit(i%2,11) for i in range(3)]
        rows=self.e.run();self.assertEqual(len(rows),15)
        self.assertEqual([x['kind'] for x in rows],
            ['PE_C']*3+['PE_B']*3+['PE_A']*3+['SEM_A_B']*3+['SEM_B_C']*3)
    def test_local_ticks_are_not_global_clock(self):
        self.pair();rows=self.e.run()
        self.assertEqual([r['tick'] for r in rows[:2]],[10,10]);self.assertNotEqual(rows[0]['slot'],rows[1]['slot'])
    def test_dispatched_slots_unique(self):
        self.pair();rows=self.e.run()
        self.assertEqual(len({x['slot'] for x in rows}),len(rows))
    def test_dispatch_slots_monotone(self):
        [self.e.submit(i%2,11) for i in range(3)];rows=self.e.run()
        self.assertEqual([x['slot'] for x in rows],list(range(15)))
    def test_dispatch_slots_durable(self):
        self.pair();self.e.run();a=self.e.audit();self.e.reopen();self.assertEqual(self.e.audit(),a)
    def test_fifo_ignores_new_small_local_ticks(self):
        self.e.submit(0,11,feedback_delay=12);self.e.step();self.e.submit(1,12)
        remaining=self.e.run();self.assertIn('SEM_B_C',[x['kind'] for x in remaining])
    def test_two_negative_same_version_one_grant(self):
        ids=self.pair();self.e.run();self.assertEqual([self.e.result(x)['grant'] for x in ids],[0,None])
    def test_two_negative_stale_veto_recorded(self):
        self.pair();self.e.run();self.assertEqual(self.e.audit()['stale_vetoes'],1)
    def test_stale_judgment_outcome_retained(self):
        a,b=self.pair();self.e.run();self.assertEqual(self.e.result(b)['outcome'],'WORSENED')
    def test_stale_judgment_no_second_version(self):
        self.pair();self.e.run();self.assertEqual(self.e.audit()['P_versions'][0],1)
    def test_stale_judgment_no_second_budget(self):
        self.pair();self.e.run();self.assertEqual(self.e.db.execute('SELECT budget FROM p WHERE cue=0').fetchone()[0],11)
    def test_different_cues_both_grant(self):
        ids=[self.e.submit(0,11),self.e.submit(1,12)];self.e.run()
        self.assertEqual([self.e.result(x)['grant'] for x in ids],[0,1])
    def test_different_cues_no_veto(self):
        self.e.submit(0,11);self.e.submit(1,12);self.e.run()
        self.assertEqual(self.e.audit()['stale_vetoes'],0)
    def test_positive_no_grant(self):
        i=self.e.submit(0,12);self.e.run();self.assertEqual(self.e.result(i)['outcome'],'IMPROVED')
        self.assertIsNone(self.e.result(i)['grant'])
    def test_no_learning_no_grants(self):
        self.e.close();self.e=MultiTickEngine(Path(self.tmp.name)/'control.sqlite',max_inflight=2,learn=False)
        [self.e.submit(0,11) for _ in range(2)];self.e.run()
        self.assertEqual(self.e.audit()['P_writes'],0)
    def test_drop_feedback_no_grant(self):
        ids=[self.e.submit(0,11,drop_feedback=True) for _ in range(3)];self.e.run()
        self.assertEqual(self.e.audit()['P_writes'],0)
    def test_drop_forward_no_grant(self):
        ids=[self.e.submit(0,11,drop_forward=True) for _ in range(3)];self.e.run()
        self.assertEqual([self.e.result(x)['outcome'] for x in ids],['ABSENT']*3)
    def test_deadline_prevents_grant(self):
        i=self.e.submit(0,11,feedback_delay=5);self.e.run();self.assertIsNone(self.e.result(i)['grant'])
    def test_deadline_still_semantic(self):
        i=self.e.submit(0,11,feedback_delay=5);self.e.run();self.assertIn('SEM_B_C',self.e.result(i)['semantic_events'])
    def test_crash_after_three_PE_stages(self):
        [self.e.submit(i%2,11) for i in range(3)];[self.e.step() for _ in range(9)]
        self.assertEqual(self.e.audit()['pending_events'],3)
    def test_crash_recovery_three_episodes(self):
        ids=[self.e.submit(0,11),self.e.submit(0,11),self.e.submit(1,12)]
        [self.e.step() for _ in range(9)];self.e.reopen();self.e.run()
        self.assertEqual(self.e.audit()['P_writes'],2)
    def test_resume_replay_none(self):
        self.pair();self.e.run();self.e.reopen();self.assertIsNone(self.e.step())
    def test_failure_before_commit_rolls_back(self):
        self.e.submit(0,11);self.e.db.execute("UPDATE event SET digest='X'")
        with self.assertRaisesRegex(Reject,'EVENT_DIGEST_DRIFT'):self.e.step()
        self.assertEqual(self.e.audit() if False else self.e.db.execute("SELECT status FROM event").fetchone()[0],'QUEUED')
    def test_invalid_event_detected_on_audit(self):
        self.e.submit(0,11);self.e.db.execute("UPDATE event SET digest='X'")
        with self.assertRaisesRegex(Reject,'EVENT_AUDIT_DRIFT'):self.e.audit()
    def test_altered_ledger_detected(self):
        self.e.submit(0,11);self.e.run();self.e.db.execute('UPDATE ledger SET digest=? WHERE seq=0',('F'*64,))
        with self.assertRaisesRegex(Reject,'LEDGER_CHAIN_DRIFT'):self.e.audit()
    def test_updated_policy_version_monotonic(self):
        self.e.submit(0,11);self.e.run();self.assertEqual(self.e.audit()['P_versions'][0],1)
    def test_host_untrusted_source_not_authenticated(self):
        x=pe_step('A',11,12,12,[3]);self.assertEqual(x['emits'],[22,7])
    def test_no_native_grant_interface(self):
        self.e.submit(0,11);self.e.run();self.assertEqual(self.e.audit()['reference_v1_tick_grants'],1)
        self.assertFalse(hasattr(self.e,'native_spk_p_grant'))
    def test_serialization_after_one_tick(self):
        self.pair();self.e.step();self.assertEqual(self.e.audit()['dispatcher_slots'],1)
    def test_atomic_peer_update_after_same_cue(self):
        self.pair();self.e.run();self.assertEqual(self.e.audit()['P_writes'],1)
    def test_starting_again_with_bad_configuration_denied(self):
        with self.assertRaisesRegex(Reject,'ALREADY_INITIALIZED'):
            MultiTickEngine(self.path,max_inflight=3)
    def test_two_process_restart_and_resume(self):
        ids=self.pair();[self.e.step() for _ in range(6)];self.e.close()
        code=("from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import MultiTickEngine;"
              "import sys;x=MultiTickEngine(sys.argv[1],max_inflight=3,create=False);"
              "x.run();x.close()")
        subprocess.run([sys.executable,'-c',code,str(self.path)],check=True,capture_output=True,timeout=25)
        self.e=MultiTickEngine(self.path,max_inflight=3,create=False)
        self.assertEqual(self.e.audit()['P_writes'],1)
    def test_denied_when_budget_exhausted(self):
        self.e.close();self.e=MultiTickEngine(Path(self.tmp.name)/'b.sqlite',budget=0,max_inflight=3)
        self.e.submit(0,11);self.e.run();self.assertEqual(self.e.audit()['reference_v1_tick_grants'],0)
    def test_strict_input_domain(self):
        for cue,goal in [(False,11),(2,11),(0,13),('0',11)]:
            with self.subTest(cue=cue,goal=goal),self.assertRaises(Reject):self.e.submit(cue,goal)

class CumulativeTests(unittest.TestCase):
    def test_serial_88(self):self.assertEqual(execute(inflight=1)['successes'],88)
    def test_serial_8_updates(self):self.assertEqual(execute(inflight=1)['grants'],8)
    def test_paired_88(self):self.assertEqual(execute(inflight=2)['successes'],88)
    def test_triple_84(self):self.assertEqual(execute(inflight=3)['successes'],84)
    def test_triple_4_vetoes(self):self.assertEqual(execute(inflight=3)['vetoes'],4)
    def test_triple_8_updates(self):self.assertEqual(execute(inflight=3)['grants'],8)
    def test_baseline_48(self):self.assertEqual(execute(inflight=3,learn=False)['successes'],48)
    def test_no_feedback_48(self):self.assertEqual(execute(inflight=3,drop_feedback=True)['successes'],48)
    def test_restart_parity(self):
        a=execute(inflight=3);b=execute(inflight=3,reopen_each_batch=True)
        self.assertEqual((a['successes'],a['grants'],a['vetoes'],a['rows_sha256']),
                         (b['successes'],b['grants'],b['vetoes'],b['rows_sha256']))
    def test_conflict_witness(self):self.assertTrue(concurrent_conflict()['two_same_version_negative_votes_one_grant'])
    def test_fairness_witness(self):self.assertTrue(fairness_witness()['late_episode_settled'])
    def test_crash_witness(self):self.assertTrue(crash_witness()['replay_safe'])
    def test_resource_witness(self):self.assertTrue(denial_witness()['active_epoch_capacity_denied'])
    def test_parent_report_sha(self):
        self.assertEqual(sha(Path(__file__).parents[1]/'reference/t8stu-vwx-yza.json'),PARENT_SHA)
    def test_report_safe_boundaries(self):
        r=report(Path(__file__).parents[3])
        self.assertFalse(r['native_learning']);self.assertEqual(r['native_SPK_P_grants'],0)
    def test_report_reproducible(self):
        root=Path(__file__).parents[3];self.assertEqual(report(root),report(root))

if __name__=='__main__':unittest.main()
