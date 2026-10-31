import unittest
from dataclasses import replace
from spk_v5_research.island_c_owned_credit_v5t3h import Measurement,execute,CreditAdmissionError
from spk_v5_research.island_source_bv_bridge_v5t3o import evidence,verify_evidence,mirrored_case

ST=('2026-10-22 12:00:00','2026-10-22 12:01:00')
def m(prev=350,now=350,co2=850,**kw):return Measurement(*ST,prev,now,co2,**kw)

class SourceTerminalMirror(unittest.TestCase):
 def test_positive_source_BV_to_A(self):
  x=evidence(m(),'persist');self.assertTrue(x['source_chain_C_to_B_to_A_valid'])
  self.assertEqual(x['terminal_verdict_sign'],1)
  self.assertEqual(x['dual_frozen_BV_v0e_source_passes']['30']['grant_count'],2)
 def test_negative_source_BV_to_A(self):
  x=evidence(m(co2=420),'persist');self.assertTrue(x['source_chain_C_to_B_to_A_valid'])
  self.assertEqual(x['terminal_verdict_sign'],-1)
  self.assertEqual(x['dual_frozen_BV_v0e_source_passes']['31']['grant_count'],2)
 def test_opposite_sign_not_minted(self):
  x=evidence(m(),'persist');self.assertEqual(x['dual_frozen_BV_v0e_source_passes']['31']['grant_count'],0)
 def test_ancestry_is_source_bv(self):
  x=evidence(m(),'persist');a=x['dual_frozen_BV_v0e_source_passes']['30']
  self.assertTrue(a['C_parent_occurrences']);self.assertEqual([v[:2] for v in a['deliveries']],[('C','B'),('B','A')])
 def test_source_resources_are_charged(self):
  x=evidence(m(),'persist');a=x['dual_frozen_BV_v0e_source_passes']['30']
  self.assertEqual(a['resource_memory_units'],4);self.assertEqual(a['resource_service_units'],2)
 def test_programs_do_not_modify_source(self):
  original=execute(m(),'current');mir=mirrored_case(m(),'current')
  self.assertEqual(tuple(n.instructions for n in mir.nodes[:2]),tuple(n.instructions for n in __import__('spk_v5_research.island_c_owned_credit_v5t3h',fromlist=['build_case']).build_case(m(),'current').nodes[:2]))
  self.assertEqual(original['C_computed_verdict'],1)
 def test_close_is_marker_timed(self):
  self.assertEqual([x.timestamp for x in mirrored_case(m(),'current').events if x.node_id=='C' and x.channel==6],[14])
 def test_source_cannot_mint_no_C(self):
  x=evidence(m(co2=None,sensor_visible=False),'current')
  self.assertFalse(x['source_chain_C_to_B_to_A_valid'])
 def test_source_cannot_mint_no_marker(self):
  x=evidence(m(send_decision=False),'current')
  self.assertFalse(x['source_chain_C_to_B_to_A_valid'])
 def test_source_cannot_mint_no_forward(self):
  x=evidence(m(forward_enabled=False),'current')
  self.assertFalse(x['source_chain_C_to_B_to_A_valid'])
 def test_source_cannot_override_lost_semantic_return(self):
  x=evidence(m(reverse_enabled=False),'current')
  self.assertFalse(x['source_chain_C_to_B_to_A_valid'])
 def test_no_silent_action_confusion(self):
  x=evidence(m(now=350,co2=850),'silent')
  self.assertEqual(x['terminal_verdict_sign'],-1)
  self.assertTrue(x['source_chain_C_to_B_to_A_valid'])
 def test_no_false_negative_credit(self):
  x=evidence(m(now=15,co2=420),'current');self.assertEqual(x['terminal_verdict_sign'],1)
 def test_all_arm_contexts(self):
  for prev in (15,350):
   for now in (15,350):
    for co2 in (420,850):
     for arm in ('current','persist','silent'):
      with self.subTest(prev=prev,now=now,co2=co2,arm=arm):
       x=evidence(m(prev,now,co2),arm)
       self.assertTrue(x['source_chain_C_to_B_to_A_valid'])
       self.assertEqual(x['terminal_verdict_sign'],execute(m(prev,now,co2),arm)['C_computed_verdict'])
 def test_verify_intact(self):self.assertTrue(verify_evidence(m(),'persist',evidence(m(),'persist')))
 def test_reject_modified_verdict(self):
  x=evidence(m(),'persist');x['terminal_verdict_sign']=-1
  with self.assertRaises(CreditAdmissionError):verify_evidence(m(),'persist',x)
 def test_reject_swapped_receiver(self):
  x=evidence(m(),'persist');x['dual_frozen_BV_v0e_source_passes']['30']['deliveries'][1]=('B','Z',16,True)
  with self.assertRaises(CreditAdmissionError):verify_evidence(m(),'persist',x)
 def test_reject_forged_grant(self):
  x=evidence(m(),'persist');x['dual_frozen_BV_v0e_source_passes']['30']['grant_count']=123
  with self.assertRaises(CreditAdmissionError):verify_evidence(m(),'persist',x)
 def test_reject_wrong_sensor(self):
  x=evidence(m(),'persist')
  with self.assertRaises(CreditAdmissionError):verify_evidence(m(co2=420),'persist',x)
 def test_invalid_physical_gap(self):
  with self.assertRaises(CreditAdmissionError):evidence(replace(m(),current_stamp='2026-10-22 12:02:00'),'persist')
 def test_reject_claim_type(self):
  with self.assertRaises(CreditAdmissionError):verify_evidence(m(),'persist',None)
 def test_two_channel_observer_not_native_single_pass(self):
  x=evidence(m(),'persist');self.assertTrue(x['not_single_pass_native_BV'])
  self.assertTrue(x['no_native_semantic_BV_credit'])
