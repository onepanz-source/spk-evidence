from __future__ import annotations
import json,sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject
from research.spk_v5_t10stu_vwx_yza.surface_probe_v0 import read_only_contract_request,reject_native_promotion
from research.spk_v5_t11_macro_memory_v1.memory_authority_v1 import OwnedMemoryV1
from research.spk_v5_t11_macro_memory_v1.macro_gate import scenario,adversarial

class OwnedMemoryContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/'runtime.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def engine(self,**kw):return OwnedMemoryV1(self.db,**kw)
    def test_empty_ledger(self):
        e=self.engine();a=e.audit_owned_memory();self.assertEqual(a['new_v1_memory_grants'],0);e.close()
    def test_actual_negative_feedback_commit(self):
        e=self.engine();e.submit(0,11);e.run();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);e.close()
    def test_positive_feedback_no_grant(self):
        e=self.engine();e.submit(0,12);e.run();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],0);e.close()
    def test_other_context_grants_independent(self):
        e=self.engine();e.submit(0,11);e.run();e.submit(1,12);e.run();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],2);e.close()
    def test_memory_scope_fields(self):
        e=self.engine();p=e.policy();self.assertEqual((p['owner'],p['domain'],p['pe_id'],p['mode']),('C','P','PE-C-RESEARCH','execute'));e.close()
    def test_single_use_grant_receipt(self):
        e=self.engine();e.submit(0,11);e.run();rows=list(e.db.execute('SELECT * FROM v1_owned_memory_grant'));self.assertEqual(len(rows),1);self.assertEqual(rows[0]['expected_version'],0);e.close()
    def test_exact_grant_lineage(self):
        e=self.engine();e.submit(0,11);e.run();g=e.db.execute('SELECT * FROM v1_owned_memory_grant').fetchone();r=e.db.execute('SELECT * FROM reference_provider_receipt').fetchone();self.assertEqual((g['grant_id'],g['event_id'],g['event_digest']),(r['grant_id'],r['event_id'],r['event_digest']));e.close()
    def test_direct_P_write_denied(self):
        e=self.engine();
        with self.assertRaises(sqlite3.DatabaseError):e.db.execute('UPDATE p SET choice=11 WHERE cue=0')
        e.close()
    def test_no_insert_P(self):
        e=self.engine();
        with self.assertRaises(sqlite3.DatabaseError):e.db.execute('INSERT INTO p VALUES(2,11,0,2)')
        e.close()
    def test_no_delete_P(self):
        e=self.engine();
        with self.assertRaises(sqlite3.DatabaseError):e.db.execute('DELETE FROM p WHERE cue=0')
        e.close()
    def test_zero_global_capacity_fails_closed(self):
        e=self.engine(global_ceiling=0);e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],0);e.close()
    def test_zero_context_capacity_fails_closed(self):
        e=self.engine(context_ceiling=0);e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],0);e.close()
    def test_denied_transaction_keeps_event_queued(self):
        e=self.engine(global_ceiling=0);e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        self.assertEqual(e.db.execute("SELECT COUNT(*) FROM event WHERE status='QUEUED'").fetchone()[0],1);e.close()
    def test_resource_expansion_recovers_once(self):
        e=self.engine(global_ceiling=0,context_ceiling=0);e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        e.reopen();e.transition_authority(expected_revision=0,global_ceiling=1,context_ceiling=1);e.step();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);e.close()
    def test_reopen_maintains_grant(self):
        e=self.engine();e.submit(0,11);e.run();before=e.audit_owned_memory();e.reopen();self.assertEqual(before,e.audit_owned_memory());e.close()
    def test_reopened_credit_not_duplicated(self):
        e=self.engine();e.submit(0,11);e.run();e.reopen();e.run();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);e.close()
    def test_verify_mode_refuses(self):
        e=self.engine();e.transition_authority(expected_revision=0,mode='verify');e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        e.close()
    def test_verify_to_execute_recovers(self):
        e=self.engine();e.transition_authority(expected_revision=0,mode='verify');e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        e.transition_authority(expected_revision=1,mode='execute');e.step();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);e.close()
    def test_profile_revision_stale_denied(self):
        e=self.engine()
        with self.assertRaises(Reject):e.transition_authority(expected_revision=7,mode='verify')
        e.close()
    def test_retrospective_capacity_shrink_denied(self):
        e=self.engine();e.submit(0,11);e.run()
        with self.assertRaises(Reject):e.transition_authority(expected_revision=0,global_ceiling=0)
        e.close()
    def test_disabled_authority_no_credit(self):
        e=self.engine();e.authority_enabled=False;e.submit(0,11)
        for _ in range(4):e.step()
        with self.assertRaises(sqlite3.DatabaseError):e.step()
        self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],0);e.close()
    def test_same_version_credit_once(self):
        e=self.engine(max_inflight=3);e.submit(0,11);e.submit(0,11);e.run();self.assertEqual(e.audit_owned_memory()['new_v1_memory_grants'],1);self.assertEqual(e.audit()['stale_vetoes'],1);e.close()
    def test_trigger_drift_rejected(self):
        e=self.engine();e.db.execute('DROP TRIGGER spk_new_v1_owned_memory_grant')
        with self.assertRaises(Reject):e.audit_owned_memory()
        e.close()
    def test_trigger_drift_reopen_rejected(self):
        e=self.engine();e.db.execute('DROP TRIGGER spk_new_v1_owned_memory_grant');e.close()
        with self.assertRaises(Reject):self.engine(create=False)
    def test_resource_grant_provider_equal(self):
        e=self.engine();e.submit(0,11);e.run();a=e.audit_owned_memory();self.assertEqual(a['new_v1_memory_grants'],e.audit_provider()['provider_v1_authorizations']);e.close()
    def test_frozen_native_zero(self):
        e=self.engine();e.submit(0,11);e.run();a=e.audit_owned_memory();self.assertEqual(a['native_frozen_SPK_grants'],0);self.assertFalse(a['original_memory_contract_called']);e.close()
    def test_reference_receipt_doesnt_become_native(self):
        r=read_only_contract_request(owner='C',domain='P',mode='execute',pe_id='PE-C-RESEARCH',context=1,version=2)
        self.assertFalse(reject_native_promotion(r['request'],{'native':True})['promotion_allowed'])
    def test_adversarial_macro(self):self.assertTrue(adversarial()['host_native_claim_rejected'])

# Independent inputs to guard against accidental broadening to unsupported
# ownership, memory domain, operating mode, context or PE.
for i,changes in enumerate([
    {'owner':'A'},{'owner':'D'},{'domain':'S'},{'domain':'E'},
    {'domain':'O'},{'mode':'verify'},{'mode':'remodel'},
    {'mode':'train'},{'pe_id':'PE-A'},{'pe_id':'PE-C'},
    {'context':-1},{'context':2},{'version':-1},
]):
    def test(self,mod=changes):
        request={'owner':'C','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':0}
        request.update(mod)
        with self.assertRaises(Reject):read_only_contract_request(**request)
    setattr(OwnedMemoryContractTests,f'test_scope_reject_{i:02d}',test)

class FullWorkloadTests(unittest.TestCase):
    def test_frozen_research_control_parity(self):self.assertEqual((scenario('batch3',learn=False)['successes'],scenario('batch3',learn=False)['reference_P_grants']),(48,0))
    def test_three_inflight_parity(self):
        r=scenario('batch3');self.assertEqual((r['successes'],r['stale_vetoes'],r['owned_memory']['new_v1_memory_grants']),(84,4,8))
    def test_affinity_parity(self):
        r=scenario('context_affinity');self.assertEqual((r['successes'],r['waves'],r['owned_memory']['new_v1_memory_grants']),(88,48,8))
    def test_serial_parity(self):
        r=scenario('serial');self.assertEqual((r['successes'],r['waves'],r['owned_memory']['new_v1_memory_grants']),(88,96,8))
    def test_restart_affinity_parity(self):
        a=scenario('context_affinity');b=scenario('context_affinity',reopen=True);self.assertEqual(a['owned_memory'],b['owned_memory'])
    def test_workload_immutable_source(self):
        from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import tasks
        t=tasks();self.assertEqual(len(t),96);self.assertEqual({x[0] for x in t},{0,1})

if __name__=='__main__':unittest.main()
