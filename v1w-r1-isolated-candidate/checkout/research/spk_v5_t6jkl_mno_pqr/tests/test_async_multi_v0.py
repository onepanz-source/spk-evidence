import copy
import unittest
from research.spk_v5_t6jkl_mno_pqr.async_multi_v0 import (MultiPolicy,LoopBoundary,
    make_votes,reseal,scenario,objective,GOALS_PHASES)

class TwoReceiverPE(unittest.TestCase):
    def setUp(self):
        self.p=MultiPolicy(True);self.d=self.p.choose(0,0);self.v=make_votes(self.d,0)
    def test_two_separate_receivers(self):self.assertEqual([x['vote']['receiver'] for x in self.v],['A','D'])
    def test_both_negative_initial(self):self.assertEqual([x['vote']['outcome'] for x in self.v],['WORSENED']*2)
    def test_receiver_measurement_from_PE(self):self.assertEqual([x['vote']['observed_raw'] for x in self.v],[11,11])
    def test_receiver_goal_local(self):self.assertEqual([x['vote']['goal_raw'] for x in self.v],[5,5])
    def test_return_channels_distinct(self):self.assertEqual([x['relay_channel'] for x in self.v],[52,55])
    def test_first_vote_no_update(self):self.assertEqual(self.p.submit(self.v[0],5),'RECEIVED')
    def test_quorum_negative_updates(self):
        self.p.submit(self.v[0],5)
        self.assertEqual(self.p.submit(self.v[1],6),'UPDATED')
        self.assertEqual(self.p.table[0],11)
    def test_reverse_order_same_update(self):
        self.p.submit(self.v[1],5)
        self.assertEqual(self.p.submit(self.v[0],6),'UPDATED')
        self.assertEqual(self.p.table[0],11)
    def test_positive_quorum_does_not_flip(self):
        self.p.submit(self.v[0],5);self.p.submit(self.v[1],6)
        d=self.p.choose(0,10);votes=make_votes(d,0)
        self.assertEqual([x['vote']['outcome'] for x in votes],['IMPROVED','IMPROVED'])
        self.p.submit(votes[0],15);self.assertEqual(self.p.submit(votes[1],16),'IMPROVED_HELD')
        self.assertEqual(self.p.table[0],11)
    def test_receiver_disagreement_holds(self):
        votes=make_votes(self.d,0,(0,))
        self.assertEqual([x['vote']['outcome'] for x in votes],['WORSENED','IMPROVED'])
        self.p.submit(votes[0],5)
        self.assertEqual(self.p.submit(votes[1],6),'CONFLICT_HELD')
        self.assertEqual(self.p.table[0],12)
    def test_conflict_does_not_block_other_context(self):
        votes=make_votes(self.d,0,(0,))
        self.p.submit(votes[0],5);self.p.submit(votes[1],6)
        d=self.p.choose(1,10);vv=make_votes(d,0,(0,))
        self.p.submit(vv[0],15);self.assertEqual(self.p.submit(vv[1],16),'UPDATED')
        self.assertEqual(self.p.table,{0:12,1:12})
    def test_explicit_budget(self):
        p=MultiPolicy(True,0);d=p.choose(0,0);v=make_votes(d,0)
        p.submit(v[0],5);self.assertEqual(p.submit(v[1],6),'HELD');self.assertEqual(p.updates,0)
    def test_unchanged_no_feedback(self):
        self.p.submit(self.v[0],5)
        self.assertEqual(self.p.close_batch(),1)
        self.assertEqual(self.p.table[0],12)
    def test_version_custody_concurrent(self):
        second=self.p.choose(0,0);vv=make_votes(second,0)
        self.p.submit(self.v[0],5);self.p.submit(self.v[1],6)
        with self.assertRaisesRegex(LoopBoundary,'OBSOLETE_POLICY_VERSION'):self.p.submit(vv[0],6)
        self.assertEqual(self.p.table[0],11)
    def test_other_cue_version_not_stale(self):
        other=self.p.choose(1,0);vv=make_votes(other,0)
        self.p.submit(self.v[0],5);self.p.submit(self.v[1],6)
        self.p.submit(vv[0],5);self.assertEqual(self.p.submit(vv[1],6),'UPDATED')
        self.assertEqual(self.p.table,{0:11,1:12})
    def test_goal_reversal(self):self.assertEqual((objective(0,0,'A'),objective(1,0,'A')),(5,11))

class Adversarial(unittest.TestCase):
    def setUp(self):
        self.p=MultiPolicy();self.d=self.p.choose(0,0);self.v=make_votes(self.d,0)
    def assert_invalid(self,mutation,tick=5):
        forged=copy.deepcopy(self.v[0]);mutation(forged)
        with self.assertRaises(LoopBoundary):self.p.submit(forged,tick)
        self.assertEqual(self.p.table[0],12)
    def test_bad_schema(self):self.assert_invalid(lambda e:e.update(extra=1))
    def test_bad_digest(self):self.assert_invalid(lambda e:e.update(vote_sha256='0'*64))
    def test_bad_relay_digest(self):self.assert_invalid(lambda e:e.update(relay_sha256='0'*64))
    def test_bad_relay_channel(self):self.assert_invalid(lambda e:e.update(relay_channel=999))
    def test_bad_outcome(self):self.assert_invalid(lambda e:e['vote'].update(outcome='IMPROVED'))
    def test_bad_receiver(self):self.assert_invalid(lambda e:e['vote'].update(receiver='D'))
    def test_bad_decision_binding(self):self.assert_invalid(lambda e:e['vote'].update(decision_sha256='0'*64))
    def test_wrong_cue(self):self.assert_invalid(lambda e:e['vote'].update(cue=1))
    def test_wrong_version(self):self.assert_invalid(lambda e:e['vote'].update(version=1))
    def test_wrong_goal(self):self.assert_invalid(lambda e:e['vote'].update(goal_raw=11))
    def test_forged_native_field(self):self.assert_invalid(lambda e:e['vote'].update(native_credit=True))
    def test_premature(self):self.assert_invalid(lambda e:None,2)
    def test_expired(self):self.assert_invalid(lambda e:None,8)
    def test_replay(self):
        self.p.submit(self.v[0],5)
        with self.assertRaisesRegex(LoopBoundary,'DUPLICATE_RECEIVER_VOTE'):self.p.submit(self.v[0],6)
    def test_replay_complete(self):
        self.p.submit(self.v[0],5);self.p.submit(self.v[1],6)
        with self.assertRaisesRegex(LoopBoundary,'NO_PENDING_OR_REPLAY'):self.p.submit(self.v[0],7)
    def test_host_forged_both_positive_suppress_update(self):
        false=[reseal({**e['vote'],'outcome':'IMPROVED'}) for e in self.v]
        self.p.submit(false[0],5);self.assertEqual(self.p.submit(false[1],6),'IMPROVED_HELD')
        self.assertEqual(self.p.table[0],12) # Known bad, but not corrected
    def test_host_forged_both_negative_destabilize(self):
        self.p.submit(self.v[0],5);self.p.submit(self.v[1],6)
        d=self.p.choose(0,10);votes=make_votes(d,0)
        self.assertEqual([x['vote']['outcome'] for x in votes],['IMPROVED']*2)
        false=[reseal({**e['vote'],'outcome':'WORSENED'}) for e in votes]
        self.p.submit(false[0],15);self.assertEqual(self.p.submit(false[1],16),'UPDATED')
        self.assertEqual(self.p.table[0],12) # host wins
    def test_one_forged_receiver_not_quorum(self):
        forged=reseal({**self.v[0]['vote'],'outcome':'IMPROVED'})
        self.p.submit(forged,5)
        self.assertEqual(self.p.submit(self.v[1],6),'CONFLICT_HELD')
        self.assertEqual(self.p.table[0],12)
    def test_host_can_impersonate_other_receiver(self):
        original=self.v[0]['vote'];fake=reseal({**original,'receiver':'D'})
        self.p.submit(self.v[0],5)
        self.assertEqual(self.p.submit(fake,6),'UPDATED') # forged D negative
        self.assertEqual(self.p.updates,1)
    def test_duplicate_tag_fails_quorum(self):
        self.p.submit(self.v[0],5)
        with self.assertRaises(LoopBoundary):self.p.submit(self.v[0],6)
        self.assertEqual(self.p.updates,0)

class ScenarioTests(unittest.TestCase):
    def test_static_baseline(self):
        x=scenario(learn=False);self.assertEqual((x['episodes'],x['joint_successes'],x['updates']),(96,48,0))
    def test_four_phase_learning(self):
        x=scenario();self.assertEqual((x['episodes'],x['joint_successes'],x['updates']),(96,80,8))
    def test_transient_cost_each_phase(self):
        x=scenario();self.assertEqual([sum(r['joint_success'] for r in x['rows'] if r['phase']==i) for i in range(4)],[20]*4)
    def test_no_lookahead_in_plant(self):
        x=scenario();self.assertEqual([x['rows'][24*i]['A_goal'] for i in range(4)],[5,11,5,11])
    def test_stale_deliveries_dont_flip(self):
        x=scenario();self.assertEqual((x['stale_rejections'],x['abandoned']),(8,8))
    def test_order_independence(self):
        a=scenario();b=scenario(mode='reverse');self.assertEqual(a['joint_successes'],b['joint_successes'])
        self.assertEqual(a['final_policy'],b['final_policy'])
    def test_jitter_reproducibility(self):
        a=scenario(mode='jitter',seed=42);b=scenario(mode='jitter',seed=42)
        self.assertEqual(a,b)
    def test_jitter_vs_baseline(self):
        a=scenario(mode='jitter',seed=42);b=scenario(learn=False,mode='jitter',seed=42)
        self.assertGreater(a['joint_successes'],b['joint_successes'])
    def test_multiple_seeds_jitter(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                a=scenario(mode='jitter',seed=seed)
                self.assertGreaterEqual(a['joint_successes'],76)
                self.assertEqual(a['updates'],8)
    def test_loss_bounded(self):
        a=scenario(mode='jitter',drop_mod=7)
        self.assertEqual(a['dropped'],27)
        self.assertEqual(a['joint_successes'],80)
    def test_loss_vs_control(self):
        a=scenario(mode='jitter',drop_mod=7)
        b=scenario(learn=False,mode='jitter',drop_mod=7)
        self.assertGreater(a['joint_successes'],b['joint_successes'])
    def test_total_loss_no_learning(self):
        # drop_mod=1 suppresses every receiver vote.
        a=scenario(drop_mod=1)
        self.assertEqual((a['updates'],a['joint_successes']),(0,48))
    def test_conflicting_receiver_holds(self):
        a=scenario(mode='reverse',conflict_contexts=(0,))
        self.assertEqual((a['updates'],a['conflicts'],a['joint_successes']),(4,48,40))
    def test_conflict_no_spurious_update_cue0(self):
        a=scenario(mode='reverse',conflict_contexts=(0,))
        self.assertEqual(a['updates'],4)
        self.assertEqual(a['conflicts'],48)
        self.assertEqual(a['A_successes'],64)
    def test_conflict_joint_bound(self):
        a=scenario(conflict_contexts=(0,),mode='reverse')
        self.assertEqual(sum(r['joint_success'] for r in a['rows'] if r['cue']==0),0)
    def test_budget_underfit_is_exposed(self):
        a=scenario(budget=1);b=scenario(learn=False,budget=1)
        self.assertLess(a['joint_successes'],b['joint_successes'])
    def test_final_policy_exact(self):self.assertEqual(scenario()['final_policy'],{0:12,1:11})
    def test_one_phase(self):self.assertEqual(scenario(phases=1)['joint_successes'],20)
    def test_two_phases(self):self.assertEqual(scenario(phases=2)['joint_successes'],40)
    def test_no_native_credit(self):
        a=scenario();self.assertNotIn('native_learning',a)
    def test_invalid_drop_rate(self):
        with self.assertRaises(LoopBoundary):scenario(drop_mod=-1)
    def test_invalid_mode(self):
        with self.assertRaises(LoopBoundary):scenario(mode='trusted')

if __name__=='__main__':unittest.main()
