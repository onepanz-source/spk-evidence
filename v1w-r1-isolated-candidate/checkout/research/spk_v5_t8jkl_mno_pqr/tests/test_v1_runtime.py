"""T8 v1 reference semantics, bounded P grant, parity and hostile-host limits."""
from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from research.spk_v5_t7abc_def_ghi.tests.test_epoch_bridge import fake_source
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import verify_source
from research.spk_v5_t8jkl_mno_pqr.semantic_bus_v1 import dispatch,verify,SCHEMA
from research.spk_v5_t8jkl_mno_pqr.p_authority_v1 import PAuthorityV1
from research.spk_v5_t8jkl_mno_pqr.runtime_v1_reference import trial,epoch
from research.spk_v5_t8jkl_mno_pqr.cumulative_reference_gate import duplicate_and_recovery,host_forgery_witness


def fake_exec(choice,goal,*,drop_forward=False):
    source=fake_source(choice,goal,drop_forward)
    verified=verify_source(source,choice,goal,drop_forward=drop_forward)
    return source,verified

class SemanticBus(unittest.TestCase):
    def setUp(self):
        self.issue={'id':0,'cue':0,'choice':12,'version':0,'goal':11}
        self.source=fake_source(12,11)
        self.packet=dispatch(self.source,self.issue)
    def test_schema(self):self.assertEqual(self.packet['schema'],SCHEMA)
    def test_path(self):
        self.assertEqual(self.packet['carrier'],'REFERENCE_V1_C_RECEIPT')
        self.assertEqual(self.packet['b']['carrier'],'REFERENCE_V1_B_TO_C')
        self.assertEqual(self.packet['b']['a']['carrier'],'REFERENCE_V1_A_TO_B')
    def test_A_verdict(self):self.assertEqual(self.packet['payload']['verdict'],'WORSENED')
    def test_not_native_claim(self):self.assertEqual(self.packet['payload']['authoritativeness'],'REFERENCE_HOST_UNATTESTED')
    def test_absence(self):
        self.assertIsNone(dispatch(fake_source(drop=True),self.issue,drop=True))
    def test_four_source_semantics(self):
        for choice in (11,12):
            for goal in (11,12):
                d={**self.issue,'choice':choice,'goal':goal}
                packet=dispatch(fake_source(choice,goal),d)
                self.assertEqual(packet['payload']['verdict'], 'IMPROVED' if choice==goal else 'WORSENED')
    def test_validate_exact(self):self.assertEqual(verify(self.source,self.issue,self.packet),self.packet)
    def test_mutations_rejected(self):
        def setv(p,path,value):
            x=p
            for part in path[:-1]:x=x[part]
            x[path[-1]]=value
        mutations=[
          (('schema',),'spk-bv-live-dual-event-scheduler/v0e'),
          (('payload','verdict'),'IMPROVED'),
          (('payload','decision_id'),99),
          (('payload','policy_version'),9),
          (('payload','context_id'),1),
          (('payload','A_emission_channel'),21),
          (('payload','source_digest'),'0'*64),
          (('payload','causal_parent_occurrence_id'),'forged'),
          (('payload','authoritativeness'),'NATIVE_SPK'),
          (('b','a_digest'),'0'*64),
          (('b','a','payload','verdict'),'IMPROVED'),
          (('b','structural_delivery_digest'),'0'*64),
          (('b_digest',),'0'*64),
          (('carrier',),'V0E_NATIVE')]
        for path,value in mutations:
            with self.subTest(path=path):
                p=copy.deepcopy(self.packet);setv(p,path,value)
                with self.assertRaises(ValueError):verify(self.source,self.issue,p)
    def test_wrong_source_rejected(self):
        with self.assertRaises(ValueError):verify(fake_source(11,11),self.issue,self.packet)
    def test_missing_reverse_rejected(self):
        s=copy.deepcopy(self.source);s['feedback']['deliveries'].pop()
        with self.assertRaises(ValueError):dispatch(s,self.issue)
    def test_missing_A_rejected(self):
        s=copy.deepcopy(self.source);s['forward']['emissions'].pop(2)
        with self.assertRaises(ValueError):dispatch(s,self.issue)
    def test_unexpected_extra_A_rejected(self):
        s=copy.deepcopy(self.source);s['forward']['emissions'].append(copy.deepcopy(s['forward']['emissions'][2]))
        with self.assertRaises(ValueError):dispatch(s,self.issue)

class PAuthority(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'P.db'
        self.state=PAuthorityV1(self.path)
    def tearDown(self):self.state.close();self.tmp.cleanup()
    def run_one(self,cue=0,goal=11,drop=False):
        d=self.state.issue(cue,goal);src=fake_source(d['choice'],goal,drop)
        packet=dispatch(src,d,drop=drop)
        return d,src,packet,self.state.settle(d,src,packet,drop=drop)
    def test_first_negative_grants_and_updates(self):
        d,s,p,r=self.run_one()
        self.assertTrue(r['P_written']);self.assertEqual(r['grant_id'],0)
        self.assertEqual(self.state.policy[0],11);self.assertEqual(self.state.versions[0],1)
    def test_positive_never_grants(self):
        *_,r=self.run_one(cue=1)
        self.assertFalse(r['P_written']);self.assertIsNone(r['grant_id'])
    def test_drop_never_grants(self):
        *_,r=self.run_one(drop=True)
        self.assertFalse(r['P_written']);self.assertEqual(r['outcome'],'ABSENT')
    def test_replay_rejected(self):
        d,s,p,r=self.run_one()
        with self.assertRaises(ValueError):self.state.settle(d,s,p)
    def test_reopen_once(self):
        d=self.state.issue(0,11);self.state.reopen();self.assertEqual(self.state.unsettled(),[d])
        s=fake_source(12,11);p=dispatch(s,d);self.state.settle(d,s,p)
        self.state.reopen();self.assertEqual(self.state.audit()['reference_grants'],1)
    def test_no_second_open_issue(self):
        self.state.issue(0,11)
        with self.assertRaises(ValueError):self.state.issue(1,12)
    def test_negative_tamper_no_commit(self):
        d=self.state.issue(0,11);s=fake_source(12,11);p=dispatch(s,d)
        p['payload']['verdict']='IMPROVED'
        with self.assertRaises(ValueError):self.state.settle(d,s,p)
        self.assertEqual(self.state.unsettled(),[d]);self.assertEqual(self.state.audit()['reference_grants'],0)
    def test_context_tamper_no_commit(self):
        d=self.state.issue(0,11);s=fake_source(12,11);p=dispatch(s,d)
        forged={**d,'cue':1}
        with self.assertRaises(ValueError):self.state.settle(forged,s,p)
    def test_version_tamper_no_commit(self):
        d=self.state.issue(0,11);s=fake_source(12,11);p=dispatch(s,d)
        with self.assertRaises(ValueError):self.state.settle({**d,'version':77},s,p)
    def test_restart_rejects_wrong_settings(self):
        with self.assertRaises(ValueError):PAuthorityV1(self.path,create=False,learn=False)
    def test_reinitialize_rejected(self):
        with self.assertRaises(ValueError):PAuthorityV1(self.path,create=True)
    def test_disable_learning_no_grants(self):
        self.state.close();self.path.unlink();self.state=PAuthorityV1(self.path,learn=False)
        *_,r=self.run_one();self.assertFalse(r['P_written'])
    def test_budget_zero_no_grants(self):
        self.state.close();self.path.unlink();self.state=PAuthorityV1(self.path,budget=0)
        *_,r=self.run_one();self.assertFalse(r['P_written'])
    def test_bad_meta(self):
        self.state.db.execute("UPDATE metadata SET v='D' WHERE k='owner'")
        with self.assertRaises(ValueError):self.state.reopen()
        self.state=PAuthorityV1(self.path,learn=True,create=False) if False else self.state
    def test_bad_materialized_P(self):
        self.state.db.execute('UPDATE p SET choice=11 WHERE cue=0')
        with self.assertRaises(ValueError):self.state.audit()
    def test_bad_ledger_hash(self):
        self.state.db.execute("UPDATE ledger SET hash='bad' WHERE seq=0")
        with self.assertRaises(ValueError):self.state.audit()
    def test_bad_grant_consumed(self):
        self.run_one();self.state.db.execute('UPDATE grant SET consumed=0')
        with self.assertRaises(ValueError):self.state.audit()
    def test_reopen_after_single_commit(self):
        self.run_one();self.state.reopen();self.assertEqual(self.state.audit()['reference_P_writes'],1)
    def test_issue_goal_out_of_domain(self):
        with self.assertRaises(ValueError):self.state.issue(0,13)
    def test_mode_cannot_inject(self):
        d=self.state.issue(0,11);s=fake_source(12,11);p=dispatch(s,d)
        d={**d,'mode':'verify'}
        with self.assertRaises(ValueError):self.state.settle(d,s,p)
    def test_no_host_native_grant(self):
        self.run_one();self.assertEqual(self.state.audit()['reference_grants'],1)
        self.assertEqual(len(list(self.state.db.execute("SELECT * FROM grant WHERE domain='P'"))),1)

class CumulativeParity(unittest.TestCase):
    def test_48_88_with_fake_executor(self):
        c=trial(learn=False,source_executor=fake_exec)
        a=trial(learn=True,source_executor=fake_exec)
        self.assertEqual((c['successes'],a['successes'],a['reference_v1_P_grants']),(48,88,8))
    def test_0_when_forward_missing(self):
        a=trial(learn=True,phases=1,drop=True,source_executor=fake_exec)
        self.assertEqual((a['successes'],a['reference_v1_P_grants'],a['reference_v1_semantic_receipts']),(0,0,0))
    def test_reopen_parity(self):
        x=trial(learn=True,source_executor=fake_exec,reopen_every=12)
        y=trial(learn=True,source_executor=fake_exec,reopen_every=0)
        self.assertEqual(x,y)
    def test_byte_determinism(self):
        self.assertEqual(trial(learn=True,source_executor=fake_exec),trial(learn=True,source_executor=fake_exec))
    def test_host_forgery_negative(self):
        self.assertTrue(host_forgery_witness()['reference_v1_grant_forged'])
    def test_recovery(self):self.assertTrue(duplicate_and_recovery()['replay_rejected'])
    def test_real_source_execution_if_complete_checkout(self):
        try:import spk_architecture_v1.temporal_transport_v1a
        except ImportError:self.skipTest('Original admission modules unavailable in this local test environment')
        from research.spk_v5_t8jkl_mno_pqr.runtime_v1_reference import epoch
        with tempfile.TemporaryDirectory() as tmp:
            state=PAuthorityV1(Path(tmp)/'p.db')
            row=epoch(state,0,11)
            self.assertTrue(row['P_write'])
            self.assertEqual(state.audit()['reference_grants'],1)
            state.close()

if __name__=='__main__':unittest.main()
