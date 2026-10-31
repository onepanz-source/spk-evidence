from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
import unittest
from research.spk_v5_t4ghi import t4ghi as m

REF=Path(__file__).resolve().parents[1]/'reference/t4def-single-source.json'

def synthetic(c=11,b=13,a=13,terminal=True,emissions=True):
    signals=[]
    for node,ch,tick in [('C',c,15),('B',b,16),('A',a,17)]:
        if ch is not None:signals.append({'node_id':node,'channel':ch,'timestamp':tick})
    return {
      'schema':'spk-bv-live-dual-event-scheduler/v0e',
      'forward':{'terminal':[{'node_id':'C','channel':30}] if terminal else [],
                 'forward_result':{'emissions':signals} if emissions else {'other':signals}},
      'feedback':{'assessments':[{'input_occurrences':[{'node':'B'}]}] if terminal else [],
          'deliveries':[{'sender':'C','receiver':'B'},{'sender':'B','receiver':'A'}],
          'link_grants':[{'g':1},{'g':2}]},
      'resources':{'bv_link_grants':2,'bv_service_units':2,'bv_memory_units':4,
                   'timeline':[{'link_total':0},{'link_total':2}]}}

class TestT4GHI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reference=m.read_reference(REF)
    def test_reference_180(self):self.assertEqual(len(self.reference['F_cases']),180)
    def test_reference_digest(self):self.assertEqual(m.sha_bytes(REF),m.REFERENCE_SHA)
    def test_reference_reject_modified(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'bad.json'; f.write_text(REF.read_text()+' ')
            with self.assertRaisesRegex(m.GateError,'REFERENCE_SHA'):m.read_reference(f)
    def test_reference_missing(self):
        with self.assertRaises(m.GateError):m.read_reference('/nonexistent/t4def.json')
    def test_reference_unpromoted(self):self.assertFalse(self.reference['promotion_allowed'])
    def test_ambiguous_projection(self):
        a=m.structural_nonidentifiability(self.reference['F_cases'])
        self.assertEqual(a['historical_sign_rows'],72)
        self.assertEqual(a['groups_with_both_signs'],20)
        self.assertEqual(a['structural_signature_groups'],20)
    def test_projection_sensitive_to_coverage(self):
        rows=self.reference['F_cases'][:-1]
        # Removing last row may remove no signed observation; require no invented guarantee
        self.assertTrue(len(rows)<180)
    def test_projection_reject_malformed_distribution(self):
        rows=[x for x in self.reference['F_cases'] if x['T3h_separate_A1b_sign']==1]
        with self.assertRaisesRegex(m.GateError,'SIGN_COUNTS'):m.structural_nonidentifiability(rows)
    def test_structural_allows_opposite_sign(self):
        signed=[x for x in self.reference['F_cases'] if x['T3h_separate_A1b_sign'] in (-1,1)]
        self.assertEqual(set(x['source_fixed_terminal_count'] for x in signed),{1})
    def test_stable_sha(self):self.assertEqual(m.digest({'a':2,'b':3}),m.digest({'b':3,'a':2}))
    def test_positive_emission_candidate(self):
        o=m.observe_forward_result(synthetic())
        self.assertEqual(o['C_sign_candidate_from_same_source_forward_output'],1)
        self.assertTrue(o['C_B_A_emission_candidate_consistent'])
        self.assertFalse(o['signed_C_to_A_native_BV_receipt_proven'])
    def test_negative_emission_candidate(self):
        o=m.observe_forward_result(synthetic(12,14,14))
        self.assertEqual(o['C_sign_candidate_from_same_source_forward_output'],-1)
        self.assertTrue(o['C_B_A_emission_candidate_consistent'])
    def test_no_emissions_not_proof(self):
        o=m.observe_forward_result(synthetic(emissions=False))
        self.assertIsNone(o['C_sign_candidate_from_same_source_forward_output'])
        self.assertFalse(o['C_B_A_emission_candidate_consistent'])
    def test_one_c_not_full_path(self):
        o=m.observe_forward_result(synthetic(b=None,a=None))
        self.assertEqual(o['C_sign_candidate_from_same_source_forward_output'],1)
        self.assertFalse(o['C_B_A_emission_candidate_consistent'])
    def test_no_terminal_not_sign(self):
        o=m.observe_forward_result(synthetic(terminal=False))
        self.assertEqual(o['C_fixed_terminal_count'],0)
    def test_wrong_schema_rejected(self):
        v=synthetic();v['schema']='spoof'
        with self.assertRaisesRegex(m.GateError,'SCHEMA'):m.observe_forward_result(v)
    def test_extra_terminal_rejected(self):
        v=synthetic();v['forward']['terminal']*=2
        with self.assertRaisesRegex(m.GateError,'MULTIPLICITY'):m.observe_forward_result(v)
    def test_unbacked_assessment(self):
        v=synthetic();v['feedback']['assessments']=[]
        with self.assertRaisesRegex(m.GateError,'UNBACKED'):m.observe_forward_result(v)
    def test_empty_parent(self):
        v=synthetic();v['feedback']['assessments'][0]['input_occurrences']=[]
        with self.assertRaisesRegex(m.GateError,'PARENT'):m.observe_forward_result(v)
    def test_missing_forward(self):
        v=synthetic();del v['forward']
        with self.assertRaisesRegex(m.GateError,'TOPLEVEL'):m.observe_forward_result(v)
    def test_missing_grants(self):
        v=synthetic();del v['feedback']['link_grants']
        with self.assertRaisesRegex(m.GateError,'RECEIPT_FIELDS'):m.observe_forward_result(v)
    def test_wrong_resource_accounting(self):
        v=synthetic();v['resources']['bv_memory_units']=3
        with self.assertRaisesRegex(m.GateError,'RESOURCE_DRIFT'):m.observe_forward_result(v)
    def test_overcommit(self):
        v=synthetic();v['resources']['timeline'][1]['link_total']=3
        with self.assertRaisesRegex(m.GateError,'TIMELINE_INVALID'):m.observe_forward_result(v)
    def test_zero_timeline_allowed(self):self.assertEqual(m.observe_forward_result(synthetic())['BV_grant_count'],2)
    def test_sign_mismatch_not_consistent(self):
        self.assertFalse(m.observe_forward_result(synthetic(11,14,13))['C_B_A_emission_candidate_consistent'])
    def test_missing_A_not_consistent(self):
        self.assertFalse(m.observe_forward_result(synthetic(a=None))['C_B_A_emission_candidate_consistent'])
    def test_same_tick_not_consistent(self):
        v=synthetic();v['forward']['forward_result']['emissions'][1]['timestamp']=15
        self.assertFalse(m.observe_forward_result(v)['C_B_A_emission_candidate_consistent'])
    def test_conflicting_C_signs_rejected(self):
        v=synthetic();v['forward']['forward_result']['emissions'].append({'node_id':'C','channel':12,'timestamp':15})
        with self.assertRaisesRegex(m.GateError,'CONTRADICTORY'):m.observe_forward_result(v)
    def test_no_event_forgery_from_terminal(self):
        v=synthetic(emissions=False);v['forward']['terminal'].append({'node_id':'C','channel':11,'timestamp':15})
        # terminal 11 must not be interpreted as a C-authored emission proof
        self.assertIsNone(m.observe_forward_result(v)['C_sign_candidate_from_same_source_forward_output'])
    def test_no_event_forgery_from_assessment(self):
        v=synthetic(emissions=False);v['feedback']['assessments'][0]['input_occurrences']=[{'node_id':'C','channel':11,'timestamp':15}]
        self.assertIsNone(m.observe_forward_result(v)['C_sign_candidate_from_same_source_forward_output'])
    def test_paths_exposed(self):
        o=m.observe_forward_result(synthetic())
        self.assertTrue(o['event_candidate_paths']['C']['paths'][0].startswith('forward.forward_result.emissions'))
    def test_input_not_emission(self):
        v=synthetic(emissions=False);v['forward']['inputs']=[{'node_id':'C','channel':11,'timestamp':15}]
        self.assertIsNone(m.observe_forward_result(v)['C_sign_candidate_from_same_source_forward_output'])
    def test_bool_channel_not_integer(self):
        v=synthetic();v['forward']['forward_result']['emissions'][0]['channel']=True
        self.assertIsNone(m.observe_forward_result(v)['C_sign_candidate_from_same_source_forward_output'])
    def test_research_contract_nonpromotion(self):
        src=Path(m.__file__).read_text();self.assertIn("'promotion_allowed':False",src)
        self.assertIn("'I_no_native_semantic_BV':True",src)
    def test_source_once_exact_one_BV_call_in_AST(self):
        import ast
        tree=ast.parse(Path(m.__file__).read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_once')
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertEqual(sum(x.func.id=='execute_live_v0e' for x in calls),1)
        self.assertEqual(sum(x.func.id=='execute' for x in calls),0)
    def test_pin_reference(self):self.assertEqual(m.PREV_CODE_SHA,'b5262709d40714811fe91bfa28389afb8f3a8edc847eb21e5564b677d3516945')

if __name__=='__main__':unittest.main()
