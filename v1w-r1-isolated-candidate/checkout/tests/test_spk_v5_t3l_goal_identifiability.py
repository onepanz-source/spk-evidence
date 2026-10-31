import unittest
from spk_v5_research.island_goal_identifiability_v5t3l import replay,paired_worlds,SCHEMA

class T3lPairedWorlds(unittest.TestCase):
 def test_schema(self):self.assertIn('observationally-indistinguishable',SCHEMA)
 def test_identical_action_trace(self):
  p=paired_worlds(29,80,stress=True)
  self.assertEqual(p['aligned_world']['A_action_and_C_credit_digest'],p['inverted_world']['A_action_and_C_credit_digest'])
 def test_identical_credit_ledger(self):
  p=paired_worlds(29,80,stress=True)
  self.assertEqual(p['aligned_world']['A_registry_head_sha256'],p['inverted_world']['A_registry_head_sha256'])
 def test_identical_updates(self):
  p=paired_worlds(29,80,stress=True)
  self.assertEqual(p['aligned_world']['C_credit_updates'],p['inverted_world']['C_credit_updates'])
 def test_identical_weights(self):
  p=paired_worlds(29,80,stress=True)
  self.assertEqual(p['aligned_world']['A_registry_weights_sha256'],p['inverted_world']['A_registry_weights_sha256'])
 def test_complementary_correctness(self):
  p=paired_worlds(29,80,stress=True)
  self.assertEqual(p['aligned_world']['correct']+p['inverted_world']['correct'],240)
 def test_opposite_goals_not_input(self):self.assertTrue(paired_worlds(29,80)['goal_is_auditor_only'])
 def test_missing_credits_still_indistinguishable(self):
  p=paired_worlds(47,80,stress=True)
  self.assertLess(p['aligned_world']['C_credit_updates'],p['episodes_per_world'])
 def test_no_stress_indistinguishable(self):
  p=paired_worlds(47,80,stress=False)
  self.assertEqual(p['aligned_world']['C_credit_updates'],240)
 def test_deterministic(self):self.assertEqual(paired_worlds(11,80),paired_worlds(11,80))
 def test_distinct_seeds_not_same_transcript(self):
  self.assertNotEqual(paired_worlds(11,80)['aligned_world']['A_action_and_C_credit_digest'],
                      paired_worlds(47,80)['aligned_world']['A_action_and_C_credit_digest'])
 def test_bad_goal_rejected(self):
  for name in ('',None,'photo','other'):
   with self.subTest(name=name),self.assertRaises(ValueError):replay(11,80,name)
 def test_bad_budget_rejected(self):
  for n in (-1,0,79,501,80.0):
   with self.subTest(n=n),self.assertRaises(ValueError):replay(11,n,'C_aligned')
 def test_bad_seed_rejected(self):
  with self.assertRaises(ValueError):replay('11',80,'C_aligned')
 def test_bool_seed_rejected(self):
  with self.assertRaises(ValueError):replay(True,80,'C_aligned')
 def test_bad_stress_rejected(self):
  with self.assertRaises(ValueError):replay(11,80,'C_aligned',stress=1)
 def test_output_no_native_learning(self):self.assertTrue(paired_worlds(11,80)['aligned_world']['schema']==SCHEMA)

if __name__=='__main__':unittest.main()
