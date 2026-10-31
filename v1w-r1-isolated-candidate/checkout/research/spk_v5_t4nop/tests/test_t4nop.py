from __future__ import annotations
import ast
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from research.spk_v5_t4nop import t4nop as m
from research.spk_v5_t4jkl_fix import t4jkl_fix as prev

REF=Path(__file__).resolve().parents[1]/'reference/t4jklm-control-flag.json'
GHI=Path(__file__).resolve().parents[2]/'spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'

def delivery_pair():
    base={'assessment_id':'as-1','evidence_ids':['ev-1'],
          'independent_receiver':True,'packet_id':'pkt-1',
          'receiver':'B','sender':'C','tick':14}
    second={**base,'packet_id':'pkt-2','sender':'B','receiver':'A','tick':15}
    return [base,second]

def forged_receipt():
    return {'semantic_sign':1,'C_emission_id':'em-1','authenticator':'host-fake',
            'source_identity':'C','causal_parent_id':'src-1'}

class ReceiverBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=m.load_reference(REF)
        cls.ghi=prev.reference(GHI)

    def test_reference_sha(self):self.assertEqual(m.sha(REF),m.REF_SHA)
    def test_case_count(self):self.assertEqual(len(self.ref['L_rows']),180)
    def test_producer_parity(self):self.assertTrue(self.ref['L_source_result_parity_180'])
    def test_recipe_controls(self):self.assertTrue(self.ref['L_recipe_flag_comparisons_180'])
    def test_prior_no_promotion(self):self.assertFalse(self.ref['promotion_allowed'])
    def test_prev_native_false(self):self.assertFalse(self.ref['native_receiver_semantic_receipt_proven'])
    def test_24_research_guard(self):self.assertEqual(self.ref['K_offline']['research_guard_eligible_count'],24)
    def test_72_signs_from_actual_source_reference(self):
        rows=self.ghi['H_rows']
        self.assertEqual(sum(r['C_sign_candidate_from_same_source_forward_output'] in (1,-1) for r in rows),72)
    def test_36_each_sign(self):
        signs=[r['C_sign_candidate_from_same_source_forward_output'] for r in self.ghi['H_rows']]
        self.assertEqual(signs.count(1),36); self.assertEqual(signs.count(-1),36)
    def test_receiver_delivery_schema_is_nonsemantic(self):
        self.assertEqual(m.EXPECTED_DELIVERY_FIELDS,set(self.ref['L_rows'][0]['receiver_field_inventory']['delivery_field_names']))
        self.assertFalse(m.SEMANTIC_REQUIRED & m.EXPECTED_DELIVERY_FIELDS)
    def test_unseen_output_rejected(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'wrong.json';p.write_text(REF.read_text()+' ')
            with self.assertRaisesRegex(m.GateError,'REFERENCE_SHA_DRIFT'):m.load_reference(p)
    def test_symlink_ref_rejected(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'link.json';p.symlink_to(REF)
            with self.assertRaisesRegex(m.GateError,'REFERENCE_MISSING_OR_SYMLINK'):m.load_reference(p)
    def test_missing_reference_rejected(self):
        with self.assertRaisesRegex(m.GateError,'REFERENCE_MISSING_OR_SYMLINK'):m.load_reference('/path/that/does/not/exist.json')
    def test_plus_visible_is_not_receipt(self):
        x=m.field_inventory(1,delivery_pair(),'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
        self.assertFalse(x['native_receiver_semantic_credit'])
        self.assertFalse(x['semantic_sign_in_receiver_delivery'])
    def test_minus_visible_is_not_receipt(self):
        x=m.field_inventory(-1,delivery_pair(),'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
        self.assertFalse(x['native_source_authentication_verifiable'])
    def test_no_sign_no_receipt(self):
        self.assertFalse(m.field_inventory(None,[], 'NO_SOURCE_SIGN')['native_receiver_semantic_credit'])
    def test_application_forward_disabled_not_credit(self):
        x=m.field_inventory(1,delivery_pair(),'APPLICATION_FORWARD_GUARD_BLOCK')
        self.assertFalse(x['native_receiver_semantic_credit'])
    def test_reverse_lost_not_credit(self):
        x=m.field_inventory(-1,delivery_pair(),'NO_CAUSAL_EMISSION_TRIPLE')
        self.assertFalse(x['native_receiver_semantic_credit'])
    def test_sign_booleans_rejected(self):
        with self.assertRaisesRegex(m.GateError,'SIGN_INVALID'):m.field_inventory(True,delivery_pair(),'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    def test_sign_wrong_rejected(self):
        with self.assertRaisesRegex(m.GateError,'SIGN_INVALID'):m.field_inventory(0,delivery_pair(),'NO_SOURCE_SIGN')
    def test_unknown_class_rejected(self):
        with self.assertRaisesRegex(m.GateError,'CLASS_INVALID'):m.field_inventory(1,delivery_pair(),'NATIVE_CREDIT')
    def test_missing_delivery_key_rejected(self):
        rows=delivery_pair();del rows[0]['packet_id'];del rows[1]['packet_id']
        with self.assertRaisesRegex(m.GateError,'UNREVIEWED_RECEIVER_SCHEMA'):m.field_inventory(1,rows,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    def test_one_delivery_rejected(self):
        with self.assertRaisesRegex(m.GateError,'DELIVERY_COUNT_INVALID'):m.field_inventory(1,delivery_pair()[:1],'NO_SOURCE_SIGN')
    def test_bad_route_rejected(self):
        rows=delivery_pair();rows[1]['receiver']='C'
        with self.assertRaisesRegex(m.GateError,'DELIVERY_ROUTE_INVALID'):m.field_inventory(1,rows,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    def test_mixed_fields_rejected(self):
        rows=delivery_pair();rows[0]['bogus']='x'
        with self.assertRaisesRegex(m.GateError,'DELIVERY_FIELD_INCONSISTENT'):m.field_inventory(1,rows,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    def test_injected_semantic_sign_rejected_as_unknown_schema(self):
        rows=delivery_pair()
        for row in rows:row['semantic_sign']=1
        with self.assertRaisesRegex(m.GateError,'UNREVIEWED_RECEIVER_SCHEMA'):m.field_inventory(1,rows,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT')
    def test_bad_tick_rejected(self):
        rows=delivery_pair();rows[0]['tick']='14'
        with self.assertRaisesRegex(m.GateError,'DELIVERY_TICK_INVALID'):m.field_inventory(1,rows,'NO_CAUSAL_EMISSION_TRIPLE')
    def test_bad_independence_rejected(self):
        rows=delivery_pair();rows[0]['independent_receiver']='true'
        with self.assertRaisesRegex(m.GateError,'INDEPENDENT_RECEIVER_FLAG_INVALID'):m.field_inventory(1,rows,'NO_SOURCE_SIGN')
    def test_false_packet_id_rejected(self):
        rows=delivery_pair();rows[0]['packet_id']=''
        with self.assertRaisesRegex(m.GateError,'DELIVERY_ID_INVALID'):m.field_inventory(1,rows,'NO_SOURCE_SIGN')
    def test_bad_evidence_ids_rejected(self):
        rows=delivery_pair();rows[0]['evidence_ids']='no'
        with self.assertRaisesRegex(m.GateError,'DELIVERY_EVIDENCE_IDS_INVALID'):m.field_inventory(1,rows,'NO_SOURCE_SIGN')
    def test_host_can_forge_all_fields_without_credit(self):
        x=m.evaluate_claimed_receipt(forged_receipt())
        self.assertEqual(x['status'],'UNTRUSTED_AUTHENTICATOR_NO_NATIVE_VERIFIER')
        self.assertFalse(x['native_credit'])
    def test_absent_semantic_fields_denied(self):
        self.assertEqual(m.evaluate_claimed_receipt({'source_identity':'C'})['status'],'MISSING_SEMANTIC_BINDING')
    def test_forged_wrong_sign_rejected(self):
        p=forged_receipt();p['semantic_sign']=0
        self.assertEqual(m.evaluate_claimed_receipt(p)['status'],'INVALID_SIGN')
    def test_forged_wrong_source_rejected(self):
        p=forged_receipt();p['source_identity']='host'
        self.assertEqual(m.evaluate_claimed_receipt(p)['status'],'INVALID_AUTHOR_CLAIM')
    def test_forged_empty_parent_rejected(self):
        p=forged_receipt();p['causal_parent_id']=''
        self.assertEqual(m.evaluate_claimed_receipt(p)['status'],'INVALID_CAUSAL_PARENT')
    def test_forged_empty_emission_rejected(self):
        p=forged_receipt();p['C_emission_id']=''
        self.assertEqual(m.evaluate_claimed_receipt(p)['status'],'INVALID_EMISSION_ID')
    def test_forged_wrong_mapping_rejected(self):
        with self.assertRaisesRegex(m.GateError,'RECEIPT_NOT_MAPPING'):m.evaluate_claimed_receipt([])
    def test_replay_attack_attestation_field_not_authority(self):
        p=forged_receipt();p['authenticator']='replayed-signed-looking-string'
        self.assertFalse(m.evaluate_claimed_receipt(p)['native_credit'])
    def test_sign_mutation_attestation_field_not_authority(self):
        p=forged_receipt();p['semantic_sign']=-1
        self.assertFalse(m.evaluate_claimed_receipt(p)['native_credit'])
    def test_absent_auth_tag_no_authority(self):
        p=forged_receipt();p.pop('authenticator')
        self.assertEqual(m.evaluate_claimed_receipt(p)['status'],'MISSING_SEMANTIC_BINDING')
    def test_positive_negative_same_receiver_shape(self):
        x=[{'observed_sign':1,'delivery_fields':sorted(m.EXPECTED_DELIVERY_FIELDS),'delivery_count':2,
            'delivery_routes':[['C','B'],['B','A']],'research_classification':'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'},
           {'observed_sign':-1,'delivery_fields':sorted(m.EXPECTED_DELIVERY_FIELDS),'delivery_count':2,
            'delivery_routes':[['C','B'],['B','A']],'research_classification':'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT'}]
        self.assertEqual(m.shape_collision(x)['dual_sign_receiver_schema_groups'],1)
    def test_no_cross_sign_collision_rejected(self):
        with self.assertRaisesRegex(m.GateError,'NO_POSITIVE_NEGATIVE_RECEIVER_SHAPE_COLLISION'):
            m.shape_collision([{'observed_sign':1,'delivery_fields':[],'delivery_count':0,'delivery_routes':[],
                                'research_classification':'NO_SOURCE_SIGN'}])
    def test_canonical_hash_stable(self):
        self.assertEqual(m.canonical_sha({'a':1,'b':2}),m.canonical_sha({'b':2,'a':1}))
    def test_no_native_signing(self):
        src=Path(m.__file__).read_text()
        self.assertNotIn('hmac.new(',src)
        self.assertNotIn('native_receiver_semantic_credit\':True',src)
    def test_one_source_invocation_ast(self):
        tree=ast.parse(Path(m.__file__).read_text())
        f=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='run')
        calls=[c for c in ast.walk(f) if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='source_once']
        self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
