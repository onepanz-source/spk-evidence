from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import BridgeRejected
from research.spk_v5_t7jkl_mno_pqr.semantic_custody_v0 import compose
from research.spk_v5_t8abc_def_ghi.semantic_packet_v1_candidate import make_packet,verify_packet
from research.spk_v5_t8abc_def_ghi.p_admission_v1_candidate import evaluate,settle_research
from research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 import recovery_witness,hostile_model_witness

ISSUE={'id':7,'cue':0,'choice':12,'version':3,'goal':11}
class T8ABC(unittest.TestCase):
    def setUp(self):
        self.src=fake_source();self.pkt=make_packet(self.src,ISSUE)
    def test_versioned_schema(self):self.assertTrue(self.pkt['schema'].endswith('v1-candidate-research'))
    def test_verdict_issuer_and_destination(self):self.assertEqual((self.pkt['verdict']['issuer'],self.pkt['destination']),('A','C'))
    def test_verdict_bound_to_decision(self):self.assertEqual(self.pkt['verdict']['decision_id'],7)
    def test_verdict_bound_to_context(self):self.assertEqual(self.pkt['verdict']['context_id'],0)
    def test_verdict_bound_to_version(self):self.assertEqual(self.pkt['verdict']['policy_version'],3)
    def test_verdict_choice(self):self.assertEqual(self.pkt['verdict']['choice'],12)
    def test_negative_value(self):self.assertEqual(self.pkt['verdict']['value'],-1)
    def test_positive_value(self):
        x=make_packet(fake_source(11,11),dict(ISSUE,choice=11))
        self.assertEqual((x['verdict']['outcome'],x['verdict']['value']),('IMPROVED',1))
    def test_A_semantic_channel(self):self.assertEqual(self.pkt['verdict']['semantic_output_channel'],22)
    def test_route(self):self.assertEqual(self.pkt['route']['hops'],['A','B','C'])
    def test_explicit_no_native_carrier(self):self.assertIn('NOT_NATIVE',self.pkt['carrier'])
    def test_unattested_provenance(self):self.assertEqual(self.pkt['provenance'],'HOST_VISIBLE_UNATTESTED')
    def test_v0e_packet_has_no_semantic_field(self):
        self.assertNotIn('outcome',self.src['feedback']['deliveries'][0])
    def test_exact_packet_passes(self):self.assertEqual(self.pkt,verify_packet(self.src,ISSUE,self.pkt))
    def reject(self,changed):
        with self.assertRaises(BridgeRejected):verify_packet(self.src,ISSUE,changed)
    def test_tampered_outcome(self):
        x=copy.deepcopy(self.pkt);x['verdict']['outcome']='IMPROVED';self.reject(x)
    def test_tampered_value(self):
        x=copy.deepcopy(self.pkt);x['verdict']['value']=1;self.reject(x)
    def test_wrong_owner(self):
        x=copy.deepcopy(self.pkt);x['verdict']['issuer']='C';self.reject(x)
    def test_tampered_route(self):
        x=copy.deepcopy(self.pkt);x['route']['hops']=['A','C'];self.reject(x)
    def test_tampered_source_digest(self):
        x=copy.deepcopy(self.pkt);x['source_sha256']='f'*64;self.reject(x)
    def test_false_native_claim(self):
        x=copy.deepcopy(self.pkt);x['provenance']='ATTESTED_NATIVE';self.reject(x)
    def test_false_native_carrier(self):
        x=copy.deepcopy(self.pkt);x['carrier']='NATIVE_V0E';self.reject(x)
    def test_wrong_version(self):
        with self.assertRaises(BridgeRejected):verify_packet(self.src,dict(ISSUE,version=4),self.pkt)
    def test_rebound_decision(self):
        with self.assertRaises(BridgeRejected):verify_packet(self.src,dict(ISSUE,id=9),self.pkt)
    def test_unsupported_C_action(self):
        with self.assertRaises(BridgeRejected):make_packet(self.src,dict(ISSUE,choice=9))
    def test_ambiguous_A_emission(self):
        x=copy.deepcopy(self.src);x['forward']['emissions'].append(x['forward']['emissions'][-2].copy())
        with self.assertRaises(BridgeRejected):make_packet(x,ISSUE)
    def test_no_reverse_route(self):
        x=copy.deepcopy(self.src);x['feedback']['deliveries'].pop()
        with self.assertRaises(BridgeRejected):make_packet(x,ISSUE)
    def test_no_forward_route(self):
        with self.assertRaises(BridgeRejected):make_packet(fake_source(drop=True),ISSUE,drop_forward=True)
    def test_bv_semantic_remains_overlay(self):
        self.assertNotIn('verdict',compose(self.src,ISSUE)['C_receipt'])

class T8DEF(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=EpochState(Path(self.tmp.name)/'p.sqlite')
        self.issued=self.store.issue(0,11);self.src=fake_source()
        self.pkt=make_packet(self.src,self.issued)
        self.grant=evaluate(self.src,self.issued,self.pkt)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_research_only(self):self.assertEqual(self.grant['authority_model'],'HOST_CONTROLLED_RESEARCH')
    def test_no_native_grant(self):self.assertIsNone(self.grant['native_grant'])
    def test_no_native_write(self):self.assertFalse(self.grant['native_write_performed'])
    def test_p_owner(self):self.assertEqual(self.grant['request']['owner'],'C')
    def test_p_domain(self):self.assertEqual(self.grant['request']['domain'],'P')
    def test_execute_mode(self):self.assertEqual(self.grant['request']['mode'],'execute')
    def test_decision_bound(self):self.assertEqual(self.grant['request']['decision_id'],0)
    def test_version_bound(self):self.assertEqual(self.grant['request']['expected_policy_version'],0)
    def test_candidate_negative(self):self.assertTrue(self.grant['request']['research_switch_candidate'])
    def test_forged_native_grant_denied(self):
        x=copy.deepcopy(self.grant);x['native_grant']={'owner':'C'}
        with self.assertRaises(BridgeRejected):settle_research(self.store,self.src,self.issued,self.pkt,x)
    def test_forged_native_written_denied(self):
        x=copy.deepcopy(self.grant);x['native_write_performed']=True
        with self.assertRaises(BridgeRejected):settle_research(self.store,self.src,self.issued,self.pkt,x)
    def test_changed_owner_denied(self):
        x=copy.deepcopy(self.grant);x['request']['owner']='A'
        with self.assertRaises(BridgeRejected):settle_research(self.store,self.src,self.issued,self.pkt,x)
    def test_wrong_version_denied(self):
        x=copy.deepcopy(self.grant);x['request']['expected_policy_version']+=1
        with self.assertRaises(BridgeRejected):settle_research(self.store,self.src,self.issued,self.pkt,x)
    def test_tampered_packet_denied(self):
        x=copy.deepcopy(self.pkt);x['verdict']['value']=1
        with self.assertRaises(BridgeRejected):evaluate(self.src,self.issued,x)
    def test_commit_research_only(self):
        r=settle_research(self.store,self.src,self.issued,self.pkt,self.grant)
        self.assertTrue(r['updated']);self.assertEqual(self.store.table[0],11)
    def test_replay_denied(self):
        settle_research(self.store,self.src,self.issued,self.pkt,self.grant)
        with self.assertRaises(BridgeRejected):settle_research(self.store,self.src,self.issued,self.pkt,self.grant)
    def test_change_packet_version_denied(self):
        x=copy.deepcopy(self.pkt);x['verdict']['policy_version']+=1
        with self.assertRaises(BridgeRejected):evaluate(self.src,self.issued,x)
    def test_readonly_evaluation(self):
        evaluate(self.src,self.issued,self.pkt)
        self.assertEqual(self.store.updates,0)
    def test_positive_no_switch(self):
        x=dict(self.issued,choice=11)
        positive=fake_source(11,11)
        z=make_packet(positive,x)
        outcome=evaluate(positive,x,z)
        self.assertFalse(outcome['request']['research_switch_candidate'])
    def test_survives_reopen(self):
        r=recovery_witness();self.assertTrue(r['replay_after_reopen_denied'])
    def test_host_still_can_forge(self):
        r=hostile_model_witness();self.assertFalse(r['native_origin_authenticated'])

if __name__=='__main__':unittest.main()
