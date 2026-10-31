"""Adversarial, origin-isolation and recovery tests. Lab signer is NOT authentic A."""
import base64,hashlib,json,sqlite3,subprocess,tempfile,unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject
from research.spk_v5_t14_macro_signed_source.signed_boundary_v1 import (
 SignedSourceGatedV1,sign_detached_for_lab,verify_detached,public_der_from_pem,SCHEMA)
from research.spk_v5_t14_macro_signed_source.macro_gate import (
 laboratory_keys,missing_receipt_counterexample,scenario,report)

ROOT=Path(__file__).resolve().parents[3]

def witness(choice,goal):
 return {'kind':'TEST_ONLY','choice':choice,'goal':goal,'original_learning_P_grants':0}

class SignedBoundary(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.dir=Path(self.tmp.name)
  self.private,self.public=laboratory_keys(self.dir)
  self.engine=SignedSourceGatedV1(self.dir/'db.sqlite',public_key_pem=self.public,
      root=ROOT,test_only=True,test_witness=witness)
  self.addCleanup(lambda: self.engine.close())
 def stage(self,cue=0,goal=11):
  ep=self.engine.submit(cue,goal)
  for kind in ('PE_C','PE_B','PE_A'):
   self.assertEqual(self.engine.step()['kind'],kind)
  msg=self.engine.expected_message(ep)
  sig=sign_detached_for_lab(self.private,msg)
  return ep,msg,sig
 def submit_signature(self,ep,msg,sig):
  self.engine.ingest(ep,msg,sig)
  self.engine.run()
  return self.engine.result(ep)
 def test_01_detached_valid(self):
  ep,msg,sig=self.stage();self.assertTrue(verify_detached(self.public,msg,sig))
 def test_02_detached_wrong_payload(self):
  ep,msg,sig=self.stage();self.assertFalse(verify_detached(self.public,msg+b'a',sig))
 def test_03_detached_truncated(self):
  ep,msg,sig=self.stage();self.assertFalse(verify_detached(self.public,msg,sig[:-1]))
 def test_04_der_fingerprint(self):
  self.assertEqual(len(hashlib.sha256(public_der_from_pem(self.public)).hexdigest()),64)
 def test_05_signed_receipt_commit(self):
  ep,msg,sig=self.stage();r=self.submit_signature(ep,msg,sig)
  self.assertEqual(r['grant'],0);self.assertEqual(self.engine.audit_signed_source()['signed_P_grants'],1)
 def test_06_no_receipt_rolls_back(self):
  self.stage();self.assertEqual(self.engine.step()['kind'],'SEM_A_B')
  with self.assertRaises(sqlite3.IntegrityError):self.engine.step()
  self.assertEqual(self.engine.db.execute('SELECT COUNT(*) FROM p_grant').fetchone()[0],0)
 def test_07_unsigned_pending_C(self):
  self.stage();self.engine.step()
  with self.assertRaises(sqlite3.IntegrityError):self.engine.step()
  self.assertEqual(self.engine.db.execute("SELECT COUNT(*) FROM event WHERE kind='SEM_B_C' AND status='QUEUED'").fetchone()[0],1)
 def test_08_corrupted_signature_denied(self):
  ep,msg,sig=self.stage()
  with self.assertRaises(Reject):self.engine.ingest(ep,msg,bytes(64))
 def test_09_wrong_goal_payload(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['goal']=12
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_10_wrong_version_payload(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['expected_P_version']=42
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_11_wrong_event_hash(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['A_event_digest']='0'*64
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_12_wrong_A_PE_digest(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['A_PE_digest']='0'*64
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_13_wrong_cue_payload(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['cue']=1
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_14_wrong_issuer(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['issuer']='HOST'
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_15_wrong_epoch(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['episode_id']=44
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_16_wrong_nonce(self):
  ep,msg,sig=self.stage();p=json.loads(msg);p['nonce']='f'*64
  with self.assertRaises(Reject):self.engine.ingest(ep,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sig)
 def test_17_replay_same_receipt(self):
  ep,msg,sig=self.stage();self.engine.ingest(ep,msg,sig)
  with self.assertRaises(Reject):self.engine.ingest(ep,msg,sig)
 def test_18_cross_key(self):
  ep,msg,sig=self.stage()
  other=self.dir/'other';other.mkdir();priv2,pub2=laboratory_keys(other)
  wrong=sign_detached_for_lab(priv2,msg)
  with self.assertRaises(Reject):self.engine.ingest(ep,msg,wrong)
 def test_19_reopen_key_mismatch(self):
  self.stage();other=self.dir/'other';other.mkdir();_,pub2=laboratory_keys(other)
  self.engine.close()
  with self.assertRaises(Reject):SignedSourceGatedV1(self.dir/'db.sqlite',public_key_pem=pub2,
      root=ROOT,create=False,test_only=True,test_witness=witness)
  self.engine=SignedSourceGatedV1(self.dir/'db.sqlite',public_key_pem=self.public,
      root=ROOT,create=False,test_only=True,test_witness=witness)
 def test_20_reopen_valid_key(self):
  ep,msg,sig=self.stage();self.engine.reopen();self.assertEqual(self.submit_signature(ep,msg,sig)['grant'],0)
 def test_21_negative_after_restart_then_recovery(self):
  ep,msg,sig=self.stage();self.engine.step()
  with self.assertRaises(sqlite3.IntegrityError):self.engine.step()
  self.engine.reopen();self.assertEqual(self.submit_signature(ep,msg,sig)['grant'],0)
 def test_22_late_settled_attestation(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig)
  with self.assertRaises(Reject):self.engine.ingest(ep,msg,sig)
 def test_23_sign_same_after_restart(self):
  ep,msg,sig=self.stage();self.engine.reopen();self.assertEqual(msg,self.engine.expected_message(ep))
 def test_24_direct_P_update_denied(self):
  ep,msg,sig=self.stage()
  with self.assertRaises(sqlite3.DatabaseError):self.engine.db.execute('UPDATE p SET version=4 WHERE cue=0')
 def test_25_trigger_drop_detected(self):
  self.engine.db.execute('DROP TRIGGER spk_t14_signed_source_grant')
  with self.assertRaises(Reject):self.engine.audit_signed_source()
 def test_26_payload_tamper_detected(self):
  ep,msg,sig=self.stage();self.engine.ingest(ep,msg,sig)
  self.engine.db.execute('UPDATE t14_attestation SET payload_json=? WHERE episode_id=?',('{}',ep))
  with self.assertRaises(Reject):self.engine.audit_signed_source()
 def test_27_sig_tamper_detected(self):
  ep,msg,sig=self.stage();self.engine.ingest(ep,msg,sig)
  self.engine.db.execute('UPDATE t14_attestation SET signature_b64=? WHERE episode_id=?',('AAAA',ep))
  with self.assertRaises(Reject):self.engine.audit_signed_source()
 def test_28_unlinked_receipt_no_credit(self):
  ep,msg,sig=self.stage();self.engine.ingest(ep,msg,sig)
  self.assertEqual(self.engine.audit_signed_source()['signed_P_grants'],0)
 def test_29_grant_link_deleted_detected(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig)
  self.engine.db.execute('DELETE FROM t14_grant_link')
  with self.assertRaises(Reject):self.engine.audit_signed_source()
 def test_30_source_receipt_reopen_audit(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig);self.engine.reopen()
  self.assertEqual(self.engine.audit_signed_source()['signed_receipts_observed'],1)
 def test_31_signature_is_not_sensor_truth(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig)
  self.assertFalse(self.engine.audit_signed_source()['original_source_sensor_authenticated'])
 def test_32_no_private_key_inside_runtime(self):
  self.assertFalse(self.engine.audit_signed_source()['source_private_key_stored_in_runtime'])
 def test_33_inferred_semantic_packet_is_unattested(self):
  ep,msg,sig=self.stage();self.assertIn(b'"issuer":"A-EXTERNAL"',msg)
  self.assertEqual(self.engine.db.execute('SELECT COUNT(*) FROM t14_grant_link').fetchone()[0],0)
 def test_34_second_live_P_grant_double_denied(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig)
  self.assertEqual(self.engine.audit()['reference_v1_tick_grants'],1)
  self.assertIsNone(self.engine.step())
  self.assertEqual(self.engine.audit()['reference_v1_tick_grants'],1)
 def test_35_negative_roll_forward(self):
  evidence=missing_receipt_counterexample(ROOT,strict=False)
  self.assertTrue(evidence['unsigned_negative_receipt_denied_atomically'])
  self.assertEqual(evidence['P_grants_after_valid_signature'],1)
 def test_36_lab_sequence_parity(self):
  r=scenario(ROOT,strict=False)
  self.assertEqual((r['successes'],r['grants'],r['waves']), (88,8,48))
 def test_37_lab_restarted_parity(self):
  r=scenario(ROOT,strict=False,crash_each_wave=True)
  self.assertEqual((r['successes'],r['grants']), (88,8))
 def test_38_attested_only_reference(self):
  ep,msg,sig=self.stage();self.submit_signature(ep,msg,sig)
  self.assertEqual(self.engine.audit_signed_source()['original_learning_P_grants'],0)

if __name__=='__main__':unittest.main()
