"""BV v2o: native-causally-ready veto, full native parity and discrimination."""
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
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    CausalAdmissionPlanV2o,DerivedCausalAdmissionV2o,derive_causal_executor,
)
from spk_bv_research.native_causal_admission_integration_v2o import (
    validate_v2n,build_report,CONTRACT_STATUS,MODES,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2n-actor-forward-fairness.json'),
         ROOT/'spk-bv-v2n-actor-forward-fairness.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2N_REPORT')
    for p in ([Path(configured)] if configured else [])+list(REPORTS):
        if p.is_file():
            return p.read_bytes()
    return None


def one_run(*,capacity=1,forward=True,bv_guard=True,case=None,
            control=None,options=None,credit=None,service_plan=None):
    basic,fabric,plans=fixture()
    selected=basic if case is None else case
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    ctrl=LiveBVPlanV0e() if control is None else control
    port=ReceiverPortV2h(**(options or {}))
    service=DerivedCausalAdmissionV2o(port,
        admission_plan=CausalAdmissionPlanV2o(forward,bv_guard),
        credit_plan=credit or ActorCreditPlanV2l(),
        service_plan=service_plan or ShadowServicePlanV2j())
    observer=CallsiteObserver()
    derived,_,semantic,resource=derive_causal_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,service,observer)
    native=execute_live_v0e(selected,fabric,*plans,ctrl)
    integrated=derived(selected,fabric,*plans,ctrl)
    projected=service.project_original_native_result(integrated)
    return native,integrated,projected,service,port,observer,semantic,resource


class TestV2oNativeCausalAdmission(unittest.TestCase):

    def test_source_pinned_three_priority_resource_semantic_anchors(self):
        original,derived,_,s,_,obs,semantic,resource=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(semantic,(('batch',194),('clock',125),
                                   ('emission',217),('ingress',136)))
        self.assertEqual(resource,(158,296,307))
        self.assertEqual(obs.counts()['_admit'],1)
        self.assertEqual(obs.counts()['_admit_plan'],1)
        self.assertNotIn('__v2o_causal_admission',execute_live_v0e.__globals__)
        self.assertEqual(derived['schema'],original['schema'])

    def test_strict_under_tight_capacity_projects_entire_native(self):
        native,result,projection,s,port,_,_,_=one_run()
        self.assertEqual(projection,native)
        self.assertEqual(result['forward'],native['forward'])
        self.assertEqual(result['feedback'],native['feedback'])
        self.assertGreater(s.summary()['pre_forward_actor_grants'],0)
        self.assertEqual(s.summary()['pregrants_during_native_causal_veto'],0)
        self.assertEqual(s.summary()['unconsumed_delivered_controls'],0)
        self.assertFalse(s.summary()['frozen_native_actor_intake_observed'])

    def test_strict_original_capacity_source_parity(self):
        native,result,projection,s,_,_,_,_=one_run(capacity=3)
        self.assertEqual(projection,native)
        self.assertEqual(result['forward'],native['forward'])
        self.assertEqual(result['feedback'],native['feedback'])
        self.assertGreater(s.summary()['pre_forward_actor_grants'],0)

    def test_both_native_forward_and_feedback_guards_are_necessary_under_bound(self):
        native,_,_,_,_,_,_,_=one_run()
        self.assertEqual(len(native['resources']['timeline']),11)
        case,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        horizon=LiveBVPlanV0e(max_ticks=11)
        for name,forward,bv in MODES:
            with self.subTest(admission=name):
                port=ReceiverPortV2h()
                service=DerivedCausalAdmissionV2o(port,
                    admission_plan=CausalAdmissionPlanV2o(forward,bv))
                executor,_,_,_=derive_causal_executor(
                    SOURCE.read_bytes(),execute_live_v0e,port,service,
                    CallsiteObserver())
                if forward and bv:
                    result=executor(case,fabric,*plans,horizon)
                    self.assertEqual(service.project_original_native_result(result),
                                     execute_live_v0e(case,fabric,*plans,horizon))
                    self.assertGreater(service.summary()['pre_forward_actor_grants'],0)
                else:
                    with self.assertRaisesRegex(LiveBVRejected,
                                                'bounded live logical horizon'):
                        executor(case,fabric,*plans,horizon)

    def test_one_sided_ablation_full_native_parity_fails_even_if_terminals_match(self):
        native,a,pa,sa,_,_,_,_=one_run(forward=True,bv_guard=False)
        _,b,pb,sb,_,_,_,_=one_run(forward=False,bv_guard=True)
        self.assertNotEqual(pa,native)
        self.assertNotEqual(pb,native)
        self.assertEqual([x['timestamp'] for x in a['forward']['terminal']],
                         [x['timestamp'] for x in native['forward']['terminal']])
        self.assertNotEqual(b['forward'],native['forward'])
        self.assertGreater(sa.summary()['native_forward_veto_ticks'],0)
        self.assertGreater(sb.summary()['native_feedback_veto_ticks'],0)

    def test_null_guard_replays_full_actor_first_v2m(self):
        native,derived,projected,s,_,_,_,_=one_run(
            forward=False,bv_guard=False)
        self.assertNotEqual(projected,native)
        self.assertEqual([x['timestamp'] for x in derived['forward']['terminal']],[5,9])
        self.assertEqual(s.summary()['native_causal_priority_veto_ticks'],0)
        self.assertEqual(s.summary()['pre_forward_actor_grants'],4)

    def test_native_causal_ready_feedback_is_an_independent_gate(self):
        _,_,_,s,_,_,_,_=one_run()
        probes=s.admission_probes()
        both=[p for p in probes if p['ready_native_feedback_packets_before_actor_admission']
              and p['ready_forward_batches_before_actor_admission']]
        feedback_only=[p for p in probes if p[
            'ready_native_feedback_packets_before_actor_admission'] and not p[
                'ready_forward_batches_before_actor_admission']]
        self.assertGreater(len(feedback_only),0)
        self.assertTrue(all(p['native_causal_priority_veto'] for p in feedback_only))
        self.assertEqual(s.summary()['pregrants_during_native_causal_veto'],0)

    def test_actor_credit_journal_exactly_once_and_resource_charged(self):
        _,result,_,s,port,_,_,_=one_run()
        acks=s.credit_journal()
        self.assertEqual(len(acks),s.summary()['derived_resource_grants_committed'])
        self.assertEqual(len(acks),len({a['judgment_id'] for a in acks}))
        self.assertEqual(len(acks),port.summary()['control_delivered'])
        self.assertTrue(s.summary()['within_original_native_plan_capacity'])
        self.assertEqual(s.summary()['native_operator_updates'],0)
        self.assertFalse(s.summary()['native_learning_proven'])

    def test_causal_null_transport_loss_restores_original_native(self):
        native,result,projection,s,port,_,_,_=one_run(
            options={'accept':lambda _:False})
        self.assertEqual(result,native)
        self.assertEqual(projection,native)
        self.assertFalse(s.credit_journal())
        self.assertEqual(s.summary()['pre_forward_actor_grants'],0)
        self.assertEqual(port.summary()['absence_certificates'],0)

    def test_causal_null_callback_fault_is_not_negative_credit(self):
        def fault(_x):
            raise RuntimeError('v2o expected callback rejection')
        native,result,projection,s,port,_,_,_=one_run(options={'accept':fault})
        self.assertEqual(result,native)
        self.assertEqual(projection,native)
        self.assertEqual(port.summary()['negative_judgments'],0)
        self.assertEqual(port.summary()['fault_lost'],
                         port.summary()['receiver_local_judgments'])

    def test_zero_credit_policy_delivers_but_never_services(self):
        native,result,projection,s,port,_,_,_=one_run(
            credit=ActorCreditPlanV2l(max_abs_credit=0))
        self.assertEqual(result,native)
        self.assertEqual(projection,native)
        self.assertGreater(port.summary()['control_delivered'],0)
        self.assertEqual(s.summary()['delivered_policy_blocked_pending'],
                         port.summary()['control_delivered'])
        self.assertFalse(s.credit_journal())

    def test_real_negative_B_control_still_scoped_to_A(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(
            replace(n,instructions=block) if n.node_id=='B' else n
            for n in case.nodes))
        native,result,projection,s,port,_,_,_=one_run(case=changed)
        self.assertEqual(projection,native)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual([ack['response'] for ack in s.credit_journal()],[-1,-1])
        self.assertEqual(s.summary()['actor_credit_register']['A'],-2)
        self.assertFalse(s.summary()['native_learning_proven'])

    def test_forged_actor_control_mailbox_before_native_veto_fails_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        service=DerivedCausalAdmissionV2o(port)
        derived,_,_,_=derive_causal_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,service,CallsiteObserver())
        regular_batch=port.batch
        injected=[False]
        def forged(actor,tick,items,outputs):
            regular_batch(actor,tick,items,outputs)
            if port.judgments and not injected[0]:
                port._mailboxes.setdefault(port.judgments[0].recipient,[]).append(
                    replace(port.judgments[0],identity='forged-native-v2o-control'))
                injected[0]=True
        port.batch=forged
        with self.assertRaises(NativeForkError):
            derived(case,fabric,*plans,LiveBVPlanV0e())

    def test_admission_trace_and_resource_counter_tampering_fails_closed(self):
        _,result,_,s,_,_,_,_=one_run()
        native_ready=next(x for x in s._admission_probes
                          if x['native_feedback_priority_veto'])
        native_ready['ready_native_feedback_packets_before_actor_admission']=0
        with self.assertRaises(NativeForkError):
            s.summary()
        _,result,_,s,_,_,_,_=one_run()
        modified={**result,'resources':dict(result['resources'])}
        modified['resources']['timeline']=[dict(x) for x in
                                          result['resources']['timeline']]
        modified['resources']['timeline'][0]['forward_computations']+=1
        with self.assertRaises(NativeForkError):
            s.project_original_native_result(modified)

    def test_invalid_plan_wrong_adapter_and_source_drift_fail_closed(self):
        for plan in (CausalAdmissionPlanV2o(1,True),
                     CausalAdmissionPlanV2o(True,'yes')):
            with self.subTest(plan=plan),self.assertRaises(NativeForkError):
                DerivedCausalAdmissionV2o(ReceiverPortV2h(),admission_plan=plan)
        port=ReceiverPortV2h()
        service=DerivedCausalAdmissionV2o(port)
        with self.assertRaises(NativeForkError):
            derive_causal_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,service,CallsiteObserver())
        with self.assertRaises(NativeForkError):
            derive_causal_executor(SOURCE.read_bytes(),execute_live_v0e,port,
                object(),CallsiteObserver())

    def test_15_organic_recipes_strict_full_native_resource_projection(self):
        basic,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        source=SOURCE.read_bytes()
        for label,recipe in RECIPES:
            with self.subTest(recipe=label):
                changed=build_workload(basic,recipe)
                native=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                port=ReceiverPortV2h()
                service=DerivedCausalAdmissionV2o(port)
                derived,_,_,_=derive_causal_executor(source,execute_live_v0e,
                                                    port,service,CallsiteObserver())
                result=derived(changed,fabric,*plans,LiveBVPlanV0e())
                self.assertEqual(service.project_original_native_result(result),native)
                self.assertEqual(result['feedback'],native['feedback'])

    def test_signed_v2n_predecessor_mutations_refused(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2n predecessor not mounted')
        previous=json.loads(raw)
        self.assertTrue(validate_v2n(previous,raw))
        self.assertEqual(build_report(previous,raw)['status'],CONTRACT_STATUS)
        for field,value in (
            ('new_derived_fairness_window_runs',269),
            ('native_actor_credit_admission_proven',True),
            ('universal_forward_liveness_proven',True),
            ('native_operator_updates',1),
        ):
            with self.subTest(field=field):
                changed=dict(previous);changed[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2n(changed,canon(changed))


if __name__=='__main__':
    unittest.main()
