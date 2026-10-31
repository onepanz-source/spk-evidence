"""V5-T2e resource bridge: real source replay, adversarial accounting, no semantic minting."""
import copy
from dataclasses import replace
from unittest import TestCase

from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import observe_closed_episode
from spk_v5_research.island_bv_resource_bridge_v5t2e import (
    MODES, SCHEMA, audit_resource_execution, benchmark_cases, run_t2e,
    source_execution, verify_source_replay,
)

class TestIslandBVResourceBridge(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = benchmark_cases()
        cls.result = run_t2e()
        cls.over = next((r,c) for r,c in cls.samples if c=='overemit' and r.template_id==2 and r.demand is False)
        cls.silent = next((r,c) for r,c in cls.samples if c=='silent' and r.demand is True)

    def test_01_complete_factorial_and_signature(self):
        self.assertEqual(len(self.samples),42)
        self.assertEqual(self.result['schema'],SCHEMA)
        self.assertEqual({c for r,c in self.samples},set(CANDIDATES))
        self.assertEqual({r.demand for r,c in self.samples},{True,False})
        self.assertEqual({r.template_id for r,c in self.samples},set(range(7)))

    def test_02_source_uses_unchanged_BV_v0e_schema(self):
        r,c=self.over
        self.assertEqual(source_execution(r,c,'feedback_first')['schema'],'spk-bv-live-dual-event-scheduler/v0e')

    def test_03_source_disabled_zero_reverse_resource(self):
        a=self.result['modes']['disabled']
        self.assertEqual(a['feedback_grants'],0)
        self.assertEqual(a['abstract_OE_memory_units'],0)
        self.assertEqual(a['total_link_grants'],a['forward_grants'])

    def test_04_source_forward_feedback_charges_are_equal(self):
        for mode in ('forward_first','feedback_first'):
            a=self.result['modes'][mode]
            self.assertEqual(a['feedback_grants'],32)
            self.assertEqual(a['abstract_PE_service_units'],32)
            self.assertEqual(a['abstract_OE_memory_units'],64)
            self.assertEqual(a['total_link_grants'],64)
            self.assertEqual(a['feedback_bearing_cells'],14)

    def test_05_every_episode_closes_exactly_once(self):
        for mode in MODES:
            self.assertEqual(self.result['modes'][mode]['closure_count'],42)

    def test_06_feedback_first_changes_actual_source_C_timing(self):
        self.assertEqual(self.result['changed_terminal_cells_vs_v0e_disabled'],{'feedback_first':2})
        self.assertEqual(self.result['changed_batch_cells_vs_v0e_disabled'],{'feedback_first':2})

    def test_07_feedback_first_and_forward_first_still_same_grant_total(self):
        self.assertEqual(self.result['modes']['forward_first']['feedback_grants'],
                         self.result['modes']['feedback_first']['feedback_grants'])

    def test_08_closure_not_a_reverse_credit_without_ancestry(self):
        r,c=self.silent
        x=source_execution(r,c,'closure_only')
        self.assertEqual(len(x['feedback']['assessments']),1)
        self.assertEqual(x['feedback']['assessments'][0]['input_occurrences'],[])
        self.assertEqual(x['feedback']['link_grants'],[])

    def test_09_closure_assessment_always_zero_reverse(self):
        a=self.result['modes']['closure_only']
        self.assertEqual(a['feedback_grants'],0)
        self.assertEqual(a['feedback_bearing_cells'],0)

    def test_10_no_spike_but_negative_shadow_reward_is_unrouted(self):
        r,c=self.silent
        receipt=observe_closed_episode(r,c)
        self.assertEqual(receipt.verdict,'negative')
        self.assertEqual(receipt.local_reward,-1)
        self.assertEqual(source_execution(r,c,'feedback_first')['resources']['bv_link_grants'],0)
        self.assertFalse(self.result['semantic_reverse_credit_proven'])

    def test_11_positive_echo_is_not_task_reward(self):
        r,c=self.over
        receipt=observe_closed_episode(r,c)
        self.assertEqual(receipt.verdict,'negative')
        self.assertGreater(source_execution(r,c,'feedback_first')['resources']['bv_link_grants'],0)
        self.assertEqual(self.result['charged_semantic_rewards'],0)

    def test_12_shadow_truth_stays_distinct_from_v0e_assessment(self):
        self.assertEqual(len([x for x in self.result['cell_evidence'] if x['A1b_shadow_local_reward']==-1]),
                         len([x for x in self.result['cell_evidence'] if x['A1b_shadow_semantic_verdict']=='negative']))

    def test_13_no_program_adoption_or_native_learning_claim(self):
        self.assertFalse(self.result['native_learning'])
        self.assertFalse(self.result['architecture_modified'])
        self.assertTrue(any('NOT transported' in item for item in self.result['inference_boundary']))

    def test_14_resource_timeline_fabric_limit(self):
        for mode in MODES:
            r,c=self.over
            e=source_execution(r,c,mode)
            audit=audit_resource_execution(r,c,mode,e)
            self.assertLessEqual(audit['max_link_per_tick'],1)

    def test_15_typing_invalid_mode_fails(self):
        r,c=self.over
        for mode in ('magic',None,False):
            with self.assertRaises(ValueError):source_execution(r,c,mode)

    def test_16_unknown_demand_rejected(self):
        r,c=self.over
        with self.assertRaises(ValueError):source_execution(replace(r,demand=None),c,'disabled')

    def test_17_invalid_candidate_rejected(self):
        r,c=self.over
        with self.assertRaises(ValueError):source_execution(r,'invented','feedback_first')

    def test_18_fake_source_feedback_grant_count_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['resources']['bv_link_grants']+=1
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',x)

    def test_19_fake_memory_units_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['resources']['bv_memory_units']-=1
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',x)

    def test_20_fake_PE_service_units_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['resources']['bv_service_units']-=1
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',x)

    def test_21_inconsistent_mode_claim_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'disabled',x)

    def test_22_forward_time_travel_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['forward']['link_grants'][0]['delivered_at']=x['forward']['link_grants'][0]['tick']
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',x)

    def test_23_link_budget_forgery_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['resources']['timeline'][0]['link_total']=999
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',x)

    def test_24_missing_closure_rejected(self):
        r,c=self.over
        x=source_execution(r,c,'disabled')
        x['forward']['terminal']=[v for v in x['forward']['terminal'] if v['channel']!=9]
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'disabled',x)

    def test_25_forged_causal_assessment_denied_by_independent_replay(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['feedback']['assessments'][0]['tick']+=1
        with self.assertRaises(ValueError):verify_source_replay(r,c,'feedback_first',x)

    def test_26_mutated_forward_program_claim_denied_by_replay(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        x['forward']['states']['A']+=1
        with self.assertRaises(ValueError):verify_source_replay(r,c,'feedback_first',x)

    def test_27_replay_same_source_passes(self):
        r,c=self.over
        x=source_execution(r,c,'feedback_first')
        verify_source_replay(r,c,'feedback_first',x)
        self.assertEqual(digest(x),digest(source_execution(r,c,'feedback_first')))

    def test_28_resource_report_deterministic(self):
        self.assertEqual(digest(run_t2e()),digest(self.result))

    def test_29_stress_report_does_not_certify_feedback_cost_for_reward(self):
        self.assertEqual(self.result['charged_semantic_rewards'],0)
        self.assertNotIn('semantic_rewards',self.result['modes']['feedback_first'])

    def test_30_source_auditor_does_not_accept_unrelated_result(self):
        r,c=self.over
        with self.assertRaises(ValueError):audit_resource_execution(r,c,'feedback_first',{'schema':'fake'})
