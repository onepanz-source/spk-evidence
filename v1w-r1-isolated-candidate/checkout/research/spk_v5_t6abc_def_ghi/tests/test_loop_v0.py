import copy, unittest
from research.spk_v5_t6abc_def_ghi.loop_v0 import (CPolicy,LoopBoundary,GOALS,INITIAL,Node,
    pe,emit_single,forward,a_measure,backward,episode,compare_interventions,trial,digest)

class ExecutableLoopTests(unittest.TestCase):
    def test_exact_pe_C(self):
        c=CPolicy(True);d,e=c.choose(0)
        self.assertEqual((d['choice'],e['emissions']),(12,(12,)))
    def test_exact_pe_B(self):
        c=CPolicy(True);d,_=c.choose(0)
        self.assertEqual(forward(d)['emissions'],(32,))
    def test_exact_pe_A(self):
        c=CPolicy(True);d,_=c.choose(0)
        pkt,a=a_measure(0,forward(d)['emissions'][0],d)
        self.assertEqual((a['raw'],pkt['outcome']),(11,'WORSENED'))
    def test_return_is_pe(self):
        c=CPolicy(True);d,_=c.choose(0);p,_=a_measure(0,forward(d)['emissions'][0],d)
        b,areturn,breturn=backward(p)
        self.assertEqual((areturn['emissions'],breturn['emissions']),((42,),(52,)))
        self.assertEqual(c.apply(b)['C_return_emission'],[72])
    def test_completed_feedback_updates_future_C(self):
        c=CPolicy(True);x=episode(c,0);y=episode(c,0)
        self.assertEqual((x['C_choice'],y['C_choice']),(12,11))
        self.assertEqual((x['A_outcome'],y['A_outcome']),('WORSENED','IMPROVED'))
    def test_control_no_learning(self):
        c=CPolicy(False);x=episode(c,0);y=episode(c,0)
        self.assertEqual((x['C_choice'],y['C_choice']),(12,12))
        self.assertEqual(c.updates,0)
    def test_48_episode_paired_ablation(self):
        seq=tuple(i%2 for i in range(48));trained=trial(True,seq);control=trial(False,seq)
        self.assertEqual((trained['successes'],control['successes'],trained['updates']),(46,0,2))
        self.assertEqual(trained['final_policy'],{0:11,1:12})
        self.assertEqual(control['final_policy'],INITIAL)
    def test_intervention_is_real_source_PE(self):
        c=CPolicy(True);d,_=c.choose(0);cf=compare_interventions(0,d)
        self.assertEqual(cf['outcome_delta'],-1)
        self.assertEqual(cf['absent_raw'],0)
    def test_counterfactual_effect_flip(self):
        c=CPolicy(True);episode(c,0);d,_=c.choose(0);cf=compare_interventions(0,d)
        self.assertEqual(cf['outcome_delta'],1)
        self.assertEqual(cf['opposite_success'],0)
    def test_context_custody(self):
        c=CPolicy(True);episode(c,0)
        self.assertEqual(c.table[1],11)
    def test_3_way_neutral_no_update(self):
        c=CPolicy(True);d,_=c.choose(0)
        pkt,_=a_measure(0,None,d,allow_absent=True)
        relay,_,_=backward(pkt)
        self.assertFalse(c.apply(relay)['policy_updated'])
        self.assertEqual(c.table,INITIAL)
    def test_no_feedback_no_update(self):
        c=CPolicy(True)
        x=episode(c,0,False)
        self.assertFalse(x['updated']);self.assertEqual(c.table,INITIAL)
        self.assertEqual(len(c.pending),1)
    def test_missing_C_without_explicit_ablation_fails(self):
        c=CPolicy(True);d,_=c.choose(0)
        with self.assertRaises(LoopBoundary):a_measure(0,None,d)
    def test_cue_out_of_domain(self):
        c=CPolicy(True)
        for cue in (-1,2,True,'0',None):
            with self.subTest(cue=cue),self.assertRaises(LoopBoundary): c.choose(cue)
    def test_incorrect_output_rejected(self):
        with self.assertRaises(LoopBoundary):emit_single('test',0,1,2,0)
    def test_future_tick_rejected(self):
        with self.assertRaises(LoopBoundary):pe('x',(),-1,())

class AdversarialFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.c=CPolicy(True)
        self.d,_=self.c.choose(0)
        self.p,_=a_measure(0,forward(self.d)['emissions'][0],self.d)
        self.relay,_,_=backward(self.p)
    def assert_rejected(self,mutate):
        copyrelay=copy.deepcopy(self.relay);mutate(copyrelay)
        with self.assertRaises(LoopBoundary):self.c.apply(copyrelay)
        self.assertEqual(self.c.table,INITIAL)
    def test_A_payload_tamper(self):self.assert_rejected(lambda x:x['payload'].update(outcome='IMPROVED'))
    def test_A_sha_tamper(self):self.assert_rejected(lambda x:x.update(a_sha256='0'*64))
    def test_B_digest_tamper(self):self.assert_rejected(lambda x:x.update(b_sha256='0'*64))
    def test_wrong_receiver_channel(self):self.assert_rejected(lambda x:x.update(c_channel=99))
    def test_wrong_B_channel(self):self.assert_rejected(lambda x:x.update(b_channel=99))
    def test_wrong_decision_id(self):self.assert_rejected(lambda x:x['payload'].update(decision_id=10))
    def test_wrong_decision_binding(self):self.assert_rejected(lambda x:x['payload'].update(decision_sha256='0'*64))
    def test_wrong_cue(self):self.assert_rejected(lambda x:x['payload'].update(cue=1))
    def test_unsupported_feedback_outcome(self):self.assert_rejected(lambda x:x['payload'].update(outcome='PERFECT'))
    def test_disallowed_extra_A_field(self):self.assert_rejected(lambda x:x['payload'].update(native_credit=True))
    def test_reject_invalid_return_tick(self):
        with self.assertRaises(LoopBoundary):self.c.apply(self.relay,current_tick=8)
    def test_accept_delayed_before_deadline(self):
        self.assertTrue(self.c.apply(self.relay,current_tick=7)['policy_updated'])
    def test_reject_replay(self):
        self.c.apply(self.relay)
        with self.assertRaises(LoopBoundary):self.c.apply(self.relay)
    def test_reject_conflict_after_first(self):
        self.c.apply(self.relay)
        altered=copy.deepcopy(self.relay); altered['payload']['outcome']='IMPROVED'
        with self.assertRaises(LoopBoundary):self.c.apply(altered)
    def test_wrong_pe_policy_choice_rejected(self):
        self.assert_rejected(lambda x:x['payload'].update(a_feedback_ch=41))
    def test_forged_rebound_A_record_is_accepted(self):
        """A privileged host reissues a structurally valid FALSE success receipt."""
        host=copy.deepcopy(self.p)
        host['outcome']='IMPROVED';host['a_feedback_ch']=41
        forged,_,_=backward(host)
        self.assertFalse(self.c.apply(forged)['policy_updated'])
        self.assertEqual(self.c.table,INITIAL)
        self.assertEqual(host['observed_raw'],11)  # A actually missed goal 5.
    def test_forged_negative_can_force_bad_change(self):
        c=CPolicy(True);episode(c,0)  # now correct for cue 0
        d,_=c.choose(0)
        p,_=a_measure(0,forward(d)['emissions'][0],d)
        self.assertEqual(p['outcome'],'IMPROVED')
        p['outcome']='WORSENED';p['a_feedback_ch']=42
        forged,_,_=backward(p)
        self.assertTrue(c.apply(forged)['policy_updated'])
        self.assertEqual(c.table[0],12)  # host lies; learning destabilized
    def test_bad_packet_structure_rejected(self):self.assert_rejected(lambda x:x.pop('payload'))
    def test_wrong_goal_raw_is_not_anti_host_attestation(self):
        """C does not know A's goal; host may rewrite it with coherent digest."""
        host=copy.deepcopy(self.p);host['goal_raw']=11;host['outcome']='IMPROVED';host['a_feedback_ch']=41
        forged,_,_=backward(host)
        self.assertFalse(self.c.apply(forged)['policy_updated'])

if __name__=='__main__':unittest.main()

class ConcurrentPolicyTests(unittest.TestCase):
    def test_second_old_negative_rejected_after_first_updates(self):
        c=CPolicy(True)
        d1,_=c.choose(0);d2,_=c.choose(0)
        self.assertEqual(d1['policy_version'],d2['policy_version'])
        p1,_=a_measure(0,forward(d1)['emissions'][0],d1)
        p2,_=a_measure(0,forward(d2)['emissions'][0],d2)
        m1,_,_=backward(p1);m2,_,_=backward(p2)
        self.assertTrue(c.apply(m1)['policy_updated'])
        with self.assertRaisesRegex(LoopBoundary,'STALE_POLICY_VERSION'):c.apply(m2)
        self.assertEqual(c.table[0],11)
    def test_unrelated_context_credit_stays_valid(self):
        c=CPolicy(True);d1,_=c.choose(0);d2,_=c.choose(1)
        p1,_=a_measure(0,forward(d1)['emissions'][0],d1)
        p2,_=a_measure(1,forward(d2)['emissions'][0],d2)
        m1,_,_=backward(p1);m2,_,_=backward(p2)
        c.apply(m1)
        self.assertTrue(c.apply(m2)['policy_updated'])
        self.assertEqual(c.table,{0:11,1:12})
    def test_stale_negative_cannot_destabilize_new_version(self):
        c=CPolicy(True);old,_=c.choose(0);episode(c,0)
        p,_=a_measure(0,forward(old)['emissions'][0],old)
        m,_,_=backward(p)
        with self.assertRaisesRegex(LoopBoundary,'STALE_POLICY_VERSION'):c.apply(m)
        self.assertEqual(c.table[0],11)
