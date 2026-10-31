"""Adversarial finite verification of native A1b-computed *research* reverse credit."""
from __future__ import annotations
from dataclasses import replace
from itertools import product
import copy
import unittest
from unittest.mock import patch
from spk_v5_research.island_c_owned_credit_v5t3h import (
 Measurement, ARMS,SCHEMA,EDGES,A_CREDIT,B_PROGRAM,C_PROGRAM,
 CreditAdmissionError,execute,build_case,verify_custody,compact_audit,
)
from spk_v5_research.island_successor_competition_v5t3e import native_boolean_truth_table
from search.spk_v5_t3h_c_owned_credit import pins_ok

STAMP0='2026-10-22 12:00:00';STAMP1='2026-10-22 12:01:00'
def sample(prev=False,now=True,co2=True,**kwargs):
    return Measurement(STAMP0,STAMP1,300.0 if prev else 5.0,
              300.0 if now else 5.0,None if co2 is None else 800.0 if co2 else 450.0,
              sensor_visible=co2 is not None,**kwargs)

class T3hCredit(unittest.TestCase):
    def test_new_pins(self):pins_ok()
    def test_boolean_truth_table_inherited_frozen(self):
        self.assertEqual(native_boolean_truth_table()['11']['persist'],True)
    def test_each_new_code_has_explicit_custody(self):
        self.assertIn(('ACC',(32,5)),A_CREDIT)
        self.assertIn(('ACC',(64,6)),C_PROGRAM)
        self.assertEqual(len(EDGES),8)
    def test_exhaustive_C_signed_decision_truth_table(self):
        for prev,now,demand in product((False,True),repeat=3):
            # dedicated second sweep arms below; current sweep checks current
            m=sample(prev,now,demand)
            r=execute(m,'current')
            self.assertEqual(r['status'],'C_authored_credit_delivered')
            self.assertEqual(r['C_computed_verdict'],1 if now==demand else -1)
            self.assertEqual(r['A_consumed_credit'],r['C_computed_verdict'])
        for arm in ARMS:
            for prev,now,demand in product((False,True),repeat=3):
                r=execute(sample(prev,now,demand),arm)
                emitted={'current':now,'persist':prev and now,'silent':False}[arm]
                self.assertEqual(r['A_light_decision'],emitted)
                self.assertEqual(r['C_computed_verdict'],1 if emitted==demand else -1)
                self.assertEqual(r['A_consumed_credit'],r['C_computed_verdict'])
                self.assertTrue(verify_custody(sample(prev,now,demand),arm,r))
    def test_C_reward_at_closure_only(self):
        r=execute(sample(),'persist')
        self.assertTrue(all(t==15 for t,n,c in r['A1b_emission_proof'] if n=='C'))
    def test_reverse_A_consumes_only_after_B(self):
        r=execute(sample(),'persist')
        trace=r['A1b_emission_proof']
        self.assertEqual([t for t,n,c in trace if n=='C' and c in (11,12)],[15])
        self.assertEqual([t for t,n,c in trace if n=='B' and c in (13,14)],[16])
        self.assertEqual([t for t,n,c in trace if n=='A' and c in (13,14)],[17])
    def test_explicit_silent_choice_positive(self):
        r=execute(sample(False,True,False),'silent')
        self.assertFalse(r['A_light_decision']);self.assertTrue(r['C_decision_marker_received'])
        self.assertEqual(r['A_consumed_credit'],1)
    def test_explicit_silent_choice_negative(self):
        r=execute(sample(False,True,True),'silent')
        self.assertEqual(r['A_consumed_credit'],-1)
    def test_sensor_absence_never_negative(self):
        for arm in ARMS:
            r=execute(sample(co2=None),arm)
            self.assertEqual(r['status'],'C_evidence_missing')
            self.assertIsNone(r['C_computed_verdict']);self.assertIsNone(r['A_consumed_credit'])
    def test_decision_missing_never_score(self):
        for arm in ARMS:
            r=execute(sample(send_decision=False),arm)
            self.assertEqual(r['status'],'decision_custody_failed')
            self.assertIsNone(r['A_consumed_credit'])
            self.assertIsNone(r['C_computed_verdict'])
    def test_decision_missing_sensor_missing_no_credit(self):
        r=execute(sample(co2=None,send_decision=False),'current')
        self.assertEqual(r['status'],'decision_custody_failed')
    def test_reverse_failure_separates_C_from_A(self):
        for arm in ARMS:
            r=execute(sample(reverse_enabled=False),arm)
            self.assertEqual(r['status'],'reverse_delivery_lost')
            self.assertIn(r['C_computed_verdict'],(1,-1))
            self.assertIsNone(r['A_consumed_credit'])
    def test_forward_failure_when_A_emits_cannot_masquerade_silence(self):
        for arm in ('current','persist'):
            r=execute(sample(True,True,False,forward_enabled=False),arm)
            self.assertEqual(r['status'],'forward_custody_failed')
            self.assertIsNone(r['A_consumed_credit'])
    def test_forward_route_unused_by_silent_choice_not_failure(self):
        r=execute(sample(True,True,False,forward_enabled=False),'silent')
        self.assertEqual(r['status'],'C_authored_credit_delivered')
        self.assertEqual(r['A_consumed_credit'],1)
    def test_source_custody_gapped_58(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),current_stamp='2026-10-22 12:00:58'),'current')
    def test_source_custody_gapped_62(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),current_stamp='2026-10-22 12:01:02'),'current')
    def test_source_custody_timestamp_reverse(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),current_stamp='2026-10-21 12:00:00'),'current')
    def test_59_seconds_admitted(self):
        self.assertTrue(execute(replace(sample(),current_stamp='2026-10-22 12:00:59'),'current')['A_consumed_credit'])
    def test_61_seconds_admitted(self):
        self.assertTrue(execute(replace(sample(),current_stamp='2026-10-22 12:01:01'),'current')['A_consumed_credit'])
    def test_nan_sensor_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),co2_current=float('nan')),'current')
    def test_inf_light_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),current_light=float('inf')),'current')
    def test_negative_light_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),previous_light=-1),'current')
    def test_negative_co2_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),co2_current=-1),'current')
    def test_bool_as_light_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),previous_light=True),'current')
    def test_co2_sensor_none_but_claim_present_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),co2_current=None),'current')
    def test_sensor_visible_string_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),sensor_visible='yes'),'current')
    def test_send_decision_string_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),send_decision=1),'current')
    def test_reverse_flag_string_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),reverse_enabled=None),'current')
    def test_forward_flag_string_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(replace(sample(),forward_enabled=0),'current')
    def test_invalid_arm_refused(self):
        with self.assertRaises(CreditAdmissionError):execute(sample(),'unknown')
    def test_wrong_row_type_refused(self):
        with self.assertRaises(CreditAdmissionError):execute({},'current')
    def test_no_photo_truth_in_A1b_input_case(self):
        case=build_case(sample(True,True,True),'current')
        self.assertEqual(set(e.node_id for e in case.events),{'A','C'})
        self.assertEqual(sum(e.node_id=='C' and e.channel in (4,5) for e in case.events),1)
        self.assertFalse(any(e.channel==99 for e in case.events))
    def test_C_sensor_swap_inverts_credit_for_same_A_decision(self):
        x=execute(sample(True,True,True),'persist')
        y=execute(sample(True,True,False),'persist')
        self.assertEqual(x['A_light_decision'],y['A_light_decision'])
        self.assertEqual(x['A_consumed_credit'],-y['A_consumed_credit'])
    def test_A_choice_changes_C_verdict_for_same_sensor(self):
        x=execute(sample(True,True,True),'persist')
        y=execute(sample(True,True,True),'silent')
        self.assertEqual(x['A_consumed_credit'],-y['A_consumed_credit'])
    def test_C_no_sensor_does_not_become_assumed_false(self):
        r=execute(sample(co2=None),'silent')
        self.assertIsNone(r['C_computed_verdict'])
    def test_claim_forged_sign_refused(self):
        r=execute(sample(),'persist');bad=dict(r,A_consumed_credit=1-r['A_consumed_credit'])
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(),'persist',bad)
    def test_claim_forged_C_verdict_refused(self):
        r=execute(sample(),'persist');bad=dict(r,C_computed_verdict=0)
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(),'persist',bad)
    def test_claim_forged_status_refused(self):
        r=execute(sample(reverse_enabled=False),'persist')
        bad=dict(r,status='C_authored_credit_delivered',A_consumed_credit=1)
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(reverse_enabled=False),'persist',bad)
    def test_claim_trace_forgery_refused(self):
        r=execute(sample(),'persist');bad=copy.deepcopy(r)
        bad['A1b_emission_proof'].append((15,'C',11))
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(),'persist',bad)
    def test_claim_duplicate_proof_refused(self):
        r=execute(sample(),'persist');bad=copy.deepcopy(r)
        bad['A1b_emission_proof'][0]=(999,'A',20)
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(),'persist',bad)
    def test_other_arm_proof_refused(self):
        r=execute(sample(True,True,False),'current')
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(True,True,False),'persist',r)
    def test_mismatched_case_refused(self):
        r=execute(sample(True,True,False),'current')
        with self.assertRaises(CreditAdmissionError):verify_custody(sample(False,True,False),'current',r)
    def test_credit_not_signed_or_native(self):
        r=execute(sample(),'persist')
        self.assertFalse(r['native_learning']);self.assertFalse(r['native_BV_credit'])
        self.assertFalse(r['external_photo_labels_seen'])
        self.assertEqual(r['source_authority'],'A1b_derived_research_C_instructions')
    def test_synthetic_matrix_size(self):
        report=compact_audit()
        self.assertEqual(report['case_count'],144)
        self.assertGreater(report['statuses']['C_authored_credit_delivered'],0)
        self.assertGreater(report['statuses']['reverse_delivery_lost'],0)
        self.assertGreater(report['statuses']['C_evidence_missing'],0)
        self.assertGreater(report['statuses']['decision_custody_failed'],0)
        self.assertEqual(report['schema'],SCHEMA)
    def test_no_duplicate_outputs_per_single_case(self):
        r=execute(sample(True,True,True),'current')
        self.assertEqual(len([x for x in r['A1b_emission_proof'] if x[1]=='A' and x[2]==20]),1)
        self.assertEqual(len([x for x in r['A1b_emission_proof'] if x[1]=='A' and x[2] in (13,14)]),1)
    def test_A1b_program_not_rewritten(self):
        from spk_v5_research.island_objective_v5t1 import PROGRAMS
        self.assertNotIn('persist',PROGRAMS)
        self.assertEqual(set(PROGRAMS),{'overemit','silent','temporal'})
    def test_derived_no_future_learning(self):
        r=execute(sample(),'current')
        self.assertNotIn('weights',r);self.assertNotIn('policy_update',r)

if __name__=='__main__':unittest.main()
