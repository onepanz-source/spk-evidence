import copy
from pathlib import Path
import json
import unittest
from research.spk_v5_t5jkl import t5jkl
from research.spk_v5_t5jkl.independence_contract_v0 import (
    BoundaryViolation,assess_A_claim,classify)

ROOT=Path(__file__).resolve().parents[3]
G=json.loads((ROOT/'research/spk_v5_t5jkl/reference/t4ghi-one-pass-sign.json').read_text())
A=json.loads((ROOT/'research/spk_v5_t5jkl/reference/t5ghi-receiver-freshness.json').read_text())

class TestCrossPlane(unittest.TestCase):
    def row(self,i):return copy.deepcopy(A['rows'][i]),copy.deepcopy(G['H_rows'][i])
    def test_sha_pins(self):
        self.assertEqual(t5jkl.sha_file(ROOT/'research/spk_v5_t5jkl/reference/t5ghi-receiver-freshness.json'),t5jkl.T5GHI_SHA)
        self.assertEqual(t5jkl.sha_file(ROOT/'research/spk_v5_t5jkl/reference/t4ghi-one-pass-sign.json'),t5jkl.T4GHI_SHA)
    def test_180_reference_parity(self):
        d=t5jkl.audit(ROOT,full_source_pins=False)
        self.assertEqual(d['cases'],180)
        self.assertEqual(d['classification_counts']['fresh_received'],72)
        self.assertEqual(d['classification_counts']['research_guard_candidates'],24)
        self.assertEqual(d['classification_counts']['fork_receipt_without_source_forward_emission_chain'],24)
        self.assertEqual(d['A_independent_judgments_authenticated'],0)
        self.assertEqual(d['native_BV_credit'],0)
        self.assertFalse(d['promotion_allowed'])
    def test_no_sign(self):
        r,g=self.row(1);self.assertEqual(classify(r,g)['classification'],'NO_SIGN_RECEIVED')
    def test_clean_candidate(self):
        r,g=self.row(0);self.assertEqual(classify(r,g)['classification'],'FRESH_RECEIPT_GUARD_CANDIDATE')
    def test_no_forward_receipt(self):
        r,g=self.row(3);v=classify(r,g);self.assertEqual(v['classification'],'FRESH_RECEIPT_WITH_SOURCE_FAULT');self.assertTrue(v['source_forward_emission_chain'])
    def test_no_reverse_no_observed_forward_chain(self):
        r,g=self.row(4);v=classify(r,g);self.assertTrue(v['A_fresh_receipt']);self.assertFalse(v['source_forward_emission_chain'])
    def test_nonpromoted(self):
        for i in range(180):
            with self.subTest(i=i):
                r,g=self.row(i);v=classify(r,g)
                self.assertFalse(v['native_semantic_BV_credit']);self.assertFalse(v['A_independent_judgment_authenticated'])
    def test_index_reorder_rejected(self):
        r,g=self.row(0);g['index']=1
        with self.assertRaisesRegex(BoundaryViolation,'CASE_ID_DRIFT'):classify(r,g)
    def test_source_sha_swap_rejected(self):
        r,g=self.row(0);g['source_sha256']='f'*64
        with self.assertRaisesRegex(BoundaryViolation,'SOURCE_HASH_MISMATCH'):classify(r,g)
    def test_claimed_native_credit_rejected(self):
        r,g=self.row(0);r['native_credit']=True
        with self.assertRaisesRegex(BoundaryViolation,'NATIVE_PROMOTION_CLAIM'):classify(r,g)
    def test_forged_A_acceptance_rejected(self):
        r,g=self.row(1);r['A_fresh_accept']=True;r['C_issued']=1
        with self.assertRaisesRegex(BoundaryViolation,'SOURCE_SIGN_RECEIPT_PARITY'):classify(r,g)
    def test_bad_C_sign_rejected(self):
        r,g=self.row(0);g['C_sign_candidate_from_same_source_forward_output']=0
        with self.assertRaisesRegex(BoundaryViolation,'SOURCE_SIGN_INVALID'):classify(r,g)
    def test_forged_guard_rejected(self):
        r,g=self.row(3);r['guard_only']=True
        with self.assertRaisesRegex(BoundaryViolation,'GUARD_CANDIDATE_DRIFT'):classify(r,g)
    def test_boolean_issuer_rejected(self):
        r,g=self.row(0);r['C_issued']=True
        with self.assertRaisesRegex(BoundaryViolation,'RECEIPT_SHAPE_MISMATCH'):classify(r,g)
    def test_coherent_without_receipt_rejected(self):
        r,g=self.row(1);g['C_B_A_emission_candidate_consistent']=True
        with self.assertRaisesRegex(BoundaryViolation,'COHERENT_WITHOUT_RECEIPT'):classify(r,g)
    def test_reference_promoted_parent_rejected(self):
        r,g=self.row(0);g['native_learning_proven']=True
        with self.assertRaisesRegex(BoundaryViolation,'NATIVE_PROMOTION_CLAIM'):classify(r,g)
    def test_no_independent_A_judgment(self):
        self.assertEqual(assess_A_claim(None)['reason'],'NO_INDEPENDENT_A_EVIDENCE')
    def test_fake_A_sensor_is_only_structural(self):
        fake={'claimant':'A','assessment':1,'goal_observation_sha256':'c'*64,
              'lineage_roots':['A_SENSOR:fake'],'attested_by':'fake-attestor'}
        verdict=assess_A_claim(fake)
        self.assertTrue(verdict['structural_independence']);self.assertFalse(verdict['authenticated'])
        r,g=self.row(0);x=classify(r,g,fake)
        self.assertTrue(x['A_independent_judgment_structural']);self.assertFalse(x['native_semantic_BV_credit'])
    def test_C_echo_does_not_count_as_A(self):
        fake={'claimant':'A','assessment':1,'goal_observation_sha256':'a'*64,
              'lineage_roots':['C:sign','A_SENSOR:relay'],'attested_by':None}
        verdict=assess_A_claim(fake)
        self.assertFalse(verdict['structural_independence']);self.assertFalse(verdict['authenticated'])
    def test_host_claim_does_not_count_as_A(self):
        fake={'claimant':'A','assessment':-1,'goal_observation_sha256':'b'*64,
              'lineage_roots':['HOST:derived_proxy'],'attested_by':None}
        self.assertFalse(assess_A_claim(fake)['structural_independence'])
    def test_attestation_label_not_enough(self):
        fake={'claimant':'A','assessment':1,'goal_observation_sha256':'b'*64,
              'lineage_roots':['A_SENSOR:local'],'attested_by':'silicon-backed-sounding-label'}
        self.assertFalse(assess_A_claim(fake)['authenticated'])
    def test_bad_independent_claim_shape(self):
        for fake in ({}, {'claimant':'C'}, {'claimant':'A','assessment':True,'goal_observation_sha256':'a'*64,
                  'lineage_roots':['A_SENSOR:1'],'attested_by':None},
                     {'claimant':'A','assessment':1,'goal_observation_sha256':'f'*64,
                      'lineage_roots':['A_SENSOR:1','A_SENSOR:1'],'attested_by':None}):
            with self.subTest(fake=fake),self.assertRaises(BoundaryViolation):assess_A_claim(fake)
    def test_archive_host_witness_present(self):
        self.assertEqual(A['host_rebind_forgery_witness']['C_new_PE_computations'],0)
        self.assertTrue(A['host_rebind_forgery_witness']['fresh_challenge_accepted_by_A'])
    def test_counts_24_and_48_are_distinct(self):
        d=t5jkl.audit(ROOT,False);k=d['classification_counts']
        self.assertEqual(k['FRESH_RECEIPT_WITH_SOURCE_FAULT'],48)
        self.assertEqual(k['FRESH_RECEIPT_GUARD_CANDIDATE'],24)
        self.assertEqual(k['source_chain_observed'],48)
    def test_tampered_reference_SHA_denied(self):
        with self.assertRaisesRegex(BoundaryViolation,'SHA_DRIFT'):
            t5jkl.pinned(ROOT/'research/spk_v5_t5jkl/reference/t5ghi-receiver-freshness.json','0'*64,'T5GHI')

if __name__=='__main__':unittest.main()
