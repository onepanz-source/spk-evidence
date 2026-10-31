"""Pure boundary tests; not claimed as real BV native integration."""
from __future__ import annotations
import dataclasses
import importlib.util
import pathlib
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

MOD=pathlib.Path(__file__).resolve().parents[1]/'t4def.py'
spec=importlib.util.spec_from_file_location('spk_t4def',MOD)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@dataclasses.dataclass(frozen=True)
class Node:
    node_id:str
    instructions:tuple
@dataclasses.dataclass(frozen=True)
class Ev:
    node_id:str
    channel:int
    timestamp:int
@dataclasses.dataclass(frozen=True)
class Case:
    nodes:tuple
    events:tuple

def fake_case(_m,_arm):
    return Case((Node('A',(('EMIT',7),)),Node('C',(('EMIT',11),('EMIT',12),('RESET',0)))),(Ev('C',6,15),Ev('A',5,12)))

def synthetic(sign=1,terminal=True,grants=2):
    return {'schema':'spk-bv-live-dual-event-scheduler/v0e',
      'forward':{'terminal':[{'node_id':'C','channel':30}] if terminal else []},
      'feedback':{'assessments':[{'input_occurrences':[1,2]}] if terminal else [],
                  'deliveries':[{'sender':'C','receiver':'B','independent_receiver':True,'tick':1},
                                {'sender':'B','receiver':'A','independent_receiver':True,'tick':2}] if grants else [],
                  'link_grants':[{}]*grants},
      'resources':{'bv_link_grants':grants,'bv_service_units':grants,'bv_memory_units':2*grants,
                   'timeline':[{'link_total':2}]}}

def witness(sign=1):return {'C_computed_verdict':sign,'status':'C_authored_credit_delivered','A_consumed_credit':sign}

class TestSingleSourceResearch(unittest.TestCase):
    def test_single_fixed_terminal_positive_and_negative(self):
        result=m.fixed_terminal_case(None,'current',fake_case)
        ci=result.nodes[1].instructions
        self.assertEqual(ci,(('EMIT',11),('EMIT',30),('EMIT',12),('EMIT',30),('RESET',0)))
        self.assertEqual(result.events[0].timestamp,14)
        self.assertEqual(result.events[1].timestamp,12)
    def test_static_terminal_does_not_encode_sign(self):
        ci=m.fixed_terminal_case(None,'current',fake_case).nodes[1].instructions
        self.assertEqual([v for op,v in ci if op=='EMIT' and v>=30],[30,30])
    def test_missing_c_node_rejected(self):
        with self.assertRaisesRegex(m.BoundaryError,'C_NEURON_MISSING'):
            m.fixed_terminal_case(None,'current',lambda *_:Case((Node('A',()),),()))
    def test_valid_positive_structural(self):
        row=m.evaluate_source_result(synthetic(),witness(1))
        self.assertTrue(row['research_structural_eligible'])
        self.assertFalse(row['source_transmits_semantic_sign'])
        self.assertFalse(row['single_native_semantic_BV'])
    def test_valid_negative_structural(self):
        self.assertTrue(m.evaluate_source_result(synthetic(-1),witness(-1))['research_structural_eligible'])
    def test_no_terminal_no_semantic(self):
        r=synthetic(sign=None,terminal=False,grants=0)
        row=m.evaluate_source_result(r,witness(None))
        self.assertFalse(row['research_structural_eligible'])
    def test_missing_credit_chain_rejected_as_eligibility(self):
        r=synthetic(grants=0)
        self.assertFalse(m.evaluate_source_result(r,witness(1))['research_structural_eligible'])
    def test_duplicate_terminal_rejected(self):
        r=synthetic();r['forward']['terminal'].append({'node_id':'C','channel':30})
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_missing_assessment_rejected(self):
        r=synthetic();r['feedback']['assessments']=[]
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_empty_parent_ancestry_rejected(self):
        r=synthetic();r['feedback']['assessments'][0]['input_occurrences']=[]
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_without_terminal_sign_rejected(self):
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(synthetic(),witness(None))
    def test_with_sign_but_no_terminal_rejected(self):
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(synthetic(terminal=False,grants=0),witness(1))
    def test_invalid_semantic_sign_rejected(self):
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(synthetic(),witness(2))
    def test_resource_service_drift_rejected(self):
        r=synthetic();r['resources']['bv_service_units']=1
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_resource_memory_drift_rejected(self):
        r=synthetic();r['resources']['bv_memory_units']=2
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_resource_overcommit_rejected(self):
        r=synthetic();r['resources']['timeline'][0]['link_total']=3
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_schema_forgery_rejected(self):
        r=synthetic();r['schema']='invented'
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_missing_feedback_rejected(self):
        r=synthetic();del r['feedback']
        with self.assertRaises(m.BoundaryError):m.evaluate_source_result(r,witness())
    def test_wrong_receiver_rejects_eligibility(self):
        r=synthetic();r['feedback']['deliveries'][1]['receiver']='C'
        self.assertFalse(m.evaluate_source_result(r,witness())['research_structural_eligible'])
    def test_unindependent_receiver_rejects_eligibility(self):
        r=synthetic();r['feedback']['deliveries'][0]['independent_receiver']=False
        self.assertFalse(m.evaluate_source_result(r,witness())['research_structural_eligible'])
    def test_missing_T3h_credit_rejects_eligibility(self):
        w=witness();w['A_consumed_credit']=None
        self.assertFalse(m.evaluate_source_result(synthetic(),w)['research_structural_eligible'])
    def test_broken_T3h_status_rejects_eligibility(self):
        w=witness();w['status']='reverse_delivery_lost'
        self.assertFalse(m.evaluate_source_result(synthetic(),w)['research_structural_eligible'])
    def test_deterministic_source_digest(self):
        r=synthetic();self.assertEqual(m.evaluate_source_result(r,witness())['source_receipt_sha256'],m.digest_json(r))
    def test_source_pins_count(self):self.assertEqual(len(m.FROZEN)+len(m.SOURCE_PINS),8)
    def test_bundle_has_original_t3o_sha_pins(self):
        source=pathlib.Path.cwd()/'spk_v5_research/island_source_bv_bridge_v5t3o.py'
        if source.is_file():
            self.assertEqual(m.digest_bytes(source),m.BRIDGE_SHA)
    def test_ast_locus_original(self):
        p=pathlib.Path.cwd()/'spk_v5_research/island_source_bv_bridge_v5t3o.py'
        if p.is_file(): self.assertTrue(m.dual_replay_locus(p)['posthoc_sign_selection'])
    def test_ast_locus_detects_mutation(self):
        p=pathlib.Path.cwd()/'spk_v5_research/island_source_bv_bridge_v5t3o.py'
        if p.is_file():
            s=p.read_text().replace('passes={str(ch):_source_pass(case,fabric,ch) for ch in (30,31)}','passes={}')
            with tempfile.TemporaryDirectory() as d:
                q=pathlib.Path(d)/'orig.py';q.write_text(s)
                with self.assertRaises(m.BoundaryError):m.dual_replay_locus(q)
    def test_no_extra_BV_invocation_visible_AST(self):
        tree=__import__('ast').parse(MOD.read_text());fn=next(x for x in tree.body if isinstance(x,__import__('ast').FunctionDef) and x.name=='run_one')
        calls=[x for x in __import__('ast').walk(fn) if isinstance(x,__import__('ast').Call) and isinstance(x.func,__import__('ast').Name) and x.func.id=='execute_live_v0e']
        self.assertEqual(len(calls),1)
    def test_explicit_nonpromotion(self):
        code=MOD.read_text()
        for label in ('native_semantic_BV_proven\':False','native_learning_proven\':False','promotion_allowed\':False'):
            self.assertIn(label,code)
    def test_evidence_dossier_digest(self):
        p=pathlib.Path('/tmp/spk-v5-t4abc-causal-origin.json')
        if p.is_file():self.assertEqual(m.digest_bytes(p),m.DOSSIER_SHA)

if __name__=='__main__':unittest.main()
