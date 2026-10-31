import sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject,digest
from research.spk_v5_t9stu_vwx_yza.p_target_admission_port_v1 import target_for
from research.spk_v5_t10abc_def_ghi.provider_v1 import ProviderFencedTickEngine,native_gate_must_deny,PROVIDER_TRIGGERS
from research.spk_v5_t10abc_def_ghi.cumulative_provider_gate import report,scenario,negative_witness,sha,PARENT
ROOT=Path(__file__).resolve().parents[3]

class ProviderAtTick(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.engine=ProviderFencedTickEngine(Path(self.tmp.name)/'database.sqlite')
        self.addCleanup(lambda:self.engine.close())
    def check_provider(self,expected):
        r=self.engine.audit_provider()
        self.assertEqual(r['provider_v1_authorizations'],expected)
        self.assertEqual(r['provider_v1_commits'],expected)
        self.assertEqual(r['native_SPK_Memory_Contract_grants'],0)
        return r
    def test_provider_installed(self):self.engine.assert_provider()
    def test_extra_sql_triggers_exact(self):
        names={r['name'] for r in self.engine.db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='p'")}
        self.assertTrue(set(PROVIDER_TRIGGERS).issubset(names));self.assertEqual(len(names),5)
    def test_reference_first_negative_commit(self):
        self.engine.submit(0,11);self.engine.run();self.check_provider(1)
    def test_no_mutation_on_positive(self):
        self.engine.submit(0,12);self.engine.run();self.check_provider(0)
    def test_learning_disabled_no_grant(self):
        self.engine.close();self.engine=ProviderFencedTickEngine(Path(self.tmp.name)/'disabled.sqlite',learn=False)
        self.engine.submit(0,11);self.engine.run();self.check_provider(0)
    def test_drop_forward_blocks_provider(self):
        self.engine.submit(0,11,drop_forward=True);self.engine.run();self.check_provider(0)
    def test_drop_feedback_blocks_provider(self):
        self.engine.submit(0,11,drop_feedback=True);self.engine.run();self.check_provider(0)
    def test_deadline_18_grants(self):
        self.engine.submit(0,11,feedback_delay=4);self.engine.run();self.check_provider(1)
    def test_deadline_19_denies(self):
        self.engine.submit(0,11,feedback_delay=5);self.engine.run();self.check_provider(0)
    def test_two_same_versions_single_commit(self):
        self.engine.submit(0,11);self.engine.submit(0,11);self.engine.run()
        self.check_provider(1);self.assertEqual(self.engine.audit()['stale_vetoes'],1)
    def test_different_contexts_two_commits(self):
        self.engine.submit(0,11);self.engine.submit(1,12);self.engine.run();self.check_provider(2)
    def test_one_grant_per_version_chain(self):
        self.engine.submit(0,11);self.engine.run();self.engine.submit(0,12);self.engine.run()
        self.assertEqual(self.engine.audit()['P_writes'],2);self.check_provider(2)
    def test_p_store_denies_direct_choice(self):
        with self.assertRaises(sqlite3.IntegrityError):self.engine.db.execute('UPDATE p SET choice=11 WHERE cue=0')
    def test_p_store_denies_direct_version(self):
        with self.assertRaises(sqlite3.IntegrityError):self.engine.db.execute('UPDATE p SET version=version+1 WHERE cue=0')
    def test_p_store_denies_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):self.engine.db.execute('INSERT INTO p VALUES(2,11,0,12)')
    def test_p_store_denies_delete(self):
        with self.assertRaises(sqlite3.IntegrityError):self.engine.db.execute('DELETE FROM p WHERE cue=0')
    def test_provider_denies_without_grant(self):
        self.assertEqual(self.engine._authorize(0,12,0,12,11,1,11),0)
    def test_provider_denies_if_disabled(self):
        self.engine.provider_enabled=False
        self.assertEqual(self.engine._authorize(0,12,0,12,11,1,11),0)
    def test_wrong_context_denied(self):
        self.assertEqual(self.engine._authorize(2,12,0,12,11,1,11),0)
    def test_wrong_version_denied(self):
        self.assertEqual(self.engine._authorize(0,12,-1,12,11,0,11),0)
    def test_wrong_choice_denied(self):
        self.assertEqual(self.engine._authorize(0,12,0,12,12,1,11),0)
    def test_wrong_budget_denied(self):
        self.assertEqual(self.engine._authorize(0,12,0,12,11,1,12),0)
    def test_wrong_cas_increment_denied(self):
        self.assertEqual(self.engine._authorize(0,12,0,12,11,2,11),0)
    def test_provider_denial_is_atomic(self):
        self.engine.submit(0,11)
        for _ in range(4):self.engine.step()
        p_before=tuple(self.engine.db.execute('SELECT * FROM p WHERE cue=0').fetchone())
        self.engine.provider_enabled=False
        with self.assertRaises(sqlite3.IntegrityError):self.engine.step()
        self.assertEqual(tuple(self.engine.db.execute('SELECT * FROM p WHERE cue=0').fetchone()),p_before)
        self.assertEqual(self.engine.db.execute('SELECT count(*) FROM p_grant').fetchone()[0],0)
        self.assertEqual(self.engine.db.execute("SELECT count(*) FROM event WHERE kind='SEM_B_C' AND status='QUEUED'").fetchone()[0],1)
        self.engine.reopen();self.engine.step();self.check_provider(1)
    def test_provider_trigger_missing_detected(self):
        self.engine.db.execute('DROP TRIGGER spk_ref_v2_provider_guard')
        with self.assertRaises(Reject):self.engine.assert_provider()
    def test_provider_trigger_modified_detected(self):
        self.engine.db.execute('DROP TRIGGER spk_ref_v2_provider_guard')
        self.engine.db.execute('CREATE TRIGGER spk_ref_v2_provider_guard BEFORE UPDATE ON p BEGIN SELECT 1; END')
        with self.assertRaises(Reject):self.engine.assert_fence()
    def test_provider_receipt_store_deleted_detected(self):
        self.engine.db.execute('DROP TABLE reference_provider_receipt')
        with self.assertRaises(Reject):self.engine.assert_provider()
    def test_provider_receipts_survive_reopen(self):
        self.engine.submit(0,11);self.engine.run();old=self.check_provider(1)
        self.engine.reopen();self.assertEqual(self.check_provider(1),old)
    def test_provider_cannot_double_write_after_settle(self):
        self.engine.submit(0,11);self.engine.run()
        with self.assertRaises(sqlite3.IntegrityError):
            self.engine.db.execute('UPDATE p SET choice=12,version=2,budget=10 WHERE cue=0')
    def test_provider_record_tamper_rejected(self):
        self.engine.submit(0,11);self.engine.run()
        self.engine.db.execute('UPDATE reference_provider_receipt SET event_digest=?',('f'*64,))
        with self.assertRaises(Reject):self.engine.audit_provider()
    def test_provider_grant_tamper_rejected(self):
        self.engine.submit(0,11);self.engine.run()
        self.engine.db.execute('UPDATE p_grant SET verdict_digest=?',('f'*64,))
        with self.assertRaises(Reject):self.engine.audit_provider()
    def test_provider_event_tamper_rejected(self):
        self.engine.submit(0,11);self.engine.run()
        self.engine.db.execute("UPDATE event SET digest=? WHERE kind='SEM_B_C'",('f'*64,))
        with self.assertRaises(Reject):self.engine.audit_provider()
    def test_provider_receipt_delete_rejected(self):
        self.engine.submit(0,11);self.engine.run()
        self.engine.db.execute('DELETE FROM reference_provider_receipt')
        with self.assertRaises(Reject):self.engine.audit_provider()
    def test_native_port_fail_closed(self):
        self.assertEqual(native_gate_must_deny(target_for(cue=0,version=0)),
                         'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT')
    def test_native_zero_in_provider_audit(self):
        self.engine.submit(0,11);self.engine.run()
        self.assertEqual(self.check_provider(1)['native_SPK_Memory_Contract_grants'],0)
    def test_provider_origin_not_authenticated(self):
        self.engine.submit(0,11);self.engine.run()
        self.assertFalse(self.check_provider(1)['provider_origin_authenticated'])

class CumulativeProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=report(ROOT)
    def test_parent_pin(self):
        self.assertEqual(sha(ROOT/'research/spk_v5_t10abc_def_ghi/reference/t9stu-vwx-yza-cumulative.json'),PARENT)
    def test_naive_84(self):self.assertEqual(self.r['T10DEF']['reference_provider_scenarios']['naive_three']['successes'],84)
    def test_affinity_88(self):self.assertEqual(self.r['T10DEF']['reference_provider_scenarios']['context_affinity']['successes'],88)
    def test_serial_88(self):self.assertEqual(self.r['T10DEF']['reference_provider_scenarios']['serial']['successes'],88)
    def test_control_48(self):self.assertEqual(self.r['T10DEF']['reference_provider_scenarios']['fixed_control']['successes'],48)
    def test_provider_8(self):self.assertEqual(self.r['T10DEF']['provider_v1_authorizations_in_affinity'],8)
    def test_restart_exact(self):
        x=self.r['T10DEF']['reference_provider_scenarios']
        self.assertEqual(x['restarted_affinity']['provider'],x['context_affinity']['provider'])
    def test_parent_parity(self):self.assertTrue(self.r['T10DEF']['outcome_parity_to_T9'])
    def test_atomic_denial_witness(self):self.assertTrue(self.r['T10GHI']['negative_witness']['provider_denial_rollback_atomic'])
    def test_stale_single_grant(self):self.assertTrue(self.r['T10GHI']['negative_witness']['two_same_version_negative_votes_one_grant'])
    def test_host_can_override_provider(self):self.assertTrue(self.r['host_can_forge'])
    def test_native_grants_zero(self):self.assertEqual(self.r['native_SPK_P_grants'],0)
    def test_native_writes_zero(self):self.assertEqual(self.r['native_SPK_P_writes'],0)
    def test_native_learning_false(self):self.assertFalse(self.r['native_learning'])
    def test_source_untouched(self):self.assertEqual(self.r['new_frozen_scheduler_calls'],0)
    def test_no_promotion(self):self.assertFalse(self.r['promotion_allowed'])
    def test_deterministic_repeat(self):self.assertEqual(self.r,report(ROOT))

if __name__=='__main__':unittest.main()
