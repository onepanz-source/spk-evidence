"""Bounded adversarial conformance of the V5 T2h isolated research fork."""
import copy
import subprocess
import tempfile
import sys
from dataclasses import replace
import unittest
from pathlib import Path
from unittest.mock import patch

from spk_v5_research.island_endogenous_demand_v5t2c import generate_corpus
from spk_v5_research.island_objective_v5t1 import CANDIDATES,digest
from spk_v5_research.island_bv_resource_bridge_v5t2e import source_plan
from spk_v5_research.island_interleaved_v5t2h import (
    InterleavedPlan, AdmissionError, LiveBVRejected, LiveBVPlanV0e,
    FROZEN_EXECUTE, integrated_execution, verify_integrated_execution, run_t2h,
)


class InterleavedV5T2h(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=generate_corpus(blocks=1,seed=37217,regime='aligned',train=False)
        cls.examples=tuple((replace(r,demand=(False,True,None)[i%3]),CANDIDATES[i%3])
                           for i,r in enumerate(cls.corpus))
        cls.matrix={name:[integrated_execution(r,a,plan) for r,a in cls.examples]
                    for name,plan in (
                        ('off',InterleavedPlan(enabled=False)),
                        ('source',InterleavedPlan()),
                        ('control',InterleavedPlan(priority='control-first')),
                        ('deadline',InterleavedPlan(deadline_after_start=9)),
                        ('loss',InterleavedPlan(drop_stage='B_to_A')))}

    def test_01_seven_signed_template_examples(self):
        self.assertEqual([r.template_id for r,_ in self.examples],list(range(7)))

    def test_02_off_exact_native_including_resources(self):
        for (r,a),e in zip(self.examples,self.matrix['off']):
            case,fabric,plans=source_plan(r,a)
            real=FROZEN_EXECUTE(case,fabric,*plans,LiveBVPlanV0e(
                enabled=True,priority='forward-first',assessor='C',terminal_channel=7,max_ticks=256))
            self.assertEqual(e['source_view'],real)

    def test_03_off_exact_native_when_source_BV_off(self):
        r,a=self.examples[0]
        result=integrated_execution(r,a,InterleavedPlan(enabled=False,source_bv_enabled=False))
        case,fabric,plans=source_plan(r,a)
        real=FROZEN_EXECUTE(case,fabric,*plans,LiveBVPlanV0e(
            enabled=False,priority='forward-first',assessor='C',terminal_channel=7,max_ticks=256))
        self.assertEqual(result['source_view'],real)

    def test_04_off_no_control_cost(self):
        for result in self.matrix['off']:
            self.assertEqual(result['control']['status'],'disabled')
            self.assertEqual(sum(result['control']['cost'].values()),0)
            self.assertEqual(result['control']['trace'],[])

    def test_05_enabled_control_changes_source_timing(self):
        self.assertTrue(any(a['source_view']['forward']['batches'] !=b['source_view']['forward']['batches']
            for a,b in zip(self.matrix['control'],self.matrix['off'])))

    def test_06_source_and_control_priorities_differ(self):
        self.assertNotEqual([digest(x['source_view']) for x in self.matrix['source']],
                            [digest(x['source_view']) for x in self.matrix['control']])

    def test_07_source_priority_does_not_rewrite_source_forward(self):
        for a,b in zip(self.matrix['source'],self.matrix['off']):
            self.assertEqual(a['source_view']['forward']['batches'],b['source_view']['forward']['batches'])

    def test_08_control_is_paid_inside_same_resource_timeline(self):
        for result in self.matrix['source']+self.matrix['control']:
            timeline=result['source_view']['resources']['timeline']
            control=result['control']
            self.assertEqual(sum(r['semantic_control_PE'] for r in timeline),control['cost']['PE'])
            self.assertEqual(sum(r['semantic_control_memory'] for r in timeline),control['cost']['memory'])
            self.assertEqual(sum(r['semantic_control_link'] for r in timeline),control['cost']['link'])

    def test_09_per_tick_global_caps_not_exceeded(self):
        for group in self.matrix.values():
            for result in group:
                for row in result['source_view']['resources']['timeline']:
                    self.assertLessEqual(row['pe_service_total'],4)
                    self.assertLessEqual(row['memory_total'],768)
                    self.assertLessEqual(row['link_total'],1)

    def test_10_per_pe_caps_not_exceeded(self):
        for group in self.matrix.values():
            for result in group:
                for row in result['source_view']['resources']['timeline']:
                    self.assertTrue(all(v<=3 for v in row['pe_service_by_pe'].values()))
                    self.assertTrue(all(v<=256 for v in row['memory_by_pe'].values()))
                    self.assertTrue(all(v<=256 for v in row['memory_by_domain'].values()))

    def test_11_monotonic_stage_causal_order(self):
        for result in self.matrix['source']+self.matrix['control']:
            trace=result['control']['trace']
            self.assertEqual([x['tick'] for x in trace],sorted(set(x['tick'] for x in trace)))
            self.assertEqual([x['stage'] for x in trace],
                ['decision_commit','A_to_B','B_to_C','C_observe_close',
                 'C_to_B','B_to_A','A_consume'])

    def test_12_transits_have_real_positive_arrival_delay(self):
        for result in self.matrix['source']:
            grants=[x for x in result['control']['trace'] if x['link']]
            arrivals=result['control']['arrivals']
            self.assertEqual(len(grants),len(arrivals))
            self.assertEqual([(x['stage'],x['due_tick']) for x in grants],
                             [(x['stage'],x['tick']) for x in arrivals])

    def test_13_observer_cannot_run_before_closure(self):
        for result in self.matrix['control']+self.matrix['source']:
            closure=[x['timestamp'] for x in result['source_view']['forward']['terminal']
                     if x['node_id']=='C' and x['channel']==9]
            observe=next(x['tick'] for x in result['control']['trace']
                         if x['stage']=='C_observe_close')
            self.assertGreaterEqual(observe,closure[0])

    def test_14_forward_silent_choice_positive_reward(self):
        result=integrated_execution(replace(self.corpus[0],demand=False),'silent')
        self.assertTrue(result['control']['silent']);self.assertEqual(result['control']['reward'],1)

    def test_15_forward_silent_choice_negative_reward(self):
        result=integrated_execution(replace(self.corpus[0],demand=True),'silent')
        self.assertEqual(result['control']['reward'],-1)

    def test_16_absent_C_observation_abstains(self):
        result=integrated_execution(replace(self.corpus[0],demand=None),'silent')
        self.assertEqual(result['control']['status'],'abstain_delivered')
        self.assertIsNone(result['control']['reward'])

    def test_17_return_loss_never_becomes_negative(self):
        for result in self.matrix['loss']:
            self.assertEqual(result['control']['status'],'transport_loss')
            self.assertIsNone(result['control']['reward'])
            self.assertEqual(result['control']['trace'][-1]['stage'],'B_to_A')
            self.assertFalse(result['control']['trace'][-1]['delivered'])

    def test_18_short_deadline_never_becomes_negative(self):
        for result in self.matrix['deadline']:
            if result['control']['status']=='pending_deadline_expired':
                self.assertIsNone(result['control']['reward'])

    def test_19_no_drain_after_deadline_for_control(self):
        for (rec,_),result in zip(self.examples,self.matrix['deadline']):
            self.assertTrue(all(x['tick']<=rec.episode.inputs[0][0]+9
                                for x in result['control']['trace']))

    def test_20_no_free_control_service(self):
        for group in ('source','control','deadline','loss'):
            for result in self.matrix[group]:
                t=result['control']['trace'];c=result['control']['cost']
                self.assertEqual(c['PE'],len(t))
                self.assertEqual(c['memory'],sum(x['memory'] for x in t))
                self.assertEqual(c['link'],sum(x['link'] for x in t))

    def test_21_semantic_timing_mismatch_fail_closed(self):
        self.assertTrue(any(not x['control']['source_semantic_parity']
                            for x in self.matrix['control']))
        for x in self.matrix['control']:
            if not x['control']['source_semantic_parity']:
                self.assertIsNone(x['control']['reward'])

    def test_22_forward_acks_still_source_owned(self):
        for result in self.matrix['source']:
            src=result['source_view']
            self.assertEqual(src['resources']['bv_service_units'],len(src['feedback']['link_grants']))
            self.assertEqual(src['resources']['bv_memory_units'],2*len(src['feedback']['link_grants']))

    def test_23_control_not_falsely_called_native(self):
        for group in self.matrix.values():
            for result in group:
                self.assertTrue(result['control']['host_origin_not_native'])
                self.assertFalse(result['source_native_granted_semantic_control'])
                self.assertFalse(result['frozen_modified'])
                self.assertEqual(result['learning_updates'],0)

    def test_24_identical_determinism_across_reexecution(self):
        r,a=self.examples[1];plan=InterleavedPlan(priority='control-first')
        self.assertEqual(integrated_execution(r,a,plan),integrated_execution(r,a,plan))

    def test_25_invalid_action_rejected(self):
        with self.assertRaises(AdmissionError):integrated_execution(self.examples[0][0],'unbounded_magic')

    def test_26_wrong_dataclass_plan_rejected(self):
        with self.assertRaises(AdmissionError):integrated_execution(self.examples[0][0], 'silent',plan={})

    def test_27_bad_priority_rejected(self):
        with self.assertRaises(AdmissionError):InterleavedPlan(priority='magic')

    def test_28_boolean_tick_rejected(self):
        with self.assertRaises(AdmissionError):InterleavedPlan(deadline_after_start=True)

    def test_29_overlong_horizon_rejected(self):
        with self.assertRaises(AdmissionError):InterleavedPlan(deadline_after_start=9999)

    def test_30_invalid_drop_stage_rejected(self):
        with self.assertRaises(AdmissionError):InterleavedPlan(drop_stage='C_observe_close')

    def test_31_signed_original_source_sha_unchanged(self):
        from spk_v5_research.island_interleaved_v5t2h import FROZEN_EXECUTE
        self.assertEqual(FROZEN_EXECUTE.__module__,'spk_backvalidation_v0.live_dual_scheduler_v0e')

    def test_32_functional_result_is_not_a_native_learning_claim(self):
        report=run_t2h()
        self.assertFalse(report['native_engine_modified'])
        self.assertFalse(report['native_integration'])
        self.assertFalse(report['blind_T3'])
        self.assertEqual(report['native_learning_updates'],0)

    def test_33_known_canonical_profile_counts(self):
        report=run_t2h()
        self.assertEqual(report['profiles']['source_first']['statuses'],
                         {'abstain_delivered':2,'reward_delivered':5})
        self.assertEqual(report['profiles']['deadline_short']['statuses']['pending_deadline_expired'],2)
        self.assertEqual(report['profiles']['control_first']['source_forward_batch_changes_vs_off'],1)

    def test_34_identifiers_stable_against_future_demand(self):
        r=self.corpus[0]
        a=integrated_execution(replace(r,demand=True),'silent')['control']['decision_token']
        b=integrated_execution(replace(r,demand=False),'silent')['control']['decision_token']
        self.assertEqual(a,b)

    def test_36_forged_control_grant_rejected_by_replay(self):
        r,a=self.examples[0];p=InterleavedPlan()
        forged=copy.deepcopy(self.matrix['source'][0]);forged['control']['trace'][0]['tick']-=1
        with self.assertRaises(AdmissionError):verify_integrated_execution(r,a,p,forged)

    def test_37_forged_cost_rejected_by_replay(self):
        r,a=self.examples[0];p=InterleavedPlan()
        forged=copy.deepcopy(self.matrix['source'][0]);forged['control']['cost']['PE']=0
        with self.assertRaises(AdmissionError):verify_integrated_execution(r,a,p,forged)

    def test_38_forged_source_timing_rejected(self):
        r,a=self.examples[0];p=InterleavedPlan()
        forged=copy.deepcopy(self.matrix['source'][0])
        forged['source_view']['resources']['timeline'][0]['pe_service_total']=999
        with self.assertRaises(AdmissionError):verify_integrated_execution(r,a,p,forged)

    def test_39_forged_reward_not_accepted(self):
        r,a=self.examples[0];p=InterleavedPlan()
        forged=copy.deepcopy(self.matrix['source'][0]);forged['control']['reward']=1
        with self.assertRaises(AdmissionError):verify_integrated_execution(r,a,p,forged)

    def test_40_exact_reexecution_accepted(self):
        r,a=self.examples[0];p=InterleavedPlan()
        self.assertIsNone(verify_integrated_execution(r,a,p,self.matrix['source'][0]))

    def test_41_create_only_report_matches_canonical(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'new.json'
            done=subprocess.run([sys.executable,'search/spk_v5_t2h_integrated.py',str(out)],
                                capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertEqual(out.read_bytes(),Path('docs/spk-v5-t2h-reference.json').read_bytes())

    def test_42_cli_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'old.json';out.write_text('do-not-replace')
            done=subprocess.run([sys.executable,'search/spk_v5_t2h_integrated.py',str(out)],
                                capture_output=True,text=True)
            self.assertNotEqual(done.returncode,0)
            self.assertEqual(out.read_text(),'do-not-replace')

    def test_43_cli_symlink_target_refused(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'real';target.write_text('preserve')
            link=Path(d)/'fake';link.symlink_to(target)
            done=subprocess.run([sys.executable,'search/spk_v5_t2h_integrated.py',str(link)],
                                capture_output=True,text=True)
            self.assertNotEqual(done.returncode,0)
            self.assertEqual(target.read_text(),'preserve')

    def test_44_cli_in_repository_target_refused(self):
        repo=Path.cwd()
        out=repo/'DO_NOT_CREATE_V5_T2H_REPORT.json'
        self.assertFalse(out.exists())
        done=subprocess.run([sys.executable,'search/spk_v5_t2h_integrated.py',str(out)],
                            capture_output=True,text=True)
        self.assertNotEqual(done.returncode,0)
        self.assertFalse(out.exists())

    def test_35_declared_origin_is_shadow_host(self):
        x=self.matrix['source'][0]['control']
        self.assertTrue(x['host_origin_not_native'])


if __name__=='__main__':unittest.main()
