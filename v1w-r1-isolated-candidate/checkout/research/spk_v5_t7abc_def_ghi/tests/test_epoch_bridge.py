from __future__ import annotations
import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import verify_source,BridgeRejected
from research.spk_v5_t7abc_def_ghi.epoch_state_v0 import EpochState
from research.spk_v5_t7abc_def_ghi.cumulative_gate_v0 import privileged_host_forgery_counterexample


def fake_source(choice=12,goal=11,drop=False):
    if drop:
        events=[{'timestamp':10,'node_id':'C','channel':choice}]
        occ=[]; batches=[{'node':'C'}];asse=[];delivery=[];grants=[]
    else:
        c=1 if choice==11 else 2
        b=13 if choice==11 else 14
        a=21 if choice==goal else 22
        events=[{'timestamp':10,'node_id':'C','channel':choice},
                {'timestamp':11,'node_id':'B','channel':b},
                {'timestamp':12,'node_id':'A','channel':a},
                {'timestamp':12,'node_id':'A','channel':7}]
        batches=[{'node':'C'},{'node':'B'},{'node':'A'}]
        occ=[{'id':'r1','source':'C','target':'B','channel':c,'parents':[], 'delivered_at':11},
             {'id':'r2','source':'B','target':'A','channel':3 if c==1 else 4,'parents':['r1'],'delivered_at':12}]
        asse=[{'observer':'A','input_occurrences':['r2']}]
        delivery=[{'sender':'A','receiver':'B'},{'sender':'B','receiver':'C'}]
        grants=[{},{}]
    return {'schema':'spk-bv-live-dual-event-scheduler/v0e',
        'constraints':['no-learning','three-node-admission'],
        'forward':{'emissions':events,'occurrences':occ,'batches':batches,'terminal':[]},
        'feedback':{'assessments':asse,'deliveries':delivery,'link_grants':grants},
        'resources':{'timeline':[],'bv_link_grants':len(grants),'bv_service_units':len(grants),
                     'bv_memory_units':2*len(grants)}}

class SourceVerification(unittest.TestCase):
    def test_all_combinations(self):
        for choice in (11,12):
            for goal in (11,12):
                with self.subTest(choice=choice,goal=goal):
                    x=verify_source(fake_source(choice,goal),choice,goal)
                    self.assertEqual(x['A_outcome'],'IMPROVED' if choice==goal else 'WORSENED')
                    self.assertTrue(x['reverse_A_B_C'])
                    self.assertEqual(x['source_bv_deliveries'],2)
    def test_drop(self):
        x=verify_source(fake_source(drop=True),12,11,drop_forward=True)
        self.assertEqual(x['A_outcome'],'ABSENT');self.assertFalse(x['eligible_to_update'])
    def test_no_semantic_in_packet(self):
        self.assertEqual(fake_source()['feedback']['deliveries'][0].keys(),{'sender','receiver'})
    def test_rejected_variants(self):
        base=fake_source()
        trials=[('schema',lambda x:x.update(schema='wrong')),
          ('missing_constraint',lambda x:x.update(constraints=[])),
          ('lost_B',lambda x:x['forward']['emissions'].pop(1)),
          ('lost_A',lambda x:x['forward']['emissions'].pop(2)),
          ('extra_C',lambda x:x['forward']['emissions'].append({'node_id':'C','channel':12})),
          ('fake_A',lambda x:x['forward']['emissions'][2].update(channel=21)),
          ('bad_C_B',lambda x:x['forward']['occurrences'][0].update(target='A')),
          ('bad_B_A',lambda x:x['forward']['occurrences'][1].update(channel=1)),
          ('missing_parent',lambda x:x['forward']['occurrences'][1].update(parents=[])),
          ('no_assessment',lambda x:x['feedback']['assessments'].clear()),
          ('no_delivery',lambda x:x['feedback']['deliveries'].clear()),
          ('wrong_sender',lambda x:x['feedback']['deliveries'][0].update(sender='C')),
          ('wrong_grants',lambda x:x['resources'].update(bv_link_grants=0)),
          ('fake_resources',lambda x:x['resources'].update(bv_memory_units=2)),
          ('PE_order',lambda x:x['forward']['batches'].reverse()),
          ('miss_occ',lambda x:x['forward']['occurrences'].pop()),
          ('wrong_birth',lambda x:x['forward']['occurrences'][0].update(delivered_at=None))]
        for label,mutate in trials:
            with self.subTest(label=label):
                sample=copy.deepcopy(base);mutate(sample)
                with self.assertRaises(BridgeRejected):verify_source(sample,12,11)
    def test_drop_cannot_have_BV(self):
        s=fake_source(drop=True)
        s['feedback']['deliveries'].append({'sender':'A','receiver':'B'})
        with self.assertRaises(BridgeRejected):verify_source(s,12,11,drop_forward=True)
    def test_drop_cannot_have_B_emission(self):
        s=fake_source(drop=True)
        s['forward']['emissions'].append({'node_id':'B','channel':14})
        with self.assertRaises(BridgeRejected):verify_source(s,12,11,drop_forward=True)

class CState(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'P.sqlite'
        self.store=EpochState(self.path,learn=True)
    def tearDown(self):
        self.store.close();self.tmp.cleanup()
    def ev(self,dec,drop=False):
        return verify_source(fake_source(dec['choice'],dec['goal'],drop),
            dec['choice'],dec['goal'],drop_forward=drop)
    def test_recover_pending(self):
        dec=self.store.issue(0,11);self.store.reopen()
        self.assertEqual(self.store.unsettled(),[dec])
        self.assertTrue(self.store.settle(dec,self.ev(dec))['updated'])
        self.store.reopen();self.assertEqual(self.store.updates,1)
    def test_double_apply_rejected(self):
        dec=self.store.issue(0,11);ev=self.ev(dec)
        self.store.settle(dec,ev)
        with self.assertRaises(BridgeRejected):self.store.settle(dec,ev)
    def test_concurrent_issues_not_accepted(self):
        self.store.issue(0,11)
        with self.assertRaises(BridgeRejected):self.store.issue(1,12)
        self.store.reopen();self.assertEqual(len(self.store.unsettled()),1)
    def test_negative_changes_choice(self):
        dec=self.store.issue(0,11)
        self.assertEqual(dec['choice'],12)
        x=self.store.settle(dec,self.ev(dec))
        self.assertTrue(x['updated']);self.assertEqual(self.store.table[0],11)
    def test_positive_does_not_change(self):
        dec=self.store.issue(1,11)
        self.assertEqual(dec['choice'],11)
        x=self.store.settle(dec,self.ev(dec))
        self.assertFalse(x['updated']);self.assertEqual(self.store.table[1],11)
    def test_drop_has_no_update(self):
        dec=self.store.issue(0,11)
        x=self.store.settle(dec,self.ev(dec,True))
        self.assertFalse(x['updated']);self.assertEqual(self.store.table[0],12)
    def test_sequential_multiple_epochs(self):
        for i in range(8):
            cue=i%2;goal=11 if cue==0 else 12
            dec=self.store.issue(cue,goal);self.store.settle(dec,self.ev(dec))
            if i%3==2:self.store.reopen()
        self.assertEqual(self.store.updates,2)
        self.assertEqual(self.store.audit()['episodes'],8)
    def test_readback_case_version(self):
        first=self.store.issue(0,11);self.store.settle(first,self.ev(first))
        second=self.store.issue(0,11)
        self.assertEqual(second['version'],1)
        self.assertEqual(second['choice'],11)
        self.store.settle(second,self.ev(second))
        self.assertEqual(self.store.updates,1)
    def test_budget_zero(self):
        self.store.close()
        self.path.unlink()
        self.store=EpochState(self.path,learn=True,budget=0)
        d=self.store.issue(0,11)
        self.store.settle(d,self.ev(d));self.assertEqual(self.store.updates,0)
    def test_learning_disabled(self):
        self.store.close();self.path.unlink()
        self.store=EpochState(self.path,learn=False)
        d=self.store.issue(0,11);self.store.settle(d,self.ev(d))
        self.assertEqual(self.store.updates,0)
    def test_config_drift_rejected(self):
        with self.assertRaises(BridgeRejected):EpochState(self.path,learn=False,create=False)
    def test_reinitialize_denied(self):
        with self.assertRaises(BridgeRejected):EpochState(self.path,learn=True)
    def test_invalid_goal(self):
        with self.assertRaises(BridgeRejected):self.store.issue(0,13)
    def test_tampered_vote(self):
        d=self.store.issue(0,11);e=self.ev(d)
        e['A_outcome']='IMPROVED'
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_tampered_choice(self):
        d=self.store.issue(0,11);e=self.ev(d)
        e['C_choice']=11
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_bad_source_digest(self):
        d=self.store.issue(0,11);e=self.ev(d)
        e['source_sha256']='bad'
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_structural_missing_BV(self):
        d=self.store.issue(0,11);e=self.ev(d)
        e['reverse_A_B_C']=False
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_extra_evidence_key(self):
        d=self.store.issue(0,11);e=self.ev(d)
        e['secret']='no'
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_issue_rebinding(self):
        d=self.store.issue(0,11);e=self.ev(d)
        d['choice']=11
        with self.assertRaises(BridgeRejected):self.store.settle(d,e)
    def test_audit_state_mutation(self):
        d=self.store.issue(0,11);self.store.settle(d,self.ev(d))
        self.store.db.execute('UPDATE policy SET choice=12 WHERE cue=0')
        with self.assertRaises(BridgeRejected):self.store.audit()
    def test_audit_ledger_mutation(self):
        d=self.store.issue(0,11);self.store.settle(d,self.ev(d))
        self.store.db.execute("UPDATE ledger SET hash=? WHERE seq=1",('bad',))
        with self.assertRaises(BridgeRejected):self.store.audit()
    def test_failed_settlement_does_not_consume(self):
        d=self.store.issue(0,11);e=self.ev(d)
        bad=copy.deepcopy(e);bad['A_emission']=21
        with self.assertRaises(BridgeRejected):self.store.settle(d,bad)
        self.assertEqual(self.store.unsettled(),[d])
        self.store.settle(d,e)
    def test_host_privilege_counterexample(self):
        self.assertTrue(privileged_host_forgery_counterexample()['host_forged_ledger_accepted'])

class RealSourceOptional(unittest.TestCase):
    def test_frozen_run_if_all_deps_present(self):
        try:from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
        except ImportError:self.skipTest('complete architecture checkout unavailable')
        from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import execute_episode
        for choice in (11,12):
            for goal in (11,12):
                x=execute_episode(choice,goal)
                self.assertEqual(x['A_outcome'],'IMPROVED' if choice==goal else 'WORSENED')
        self.assertFalse(execute_episode(12,11,drop_forward=True)['reverse_A_B_C'])

if __name__=='__main__':unittest.main()
