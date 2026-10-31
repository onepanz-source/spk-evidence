"""T12 v1d tests: only original A1d outputs can enter projection."""
from __future__ import annotations
import tempfile, unittest, types
from pathlib import Path
from unittest.mock import patch
from research.spk_v5_t12_macro_native_memory_seam import native_bridge_v1d as b
from research.spk_v5_t12_macro_native_memory_seam import macro_gate_v1d as gate

class A1dProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.ctx=tempfile.TemporaryDirectory(prefix='t12-a1d-test-')
        self.addCleanup(self.ctx.cleanup)
        self.root=Path(self.ctx.name)
        (self.root/'spk_architecture_v1').mkdir()
        self.path=self.root/'spk_architecture_v1/pe_fault_v1d.py'
        self.path.write_text('# test-only fixture, never a native replacement\n')
        self.module=types.ModuleType(b.A1D_MODULE)
    def do(self,fn):
        fn.__module__=b.A1D_MODULE
        self.module.execute_failstop_v1d=fn
        with patch.object(b.importlib,'import_module',return_value=self.module),\
             patch.object(b.inspect,'getfile',return_value=str(self.path)):
            return b.original_a1d_execution(self.root,object(),object(),object(),object())
    def test_genuine_a1d_closed_shape_with_producer_provenance(self):
        def fn(case,fabric):
            return {'status':'CLOSED','result':{'observations':{'batches':[],'routes':[]},
                     'processed_batches':0,'processed_events':0}}
        r,meta=self.do(fn)
        self.assertEqual(r['status'],'CLOSED')
        self.assertEqual(meta['producer'],b.A1D_MODULE+'.execute_failstop_v1d')
        self.assertEqual(meta['source_sha256'],b.sha(self.path))
    def test_genuine_a1d_fault_prefix(self):
        def fn(case,fabric):
            return {'status':'PE_FAULT','committed_prefix':{'observations':{'batches':[],'routes':[]},
                     'processed_batches':0,'processed_events':0}}
        r,_=self.do(fn)
        self.assertEqual(r['status'],'PE_FAULT')
    def test_refuse_A1b_unwrapped_even_if_batches_present(self):
        def fn(case,fabric):
            return {'result':{'observations':{'batches':[],'routes':[]}}}
        with self.assertRaisesRegex(b.A1dUnavailable,'NO_VALID_ORIGINAL_A1D_RESULT'):
            self.do(fn)
    def test_refuse_missing_observations(self):
        def fn(case,fabric):return {'status':'CLOSED','result':{'processed_events':0}}
        with self.assertRaisesRegex(b.A1dUnavailable,'MISSING_A1D_OBSERVATIONS'):
            self.do(fn)
    def test_refuse_unknown_required_parameter(self):
        def fn(case,fabric,invalid_required):return {'status':'CLOSED'}
        with self.assertRaisesRegex(b.A1dUnavailable,'REQUIRED_ORIGINAL_PARAMETER'):
            b._invoke_a1d(fn,None,None,None,None)
    def test_optional_parameters_remain_original_defaults(self):
        def fn(case,fabric,fault_after_grant=None):return fault_after_grant
        self.assertIsNone(b._invoke_a1d(fn,1,2,3,4))
    def test_original_admission_and_service_provided_if_required(self):
        admission=object();service=object()
        def fn(case,fabric,admission,service_plan):return (admission,service_plan)
        self.assertEqual(b._invoke_a1d(fn,1,2,admission,service),(admission,service))
    def test_imported_A1b_executor_not_considered_original_A1d(self):
        def fn(case,fabric):return {}
        fn.__module__='spk_architecture_v1.pe_execution_v1b'
        self.module.execute_on_pes_v1b=fn
        self.assertEqual(b.a1d_entrypoints(self.module),[])
    def test_refuse_module_path_mismatch(self):
        def fn(case,fabric):return {'status':'CLOSED'}
        fn.__module__=b.A1D_MODULE
        self.module.execute_failstop_v1d=fn
        with patch.object(b.importlib,'import_module',return_value=self.module),\
             patch.object(b.inspect,'getfile',return_value=__file__):
            with self.assertRaisesRegex(b.A1dUnavailable,'MODULE_PATH'):
                b.original_a1d_execution(self.root,1,2,3,4)
    def test_refuse_unavailable_native_source(self):
        self.path.unlink()
        with self.assertRaisesRegex(b.A1dUnavailable,'SOURCE_UNAVAILABLE'):
            b.original_a1d_execution(self.root,1,2,3,4)
    def test_no_original_module_monkeypatch_shipped(self):
        source=Path(b.__file__).read_text()
        self.assertNotIn("'status':'CLOSED','result'",source)
        self.assertNotIn('execute_on_pes_v1b(',source)
    def test_gate_requires_full_chain(self):
        source=Path(gate.__file__).read_text()
        self.assertIn("native['counts']['completed_original_memory_chains']>=1",source)
        self.assertNotIn("native['counts']['native_execution_memory_admissions']>=1",source)
    def test_learning_p_denial_preserved(self):
        original={'counts':{'native_execution_access_authorizations':4,'native_learning_P_grants':0}}
        r=b.native_policy_p_boundary(original,{'new_v1_memory_grants':8})
        self.assertFalse(r['promotion_allowed']);self.assertEqual(r['original_learning_P_grants'],0)

if __name__=='__main__':unittest.main()
