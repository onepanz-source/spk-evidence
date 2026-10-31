"""BV v2m: source-pinned actor-first contention, causal nulls and bounds."""
from __future__ import annotations

import json
import os
import unittest
from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e,LiveBVRejected,execute_live_v0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,NativeForkError,PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import (
    DerivedActorPriorityV2m,derive_priority_executor,
)
from spk_bv_research.actor_priority_contention_integration_v2m import (
    validate_v2l,experiment,build_report,STATUS,CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2l-actor-credit-protocol.json'),
         ROOT/'spk-bv-v2l-actor-credit-protocol.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2L_REPORT')
    for p in ([Path(configured)] if configured else [])+list(REPORTS):
        if p.is_file():return p.read_bytes()
    return None


def one_run(*,capacity=3,actor_priority='actor-first',case=None,
            port_options=None,credit_plan=None,bv=None):
    basic,fabric,plans=fixture()
    case=basic if case is None else case
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    ctrl=LiveBVPlanV0e() if bv is None else bv
    port=ReceiverPortV2h(**(port_options or {}))
    service=DerivedActorPriorityV2m(port,priority=actor_priority,
        credit_plan=credit_plan or ActorCreditPlanV2l())
    observer=CallsiteObserver()
    derived,_,anchors,resource=derive_priority_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,service,observer)
    native=execute_live_v0e(case,fabric,*plans,ctrl)
    integrated=derived(case,fabric,*plans,ctrl)
    projected=service.project_original_native_result(integrated)
    return native,integrated,projected,service,port,observer,anchors,resource


class TestV2mActorPriorityContention(unittest.TestCase):

    def test_three_pinned_priority_resource_and_semantic_anchors(self):
        native,_,_,service,_,obs,anchors,resource=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(anchors,(('batch',194),('clock',125),
                                  ('emission',217),('ingress',136)))
        self.assertEqual(resource,(158,296,307))
        self.assertEqual(obs.counts(),{'_admit':1,'_admit_plan':1,
                                       'offer_feedback':6})
        self.assertNotIn('__v2m_priority',execute_live_v0e.__globals__)

    def test_forward_first_fully_projects_original_native_under_tight_capacity(self):
        native,changed,projected,service,_,_,_,_=one_run(
            capacity=1,actor_priority='forward-first')
        self.assertEqual(projected,native)
        self.assertEqual(changed['forward'],native['forward'])
        self.assertEqual(service.summary()['pre_forward_actor_grants'],0)
        self.assertEqual(service.summary()['ready_forward_batches_blocked_by_pre_grants'],0)
        self.assertGreater(service.summary()['derived_control_tail_grants'],0)

    def test_actor_first_original_capacity_may_preserve_native_result(self):
        native,changed,projected,service,_,_,_,_=one_run()
        self.assertEqual(projected,native)
        self.assertEqual(changed['forward'],native['forward'])
        self.assertEqual(service.summary()['pre_forward_actor_grants'],4)
        self.assertEqual(service.summary()['ready_forward_batches_blocked_by_pre_grants'],0)

    def test_actor_first_tight_PE_capacity_causes_actual_forward_delay(self):
        native,changed,projected,service,_,_,_,_=one_run(capacity=1)
        self.assertNotEqual(projected,native)
        self.assertNotEqual(changed['forward'],native['forward'])
        self.assertEqual([x['timestamp'] for x in native['forward']['terminal']],[4,6])
        self.assertEqual([x['timestamp'] for x in changed['forward']['terminal']],[5,9])
        s=service.summary()
        self.assertEqual(s['pre_forward_actor_grants'],4)
        self.assertEqual(s['ready_forward_batches_blocked_by_pre_grants'],4)
        self.assertTrue(s['derived_preemptive_only_between_atomic_forward_batches'])

    def test_actor_first_changed_timing_still_preserves_state_and_payload(self):
        native,changed,projected,service,port,_,_,_=one_run(capacity=1)
        self.assertEqual(changed['forward']['states'],native['forward']['states'])
        self.assertEqual(changed['forward']['processed_events'],
                         native['forward']['processed_events'])
        self.assertEqual(changed['forward']['processed_batches'],
                         native['forward']['processed_batches'])
        self.assertEqual(Counter((x['node_id'],x['channel']) for x in
                                 changed['forward']['terminal']),
                         Counter((x['node_id'],x['channel']) for x in
                                 native['forward']['terminal']))
        self.assertEqual(service.summary()['derived_actor_credit_ack_count'],4)

    def test_pre_grant_booked_before_forward_in_real_derived_counters(self):
        _,changed,_,service,_,_,_,_=one_run(capacity=1)
        audit=service.resource_timeline()
        first=next(row for row in service.priority_probes()
                   if row['pre_forward_actor_control_grants']>0)
        self.assertEqual(first['service_units_before_forward'],1)
        self.assertEqual(first['memory_units_before_forward'],2)
        for row,source in zip(changed['resources']['timeline'],audit):
            with self.subTest(tick=row['tick']):
                self.assertEqual(row['pe_service_total'],source['combined_service_used'])
                self.assertEqual(row['memory_total'],source['combined_memory_used'])
                self.assertLessEqual(row['pe_service_total'],1)
                self.assertLessEqual(row['memory_total'],source['memory_budget'])
        self.assertTrue(service.summary()['within_original_native_plan_capacity'])

    def test_loss_restores_full_native_when_no_actor_control_can_be_served(self):
        native,changed,projected,service,port,_,_,_=one_run(
            capacity=1,port_options={'accept':lambda _:False})
        self.assertEqual(projected,native)
        self.assertEqual(changed,native)
        self.assertEqual(port.summary()['lost'],port.summary()['receiver_local_judgments'])
        self.assertFalse(service.credit_journal())
        self.assertEqual(service.summary()['pre_forward_actor_grants'],0)

    def test_callback_fault_is_loss_not_negative_actor_credit(self):
        def fault(_record):
            raise RuntimeError('feedback callback fault')
        native,changed,projected,service,port,_,_,_=one_run(
            capacity=1,port_options={'accept':fault})
        self.assertEqual(projected,native)
        self.assertEqual(changed,native)
        self.assertEqual(port.summary()['fault_lost'],
                         port.summary()['receiver_local_judgments'])
        self.assertEqual(service.summary()['absence_certificates'],0)

    def test_zero_actor_credit_grant_capacity_restores_full_native(self):
        native,changed,projected,service,port,_,_,_=one_run(
            capacity=1,credit_plan=ActorCreditPlanV2l(max_abs_credit=0))
        self.assertEqual(projected,native)
        self.assertEqual(changed,native)
        self.assertEqual(port.summary()['control_delivered'],4)
        self.assertEqual(service.summary()['delivered_policy_blocked_pending'],4)
        self.assertEqual(service.summary()['pre_forward_actor_grants'],0)
        self.assertEqual(service.summary()['native_operator_updates'],0)

    def test_forced_tight_horizon_rejects_actor_first_without_closed_witness(self):
        case,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        cap=LiveBVPlanV0e(max_ticks=11)
        native=execute_live_v0e(case,fabric,*plans,cap)
        self.assertEqual(len(native['resources']['timeline']),11)
        port=ReceiverPortV2h()
        service=DerivedActorPriorityV2m(port,priority='actor-first')
        derived,_,_,_=derive_priority_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,service,CallsiteObserver())
        with self.assertRaises(LiveBVRejected):
            derived(case,fabric,*plans,cap)

    def test_tampered_actor_grant_counters_refuse_resource_projection(self):
        _,result,_,service,_,_,_,_=one_run(capacity=1)
        altered={**result,'resources':dict(result['resources'])}
        altered['resources']['timeline']=[dict(r) for r in
                                         result['resources']['timeline']]
        row=next(r for r in altered['resources']['timeline']
                 if r['pe_service_total']>0)
        row['memory_total']+=1
        with self.assertRaises(NativeForkError):
            service.project_original_native_result(altered)

    def test_tampered_forward_pressure_probe_refuses_priority_summary(self):
        _,_,_,service,_,_,_,_=one_run(capacity=1)
        target=next(p for p in service._pre_probes
                    if p['pre_forward_actor_control_grants']>0)
        target['pre_forward_actor_control_grants']+=1
        with self.assertRaises(NativeForkError):
            service.summary()

    def test_invalid_priority_or_drifting_source_fails_closed(self):
        port=ReceiverPortV2h()
        with self.assertRaises(NativeForkError):
            DerivedActorPriorityV2m(port,priority='actor-after-forever')
        priority=DerivedActorPriorityV2m(port,priority='actor-first')
        with self.assertRaises(NativeForkError):
            derive_priority_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,priority,CallsiteObserver())

    def test_forged_actor_mailbox_before_priority_grant_fails_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        service=DerivedActorPriorityV2m(port,priority='actor-first')
        derived,_,_,_=derive_priority_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,service,CallsiteObserver())
        original=port.batch
        attack={'once':False}
        def evil(actor,tick,items,outputs):
            original(actor,tick,items,outputs)
            if port.judgments and not attack['once']:
                forged=replace(port.judgments[0],identity='fake-pre-credit')
                port._mailboxes.setdefault(forged.recipient,[]).append(forged)
                attack['once']=True
        port.batch=evil
        with self.assertRaises(NativeForkError):
            derived(case,fabric,*plans,LiveBVPlanV0e())

    def test_native_negative_B_remains_actor_scoped_and_not_learning(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        altered=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        native,changed,projected,service,port,_,_,_=one_run(
            capacity=1,case=altered)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(service.summary()['actor_credit_register']['A'],-2)
        self.assertEqual([a['response'] for a in service.credit_journal()],[-1,-1])
        self.assertFalse(service.summary()['native_learning_proven'])

    def test_15_recipes_tight_PE_priority_delay_preserves_functional_result(self):
        case,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        src=SOURCE.read_bytes()
        for label,recipe in RECIPES:
            with self.subTest(recipe=label):
                changed=build_workload(case,recipe)
                ctrl=LiveBVPlanV0e()
                frozen=execute_live_v0e(changed,fabric,*plans,ctrl)
                port=ReceiverPortV2h()
                service=DerivedActorPriorityV2m(port,priority='actor-first')
                derived,_,_,_=derive_priority_executor(
                    src,execute_live_v0e,port,service,CallsiteObserver())
                result=derived(changed,fabric,*plans,ctrl)
                reconstructed=service.project_original_native_result(result)
                self.assertNotEqual(reconstructed,frozen)
                self.assertEqual(result['forward']['states'],frozen['forward']['states'])
                self.assertGreater(service.summary()[
                    'ready_forward_batches_blocked_by_pre_grants'],0)

    def test_signed_v2l_predecessor_tampering_fails_closed(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2l predecessor not mounted')
        previous=json.loads(raw)
        self.assertTrue(validate_v2l(previous,raw))
        for field,value in (
            ('full_native_projection_parity_cells',44),
            ('real_frozen_native_actor_acknowledgments_proven',True),
            ('native_learning_proven',True),
        ):
            with self.subTest(field=field):
                changed=dict(previous);changed[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2l(changed,canon(changed))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2l(previous,raw+b'\n')

    def test_full_45_cell_both_regimes_pinned_priority_and_null_matrix(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2l predecessor not mounted')
        previous=json.loads(raw)
        self.assertEqual(build_report(previous,raw)['status'],CONTRACT_STATUS)
        result=experiment(previous,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        self.assertEqual(report['status'],STATUS)
        normal=report['priority_contention_totals']['original_capacity']
        tight=report['priority_contention_totals']['contended_capacity']
        self.assertEqual(normal['forward_first_v2l_journal_parity'],45)
        self.assertEqual(tight['forward_first_full_original_native_parity'],45)
        self.assertEqual(tight['actor_first_changed_forward_timing'],45)
        self.assertEqual(tight['actor_first_final_state_parity'],45)
        self.assertEqual(tight['actor_first_terminal_payload_parity'],45)
        self.assertEqual(tight['actor_first_ready_forward_PE_blocked'],162)
        self.assertEqual(tight['actor_first_acks'],156)
        self.assertEqual(tight['loss_full_native_parity'],45)
        self.assertEqual(tight['cap_zero_full_native_parity'],45)
        self.assertFalse(report['frozen_native_actor_service_or_learning_proven'])
        self.assertEqual(canon(report),canon(json.loads(canon(report))))


if __name__=='__main__':
    unittest.main()
