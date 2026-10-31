"""Adversarial tests for bounded V5-T2g source-grounded shadow arbitration."""
from dataclasses import replace
from pathlib import Path
import json, subprocess, sys, tempfile, unittest

from spk_v5_research.island_endogenous_demand_v5t2c import generate_corpus
from spk_v5_research.island_residual_service_v5t2g import (
    SCHEMA, STAGES, ResidualPlan, AdmissionError,
    residual_execution, verify_residual_execution, run_t2g,
)
from spk_v5_research.island_objective_v5t1 import digest
from spk_v5_research.island_bv_resource_bridge_v5t2e import source_plan
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e,execute_live_v0e

ROOT=Path(__file__).resolve().parents[1]

class TestT2g(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=generate_corpus(blocks=1,seed=37217,regime='aligned',train=False)
        cls.yes=replace(cls.corpus[0],demand=True)
        cls.no=replace(cls.corpus[0],demand=False)
        cls.unknown=replace(cls.corpus[0],demand=None)
        cls.report=run_t2g()

    def paid(self,record=None,action='silent',plan=None):
        return residual_execution(record if record is not None else self.yes,
                                  action,plan if plan is not None else ResidualPlan())

    def test_01_schema_deterministic(self):
        self.assertEqual(self.report['schema'],SCHEMA)
        self.assertEqual(self.report,run_t2g())

    def test_02_seven_real_source_cases_five_profiles(self):
        self.assertEqual(self.report['cells'],35)
        self.assertEqual(sum(self.report['profiles']['normal']['counts'].get(x,0)
                             for x in ('reward_delivered','abstain_delivered')),7)

    def test_03_boundary_flags(self):
        for x in ('frozen_native_modified','native_shadow_control_admission','shadow_grants_native','blind_validation'):
            self.assertFalse(self.report[x])
        self.assertTrue(self.report['source_timeline_native'])
        self.assertEqual(self.report['native_learner_updates'],0)

    def test_04_silent_negative_delivered(self):
        r=self.paid()
        self.assertTrue(r['silent'])
        self.assertEqual((r['status'],r['reward']),('reward_delivered',-1))

    def test_05_silent_positive_delivered(self):
        r=self.paid(self.no)
        self.assertEqual((r['status'],r['reward']),('reward_delivered',1))

    def test_06_unknown_sensor_abstains(self):
        r=self.paid(self.unknown)
        self.assertEqual((r['status'],r['verdict'],r['reward']),('abstain_delivered','abstain',None))

    def test_07_stage_ownership_and_sequence(self):
        r=self.paid()
        self.assertEqual([x['stage'] for x in r['shadow_trace']],list(STAGES))
        self.assertEqual([x['PE_owner'] for x in r['shadow_trace']],
                         ['PE0','PE0','PE1','PE2','PE2','PE1','PE0'])

    def test_08_no_time_travel_and_closure(self):
        r=self.paid()
        ts=[x['tick'] for x in r['shadow_trace']]
        self.assertEqual(ts,sorted(set(ts)))
        self.assertGreaterEqual(r['shadow_trace'][3]['tick'],r['source_closure_tick'])

    def test_09_bv_unchanged_source_sha(self):
        case,fab,pls=source_plan(self.yes,'silent')
        native=execute_live_v0e(case,fab,*pls,LiveBVPlanV0e(
            enabled=True,priority='forward-first',assessor='C',terminal_channel=7,max_ticks=256))
        self.assertEqual(self.paid()['source_bv_v0e_sha256'],digest(native))

    def test_10_native_demand_is_replayed_not_replaced(self):
        self.assertNotEqual(self.paid(self.yes)['source_bv_v0e_sha256'],
                            self.paid(self.no)['source_bv_v0e_sha256'])
        self.assertNotEqual(self.paid(self.no)['source_bv_v0e_sha256'],
                            self.paid(self.unknown)['source_bv_v0e_sha256'])

    def test_11_source_semantic_parity_required(self):
        for r in (self.yes,self.no,self.unknown):
            self.assertTrue(self.paid(r)['source_semantic_parity'])

    def test_12_tight_PE_has_real_deferral(self):
        self.assertGreater(self.report['profiles']['tight_PE']['deferrals'].get('PE_busy',0),0)
        self.assertEqual(self.report['profiles']['tight_PE']['counts']['reward_delivered'],5)

    def test_13_link_competes_against_native_grant(self):
        self.assertGreater(self.report['profiles']['normal']['deferrals'].get('link_busy',0),0)
        self.assertTrue(any(x['source_link_at_grant']==0 for x in self.paid()['shadow_trace'] if x['link']))

    def test_14_exact_resource_sum_complete(self):
        r=self.paid()
        self.assertEqual(r['shadow_charged'],{'PE':7,'memory':12,'link':4})
        self.assertEqual([sum(x[k] for x in r['shadow_trace']) for k in ('PE','memory','link')],[7,12,4])

    def test_15_global_PE_cap_never_violated(self):
        r=self.paid(plan=ResidualPlan(global_pe_cap=2,per_pe_cap=2))
        self.assertTrue(all(x['source_PE_at_grant']+1<=2 for x in r['shadow_trace']))

    def test_16_global_link_cap_never_violated(self):
        r=self.paid()
        self.assertTrue(all(x['source_link_at_grant']+x['link']<=1 for x in r['shadow_trace']))

    def test_17_deadline_blocks_completion(self):
        r=residual_execution(self.no,'overemit',ResidualPlan(max_ticks_after_start=9))
        self.assertEqual(r['status'],'pending_deadline')
        self.assertIsNone(r['reward'])
        self.assertFalse(r['full_semantic_delivery'])
        self.assertIn(r['unserved_stage'],STAGES)

    def test_18_deadline_is_not_negative(self):
        r=residual_execution(self.yes,'overemit',ResidualPlan(max_ticks_after_start=2))
        self.assertEqual((r['status'],r['reward']),('pending_deadline',None))

    def test_19_zero_shadow_service_budget_is_pending(self):
        r=self.paid(plan=ResidualPlan(shadow_pe_quota=0))
        self.assertEqual(r['status'],'pending_deadline')
        self.assertEqual(r['shadow_charged']['PE'],0)

    def test_20_zero_shadow_memory_budget_is_pending(self):
        r=self.paid(plan=ResidualPlan(shadow_mem_quota=0))
        self.assertEqual((r['status'],r['shadow_charged']['memory']),('pending_deadline',0))

    def test_21_zero_shadow_link_budget_not_false_credit(self):
        r=self.paid(plan=ResidualPlan(shadow_link_quota=0))
        self.assertEqual((r['status'],r['reward']),('pending_deadline',None))
        self.assertEqual(r['unserved_stage'],'A_to_B')

    def test_22_bad_source_cap_is_refused(self):
        with self.assertRaises(AdmissionError):self.paid(self.no,'overemit',ResidualPlan(global_pe_cap=1))

    def test_23_no_link_cap_can_refuse_source(self):
        with self.assertRaises(AdmissionError):self.paid(self.no,'overemit',ResidualPlan(link_cap=0))

    def test_24_no_link_source_silence_cannot_deliver(self):
        r=self.paid(plan=ResidualPlan(link_cap=0))
        self.assertEqual((r['status'],r['reward']),('pending_deadline',None))

    def test_25_loss_all_four_transit_stages(self):
        for s in ('A_to_B','B_to_C','C_to_B','B_to_A'):
            r=self.paid(plan=ResidualPlan(drop_stage=s))
            self.assertEqual((r['status'],r['reward']),('transport_loss',None))
            self.assertEqual(r['shadow_trace'][-1]['stage'],s)
            self.assertFalse(r['shadow_trace'][-1]['delivered'])

    def test_26_missing_sensor_with_loss_is_not_abstention(self):
        r=self.paid(self.unknown,plan=ResidualPlan(drop_stage='B_to_A'))
        self.assertEqual(r['status'],'transport_loss')

    def test_27_disabled_shadow_has_no_cost(self):
        r=self.paid(plan=ResidualPlan(enabled=False))
        self.assertEqual((r['status'],r['reward']),('shadow_disabled',None))
        self.assertEqual(r['shadow_charged'],{'PE':0,'memory':0,'link':0})

    def test_28_invalid_bool_cap(self):
        with self.assertRaises(AdmissionError):ResidualPlan(global_pe_cap=True)

    def test_29_invalid_negative_limit(self):
        with self.assertRaises(AdmissionError):ResidualPlan(shadow_mem_quota=-1)

    def test_30_horizon_unbounded_refused(self):
        with self.assertRaises(AdmissionError):ResidualPlan(max_ticks_after_start=257)

    def test_31_invalid_loss_stage(self):
        with self.assertRaises(AdmissionError):ResidualPlan(drop_stage='C_observe_close')

    def test_32_dishonest_plan_type(self):
        with self.assertRaises(AdmissionError):residual_execution(self.yes,'silent',None)

    def test_33_wrong_record_type(self):
        with self.assertRaises(AdmissionError):residual_execution({},'silent')

    def test_34_invalid_sensor_type(self):
        with self.assertRaises(AdmissionError):residual_execution(replace(self.yes,demand=1),'silent')

    def test_35_forged_positive_credit(self):
        r=self.paid()
        r['reward']=1
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_36_forged_grant_tick(self):
        r=self.paid();r['shadow_trace'][2]['tick']+=100
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_37_forged_source_SHA(self):
        r=self.paid();r['source_bv_v0e_sha256']='0'*64
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_38_wrong_origin_and_ownership(self):
        r=self.paid();r['shadow_trace'][0]['PE_owner']='PE2'
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_39_changed_resource_is_refused(self):
        r=self.paid();r['shadow_charged']['link']=0
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_40_wrong_episode_is_refused(self):
        r=self.paid()
        with self.assertRaises(AdmissionError):verify_residual_execution(self.corpus[1],'silent',ResidualPlan(),r)

    def test_41_wrong_arm_is_refused(self):
        r=self.paid()
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'overemit',ResidualPlan(),r)

    def test_42_correct_audit_replay(self):
        r=self.paid();verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_43_rehashed_forgery_not_enough(self):
        r=self.paid();r['reward']=1; _=digest(r)
        with self.assertRaises(AdmissionError):verify_residual_execution(self.yes,'silent',ResidualPlan(),r)

    def test_44_whole_source_memory_capacity_is_checked(self):
        with self.assertRaises(AdmissionError):
            self.paid(plan=ResidualPlan(memory_global_cap=0,enabled=False))

    def test_45_whole_source_service_capacity_is_checked_when_shadow_off(self):
        with self.assertRaises(AdmissionError):
            self.paid(self.yes,'overemit',ResidualPlan(global_pe_cap=1,enabled=False))

    def test_46_canonical_reference(self):
        expected=json.loads((ROOT/'docs/spk-v5-t2g-reference.json').read_text())
        self.assertEqual(expected,self.report)

    def test_47_create_only_report_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'res.json'
            cmd=[sys.executable,str(ROOT/'search/spk_v5_t2g_residual_service.py'),str(path)]
            x=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(x.returncode,0,x.stderr)
            self.assertEqual(path.read_bytes(),(ROOT/'docs/spk-v5-t2g-reference.json').read_bytes())
            second=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)

    def test_48_reject_in_repo_report(self):
        x=subprocess.run([sys.executable,str(ROOT/'search/spk_v5_t2g_residual_service.py'),
                          str(ROOT/'docs/never-reward.json')],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(x.returncode,0)
        self.assertFalse((ROOT/'docs/never-reward.json').exists())

    def test_49_refuse_symlink_target(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'target';target.write_text('original')
            link=Path(d)/'link';link.symlink_to(target)
            x=subprocess.run([sys.executable,str(ROOT/'search/spk_v5_t2g_residual_service.py'),str(link)],
                             cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(x.returncode,0)
            self.assertEqual(target.read_text(),'original')

if __name__=='__main__':unittest.main()
