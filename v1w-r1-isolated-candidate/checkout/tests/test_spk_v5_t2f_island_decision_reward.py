"""V5-T2f adversarial research gate; source-engine executions, no native edits."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace

from spk_v5_research.island_endogenous_demand_v5t2c import generate_corpus
from spk_v5_research.island_decision_reward_v5t2f import (
    SCHEMA, STAGES, ChargePlan, AdmissionError, EpisodeLedger, DecisionWitness,
    witnessed_decision, verify_witness, paid_control, verify_paid_control, run_t2f,
)
from spk_v5_research.island_objective_v5t1 import digest


class TestV5T2f(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = generate_corpus(blocks=1,seed=37217,regime='aligned',train=False)
        cls.r = cls.source[0]
        cls.silent = replace(cls.r,demand=True)
        cls.no = replace(cls.r,demand=False)
        cls.unknown = replace(cls.r,demand=None)
        cls.report = run_t2f()

    def test_01_schema_and_determinism(self):
        self.assertEqual(self.report['schema'],SCHEMA)
        self.assertEqual(digest(self.report),digest(run_t2f()))

    def test_02_research_boundary_is_explicit(self):
        for claim in ('forward_decision_control_is_native','reverse_semantic_feedback_is_native',
                      'costs_are_source_v0e_grants','task_truth_is_independent'):
            self.assertFalse(self.report[claim])
        self.assertEqual(self.report['native_learner_updates'],0)

    def test_03_sensor_future_not_in_action_commit(self):
        tokens = [witnessed_decision(replace(self.r,demand=d),'temporal')[0].token
                  for d in (True,False,None)]
        self.assertEqual(len(set(tokens)),1)

    def test_04_silent_witness_exists_without_spike(self):
        w,receipt=witnessed_decision(self.silent,'silent')
        self.assertFalse(w.has_A_spike)
        self.assertEqual(w.observed_C_forward_ticks,())
        self.assertEqual(receipt.local_reward,-1)

    def test_05_silent_negative_is_delivered_not_omission(self):
        p=paid_control(self.silent,'silent')
        self.assertEqual((p['status'],p['reward'],p['A_spike']),('reward_delivered',-1,False))
        self.assertEqual(p['trace'][-1]['stage'],'A_consume')

    def test_06_silent_positive_is_delivered(self):
        p=paid_control(self.no,'silent')
        self.assertEqual((p['status'],p['reward'],p['A_spike']),('reward_delivered',1,False))

    def test_07_no_sensor_abstains_not_negative(self):
        p=paid_control(self.unknown,'silent')
        self.assertEqual((p['status'],p['verdict'],p['reward']),('abstain_delivered','abstain',None))

    def test_08_all_full_charge_really_paid(self):
        for c in ('silent','temporal','overemit'):
            p=paid_control(self.no,c)
            self.assertEqual(p['charged'],{'PE':7,'memory':12,'link':4})
            self.assertEqual(len(p['trace']),7)

    def test_09_chronological_hops_and_closure(self):
        p=paid_control(self.silent,'silent')
        self.assertEqual([x['stage'] for x in p['trace']],list(STAGES))
        self.assertEqual([x['tick']-self.silent.episode.inputs[0][0] for x in p['trace']], [2,3,4,6,7,8,9])

    def test_10_all_route_limits_enforced(self):
        for kw in ({'pe_units':6},{'memory_units':11},{'link_units':3},
                   {'pe_per_tick':0},{'link_per_tick':0}):
            with self.assertRaises(AdmissionError):paid_control(self.silent,'silent',ChargePlan(**kw))

    def test_11_zero_budgets_explicitly_rejected(self):
        with self.assertRaises(AdmissionError):paid_control(self.r,'overemit',ChargePlan(link_units=0))

    def test_12_bad_type_bool_budget_rejected(self):
        with self.assertRaises(AdmissionError):ChargePlan(pe_units=True)

    def test_13_bad_negative_budget_rejected(self):
        with self.assertRaises(AdmissionError):ChargePlan(memory_units=-1)

    def test_14_unknown_route_loss_stage_rejected(self):
        with self.assertRaises(AdmissionError):ChargePlan(lost_stage='C_observe_close')

    def test_15_forward_loss_no_negative_credit(self):
        p=paid_control(self.silent,'silent',ChargePlan(lost_stage='B_to_C'))
        self.assertEqual((p['status'],p['reward'],p['verdict']),('transport_loss',None,None))
        self.assertIsNone(p['delivered_control'])
        self.assertIsNone(p['C_observed_demand_if_delivered'])
        self.assertEqual(p['charged'],{'PE':3,'memory':5,'link':2})

    def test_16_reverse_loss_no_negative_credit(self):
        p=paid_control(self.silent,'silent',ChargePlan(lost_stage='B_to_A'))
        self.assertEqual((p['status'],p['reward']),('transport_loss',None))
        self.assertEqual(p['charged'],{'PE':6,'memory':11,'link':4})

    def test_17_each_transit_drop_fail_closed(self):
        for lost in ('A_to_B','B_to_C','C_to_B','B_to_A'):
            for choice in ('silent','overemit'):
                p=paid_control(self.silent,choice,ChargePlan(lost_stage=lost))
                self.assertIsNone(p['reward'])
                self.assertEqual(p['status'],'transport_loss')

    def test_18_loss_still_charges_attempted_hop(self):
        p=paid_control(self.silent,'silent',ChargePlan(lost_stage='A_to_B'))
        self.assertEqual(p['charged'],{'PE':2,'memory':3,'link':1})
        self.assertEqual(p['trace'][-1]['delivered'],False)

    def test_19_replay_original_witness_ok(self):
        w,r=witnessed_decision(self.silent,'silent')
        verify_witness(self.silent,'silent',w,r)

    def test_20_forged_token_rejected(self):
        w,r=witnessed_decision(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_witness(self.silent,'silent',replace(w,token='fake'),r)

    def test_21_forged_actor_id_rejected(self):
        w,r=witnessed_decision(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_witness(self.silent,'silent',replace(w,episode_id='other'),r)

    def test_22_forged_future_tick_rejected(self):
        w,r=witnessed_decision(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_witness(self.silent,'silent',replace(w,decision_tick=w.c_closure_tick+1),r)

    def test_23_forged_closure_sensor_rejected(self):
        w,r=witnessed_decision(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_witness(self.silent,'silent',w,replace(r,c_demand=False))

    def test_24_forged_reward_rejected_by_reexecution(self):
        r=paid_control(self.silent,'silent')
        r['reward']=1
        with self.assertRaises(AdmissionError):verify_paid_control(self.silent,'silent',ChargePlan(),r)

    def test_25_forged_resource_cost_rejected(self):
        r=paid_control(self.silent,'silent')
        r['charged']['PE']=0
        with self.assertRaises(AdmissionError):verify_paid_control(self.silent,'silent',ChargePlan(),r)

    def test_26_rehashed_transport_not_source_replay(self):
        r=paid_control(self.silent,'silent')
        r['trace'][4]['tick']+=100
        _=digest(r)
        with self.assertRaises(AdmissionError):verify_paid_control(self.silent,'silent',ChargePlan(),r)

    def test_27_wrong_episode_cannot_steal_reward(self):
        r=paid_control(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_paid_control(self.source[1],'silent',ChargePlan(),r)

    def test_28_wrong_arm_cannot_steal_reward(self):
        r=paid_control(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_paid_control(self.silent,'overemit',ChargePlan(),r)

    def test_29_duplicate_episode_rejected_even_if_different_action(self):
        l=EpisodeLedger()
        l.record(self.no,'silent',ChargePlan(),paid_control(self.no,'silent'))
        with self.assertRaises(AdmissionError):l.record(self.no,'temporal',ChargePlan(),paid_control(self.no,'temporal'))

    def test_30_no_duplicate_token(self):
        l=EpisodeLedger(); p=paid_control(self.no,'silent')
        l.record(self.no,'silent',ChargePlan(),p)
        with self.assertRaises(AdmissionError):l.record(self.no,'silent',ChargePlan(),p)

    def test_31_abstention_does_not_change_credit(self):
        l=EpisodeLedger()
        l.record(self.unknown,'silent',ChargePlan(),paid_control(self.unknown,'silent'))
        self.assertEqual(l.rewards_received['silent'],0)
        self.assertEqual(l.abstentions,1)
        self.assertEqual(l.cost['PE'],7)

    def test_32_transport_loss_does_not_change_credit(self):
        l=EpisodeLedger(); q=ChargePlan(lost_stage='C_to_B')
        l.record(self.silent,'silent',q,paid_control(self.silent,'silent',q))
        self.assertEqual(l.rewards_received['silent'],0)
        self.assertEqual(l.transport_losses,1)
        self.assertGreater(l.cost['link'],0)

    def test_33_negative_credit_applied_once(self):
        l=EpisodeLedger()
        l.record(self.silent,'silent',ChargePlan(),paid_control(self.silent,'silent'))
        self.assertEqual((l.reward_sum['silent'],l.rewards_received['silent']),(-1,1))

    def test_34_source_has_no_native_message_on_silence(self):
        w,_=witnessed_decision(self.silent,'silent')
        self.assertEqual(w.origin,'external_shadow_host_not_frozen_A')
        self.assertFalse(w.has_A_spike)

    def test_35_finite_matrix_exact(self):
        a=self.report['per_scenario']
        self.assertEqual(a['paid']['status_counts'],{'reward_delivered':14,'abstain_delivered':7})
        self.assertEqual(a['paid']['silent_rewards'],5)
        self.assertEqual(a['lost_forward']['cost'],{'PE':63,'memory':105,'link':42})
        self.assertEqual(a['lost_reverse']['cost'],{'PE':126,'memory':231,'link':84})

    def test_36_only_one_chosen_action_per_episode(self):
        self.assertEqual(self.report['source_event_count'],63)
        self.assertEqual(self.report['per_scenario']['paid']['episodes'],21)

    def test_37_no_shadow_native_adoption(self):
        self.assertFalse(paid_control(self.r,'silent')['native_learning'])

    def test_38_bad_program_refused(self):
        with self.assertRaises(AdmissionError):paid_control(self.r,'fake')

    def test_39_nonsource_report_rejected(self):
        with self.assertRaises(AdmissionError):verify_paid_control(self.r,'silent',ChargePlan(),{'schema':SCHEMA})

    def test_40_typed_receipt_required(self):
        w,_=witnessed_decision(self.silent,'silent')
        with self.assertRaises(AdmissionError):verify_witness(self.silent,'silent',w,object())

    def test_41_create_only_cli_exact_and_repeat_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'report.json'
            cmd=[sys.executable,'search/spk_v5_t2f_island_decision_reward.py',str(path)]
            p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(path.read_text()),self.report)
            p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(p.returncode,0)

    def test_42_cli_rejects_output_inside_repo(self):
        path=Path.cwd()/'test-v5-t2f-cannot-create.json'
        try:
            p=subprocess.run([sys.executable,'search/spk_v5_t2f_island_decision_reward.py',str(path)],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(path.exists())
        finally:
            if path.exists():path.unlink()

    def test_43_cli_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'report.json'
            path.symlink_to(Path(td)/'uncreated.json')
            p=subprocess.run([sys.executable,'search/spk_v5_t2f_island_decision_reward.py',str(path)],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertTrue(path.is_symlink())

    def test_44_untyped_ledger_report_rejected(self):
        with self.assertRaises(AdmissionError):EpisodeLedger().record(self.silent,'silent',ChargePlan(),None)

if __name__ == '__main__':unittest.main()
