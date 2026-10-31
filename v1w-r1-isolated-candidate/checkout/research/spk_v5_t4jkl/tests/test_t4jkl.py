from __future__ import annotations
from collections import Counter
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from research.spk_v5_t4jkl import t4jkl as m

REF=Path(__file__).resolve().parents[1]/'reference/t4ghi-one-pass-sign.json'

class T4JKLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=m.reference(REF)
        cls.rows=cls.d['H_rows']
        cls.off=m.offline_analysis(cls.d)
    def row(self, failure='none',sign=1):
        return deepcopy(next(x for x in self.rows if x['failure']==failure and x['C_sign_candidate_from_same_source_forward_output']==sign))
    def checked(self,row):return m.checked_row(row)
    def fails(self,row,msg):
        with self.assertRaisesRegex(m.GateError,msg): self.checked(row)
    def test_reference(self):self.assertEqual(m.file_sha(REF),m.REFERENCE_SHA)
    def test_reference_missing(self):
        with self.assertRaisesRegex(m.GateError,'MISSING'):m.reference('/not-a-real-reference-jkl.json')
    def test_reference_modified(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'reference.json';p.write_bytes(REF.read_bytes()+b' ')
            with self.assertRaisesRegex(m.GateError,'SHA_DRIFT'):m.reference(p)
    def test_reference_count(self):self.assertEqual(len(self.rows),180)
    def test_reference_not_promoted(self):self.assertIs(self.d['promotion_allowed'],False)
    def test_class_totals(self):
        self.assertEqual(self.off['classification_counts'],{
            'NO_SOURCE_SIGN':108,'NO_CAUSAL_EMISSION_TRIPLE':24,
            'APPLICATION_FORWARD_GUARD_BLOCK':24,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT':24})
    def test_research_guard_is_24(self):self.assertEqual(self.off['research_guard_eligible_count'],24)
    def test_48_triples(self):self.assertEqual(self.off['emission_triple_count'],48)
    def test_no_forward_triples_not_credit(self):
        x=self.checked(self.row('no_forward'))
        self.assertTrue(x['BV_emission_triple']);self.assertFalse(x['research_guard_eligible'])
    def test_no_reverse_no_credit(self):
        x=self.checked(self.row('no_reverse'))
        self.assertEqual(x['classification'],'NO_CAUSAL_EMISSION_TRIPLE')
    def test_no_C_no_sign(self):
        x=self.checked(self.row('no_C',None));self.assertEqual(x['classification'],'NO_SOURCE_SIGN')
    def test_no_marker_no_sign(self):
        x=self.checked(self.row('no_marker',None));self.assertEqual(x['classification'],'NO_SOURCE_SIGN')
    def test_neutral_sensor_no_sign(self):
        x=next(r for r in self.rows if r['failure']=='none' and r['C_sensor'] is None)
        self.assertEqual(self.checked(x)['classification'],'NO_SOURCE_SIGN')
    def test_valid_pos(self):self.assertTrue(self.checked(self.row('none',1))['research_guard_eligible'])
    def test_valid_neg(self):self.assertTrue(self.checked(self.row('none',-1))['research_guard_eligible'])
    def test_no_promotions_even_guard(self):
        x=self.checked(self.row());self.assertIs(x['native_semantic_receipt_proven'],False)
    def test_missing_index(self):
        x=self.row();del x['index'];self.fails(x,'INDEX_INVALID')
    def test_wrong_status(self):
        x=self.row();x['status']='NATIVE_BV_VERIFIED';self.fails(x,'STATUS_INVALID')
    def test_forged_promotion(self):
        x=self.row();x['signed_C_to_A_native_BV_receipt_proven']=True;self.fails(x,'PROMOTION')
    def test_wrong_failure(self):
        x=self.row();x['failure']='fake';self.fails(x,'FAILURE_CLASS')
    def test_wrong_arm(self):
        x=self.row();x['arm']='fictitious';self.fails(x,'ARM_INVALID')
    def test_wrong_context(self):
        x=self.row();x['context']='999';self.fails(x,'CONTEXT_INVALID')
    def test_wrong_sensor(self):
        x=self.row();x['C_sensor']='unknown';self.fails(x,'SENSOR_INVALID')
    def test_wrong_sign(self):
        x=self.row();x['C_sign_candidate_from_same_source_forward_output']=2;self.fails(x,'SIGN_INVALID')
    def test_swapped_C_sign(self):
        x=self.row();x['C_sign_candidate_from_same_source_forward_output']=-1;self.fails(x,'C_SIGN_CHANNEL')
    def test_missing_B_not_consistent(self):
        x=self.row();x['event_candidate_paths']['B']=None;self.fails(x,'CONSISTENCY_DRIFT')
    def test_B_wrong_sign(self):
        x=self.row();x['event_candidate_paths']['B']['channel']=14;self.fails(x,'CONSISTENCY_DRIFT')
    def test_A_wrong_sign(self):
        x=self.row();x['event_candidate_paths']['A']['channel']=14;self.fails(x,'CONSISTENCY_DRIFT')
    def test_out_of_order_B(self):
        x=self.row();x['event_candidate_paths']['B']['timestamp']=13;self.fails(x,'CONSISTENCY_DRIFT')
    def test_out_of_order_A(self):
        x=self.row();x['event_candidate_paths']['A']['timestamp']=14;self.fails(x,'CONSISTENCY_DRIFT')
    def test_forged_emission_path(self):
        x=self.row();x['event_candidate_paths']['C']['paths']=['feedback.assessments[0]'];self.fails(x,'FORGED_EVENT_ORIGIN')
    def test_missing_emissions(self):
        x=self.row();x['event_candidate_paths']={};self.fails(x,'EVENT_ROLE_KEYS')
    def test_boolean_timestamp(self):
        x=self.row();x['event_candidate_paths']['C']['timestamp']=True;self.fails(x,'EVENT_SHAPE')
    def test_bad_grants(self):
        x=self.row();x['BV_grant_count']=3;self.fails(x,'GRANT_COUNT')
    def test_bad_terminal_count(self):
        x=self.row();x['C_fixed_terminal_count']=2;self.fails(x,'TERMINAL_COUNT')
    def test_unbacked_assessment(self):
        x=self.row();x['BV_assessment_count']=0;self.fails(x,'ASSESSMENT_TERMINAL')
    def test_forged_delivery_roles(self):
        x=self.row();x['BV_delivery_roles']=[['A','C']];self.fails(x,'DELIVERY_ROLES_DRIFT')
    def test_source_none_yet_consistent(self):
        x=self.row('no_C',None);x['C_B_A_emission_candidate_consistent']=True;self.fails(x,'CONSISTENCY_DRIFT')
    def test_row_identity_drift(self):
        d=deepcopy(self.d);d['H_rows'][1]['index']=9
        with self.assertRaisesRegex(m.GateError,'ROW_INDEX_DRIFT'):m.offline_analysis(d)
    def test_drop_one_row(self):
        d=deepcopy(self.d);d['H_rows'].pop()
        with self.assertRaisesRegex(m.GateError,'NEGATIVE_CONTROL_COUNTS_DRIFT'):m.offline_analysis(d)
    def test_receiver_field_inventory_only(self):
        src={'forward':{'emissions':[{'node_id':'C','channel':11,'timestamp':14,'opaque':'x'}]},'feedback':{'deliveries':[{'sender':'C','receiver':'B'}]},'resources':{}}
        v=m.visible_event_schema(src)
        self.assertIn('opaque',v['emission_field_names'])
        self.assertFalse(v['native_authentication_evident'])
        self.assertFalse(v['receiver_readable_sign_receipt_proven'])
    def test_inventory_reject_fake_deliveries(self):
        src={'forward':{},'feedback':{'deliveries':['bogus']},'resources':{}}
        with self.assertRaisesRegex(m.GateError,'DELIVERY_SHAPE'):m.visible_event_schema(src)
    def test_checksum_failure_custody_offline(self):self.assertNotEqual(m.PREV_SHA,'f'*64)

if __name__=='__main__':unittest.main()
