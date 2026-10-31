from __future__ import annotations
import inspect
from pathlib import Path
from collections import Counter
from copy import deepcopy
from pathlib import Path
import unittest
from research.spk_v5_t4jkl_fix import t4jkl_fix as m
from research.spk_v5_t4jkl import t4jkl as broken

REF=Path(__file__).resolve().parents[2]/'spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'

class T4JKLMControlFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=m.reference(REF)
        cls.rows=cls.ref['H_rows']
        # The complete native source tree is intentionally not bundled. Verify
        # the pinned producer recipe's actual source expressions without imports.
        producer=inspect.getsource(m.prev.prev.table_cases)
        for required in ("send_decision=failure!='no_marker'",
                         "forward_enabled=failure!='no_forward'",
                         "reverse_enabled=failure!='no_reverse'"):
            assert required in producer, 'T4DEF_CONTROL_RECIPE_SOURCE_DRIFT:'+required
        cls.recipes=[dict(send_decision=r['failure']!='no_marker',
                          forward_enabled=r['failure']!='no_forward',
                          reverse_enabled=r['failure']!='no_reverse') for r in cls.rows]

    def test_reference_integrity(self):
        self.assertEqual(m.file_sha(REF),m.REFERENCE_SHA)
    def test_recipe_length(self):
        self.assertEqual(len(self.recipes),180)
    def test_regression_reproduces_original_bug(self):
        r=self.rows[2]
        self.assertEqual(r['failure'],'no_marker')
        self.assertFalse(broken.checked_row(r)['application_action_forward_enabled'])
        self.assertTrue(self.recipes[2]['forward_enabled'])
    def test_no_marker_decision_disabled(self):
        x=m.checked_row(self.rows[2]);self.assertFalse(x['application_send_decision_enabled'])
    def test_no_marker_forward_still_enabled(self):
        self.assertTrue(m.checked_row(self.rows[2])['application_action_forward_enabled'])
    def test_no_marker_reverse_still_enabled(self):
        self.assertTrue(m.checked_row(self.rows[2])['application_reverse_enabled'])
    def test_no_marker_has_no_source_sign(self):
        self.assertIsNone(m.checked_row(self.rows[2])['sign'])
    def test_no_C_forward_still_enabled(self):
        self.assertTrue(m.checked_row(self.rows[1])['application_action_forward_enabled'])
    def test_no_forward_decision_is_enabled(self):
        x=next(x for x in self.rows if x['failure']=='no_forward')
        self.assertTrue(m.checked_row(x)['application_send_decision_enabled'])
    def test_no_forward_forward_is_disabled(self):
        x=next(x for x in self.rows if x['failure']=='no_forward')
        self.assertFalse(m.checked_row(x)['application_action_forward_enabled'])
    def test_no_forward_reverse_remains_enabled(self):
        x=next(x for x in self.rows if x['failure']=='no_forward')
        self.assertTrue(m.checked_row(x)['application_reverse_enabled'])
    def test_no_reverse_forward_remains_enabled(self):
        x=next(x for x in self.rows if x['failure']=='no_reverse')
        self.assertTrue(m.checked_row(x)['application_action_forward_enabled'])
    def test_no_reverse_reverse_disabled(self):
        x=next(x for x in self.rows if x['failure']=='no_reverse')
        self.assertFalse(m.checked_row(x)['application_reverse_enabled'])
    def test_no_reverse_decision_enabled(self):
        x=next(x for x in self.rows if x['failure']=='no_reverse')
        self.assertTrue(m.checked_row(x)['application_send_decision_enabled'])
    def test_all_180_source_flags_match_recipes(self):
        for index,(row,recipe) in enumerate(zip(self.rows,self.recipes)):
            self.assertEqual(row['index'],index)
            x=m.checked_row(row)
            self.assertEqual(x['application_action_forward_enabled'],recipe['forward_enabled'],index)
            self.assertEqual(x['application_reverse_enabled'],recipe['reverse_enabled'],index)
            self.assertEqual(x['application_send_decision_enabled'],recipe['send_decision'],index)
    def test_180_reference_source_sha_distinct_from_authorship(self):
        self.assertTrue(all(not m.checked_row(row)['native_semantic_receipt_proven'] for row in self.rows))
    def test_offline_class_counts_unaltered(self):
        counts=m.offline_analysis(self.ref)['classification_counts']
        self.assertEqual(counts,{'NO_SOURCE_SIGN':108,'NO_CAUSAL_EMISSION_TRIPLE':24,
            'APPLICATION_FORWARD_GUARD_BLOCK':24,'RESEARCH_GUARD_ELIGIBLE_NOT_NATIVE_CREDIT':24})
    def test_research_24_not_native(self):
        d=m.offline_analysis(self.ref)
        self.assertEqual(d['research_guard_eligible_count'],24)
        self.assertEqual(d['emission_triple_count'],48)
    def test_no_forward_emissions_not_credit(self):
        x=next(x for x in self.rows if x['failure']=='no_forward' and x['C_B_A_emission_candidate_consistent'])
        self.assertEqual(m.checked_row(x)['classification'],'APPLICATION_FORWARD_GUARD_BLOCK')
    def test_no_marker_forged_sign_rejected(self):
        x=deepcopy(self.rows[2]);x['C_sign_candidate_from_same_source_forward_output']=1
        with self.assertRaisesRegex(m.GateError,'DECISION_DISABLED_WITH_SOURCE_SIGN'):
            m.checked_row(x)
    def test_no_marker_emission_triple_forgery_rejected(self):
        x=deepcopy(self.rows[2]);x['event_candidate_paths']={
            'C':{'channel':11,'timestamp':14,'paths':['forward.emissions[3]']},
            'B':{'channel':13,'timestamp':15,'paths':['forward.emissions[4]']},
            'A':{'channel':13,'timestamp':16,'paths':['forward.emissions[5]']}}
        x['C_sign_candidate_from_same_source_forward_output']=1
        x['C_B_A_emission_candidate_consistent']=True
        with self.assertRaisesRegex(m.GateError,'DECISION_DISABLED_WITH_SOURCE_SIGN'):
            m.checked_row(x)
    def test_metadata_absence_prevents_accidental_promotion(self):
        self.assertIs(self.ref['promotion_allowed'],False)
    def test_invalid_row_status_not_pass(self):
        x=deepcopy(self.rows[0]);x['status']='native_proven'
        with self.assertRaisesRegex(m.GateError,'ROW_STATUS_INVALID'):
            m.checked_row(x)
    def test_read_only_nonpromotion(self):
        self.assertNotIn('update',m.STATUS.lower())
    def test_no_new_semantic_certificate(self):
        self.assertFalse(m.checked_row(self.rows[0])['native_learning_proven'])

if __name__=='__main__':unittest.main()
