"""V5-T2d adversarial sensor/world segregation on frozen A1b SPK execution."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import (
    arm_plan, generate_corpus, verify_closed_receipt,
)
from spk_v5_research.island_sensor_robustness_v5t2d import (
    FAULTS, SCHEMA, ObservationSplit, SensorFault, audit_observation,
    audit_truth_risk, corrupt_observation, one_episode_feedback, run_t2d,
)
from spk_v5_research.island_endogenous_demand_v5t2c import learn_single_arm

ROOT=Path(__file__).resolve().parents[1]


class TestV5T2dSensorResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world=generate_corpus(blocks=2,seed=37217,regime='aligned',train=True)
        cls.report=run_t2d()

    def test_01_admitted_faults_and_immutable_config(self):
        self.assertEqual(tuple(x.name for x in FAULTS),(
            'clean','flip_10pct','flip_35pct','fully_inverted',
            'missing_at_random_30pct','selective_missing_true_90pct','all_missing'))
        with self.assertRaises(AttributeError): FAULTS[0].flip_probability=.5

    def test_02_fault_config_bounds_bool_and_nonfinite_rejected(self):
        for vals in ((True,0.,0.),(-.1,0.,0.),(1.01,0.,0.),
                     (float('nan'),0.,0.),(0.,float('inf'),0.),(0.,0.,'x')):
            with self.assertRaises(ValueError): SensorFault('bad',*vals)

    def test_03_world_and_sensor_separate_ledger(self):
        split=corrupt_observation(self.world,FAULTS[0],seed=12)
        self.assertIsInstance(split,ObservationSplit)
        self.assertEqual(len(split.sensor),len(split.world_truth))
        self.assertEqual(tuple((r.episode.identity,r.demand) for r in split.sensor),split.world_truth)

    def test_04_deterministic_pre_action_faults(self):
        a=corrupt_observation(self.world,FAULTS[1],seed=33)
        self.assertEqual(a,corrupt_observation(self.world,FAULTS[1],seed=33))
        self.assertNotEqual(a.sensor,corrupt_observation(self.world,FAULTS[1],seed=34).sensor)

    def test_05_fault_generator_rejects_ambiguous_episode_ids(self):
        with self.assertRaises(ValueError):
            corrupt_observation((self.world[0],self.world[0]),FAULTS[0],seed=4)

    def test_06_fault_generator_rejects_unknown_truth_and_untyped_seed(self):
        for dataset,seed in (((replace(self.world[0],demand=None),),4),
                             ((self.world[0],),True)):
            with self.assertRaises(ValueError): corrupt_observation(dataset,FAULTS[0],seed=seed)

    def test_07_full_inversion_all_observations_mismatched(self):
        a=corrupt_observation(self.world,FAULTS[3],seed=11)
        audit=audit_observation(a)
        self.assertEqual(audit['wrong_sensor_bit'],len(self.world))
        self.assertEqual(audit['unknown'],0)

    def test_08_full_dropout_unknown_not_negative(self):
        a=corrupt_observation(self.world,FAULTS[-1],seed=11)
        self.assertTrue(all(r.demand is None for r in a.sensor))
        for c in CANDIDATES:
            r=one_episode_feedback(a.sensor[0],c)
            self.assertEqual((r.verdict,r.local_reward),('abstain',None))

    def test_09_sensor_census_conserves(self):
        for f in FAULTS:
            x=corrupt_observation(self.world,f,seed=24)
            a=audit_observation(x)
            self.assertEqual(a['observed']+a['unknown'],len(self.world))
            self.assertEqual(a['world_true']+a['world_false'],len(self.world))
            self.assertEqual(a['observed_true']+a['observed_false'],a['observed'])

    def test_10_world_truth_digest_mutation_rejected(self):
        a=corrupt_observation(self.world,FAULTS[0],seed=24)
        tamper=((a.world_truth[0][0],not a.world_truth[0][1]),)+a.world_truth[1:]
        with self.assertRaises(ValueError):audit_observation(replace(a,world_truth=tamper))

    def test_11_world_episode_id_reorder_rejected_even_resigned(self):
        a=corrupt_observation(self.world,FAULTS[0],seed=24)
        swapped=(a.world_truth[1],a.world_truth[0])+a.world_truth[2:]
        with self.assertRaises(ValueError):
            audit_observation(replace(a,world_truth=swapped,world_sha256=digest(swapped)))

    def test_12_input_mutation_rejected_even_if_truth_digest_unchanged(self):
        a=corrupt_observation(self.world,FAULTS[0],seed=24)
        ep=replace(a.sensor[0].episode,inputs=((3,1),(4,2)))
        with self.assertRaises(ValueError):
            audit_observation(replace(a,sensor=(replace(a.sensor[0],episode=ep),)+a.sensor[1:]))

    def test_13_sensor_untyped_boolean_refused(self):
        a=corrupt_observation(self.world,FAULTS[0],seed=24)
        with self.assertRaises(ValueError):
            audit_observation(replace(a,sensor=(replace(a.sensor[0],demand=1),)+a.sensor[1:]))

    def test_14_sensor_forward_and_closure_still_real_A1b(self):
        x=corrupt_observation(self.world,FAULTS[0],seed=24).sensor[0]
        for c in CANDIDATES:
            receipt=one_episode_feedback(x,c)
            verify_closed_receipt(x,c,receipt)
            self.assertEqual(receipt.closure_tick,x.episode.inputs[0][0]+6)
            self.assertEqual(receipt.c_sensor_tick,x.episode.inputs[0][0]+5)

    def test_15_wrong_sensor_value_can_reward_world_wrong_action(self):
        x=next(r for r in self.world if r.demand is True)
        corrupted=replace(x,demand=False)
        r=one_episode_feedback(corrupted,'silent')
        self.assertEqual((r.verdict,r.local_reward),('positive',1))
        self.assertEqual(audit_truth_risk((x,),'silent')['error'],1)

    def test_16_no_observed_sensor_cannot_certify_negative_silence(self):
        x=next(r for r in self.world if r.demand is True)
        r=one_episode_feedback(replace(x,demand=None),'silent')
        self.assertEqual((r.c_demand,r.verdict,r.local_reward),(None,'abstain',None))
        with self.assertRaises(ValueError):
            verify_closed_receipt(replace(x,demand=None),'silent',replace(r,local_reward=-1,verdict='negative'))

    def test_17_closed_receipt_rejects_forged_actor_and_timestamp(self):
        x=self.world[0]
        r=one_episode_feedback(x,'overemit')
        for bad in (replace(r,candidate='temporal'),replace(r,closure_tick=r.closure_tick+1),
                    replace(r,episode_id='invented')):
            with self.assertRaises(ValueError):verify_closed_receipt(x,'overemit',bad)

    def test_18_missing_closure_rejected_before_any_reward(self):
        x=self.world[0]
        from spk_v5_research import island_endogenous_demand_v5t2c as original
        case=original.make_case(x,'silent')
        bad=replace(case,events=tuple(e for e in case.events if e.channel!=6))
        with patch.object(original,'make_case',return_value=bad):
            with self.assertRaises(AssertionError):one_episode_feedback(x,'silent')

    def test_19_learner_not_allowed_audit_truth_or_task_label(self):
        x=corrupt_observation(self.world,FAULTS[1],seed=11)
        p=arm_plan(x.sensor,seed=4482)
        with patch('spk_v5_research.island_sensor_robustness_v5t2d.audit_truth_risk',side_effect=AssertionError('audit leaked')):
            with patch('spk_v5_research.island_objective_v5t1.task_label',side_effect=AssertionError('task leaked')):
                r=learn_single_arm(x.sensor,p)
        self.assertEqual(sum(r['chosen_actions'].values()),len(self.world))
        self.assertEqual(r['policy_changes_native'],0)

    def test_20_single_arm_only_and_no_unevaluated_counterfactuals(self):
        x=corrupt_observation(self.world,FAULTS[0],seed=11)
        p=arm_plan(x.sensor,seed=4482)
        r=learn_single_arm(x.sensor,p)
        self.assertEqual(sum(r['chosen_actions'].values()),len(self.world))
        self.assertEqual(set(r),{'choice','reward_sums','observed_rewards','abstentions',
                                  'forward_spike_counts','chosen_actions','policy_changes_native'})

    def test_21_report_source_engine_and_research_boundary(self):
        r=self.report
        self.assertEqual(r['schema'],SCHEMA)
        self.assertFalse(r['native_learning'])
        self.assertFalse(r['native_reverse_bv_delivery'])
        self.assertIn('NO_INDEPENDENT_TRUTH',r['status'])
        self.assertEqual(r['research_candidate_program_adoptions'],0)
        self.assertEqual(r['train_episode_count'],504)

    def test_22_clean_information_supports_temporal(self):
        r=self.report['scenarios']['clean']
        self.assertEqual((r['learner']['choice'],r['aligned_truth_error']),('temporal',10))
        self.assertEqual(r['sensor_census']['wrong_sensor_bit'],0)

    def test_23_moderate_sensor_bit_error_disclosed_not_claimed_universal(self):
        r=self.report['scenarios']
        self.assertEqual(r['flip_10pct']['sensor_census']['wrong_sensor_bit'],56)
        self.assertEqual(r['flip_35pct']['sensor_census']['wrong_sensor_bit'],186)
        self.assertEqual(r['flip_10pct']['learner']['choice'],'temporal')
        self.assertEqual(r['flip_35pct']['learner']['choice'],'temporal')

    def test_24_inverted_sensor_worsens_actual_island_task(self):
        r=self.report['scenarios']
        self.assertEqual(r['fully_inverted']['learner']['choice'],'overemit')
        self.assertGreater(r['fully_inverted']['aligned_truth_error'],r['clean']['aligned_truth_error'])
        self.assertEqual(r['fully_inverted']['sensor_census']['wrong_sensor_bit'],504)

    def test_25_missing_at_random_abstentions_never_punishment(self):
        r=self.report['scenarios']['missing_at_random_30pct']
        self.assertEqual(r['sensor_census']['unknown'],158)
        self.assertEqual(sum(r['learner']['abstentions'].values()),158)
        self.assertEqual(r['learner']['choice'],'temporal')

    def test_26_selective_missing_changes_choice_without_any_wrong_bit(self):
        r=self.report['scenarios']['selective_missing_true_90pct']
        self.assertEqual(r['sensor_census']['wrong_sensor_bit'],0)
        self.assertEqual((r['learner']['choice'],r['aligned_truth_error']),('silent',18))
        self.assertGreater(r['sensor_census']['unknown_world_true'],r['sensor_census']['unknown_world_false'])

    def test_27_all_missing_preserves_baseline_and_unknowns(self):
        r=self.report['scenarios']['all_missing']
        self.assertEqual(r['learner']['choice'],'overemit')
        self.assertEqual(sum(r['learner']['observed_rewards'].values()),0)
        self.assertEqual(sum(r['learner']['abstentions'].values()),504)

    def test_28_placebo_preserves_marginals_and_does_not_pretend_significance(self):
        for r in self.report['scenarios'].values():
            self.assertEqual(sum(r['placebo_choices'].values()),16)
        self.assertEqual(self.report['scenarios']['clean']['placebo_choices'],{'silent':16})
        self.assertEqual(self.report['scenarios']['all_missing']['placebo_choices'],{'overemit':16})

    def test_29_distribution_shift_reverses_relative_utility(self):
        tr=self.report['truth_audit_aligned']
        shift=self.report['truth_audit_inverted_shift']
        self.assertEqual((tr['temporal']['error'],shift['temporal']['error']),(10,61))
        self.assertEqual((tr['overemit']['error'],shift['overemit']['error']),(44,25))
        self.assertTrue(self.report['scenarios']['clean']['inverted_shift_truth_error']>25)

    def test_30_report_is_deterministic_and_complete(self):
        self.assertEqual(self.report,run_t2d())
        self.assertEqual(set(self.report['scenarios']),set(f.name for f in FAULTS))

    def test_31_input_action_schedule_pinned_across_scenarios(self):
        p=arm_plan(self.world,seed=4482)
        self.assertEqual(sum(Counter(p).values()),len(self.world))
        self.assertEqual(self.report['action_schedule_sha256'],digest(arm_plan(
            generate_corpus(blocks=24,seed=37217,regime='aligned',train=True),seed=4482)))

    def test_32_no_new_native_BV_or_learning_authority(self):
        self.assertTrue(any('no native reverse BV' in x for x in self.report['limits']))
        self.assertTrue(any('no physical sensors' in x for x in self.report['limits']))
        self.assertEqual(self.report['research_candidate_program_adoptions'],0)

    def test_33_cli_create_only_and_reference(self):
        script=ROOT/'search/spk_v5_t2d_sensor_robustness.py'
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'report.json'
            p=subprocess.run([sys.executable,str(script),str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            ref=(ROOT/'docs/spk-v5-t2d-reference.json').read_bytes()
            self.assertEqual(output.read_bytes(),ref)
            p=subprocess.run([sys.executable,str(script),str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)

    def test_34_cli_in_repo_and_symlink_rejected(self):
        script=ROOT/'search/spk_v5_t2d_sensor_robustness.py'
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            p=subprocess.run([sys.executable,str(script),str(Path(d)/'x.json')],cwd=ROOT,capture_output=True)
            self.assertNotEqual(p.returncode,0)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'link.json'
            target.symlink_to(Path(d)/'missing.json')
            p=subprocess.run([sys.executable,str(script),str(target)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(p.returncode,0)

    def test_35_pinned_source_drift_fails_closed(self):
        manifest=json.loads((ROOT/'docs/spk-v5-t2d-manifest.json').read_text())
        for rel,expected in manifest['pins_sha256'].items():
            f=ROOT/rel
            self.assertTrue(f.is_file() and not f.is_symlink(),rel)
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),expected,rel)


if __name__=='__main__':unittest.main()
