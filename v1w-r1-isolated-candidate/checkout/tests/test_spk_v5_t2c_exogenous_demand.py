"""V5-T2c: source engine, real closure/negative-vs-unknown, shadow bandit controls."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spk_v5_research.island_objective_v5t1 import CANDIDATES
from spk_v5_research.island_endogenous_demand_v5t2c import (
    C_PROGRAM, ClosedReceipt, DemandEpisode, REGIMES, TEMPLATES,
    arm_plan, evaluate_candidate, generate_corpus, learn_single_arm,
    make_case, observe_closed_episode, run_t2c, verify_closed_receipt,
)

ROOT = Path(__file__).resolve().parents[1]


def row(demand, index=0):
    corpus = generate_corpus(blocks=1,seed=37,regime='aligned',train=False)
    return replace(corpus[index],demand=demand)


class TestV5T2c(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=run_t2c()

    def test_01_three_source_engine_neurons_unmodified_two_edges(self):
        case=make_case(row(True),'temporal')
        self.assertEqual([n.node_id for n in case.nodes],list('ABC'))
        self.assertEqual([(e.source_node,e.target_node,e.delay_ticks) for e in case.edges],
                         [('A','B',1),('B','C',1)])
        self.assertEqual(case.nodes[-1].instructions,C_PROGRAM)

    def test_02_exogenous_C_true_false_and_absent_are_typed_pulses(self):
        for value,expected in ((True,[4,6]),(False,[5,6]),(None,[6])):
            case=make_case(row(value),'silent')
            self.assertEqual([x.channel for x in case.events if x.node_id=='C'],expected)

    def test_03_C_real_forward_sensing_and_closed_batch(self):
        receipt=observe_closed_episode(row(True),'temporal')
        self.assertEqual((receipt.c_forward_ticks,receipt.c_sensor_tick,receipt.closure_tick),
                         ((3,),5,6))
        self.assertEqual((receipt.c_demand,receipt.verdict,receipt.local_reward),(True,'positive',1))
        verify_closed_receipt(row(True),'temporal',receipt)

    def test_04_C_demand_true_and_silent_negative_after_real_closure(self):
        receipt=observe_closed_episode(row(True),'silent')
        self.assertEqual(receipt.c_forward_ticks,())
        self.assertEqual((receipt.verdict,receipt.local_reward),('negative',-1))

    def test_05_C_no_demand_and_silent_positive_after_real_closure(self):
        receipt=observe_closed_episode(row(False),'silent')
        self.assertEqual(receipt.c_forward_ticks,())
        self.assertEqual((receipt.verdict,receipt.local_reward),('positive',1))

    def test_06_C_no_demand_and_wrong_emission_negative(self):
        receipt=observe_closed_episode(row(False),'overemit')
        self.assertEqual((receipt.c_forward_ticks,receipt.verdict,receipt.local_reward),
                         ((3,),'negative',-1))

    def test_07_unknown_sensor_abstains_even_after_explicit_closure(self):
        for candidate in CANDIDATES:
            receipt=observe_closed_episode(row(None),candidate)
            self.assertEqual((receipt.verdict,receipt.local_reward,receipt.c_demand),
                             ('abstain',None,None))
            self.assertEqual(receipt.closure_tick,6)

    def test_08_sensor_is_not_task_label_or_derived_from_candidate(self):
        with patch('spk_v5_research.island_objective_v5t1.task_label',side_effect=AssertionError('oracle leak')):
            for candidate in CANDIDATES:
                self.assertEqual(observe_closed_episode(row(False),candidate).c_demand,False)
                self.assertEqual(observe_closed_episode(row(True),candidate).c_demand,True)

    def test_09_same_context_independently_supports_opposite_truth_worlds(self):
        yes,no=row(True),row(False)
        for candidate in CANDIDATES:
            a,b=observe_closed_episode(yes,candidate),observe_closed_episode(no,candidate)
            self.assertEqual(a.c_forward_ticks,b.c_forward_ticks)
            self.assertNotEqual(a.local_reward,b.local_reward)

    def test_10_CAUSAL_two_hop_replies_placement_invariant(self):
        for c in CANDIDATES:
            for mode in (True,False,None):
                observations=[observe_closed_episode(row(mode),c,scheme=scheme)
                              for scheme in ('single','split','spread')]
                self.assertEqual(observations,observations[:1]*3)

    def test_11_exact_closed_receipt_rejects_forged_positive(self):
        x=observe_closed_episode(row(False),'overemit')
        with self.assertRaises(ValueError):
            verify_closed_receipt(row(False),'overemit',replace(x,verdict='positive',local_reward=1))

    def test_12_receipt_rejects_wrong_action_or_wrong_episode(self):
        x=observe_closed_episode(row(True),'overemit')
        for y in (replace(x,candidate='temporal'),replace(x,episode_id='other')):
            with self.assertRaises(ValueError):verify_closed_receipt(row(True),'overemit',y)

    def test_13_receipt_rejects_future_early_or_repeated_C(self):
        x=observe_closed_episode(row(True),'overemit')
        for y in (replace(x,closure_tick=5),replace(x,c_forward_ticks=(4,)),
                  replace(x,c_forward_ticks=x.c_forward_ticks*2)):
            with self.assertRaises(ValueError):verify_closed_receipt(row(True),'overemit',y)

    def test_14_receipt_rejects_fake_sign_on_missing_sensor(self):
        x=observe_closed_episode(row(None),'silent')
        with self.assertRaises(ValueError):
            verify_closed_receipt(row(None),'silent',replace(x,verdict='negative',local_reward=-1))

    def test_15_episode_generation_is_pinned_repeatable_and_action_independent(self):
        for regime in REGIMES:
            a=generate_corpus(blocks=2,seed=822,regime=regime,train=True)
            b=generate_corpus(blocks=2,seed=822,regime=regime,train=True)
            self.assertEqual(a,b)
            self.assertEqual(len(a),42)
            self.assertTrue(all(x.template_id in range(len(TEMPLATES)) for x in a))

    def test_16_world_demand_correlation_aligned_inverted_not_blind(self):
        r=self.report['regimes']
        self.assertGreater(r['inverted']['train_exogenous_demand_present'],
                           r['aligned']['train_exogenous_demand_present'])
        self.assertTrue(self.report['world_construction'].startswith('Exogenous'))
        self.assertIn('Synthetic world',self.report['limitations'][0])

    def test_17_balanced_action_schedule_each_template_all_three_arms(self):
        corpus=generate_corpus(blocks=3,seed=822,regime='aligned',train=True)
        plan=arm_plan(corpus,seed=44)
        for i in range(0,len(plan),3):
            self.assertEqual(set(plan[i:i+3]),set(CANDIDATES))
            self.assertEqual(len(set(x.template_id for x in corpus[i:i+3])),1)

    def test_18_one_action_observed_per_training_episode(self):
        r=self.report['regimes']['aligned']['learner']
        self.assertEqual(sum(r['chosen_actions'].values()),504)
        self.assertEqual(sum(r['observed_rewards'].values()),504)
        self.assertEqual(r['chosen_actions'],{x:168 for x in CANDIDATES})
        self.assertEqual(r['policy_changes_native'],0)

    def test_19_unavailable_sensor_cannot_coerce_updates(self):
        r=self.report['regimes']['absent']['learner']
        self.assertEqual(r['choice'],'overemit')
        self.assertEqual(sum(r['observed_rewards'].values()),0)
        self.assertEqual(sum(r['abstentions'].values()),504)
        self.assertEqual(sum(r['reward_sums'].values()),0)

    def test_20_aligned_bandit_chooses_temporal_and_errors_below_baselines(self):
        r=self.report['regimes']['aligned']
        self.assertEqual(r['learner']['choice'],'temporal')
        self.assertEqual(r['evaluation']['temporal']['error'],10)
        self.assertLess(r['selected_evaluation']['error'],r['evaluation']['silent']['error'])
        self.assertLess(r['selected_evaluation']['error'],r['evaluation']['overemit']['error'])

    def test_21_inverted_context_reward_chooses_permissive(self):
        r=self.report['regimes']['inverted']
        self.assertEqual(r['learner']['choice'],'overemit')
        self.assertLess(r['evaluation']['overemit']['error'],r['evaluation']['temporal']['error'])

    def test_22_placebo_is_stochastic_not_always_correct(self):
        r=self.report['regimes']['aligned']
        self.assertEqual(sum(r['matched_demand_shuffle_placebo_choices'].values()),32)
        self.assertEqual(r['matched_demand_shuffle_placebo_choices'],{'silent':30,'temporal':2})
        self.assertEqual(r['matched_demand_shuffle_placebo_losses'],{'10':2,'18':30})

    def test_23_no_label_access_in_arm_learning(self):
        corpus=generate_corpus(blocks=2,seed=11,regime='aligned',train=True)
        p=arm_plan(corpus,seed=11)
        with patch('spk_v5_research.island_objective_v5t1.task_label',side_effect=AssertionError('label leak')):
            r=learn_single_arm(corpus,p)
        self.assertEqual(sum(r['chosen_actions'].values()),42)

    def test_24_degraded_records_cannot_produce_negative_credit_for_missing(self):
        corpus=generate_corpus(blocks=1,seed=11,regime='absent',train=True)
        p=arm_plan(corpus,seed=11)
        r=learn_single_arm(corpus,p)
        self.assertEqual(r['choice'],'overemit')
        self.assertEqual(sum(r['abstentions'].values()),21)

    def test_25_no_claims_of_native_BV_learning_or_independence(self):
        r=self.report
        self.assertFalse(r['native_learning'])
        self.assertFalse(r['runtime_reverse_BV_delivery'])
        self.assertIn('BLIND_BLOCKED',r['status'])
        self.assertIn('A1b',r['native_engine'])
        self.assertIn('seeds are public', ' '.join(r['limitations']))

    def test_26_invalid_world_candidate_and_arm_input_fail_closed(self):
        for kw in ({'blocks':0,'seed':1,'regime':'aligned','train':True},
                   {'blocks':1,'seed':True,'regime':'aligned','train':True},
                   {'blocks':1,'seed':1,'regime':'faked','train':True}):
            with self.assertRaises(ValueError):generate_corpus(**kw)
        with self.assertRaises(ValueError):make_case(row(True),'oracle')
        with self.assertRaises(ValueError):arm_plan((row(True),),seed=1)
        with self.assertRaises(ValueError):learn_single_arm((row(True),),('oracle',))
        with self.assertRaises(ValueError):evaluate_candidate((row(True),),'oracle')

    def test_27_canonical_report_deterministic(self):
        self.assertEqual(run_t2c(),self.report)

    def test_28_C_demand_evidence_bounded_does_not_overwrite_A_B_replay(self):
        for c in CANDIDATES:
            ys=[observe_closed_episode(row(d),c) for d in (True,False,None)]
            self.assertEqual(len({x.c_forward_ticks for x in ys}),1)

    def test_29_C_silent_positive_depends_on_observed_negative_demand(self):
        x=observe_closed_episode(row(False),'silent')
        y=observe_closed_episode(row(None),'silent')
        self.assertEqual(x.verdict,'positive')
        self.assertEqual(y.verdict,'abstain')

    def test_30_create_only_cli_and_no_overwrite(self):
        script=ROOT/'search/spk_v5_t2c_exogenous_demand.py'
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'report.json'
            result=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(target.read_text()),self.report)
            again=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(again.returncode,0)

    def test_31_cli_repository_path_and_symlink_fail_closed(self):
        script=ROOT/'search/spk_v5_t2c_exogenous_demand.py'
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            target=Path(d)/'output.json'
            res=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(res.returncode,0)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'symlink.json'
            target.symlink_to(Path(d)/'nonexistent')
            res=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(res.returncode,0)


if __name__ == '__main__':unittest.main()
