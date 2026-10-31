import unittest
from spk_v5_research.island_regime_replay_v5t3j import (generate,trial,actual_correct,measurement_of,
 _conditions,REGIMES,PlaceboSelector)
from spk_v5_research.island_c_owned_credit_v5t3h import execute
from spk_v5_research.island_online_credit_v5t3i import OnlinePolicy
class T3jRegime(unittest.TestCase):
 def test_three_regimes(self):
  x=list(generate(29,80));self.assertEqual(len(x),240)
  self.assertEqual([x[i].regime for i in (0,80,160)],list(REGIMES))
 def test_fixed_determinism(self):
  self.assertEqual(list(generate(29,80)),list(generate(29,80)))
 def test_seed_differentiation(self):
  self.assertNotEqual(list(generate(29,80)),list(generate(30,80)))
 def test_different_temporal_pairs(self):
  x=list(generate(29,80));self.assertTrue(any(y.previous_light!=y.current_light for y in x))
 def test_valid_original_tick_gap(self):
  from datetime import datetime
  for r in generate(29,80):
   a=datetime.strptime(r.previous_stamp,'%Y-%m-%d %H:%M:%S');b=datetime.strptime(r.current_stamp,'%Y-%m-%d %H:%M:%S')
   self.assertIn(int((b-a).total_seconds()),(59,60,61))
 def test_small_positive_shift(self):
  x=trial(29,100)
  self.assertGreater(x['summaries']['learned']['accuracy'],x['summaries']['current']['accuracy'])
  self.assertGreater(x['summaries']['learned']['accuracy'],x['summaries']['placebo']['accuracy'])
 def test_stress_reduces_credits(self):
  plain=trial(29,100);stressed=trial(29,100,True)
  self.assertEqual(plain['policy_registry']['updates'],300)
  self.assertLess(stressed['policy_registry']['updates'],300)
 def test_harness_no_photo(self):
  x=trial(29,80)
  self.assertNotIn('photographic',str(x));self.assertIn('C_paid_research_A1b_replay_sha256',x)
 def test_fake_credits_not_added(self):
  p=PlaceboSelector(29);self.assertIsInstance(p.feed_unrelated_coin(0,300,'current'),int)
  self.assertFalse(hasattr(p,'settle'))
 def test_informative_vs_uninformative(self):
  x=trial(29,110,True,pattern='uninformative_coin')
  self.assertLess(abs(x['summaries']['learned']['accuracy']-.5),.10)
 def test_stationary_fixed_best(self):
  x=trial(29,100,True,pattern='stationary_current')
  self.assertGreater(x['summaries']['current']['accuracy'],x['summaries']['learned']['accuracy'])
 def test_rapid_switch_no_guarantee(self):
  x=trial(29,110,True,pattern='rapid_switch')
  self.assertEqual(x['summaries']['learned']['total'],330)
 def test_unknown_regime_rejected(self):
  with self.assertRaises(ValueError):list(generate(29,100,'unknown'))
 def test_underbudget_rejected(self):
  for x in (0,79,-1,1.2):
   with self.subTest(x=x),self.assertRaises(ValueError):list(generate(29,x))
 def test_proof_pair_for_two_arms(self):
  row=next(generate(29,80))
  for arm in ('current','persist','silent'):
   r=execute(measurement_of(row),arm)
   self.assertEqual(r['A_consumed_credit']==1,actual_correct(arm,row))
 def test_modelled_loss_not_negative(self):
  c=_conditions(29,5,True)
  self.assertIn(c['delay'],(0,1,2,3))
 def test_replayed_run_exact(self):
  a=trial(29,100,True);b=trial(29,100,True)
  self.assertEqual(a,b)
 def test_seeds_have_different_hashes(self):
  a=trial(29,80,True);b=trial(30,80,True)
  self.assertNotEqual(a['C_paid_research_A1b_replay_sha256'],b['C_paid_research_A1b_replay_sha256'])
 def test_no_missing_credits_in_normal(self):
  x=trial(29,80)
  self.assertEqual(x['observed_C_origin_statuses'],{'C_authored_credit_delivered':240})
 def test_stressed_has_forward_losses(self):
  x=trial(29,120,True)
  self.assertGreater(x['observed_C_origin_statuses'].get('forward_custody_failed',0),0)
 def test_all_three_fixed_replayed_in_A1b(self):
  x=trial(29,80)
  self.assertEqual(x['source_executions'],960)
 def test_settled_count(self):
  x=trial(29,80,True)
  r=x['policy_registry'];self.assertEqual(r['pending'],0)
  self.assertEqual(r['updates']+r['discarded'],x['observed_C_origin_statuses']['C_authored_credit_delivered'])
 def test_no_future_arms_in_context_API(self):
  s=OnlinePolicy(seed=29)
  a=s.decide('x',0,300,0)
  self.assertIn(a,('current','persist','silent'))
  self.assertNotIn('C',s.reserved['x'])

if __name__=='__main__':unittest.main()
