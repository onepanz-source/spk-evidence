import unittest
from dataclasses import replace
from spk_v5_research.island_c_owned_credit_v5t3h import Measurement,CreditAdmissionError
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy,packet_for,context_of,digest

P='2026-10-22 12:00:00';Q='2026-10-22 12:01:00'

class T3iCreditCustody(unittest.TestCase):
 def setUp(self):
  self.a=OnlinePolicy(seed=1,exploration=0)
  self.m=Measurement(P,Q,12.,350.,850.)
 def elected(self,eid='e',idx=0,m=None,kw=None):
  m=m or self.m
  a=self.a.decide(eid,m.previous_light,m.current_light,idx)
  p=packet_for(eid,a,m,idx,**(kw or {}))
  self.a.register(p)
  return p
 def assertRejected(self,fn):
  before=(self.a.updates,len(self.a.pending),self.a.head,len(self.a.issued),len(self.a.closed))
  with self.assertRaises(CreditAdmissionError):fn()
  self.assertEqual(before,(self.a.updates,len(self.a.pending),self.a.head,len(self.a.issued),len(self.a.closed)))
 def test_all_contexts(self):
  self.assertEqual([context_of(i,j) for i,j in ((0,0),(0,200),(200,0),(200,200))],['00','01','10','11'])
 def test_causal_selection_determinism(self):
  self.assertEqual(OnlinePolicy(2).choose(0,300),OnlinePolicy(2).choose(0,300))
 def test_selection_no_C_arg(self):
  self.assertEqual(self.a.choose(0,300),self.a.choose(0,300))
 def test_basic_update(self):
  p=self.elected();self.assertEqual(p.witness['status'],'C_authored_credit_delivered')
  self.assertEqual(self.a.settle(p.packet_id,1),1)
  self.assertEqual(self.a.updates,1);self.assertEqual(self.a.audit()['updates'],1)
 def test_negative_credit_real(self):
  m=replace(self.m,co2_current=450.)
  p=self.elected(m=m);self.assertEqual(self.a.settle(p.packet_id,1),-1)
 def test_decision_precommitted(self):
  self.elected();self.assertEqual(self.a.ledger[0]['entry']['kind'],'A_program_committed_before_C_sensor')
 def test_early_delivery(self):
  p=self.elected(kw={'delay':2});self.assertRejected(lambda:self.a.settle(p.packet_id,1))
  self.a.settle(p.packet_id,3)
 def test_duplicate_receipt(self):
  p=self.elected();self.a.settle(p.packet_id,1)
  self.assertRejected(lambda:self.a.settle(p.packet_id,2))
 def test_duplicate_decision(self):
  p=self.elected();self.assertRejected(lambda:self.a.register(p))
 def test_replayed_episode_id(self):
  self.elected();self.assertRejected(lambda:self.a.decide('e',12.,350.,2))
 def test_no_unsigned_packet(self):
  self.assertRejected(lambda:self.a.register(object()))
 def test_program_swap(self):
  arm=self.a.decide('x',12.,350.,0)
  other='silent' if arm!='silent' else 'current'
  p=packet_for('x',other,self.m,0)
  self.assertRejected(lambda:self.a.register(p))
 def test_proof_forgery(self):
  arm=self.a.decide('x',12.,350.,0);p=packet_for('x',arm,self.m,0)
  proof={**p.witness,'A_consumed_credit':-1}
  self.assertRejected(lambda:self.a.register(replace(p,witness=proof)))
 def test_identity_forgery(self):
  arm=self.a.decide('x',12.,350.,0);p=packet_for('x',arm,self.m,0)
  self.assertRejected(lambda:self.a.register(replace(p,packet_id='0'*64)))
 def test_wrong_timestamp_receipt(self):
  arm=self.a.decide('x',12.,350.,0);p=packet_for('x',arm,self.m,0)
  self.assertRejected(lambda:self.a.register(replace(p,arrival_step=-1)))
 def test_too_late(self):
  p=self.elected();self.assertRejected(lambda:self.a.settle(p.packet_id,9))
  self.a.expire(p.packet_id,9,'deadline_exceeded');self.assertEqual(self.a.updates,0)
 def test_missing_c_no_update(self):
  m=replace(self.m,co2_current=None,sensor_visible=False)
  p=self.elected(m=m);self.assertNotIn(p.packet_id,self.a.pending);self.assertEqual(self.a.audit()['updates'],0)
 def test_reverse_loss_no_update(self):
  m=replace(self.m,reverse_enabled=False)
  p=self.elected(m=m);self.assertNotIn(p.packet_id,self.a.pending)
 def test_forward_loss_no_update(self):
  m=replace(self.m,forward_enabled=False)
  p=self.elected(m=m);self.assertNotIn(p.packet_id,self.a.pending)
 def test_missing_decision_no_update(self):
  m=replace(self.m,send_decision=False)
  p=self.elected(m=m);self.assertNotIn(p.packet_id,self.a.pending)
 def test_discard_prevents_update(self):
  p=self.elected();self.a.expire(p.packet_id,0,'modeled_relay_loss')
  self.assertRejected(lambda:self.a.settle(p.packet_id,1));self.assertEqual(self.a.audit()['updates'],0)
 def test_ledger_tamper(self):
  p=self.elected();self.a.settle(p.packet_id,1)
  self.a.ledger[0]['entry']['arm']='silent'
  with self.assertRaises(CreditAdmissionError):self.a.audit()
 def test_weight_tamper(self):
  p=self.elected();self.a.settle(p.packet_id,1)
  self.a.q['01'][p.action]=.88
  with self.assertRaises(CreditAdmissionError):self.a.audit()
 def test_history_old_weight_tamper(self):
  p=self.elected();self.a.settle(p.packet_id,1)
  self.a.ledger[-1]['entry']['old']=.8
  with self.assertRaises(CreditAdmissionError):self.a.audit()
 def test_nan_context(self):
  for v in (float('nan'),float('inf'),-1.,True):
   with self.subTest(v=str(v)),self.assertRaises(CreditAdmissionError):context_of(v,350.)
 def test_delay_limit(self):
  with self.assertRaises(CreditAdmissionError):packet_for('e','current',self.m,0,7)
 def test_hash_determinism(self):
  self.assertEqual(digest({'a':1,'b':2}),digest({'b':2,'a':1}))

if __name__=='__main__':unittest.main()
