from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('t3xyz',HERE/'t3xyz.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class T3XYZTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.trace=self.root/'profile.jsonl'
    def fire_python(self,capture='1'):
        env=os.environ.copy(); env['PYTHONPATH']=str(HERE/'instrument')
        env['SPK_T3XYZ_TRACE_FILE']=str(self.trace)
        env['SPK_T3XYZ_CAPTURE']=capture
        code='''import spk_t3xyz_hook\ndef _compute_local(node,state,timestamp,channels):\n    return (node,timestamp)\na=_compute_local('C', {}, 2, [1]);print(a)'''
        return subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    def test_probe_observes_real_python_function_not_a_verdict(self):
        r=self.fire_python()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("('C', 2)",r.stdout)
        s=m.read_trace(self.trace,self.root)
        self.assertEqual(s['events']['compute_call'],1)
        self.assertEqual(s['events']['compute_return'],1)
        self.assertEqual(s['events']['probe_loaded'],1)
        self.assertTrue(s['structural_compute_observed'])
        j=[json.loads(x) for x in self.trace.read_text().splitlines()]
        self.assertEqual(j[1]['locals']['node'],'C')
        self.assertEqual(j[1]['locals']['timestamp'],2)
        r2=m.interpretation(s,{'dual_replay':True,'host_posthoc_selection':True})
        self.assertFalse(r2['native_C_authored_single_pass_verdict_proven'])
        self.assertFalse(r2['native_operator_update_proven'])
    def test_probe_off_no_trace(self):
        r=self.fire_python('0')
        self.assertEqual(r.returncode,0)
        self.assertFalse(self.trace.exists())
    def test_invalid_report_fails_closed(self):
        for x in [None,[],{}, {'schema':'wrong'}, {'schema':'spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0','status':'wrong'}]:
            with self.subTest(x=x),self.assertRaises(m.GateError):m.validate_report(x)
    def test_genuine_t3opq_report_structurally_valid(self):
        fixture=HERE/'fixtures/reference_t3opq.json'
        self.assertEqual(m.sha_file(fixture),m.EXPECTED_T3OPQ_REPORT_SHA)
        r=json.loads(fixture.read_text()); c=m.validate_report(r)
        self.assertTrue(c['dual_replay']);self.assertEqual(c['shadow_eligible'],42)
    def test_tampered_schema_rejected(self):
        s={'schema':'spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0',
           'status':'SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING',
           'C_verdict_table':{'cases':180,'counts':{'REJECT_NO_UPDATE':138,'SHADOW_SOURCE_REPLAY_ELIGIBLE':42}},
           'total_online_episodes':720,'total_credited_updates':617,
           'claims_excluded':['dual BV-v0e source invocations','host selects terminal observer']}
        self.assertTrue(m.validate_report(s))
        for path,value in [('total_online_episodes',719),('total_credited_updates',618)]:
            bad=dict(s);bad[path]=value
            with self.assertRaises(m.GateError):m.validate_report(bad)
        bad=dict(s); bad['claims_excluded']=['dual BV-v0e source invocations']
        with self.assertRaises(m.GateError):m.validate_report(bad)
    def test_missing_profile_rejected(self):
        with self.assertRaises(m.GateError):m.read_trace(self.trace,self.root)
    def test_invalid_json_line_rejected(self):
        self.trace.write_text('not json\n')
        with self.assertRaises(m.GateError):m.read_trace(self.trace,self.root)
    def test_nonmonotonic_sequence_rejected(self):
        self.trace.write_text('\n'.join(json.dumps(x) for x in [
          {'pid':101,'seq':1,'kind':'probe_loaded'},
          {'pid':101,'seq':1,'kind':'probe_loaded'}])+'\n')
        with self.assertRaises(m.GateError):m.read_trace(self.trace,self.root)
    def test_unknown_kind_rejected(self):
        self.trace.write_text(json.dumps({'pid':99,'seq':1,'kind':'semantic_credit'})+'\n')
        with self.assertRaises(m.GateError):m.read_trace(self.trace,self.root)
    def test_only_probe_not_fabricated_compute(self):
        self.trace.write_text(json.dumps({'pid':99,'seq':1,'kind':'probe_loaded'})+'\n')
        r=m.read_trace(self.trace,self.root)
        self.assertFalse(r['structural_compute_observed'])
        self.assertFalse(m.interpretation(r,{'dual_replay':True,'host_posthoc_selection':True})['native_BV_semantic_receipt_proven'])
    def test_source_pin_fail_closed(self):
        for name in m.PINS:
            (self.root/name).parent.mkdir(parents=True,exist_ok=True)
            (self.root/name).write_text('tampered')
        for name in m.SCRIPTS:
            (self.root/name).parent.mkdir(parents=True,exist_ok=True)
            (self.root/name).write_text('fixture')
        with self.assertRaisesRegex(m.GateError,'FROZEN_PIN_MISMATCH'):m.source_snapshot(self.root)
    def test_missing_source_fail_closed(self):
        with self.assertRaisesRegex(m.GateError,'SOURCE_MISSING'):m.source_snapshot(self.root)
    def test_unexpected_semantic_promotion_context_rejected(self):
        s={'structural_compute_observed':True}
        with self.assertRaises(m.GateError):m.interpretation(s,{'dual_replay':False,'host_posthoc_selection':True})
        with self.assertRaises(m.GateError):m.interpretation(s,{'dual_replay':True,'host_posthoc_selection':False})
    def test_probe_captures_no_mutable_objects(self):
        r=self.fire_python()
        self.assertEqual(r.returncode,0)
        rows=[json.loads(x) for x in self.trace.read_text().splitlines()]
        entry=next(e for e in rows if e['kind']=='compute_call')
        self.assertEqual(entry['locals']['channels'],{'kind':'list','size':1})
    def test_trace_too_large_rejected(self):
        with patch.object(m,'MAX_TRACE_BYTES',4):
            self.trace.write_text('01234567')
            with self.assertRaisesRegex(m.GateError,'SIZE_INVALID'):m.read_trace(self.trace,self.root)
    def test_no_promotion_boolean(self):
        out=m.interpretation({'structural_compute_observed':True},{'dual_replay':True,'host_posthoc_selection':True})
        self.assertTrue(out['no_promotion'])
        self.assertFalse(any(out[k] for k in ('native_C_authored_single_pass_verdict_proven',
                                              'native_BV_semantic_receipt_proven',
                                              'native_operator_update_proven','independent_sensor_authentication')))

if __name__=='__main__':unittest.main()
