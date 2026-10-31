from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('spk_t3xyz_trace_recovery',HERE/'trace_recovery.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestTraceRecovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'trace.jsonl'
  self.t=1000
 def record(self,kind,pid=5,seq=1,**kwargs):
  obj={'kind':kind,'pid':pid,'seq':seq,'host_monotonic_ns':self.t}
  self.t+=1
  if kind!='probe_loaded':
   obj.update({'function':'_compute_local','source':'/repo/spk_architecture_v1/pe_execution_v1b.py'})
   if kind=='compute_call':
    obj.update({'stack':[{'file':'live_dual_scheduler_v0e.py','function':'execute_live_v0e'}],
                'declared_argument_names':['node','state','timestamp','channels']})
  else:
   obj.update({'scope':'cpython_profile_only_not_native_attestation'})
  obj.update(kwargs)
  return obj
 def write(self,rows):
  self.path.write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows))
 def valid(self):
  return [self.record('probe_loaded',5,1),self.record('compute_call',5,2),
          self.record('compute_return',5,3),self.record('probe_loaded',6,1)]
 def test_valid_and_no_native_promotion(self):
  self.write(self.valid());j=m.analyze_trace(self.path)
  self.assertEqual(j['event_counts']['compute_call'],1)
  self.assertFalse(j['complete_execution_coverage_proven']);self.assertFalse(j['C_authored_semantic_verdict_observed'])
  self.assertEqual(j['saturated_pid_count'],0)
 def test_missing_file(self):
  with self.assertRaisesRegex(m.AuditError,'TRACE_MISSING'):m.analyze_trace(self.path)
 def test_empty_file(self):
  self.path.write_text('')
  with self.assertRaisesRegex(m.AuditError,'TRACE_SIZE_INVALID'):m.analyze_trace(self.path)
 def test_legacy_32mb_limit_removed_without_removing_bounds(self):
  self.write(self.valid());self.assertGreater(m.MAX_BYTES,47_545_722)
 def test_hard_size_limit(self):
  self.write(self.valid())
  with patch.object(m,'MAX_BYTES',3),self.assertRaisesRegex(m.AuditError,'TRACE_SIZE_INVALID'):
   m.analyze_trace(self.path)
 def test_broken_json(self):
  self.path.write_text('{bad json}\n')
  with self.assertRaisesRegex(m.AuditError,'TRACE_JSON_INVALID'):m.analyze_trace(self.path)
 def test_unterminated_line(self):
  self.path.write_text(json.dumps(self.valid()[0]))
  with self.assertRaisesRegex(m.AuditError,'TRACE_UNTERMINATED_LINE'):m.analyze_trace(self.path)
 def test_unknown_kind(self):
  a=self.valid();a[1]['kind']='semantic_credit';self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_KIND_INVALID'):m.analyze_trace(self.path)
 def test_pid_seq_replay(self):
  a=self.valid();a[2]['seq']=2;self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_PID_SEQUENCE_GAP_OR_REPLAY'):m.analyze_trace(self.path)
 def test_pid_seq_gap(self):
  a=self.valid();a[2]['seq']=4;self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_PID_SEQUENCE_GAP_OR_REPLAY'):m.analyze_trace(self.path)
 def test_return_without_call(self):
  a=self.valid();a[1]['kind']='compute_return';self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_UNPAIRED_COMPUTE_RETURN'):m.analyze_trace(self.path)
 def test_unclosed_call(self):
  a=self.valid();a.pop(2);self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_OBSERVED_CALL_RETURN_UNBALANCED'):m.analyze_trace(self.path)
 def test_fake_compute_function(self):
  a=self.valid();a[1]['function']='_fake_verdict';self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_COMPUTE_FUNCTION_INVALID'):m.analyze_trace(self.path)
 def test_wrong_signature(self):
  a=self.valid();a[1]['declared_argument_names']=['node'];self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_SIGNATURE_UNEXPECTED'):m.analyze_trace(self.path)
 def test_monotone_host_clock(self):
  a=self.valid();a[2]['host_monotonic_ns']=1;self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_HOST_MONOTONIC_CLOCK_BACKWARDS'):m.analyze_trace(self.path)
 def test_provenance_outside_checkout(self):
  a=self.valid();self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_SOURCE_NOT_REPO_COMPUTE_LOCAL'):
   m.analyze_trace(self.path,Path('/a/different/repo'))
 def test_mark_capture_cap(self):
  a=self.valid();self.write(a)
  with patch.object(m,'PER_PROCESS_CAPTURE_CAP',2):
   j=m.analyze_trace(self.path)
  self.assertEqual(j['saturated_pid_count'],1)
  self.assertFalse(j['complete_execution_coverage_proven'])
 def test_invalid_probe_scope(self):
  a=self.valid();a[0]['scope']='native_attestation';self.write(a)
  with self.assertRaisesRegex(m.AuditError,'TRACE_SCOPE_INVALID'):m.analyze_trace(self.path)
 def test_max_line_size(self):
  a=self.valid();self.write(a)
  with patch.object(m,'MAX_LINE_BYTES',10),self.assertRaisesRegex(m.AuditError,'TRACE_LINE_SIZE_INVALID'):
   m.analyze_trace(self.path)
 def test_independent_process_without_compute_still_valid(self):
  self.write(self.valid());j=m.analyze_trace(self.path)
  self.assertEqual(j['process_count'],2)
 def test_native_no_go_when_cap_not_reached(self):
  self.write(self.valid());j=m.analyze_trace(self.path)
  self.assertFalse(j['native_learning_observed'])
if __name__=='__main__':unittest.main()
