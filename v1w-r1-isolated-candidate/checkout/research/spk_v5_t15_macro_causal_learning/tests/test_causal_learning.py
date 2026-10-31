import json, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from research.spk_v5_t15_macro_causal_learning.causal_cell_v1 import (
    ANeuron,BRelay,CNeuron,LearningCell,ThermalWorld,HEAT,COOL,sha)
from research.spk_v5_t15_macro_causal_learning.prospective_gate import (
    TRAIN_TEMPS,TEST_TEMPS,EQUILIBRIA,SEEDS,one_cell,experiment)

class CausalLocalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'cell.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def new(self,target=6,theta=12):return LearningCell(self.path,setpoint=target,theta=theta)

    def test_world_only_actions_not_verdicts(self):
        w=ThermalWorld(8)
        self.assertEqual(w.apply(4,HEAT),5)
        self.assertEqual(w.apply(4,COOL),3)
        self.assertEqual(w.apply(0,COOL),0)
        self.assertEqual(w.apply(15,HEAT),15)
        self.assertFalse(hasattr(w,'verdict'))
    def test_reverse_actuator_is_different_world(self):
        world=ThermalWorld(8,reverse_actuator=True)
        self.assertEqual(world.apply(4,HEAT),3)
        self.assertEqual(world.apply(4,COOL),5)
    def test_reverse_actuator_reopen(self):
        e=LearningCell(self.path,setpoint=8,reverse_actuator=True)
        try:
            e.trial(4)
            before=e.audit();e.reopen()
            self.assertEqual(before,e.audit())
        finally:e.close()
    def test_world_does_not_offer_correct_choice(self):
        w=ThermalWorld(8)
        self.assertFalse(hasattr(w,'correct_choice'))
        self.assertFalse(hasattr(w,'reward'))
    def test_invalid_setpoints(self):
        for t in (-1,0,2,13,17,8.0,'8'):
            with self.subTest(t=t),self.assertRaises(ValueError):ThermalWorld(t)
    def test_invalid_temperatures(self):
        w=ThermalWorld(8)
        for temp in (-1,16,3.0,'4',True):
            with self.subTest(temp=temp),self.assertRaises(ValueError):w.apply(temp,HEAT)
    def test_invalid_action(self):
        with self.assertRaises(ValueError):ThermalWorld(8).apply(4,42)
    def test_c_thresholds_all_temperatures(self):
        for theta in range(1,17):
            for temp in range(16):
                action,proof=CNeuron.choose(temp,theta)
                self.assertEqual(action,HEAT if temp<theta else COOL)
                self.assertEqual(len(proof),64)
    def test_c_invalid(self):
        for temp,theta in [(16,8),(2,0),(2,17),(2,1.0),(2,True)]:
            with self.subTest(temp=temp,theta=theta),self.assertRaises(ValueError):CNeuron.choose(temp,theta)
    def test_a_sign_of_environment_not_choice_label(self):
        self.assertEqual(ANeuron.judge(4,5,8)['verdict'],'IMPROVED')
        self.assertEqual(ANeuron.judge(4,3,8)['verdict'],'WORSENED')
        self.assertEqual(ANeuron.judge(8,8,8)['verdict'],'NEUTRAL')
    def test_a_pe_truth_table_all_states(self):
        for t in range(3,13):
            for before in range(16):
                for after in range(16):
                    msg=ANeuron.judge(before,after,t)
                    old,new=abs(before-t),abs(after-t)
                    exp='IMPROVED' if new<old else 'WORSENED' if new>old else 'NEUTRAL'
                    self.assertEqual(msg['verdict'],exp)
                    self.assertEqual(msg['emissions'],[21] if new<old else [22] if new>old else [])
    def test_a_does_not_accept_precomputed_verdict(self):
        with self.assertRaises(TypeError):ANeuron.judge(3,4,8,verdict='IMPROVED')
    def test_a_invalid_sensor(self):
        for case in ((-1,1,6),(3,16,6),(4,5,'6')):
            with self.assertRaises(ValueError):ANeuron.judge(*case)
    def test_b_only_relays_a(self):
        a=ANeuron.judge(4,5,8);b=BRelay.forward(0,a['verdict'],a)
        self.assertEqual(b['verdict'],'IMPROVED');self.assertEqual(b['relay_channel'],31)
        self.assertEqual(b['A_digest'],sha(a))
    def test_b_invalid(self):
        with self.assertRaises(ValueError):BRelay.forward(0,'EXTERNAL_GOAL',{})
    def test_rule_credit_only_worsened(self):
        self.assertEqual(CNeuron.propose(12,8,HEAT,'WORSENED'),8)
        self.assertEqual(CNeuron.propose(3,8,COOL,'WORSENED'),9)
        for verdict in ('IMPROVED','NEUTRAL'):
            self.assertEqual(CNeuron.propose(12,8,HEAT,verdict),12)
    def test_rule_invalid(self):
        with self.assertRaises(ValueError):CNeuron.propose(12,8,HEAT,'ANSWER_12')
    def test_cannot_supply_goal_or_verdict_to_trial(self):
        e=self.new()
        try:
            with self.assertRaises(TypeError):e.trial(8,goal=10)
            with self.assertRaises(TypeError):e.trial(8,verdict='WORSENED')
        finally:e.close()
    def test_learning_credit(self):
        e=self.new()
        try:
            r=e.trial(8,learning=True)
            self.assertEqual(r['verdict'],'WORSENED')
            self.assertEqual(r['credit'],1)
            self.assertEqual(e.state(),{'theta':8,'version':1,'commit_count':1})
            self.assertEqual(e.audit()['credits'],1)
        finally:e.close()
    def test_later_correct_decision(self):
        e=self.new()
        try:
            e.trial(8)
            r=e.trial(8)
            self.assertEqual(r['choice'],COOL)
            self.assertTrue(r['improved'])
            self.assertEqual(r['credit'],0)
        finally:e.close()
    def test_no_learning_evaluation(self):
        e=self.new()
        try:
            e.trial(8,learning=False)
            self.assertEqual(e.state()['version'],0)
            self.assertEqual(e.audit()['credits'],0)
        finally:e.close()
    def test_missing_feedback_rejects(self):
        e=self.new()
        try:
            r=e.trial(8,feedback='missing')
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.state()['version'],0)
        finally:e.close()
    def test_wrong_lineage_rejects(self):
        e=self.new()
        try:
            r=e.trial(8,feedback='wrong_lineage')
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.audit()['credits'],0)
        finally:e.close()
    def test_corrupted_B_message_is_really_different(self):
        e=self.new()
        try:
            r=e.trial(8,feedback='altered')
            recorded=json.loads(e.db.execute("SELECT payload_json FROM event WHERE kind='B_PE_RELAY'").fetchone()[0])
            self.assertNotEqual(recorded['verdict'],r['verdict'])
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.audit()['credits'],0)
        finally:e.close()
    def test_relay_lineage_mismatch_is_really_injected(self):
        e=self.new()
        try:
            r=e.trial(8,feedback='wrong_lineage')
            recorded=json.loads(e.db.execute("SELECT payload_json FROM event WHERE kind='B_PE_RELAY'").fetchone()[0])
            self.assertNotEqual(recorded['episode'],r['episode'])
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.audit()['credits'],0)
        finally:e.close()
    def test_altered_feedback_rejects(self):
        e=self.new()
        try:
            r=e.trial(8,feedback='altered')
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.audit()['credits'],0)
        finally:e.close()
    def test_recovery_exactly_once(self):
        e=self.new()
        try:
            e.trial(8);before=e.audit();e.reopen();after=e.audit()
            self.assertEqual(before,after)
            r=e.trial(8)
            self.assertEqual(r['credit'],0)
            self.assertEqual(e.state()['version'],1)
        finally:e.close()
    def test_wrong_target_reopen_rejected(self):
        e=self.new();e.close()
        with self.assertRaises(ValueError):LearningCell(self.path,setpoint=7,create=False)
    def test_reinitialization_rejected(self):
        e=self.new()
        try:
            with self.assertRaises(ValueError):LearningCell(self.path,setpoint=6)
        finally:e.close()
    def test_bad_feedback_mode(self):
        e=self.new()
        try:
            with self.assertRaises(ValueError):e.trial(8,feedback='invented_goal')
        finally:e.close()
    def test_bad_learn_mode(self):
        e=self.new()
        try:
            with self.assertRaises(ValueError):e.trial(8,learning=1)
        finally:e.close()
    def test_credit_lineage(self):
        e=self.new()
        try:
            r=e.trial(8);credit=e.db.execute('SELECT * FROM p_credit').fetchone()
            self.assertEqual(credit['source_digest'],r['A_event_digest'])
            kinds=[x[0] for x in e.db.execute('SELECT kind FROM event ORDER BY id')]
            self.assertEqual(kinds,['C_PE_DECISION','WORLD_TRANSITION','A_PE_ASSESSMENT','B_PE_RELAY','C_P_CREDIT'])
        finally:e.close()
    def test_direct_p_tamper_detected(self):
        e=self.new()
        try:
            e.trial(8)
            e.db.execute('UPDATE p SET theta=11 WHERE singleton=1')
            with self.assertRaisesRegex(ValueError,'P_THETA_RECONSTRUCTION_FAILURE'):e.audit()
        finally:e.close()
    def test_p_version_tamper_detected(self):
        e=self.new()
        try:
            e.trial(8)
            e.db.execute('UPDATE p SET version=9 WHERE singleton=1')
            with self.assertRaisesRegex(ValueError,'P_VERSION_COUNT_DRIFT'):e.audit()
        finally:e.close()
    def test_event_payload_tamper_detected(self):
        e=self.new()
        try:
            e.trial(8)
            e.db.execute("UPDATE event SET payload_json='{}' WHERE kind='A_PE_ASSESSMENT'")
            with self.assertRaisesRegex(ValueError,'EVENT_DIGEST_TAMPER'):e.audit()
        finally:e.close()
    def test_episode_outcome_tamper_detected(self):
        e=self.new()
        try:
            e.trial(8)
            e.db.execute("UPDATE episode SET choice=12 WHERE id=0")
            with self.assertRaisesRegex(ValueError,'C_DECISION_RECONSTRUCTION_FAILURE'):e.audit()
        finally:e.close()
    def test_credit_tamper_detected(self):
        e=self.new()
        try:
            e.trial(8)
            e.db.execute('UPDATE p_credit SET new_theta=3')
            with self.assertRaisesRegex(ValueError,'CREDIT_THETA_DRIFT'):e.audit()
        finally:e.close()
    def test_atomic_denial_no_partial_event(self):
        e=self.new()
        try:
            initial=e.audit()
            with patch('research.spk_v5_t15_macro_causal_learning.causal_cell_v1.BRelay.forward',
                       side_effect=ValueError('B_FAULT')):
                with self.assertRaisesRegex(ValueError,'B_FAULT'):e.trial(8)
            self.assertEqual(e.audit(),initial)
        finally:e.close()
    def test_explicit_third_party_source_modification_not_proven(self):
        e=self.new()
        try:
            self.assertEqual(dict(e.db.execute('SELECT key,value FROM config'))['frozen_SPK_P_learning'],'FALSE')
        finally:e.close()

class ProspectiveTests(unittest.TestCase):
    def test_disjoint_prespecified_raw_temps(self):
        self.assertFalse(set(TRAIN_TEMPS)&set(TEST_TEMPS))
        self.assertEqual(len(EQUILIBRIA),10)
        self.assertEqual(len(SEEDS),3)
    def test_one_cell_heldout_is_blind(self):
        with tempfile.TemporaryDirectory() as td:
            result=one_cell(td,6,17,'adaptive')
        self.assertFalse(set(result['train_temps'])&set(result['eval_temps']))
        self.assertTrue(result['heldout_P_frozen'])
        self.assertNotIn(6,result['train_temps'])
    def test_fixed_baseline_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            r=one_cell(td,5,29,'frozen')
        self.assertEqual(r['credits'],0)
        self.assertEqual(r['P_version'],0)
    def test_missing_observation_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            r=one_cell(td,5,29,'no_feedback')
        self.assertEqual(r['credits'],0)
    def test_wrong_lineage_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            r=one_cell(td,5,29,'wrong_lineage')
        self.assertEqual(r['credits'],0)
    def test_altered_observation_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            r=one_cell(td,5,29,'altered')
        self.assertEqual(r['credits'],0)
    def test_unrecognized_condition_denied(self):
        with tempfile.TemporaryDirectory() as td,self.assertRaises(ValueError):one_cell(td,5,29,'oracle')
    def test_scientific_report_explicit_limited_conclusion(self):
        r=experiment()
        self.assertEqual(r['status'],'RESTRICTED_CAUSAL_LEARNING_SUPPORTED')
        self.assertFalse(r['original_frozen_sPK_P_learning'])
        self.assertFalse(r['promotion_allowed'])
        self.assertEqual(r['totals']['adaptive']['heldout_cases'],225)
        self.assertEqual(r['totals']['frozen']['heldout_cases'],225)
        self.assertEqual(r['totals']['frozen']['heldout_improved'],165)
        self.assertEqual(r['totals']['adaptive']['heldout_improved'],213)
        self.assertTrue(r['negative_controls_fail_closed'])
        self.assertTrue(r['evaluation_has_no_P_writes'])
        self.assertTrue(r['hypothesis_support_on_restricted_world'])
    def test_new_worlds_expose_model_limits(self):
        r=experiment()
        # Single-parameter learner fails to identify every boundary perfectly;
        # do not report general solving of thermal control.
        self.assertLess(r['totals']['adaptive']['heldout_improved'],225)
        self.assertTrue(any(x['delta']==0 for x in r['gain_by_world']))
        self.assertEqual(len(r['gain_by_world']),10)
    def test_reversed_dynamics_exposes_model_dependence(self):
        r=experiment()
        flipped=r['reversed_actuator_counterfactual']
        self.assertEqual(flipped['adaptive']['cases'],75)
        self.assertEqual(flipped['adaptive']['hits'],30)
        self.assertLess(flipped['adaptive']['hits']/75,
                        r['totals']['adaptive']['heldout_accuracy'])
    def test_deterministic_report_across_runs(self):
        self.assertEqual(sha(experiment()),sha(experiment()))

if __name__=='__main__':unittest.main()
