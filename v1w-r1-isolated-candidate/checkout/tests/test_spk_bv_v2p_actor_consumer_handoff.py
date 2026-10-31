"""BV v2p adversarial tests: ACK custody is separate from applied actor credit."""
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
from spk_backvalidation_v2.derived_actor_consumer_v2p import (
    ActorConsumerPlanV2p,DerivedActorConsumerV2p,derive_consumer_executor,
    _consume_digest,
)
from spk_bv_research.actor_consumer_handoff_integration_v2p import (
    PREDECESSOR_SHA,CONTRACT_STATUS,STATUS,validate_v2o,build_report,experiment,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2o-native-causal-admission.json'),
         ROOT.parent.parent/'spk-bv-v2o-native-causal-admission.json',
         ROOT/'spk-bv-v2o-native-causal-admission.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2O_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,capacity=1,plan=None,case=None,receiver=None,control=None):
    base,fabric,plans=fixture()
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    port=ReceiverPortV2h(**(receiver or {}))
    consumer=DerivedActorConsumerV2p(port,consumer_plan=plan or ActorConsumerPlanV2p())
    observer=CallsiteObserver()
    derived,_,semantic,resources=derive_consumer_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,consumer,observer)
    chosen=base if case is None else case
    ctrl=LiveBVPlanV0e() if control is None else control
    native=execute_live_v0e(chosen,fabric,*plans,ctrl)
    integrated=derived(chosen,fabric,*plans,ctrl)
    projected=consumer.project_original_native_result(integrated)
    return native,integrated,projected,consumer,port,observer,semantic,resources


class TestV2pActorConsumerHandoff(unittest.TestCase):

    def test_source_unchanged_and_native_causal_hooks(self):
        native,derived,projected,s,_,obs,semantic,resources=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(projected,native)
        self.assertEqual(derived['forward'],native['forward'])
        self.assertEqual(semantic,(('batch',194),('clock',125),
                                   ('emission',217),('ingress',136)))
        self.assertEqual(resources,(158,296,307))
        self.assertEqual(obs.counts()['_admit'],1)
        self.assertNotIn('__v2o_causal_admission',execute_live_v0e.__globals__)
        self.assertNotIn('__v2k_admission',execute_live_v0e.__globals__)
        self.assertFalse(s.summary()['real_frozen_native_actor_consumer_changed'])

    def test_ACK_and_actor_application_are_distinct(self):
        _,_,_,s,_,_,_,_=one_run()
        acks=s.credit_journal()
        applied=s.consumer_journal()
        self.assertEqual(len(acks),4)
        self.assertEqual(len(applied),4)
        self.assertEqual(s.summary()['actor_credit_register'],
                         s.summary()['actor_consumer_applied_credit'])
        self.assertTrue(any(a['consume_tick']>a['ack_service_tick']
                            for a in applied))
        self.assertTrue(all(a['ack_digest'] in
                            {ack['chain_digest'] for ack in acks}
                            for a in applied))
        self.assertEqual(len({a['chain_digest'] for a in applied}),4)
        self.assertTrue(s.audit_consumer())

    def test_causal_receipts_bind_actor_owner_source_ACK_and_epoch(self):
        _,_,_,s,_,_,_,_=one_run()
        original=s.consumer_journal()
        for ack,receipt in zip(s.credit_journal(),original):
            self.assertEqual(receipt['owner_pe'],ack['owner_pe'])
            self.assertEqual(receipt['actor'],ack['actor'])
            self.assertEqual(receipt['ack_seq'],ack['seq'])
            self.assertEqual(receipt['judgment_id'],ack['judgment_id'])
            self.assertEqual(receipt['source_emission'],ack['source_emission'])
            self.assertGreaterEqual(receipt['consume_tick'],ack['serviced_tick'])
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],0)

    def test_full_15_native_recipes_across_both_PE_capacities(self):
        case,fabric,plans=fixture()
        for label,recipe in RECIPES:
            for capacity in (1,3):
                with self.subTest(label=label,capacity=capacity):
                    native,derived,projection,s,_,_,_,_=one_run(
                        case=build_workload(case,recipe),capacity=capacity)
                    self.assertEqual(projection,native)
                    self.assertEqual(derived['forward'],native['forward'])
                    self.assertEqual(derived['feedback'],native['feedback'])
                    self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],0)

    def test_quota_one_ACKs_stay_intact_applied_once(self):
        native,_,projection,s,_,_,_,_=one_run(
            plan=ActorConsumerPlanV2p(max_total_consume=1))
        self.assertEqual(native,projection)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertEqual(len(s.consumer_journal()),1)
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],3)
        self.assertTrue(s.audit_consumer())

    def test_total_zero_is_not_silence_or_negative(self):
        native,_,projection,s,port,_,_,_=one_run(
            plan=ActorConsumerPlanV2p(max_total_consume=0))
        self.assertEqual(native,projection)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertFalse(s.consumer_journal())
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)
        self.assertEqual(port.summary()['negative_judgments'],0)
        self.assertEqual(port.summary()['absence_certificates'],0)
        self.assertEqual(s.summary()['consumer_extra_tail_ticks'],0)

    def test_zero_throughput_keeps_all_real_ACKs_pending_without_fake_tail(self):
        _,_,_,s,_,_,_,_=one_run(
            plan=ActorConsumerPlanV2p(max_consume_per_tick=0))
        self.assertEqual(s.summary()['actor_consumer_applications'],0)
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)
        self.assertEqual(s.summary()['consumer_extra_tail_ticks'],0)

    def test_no_consumer_tail_preserves_native_but_defers_application(self):
        native,_,projection,s,_,_,_,_=one_run(
            plan=ActorConsumerPlanV2p(max_tail_ticks=0))
        self.assertEqual(native,projection)
        self.assertGreater(len(s.credit_journal()),len(s.consumer_journal()))
        self.assertEqual(s.summary()['consumer_extra_tail_ticks'],0)
        self.assertEqual(s.summary()['consumer_tail_applications'],0)

    def test_higher_throughput_preserves_FIFO_native_and_state(self):
        native,_,projection,s,_,_,_,_=one_run(
            plan=ActorConsumerPlanV2p(max_consume_per_tick=2))
        self.assertEqual(native,projection)
        self.assertEqual(len(s.consumer_journal()),len(s.credit_journal()))
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],0)
        self.assertTrue(all(row['actor_consumer_applications']<=2
                            for row in s.consumer_trace()))

    def test_consumer_backlog_overflow_fails_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h()
        consumer=DerivedActorConsumerV2p(port,consumer_plan=ActorConsumerPlanV2p(
            max_pending_ack_backlog=0))
        derived,_,_,_=derive_consumer_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,consumer,CallsiteObserver())
        with self.assertRaisesRegex(NativeForkError,'ACK mailbox overflow'):
            derived(case,fabric,*plans,LiveBVPlanV0e())

    def test_loss_fails_to_create_ACK_or_consumer_credit(self):
        native,_,projection,s,port,_,_,_=one_run(
            receiver={'accept':lambda _:False})
        self.assertEqual(native,projection)
        self.assertFalse(s.credit_journal())
        self.assertFalse(s.consumer_journal())
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],0)
        self.assertGreater(port.summary()['lost'],0)

    def test_fault_is_loss_not_actor_application_or_negative_credit(self):
        def fault(_):
            raise RuntimeError('v2p simulated callback fault')
        native,_,projection,s,port,_,_,_=one_run(receiver={'accept':fault})
        self.assertEqual(native,projection)
        self.assertFalse(s.consumer_journal())
        self.assertFalse(s.credit_journal())
        self.assertEqual(port.summary()['negative_judgments'],0)

    def test_real_negative_B_is_actor_A_application_not_native_learning(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(replace(node,instructions=block)
                        if node.node_id=='B' else node for node in case.nodes))
        native,_,projection,s,port,_,_,_=one_run(case=changed)
        self.assertEqual(native,projection)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual([r['response'] for r in s.consumer_journal()],[-1,-1])
        self.assertEqual([r['actor'] for r in s.consumer_journal()],['A','A'])
        self.assertEqual(s.summary()['actor_consumer_applied_credit']['A'],-2)
        self.assertFalse(s.summary()['native_learning_proven'])

    def test_forged_ACK_and_actor_binding_refused_before_projection(self):
        for change in ({'ack_digest':'f'*64},{'actor':'B'},
                       {'owner_pe':'FORGED'},{'ack_seq':99},
                       {'judgment_id':'forged'},{'consumer_seq':0},
                       {'response':-1},{'chain_prev':'f'*64}):
            with self.subTest(change=change):
                _,integrated,_,s,_,_,_,_=one_run()
                s._consume_journal[0]=replace(s._consume_journal[0],**change)
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(integrated)

    def test_duplicate_or_reordered_consumer_receipts_refused(self):
        for mutate in ('replay','reverse','delete'):
            with self.subTest(mutate=mutate):
                _,integrated,_,s,_,_,_,_=one_run()
                if mutate=='replay':
                    s._consume_journal[1]=s._consume_journal[0]
                elif mutate=='reverse':
                    s._consume_journal.reverse()
                else:
                    s._consume_journal.pop()
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(integrated)

    def test_rehashing_forged_future_or_wrong_phase_still_fails(self):
        for changes in ({'consume_tick':1},
                        {'consume_phase':'derived-consumer-tail'},
                        {'consume_tick':200}):
            with self.subTest(changes=changes):
                _,_,_,s,_,_,_,_=one_run()
                receipt=replace(s._consume_journal[0],**changes)
                s._consume_journal[0]=replace(
                    receipt,chain_digest=_consume_digest(receipt))
                with self.assertRaises(NativeForkError):
                    s.audit_consumer()

    def test_consumer_tick_trace_and_throughput_forgery_refused(self):
        for key,new in (('tick',99),('actor_consumer_applications',17),
                        ('ack_backlog_after_consumer',999),
                        ('consumer_extra_pe_service_units',1)):
            with self.subTest(key=key):
                _,_,_,s,_,_,_,_=one_run()
                row=next(r for r in s._consume_trace
                         if r['actor_consumer_applications'])
                row[key]=new
                with self.assertRaises(NativeForkError):
                    s.audit_consumer()

    def test_invalid_plan_and_source_mutation_fail_closed(self):
        for bad in (ActorConsumerPlanV2p(max_tail_ticks=-1),
                    ActorConsumerPlanV2p(max_total_consume=513),
                    ActorConsumerPlanV2p(max_pending_ack_backlog=-1),
                    ActorConsumerPlanV2p(max_consume_per_tick=True),
                    ActorConsumerPlanV2p(max_consume_per_tick=17)):
            with self.subTest(bad=bad):
                with self.assertRaises(NativeForkError):
                    DerivedActorConsumerV2p(ReceiverPortV2h(),consumer_plan=bad)
        port=ReceiverPortV2h()
        service=DerivedActorConsumerV2p(port)
        drift=SOURCE.read_bytes().replace(b'while True:',b'while False:',1)
        with self.assertRaises(NativeForkError):
            derive_consumer_executor(
                drift,execute_live_v0e,port,service,CallsiteObserver())

    def test_signed_predecessor_and_contract_only_are_fail_closed(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2o source predecessor not provided')
        predecessor=json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(),PREDECESSOR_SHA)
        self.assertTrue(validate_v2o(predecessor,raw))
        contract=build_report(predecessor,raw)
        self.assertEqual(contract['status'],CONTRACT_STATUS)
        self.assertFalse(contract['frozen_native_actor_consumption_proven'])
        mutation=json.loads(raw)
        mutation['paired_native_matrix'][0]['modes'][0]['capacities'][
            'contended_capacity']['admission_modes']['strict_native_causal'][
                'summary']['derived_actor_credit_ack_count']=999
        with self.assertRaises(ValueError):
            build_report(mutation,canon(mutation))
        with self.assertRaises(ValueError):
            build_report(predecessor,raw+b' ')

    def test_full_signed_45_by_two_matrix_and_canonical_report(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2o source predecessor not provided')
        predecessor=json.loads(raw)
        result=experiment(predecessor,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(predecessor,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['new_native_runs'],90)
        self.assertEqual(report['new_normal_consumer_runs'],90)
        self.assertEqual(report['new_bounded_consumer_intervention_runs'],180)
        self.assertEqual([x['consumer_applied'] for x in
                          report['consumer_handoff_totals'].values()],[156,156])
        self.assertTrue(all(x['full_native_projection_equal']==45
                            for x in report['consumer_handoff_totals'].values()))
        self.assertGreater(report['bounded_consumer_intervention_totals'][
            'tail_off']['backlog'],0)
        self.assertEqual(json.loads(canon(report)),report)


if __name__=='__main__':
    unittest.main()
