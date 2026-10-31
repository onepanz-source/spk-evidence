from __future__ import annotations
import json,hashlib,ast,tempfile,unittest
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam import native_bridge as b
from research.spk_v5_t12_macro_native_memory_seam import macro_gate as g
from research.spk_v5_t9abc_def_ghi.concurrent_engine_v1 import Reject

class NativeBridgeContract(unittest.TestCase):
    def test_parent_pin(self):self.assertEqual(len(g.T11_FWORK_SHA),64)
    def test_catalog_contains_five_pinned_modules(self):self.assertEqual(len(b.PINNED),5)
    def test_all_pins_valid(self):
        for name,value in b.PINNED.items():
            with self.subTest(name=name):
                self.assertEqual(len(value),64);int(value,16)
    def test_catalog_no_sources_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=b.pinned_source_catalog(tmp,require_sources=False)
            self.assertEqual(c['original_count'],0)
            self.assertEqual(len(c['missing']),5)
            self.assertFalse(c['source_loaded_by_execution'])
    def test_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Reject):b.pinned_source_catalog(tmp,require_sources=True)
    def test_fake_module_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel=list(b.PINNED)[0]
            p=Path(tmp)/rel;p.parent.mkdir(parents=True);p.write_text('def admit_memory_v1a(*args):return True\n')
            with self.assertRaises(Reject):b.pinned_source_catalog(tmp,require_sources=False)
    def test_catalog_ast_does_not_execute_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel=list(b.PINNED)[0];p=Path(tmp)/rel;p.parent.mkdir(parents=True)
            p.write_text('raise RuntimeError("do not import")\n')
            with self.assertRaises(Reject):b.pinned_source_catalog(tmp,require_sources=False)
    def test_native_learning_cannot_be_conferred_by_api_access(self):
        x={'counts':{'native_execution_access_authorizations':12,'native_learning_P_grants':0}}
        y=b.native_policy_p_boundary(x,{'new_v1_memory_grants':8})
        self.assertEqual((y['original_execution_access_authorizations'],y['original_learning_P_grants']), (12,0))
        self.assertFalse(y['promotion_allowed'])
    def test_fake_native_learning_does_not_pass(self):
        x={'counts':{'native_execution_access_authorizations':2,'native_learning_P_grants':1}}
        with self.assertRaises(Reject):b.native_policy_p_boundary(x,{'new_v1_memory_grants':8})
    def test_missing_v1_receipt_denied(self):
        x={'counts':{'native_execution_access_authorizations':0,'native_learning_P_grants':0}}
        with self.assertRaises(Reject):b.native_policy_p_boundary(x,None)
    def test_negative_v1_receipt_denied(self):
        x={'counts':{'native_execution_access_authorizations':0,'native_learning_P_grants':0}}
        with self.assertRaises(Reject):b.native_policy_p_boundary(x,{'new_v1_memory_grants':-1})
    def test_non_native_local_report_false_promotions(self):
        r=g.report('.',require_native=False)
        self.assertEqual(r['M4_versioned_new_runtime_P_parity']['new_v1_memory_grants'],8)
        self.assertEqual(r['M4_versioned_new_runtime_P_parity']['new_v1_memory_P_commits'],8)
        self.assertFalse(r['promotion_allowed'])
        self.assertEqual(r['M6_promotion_and_native_learning_boundary']['frozen_original_P_learning_grants'],0)
    def test_no_local_native_does_not_pretend_native(self):
        r=g.report('.',require_native=False)
        if r['M1_original_source_pin_catalog']['missing']:
            self.assertEqual(r['M2_original_memory_execution_probe']['original_api_attempts'],0)
            self.assertEqual(r['status'],'LOCAL_PARTIAL_CHECKOUT_NO_ORIGINAL_MEMORY_MODULES')
    def test_immutable_report_determinism(self):
        a=g.report('.',require_native=False)
        b_=g.report('.',require_native=False)
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b_,sort_keys=True))

if __name__=='__main__':unittest.main()
