import json
from pathlib import Path
import sys
import tempfile
import unittest
from research.spk_v5_t4zabc import t4zabc as z

class Node:
    def __init__(self,name):self.node_id=name

def _compute_local(node,state,timestamp,channels):return node.node_id

def execute_on_pes_v1b():return _compute_local(Node('C'),{},14,(3,))

def execute_live_v0e():return {'forward':'test'}

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.path=__file__
    def test_positive_probe(self):
        val,res=z.record_one(execute_on_pes_v1b,self.path,'/tmp/nonexistent')
        self.assertEqual(val,'C');self.assertEqual(res['pe_C_compute_calls'],1)
        self.assertEqual(res['pe_executor_calls'],1)
        self.assertEqual(res['pe_compute_calls'],1)
        self.assertEqual(res['bv_scheduler_calls'],0)
    def test_negative_probe(self):
        _,res=z.record_one(execute_live_v0e,self.path,self.path)
        self.assertEqual(res['bv_scheduler_calls'],1)
        self.assertEqual(res['pe_compute_calls'],0)
    def test_two_roles(self):
        def role():
            _compute_local(Node('C'),{},14,(3,))
            _compute_local(Node('B'),{},15,(3,))
        _,res=z.record_one(role,self.path,self.path)
        self.assertEqual(res['pe_compute_calls'],2)
        self.assertEqual(res['pe_C_compute_calls'],1)
        self.assertEqual(res['pe_node_id_counts']['B'],1)
    def test_restoration_normal(self):
        prior=sys.getprofile()
        z.record_one(execute_on_pes_v1b,self.path,self.path)
        self.assertIs(sys.getprofile(),prior)
    def test_restoration_exception(self):
        def explode():raise RuntimeError('boom')
        prior=sys.getprofile()
        with self.assertRaisesRegex(RuntimeError,'boom'):
            z.record_one(explode,self.path,self.path)
        self.assertIs(sys.getprofile(),prior)
    def test_existing_profiler_refused(self):
        def previous(frame,event,arg):pass
        sys.setprofile(previous)
        try:
            with self.assertRaisesRegex(z.BoundaryError,'EXISTING_PROFILER_REFUSED'):
                z.record_one(execute_on_pes_v1b,self.path,self.path)
            self.assertIs(sys.getprofile(),previous)
        finally:sys.setprofile(None)
    def test_classify_zero_compute(self):
        good={'pe_compute_calls':1,'pe_C_compute_calls':1,'bv_scheduler_calls':0}
        row={'probe':{'bv_scheduler_calls':1,'pe_compute_calls':0,'pe_C_compute_calls':0}}
        self.assertEqual(z.classify(good,[row]*180),'FROZEN_BV_V0E_DOES_NOT_ENTER_FROZEN_PE_V1B_COMPUTE_ON_THIS_WORKLOAD')
    def test_classify_pe_but_no_c(self):
        good={'pe_compute_calls':1,'pe_C_compute_calls':1,'bv_scheduler_calls':0}
        row={'probe':{'bv_scheduler_calls':1,'pe_compute_calls':1,'pe_C_compute_calls':0}}
        self.assertEqual(z.classify(good,[row]*180),'BV_V0E_ENTERS_PE_V1B_BUT_NO_NODE_C_COMPUTE_OBSERVED')
    def test_classify_c(self):
        good={'pe_compute_calls':1,'pe_C_compute_calls':1,'bv_scheduler_calls':0}
        row={'probe':{'bv_scheduler_calls':1,'pe_compute_calls':1,'pe_C_compute_calls':1}}
        self.assertEqual(z.classify(good,[row]*180),'BV_V0E_PE_V1B_C_COMPUTE_OBSERVED_WITH_HOST_ONLY_PROVENANCE')
    def test_missing_positive_refused(self):
        good={'pe_compute_calls':0,'pe_C_compute_calls':0,'bv_scheduler_calls':0}
        row={'probe':{'bv_scheduler_calls':1,'pe_compute_calls':0,'pe_C_compute_calls':0}}
        with self.assertRaisesRegex(z.BoundaryError,'POSITIVE_A1B_PROBE_DID_NOT_OBSERVE_C'):
            z.classify(good,[row]*180)
    def test_missing_bv_refused(self):
        good={'pe_compute_calls':1,'pe_C_compute_calls':1,'bv_scheduler_calls':0}
        row={'probe':{'bv_scheduler_calls':0,'pe_compute_calls':0,'pe_C_compute_calls':0}}
        with self.assertRaisesRegex(z.BoundaryError,'BV_LIVE_SCHEDULER_ENTRY_NOT_OBSERVED'):
            z.classify(good,[row]*180)
    def test_missing_case_refused(self):
        good={'pe_compute_calls':1,'pe_C_compute_calls':1,'bv_scheduler_calls':0}
        with self.assertRaisesRegex(z.BoundaryError,'SOURCE_CASE_COUNT_DRIFT'):
            z.classify(good,[{'probe':{'bv_scheduler_calls':1}}]*179)
    def test_probe_total_limit(self):
        old=z.MAX_CALLS
        z.MAX_CALLS=2
        try:
            with self.assertRaisesRegex(z.BoundaryError,'PE_PROBE_CALL_LIMIT_EXCEEDED'):
                def many():
                    for _ in range(4):_compute_local(Node('C'),{},14,())
                z.record_one(many,self.path,self.path)
        finally:z.MAX_CALLS=old
        self.assertIsNone(sys.getprofile())
    def test_probe_label_limit(self):
        old=z.MAX_SUMMARY_LABELS;z.MAX_SUMMARY_LABELS=1
        try:
            with self.assertRaisesRegex(z.BoundaryError,'PE_PROBE_NODE_LABEL_LIMIT_EXCEEDED'):
                def many():
                    _compute_local(Node('C'),{},14,())
                    _compute_local(Node('B'),{},14,())
                z.record_one(many,self.path,self.path)
        finally:z.MAX_SUMMARY_LABELS=old
        self.assertIsNone(sys.getprofile())
    def test_output_bounded_sample(self):
        def many():
            for _ in range(50):_compute_local(Node('C'),{},14,())
        _,x=z.record_one(many,self.path,self.path)
        self.assertEqual(x['pe_compute_calls'],50)
        self.assertEqual(len(x['observed_PE_entry_examples']),12)
    def test_untrusted_marking(self):
        _,x=z.record_one(execute_on_pes_v1b,self.path,self.path)
        self.assertEqual(x['source_kind'],'CPYTHON_FRAME_OBSERVATION_UNTRUSTED')
    def test_canon_deterministic(self):
        self.assertEqual(z.canon({'a':1,'b':2}),z.canon({'b':2,'a':1}))
    def test_digest_different(self):
        self.assertNotEqual(z.digest([1]),z.digest([2]))
    def test_digest_stable(self):
        self.assertEqual(z.digest({'x':1}),z.digest({'x':1}))
    def test_source_refusal_pins(self):
        self.assertIn('T4ZAB',z.__doc__)
    def test_sha_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'f';p.write_bytes(b'test')
            self.assertEqual(z.fsha(p),'9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08')
    def test_node_type_unidentified(self):
        class NoName:pass
        def _compute_local(node,state,timestamp,channels):return None
        def fn():_compute_local(NoName(),{},14,())
        _,x=z.record_one(fn,self.path,self.path)
        self.assertEqual(x['pe_node_id_counts']['<unidentified>'],1)
    def test_code_filename_not_name_only(self):
        _,x=z.record_one(execute_on_pes_v1b,'/tmp/nonexistent','/tmp/nonexistent')
        self.assertEqual(x['pe_compute_calls'],0)
        self.assertEqual(x['bv_scheduler_calls'],0)
    def test_callgraph_does_not_patch_compute(self):
        original=_compute_local
        z.record_one(execute_on_pes_v1b,self.path,self.path)
        self.assertIs(original,_compute_local)
    def test_no_fake_native_promotion(self):
        _,res=z.record_one(execute_on_pes_v1b,self.path,self.path)
        self.assertNotIn('authenticated',json.dumps(res))
    def test_require(self):
        with self.assertRaisesRegex(z.BoundaryError,'NO'):
            z.require(False,'NO')
    def test_profile_not_left_behind_by_nested_exception(self):
        def bad():
            execute_on_pes_v1b()
            raise ValueError('x')
        with self.assertRaises(ValueError):z.record_one(bad,self.path,self.path)
        self.assertIsNone(sys.getprofile())

if __name__=='__main__':unittest.main()
