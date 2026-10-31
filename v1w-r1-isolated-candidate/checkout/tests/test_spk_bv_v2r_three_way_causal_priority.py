"""BV v2r: native-ready guard discrimination with paid derived actor consumer."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e,LiveBVPlanV0e,LiveBVRejected,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,NativeForkError,PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_actor_resource_consumer_v2q import (
    ConsumerResourcePlanV2q,DerivedActorResourceConsumerV2q,
    derive_resource_consumer_executor,
)
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.three_way_causal_priority_integration_v2r import (
    PREDECESSOR_SHA,CONTRACT_STATUS,STATUS,MODES,
    validate_v2q,build_report,experiment,_bounded_horizon,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2q-independent-consumer-resource.json'),
         ROOT.parent.parent/'spk-bv-v2q-independent-consumer-resource.json',
         ROOT/'spk-bv-v2q-independent-consumer-resource.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2Q_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,capacity=1,forward=True,bv=True,case=None,resource=None,
            receiver=None,credit=None):
    initial,fabric,plans=fixture()
    plans=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
           plans[2],plans[3])
    port=ReceiverPortV2h(**(receiver or {}))
    actor=DerivedActorResourceConsumerV2q(
        port,resource_plan=resource or ConsumerResourcePlanV2q(),
        admission_plan=CausalAdmissionPlanV2o(forward,bv),
        credit_plan=credit or ActorCreditPlanV2l())
    observer=CallsiteObserver()
    derived,_,semantics,anchors=derive_resource_consumer_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,actor,observer)
    chosen=initial if case is None else case
    native=execute_live_v0e(chosen,fabric,*plans,LiveBVPlanV0e())
    integrated=derived(chosen,fabric,*plans,LiveBVPlanV0e())
    projected=actor.project_original_native_result(integrated)
    return native,integrated,projected,actor,port,observer,semantics,anchors


class TestV2rThreeWayCausalPriority(unittest.TestCase):

    def test_original_source_pinned_and_native_ownership_unchanged(self):
        native,result,projection,s,_,obs,semantic,resource=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(projection,native)
        self.assertEqual(result['forward'],native['forward'])
        self.assertEqual(semantic,(('batch',194),('clock',125),
                                   ('emission',217),('ingress',136)))
        self.assertEqual(resource,(158,296,307))
        self.assertEqual(obs.counts()['_admit'],1)
        self.assertNotIn('__v2o_causal_admission',execute_live_v0e.__globals__)
        self.assertEqual(s.summary()['native_operator_updates'],0)

    def test_both_native_ready_guards_preserve_entire_native_at_tight_PE(self):
        native,_,p,s,_,_,_,_=one_run(capacity=1)
        self.assertEqual(p,native)
        self.assertEqual(s.summary()['derived_actor_credit_ack_count'],4)
        self.assertEqual(s.summary()['derived_independent_consumer_resource_charges'],4)
        self.assertEqual(s.summary()['consumer_independent_inline_charges'],0)
        self.assertEqual(s.summary()['consumer_independent_tail_charges'],4)

    def test_strict_preserves_complete_native_at_original_PE(self):
        native,_,p,s,_,_,_,_=one_run(capacity=3)
        self.assertEqual(p,native)
        self.assertEqual(s.summary()['pregrants_during_native_causal_veto'],0)
        self.assertGreater(s.summary()['consumer_independent_inline_charges'],0)

    def test_forward_only_guard_has_native_forward_but_changes_BV_feedback(self):
        native,_,p,s,_,_,_,_=one_run(forward=True,bv=False)
        self.assertEqual(p['forward'],native['forward'])
        self.assertNotEqual(p['feedback'],native['feedback'])
        self.assertGreater(s.summary()['pre_forward_actor_grants'],0)
        self.assertEqual(s.summary()['derived_independent_consumer_resource_charges'],4)

    def test_feedback_only_guard_changes_forward_timing(self):
        native,_,p,s,_,_,_,_=one_run(forward=False,bv=True)
        self.assertNotEqual(p['forward'],native['forward'])
        self.assertEqual(_payload(p['forward']),_payload(native['forward']))
        self.assertGreater(s.summary()['native_feedback_veto_ticks'],0)
        self.assertEqual(len(s.resource_charge_journal()),4)

    def test_null_guard_changes_native_but_retains_terminal_payload(self):
        native,_,p,s,_,_,_,_=one_run(forward=False,bv=False)
        self.assertNotEqual(p,native)
        self.assertNotEqual(p['forward'],native['forward'])
        self.assertEqual(_payload(p['forward']),_payload(native['forward']))
        self.assertEqual(s.summary()['native_causal_priority_veto_ticks'],0)

    def test_full_15_workloads_strict_under_both_capacities(self):
        base,_,_=fixture()
        for label,recipe in RECIPES:
            for capacity in (1,3):
                with self.subTest(label=label,capacity=capacity):
                    native,_,projected,s,_,_,_,_=one_run(
                        capacity=capacity,case=build_workload(base,recipe))
                    self.assertEqual(projected,native)
                    self.assertEqual(len(s.credit_journal()),
                                     len(s.resource_charge_journal()))

    def test_loss_reverts_all_four_causal_guards_to_native(self):
        for name,f,b in MODES:
            with self.subTest(name=name):
                native,_,projected,s,port,_,_,_=one_run(
                    forward=f,bv=b,receiver={'accept':lambda _:False})
                self.assertEqual(projected,native)
                self.assertFalse(s.credit_journal())
                self.assertFalse(s.resource_charge_journal())
                self.assertEqual(port.summary()['negative_judgments'],0)

    def test_credit_zero_keeps_delivered_judgments_without_resource_grants(self):
        for name,f,b in MODES:
            with self.subTest(name=name):
                native,_,projected,s,port,_,_,_=one_run(
                    forward=f,bv=b,
                    credit=ActorCreditPlanV2l(max_abs_credit=0))
                self.assertEqual(projected,native)
                self.assertGreater(port.summary()['control_delivered'],0)
                self.assertFalse(s.credit_journal())
                self.assertFalse(s.resource_charge_journal())
                self.assertEqual(port.summary()['absence_certificates'],0)

    def test_disabling_only_consumer_does_not_repair_early_ACK_timing(self):
        native,_,projected,s,_,_,_,_=one_run(
            forward=False,bv=False,
            resource=ConsumerResourcePlanV2q(max_total_consumer_charges=0))
        self.assertNotEqual(projected,native)
        self.assertEqual(len(s.credit_journal()),4)
        self.assertFalse(s.consumer_journal())
        self.assertEqual(s.summary()['actor_consumer_pending_ack_backlog'],4)

    def test_tail_off_keeps_forward_change_only_from_ACK_arbitration(self):
        n,_,baseline,s,_,_,_,_=one_run(forward=False,bv=False)
        n2,_,without_tail,restricted,_,_,_,_=one_run(
            forward=False,bv=False,
            resource=ConsumerResourcePlanV2q(max_resource_tail_ticks=0))
        self.assertEqual(n,n2)
        self.assertEqual(baseline,without_tail)
        self.assertEqual(s.credit_journal(),restricted.credit_journal())
        self.assertEqual(restricted.summary()['consumer_extra_tail_ticks'],0)

    def test_guard_one_sided_ablations_fail_same_finite_horizon(self):
        case,fabric,plans=fixture()
        witness=_bounded_horizon(SOURCE.read_bytes(),case,fabric,plans,
                                 execute_live_v0e,LiveBVPlanV0e)
        self.assertEqual(witness['max_ticks'],11)
        self.assertEqual(witness['guard_modes']['strict_native_ready'],
                         'EXACT_FULL_NATIVE_PROJECTION_AND_PAID_CONSUMER')
        self.assertTrue(all(witness['guard_modes'][m]==
            'BOUNDED_HORIZON_REJECTED_NO_CERTIFICATE'
            for m,_,_ in MODES if m!='strict_native_ready'))

    def test_negative_B_still_actor_A_and_independently_paid(self):
        case,_,_=fixture()
        negative=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        changed=replace(case,nodes=tuple(replace(node,instructions=negative)
                        if node.node_id=='B' else node for node in case.nodes))
        native,_,projection,s,port,_,_,_=one_run(case=changed)
        self.assertEqual(projection,native)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(s.summary()['actor_consumer_applied_credit']['A'],-2)
        self.assertEqual(s.summary()['derived_independent_consumer_PE_units'],2)
        self.assertEqual(s.summary()['derived_independent_consumer_memory_units'],4)

    def test_invalid_causal_guard_configuration_rejected(self):
        for bad in (CausalAdmissionPlanV2o(protect_ready_forward=1),
                    CausalAdmissionPlanV2o(protect_ready_native_feedback=0)):
            with self.subTest(bad=bad):
                with self.assertRaises(NativeForkError):
                    DerivedActorResourceConsumerV2q(ReceiverPortV2h(),
                                                    admission_plan=bad)

    def test_forged_control_pre_native_competition_is_fail_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        service=DerivedActorResourceConsumerV2q(port,
            admission_plan=CausalAdmissionPlanV2o(False,False))
        compiled,_,_,_=derive_resource_consumer_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,service,CallsiteObserver())
        regular=port.batch
        injected=[False]

        def forged(actor,tick,items,outputs):
            regular(actor,tick,items,outputs)
            if port.judgments and not injected[0]:
                port._mailboxes.setdefault(port.judgments[0].recipient,[]).append(
                    replace(port.judgments[0],identity='v2r-forged-early-control'))
                injected[0]=True

        port.batch=forged
        with self.assertRaises(NativeForkError):
            compiled(case,fabric,*plans,LiveBVPlanV0e())

    def test_signed_v2q_predecessor_and_contract_only_fail_closed(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2q report not available')
        prev=json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(),PREDECESSOR_SHA)
        self.assertTrue(validate_v2q(prev,raw))
        contract=build_report(prev,raw)
        self.assertEqual(contract['status'],CONTRACT_STATUS)
        self.assertFalse(contract['native_concurrent_three_way_event_arbitration_proven'])
        mutated=json.loads(raw)
        mutated['independently_charged_consumer_totals'][
            'contended_capacity']['charged_consumptions']=999
        with self.assertRaises(ValueError):
            build_report(mutated,canon(mutated))
        with self.assertRaises(ValueError):
            build_report(prev,raw+b' ')

    def test_full_signed_45_by_two_four_guard_causal_resource_matrix(self):
        raw=predecessor_bytes()
        if raw is None:
            self.skipTest('signed v2q report not available')
        prev=json.loads(raw)
        result=experiment(prev,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,
                          plan_type=LiveBVPlanV0e)
        report=build_report(prev,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['new_native_runs'],90)
        self.assertEqual(report['new_derived_four_guard_runs'],360)
        self.assertEqual(report['new_derived_causal_intervention_runs'],720)
        self.assertEqual(report['causal_priority_resource_totals'][
            'contended_capacity']['strict_native_ready']['full_native_projection'],45)
        self.assertEqual(report['causal_priority_resource_totals'][
            'contended_capacity']['actor_first_null_guard']['full_native_projection'],0)
        self.assertEqual(report['causal_resource_intervention_totals'][
            'causal_transport_loss']['native_restored'],180)
        self.assertEqual(report,json.loads(canon(report)))


if __name__=='__main__':
    unittest.main()
