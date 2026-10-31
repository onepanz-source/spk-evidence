"""BV v2j: source-anchored control-only shadow resource service and rejection tests."""
from __future__ import annotations

import json
import os
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, NativeForkError,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ActorControlServiceV2j, ShadowServicePlanV2j,
    derive_shadow_service_executor,
)
from spk_bv_research.actor_control_service_integration_v2j import (
    validate_v2i,experiment,build_report,STATUS,CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2i-derived-actor-batch-intake.json'),
         ROOT/'spk-bv-v2i-derived-actor-batch-intake.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2I_REPORT')
    options=([Path(configured)] if configured else [])+list(REPORTS)
    for path in options:
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,case=None,plan=None,port_args=None,service_plan=None):
    original,fabric,plans=fixture()
    case=original if case is None else case
    plan=LiveBVPlanV0e() if plan is None else plan
    port=ReceiverPortV2h(**(port_args or {}))
    service=ActorControlServiceV2j(port,service_plan or ShadowServicePlanV2j())
    observer=CallsiteObserver()
    derived,calls,anchors,tick=derive_shadow_service_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,service,observer)
    native=execute_live_v0e(case,fabric,*plans,plan)
    result=derived(case,fabric,*plans,plan)
    service.close_after_native(result['resources']['timeline'][-1]['tick'])
    service.audit_native_timeline(result['resources']['timeline'])
    return native,result,service,port,observer,calls,anchors,tick


class TestV2jShadowControlService(unittest.TestCase):

    def test_real_native_slack_consumes_all_four_without_mutation(self):
        native,actual,service,port,monitor,_,anchors,tick=one_run()
        self.assertEqual(native,actual)
        self.assertEqual(anchors,(('batch',194),('clock',125),
                                  ('emission',217),('ingress',136)))
        self.assertEqual(tick,296)
        s=service.summary()
        self.assertEqual(s['shadow_control_service_grants'],4)
        self.assertEqual(s['native_slack_actor_service_grants'],4)
        self.assertEqual(s['post_native_shadow_tail_grants'],0)
        self.assertEqual(s['credit_by_actor'],{'A':2,'B':2,'C':0})
        self.assertTrue(s['all_shadow_grants_within_native_plan_envelope'])
        self.assertFalse(s['native_control_service_resources_accounted'])
        self.assertEqual(monitor.counts(),{'_admit':1,'_admit_plan':1,
                                          'offer_feedback':6})
        self.assertEqual(port.summary()['source_owned_emissions'],4)
        self.assertNotIn('__v2j_service',execute_live_v0e.__globals__)

    def test_independent_control_receipt_without_actor_batch(self):
        a,b,service,port,_,_,_,_=one_run()
        self.assertEqual(a,b)
        native_actor_batch_pairs={(r['tick'],r['node']) for r in
                                  b['forward']['batches']}
        control_only=[g for g in service.grants()
                      if (g.tick,g.actor) not in native_actor_batch_pairs]
        self.assertGreater(len(control_only),0)
        self.assertEqual(port.summary()['control_delivered'],4)
        self.assertEqual(service.summary()['shadow_control_service_grants'],4)

    def test_real_negative_B_credit_both_serviced_not_native_learning(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        before,after,service,port,_,_,_,_=one_run(case=changed)
        self.assertEqual(before,after)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(service.summary()['shadow_control_service_grants'],2)
        self.assertEqual(service.summary()['credit_by_actor']['A'],-2)
        self.assertEqual(service.summary()['native_operator_updates'],0)
        self.assertFalse(service.summary()['native_learning_proven'])

    def test_no_tail_truncates_receipts_but_never_fabricates_judgment(self):
        plan=ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=0)
        native,actual,service,port,_,_,_,_=one_run(service_plan=plan)
        self.assertEqual(native,actual)
        s=service.summary()
        self.assertEqual(s['post_native_shadow_tail_grants'],0)
        self.assertEqual(s['tail_ticks'],0)
        self.assertEqual(s['shadow_control_service_grants']+
                         s['unconsumed_delivered_controls'],
                         s['delivered_controls'])
        self.assertEqual(s['absence_certificates'],0)

    def test_tail_is_explicit_and_bounded_when_one_service_slot(self):
        base,altered,service,port,_,_,_,_=one_run(service_plan=
            ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=32))
        self.assertEqual(base,altered)
        s=service.summary()
        self.assertEqual(s['shadow_control_service_grants'],4)
        self.assertLessEqual(s['tail_ticks'],32)
        self.assertTrue(s['all_shadow_grants_within_native_plan_envelope'])
        self.assertEqual(s['shadow_memory_units'],8)

    def test_loss_and_bounded_transport_never_mutate_native_output(self):
        for label,opts in (('loss',{'accept':lambda _:False}),
                           ('fault',{'accept':lambda _:
                                (_ for _ in ()).throw(RuntimeError('offline'))}),
                           ('overflow',{'capacity':1})):
            with self.subTest(label=label):
                a,b,service,port,_,_,_,_=one_run(port_args=opts)
                self.assertEqual(a,b)
                self.assertEqual(service.summary()['absence_certificates'],0)
                if label=='loss':
                    self.assertEqual(port.summary()['lost'],4)
                    self.assertEqual(service.summary()['shadow_control_service_grants'],0)
                elif label=='fault':
                    self.assertEqual(port.summary()['fault_lost'],4)
                    self.assertEqual(service.summary()['shadow_control_service_grants'],0)
                else:
                    self.assertTrue(port.summary()['queue_overflow'] or
                                    port.summary()['mailbox_overflow'])

    def test_shadow_budget_rows_never_exceed_PEs_or_domains(self):
        native,actual,service,_,_,_,_,_=one_run()
        self.assertEqual(native,actual)
        for row in service.resource_timeline():
            with self.subTest(tick=row['tick']):
                self.assertLessEqual(row['combined_service_used'],
                                     row['service_budget'])
                self.assertLessEqual(row['combined_memory_used'],
                                     row['memory_budget'])
                for pe,cap in row['pe_service_caps'].items():
                    self.assertLessEqual(row['combined_service_by_pe'].get(pe,0),cap)
                for pe,cap in row['pe_memory_caps'].items():
                    self.assertLessEqual(row['combined_memory_by_pe'].get(pe,0),cap)
                for domain,cap in row['domain_memory_caps'].items():
                    self.assertLessEqual(row['combined_memory_by_domain'].get(domain,0),cap)

    def test_actor_owner_from_admission_and_clock_replay_rejected(self):
        port=ReceiverPortV2h()
        service=ActorControlServiceV2j(port)
        with self.assertRaises(NativeForkError):
            service.bind_admitted_actors({'A':SimpleNamespace(node_id='C')},{'A':'P0'})
        service.bind_admitted_actors({'A':SimpleNamespace(node_id='A')},{'A':'P0'})
        with self.assertRaises(NativeForkError):
            service.bind_admitted_actors({'A':SimpleNamespace(node_id='A')},{'A':'P0'})
        kwargs=(Counter(),0,Counter(),Counter(),0,
                {'P0':4},{'P0':8},{'O':8,'E':8},4,8)
        service._service_tick(1,'native-slack',*kwargs)
        with self.assertRaises(NativeForkError):
            service._service_tick(1,'native-slack',*kwargs)
        with self.assertRaises(NativeForkError):
            service._service_tick(0,'native-slack',*kwargs)

    def test_spoofed_mailbox_before_tail_rejected(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h()
        service=ActorControlServiceV2j(port)
        d,_,_,_=derive_shadow_service_executor(SOURCE.read_bytes(),
            execute_live_v0e,port,service,CallsiteObserver())
        actual=d(case,fabric,*plans,LiveBVPlanV0e())
        first=port.judgments[0]
        forged=replace(first,identity='made-up',recipient='A')
        port._mailboxes.setdefault('A',[]).append(forged)
        with self.assertRaises(NativeForkError):
            service.close_after_native(actual['resources']['timeline'][-1]['tick'])
        self.assertFalse(service._closed)

    def test_invalid_plan_and_source_drift_fail_closed(self):
        port=ReceiverPortV2h()
        for kwargs in ({'max_tail_ticks':True},{'max_tail_ticks':129},
                       {'max_per_tick':0},{'max_total_receipts':0},
                       {'per_actor_per_tick':17}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(NativeForkError):
                    ActorControlServiceV2j(port,ShadowServicePlanV2j(**kwargs))
        service=ActorControlServiceV2j(port)
        with self.assertRaises(NativeForkError):
            derive_shadow_service_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,service,CallsiteObserver())

    def test_15_native_recipes_equal_and_control_charged(self):
        case,fabric,plans=fixture()
        source=SOURCE.read_bytes()
        for label,recipe in RECIPES:
            with self.subTest(label=label):
                changed=build_workload(case,recipe)
                port=ReceiverPortV2h()
                service=ActorControlServiceV2j(port)
                derived,_,_,_=derive_shadow_service_executor(
                    source,execute_live_v0e,port,service,CallsiteObserver())
                native=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                actual=derived(changed,fabric,*plans,LiveBVPlanV0e())
                service.close_after_native(actual['resources']['timeline'][-1]['tick'])
                self.assertEqual(native,actual)
                self.assertTrue(service.audit_native_timeline(
                    actual['resources']['timeline']))
                self.assertEqual(service.summary()['delivered_controls'],
                                 len(native['forward']['occurrences']))

    def test_signed_off_v2i_predecessor_mutations_rejected(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('v2i predecessor not locally mounted')
        old=json.loads(raw)
        self.assertTrue(validate_v2i(old,raw))
        for field,value in (('full_native_result_parity_cells',44),
                            ('frozen_native_actor_intake_observed',True),
                            ('native_learning_proven',True)):
            with self.subTest(field=field):
                mutated=dict(old);mutated[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2i(mutated,canon(mutated))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2i(old,raw+b'\n')

    def test_full_pinned_native_resource_matrix_and_canonical_report(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('v2i predecessor not locally mounted')
        previous=json.loads(raw)
        self.assertEqual(build_report(previous,raw)['status'],CONTRACT_STATUS)
        result=experiment(previous,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['full_native_result_parity_cells'],45)
        totals=report['shadow_service_totals']
        self.assertEqual(totals['delivered_controls'],156)
        self.assertEqual(totals['shadow_control_service_grants'],156)
        self.assertEqual(totals['native_slack_actor_service_grants'],140)
        self.assertEqual(totals['post_native_shadow_tail_grants'],16)
        self.assertEqual(totals['unconsumed_delivered_controls'],0)
        self.assertEqual(totals['shadow_memory_units'],312)
        self.assertEqual(report['negative_native_fixture']['actor_credit']['A'],-2)
        self.assertFalse(report['native_actor_service_resource_grants_proven'])
        self.assertFalse(report['native_learning_proven'])
        self.assertEqual(canon(report),canon(json.loads(canon(report))))


if __name__=='__main__':
    unittest.main()
