import unittest,copy,json
from pathlib import Path
from spk_v5_research.island_goal_nonpromotion_v5t3n import nonpromotion_gate,report,SEEDS,SCHEMA
ROOT=Path(__file__).resolve().parent.parent
class T3nResearchBoundary(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=json.loads((ROOT/'docs/spk-v5-t3lmn-reference.json').read_text()) if (ROOT/'docs/spk-v5-t3lmn-reference.json').is_file() else None
 def test_schema(self):self.assertIn('no-promotion',SCHEMA)
 def test_seed_list(self):self.assertEqual(SEEDS,(11,29,47,83))
 def test_no_native(self):self.assertFalse(self.r['nonpromotion']['native_learning_promotion_allowed'])
 def test_no_blind(self):self.assertFalse(self.r['nonpromotion']['blind_generalization_claim_allowed'])
 def test_no_signed_sensor(self):self.assertFalse(self.r['nonpromotion']['source_sensor_identity_authenticated'])
 def test_no_goal_truth_assumption(self):self.assertFalse(self.r['nonpromotion']['C_credit_genuineness_implies_goal_truth'])
 def test_no_goal_in_A(self):self.assertFalse(self.r['nonpromotion']['goal_label_used_to_choose_A'])
 def test_no_goal_source_promoted(self):self.assertTrue(self.r['public']['posthoc_not_blind'])
 def test_paired_exact(self):
  x=self.r['paired_worlds'];self.assertEqual(len(x),4)
  for p in x:self.assertEqual(p['aligned_world']['correct']+p['inverted_world']['correct'],p['episodes_per_world'])
 def test_result_not_production(self):self.assertTrue(self.r['synthesis']['research_only'])
 def test_empty_pairs_rejected(self):
  with self.assertRaises(ValueError):nonpromotion_gate([],self.r['public'])
 def test_wrong_seed_rejected(self):
  r=copy.deepcopy(self.r['paired_worlds']);r[0]['seed']=999
  with self.assertRaises(ValueError):nonpromotion_gate(r,self.r['public'])
 def test_drifted_head_rejected(self):
  r=copy.deepcopy(self.r['paired_worlds']);r[0]['inverted_world']['A_registry_head_sha256']='0'*64
  with self.assertRaises(ValueError):nonpromotion_gate(r,self.r['public'])
 def test_drifted_success_rejected(self):
  r=copy.deepcopy(self.r['paired_worlds']);r[0]['inverted_world']['correct']+=1
  with self.assertRaises(ValueError):nonpromotion_gate(r,self.r['public'])
 def test_drifted_public_disagreement_rejected(self):
  p=copy.deepcopy(self.r['public']);p['pooled']['misleading_positive']+=1
  with self.assertRaises(ValueError):nonpromotion_gate(self.r['paired_worlds'],p)
 def test_absent_public_rejected(self):
  with self.assertRaises(ValueError):nonpromotion_gate(self.r['paired_worlds'],None)
 def test_wrong_public_number_rejected(self):
  p=copy.deepcopy(self.r['public']);p['files'].pop()
  with self.assertRaises(ValueError):nonpromotion_gate(self.r['paired_worlds'],p)
 def test_integrity_report(self):
  decision=nonpromotion_gate(self.r['paired_worlds'],self.r['public'])
  self.assertEqual(decision,self.r['nonpromotion'])
 def test_synthetic_no_external(self):
  r=report(None,80)
  self.assertIsNone(r['public']);self.assertIsNone(r['nonpromotion'])
 def test_no_false_unseen_claim(self):self.assertIn('already inspected',str(self.r['exclusions']))
 def test_three_subphases_one_report(self):self.assertEqual(self.r['synthesis']['worlds'],8)

if __name__=='__main__':unittest.main()
