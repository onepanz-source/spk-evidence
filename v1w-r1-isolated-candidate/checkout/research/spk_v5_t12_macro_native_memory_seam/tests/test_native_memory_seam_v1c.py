from __future__ import annotations
import types,unittest
from unittest.mock import patch
from research.spk_v5_t12_macro_native_memory_seam import native_bridge_v1c as bridge
from research.spk_v5_t12_macro_native_memory_seam import macro_gate_v1c

class OriginalServiceCandidateTests(unittest.TestCase):
 def test_bv_v0e_capacities_are_first(self):
  inputs=[]
  def constructor(fabric,pe_slots=0,fabric_slots_per_tick=0):
   inputs.append((pe_slots,fabric_slots_per_tick));return (pe_slots,fabric_slots_per_tick)
  module=types.ModuleType('spk_architecture_v1.temporal_service_v1b')
  constructor.__module__=module.__name__
  module.uniform_causal_service_plan_v1b=constructor
  def import_native(name):
   if name==module.__name__:return module
   raise ModuleNotFoundError(name=name)
  with patch.object(bridge.importlib,'import_module',side_effect=import_native):
   candidates,notes=bridge._native_service_plans(None,object())
  self.assertEqual(inputs[0],(3,4))
  self.assertEqual(candidates[0][1],(3,4))
 def test_real_v1c_issuer_preferred_over_fabrication(self):
  module=types.ModuleType('spk_architecture_v1.pe_service_v1c');token=object()
  def issuer(case,fabric,service_plan):return token
  issuer.__module__=module.__name__;module.admit_pe_service_v1c=issuer
  module2=types.ModuleType('spk_architecture_v1.temporal_service_v1b')
  def plan(fabric,pe_slots=0,fabric_slots_per_tick=0):return ('native_plan',pe_slots,fabric_slots_per_tick)
  plan.__module__=module2.__name__;module2.uniform_causal_service_plan_v1b=plan
  def import_native(name):
   if name==module.__name__:return module
   if name==module2.__name__:return module2
   raise ModuleNotFoundError(name=name)
  with patch.object(bridge.importlib,'import_module',side_effect=import_native):
   candidates,notes=bridge._native_service_plans(1,2)
  self.assertTrue(any(c is token for name,c in candidates))
 def test_no_native_constructor_fails_closed(self):
  with patch.object(bridge.importlib,'import_module',side_effect=lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name=name))):
   with self.assertRaisesRegex(ValueError,'NO_ORIGINAL_SERVICE_CANDIDATES'):
    bridge._native_service_plans(None,object())
 def test_original_memory_source_pins_retained(self):
  self.assertEqual(len(bridge.PINNED),5)
 def test_new_bridge_does_not_mutate_original(self):
  from research.spk_v5_t12_macro_native_memory_seam import native_bridge as old
  self.assertIsNot(old._native_service_plans,bridge._native_service_plans)
 def test_versioned_learning_claim_denied(self):
  receipt=bridge.native_policy_p_boundary({'counts':{'native_execution_access_authorizations':4,'native_learning_P_grants':0}}, {'new_v1_memory_grants':8})
  self.assertEqual(receipt['original_learning_P_grants'],0)
  self.assertFalse(receipt['promotion_allowed'])
 def test_new_report_schema(self):self.assertTrue(macro_gate_v1c.SCHEMA.endswith('/hotfix-v1c'))

if __name__=='__main__':unittest.main()
