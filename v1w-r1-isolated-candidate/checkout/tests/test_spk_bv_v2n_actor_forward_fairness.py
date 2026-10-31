"""BV v2n: falsifiable fair forward opportunity, strict causal actor custody."""
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
from spk_backvalidation_v2.derived_actor_priority_v2m import (
    DerivedActorPriorityV2m,derive_priority_executor,
)
from spk_backvalidation_v2.derived_actor_fairness_v2n import (
    FairnessPlanV2n,DerivedActorFairnessV2n,derive_fair_executor,
)
from spk_bv_research.actor_forward_fairness_integration_v2n import (
    validate_v2m,build_report,STATUS,CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2m-actor-priority-contention.json'),
         ROOT/'spk-bv-v2m-actor-priority-contention.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2M_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,window=1,capacity=1,case=None,options=None,
            credit_plan=None,service_plan=None,bv=None,reserve=1):
    original,fabric,plans=fixture()
    selected=original if case is None else case
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    plan=LiveBVPlanV0e() if bv is None else bv
    port=ReceiverPortV2h(**(options or {}))
    service=DerivedActorFairnessV2n(port,
        fairness_plan=FairnessPlanV2n(window,reserve),
        credit_plan=credit_plan or ActorCreditPlanV2l(),
        service_plan=service_plan or ShadowServicePlanV2j())
    observer=CallsiteObserver()
    executor,_,semantic,resource=derive_fair_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,service,observer)
    native=execute_live_v0e(selected,fabric,*plans,plan)
    integrated=executor(selected,fabric,*plans,plan)
    projected=service.project_original_native_result(integrated)
    return native,integrated,projected,service,port,observer,semantic,resource


class TestV2nActorForwardFairness(unittest.TestCase):

    def test_exact_source_pins_and_native_is_not_rebound(self):
        n,r,_,s,_,obs,semantic,resource=one_run(window=0)
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(semantic,(('batch',194),('clock',125),
                                   ('emission',217),('ingress',136)))
        self.assertEqual(resource,(158,296,307))
        self.assertEqual(obs.counts()['_admit'],1)
        self.assertEqual(obs.counts()['_admit_plan'],1)
        self.assertNotIn('__v2m_priority',execute_live_v0e.__globals__)
        self.assertNotIn('__v2k_admission',execute_live_v0e.__globals__)
        self.assertEqual(r['schema'],n['schema'])

    def test_budget_protection_never_spends_reserved_pe(self):
        for window in (0,1,2,16):
            with self.subTest(window=window):
                _,_,_,service,_,_,_,_=one_run(window=window)
                probes=service.fairness_probes()
                protected=[p for p in probes if p['protected_forward_opportunity']]
                if window==0:
                    self.assertGreater(len(protected),0)
                self.assertTrue(all(p['actor_pregrants']==0 for p in protected))
                self.assertTrue(all(p['actor_streak_after']<=window for p in probes))
                summary=service.summary()
                self.assertEqual(summary['protected_forward_opportunity_ticks'],
                                 len(protected))
                self.assertTrue(summary['within_original_native_plan_capacity'])

    def test_full_actor_credit_journal_still_exactly_once(self):
        n,r,_,service,port,_,_,_=one_run(window=0)
        summary=service.summary()
        journal=service.credit_journal()
        self.assertEqual(summary['derived_actor_credit_ack_count'],len(journal))
        self.assertEqual(summary['derived_resource_grants_committed'],len(journal))
        self.assertEqual(len(set(a['judgment_id'] for a in journal)),len(journal))
        self.assertEqual(summary['delivered_controls'],
                         len(journal)+summary['unconsumed_delivered_controls'])
        self.assertEqual(summary['native_operator_updates'],0)
        self.assertFalse(summary['native_learning_proven'])
        self.assertFalse(summary['frozen_native_actor_intake_observed'])
        self.assertEqual(r['forward']['states'],n['forward']['states'])

    def test_zero_window_preserves_reference_terminal_ticks_not_native_resources(self):
        native,changed,projection,service,_,_,_,_=one_run(window=0)
        self.assertEqual([e['timestamp'] for e in native['forward']['terminal']],[4,6])
        self.assertEqual([e['timestamp'] for e in changed['forward']['terminal']],[4,6])
        self.assertNotEqual(projection,native)  # reservation != full native replay
        self.assertGreater(service.summary()['protected_forward_opportunity_ticks'],0)

    def test_long_window_recovers_v2m_actor_first_contention(self):
        native,result,projection,service,_,_,_,_=one_run(window=16)
        self.assertEqual([e['timestamp'] for e in result['forward']['terminal']],[5,9])
        self.assertEqual(service.summary()['pre_forward_actor_grants'],4)
        self.assertEqual(service.summary()['ready_forward_batches_blocked_by_pre_grants'],4)
        self.assertEqual(service.summary()['protected_forward_opportunity_ticks'],0)
        self.assertNotEqual(projection,native)

    def test_one_actor_window_distinct_from_always_reservation(self):
        _,a,_,sa,_,_,_,_=one_run(window=0)
        _,b,_,sb,_,_,_,_=one_run(window=1)
        self.assertNotEqual(a['forward'],b['forward'])
        self.assertGreater(sb.summary()['ready_forward_batches_blocked_by_pre_grants'],
                           sa.summary()['ready_forward_batches_blocked_by_pre_grants'])

    def test_fairness_not_a_bounded_completion_certificate(self):
        case,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        bound=LiveBVPlanV0e(max_ticks=11)
        native=execute_live_v0e(case,fabric,*plans,bound)
        self.assertEqual(len(native['resources']['timeline']),11)
        port=ReceiverPortV2h()
        fair=DerivedActorFairnessV2n(port,fairness_plan=FairnessPlanV2n(0))
        executor,_,_,_=derive_fair_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,fair,CallsiteObserver())
        with self.assertRaisesRegex(LiveBVRejected,'bounded live logical horizon'):
            executor(case,fabric,*plans,bound)

    def test_causal_null_loss_and_callback_fault_project_exact_native(self):
        for opts in ({'accept':lambda _:False},
                     {'accept':lambda _:(_ for _ in ()).throw(RuntimeError('fault'))}):
            with self.subTest(options=opts):
                native,changed,projected,service,port,_,_,_=one_run(
                    window=1,options=opts)
                self.assertEqual(projected,native)
                self.assertEqual(changed,native)
                self.assertFalse(service.credit_journal())
                self.assertEqual(service.summary()['pre_forward_actor_grants'],0)
                self.assertEqual(port.summary()['absence_certificates'],0)

    def test_zero_credit_withholds_without_negative_judgment(self):
        native,changed,projected,service,port,_,_,_=one_run(
            credit_plan=ActorCreditPlanV2l(max_abs_credit=0))
        self.assertEqual(projected,native)
        self.assertEqual(changed,native)
        self.assertGreater(port.summary()['control_delivered'],0)
        self.assertFalse(service.credit_journal())
        self.assertEqual(service.summary()['delivered_policy_blocked_pending'],
                         port.summary()['control_delivered'])
        self.assertEqual(port.summary()['absence_certificates'],0)

    def test_service_quota_with_no_tail_is_not_silence_proof(self):
        _,_,_,service,port,_,_,_=one_run(
            window=0,service_plan=ShadowServicePlanV2j(
                max_tail_ticks=0,max_total_receipts=1))
        summary=service.summary()
        self.assertEqual(summary['derived_control_tail_grants'],0)
        self.assertGreater(summary['unconsumed_delivered_controls'],0)
        self.assertEqual(port.summary()['absence_certificates'],0)

    def test_negative_B_actual_credit_stays_actor_scoped(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        case=replace(case,nodes=tuple(replace(node,instructions=block)
            if node.node_id=='B' else node for node in case.nodes))
        _,_,_,service,port,_,_,_=one_run(case=case,window=0)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual([a['response'] for a in service.credit_journal()],[-1,-1])
        self.assertEqual(service.summary()['actor_credit_register']['A'],-2)
        self.assertFalse(service.summary()['native_learning_proven'])

    def test_forged_mailbox_record_before_protection_fails_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        service=DerivedActorFairnessV2n(port)
        derived,_,_,_=derive_fair_executor(SOURCE.read_bytes(),execute_live_v0e,
                                          port,service,CallsiteObserver())
        normal_batch=port.batch
        injected=[False]
        def attack(actor,tick,items,outputs):
            normal_batch(actor,tick,items,outputs)
            if port.judgments and not injected[0]:
                port._mailboxes.setdefault(port.judgments[0].recipient,[]).append(
                    replace(port.judgments[0],identity='forged-v2n-mailbox'))
                injected[0]=True
        port.batch=attack
        with self.assertRaises(NativeForkError):
            derived(case,fabric,*plans,LiveBVPlanV0e())

    def test_resource_counter_and_fairness_probe_tampering_rejected(self):
        _,result,_,service,_,_,_,_=one_run(window=0)
        altered={**result,'resources':dict(result['resources'])}
        altered['resources']['timeline']=[dict(r) for r in
                                         result['resources']['timeline']]
        row=next(x for x in altered['resources']['timeline']
                 if x['pe_service_total']>0)
        row['memory_total']+=1
        with self.assertRaises(NativeForkError):
            service.project_original_native_result(altered)
        altered2={**result,'resources':dict(result['resources'])}
        altered2['resources']['timeline']=[dict(r) for r in
                                          result['resources']['timeline']]
        altered2['resources']['timeline'][0]['forward_computations']+=1
        with self.assertRaises(NativeForkError):
            service.project_original_native_result(altered2)
        protected=next(x for x in service._fair_probes
                       if x['protected_forward_opportunity'])
        protected['control_pregrant_allowance']+=1
        with self.assertRaises(NativeForkError):
            service.summary()

    def test_invalid_plans_and_drifting_source_fail_closed(self):
        for plan in (FairnessPlanV2n(-1),FairnessPlanV2n(17),
                     FairnessPlanV2n(True),FairnessPlanV2n(0,0),
                     FairnessPlanV2n(0,17)):
            with self.subTest(plan=plan),self.assertRaises(NativeForkError):
                DerivedActorFairnessV2n(ReceiverPortV2h(),fairness_plan=plan)
        with self.assertRaises(NativeForkError):
            one_run(window=0,capacity=1,reserve=2)
        port=ReceiverPortV2h()
        service=DerivedActorFairnessV2n(port)
        with self.assertRaises(NativeForkError):
            derive_fair_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,service,CallsiteObserver())
        with self.assertRaises(NativeForkError):
            derive_fair_executor(SOURCE.read_bytes(),execute_live_v0e,
                port,DerivedActorPriorityV2m(port,priority='actor-first'),
                CallsiteObserver())

    def test_15_recipes_actor_fairness_keeps_functional_payload(self):
        basic,fabric,plans=fixture()
        plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
               plans[2],plans[3])
        for label,recipe in RECIPES:
            with self.subTest(recipe=label):
                case=build_workload(basic,recipe)
                native=execute_live_v0e(case,fabric,*plans,LiveBVPlanV0e())
                port=ReceiverPortV2h()
                service=DerivedActorFairnessV2n(port)
                derived,_,_,_=derive_fair_executor(SOURCE.read_bytes(),
                    execute_live_v0e,port,service,CallsiteObserver())
                result=derived(case,fabric,*plans,LiveBVPlanV0e())
                service.project_original_native_result(result)
                self.assertEqual(result['forward']['states'],native['forward']['states'])
                self.assertEqual(result['forward']['processed_batches'],
                                 native['forward']['processed_batches'])
                self.assertEqual(Counter((x['node_id'],x['channel'])
                    for x in result['forward']['terminal']),
                    Counter((x['node_id'],x['channel'])
                    for x in native['forward']['terminal']))

    def test_signed_v2m_predecessor_and_claim_mutations_fail_closed(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2m predecessor not mounted')
        previous=json.loads(raw)
        self.assertTrue(validate_v2m(previous,raw))
        contract=build_report(previous,raw)
        self.assertEqual(contract['status'],CONTRACT_STATUS)
        for field,value in (
            ('new_derived_actor_first_runs',90),
            ('native_forward_timing_full_parity_under_actor_first_claimed',True),
            ('frozen_native_actor_service_or_learning_proven',True),
            ('native_operator_updates',1),
        ):
            with self.subTest(field=field):
                tampered=dict(previous);tampered[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2m(tampered,canon(tampered))


if __name__=='__main__':
    unittest.main()
