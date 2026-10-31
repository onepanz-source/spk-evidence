from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from spk_t3rst import AuditError, audit_pair, audit_trace, audit_reference, make_witness

class Gate(unittest.TestCase):
    def good(self): return make_witness()
    def reject(self,doc, key=None):
        with self.assertRaises(AuditError):
            audit_trace(doc)

    def test_01_positive(self): self.assertEqual(audit_trace(self.good())['source_structural_credit_events'],1)
    def test_02_negative_sign(self): self.assertEqual(audit_trace(make_witness('negative'))['verdict_counts']['negative'],1)
    def test_03_silence_no_credit(self): self.assertEqual(audit_trace(make_witness(silent=True))['source_structural_credit_events'],0)
    def test_04_no_episodes(self):
        w=self.good();w['episodes']=[];self.reject(w)
    def test_05_dual_replay_forbidden(self):
        w=self.good();w['mode']='dual_replay';self.reject(w)
    def test_06_posthoc_host_selector_forbidden(self):
        w=self.good();w['selection_after_replay']=True;self.reject(w)
    def test_07_native_claim_forbidden(self):
        w=self.good();w['native_learning']=True;self.reject(w)
    def test_08_authenticated_sensor_claim_forbidden(self):
        w=self.good();w['authenticated_C_sensor']=True;self.reject(w)
    def test_09_semantic_BV_promotion_forbidden(self):
        w=self.good();w['native_semantic_BV']=True;self.reject(w)
    def test_10_host_verdict_forgery(self):
        w=self.good();w['episodes'][0]['events'][4]['author']='host';self.reject(w)
    def test_11_future_sensor(self):
        w=self.good();w['episodes'][0]['events'][3]['tick']=6;self.reject(w)
    def test_12_missing_ingress(self):
        w=self.good();del w['episodes'][0]['events'][2];self.reject(w)
    def test_13_credit_before_verdict(self):
        w=self.good();w['episodes'][0]['events'][5]['tick']=4;self.reject(w)
    def test_14_sign_flip_only_at_host(self):
        w=self.good();w['episodes'][0]['events'][5]['verdict']='negative';self.reject(w)
    def test_15_wrong_decision_identity(self):
        w=self.good();w['episodes'][0]['events'][4]['decision_id']='other';self.reject(w)
    def test_16_wrong_parent(self):
        w=self.good();w['episodes'][0]['events'][4]['parent']='e1';self.reject(w)
    def test_17_unseen_sensor(self):
        w=self.good();w['episodes'][0]['events'][4]['sensor_event_id']='e_not_found';self.reject(w)
    def test_18_duplicate_admission(self):
        w=self.good();e=copy.deepcopy(w['episodes'][0]['events'][-1]);e['event_id']='e7';e['tick']=6;w['episodes'][0]['events'].append(e);self.reject(w)
    def test_19_spoofed_sensor(self):
        w=self.good();w['episodes'][0]['events'][3]['author']='C';self.reject(w)
    def test_20_counterfactual_pass_in_online(self):
        w=self.good();w['episodes'][0]['events'][4]['pass_id']='counterfactual';self.reject(w)
    def test_21_resource_overadmission(self):
        w=self.good();w['episodes'][0]['resources']['grants'][1]['units']=2;self.reject(w)
    def test_22_grant_unlinked_clock(self):
        w=self.good();w['episodes'][0]['resources']['grants'][1]['tick']=12;self.reject(w)
    def test_23_grant_replay_id(self):
        w=self.good();w['episodes'][0]['resources']['grants'][1]['grant_id']='g1';self.reject(w)
    def test_24_event_replay_id(self):
        w=self.good();w['episodes'][0]['events'][4]['event_id']='e2';self.reject(w)
    def test_25_silent_ghost_credit(self):
        w=make_witness(silent=True);w['episodes'][0]['events'].append(dict(event_id='x',kind='credit_admission',tick=5,author='shadow_registry',episode_id='ep-001',pass_id='observed',decision_id='decision-001',verdict='negative'));self.reject(w)
    def test_26_sensor_pre_decision(self):
        w=self.good();w['episodes'][0]['events'][0]['tick']=3;self.reject(w)
    def test_27_causal_pair_same_past_different_future(self):
        a=self.good();b=make_witness('negative');self.assertEqual(audit_pair(a,b)['different_future_episodes'],1)
    def test_28_pair_retrocausal_decision(self):
        a=self.good();b=make_witness('negative');b['episodes'][0]['events'][0]['action']='silent'
        with self.assertRaises(AuditError):audit_pair(a,b)
    def test_29_pair_no_future_perturbation(self):
        a=self.good()
        with self.assertRaises(AuditError):audit_pair(a,copy.deepcopy(a))
    def test_30_cross_episode_id_mismatch(self):
        w=self.good();w['episodes'][0]['events'][2]['episode_id']='ghost';self.reject(w)
    def test_31_parent_from_future(self):
        w=self.good();w['episodes'][0]['events'][1]['parent']='e5';self.reject(w)
    def test_32_non_monotonic_time(self):
        w=self.good();w['episodes'][0]['events'][2]['tick']=0;self.reject(w)
    def test_33_wrong_environment(self):
        w=self.good();w['environment']='native';self.reject(w)
    def test_34_missing_disclosure(self):
        w=self.good();del w['episodes'][0]['events'][0]['decision_id'];self.reject(w)
    def test_35_replay_credit_without_verdict(self):
        w=self.good();del w['episodes'][0]['events'][4];self.reject(w)
    def test_36_missing_resources(self):
        w=self.good();del w['episodes'][0]['resources'];self.reject(w)

if __name__ == '__main__': unittest.main()
