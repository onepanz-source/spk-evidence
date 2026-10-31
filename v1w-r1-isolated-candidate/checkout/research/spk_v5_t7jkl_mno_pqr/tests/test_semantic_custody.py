from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import BridgeRejected
from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
from research.spk_v5_t7jkl_mno_pqr.semantic_custody_v0 import compose,verify
from research.spk_v5_t7jkl_mno_pqr.p_intent_v0 import prepare,settle
from research.spk_v5_t7jkl_mno_pqr.cumulative_gate_v0 import hostile_counterexample

ISSUE={'id':7,'cue':0,'choice':12,'version':3,'goal':11}

class Packet(unittest.TestCase):
    def setUp(self):
        self.source=fake_source()
        self.packet=compose(self.source,ISSUE)
    def test_positive_and_negative(self):
        for choice in (11,12):
            for goal in (11,12):
                issue=dict(ISSUE,choice=choice,goal=goal)
                x=compose(fake_source(choice,goal),issue)
                self.assertEqual(x['outcome'],'IMPROVED' if choice==goal else 'WORSENED')
    def test_explicit_A_B_C_chain(self):
        self.assertEqual(self.packet['A_packet']['issuer'],'A')
        self.assertEqual(self.packet['B_packet']['issuer'],'B')
        self.assertEqual(self.packet['C_receipt']['receiver'],'C')
    def test_verdict_is_not_native_BV_field(self):
        self.assertFalse(any('A_outcome' in x for x in self.source['feedback']['deliveries']))
    def test_A_semantic_channel(self):
        self.assertEqual(self.packet['A_packet']['semantic_channel'],22)
    def test_source_pin(self):
        self.assertEqual(self.packet['source_sha256'],self.packet['B_packet']['source_sha256'])
    def test_packet_exact_verification(self):
        self.assertEqual(self.packet,verify(self.source,ISSUE,self.packet))
    def test_no_forward_means_no_custody(self):
        x=compose(fake_source(drop=True),ISSUE,drop_forward=True)
        self.assertIsNone(x['C_receipt']);self.assertEqual(x['outcome'],'ABSENT')
    def test_no_forward_cannot_have_fake_delivery(self):
        source=fake_source(drop=True);source['feedback']['deliveries'].append({'sender':'B','receiver':'C'})
        with self.assertRaises(BridgeRejected):compose(source,ISSUE,drop_forward=True)
    def test_missing_A_emission(self):
        source=copy.deepcopy(self.source);source['forward']['emissions'].pop(2)
        with self.assertRaises(BridgeRejected):compose(source,ISSUE)
    def test_wrong_A_semantic_channel(self):
        source=copy.deepcopy(self.source);source['forward']['emissions'][2]['channel']=21
        with self.assertRaises(BridgeRejected):compose(source,ISSUE)
    def test_wrong_ancestry(self):
        source=copy.deepcopy(self.source);source['forward']['occurrences'][1]['parents']=[]
        with self.assertRaises(BridgeRejected):compose(source,ISSUE)
    def test_missing_BV_return(self):
        source=copy.deepcopy(self.source);source['feedback']['deliveries'].pop()
        with self.assertRaises(BridgeRejected):compose(source,ISSUE)
    def test_change_A_payload_rejected(self):
        packet=copy.deepcopy(self.packet);packet['A_packet']['semantic_channel']=21
        with self.assertRaises(BridgeRejected):verify(self.source,ISSUE,packet)
    def test_change_B_digest_rejected(self):
        packet=copy.deepcopy(self.packet);packet['B_packet']['A_packet_sha256']='f'*64
        with self.assertRaises(BridgeRejected):verify(self.source,ISSUE,packet)
    def test_change_C_receipt_rejected(self):
        packet=copy.deepcopy(self.packet);packet['C_receipt']['outcome']='IMPROVED'
        with self.assertRaises(BridgeRejected):verify(self.source,ISSUE,packet)
    def test_epoch_replay_rejected(self):
        with self.assertRaises(BridgeRejected):verify(self.source,dict(ISSUE,id=8),self.packet)
    def test_version_rebinding_rejected(self):
        with self.assertRaises(BridgeRejected):verify(self.source,dict(ISSUE,version=4),self.packet)
    def test_wrong_choice_source_rejected(self):
        with self.assertRaises(BridgeRejected):compose(self.source,dict(ISSUE,choice=11))
    def test_invalid_issue_types(self):
        with self.assertRaises(BridgeRejected):compose(self.source,dict(ISSUE,id=True))
    def test_invalid_goal(self):
        with self.assertRaises(BridgeRejected):compose(self.source,dict(ISSUE,goal=9))
    def test_extra_packet_field_rejected(self):
        packet=copy.deepcopy(self.packet);packet['native_attested']=True
        with self.assertRaises(BridgeRejected):verify(self.source,ISSUE,packet)
    def test_source_hash_only_cannot_prove_native(self):
        self.assertNotIn('native',self.packet['C_receipt'])

class StateIntent(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=EpochState(Path(self.tmp.name)/'p.sqlite')
        self.i=self.s.issue(0,11);self.source=fake_source(12,11)
        self.packet=compose(self.source,self.i)
        self.intent=prepare(self.source,self.i,self.packet)
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def test_research_only_scope(self):
        self.assertFalse(self.intent['native_authorized'])
        self.assertEqual((self.intent['owner'],self.intent['domain'],self.intent['mode']),('C','P','execute'))
    def test_fail_closed_intent(self):
        bad=copy.deepcopy(self.intent);bad['native_authorized']=True
        with self.assertRaises(BridgeRejected):settle(self.s,self.source,self.i,self.packet,bad)
    def test_wrong_owner(self):
        bad=copy.deepcopy(self.intent);bad['owner']='A'
        with self.assertRaises(BridgeRejected):settle(self.s,self.source,self.i,self.packet,bad)
    def test_wrong_version(self):
        bad=copy.deepcopy(self.intent);bad['expected_version']+=1
        with self.assertRaises(BridgeRejected):settle(self.s,self.source,self.i,self.packet,bad)
    def test_tampered_packet_intent(self):
        bad=copy.deepcopy(self.packet);bad['A_packet']['semantic_channel']=21
        with self.assertRaises(BridgeRejected):prepare(self.source,self.i,bad)
    def test_negative_commits_once(self):
        res=settle(self.s,self.source,self.i,self.packet,self.intent)
        self.assertTrue(res['updated']);self.assertEqual(self.s.table[0],11)
    def test_replay_rejected_after_reopen(self):
        settle(self.s,self.source,self.i,self.packet,self.intent);self.s.reopen()
        with self.assertRaises(BridgeRejected):settle(self.s,self.source,self.i,self.packet,self.intent)
        self.assertEqual(self.s.audit()['updates'],1)
    def test_positive_no_update(self):
        self.s.settle(self.i,dict(__import__('research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0',fromlist=['verify_source']).verify_source(self.source,12,11)))
        i=self.s.issue(0,11);src=fake_source(11,11);p=compose(src,i);v=prepare(src,i,p)
        x=settle(self.s,src,i,p,v)
        self.assertFalse(x['updated'])
    def test_drop_no_update(self):
        src=fake_source(drop=True);p=compose(src,self.i,drop_forward=True)
        v=prepare(src,self.i,p,drop_forward=True)
        self.assertFalse(v['update_candidate'])
        self.assertFalse(settle(self.s,src,self.i,p,v,drop_forward=True)['updated'])
    def test_pending_recovery(self):
        self.s.reopen()
        self.assertEqual(self.s.unsettled(),[self.i])
        self.assertTrue(settle(self.s,self.source,self.i,self.packet,self.intent)['updated'])
    def test_readonly_verify_no_update(self):
        prepare(self.source,self.i,self.packet)
        self.assertEqual(self.s.updates,0)
    def test_host_forgery_concrete(self):
        v=hostile_counterexample()
        self.assertTrue(v['forged_research_P_intent_committed'])
        self.assertEqual(v['new_original_scheduler_calls'],0)

if __name__=='__main__':unittest.main()
