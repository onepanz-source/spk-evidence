import unittest
from spk_v5_research.island_source_bridge_audit_v5t3q import table,cohort,report

class SourceBridgeAudit(unittest.TestCase):
 def test_table_180(self):
  rows,counts=table();self.assertEqual(len(rows),180)
 def test_valid_42(self):
  _,counts=table();self.assertEqual(counts['SHADOW_SOURCE_REPLAY_ELIGIBLE'],42)
 def test_all_contexts(self):
  rows,_=table();self.assertEqual(set(x['context'] for x in rows),{'00','01','10','11'})
 def test_every_arm(self):
  rows,_=table();self.assertEqual(set(x['arm'] for x in rows),{'current','persist','silent'})
 def test_faults_failclosed(self):
  rows,_=table();self.assertTrue(all(not x['eligible'] for x in rows if x['failure'] in ('no_C','no_marker','no_reverse')))
  self.assertTrue(all(not x['eligible'] for x in rows if x['failure']=='no_forward' and x['arm']=='current' and x['context'][-1]=='1'))
 def test_no_sensor_failclosed(self):
  rows,_=table();self.assertTrue(all(not x['eligible'] for x in rows if x['C_sensor'] is None))
 def test_source_grants_real_on_admitted(self):
  rows,_=table();self.assertTrue(all(x['source_grants_charged']==2 for x in rows if x['eligible']))
 def test_no_native_reward_promotion(self):
  out=report();self.assertTrue(any('single native' in s for s in out['claims_excluded']))
 def test_clean_cohort_full(self):
  x=cohort(11,120,False);self.assertEqual(x['registry']['updates'],120)
 def test_stressed_cohort_fewer(self):
  x=cohort(11,120,True);self.assertLess(x['registry']['updates'],120)
 def test_no_pending(self):
  x=cohort(47,120,True);self.assertEqual(x['registry']['pending'],0)
 def test_determinism(self):self.assertEqual(cohort(11,120,True),cohort(11,120,True))
 def test_report_all_runs(self):self.assertEqual(len(report()['online_replay_runs']),6)
 def test_report_total_episodes(self):self.assertEqual(report()['total_online_episodes'],720)
 def test_credit_counts(self):
  r=report();self.assertGreaterEqual(r['total_source_admitted'],r['total_credited_updates'])
 def test_all_source_status_exclusive(self):
  r=report();self.assertEqual(sum(r['C_verdict_table']['counts'].values()),180)
