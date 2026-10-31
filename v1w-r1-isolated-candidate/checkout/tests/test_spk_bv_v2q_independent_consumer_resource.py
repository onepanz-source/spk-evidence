"""BV v2q: independently budgeted actor consumer PE/memory and projection."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e,LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,NativeForkError,PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_resource_consumer_v2q import (
    ConsumerResourcePlanV2q,DerivedActorResourceConsumerV2q,
    derive_resource_consumer_executor,_resource_charge_digest,
)
from spk_bv_research.actor_resource_consumer_integration_v2q import (
    PREDECESSOR_SHA,CONTRACT_STATUS,STATUS,validate_v2p,build_report,experiment,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2p-actor-consumer-handoff.json'),
         ROOT.parent.parent/'spk-bv-v2p-actor-consumer-handoff.json',
         ROOT/'spk-bv-v2p-actor-consumer-handoff.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2P_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,capacity=1,resource_plan=None,case=None,receiver=None):
    base,fabric,plans=fixture()
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    port=ReceiverPortV2h(**(receiver or {}))
    consumer=DerivedActorResourceConsumerV2q(
        port,resource_plan=resource_plan or ConsumerResourcePlanV2q())
    observer=CallsiteObserver()
    compiled,_,semantic,resources=derive_resource_consumer_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,consumer,observer)
    chosen=base if case is None else case
    native=execute_live_v0e(chosen,fabric,*plans,LiveBVPlanV0e())
    derived=compiled(chosen,fabric,*plans,LiveBVPlanV0e())
    projected=consumer.project_original_native_result(derived)
    return native,derived,projected,consumer,port,observer,semantic,resources


class TestV2qIndependentActorResource(unittest.TestCase):

    def test_pinned_native_source_and_resource_semantic_anchors(self):
        native,derived,projected,s,_,obs,semantic,anchors=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(projected,native)
        self.assertEqual(derived['forward'],native['forward'])
        self.assertEqual(semantic,(('batch',194),('clock',125),
                                   ('emission',217),('ingress',136)))
        self.assertEqual(anchors,(158,296,307))
        self.assertEqual(obs.counts()['_admit'],1)
        self.assertNotIn('__v2k_admission',execute_live_v0e.__globals__)
        self.assertNotIn('__v2o_causal_admission',execute_live_v0e.__globals__)
        self.assertFalse(s.summary()['frozen_native_actor_consumer_changed'])

    def test_ACK_and_consumer_own_PE_memory_both_accounted(self):
        native,derived,projected,s,_,_,_,_=one_run()
        self.assertEqual(projected,native)
        self.assertNotEqual(derived['resources']['timeline'],
                            native['resources']['timeline'])
        self.assertEqual(len(s.credit_journal()),4)
        self.assertEqual(len(s.consumer_journal()),4)
        self.assertEqual(len(s.resource_charge_journal()),4)
        self.assertEqual(s.summary()['derived_committed_pe_service_units'],4)
        self.assertEqual(s.summary()['derived_independent_consumer_PE_units'],4)
        self.assertEqual(s.summary()['derived_independent_consumer_memory_units'],8)
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],0)
        self.assertTrue(s.audit_resource_consumer())

    def test_cost_is_in_actual_derived_counters_not_shadow_only(self):
        _,result,_,s,_,_,_,_=one_run(capacity=3)
        normal_rows=result['resources']['timeline'][:s._original_native_rows]
        inline=[c for c in s.resource_charge_journal()
                if c['resource_phase']=='after-native-forward']
        self.assertGreater(len(inline),0)
        for charge in inline:
            derived_row=next(row for row in normal_rows
                             if row['tick']==charge['resource_tick'])
            frame=next(x for x in s.resource_charge_trace()
                       if x['tick']==charge['resource_tick'])
            self.assertEqual(derived_row['pe_service_total'],
                             frame['after']['pe_service_total'])
            self.assertEqual(derived_row['memory_total'],
                             frame['after']['memory_total'])
            self.assertEqual(frame['after']['pe_service_total'],
                             frame['before']['pe_service_total']+frame['grants'])

    def test_15_native_recipes_in_two_resource_capacity_regimes(self):
        case,_,_=fixture()
        for label,recipe in RECIPES:
            for cap in (1,3):
                with self.subTest(label=label,capacity=cap):
                    native,result,projected,s,_,_,_,_=one_run(
                        capacity=cap,case=build_workload(case,recipe))
                    self.assertEqual(projected,native)
                    self.assertEqual(result['forward'],native['forward'])
                    self.assertEqual(result['feedback'],native['feedback'])
                    self.assertEqual(len(s.credit_journal()),
                                     len(s.resource_charge_journal()))

    def test_tight_one_slot_PE_capacity_requires_paid_consumer_tail(self):
        native,result,projected,s,_,_,_,_=one_run(capacity=1)
        self.assertEqual(projected,native)
        self.assertEqual(s.summary()['consumer_independent_inline_charges'],0)
        self.assertEqual(s.summary()['consumer_independent_tail_charges'],4)
        self.assertEqual(s.summary()['new_consumer_only_resource_timeline_rows'],4)
        self.assertGreater(s.summary()['consumer_resource_capacity_rejections'],0)
        self.assertTrue(all(row['pe_service_total']==1
                            for row in result['resources']['timeline'][-4:]))

    def test_global_independent_charge_quota_one_without_ACK_loss(self):
        native,_,projected,s,_,_,_,_=one_run(resource_plan=
            ConsumerResourcePlanV2q(max_total_consumer_charges=1))
        self.assertEqual(projected,native)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertEqual(len(s.resource_charge_journal()),1)
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],3)

    def test_charge_quota_zero_forbids_applications_without_silence_claim(self):
        native,_,projected,s,port,_,_,_=one_run(resource_plan=
            ConsumerResourcePlanV2q(max_total_consumer_charges=0))
        self.assertEqual(projected,native)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertFalse(s.resource_charge_journal())
        self.assertFalse(s.consumer_journal())
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)
        self.assertEqual(port.summary()['absence_certificates'],0)
        self.assertEqual(s.summary()['new_consumer_only_resource_timeline_rows'],0)

    def test_explicit_zero_memory_budget_preserves_all_ACKs_pending(self):
        native,_,projected,s,_,_,_,_=one_run(resource_plan=
            ConsumerResourcePlanV2q(max_consumer_memory_per_tick=0))
        self.assertEqual(projected,native)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertEqual(len(s.consumer_journal()),0)
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)
        self.assertEqual(s.summary()['consumer_extra_tail_ticks'],0)

    def test_no_paid_consumer_tail_under_tight_capacity_defers_all(self):
        native,_,projected,s,_,_,_,_=one_run(capacity=1,resource_plan=
            ConsumerResourcePlanV2q(max_resource_tail_ticks=0))
        self.assertEqual(projected,native)
        self.assertFalse(s.resource_charge_journal())
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)

    def test_loss_and_callback_fault_never_allocate_consumer_resources(self):
        def fault(_):
            raise RuntimeError('expected v2q transport callback failure')
        for receiver in ({'accept':lambda _:False},{'accept':fault}):
            with self.subTest(receiver=str(receiver)):
                native,_,projection,s,port,_,_,_=one_run(receiver=receiver)
                self.assertEqual(native,projection)
                self.assertFalse(s.credit_journal())
                self.assertFalse(s.resource_charge_journal())
                self.assertEqual(port.summary()['negative_judgments'],0)

    def test_real_negative_B_applied_to_A_and_paid_twice(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(replace(node,instructions=block)
                        if node.node_id=='B' else node for node in case.nodes))
        native,_,projection,s,port,_,_,_=one_run(capacity=1,case=changed)
        self.assertEqual(native,projection)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual([r['actor'] for r in s.resource_charge_journal()],['A','A'])
        self.assertEqual(s.summary()['actor_consumer_applied_credit']['A'],-2)
        self.assertEqual(s.summary()['derived_independent_consumer_memory_units'],4)
        self.assertFalse(s.summary()['native_learning_proven'])

    def test_charge_chain_spoof_replay_and_wrong_ownership_fail_closed(self):
        for change in ({'actor':'B'},{'owner_pe':'FAKE'},
                       {'ack_digest':'f'*64},
                       {'consumer_receipt_digest':'f'*64},
                       {'prior_charge_digest':'f'*64},
                       {'pe_service_units':0},
                       {'memory_units':0},
                       {'resource_tick':200}):
            with self.subTest(change=change):
                _,result,_,s,_,_,_,_=one_run()
                s._consumer_resource_charges[0]=replace(
                    s._consumer_resource_charges[0],**change)
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_rehashed_resource_charge_fails_due_to_prior_root(self):
        _,_,_,s,_,_,_,_=one_run()
        bad=replace(s._consumer_resource_charges[0],resource_tick=500)
        s._consumer_resource_charges[0]=replace(
            bad,charge_digest=_resource_charge_digest(bad))
        with self.assertRaises(NativeForkError):
            s.audit_resource_consumer()

    def test_resource_trace_source_budget_and_pressure_tampering_refused(self):
        for key,value in (('source_PE_budget',99),
                          ('source_memory_budget',99),
                          ('reject_reason','forged'),
                          ('grants',99)):
            with self.subTest(key=key):
                _,_,_,s,_,_,_,_=one_run()
                s._resource_charge_trace[-1][key]=value
                with self.assertRaises(NativeForkError):
                    s.audit_resource_consumer()

    def test_resource_counter_unaccounted_inline_mutation_refuses_native_projection(self):
        _,derived,_,s,_,_,_,_=one_run(capacity=3)
        row=next(row for row in derived['resources']['timeline']
                 if row['tick']==next(t['tick'] for t in s.resource_charge_trace()
                                      if t['phase']=='after-native-forward' and t['grants']))
        row['pe_service_total']+=1
        with self.assertRaises(NativeForkError):
            s.project_original_native_result(derived)

    def test_resource_tail_counter_and_timeline_forgery_refuses_projection(self):
        _,derived,_,s,_,_,_,_=one_run()
        derived['resources']['timeline'][-1]['memory_total']+=2
        with self.assertRaises(NativeForkError):
            s.project_original_native_result(derived)

    def test_invalid_resource_policy_and_pinned_source_drift(self):
        for bad in (ConsumerResourcePlanV2q(max_total_consumer_charges=-1),
                    ConsumerResourcePlanV2q(max_consumer_service_per_tick=17),
                    ConsumerResourcePlanV2q(max_resource_tail_ticks=129),
                    ConsumerResourcePlanV2q(max_consumer_memory_per_tick=33),
                    ConsumerResourcePlanV2q(max_consumer_memory_per_tick=True)):
            with self.subTest(bad=bad):
                with self.assertRaises(NativeForkError):
                    DerivedActorResourceConsumerV2q(ReceiverPortV2h(),
                                                    resource_plan=bad)
        port=ReceiverPortV2h()
        service=DerivedActorResourceConsumerV2q(port)
        drift=SOURCE.read_bytes().replace(b'while True:',b'while False:',1)
        with self.assertRaises(NativeForkError):
            derive_resource_consumer_executor(drift,execute_live_v0e,port,
                                              service,CallsiteObserver())

    def test_signed_predecessor_mutation_and_contract_only_fail_closed(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2p predecessor unavailable')
        predecessor=json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(),PREDECESSOR_SHA)
        self.assertTrue(validate_v2p(predecessor,raw))
        contract=build_report(predecessor,raw)
        self.assertEqual(contract['status'],CONTRACT_STATUS)
        self.assertFalse(contract['frozen_native_actor_resource_consumption_proven'])
        tampered=json.loads(raw)
        tampered['consumer_handoff_totals']['contended_capacity']['acked']=999
        with self.assertRaises(ValueError):
            build_report(tampered,canon(tampered))
        with self.assertRaises(ValueError):
            build_report(predecessor,raw+b' ')

    def test_full_pinned_45_by_two_resource_matrix_and_canonical_report(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2p predecessor unavailable')
        previous=json.loads(raw)
        result=experiment(previous,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['new_native_runs'],90)
        self.assertEqual(report['new_resource_charged_normal_runs'],90)
        self.assertEqual(report['new_resource_backpressure_intervention_runs'],180)
        for regime in report['independently_charged_consumer_totals'].values():
            self.assertEqual(regime['native_projection'],45)
            self.assertEqual(regime['independent_PE_units'],156)
            self.assertEqual(regime['independent_memory_units'],312)
        self.assertEqual(report['independently_charged_consumer_totals'][
            'contended_capacity']['native_tick_paid'],0)
        self.assertEqual(report['resource_backpressure_intervention_totals'][
            'memory_zero']['pending_backlog'],156)
        self.assertEqual(json.loads(canon(report)),report)


if __name__=='__main__':
    unittest.main()
