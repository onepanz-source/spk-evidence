import json,sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject
from research.spk_v5_t9stu_vwx_yza.fenced_p_store_v1 import FencedMultiTickEngine,independent_grant_custody
from research.spk_v5_t9stu_vwx_yza.p_target_admission_port_v1 import target_for,project_grant,native_authorize,NativeUnavailable
from research.spk_v5_t9stu_vwx_yza.cumulative_p_boundary_gate import negative_witness,run_fenced,report,sha,PARENT
ROOT=Path(__file__).resolve().parents[3]

class FencedStore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=FencedMultiTickEngine(Path(self.tmp.name)/'engine.db')
        self.addCleanup(lambda:self.e.close())
    def test_initial_fence_installed(self):self.e.assert_fence()
    def test_direct_choice_update_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):self.e.db.execute('UPDATE p SET choice=11 WHERE cue=0')
    def test_direct_version_update_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):self.e.db.execute('UPDATE p SET version=version+1 WHERE cue=0')
    def test_delete_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):self.e.db.execute('DELETE FROM p')
    def test_insert_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):self.e.db.execute('INSERT INTO p VALUES(2,11,0,1)')
    def test_original_semantic_grant_commits(self):
        self.e.submit(0,11);self.e.run();self.assertEqual(self.e.audit()['P_writes'],1)
    def test_independent_receipt_verification(self):
        self.e.submit(0,11);self.e.run();self.assertEqual(independent_grant_custody(self.e)['verified_reference_grants'],1)
    def test_no_grant_on_positive(self):
        self.e.submit(0,12);self.e.run();self.assertEqual(independent_grant_custody(self.e)['verified_reference_grants'],0)
    def test_no_grant_when_learning_disabled(self):
        self.e.close();self.e=FencedMultiTickEngine(Path(self.tmp.name)/'disabled.db',learn=False)
        self.e.submit(0,11);self.e.run();self.assertEqual(self.e.audit()['P_writes'],0)
    def test_second_stale_vote_cannot_write(self):
        self.e.submit(0,11);self.e.submit(0,11);self.e.run()
        self.assertEqual((self.e.audit()['P_writes'],self.e.audit()['stale_vetoes']),(1,1))
    def test_other_cue_updates_independently(self):
        self.e.submit(0,11);self.e.submit(1,12);self.e.run()
        self.assertEqual(self.e.audit()['P_writes'],2)
    def test_grant_materialized_in_reference_only(self):
        self.e.submit(0,11);self.e.run();x=project_grant(self.e,0)
        self.assertFalse(x['target']['native_memory_grant']);self.assertIsNone(x['native_grant_id'])
    def test_reopen_retains_trigger(self):
        self.e.submit(0,11);self.e.run();before=independent_grant_custody(self.e)
        self.e.reopen();self.e.assert_fence();self.assertEqual(before,independent_grant_custody(self.e))
    def test_open_rejects_removed_trigger(self):
        self.e.db.execute('DROP TRIGGER spk_ref_p_fence')
        with self.assertRaisesRegex(Reject,'REFERENCE_P_FENCE_MISSING_OR_EXTRA'):self.e.reopen()
        self.e=FencedMultiTickEngine(Path(self.tmp.name)/'recovered.db')
    def test_trigger_drift_rejected(self):
        self.e.db.execute('DROP TRIGGER spk_ref_p_fence')
        self.e.db.execute('CREATE TRIGGER spk_ref_p_fence BEFORE UPDATE ON p BEGIN SELECT 1; END')
        with self.assertRaisesRegex(Reject,'REFERENCE_P_FENCE_DRIFT'):self.e.assert_fence()
    def test_event_lineage_tamper_fails(self):
        self.e.submit(0,11);self.e.run()
        self.e.db.execute("UPDATE p_grant SET verdict_digest=?",('f'*64,))
        with self.assertRaises(Reject):independent_grant_custody(self.e)
    def test_semantic_event_tamper_fails(self):
        self.e.submit(0,11);self.e.run()
        self.e.db.execute("UPDATE event SET digest=? WHERE kind='SEM_B_C'",('f'*64,))
        with self.assertRaises(Reject):independent_grant_custody(self.e)
    def test_direct_second_commit_denied(self):
        self.e.submit(0,11);self.e.run()
        with self.assertRaises(sqlite3.IntegrityError):
            self.e.db.execute('UPDATE p SET choice=12,version=version+1,budget=budget-1 WHERE cue=0')
    def test_target_scope(self):
        self.assertEqual(target_for(cue=0,version=2)['target_id'],'P/C/context-0')
    def test_invalid_target_owner(self):
        with self.assertRaisesRegex(Reject,'TARGET_OWNER_DENIED'):target_for(owner='A',cue=0,version=0)
    def test_invalid_target_domain(self):
        with self.assertRaisesRegex(Reject,'TARGET_DOMAIN_DENIED'):target_for(domain='S',cue=0,version=0)
    def test_invalid_target_mode(self):
        with self.assertRaisesRegex(Reject,'TARGET_MODE_DENIED'):target_for(mode='training',cue=0,version=0)
    def test_invalid_target_pe(self):
        with self.assertRaisesRegex(Reject,'TARGET_PE_DENIED'):target_for(pe='OTHER',cue=0,version=0)
    def test_invalid_target_cue(self):
        with self.assertRaisesRegex(Reject,'TARGET_CONTEXT_DENIED'):target_for(cue=2,version=0)
    def test_invalid_target_version(self):
        with self.assertRaisesRegex(Reject,'TARGET_VERSION_DENIED'):target_for(cue=0,version=-1)
    def test_native_port_not_connected(self):
        with self.assertRaises(NativeUnavailable):native_authorize(target_for(cue=0,version=0))

class NewCumulative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=report(ROOT)
    def test_parent_sha_pin(self):self.assertEqual(sha(ROOT/'research/spk_v5_t9stu_vwx_yza/reference/t9jkl-mno-pqr-cumulative.json'),PARENT)
    def test_fenced_parallel_results(self):
        self.assertEqual((self.r['T9STU']['fenced_naive']['successes'],self.r['T9STU']['fenced_affinity']['successes']),(84,88))
    def test_fenced_serial_result(self):self.assertEqual(self.r['T9STU']['fenced_serial']['successes'],88)
    def test_stale_counts(self):self.assertEqual((self.r['T9STU']['fenced_naive']['stale_vetoes'],self.r['T9STU']['fenced_affinity']['stale_vetoes']),(4,0))
    def test_admission_cost_unchanged(self):self.assertEqual(self.r['T9YZA']['performance_cost_waves'],16)
    def test_no_native_auth(self):self.assertEqual(self.r['native_SPK_P_grants'],0)
    def test_no_native_updates(self):self.assertEqual(self.r['native_SPK_P_writes'],0)
    def test_no_original_scheduler_calls(self):self.assertEqual(self.r['new_frozen_scheduler_calls'],0)
    def test_no_promotion(self):self.assertFalse(self.r['promotion_allowed'])
    def test_host_owns_triggers(self):self.assertTrue(self.r['T9YZA']['negative_witness']['privileged_host_can_reseal'])
    def test_reference_grant_custody(self):self.assertEqual(self.r['T9STU']['fenced_naive']['custody']['verified_reference_grants'],8)
    def test_restart_parity(self):
        self.assertEqual(self.r['T9STU']['fenced_affinity']['core_rows_sha256'],self.r['T9YZA']['restarted_affinity']['core_rows_sha256'])
    def test_direct_p_denials(self):self.assertEqual(len(self.r['T9YZA']['negative_witness']['direct_P_attempts_denied']),4)
    def test_unavailable_native_port(self):self.assertFalse(self.r['T9VWX']['native_memory_contract_port_implemented'])
    def test_repeat_byte_equal(self):self.assertEqual(self.r,report(ROOT))

if __name__=='__main__':unittest.main()
