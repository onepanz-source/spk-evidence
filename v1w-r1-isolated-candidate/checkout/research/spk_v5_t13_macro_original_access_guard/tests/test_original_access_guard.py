"""T13 fail-closed and source-scoped unit tests (synthetic callbacks never native)."""
import json, sqlite3, tempfile, unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject,digest
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import (
    OriginalAccessGatedV1,original_execution_access_for_choice,ORIGINAL_A1D_SHA)
from research.spk_v5_t13_macro_original_access_guard.macro_gate import run_scenario, report


def good(c,g):return {'kind':'TEST_ONLY','choice':c,'goal':g,'original_learning_P_grants':0}

def reject(f):
    try:f()
    except (ValueError,sqlite3.DatabaseError,RuntimeError,OSError):return True
    return False

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='spk-t13-test-')
        self.p=Path(self.tmp.name)/'state.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def engine(self,callback=good,**kw):
        return OriginalAccessGatedV1(self.p,root='.',test_witness=callback,test_only=True,**kw)
    def prior(self,e):
        return (tuple(e.db.execute('SELECT cue,choice,version,budget FROM p WHERE cue=0').fetchone()),
                e.db.execute('SELECT count(*) FROM p_grant').fetchone()[0],
                e.db.execute('SELECT count(*) FROM original_access_witness').fetchone()[0])
    def one(self,e,cue=0,goal=11):
        e.submit(cue,goal)
        for _ in range(4):e.step()
    def test_01_positive_live_commit(self):
        e=self.engine();self.one(e);v=e.step();self.assertEqual(v['kind'],'SEM_B_C')
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],1)
        self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);e.close()
    def test_02_reopen_receipt_same(self):
        e=self.engine();self.one(e);e.step();a=e.audit_original_access();e.reopen()
        self.assertEqual(a,e.audit_original_access());e.close()
    def test_03_no_callback_without_test_flag(self):
        self.assertTrue(reject(lambda:OriginalAccessGatedV1(self.p,test_witness=good)))
    def test_04_test_mode_requires_callable(self):
        self.assertTrue(reject(lambda:OriginalAccessGatedV1(self.p,test_only=True)))
    def test_05_missing_original_source_denied_in_strict_mode(self):
        e=OriginalAccessGatedV1(self.p,root=self.tmp.name);self.one(e);before=self.prior(e)
        self.assertTrue(reject(e.step));self.assertEqual(before,self.prior(e))
        self.assertEqual(e.audit_original_access()['original_access_witnesses'],0);e.close()
    def test_06_bad_source_kind(self):
        e=self.engine(lambda c,g:{**good(c,g),'kind':'ORIGINAL_A1D_EXECUTION_ACCESS'})
        self.one(e);p=self.prior(e);self.assertTrue(reject(e.step));self.assertEqual(p,self.prior(e));e.close()
    def test_07_wrong_choice_binding(self):
        e=self.engine(lambda c,g:{**good(c,g),'choice':12 if c==11 else 11})
        self.one(e);self.assertTrue(reject(e.step));e.close()
    def test_08_wrong_goal_binding(self):
        e=self.engine(lambda c,g:{**good(c,g),'goal':12 if g==11 else 11})
        self.one(e);self.assertTrue(reject(e.step));e.close()
    def test_09_forged_original_learning_grant(self):
        e=self.engine(lambda c,g:{**good(c,g),'original_learning_P_grants':1})
        self.one(e);self.assertTrue(reject(e.step));e.close()
    def test_10_non_dict_witness(self):
        e=self.engine(lambda c,g:True);self.one(e);self.assertTrue(reject(e.step));e.close()
    def test_11_witness_exception_denied(self):
        def broken(c,g):raise ValueError('SOURCE_REJECTED')
        e=self.engine(broken);self.one(e);self.assertTrue(reject(e.step))
        self.assertIn('SOURCE_REJECTED',e.last_original_denial);e.close()
    def test_12_denial_event_queued_and_recovery(self):
        enabled=[False]
        def candidate(c,g):
            if not enabled[0]:raise ValueError('INACCESSIBLE')
            return good(c,g)
        e=self.engine(candidate);self.one(e);p=self.prior(e)
        self.assertTrue(reject(e.step));self.assertEqual(p,self.prior(e))
        self.assertEqual(e.db.execute("SELECT count(*) FROM event WHERE kind='SEM_B_C' AND status='QUEUED'").fetchone()[0],1)
        enabled[0]=True;e.reopen();e.step();self.assertEqual(e.audit_original_access()['test_only_witnesses'],1)
        self.assertIsNone(e.step());e.close()
    def test_13_same_policy_version_only_one_credit(self):
        e=self.engine(max_inflight=3);e.submit(0,11);e.submit(0,11);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],1)
        self.assertEqual(e.audit()['stale_vetoes'],1);e.close()
    def test_14_separate_contexts_both_credit(self):
        e=self.engine();e.submit(0,11);e.submit(1,12);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],2);e.close()
    def test_15_matching_goal_correct_emits_no_grant(self):
        e=self.engine();e.submit(0,12);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],0);e.close()
    def test_16_lost_feedback_never_certified(self):
        e=self.engine();e.submit(0,11,drop_feedback=True);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],0);e.close()
    def test_17_drop_forward_no_original(self):
        e=self.engine();e.submit(0,11,drop_forward=True);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],0);e.close()
    def test_18_deadline_no_original(self):
        e=self.engine();e.submit(0,11,feedback_delay=6);e.run()
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],0);e.close()
    def test_19_verify_mode_denies(self):
        e=self.engine();e.transition_authority(expected_revision=0,mode='verify')
        self.one(e);self.assertTrue(reject(e.step))
        self.assertEqual(e.audit_original_access()['test_only_witnesses'],0);e.close()
    def test_20_zero_budget_denies(self):
        e=self.engine(global_ceiling=0,context_ceiling=0)
        self.one(e);self.assertTrue(reject(e.step));self.assertEqual(self.prior(e)[1:],(0,0));e.close()
    def test_21_direct_update_denied(self):
        e=self.engine();self.assertTrue(reject(lambda:e.db.execute('UPDATE p SET choice=11 WHERE cue=0')));e.close()
    def test_22_invalid_test_to_production_reopen(self):
        e=self.engine();self.one(e);e.step();e.close()
        self.assertTrue(reject(lambda:OriginalAccessGatedV1(self.p,create=False)))
    def test_23_tamper_original_witness_detected(self):
        e=self.engine();self.one(e);e.step()
        e.db.execute("UPDATE original_access_witness SET event_digest=?",('f'*64,))
        self.assertTrue(reject(e.audit_original_access));e.close()
    def test_24_tamper_schema_trigger_detected(self):
        e=self.engine();e.db.execute('DROP TRIGGER spk_t13_original_access_witness')
        self.assertTrue(reject(e.audit_original_access));e.close()
    def test_25_tamper_policy_mode_detected(self):
        e=self.engine();e.db.execute("UPDATE original_access_policy SET proof_kind='ORIGINAL_A1D_EXECUTION_ACCESS'")
        self.assertTrue(reject(e.audit_original_access));e.close()
    def test_26_unearned_receipt_rejected(self):
        e=self.engine();self.assertTrue(reject(lambda:e.db.execute("INSERT INTO reference_provider_receipt VALUES(0,0,0,0,'f','REFERENCE_PROVIDER_V1')")));e.close()
    def test_27_test_only_status_no_promotion(self):
        e=self.engine();self.one(e);e.step();x=e.audit_original_access()
        self.assertEqual((x['original_access_witnesses'],x['original_A1d_executions_for_witnesses'],x['original_learning_P_grants']), (0,0,0));e.close()
    def test_28_local_source_absence_explicit(self):
        self.assertTrue(reject(lambda:original_execution_access_for_choice(self.tmp.name,12,11)))
    def test_29_serial_parity(self):
        s=run_scenario('.',strategy='serial',test_callback=good)
        self.assertEqual((s['successes'],s['waves'],s['reference_P_grants']),(88,96,8))
    def test_30_parallel_parity(self):
        s=run_scenario('.',strategy='batch3',test_callback=good)
        self.assertEqual((s['successes'],s['stale_vetoes'],s['reference_P_grants']),(84,4,8))
    def test_31_affinity_parity(self):
        s=run_scenario('.',strategy='context_affinity',test_callback=good)
        self.assertEqual((s['successes'],s['stale_vetoes'],s['waves']),(88,0,48))
    def test_32_recovery_parity(self):
        s=run_scenario('.',strategy='context_affinity',test_callback=good,reopen=True)
        self.assertEqual((s['successes'],s['original_witness']['test_only_witnesses']),(88,8))
    def test_33_local_report_not_original(self):
        r=report('.',strict=False)
        self.assertFalse(r['production_original_A1d_invoked_during_C_tick'])
        self.assertTrue(r['M3_reference_v1_runtime']['test_only'])
        self.assertEqual(r['M5_boundary']['original_P_learning_grants'],0)
    def test_34_never_count_original_in_controlled_test(self):
        e=self.engine();self.one(e);e.step();r=e.audit_original_access()
        self.assertEqual(r['witness_kind'],'TEST_ONLY');self.assertTrue(r['host_can_forge']);e.close()
    def test_35_reference_event_rollback_has_no_settled_grant(self):
        e=self.engine(lambda c,g:{**good(c,g),'original_learning_P_grants':1})
        self.one(e);self.assertTrue(reject(e.step))
        self.assertEqual(e.db.execute("SELECT COUNT(*) FROM episode WHERE status='SETTLED'").fetchone()[0],0)
        self.assertEqual(e.db.execute("SELECT COUNT(*) FROM ledger WHERE kind='GRANT_P'").fetchone()[0],0);e.close()

if __name__=='__main__':unittest.main()
