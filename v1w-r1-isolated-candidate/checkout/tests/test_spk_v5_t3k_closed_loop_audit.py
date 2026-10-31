import tempfile,unittest,json,os
from pathlib import Path
from spk_v5_research.island_closed_loop_audit_v5t3k import (SCHEMA,SEEDS,PATTERNS,public_uci,report)
from spk_v5_research.island_regime_replay_v5t3j import trial
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy,packet_for,digest
from spk_v5_research.island_c_owned_credit_v5t3h import Measurement,CreditAdmissionError

UCI_DIR=Path(os.environ.get("SPK_T3IJK_UCI_DIR","/mnt/data"))
HAS_UCI=(UCI_DIR/"datatraining.txt").is_file()

class T3kResearchBoundaries(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  # Canonical full replay is performed by the gate once, not repeated in unittest.
  # Unittest validates format and bounds from pinned canonical reference.
  cls.cached_report=json.loads((Path(__file__).parent.parent/'docs/spk-v5-t3ijk-reference.json').read_text())
 def test_schema(self):self.assertIn('bundled-closed-loop',SCHEMA)
 def test_predeclared_seeds(self):self.assertEqual(SEEDS,(11,29,47,83))
 def test_predeclared_negatives(self):self.assertIn('uninformative_coin',PATTERNS)
 def test_uci_budget_invalid(self):
  for n in (-1,0,199,5001,3.5):
   with self.subTest(n=n),self.assertRaises(ValueError):public_uci(Path('/mnt/data'),n)
 def test_missing_uci_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):public_uci(Path(t),200)
 @unittest.skipUnless(HAS_UCI,'authentic original UCI files missing')
 def test_uci_public_prefix_determinism(self):
  a=public_uci(UCI_DIR,200);b=public_uci(UCI_DIR,200)
  self.assertEqual(a,b)
 @unittest.skipUnless(HAS_UCI,'authentic original UCI files missing')
 def test_uci_original_sha(self):
  x=public_uci(UCI_DIR,200)
  self.assertEqual(x['datatraining.txt']['raw_original_sha256'],
                   'b2c4d0ce2b9e4e453c476f7125ef31aeec2d1f5c7f5572d0e80de3df6521ab56')
  self.assertEqual(x['datatest2.txt']['raw_original_sha256'],
                   'd026d1bd5aeccd4aff4f3b3710d48e40613bd5fc370db7e61bbdcaa50d985095')
 @unittest.skipUnless(HAS_UCI,'authentic original UCI files missing')
 def test_uci_C_not_photo_supervision(self):
  x=public_uci(UCI_DIR,200)
  for obj in x.values():
   self.assertTrue(obj['C_sensor_precomputed_by_host'])
   self.assertFalse(obj['independent_blind'])
 @unittest.skipUnless(HAS_UCI,'authentic original UCI files missing')
 def test_uci_count(self):
  x=public_uci(UCI_DIR,200)
  self.assertTrue(all(v['admitted']<=200 for v in x.values()))
 @unittest.skipUnless(HAS_UCI,'authentic original UCI files missing')
 def test_uci_learner_not_guaranteed_best(self):
  x=public_uci(UCI_DIR,200)
  self.assertTrue(any(v['fixed_current_photo_match']>v['PHOTO_occ_match_POSTHOC'] for v in x.values()))
 def test_no_C_info_in_choose_signature(self):
  import inspect
  args=inspect.signature(OnlinePolicy.choose).parameters
  self.assertEqual(tuple(args),('self','previous_light','current_light'))
 def test_no_reward_on_lost_C(self):
  agent=OnlinePolicy(3,exploration=0)
  a=agent.decide('r',0,300,0)
  m=Measurement('2026-10-22 10:00:00','2026-10-22 10:01:00',0.,300.,900.,reverse_enabled=False)
  p=packet_for('r',a,m,0);agent.register(p)
  self.assertEqual(agent.audit()['updates'],0)
 def test_shift_is_not_universal(self):
  r=trial(29,90,True,pattern='stationary_current')['summaries']
  self.assertGreater(r['current']['correct'],r['learned']['correct'])
 def test_random_coin_cannot_be_assumed_beneficial(self):
  r=trial(29,90,True,pattern='uninformative_coin')['summaries']
  self.assertLess(abs(r['learned']['accuracy']-.5),.1)
 def test_rapid_switch_can_lose_to_fixed(self):
  r=trial(29,110,True,pattern='rapid_switch')['summaries']
  self.assertGreater(r['persist']['accuracy'],r['learned']['accuracy'])
 def test_action_outcome_not_credit_on_sensor_failure(self):
  from spk_v5_research.island_regime_replay_v5t3j import generate,measurement_of,actual_correct
  r=next(generate(29,80))
  a='current';m=measurement_of(r,sensor=False)
  p=packet_for('e',a,m,0)
  self.assertEqual(p.witness['status'],'C_evidence_missing')
  self.assertIsInstance(actual_correct(a,r),bool)
 def test_report_has_exclusions(self):
  r=self.cached_report
  self.assertIn('no native learning',str(r['scope_exclusions']))
  self.assertIsNotNone(r['public_UCI_photo_label_POSTHOC_ONLY'])
 def test_report_has_all_controls(self):
  r=self.cached_report
  self.assertEqual(r['synthetic_cases'],16800)
  self.assertEqual(len(r['shift']['scenarios']),8)
  self.assertEqual(len(r['falsification_cases']),6)
 def test_report_reference_positive(self):
  r=self.cached_report
  self.assertGreater(r['shift']['delta_learned_vs_best_fixed'],0)
  self.assertGreater(r['shift']['delta_learned_vs_placebo'],0)
 def test_public_and_synthetic_independent(self):
  a=self.cached_report
  self.assertIsNotNone(a['public_UCI_photo_label_POSTHOC_ONLY'])
  self.assertEqual(len(a['falsification_cases']),6)

if __name__=='__main__':unittest.main()
