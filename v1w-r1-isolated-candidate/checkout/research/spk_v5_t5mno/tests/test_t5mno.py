import copy,hashlib,json,unittest
from pathlib import Path
from research.spk_v5_t5mno import t5mno
from research.spk_v5_t5mno.a_local_outcome_v0 import synthetic_A_observation,evaluate_observation,LocalAError
from research.spk_v5_t5mno.a_receiver_process_v0 import compute
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/'research/spk_v5_t5mno/reference/t5jkl-receiver-independence.json').read_text())

def inbound():
    return [{'case_index':x['index'],'source_sha256':x['source_sha256'],'receipt_present':x['A_fresh_receipt']} for x in REF['rows']]

class TestIndependentLocalA(unittest.TestCase):
    def test_reference_pin(self):self.assertEqual(t5mno.sha_file(ROOT/'research/spk_v5_t5mno/reference/t5jkl-receiver-independence.json'),t5mno.T5JKL_SHA)
    def test_a_does_not_receive_C_sign_or_fault(self):
        self.assertFalse(any('sign' in k or 'fault' in k or 'goal' in k or 'after' in k for k in inbound()[0]))
    def test_all_180_local_measurements(self):
        d=compute(inbound());self.assertEqual(d['A_local_synthetic_observations'],180)
        self.assertEqual(d['A_paired_research_outcomes'],72)
        self.assertEqual(d['outcome_counts'],{'IMPROVED':60,'WORSENED':60,'UNCHANGED':60,
           'paired_IMPROVED':24,'paired_WORSENED':24,'paired_UNCHANGED':24,'paired_receipts':72})
    def test_unpaired_still_measures(self):
        r=compute(inbound())['rows'][1];self.assertFalse(r['C_receipt_present']);self.assertEqual(r['A_outcome'],'WORSENED')
    def test_a_local_no_C_sign_parameter(self):
        for idx,o in ((0,'IMPROVED'),(1,'WORSENED'),(2,'UNCHANGED')):
            self.assertEqual(evaluate_observation(synthetic_A_observation(idx))['outcome'],o)
    def test_outcome_changes_with_A_only(self):
        x=synthetic_A_observation(0)
        self.assertEqual([evaluate_observation({**x,'after':a})['assessment'] for a in (8,4,6)],[1,-1,0])
    def test_receipt_toggle_cannot_change_A_outcome(self):
        inp=inbound();before=compute(inp)['rows'][0];inp[0]['receipt_present']=False
        after=compute(inp)['rows'][0]
        self.assertEqual((before['A_outcome'],before['A_local_observation_sha256']),
                         (after['A_outcome'],after['A_local_observation_sha256']))
    def test_reject_inbound_C_echo(self):
        x=inbound();x[0]['C_sign']=1
        with self.assertRaisesRegex(LocalAError,'ALLOWED_FIELDS'):compute(x)
    def test_reject_goal_injection(self):
        x=inbound();x[0]['goal']=10
        with self.assertRaisesRegex(LocalAError,'ALLOWED_FIELDS'):compute(x)
    def test_reject_duplicate(self):
        x=inbound();x[1]['case_index']=0
        with self.assertRaisesRegex(LocalAError,'DUPLICATE'):compute(x)
    def test_reject_reorder(self):
        x=inbound();x[0],x[1]=x[1],x[0]
        with self.assertRaisesRegex(LocalAError,'NONCANONICAL'):compute(x)
    def test_reject_count(self):
        with self.assertRaisesRegex(LocalAError,'INPUT_COUNT'):compute(inbound()[:-1])
    def test_reject_bogus_sha(self):
        x=inbound();x[5]['source_sha256']='0'
        with self.assertRaisesRegex(LocalAError,'RECEIVER_SHA'):compute(x)
    def test_reject_bool_case(self):
        x=inbound();x[0]['case_index']=True
        with self.assertRaises(LocalAError):compute(x)
    def test_reject_accepted_integer(self):
        x=inbound();x[0]['receipt_present']=1
        with self.assertRaisesRegex(LocalAError,'RECEIPT_FLAG'):compute(x)
    def test_a_sensor_claim_never_authenticated(self):
        v=compute(inbound());self.assertFalse(v['promotion_allowed'])
        self.assertFalse(any(x['A_external_authenticated'] or x['native_credit'] or x['A_causally_attributed_to_C'] for x in v['rows']))
    def test_host_sensor_forgery_changes_outcome(self):
        x=synthetic_A_observation(0);self.assertEqual(evaluate_observation(x)['assessment'],1)
        self.assertEqual(evaluate_observation({**x,'after':4})['assessment'],-1)
    def test_reject_origin_claim(self):
        with self.assertRaisesRegex(LocalAError,'A_LINEAGE'):
            evaluate_observation({**synthetic_A_observation(0),'lineage':'HARDWARE_ATTESTED'})
    def test_reject_bad_measurement(self):
        with self.assertRaises(LocalAError):evaluate_observation({**synthetic_A_observation(0),'after':True})
    def test_end_to_end_audit(self):
        d=t5mno.audit(ROOT,False)
        self.assertEqual(d['A_paired_research_outcomes'],72)
        self.assertEqual(d['A_research_guard_candidates'],24)
        self.assertEqual(d['A_paired_without_frozen_emission_chain'],24)
        self.assertEqual([x['count'] for x in d['C_sign_cross_tab']],[12]*6)
        self.assertTrue(d['host_can_forge_A_measurement'])
        self.assertFalse(d['A_sensor_source_authenticated']);self.assertFalse(d['A_C_causal_attribution_proven'])
        self.assertFalse(d['promotion_allowed'])
    def test_cross_plane_not_claim_causality(self):
        for row in t5mno.audit(ROOT,False)['rows']:
            self.assertFalse(row['A_causal_attribution_to_C'])
            self.assertFalse(row['A_to_C_credit'])
    def test_local_input_invariant_to_C_sign(self):
        g=json.loads((ROOT/'research/spk_v5_t5jkl/reference/t4ghi-one-pass-sign.json').read_text())
        d=compute(inbound())['rows']
        pairs=[(x['A_outcome'],src['C_sign_candidate_from_same_source_forward_output']) for x,src in zip(d,g['H_rows']) if x['C_receipt_present']]
        self.assertEqual(len(pairs),72)
        self.assertNotEqual(len(set(pairs)),1)
    def test_reference_has_no_authenticated_A_source(self):
        self.assertEqual(REF['A_independent_goal_observations'],0)
        self.assertEqual(REF['A_independent_judgments_authenticated'],0)
if __name__=='__main__':unittest.main()
