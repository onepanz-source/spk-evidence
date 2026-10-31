import copy,hashlib,json,unittest
from pathlib import Path
from research.spk_v5_t5pqr_stu_vwx.causal_contract_v0 import (
    CausalBoundary,need,digest,validate_source,observational_twins,intervention_pairs,research_feedback)
from research.spk_v5_t5pqr_stu_vwx.feedback_process_v0 import issue,relay,receive,valid_packet
from research.spk_v5_t5pqr_stu_vwx.cumulative_gate_v0 import T5MNO_SHA,run

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'research/spk_v5_t5pqr_stu_vwx/reference/t5mno-A-local-outcome.json'
DOC=json.loads(SOURCE.read_bytes());ROWS=DOC['rows'];P=research_feedback(ROWS)

class TestT5PQRObservationalNonIdentifiability(unittest.TestCase):
    def test_pinned_prior_exact(self):self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),T5MNO_SHA)
    def test_180_observations(self):validate_source(ROWS)
    def test_same_observed_vector(self):
        w=observational_twins(ROWS)
        self.assertEqual(w[0]['observed_rows_sha256'],w[1]['observed_rows_sha256'])
    def test_opposite_hypothetical_effects(self):
        a,b=observational_twins(ROWS)
        self.assertEqual((a['illustrative_effect'],b['illustrative_effect']),(1,-1))
    def test_same_observation_each_row(self):
        for w in observational_twins(ROWS):
            self.assertTrue(all(x['Y_observed']==ROWS[x['index']]['A_assessment'] for x in w['potential_outcomes']))
    def test_opposite_unobserved_potentials(self):
        a,b=observational_twins(ROWS)
        self.assertNotEqual(a['unobserved_potential_outcome_sha256'],b['unobserved_potential_outcome_sha256'])
    def test_invalid_row_count_rejected(self):
        with self.assertRaises(CausalBoundary):observational_twins(ROWS[:-1])
    def test_native_credit_claim_rejected(self):
        r=copy.deepcopy(ROWS);r[0]['A_to_C_credit']=True
        with self.assertRaises(CausalBoundary):validate_source(r)
    def test_source_guard_without_chain_rejected(self):
        r=copy.deepcopy(ROWS);r[0]['source_forward_emission_chain']=False
        with self.assertRaises(CausalBoundary):validate_source(r)
    def test_outcome_mismatch_rejected(self):
        r=copy.deepcopy(ROWS);r[0]['A_assessment']=-1
        with self.assertRaises(CausalBoundary):validate_source(r)

class TestT5STUSyntheticPairedTrials(unittest.TestCase):
    def test_exact_24_pairs(self):self.assertEqual(len(intervention_pairs(ROWS)['trials']),24)
    def test_exact_48_arms(self):self.assertEqual(sum(len(t['arms']) for t in intervention_pairs(ROWS)['trials']),48)
    def test_assignment_per_pair_balanced(self):
        for t in intervention_pairs(ROWS)['trials']:
            self.assertEqual(sorted(x['simulated_action'] for x in t['arms']),[0,1])
    def test_assigned_difference_matches_model(self):
        for t in intervention_pairs(ROWS)['trials']:
            self.assertEqual(t['paired_difference'],t['synthetic_plant_effect'])
    def test_effect_distribution(self):self.assertEqual(intervention_pairs(ROWS)['synthetic_effect_counts'],{'-1':8,'0':8,'2':8})
    def test_exact_synthetic_mean(self):
        d=intervention_pairs(ROWS);self.assertEqual((d['mean_synthetic_paired_effect_numerator'],d['mean_synthetic_paired_effect_denominator']),(8,24))
    def test_no_native_actions(self):self.assertEqual(intervention_pairs(ROWS)['native_C_actions'],0)
    def test_determinism(self):self.assertEqual(digest(intervention_pairs(ROWS)),digest(intervention_pairs(ROWS)))
    def test_paired_trial_uses_source_guard_only(self):
        self.assertEqual(set(t['case_index'] for t in intervention_pairs(ROWS)['trials']),set(r['index'] for r in ROWS if r['research_guard_candidate']))
    def test_host_synthetic_flag(self):
        self.assertTrue(all(t['host_controlled_pseudorandom_assignment'] and not t['sensor_authenticated'] for t in intervention_pairs(ROWS)['trials']))

class TestT5VWXFeedbackForwarding(unittest.TestCase):
    def test_exact_24_messages(self):self.assertEqual(len(P),24)
    def test_no_C_signs_or_source_faults(self):
        self.assertTrue(all('C_sign' not in row and 'failure' not in row for row in P))
    def test_a_owned_outcome_split(self):
        c=receive(relay(issue(P)))
        self.assertEqual(c['research_feedback_outcomes'],{'IMPROVED':8,'UNCHANGED':8,'WORSENED':8})
    def test_a_chain_commits(self):self.assertEqual(issue(P)['entries'][-1]['A_entry_sha256'],issue(P)['end_sha256'])
    def test_b_relay_preserves_A_end(self):self.assertEqual(relay(issue(P))['A_end_sha256'],issue(P)['end_sha256'])
    def test_c_has_no_native_learning(self):
        c=receive(relay(issue(P)))
        self.assertEqual(c['C_native_credit_applied'],0);self.assertEqual(c['C_native_learning_steps'],0)
    def test_duplicate_index_rejected_at_A(self):
        r=copy.deepcopy(P);r[1]['case_index']=r[0]['case_index']
        with self.assertRaises(CausalBoundary):issue(r)
    def test_replay_extra_rejected_at_C(self):
        d=relay(issue(P));d['entries'].append(copy.deepcopy(d['entries'][0]))
        with self.assertRaises(CausalBoundary):receive(d)
    def test_tamper_payload_rejected(self):
        d=relay(issue(P));d['entries'][0]['a_entry']['packet']['a_outcome']='WORSENED'
        with self.assertRaises(CausalBoundary):receive(d)
    def test_invalid_relay_digest_rejected(self):
        d=relay(issue(P));d['entries'][0]['B_relay_sha256']='0'*64
        with self.assertRaises(CausalBoundary):receive(d)
    def test_credit_claim_rejected(self):
        r=copy.deepcopy(P);r[0]['native_credit']=True
        with self.assertRaises(CausalBoundary):issue(r)
    def test_sensor_auth_claim_rejected(self):
        r=copy.deepcopy(P);r[0]['sensor_authenticated']=True
        with self.assertRaises(CausalBoundary):issue(r)
    def test_causal_claim_rejected(self):
        r=copy.deepcopy(P);r[0]['causally_attributed_to_C']=True
        with self.assertRaises(CausalBoundary):issue(r)
    def test_rewrite_fresh_host_forgery_accepted(self):
        original=receive(relay(issue(P)))
        forged=copy.deepcopy(P);forged[0]['a_outcome']='WORSENED';forged[0]['a_observation_sha256']='f'*64
        fake=receive(relay(issue(forged)))
        self.assertEqual(fake['received'],24)
        self.assertNotEqual(original['research_feedback_sha256'],fake['research_feedback_sha256'])
    def test_incomplete_feedback_rejected(self):
        with self.assertRaises(CausalBoundary):issue(P[:-1])
    def test_invalid_envelope_fields_rejected(self):
        r=copy.deepcopy(P);r[0]['C_sign']=1
        with self.assertRaises(CausalBoundary):issue(r)

class TestCumulativeWholeCheckpoint(unittest.TestCase):
    def test_three_gates_one_report(self):
        r=run(ROOT,False)
        self.assertEqual((r['T5PQR']['cases'],r['T5STU']['model_only_twin_trials'],r['T5VWX']['C_receiver_messages']),(180,24,24))
    def test_inherited_evidence_pin_and_nonpromotion(self):
        r=run(ROOT,False)
        self.assertTrue(r['T5MNO_reexecuted_byte_exact'])
        self.assertFalse(r['promotion_allowed']);self.assertEqual(r['native_BV_credit'],0)
    def test_six_rejections_one_host_acceptance(self):
        r=run(ROOT,False)
        self.assertEqual(len(r['T5VWX']['negative_attacks']),6)
        self.assertTrue(r['T5VWX']['host_reconstructed_fresh_ledger_accepted'])
    def test_deterministic_summary(self):
        self.assertEqual(digest(run(ROOT,False)),digest(run(ROOT,False)))

if __name__=='__main__':unittest.main()
