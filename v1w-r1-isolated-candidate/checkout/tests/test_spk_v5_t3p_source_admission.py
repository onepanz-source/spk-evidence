import unittest
from dataclasses import replace
from spk_v5_research.island_c_owned_credit_v5t3h import Measurement,CreditAdmissionError
from spk_v5_research.island_online_credit_v5t3i import packet_for
from spk_v5_research.island_source_admission_v5t3p import (SourceGatedPolicy,receipt_for,verify_receipt)
ST=('2026-10-22 12:00:00','2026-10-22 12:01:00')
def m(**kw):return Measurement(*ST,350,350,850,**kw)
def start():
 x=SourceGatedPolicy(seed=71);arm=x.decide('e0',350,350,0);p=packet_for('e0',arm,m(),0)
 return x,p

class SourcePolicyAdmission(unittest.TestCase):
 def test_admit_and_settle(self):
  x,p=start();self.assertTrue(x.submit(p));self.assertEqual(x.settle(p.packet_id,1),p.witness['A_consumed_credit']);self.assertEqual(x.audit()['registry']['updates'],1)
 def test_source_positive(self):
  x,p=start();self.assertTrue(verify_receipt(p,receipt_for(p)))
 def test_exactly_once(self):
  x,p=start();x.submit(p);x.settle(p.packet_id,1)
  with self.assertRaises(CreditAdmissionError):x.settle(p.packet_id,2)
 def test_settle_not_before_arrival(self):
  x,p=start();x.submit(p)
  with self.assertRaises(CreditAdmissionError):x.settle(p.packet_id,0)
 def test_reject_modified_bv_ancestry_before_register(self):
  x,p=start();r=receipt_for(p);r.source_evidence['dual_frozen_BV_v0e_source_passes']['30']['deliveries'].append(('X','A',30,True))
  before=x.audit()['registry']['head_sha256']
  with self.assertRaises(CreditAdmissionError):x.submit(p,r)
  self.assertEqual(x.audit()['registry']['head_sha256'],before)
 def test_reject_forged_receipt_commit(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,replace(receipt_for(p),commitment_hash='0'*64))
 def test_reject_wrong_actor(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,replace(receipt_for(p),episode_id='another'))
 def test_reject_wrong_action(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,replace(receipt_for(p),arm='silent' if p.action!='silent' else 'current'))
 def test_reject_wrong_measured_hash(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,replace(receipt_for(p),measurement_hash='0'*64))
 def test_reject_wrong_packet_id(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,replace(receipt_for(p),packet_id='other'))
 def test_reject_missing_credential(self):
  x,p=start()
  with self.assertRaises(CreditAdmissionError):x.submit(p,{})
 def test_missing_sensor_no_update(self):
  x,p=start();bad=replace(p.measurement,co2_current=None,sensor_visible=False)
  p=packet_for('e0',p.action,bad,0)
  self.assertFalse(x.submit(p));self.assertEqual(x.audit()['registry']['updates'],0)
 def test_forward_loss_no_update(self):
  x,p=start();p=packet_for('e0',p.action,replace(p.measurement,forward_enabled=False),0)
  self.assertFalse(x.submit(p));self.assertEqual(x.audit()['registry']['updates'],0)
 def test_reverse_loss_no_update(self):
  x,p=start();p=packet_for('e0',p.action,replace(p.measurement,reverse_enabled=False),0)
  self.assertFalse(x.submit(p));self.assertEqual(x.audit()['registry']['updates'],0)
 def test_missing_marker_no_update(self):
  x,p=start();p=packet_for('e0',p.action,replace(p.measurement,send_decision=False),0)
  self.assertFalse(x.submit(p));self.assertEqual(x.audit()['registry']['updates'],0)
 def test_replay_submit_blocked(self):
  x,p=start();x.submit(p)
  with self.assertRaises(CreditAdmissionError):x.submit(p)
 def test_pending_receipt_auditable(self):
  x,p=start();x.submit(p)
  self.assertEqual(x.audit()['source_receipts_pending'],1)
 def test_post_registration_source_tamper_blocked(self):
  x,p=start();x.submit(p)
  x._receipts[p.packet_id].source_evidence['dual_frozen_BV_v0e_source_passes']['30']['grant_count']=0
  with self.assertRaises(CreditAdmissionError):x.settle(p.packet_id,1)
  self.assertEqual(x.audit()['registry']['updates'],0)
 def test_event_digest_replay(self):
  x,p=start();x.submit(p);x.settle(p.packet_id,1)
  a=x.audit()['registry']['head_sha256'];self.assertEqual(a,x.audit()['registry']['head_sha256'])
 def test_early_mint_rejected(self):
  x,p=start();self.assertFalse(x.audit()['registry']['updates']);
  with self.assertRaises(CreditAdmissionError):x.settle('unissued',1)
 def test_admission_requires_host_separate_decision(self):
  x=SourceGatedPolicy();p=packet_for('rogue','current',m(),0)
  with self.assertRaises(CreditAdmissionError):x.submit(p)
 def test_host_not_native(self):
  x,p=start();x.submit(p);self.assertFalse(x.audit()['native_learning']);self.assertFalse(x.audit()['native_BV_semantic_credit'])
