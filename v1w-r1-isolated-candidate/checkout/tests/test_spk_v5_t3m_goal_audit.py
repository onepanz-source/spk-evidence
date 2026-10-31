import unittest, tempfile, json, os
from pathlib import Path
from spk_v5_research.island_goal_audit_v5t3m import EXPECTED_SHA,SCHEMA,one_public,public_audit

ROOT=Path(__file__).resolve().parent.parent
class T3mPublicGoalAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.reference=json.loads((ROOT/'docs/spk-v5-t3lmn-reference.json').read_text()) if (ROOT/'docs/spk-v5-t3lmn-reference.json').is_file() else None
 def test_schema(self):self.assertIn('proxy-credit',SCHEMA)
 def test_exact_original_source_hash_count(self):self.assertEqual(len(EXPECTED_SHA),3)
 def test_sha_shape(self):self.assertTrue(all(len(h)==64 for h in EXPECTED_SHA.values()))
 def test_unknown_filename_rejected(self):
  with self.assertRaises(ValueError):one_public(Path('other.txt'))
 def test_str_filename_rejected(self):
  with self.assertRaises(ValueError):one_public('/mnt/data/datatest.txt')
 def test_missing_original_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):one_public(Path(td)/'datatraining.txt')
 def test_empty_directory_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):public_audit(Path(td))
 def test_invalid_dir_rejected(self):
  for v in (None,'/mnt/data',Path('/__absent_spk__')):
   with self.subTest(v=v),self.assertRaises(ValueError):public_audit(v)
 def test_wrong_budget_rejected(self):
  for n in (0,1,99,1501,100.0,None):
   with self.subTest(n=n),self.assertRaises(ValueError):one_public(Path('/mnt/data/datatest.txt'),max_pairs=n)
 def test_malicious_fixture_same_name_rejected_by_sha(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'datatest.txt';p.write_text('made-up data')
   with self.assertRaises(ValueError):one_public(p)
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'datatest.txt';p.symlink_to('/mnt/data/datatest.txt')
   with self.assertRaises(ValueError):one_public(p)
 def test_credit_disagreement_identity(self):
  c=self.reference['public']['pooled']
  self.assertEqual(c['misleading_positive']+c['misleading_negative'],c['proxy_mismatch_photo'])
 def test_credit_updates_match_episodes(self):
  for file in self.reference['public']['files']:
   self.assertEqual(file['A1b_C_authored_credit_admitted'],file['counts']['episodes'])
 def test_photo_not_in_A_or_C(self):
  self.assertTrue(all(f['goal_labels_consulted_posthoc'] and not f['photo_label_in_policy'] for f in self.reference['public']['files']))
 def test_only_original_source_sha(self):
  for f in self.reference['public']['files']:
   self.assertEqual(f['source_sha256'],EXPECTED_SHA[f['name']])
 def test_disagreement_nonzero(self):self.assertGreater(self.reference['public']['pooled']['proxy_mismatch_photo'],0)
 def test_bad_goal_reward_nonzero(self):self.assertGreater(self.reference['public']['pooled']['misleading_positive']+self.reference['public']['pooled']['misleading_negative'],0)
 def test_public_pooled_reconcile(self):
  for metric,val in self.reference['public']['pooled'].items():
   self.assertEqual(val,sum(f['counts'].get(metric,0) for f in self.reference['public']['files']))
 def test_audit_each_day_reconcile(self):
  for f in self.reference['public']['files']:
   self.assertEqual(sum(d.get('episodes',0) for d in f['by_day'].values()),f['counts']['episodes'])
 def test_context_reconcile(self):
  for f in self.reference['public']['files']:
   self.assertEqual(sum(d.get('episodes',0) for d in f['by_A_light_context'].values()),f['counts']['episodes'])
 def test_no_blind_claim(self):self.assertTrue(self.reference['public']['posthoc_not_blind'])

if __name__=='__main__':unittest.main()
