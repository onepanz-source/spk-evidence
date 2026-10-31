"""BV v2k: integrated DERIVED counters and exact native-report projection."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e,execute_live_v0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,NativeForkError,PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ShadowServicePlanV2j,
)
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    DerivedActorAdmissionV2k,derive_resource_admission_executor,
)
from spk_bv_research.actor_resource_admission_integration_v2k import (
    validate_v2j,experiment,build_report,STATUS,CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2j-shadow-actor-control-service.json'),
         ROOT/'spk-bv-v2j-shadow-actor-control-service.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2J_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,case=None,bv=None,port_args=None,service_plan=None):
    default,fabric,plans=fixture()
    case=default if case is None else case
    bv=LiveBVPlanV0e() if bv is None else bv
    port=ReceiverPortV2h(**(port_args or {}))
    service=DerivedActorAdmissionV2k(port,service_plan or ShadowServicePlanV2j())
    watcher=CallsiteObserver()
    derivative,_,anchors,resource=derive_resource_admission_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,service,watcher)
    native=execute_live_v0e(case,fabric,*plans,bv)
    integrated=derivative(case,fabric,*plans,bv)
    projected=service.project_original_native_result(integrated)
    return native,integrated,projected,service,port,watcher,anchors,resource


class TestV2kIntegratedActorAdmission(unittest.TestCase):

    def test_resource_commit_modifies_derived_result_not_forward_or_original(self):
        native,integrated,projected,service,port,watcher,anchors,resource=one_run()
        self.assertEqual(projected,native)
        self.assertNotEqual(integrated,native)
        self.assertEqual(integrated['forward'],native['forward'])
        self.assertEqual(integrated['feedback'],native['feedback'])
        self.assertEqual(anchors,(('batch',194),('clock',125),
                                  ('emission',217),('ingress',136)))
        self.assertEqual(resource,(296,307))
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(watcher.counts(),{'_admit':1,'_admit_plan':1,
                                          'offer_feedback':6})
        self.assertNotIn('__v2k_admission',execute_live_v0e.__globals__)
        s=service.summary()
        self.assertEqual(s['derived_resource_grants_committed'],4)
        self.assertEqual(s['derived_inline_actor_grants'],4)
        self.assertEqual(s['derived_committed_memory_units'],8)
        self.assertFalse(s['frozen_original_resource_counters_changed'])
        self.assertFalse(s['frozen_native_actor_intake_observed'])

    def test_budget_commits_are_in_derived_timeline_not_shadow_only(self):
        native,modified,projected,service,_,_,_,_=one_run()
        self.assertEqual(native,projected)
        for row,ledger in zip(modified['resources']['timeline'],
                              service.resource_timeline()):
            with self.subTest(tick=row['tick']):
                self.assertEqual(row['pe_service_total'],
                                 ledger['combined_service_used'])
                self.assertEqual(row['memory_total'],
                                 ledger['combined_memory_used'])
                self.assertEqual(row['memory_by_domain'],
                                 ledger['combined_memory_by_domain'])
                self.assertLessEqual(row['pe_service_total'],ledger['service_budget'])
                self.assertLessEqual(row['memory_total'],ledger['memory_budget'])

    def test_unaccounted_inline_mutation_must_fail_native_projection(self):
        _,integrated,_,service,_,_,_,_=one_run()
        edited={**integrated,'resources':dict(integrated['resources'])}
        edited['resources']['timeline']=[dict(row) for row in
                                         integrated['resources']['timeline']]
        targeted=next(row for row in edited['resources']['timeline']
                      if row['pe_service_total']>0)
        targeted['memory_total']+=1
        with self.assertRaises(NativeForkError):
            service.project_original_native_result(edited)

    def test_unaccounted_tail_mutation_must_fail_native_projection(self):
        native,integrated,projected,service,_,_,_,_=one_run(
            port_args={'latency':16})
        self.assertEqual(native,projected)
        self.assertGreater(service.summary()['new_derived_control_only_timeline_rows'],0)
        bad={**integrated,'resources':dict(integrated['resources'])}
        bad['resources']['timeline']=[dict(row) for row in
                                      integrated['resources']['timeline']]
        bad['resources']['timeline'][-1]['memory_total']+=1
        with self.assertRaises(NativeForkError):
            service.project_original_native_result(bad)

    def test_control_only_tail_rows_have_no_forward_computation(self):
        native,changed,projected,service,port,_,_,_=one_run(
            port_args={'latency':16})
        self.assertEqual(projected,native)
        original_rows=len(native['resources']['timeline'])
        tail=changed['resources']['timeline'][original_rows:]
        self.assertEqual(len(tail),
                         service.summary()['new_derived_control_only_timeline_rows'])
        self.assertTrue(tail)
        self.assertTrue(all(row['forward_computations']==0 and
                            row['feedback_sends']==0 and
                            row['link_total']==0 and
                            row['cross_inflight_end_tick']==0 for row in tail))

    def test_disabled_native_BV_and_priority_keep_forward_and_projection(self):
        for enabled,priority in ((False,'forward-first'),
                                 (True,'forward-first'),(True,'feedback-first')):
            with self.subTest(enabled=enabled,priority=priority):
                original,changed,recovered,service,port,_,_,_=one_run(bv=
                    LiveBVPlanV0e(enabled=enabled,priority=priority))
                self.assertEqual(original,recovered)
                self.assertEqual(original['forward'],changed['forward'])
                self.assertEqual(original['feedback'],changed['feedback'])
                self.assertEqual(service.summary()['delivered_controls'],4)

    def test_negative_B_two_derived_resource_grants_not_learning(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        original,integrated,projected,service,port,_,_,_=one_run(case=changed)
        self.assertEqual(original,projected)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(service.summary()['derived_resource_grants_committed'],2)
        self.assertEqual(service.summary()['credit_by_actor']['A'],-2)
        self.assertEqual(service.summary()['native_operator_updates'],0)
        self.assertFalse(service.summary()['native_learning_proven'])

    def test_loss_and_callback_fault_do_not_create_derived_resource_grants(self):
        for label,args in (
            ('loss',{'accept':lambda _:False}),
            ('fault',{'accept':lambda _:
                (_ for _ in ()).throw(RuntimeError('control unavailable'))}),
        ):
            with self.subTest(label=label):
                native,changed,projected,service,port,_,_,_=one_run(port_args=args)
                self.assertEqual(native,projected)
                self.assertEqual(native,changed)
                self.assertEqual(service.summary()['derived_resource_grants_committed'],0)
                self.assertEqual(service.summary()['absence_certificates'],0)

    def test_capacity_pressure_and_no_tail_do_not_break_projection(self):
        for label,kwargs in (
            ('overflow',{'port_args':{'capacity':1}}),
            ('no_tail',{'service_plan':ShadowServicePlanV2j(
                max_per_tick=1,max_tail_ticks=0)}),
            ('tight',{'service_plan':ShadowServicePlanV2j(
                max_per_tick=1,max_tail_ticks=32)}),
        ):
            with self.subTest(label=label):
                native,altered,recovered,service,port,_,_,_=one_run(**kwargs)
                self.assertEqual(native,recovered)
                self.assertEqual(altered['forward'],native['forward'])
                s=service.summary()
                self.assertEqual(s['derived_resource_grants_committed']+
                                 s['unconsumed_delivered_controls'],
                                 s['delivered_controls'])
                self.assertTrue(s['within_original_native_plan_capacity'])
                if label=='no_tail':
                    self.assertEqual(s['new_derived_control_only_timeline_rows'],0)

    def test_manual_causal_mailbox_forgery_before_tail_rejected(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        service=DerivedActorAdmissionV2k(port)
        derivative,_,_,_=derive_resource_admission_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,service,CallsiteObserver())
        # Derived finish runs inside the executor; intervene at the port's
        # causal validator so no forged native projection is returned.
        original_batch=port.batch
        attacked={'done':False}
        def malicious_batch(actor,tick,items,outputs):
            original_batch(actor,tick,items,outputs)
            if port.judgments and not attacked['done']:
                forged=replace(port.judgments[0],identity='fake-inbox',recipient='A')
                port._mailboxes.setdefault('A',[]).append(forged)
                attacked['done']=True
        port.batch=malicious_batch
        with self.assertRaises(NativeForkError):
            derivative(case,fabric,*plans,LiveBVPlanV0e())

    def test_invalid_plan_and_pinned_source_drift_rejected(self):
        port=ReceiverPortV2h()
        with self.assertRaises(NativeForkError):
            DerivedActorAdmissionV2k(port,ShadowServicePlanV2j(max_tail_ticks=129))
        service=DerivedActorAdmissionV2k(port)
        with self.assertRaises(NativeForkError):
            derive_resource_admission_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,service,CallsiteObserver())

    def test_15_native_recipes_project_full_result_exactly(self):
        case,fabric,plans=fixture()
        source=SOURCE.read_bytes()
        for label,recipe in RECIPES:
            with self.subTest(label=label):
                changed=build_workload(case,recipe)
                port=ReceiverPortV2h()
                service=DerivedActorAdmissionV2k(port)
                derivative,_,_,_=derive_resource_admission_executor(
                    source,execute_live_v0e,port,service,CallsiteObserver())
                original=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                integrated=derivative(changed,fabric,*plans,LiveBVPlanV0e())
                self.assertEqual(service.project_original_native_result(integrated),
                                 original)
                self.assertEqual(integrated['forward'],original['forward'])
                self.assertNotEqual(integrated['resources']['timeline'],
                                    original['resources']['timeline'])

    def test_signed_off_v2j_predecessor_mutation_fail_closed(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2j predecessor not mounted')
        obj=json.loads(raw)
        self.assertTrue(validate_v2j(obj,raw))
        for field,value in (('full_native_result_parity_cells',44),
                            ('native_actor_service_resource_grants_proven',True),
                            ('native_learning_proven',True)):
            with self.subTest(field=field):
                changed=dict(obj);changed[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2j(changed,canon(changed))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2j(obj,raw+b'\n')

    def test_full_45_cell_native_projection_replay_and_canonical_report(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2j predecessor not mounted')
        previous=json.loads(raw)
        self.assertEqual(build_report(previous,raw)['status'],CONTRACT_STATUS)
        result=experiment(previous,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['full_native_projection_parity_cells'],45)
        self.assertEqual(report['derived_resource_timeline_changed_cells'],45)
        s=report['integrated_admission_totals']
        self.assertEqual(s['delivered_controls'],156)
        self.assertEqual(s['derived_resource_grants_committed'],156)
        self.assertEqual(s['derived_inline_actor_grants'],140)
        self.assertEqual(s['derived_control_tail_grants'],16)
        self.assertEqual(s['unconsumed_delivered_controls'],0)
        self.assertEqual(s['derived_committed_memory_units'],312)
        self.assertFalse(report['frozen_native_actor_resource_grant_commits_observed'])
        self.assertFalse(report['native_learning_proven'])
        self.assertEqual(canon(report),canon(json.loads(canon(report))))


if __name__=='__main__':
    unittest.main()
