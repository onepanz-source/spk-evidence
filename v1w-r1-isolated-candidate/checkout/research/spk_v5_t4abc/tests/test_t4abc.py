import ast
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t4abc as m

class T4ABCTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory()
  self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)

 def write(self,name,data):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(data,encoding='utf8');return p

 def test_known_frozen_pins_distinct(self):
  self.assertEqual(len(m.FROZEN),3)
  self.assertEqual(len(set(m.FROZEN.values())),3)

 def test_known_primary_targets(self):
  self.assertEqual(len(m.REQUIRED_NAMES),2)
  self.assertTrue(m.REQUIRED_NAMES.issubset(m.TARGET_NAMES))

 def test_ast_extract_lines_calls(self):
  p=self.write('demo.py','def evidence():\n    return execute(verify_custody())\n')
  d=m.inspect_source(p,self.root)
  self.assertEqual(d['functions'][0]['name'],'evidence')
  self.assertEqual(d['functions'][0]['calls']['execute'],1)
  self.assertEqual(d['functions'][0]['calls']['verify_custody'],1)

 def test_ast_object_method_call(self):
  p=self.write('demo.py','def f(x):\n  return x.receipt_for()\n')
  d=m.inspect_source(p,self.root)
  self.assertEqual(d['functions'][0]['calls']['x.receipt_for'],1)

 def test_ast_reject_invalid_code(self):
  p=self.write('demo.py','def ^! nope')
  with self.assertRaisesRegex(m.GateError,'TARGET_SOURCE_INVALID'):m.inspect_source(p,self.root)

 def test_ast_reject_empty(self):
  p=self.write('demo.py','')
  with self.assertRaisesRegex(m.GateError,'TARGET_SOURCE_SIZE_INVALID'):m.inspect_source(p,self.root)

 def test_ast_reject_too_big(self):
  p=self.write('demo.py','#'+('x'*(m.MAX_SOURCE_BYTES+1)))
  with self.assertRaisesRegex(m.GateError,'TARGET_SOURCE_SIZE_INVALID'):m.inspect_source(p,self.root)

 def test_ast_reject_function_storm(self):
  p=self.write('demo.py',''.join(f'def f{i}():\n  pass\n' for i in range(m.MAX_AST_FUNCTIONS+1)))
  with self.assertRaisesRegex(m.GateError,'AST_FUNCTIONS_LIMIT'):m.inspect_source(p,self.root)

 def test_allowlist_missing_primary(self):
  self.write('research/island_source_bv_bridge_v5t3o.py','def evidence(): pass')
  with self.assertRaisesRegex(m.GateError,'TARGET_MISSING_OR_AMBIGUOUS'):m.find_allowlisted(self.root)

 def test_allowlist_duplicate_rejected(self):
  for rel in ['research/island_source_bv_bridge_v5t3o.py','research/island_c_owned_credit_v5t3h.py','tests/island_c_owned_credit_v5t3h.py']:
   self.write(rel,'def f(): return None')
  with self.assertRaisesRegex(m.GateError,'TARGET_DUPLICATE'):m.find_allowlisted(self.root)

 def test_allowlist_ignores_venv(self):
  self.write('research/island_source_bv_bridge_v5t3o.py','def f(): pass')
  self.write('research/island_c_owned_credit_v5t3h.py','def f(): pass')
  self.write('.venv/island_c_owned_credit_v5t3h.py','def f(): pass')
  x=m.find_allowlisted(self.root)
  self.assertEqual(len(x),2)

 def test_allowlist_excludes_symlink(self):
  p=self.write('a/source.py','x=1')
  for rel in ['research/island_source_bv_bridge_v5t3o.py','research/island_c_owned_credit_v5t3h.py']:
   q=self.root/rel;q.parent.mkdir(exist_ok=True,parents=True);q.symlink_to(p)
  with self.assertRaises(m.GateError):m.find_allowlisted(self.root)

 def test_frozen_absent(self):
  with self.assertRaisesRegex(m.GateError,'FROZEN_SOURCE_MISSING'):m.verify_frozen(self.root)

 def test_frozen_mismatch(self):
  for rel in m.FROZEN:self.write(rel,'# changed\n')
  with self.assertRaisesRegex(m.GateError,'FROZEN_SOURCE_SHA_DRIFT'):m.verify_frozen(self.root)

 def test_verify_missing_evidence(self):
  with self.assertRaisesRegex(m.GateError,'EVIDENCE_INPUT_MISSING'):
   m.verify_inputs(self.root/'missing.json',self.root/'missing.jsonl')

 def test_verify_evidence_hash_mismatch(self):
  r=self.write('x.json','{}');t=self.write('x.jsonl','{}\n')
  with self.assertRaisesRegex(m.GateError,'RECOVERY_SHA_MISMATCH'):m.verify_inputs(r,t)

 def test_verify_evidence_size_limit(self):
  r=self.write('x.json','{}');t=self.write('x.jsonl','{}\n')
  with patch.object(m,'MAX_TRACE_BYTES',1):
   with self.assertRaisesRegex(m.GateError,'TRACE_SIZE_INVALID'):m.verify_inputs(r,t)

 def test_call_name_dynamic(self):
  node=ast.parse('call()').body[0].value.func
  self.assertEqual(m.call_name(node),'call')
  self.assertEqual(m.call_name(ast.parse('(lambda x:x)(3)').body[0].value.func),'dynamic')

 def test_find_allowlist_optional_absent_allowed(self):
  for rel in ['research/island_source_bv_bridge_v5t3o.py','research/island_c_owned_credit_v5t3h.py']:
   self.write(rel,'def f(): pass')
  self.assertEqual(len(m.find_allowlisted(self.root)),2)

 def test_produce_fail_on_existing_output(self):
  out=self.write('existing.json','{}')
  with self.assertRaisesRegex(m.GateError,'OUTPUT_ALREADY_EXISTS'):
   m.produce(self.root,self.root/'missing',self.root/'missing',out,self.root/'out.tar.gz')

 def test_produce_fail_on_bad_extension(self):
  with self.assertRaisesRegex(m.GateError,'OUTPUT_PATH_INVALID'):
   m.produce(self.root,self.root/'missing',self.root/'missing',self.root/'out.json',self.root/'out.zip')

 def test_produce_local_allowlisted_bundle_and_nonpromotion(self):
  for rel in m.FROZEN:self.write(rel,'# pinned\n')
  self.write('research/island_source_bv_bridge_v5t3o.py','def evidence():\n  return _source_pass()\n')
  self.write('research/island_c_owned_credit_v5t3h.py','def execute():\n  return 1\n')
  self.write('research/island_online_credit_v5t3i.py','def packet_for(): return 1\n')
  self.write('secrets.env','THIS_MUST_NOT_BE_EXPORTED')
  r=self.write('recovery.json','{}');p=self.write('profile.jsonl','{}\n')
  out=self.root/'out.json';bundle=self.root/'out.tar.gz'
  frozen={rel:m.sha(self.root/rel) for rel in m.FROZEN}
  profile={'observable_bridge_compute_calls':3,'observable_C_credit_module_compute_calls':1,'observable_BV_v0e_compute_calls':2,'coverage_complete':False}
  with patch.object(m,'verify_frozen',return_value=frozen),patch.object(m,'verify_inputs',return_value={}),patch.object(m,'census_trace',return_value=profile):
   result=m.produce(self.root,r,p,out,bundle)
  self.assertFalse(result['promotion_allowed'])
  self.assertFalse(result['native_semantic_BV_proven'])
  self.assertTrue(out.exists() and bundle.exists())
  with tarfile.open(bundle) as tar:
   names=tar.getnames()
   self.assertEqual(len(names),3)
   self.assertNotIn('secrets.env',names)
   self.assertTrue(all(n.endswith('.py') for n in names))

 def test_produce_fail_when_zero_C_credit_observations(self):
  for rel in m.FROZEN:self.write(rel,'# pinned\n')
  self.write('research/island_source_bv_bridge_v5t3o.py','def evidence(): pass\n')
  self.write('research/island_c_owned_credit_v5t3h.py','def execute(): pass\n')
  r=self.write('recovery.json','{}');p=self.write('trace.jsonl','{}\n')
  profile={'observable_bridge_compute_calls':1,'observable_C_credit_module_compute_calls':0,'observable_BV_v0e_compute_calls':1}
  with patch.object(m,'verify_frozen',return_value={}),patch.object(m,'verify_inputs',return_value={}),patch.object(m,'census_trace',return_value=profile):
   with self.assertRaisesRegex(m.GateError,'C_CREDIT_MODULE_NEVER_OBSERVED'):
    m.produce(self.root,r,p,self.root/'out.json',self.root/'out.tar.gz')

if __name__=='__main__':unittest.main()

class EvidenceFalsificationTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)
  self.r=self.root/'recovery.json';self.p=self.root/'profile.jsonl'
  self.p.write_text('a\n')
  self.valid={
   'schema':'spk-v5-t3xyz-trace-volume-recovery/research-v0',
   'status':'PASSIVE_TRACE_VALID_WITH_BOUNDED_COVERAGE_NOT_NATIVE_BV',
   'promotion_allowed':False,'native_single_pass_C_verdict_proven':False,
   'passive_profile':{'sha256':m.TRACE_SHA,'jsonl_records':64615,
     'saturated_pid_count':2,'complete_execution_coverage_proven':False},
   'original_T3OPQ':{'producer_report_sha256':m.ORIGINAL_SHA,'dual_replay':True}
  }
 def audit(self,d):
  self.r.write_text(json.dumps(d))
  def digest(path):return m.RECOVERY_SHA if path==self.r else m.TRACE_SHA
  with patch.object(m,'sha',side_effect=digest):return m.verify_inputs(self.r,self.p)
 def test_good_boundary_is_nonpromotable(self):
  self.assertIs(self.audit(self.valid)['promotion_allowed'],False)
 def test_reject_promotion(self):
  x=json.loads(json.dumps(self.valid));x['promotion_allowed']=True
  with self.assertRaisesRegex(m.GateError,'RECOVERY_FALSE_PROMOTION'):self.audit(x)
 def test_reject_native_verdict_claim(self):
  x=json.loads(json.dumps(self.valid));x['native_single_pass_C_verdict_proven']=True
  with self.assertRaisesRegex(m.GateError,'RECOVERY_FALSE_PROMOTION'):self.audit(x)
 def test_reject_falsified_complete_coverage(self):
  x=json.loads(json.dumps(self.valid));x['passive_profile']['complete_execution_coverage_proven']=True
  with self.assertRaisesRegex(m.GateError,'COVERAGE_LIMIT_NOT_DISCLOSED'):self.audit(x)
 def test_reject_saturation_suppression(self):
  x=json.loads(json.dumps(self.valid));x['passive_profile']['saturated_pid_count']=0
  with self.assertRaisesRegex(m.GateError,'COVERAGE_LIMIT_NOT_DISCLOSED'):self.audit(x)
 def test_reject_wrong_producer(self):
  x=json.loads(json.dumps(self.valid));x['original_T3OPQ']['producer_report_sha256']='0'*64
  with self.assertRaisesRegex(m.GateError,'ORIGINAL_CUSTODY_INVALID'):self.audit(x)
 def test_reject_dual_replay_disguise(self):
  x=json.loads(json.dumps(self.valid));x['original_T3OPQ']['dual_replay']=False
  with self.assertRaisesRegex(m.GateError,'ORIGINAL_CUSTODY_INVALID'):self.audit(x)
 def test_reject_profile_size_drift(self):
  x=json.loads(json.dumps(self.valid));x['passive_profile']['jsonl_records']=64614
  with self.assertRaisesRegex(m.GateError,'TRACE_RECEIPT_COUNTS_INVALID'):self.audit(x)
