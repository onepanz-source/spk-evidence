import json, tempfile, unittest
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject
from research.spk_v5_t10stu_vwx_yza.surface_probe_v0 import *
from research.spk_v5_t10stu_vwx_yza.cumulative_surface_gate import report,sha,PARENT

R={'owner':'C','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'expected_version':2}
class SurfaceTests(unittest.TestCase):
 def test_request(self):
  x=read_only_contract_request(**dict(R,version=R['expected_version']) if False else
      {'owner':'C','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':2})
  self.assertFalse(x['native_grant']);self.assertFalse(x['native_write'])
  self.assertTrue(x['request_digest'])
 def test_deny_promotion(self):
  for claimed in (None,{}, {'issuer':'ORIGINAL','native':True,'signature':'FAKE'}, {'grant':2}):
   out=reject_native_promotion(R,claimed)
   self.assertFalse(out['promotion_allowed']);self.assertEqual(out['native_grants'],0)
 def test_strict_fields(self):
  for field,bad in [('owner','A'),('owner',1),('domain','S'),('mode','verify'),('pe_id','PE-X'),
                    ('context',9),('context',True),('version',-1),('version',False)]:
   arg={'owner':'C','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':2}
   arg[field]=bad
   with self.subTest(field=field,bad=bad),self.assertRaises(Reject):read_only_contract_request(**arg)
 def test_missing_scope(self):
  for f in R:
   x=dict(R);x.pop(f)
   with self.assertRaises(Reject):reject_native_promotion(x)
 def test_probe_ast_no_execution(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_contract_v0.py').write_text('raise RuntimeError("EXECUTED")\nclass Contract:\n def authorize(self,target,version):pass\n')
   r=probe(tmp)
   self.assertEqual(r['candidate_count'],1)
   self.assertIn('authorize',r['candidates'][0]['surface'][0]['methods'])
   self.assertFalse(r['native_memory_grant_executed'])
 def test_surfaces_deterministic(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_access_v0.py').write_text('def authorize(a,b):return False\n')
   self.assertEqual(probe(tmp),probe(tmp))
 def test_ignores_research_and_misleading_names(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp,'research');p.mkdir();(p/'memory_contract_v0.py').write_text('def permit():pass')
   self.assertEqual(probe(tmp)['candidate_count'],0)
 def test_symlink_denied(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   real=a/'memory_real.py';real.write_text('pass')
   (a/'memory_contract_v0.py').symlink_to(real)
   with self.assertRaises(Reject):probe(tmp)
 def test_invalid_source_deny(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_contract_v0.py').write_text('\0')
   with self.assertRaises((SyntaxError,ValueError)):probe(tmp)
 def test_oversize_deny(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_contract_v0.py').write_bytes(b'#'+b'x'*256005)
   with self.assertRaises(Reject):probe(tmp)
 def test_parent_source_pin(self):
  self.assertEqual(sha('research/spk_v5_t10stu_vwx_yza/reference/t10jkl-mno-pqr-cumulative.json'),PARENT)
 def test_cumulative(self):
  r=report('.')
  self.assertEqual(r['T10YZA']['prior_results']['context_affinity']['successes'],88)
  self.assertEqual(r['T10YZA']['prior_results']['naive_three']['successes'],84)
  self.assertFalse(r['promotion_allowed'])
  self.assertFalse(r['native_learning'])
  self.assertEqual(r['native_SPK_P_grants'],0)
class NegativeContractTests(unittest.TestCase):
 def mk(self):
  return {'owner':'C','domain':'P','mode':'execute','pe_id':'PE-C-RESEARCH','context':0,'version':0}
 def test_reference_false_grant_exhaustive(self):
  for i in range(20):
   claim={'grant':i,'issuer':'native','authorized':True,'signature':str(i)}
   z=reject_native_promotion(R,claim)
   self.assertEqual((z['native_grants'],z['native_writes'],z['promotion_allowed']),(0,0,False))
 def test_context_version_independence(self):
  for ctx in (0,1):
   for v in (0,1,2,15,100):
    a=self.mk();a['context']=ctx;a['version']=v
    z=read_only_contract_request(**a)
    self.assertEqual(z['request']['expected_version'],v)
    self.assertEqual(z['request']['context'],ctx)
 def test_no_cross_mode(self):
  for m in ('train','training','verify','remodel','',None):
   a=self.mk();a['mode']=m
   with self.assertRaises(Reject):read_only_contract_request(**a)
 def test_no_cross_domain(self):
  for m in ('S','E','O','P ',None):
   a=self.mk();a['domain']=m
   with self.assertRaises(Reject):read_only_contract_request(**a)
 def test_no_cross_owner(self):
  for m in ('A','D','B','C ',None):
   a=self.mk();a['owner']=m
   with self.assertRaises(Reject):read_only_contract_request(**a)
 def test_request_digest_binds_context(self):
  a=self.mk();a['context']=0;x=read_only_contract_request(**a)
  a['context']=1;y=read_only_contract_request(**a)
  self.assertNotEqual(x['request_digest'],y['request_digest'])
 def test_request_digest_binds_version(self):
  a=self.mk();x=read_only_contract_request(**a)
  a['version']=1;y=read_only_contract_request(**a)
  self.assertNotEqual(x['request_digest'],y['request_digest'])
 def test_probe_distinct_classes(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_access_v0.py').write_text('class Owner:\n def approve(self, x): return x\n\ndef write(a):return 1\n')
   r=probe(tmp)
   self.assertEqual(r['candidate_count'],1)
   self.assertEqual([x['kind'] for x in r['candidates'][0]['surface']],['class','function'])
 def test_probe_source_hash_changes(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir();p=a/'memory_contract_v0.py'
   p.write_text('def foo():return 1')
   x=probe(tmp);p.write_text('def foo():return 2');y=probe(tmp)
   self.assertNotEqual(x['candidate_digest'],y['candidate_digest'])
 def test_probe_filters_unsuspected_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'functionality.py').write_text('def foo():pass')
   self.assertEqual(probe(tmp)['candidate_count'],0)
 def test_probe_invalid_ast_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_contract_v0.py').write_text('def broken(')
   with self.assertRaises(SyntaxError):probe(tmp)
 def test_promotion_requires_explicit_scope(self):
  for f in ('owner','domain','mode','pe_id','context','expected_version'):
   r=dict(R);r[f]=None
   with self.assertRaises(Reject):reject_native_promotion(r)
 def test_candidate_does_not_grant(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp,'spk_architecture_v1');a.mkdir()
   (a/'memory_contract_v0.py').write_text('class NativeAuthority:\n def grant(self):return True')
   x=probe(tmp)
   self.assertEqual(x['candidate_count'],1)
   self.assertFalse(x['source_contract_api_authorized'])
   self.assertFalse(x['native_memory_grant_executed'])

if __name__=='__main__':unittest.main()
