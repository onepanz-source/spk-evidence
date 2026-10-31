"""Independent executable tests for the reference resource-fenced P port."""
import sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject
from research.spk_v5_t10jkl_mno_pqr.resource_authority_v1 import ResourceAdmittedEngine,native_seam_denial
from research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate import scenario,negative_witness,report

class ResourceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'db.sqlite'
    def new(self,**kwargs):
        e=ResourceAdmittedEngine(self.db,**kwargs);self.addCleanup(lambda: e.db.close() if e.db else None)
        return e
    def test_default_manifest_scope(self):
        e=self.new();r=e.resource();self.assertEqual((r['owner'],r['domain'],r['pe_id'],r['mode']),('C','P','PE-C-RESEARCH','execute'))
    def test_default_limits(self):
        e=self.new();r=e.resource();self.assertEqual((r['grant_ceiling'],r['cue0_ceiling'],r['cue1_ceiling']),(8,4,4))
    def test_unlimited_not_accepted(self):
        for val in (-1,49,True,False,'8'):
            with self.subTest(val=val):
                with self.assertRaises(Reject):ResourceAdmittedEngine(self.db,grant_ceiling=val)
    def test_context_limits_domain(self):
        for val in (-1,49,True,'4'):
            with self.subTest(val=val):
                with self.assertRaises(Reject):ResourceAdmittedEngine(self.db,context_ceiling=val)
    def test_empty_resource_custody(self):
        e=self.new();a=e.audit_resource_custody();self.assertEqual(a['total_consumed'],0)
    def test_actual_tick_commits_once(self):
        e=self.new();e.submit(0,11);self.assertEqual(len(e.run()),5);self.assertEqual(e.audit_resource_custody()['total_consumed'],1)
    def test_reopen_manifest(self):
        e=self.new();r=e.resource();e.reopen();self.assertEqual(e.resource(),r)
    def test_reopen_nonzero_grant(self):
        e=self.new();e.submit(0,11);e.run();old=e.audit_resource_custody();e.reopen();self.assertEqual(e.audit_resource_custody(),old)
    def test_reopen_rejects_extra_guard(self):
        e=self.new();e.db.execute('CREATE TRIGGER spk_unknown_guard BEFORE UPDATE ON p BEGIN SELECT 0; END')
        with self.assertRaises(Reject):e.audit_resource_contract()
    def test_rejects_deleted_guard(self):
        e=self.new();e.db.execute('DROP TRIGGER spk_ref_v3_resource_guard')
        with self.assertRaises(Reject):e.audit_resource_contract()
    def test_rejects_deleted_manifest(self):
        e=self.new();e.db.execute('DELETE FROM reference_p_resource')
        with self.assertRaises(Reject):e.audit_resource_contract()
    def test_verify_mode_no_new_grants(self):
        e=self.new();e.transition_profile(expected_revision=0,mode='verify');e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.IntegrityError):e.step()
        self.assertEqual(e.audit_resource_custody()['total_consumed'],0)
    def test_verify_restores_execute(self):
        e=self.new();e.transition_profile(expected_revision=0,mode='verify');e.transition_profile(expected_revision=1,mode='execute')
        e.submit(0,11);e.run();self.assertEqual(e.audit_resource_custody()['total_consumed'],1)
    def test_zero_quota_denies_tick(self):
        e=self.new(grant_ceiling=0,context_ceiling=0);e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.IntegrityError):e.step()
        self.assertEqual(e.audit()['P_writes'],0)
    def test_global_quota_at_one(self):
        e=self.new(grant_ceiling=1,context_ceiling=2);e.submit(0,11);e.run();e.submit(1,12)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.IntegrityError):e.step()
        self.assertEqual(e.audit_resource_custody()['total_consumed'],1)
    def test_context_quota_zero(self):
        e=self.new(grant_ceiling=8,context_ceiling=0);e.submit(1,12)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.IntegrityError):e.step()
    def test_admin_stale_revision_denied(self):
        e=self.new();e.transition_profile(expected_revision=0,grant_ceiling=8)
        with self.assertRaises(Reject):e.transition_profile(expected_revision=0,grant_ceiling=9)
    def test_admin_bool_revision_denied(self):
        e=self.new()
        with self.assertRaises(Reject):e.transition_profile(expected_revision=True)
    def test_admin_bad_mode_denied(self):
        e=self.new()
        for mode in ('training','remodel','dangerous',None):
            if mode is None:continue
            with self.subTest(mode=mode),self.assertRaises(Reject):e.transition_profile(expected_revision=0,mode=mode)
    def test_cannot_shrink_spent_capacity(self):
        e=self.new();e.submit(0,11);e.run()
        with self.assertRaises(Reject):e.transition_profile(expected_revision=0,grant_ceiling=0)
    def test_cannot_shrink_pending_budget(self):
        e=self.new();e.submit(0,11)
        with self.assertRaises(Reject):e.transition_profile(expected_revision=0,grant_ceiling=7)
    def test_can_expand_pending_budget(self):
        e=self.new();e.submit(0,11);e.transition_profile(expected_revision=0,grant_ceiling=9,context_ceiling=5)
        e.run();self.assertEqual(e.audit_resource_custody()['total_consumed'],1)
    def test_direct_mutation_denied(self):
        e=self.new()
        with self.assertRaises(sqlite3.IntegrityError):e.db.execute('UPDATE p SET version=version+1 WHERE cue=0')
    def test_idempotent_after_restart(self):
        e=self.new();e.submit(0,11);e.run();a=e.audit_resource_custody();e.reopen()
        self.assertIsNone(e.step());self.assertEqual(e.audit_resource_custody(),a)
    def test_native_remains_denied(self):
        self.assertEqual(native_seam_denial(),'DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT')
    def test_fixed_control_zero_grants(self):
        s=scenario('batch3',learn=False);self.assertEqual((s['successes'],s['reference_grants']),(48,0))
    def test_affinity_success_unchanged(self):
        s=scenario('context_affinity');self.assertEqual((s['successes'],s['reference_grants'],s['waves']),(88,8,48))
    def test_naive_stale_veto_unchanged(self):
        s=scenario('batch3');self.assertEqual((s['successes'],s['stale_vetoes'],s['waves']),(84,4,32))
    def test_serial_parity(self):
        s=scenario('serial');self.assertEqual((s['successes'],s['waves']),(88,96))
    def test_affinity_restart_byte_parity(self):
        a=scenario('context_affinity');b=scenario('context_affinity',reopen=True)
        self.assertEqual(a['resource'],b['resource']);self.assertEqual(a['source_rows_sha256'],b['source_rows_sha256'])
    def test_negative_witness_all(self):
        self.assertTrue(all(negative_witness().values()))
    def test_complete_report_invariants(self):
        r=report('.');self.assertEqual(r['T10MNO']['reference_success_delta_affinity_vs_naive'],4)
        self.assertEqual((r['native_SPK_P_grants'],r['native_learning'],r['promotion_allowed']),(0,False,False))

if __name__=='__main__':unittest.main()
