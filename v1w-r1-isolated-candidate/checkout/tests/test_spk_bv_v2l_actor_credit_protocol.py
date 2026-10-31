"""SPK BV v2l: exactly-once actor-addressed derived credit event protocol."""
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
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,DerivedActorCreditProtocolV2l,
    derive_actor_credit_executor,ZERO_ROOT,
)
from spk_bv_research.actor_credit_protocol_integration_v2l import (
    validate_v2k,experiment,build_report,STATUS,CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS=(Path('/tmp/spk-bv-v2k-integrated-actor-resource-admission.json'),
         ROOT/'spk-bv-v2k-integrated-actor-resource-admission.json')


def predecessor_bytes():
    configured=os.environ.get('SPK_V2K_REPORT')
    for path in ([Path(configured)] if configured else [])+list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*,case=None,port_kw=None,credit_plan=None,service_plan=None):
    default,fabric,plans=fixture()
    case=default if case is None else case
    port=ReceiverPortV2h(**(port_kw or {}))
    credit=DerivedActorCreditProtocolV2l(port,credit_plan or ActorCreditPlanV2l(),
                                             service_plan or ShadowServicePlanV2j())
    obs=CallsiteObserver()
    derived,_,anchors,resource=derive_actor_credit_executor(
        SOURCE.read_bytes(),execute_live_v0e,port,credit,obs)
    native=execute_live_v0e(case,fabric,*plans,LiveBVPlanV0e())
    integrated=derived(case,fabric,*plans,LiveBVPlanV0e())
    projected=credit.project_original_native_result(integrated)
    return native,integrated,projected,credit,port,obs,anchors,resource


class TestV2lActorCreditProtocol(unittest.TestCase):

    def test_pinned_ast_causal_and_resource_anchors(self):
        native,integrated,projected,credit,_,obs,anchors,resource=one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(),PINNED_SCHED)
        self.assertEqual(anchors,(('batch',194),('clock',125),
                                  ('emission',217),('ingress',136)))
        self.assertEqual(resource,(296,307))
        self.assertEqual(native,projected)
        self.assertEqual(native['forward'],integrated['forward'])
        self.assertNotEqual(native['resources']['timeline'],
                            integrated['resources']['timeline'])
        self.assertEqual(obs.counts(),{'_admit':1,'_admit_plan':1,
                                       'offer_feedback':6})
        self.assertNotIn('__v2k_admission',execute_live_v0e.__globals__)

    def test_four_credit_acks_bind_resource_commits_exactly_once(self):
        native,integrated,projected,credit,port,_,_,_=one_run()
        self.assertEqual(native,projected)
        summary=credit.summary()
        self.assertEqual(summary['delivered_controls'],4)
        self.assertEqual(summary['derived_resource_grants_committed'],4)
        self.assertEqual(summary['derived_actor_credit_ack_count'],4)
        self.assertEqual(summary['actor_credit_register'],{'A':2,'B':2,'C':0})
        self.assertEqual(sum(summary['actor_credit_event_epochs'].values()),4)
        self.assertEqual(len(credit.credit_journal()),4)
        self.assertFalse(summary['frozen_actor_state_changed'])
        self.assertFalse(summary['frozen_actor_credit_contract_proven'])
        self.assertFalse(summary['native_learning_proven'])

    def test_ack_custody_is_actor_owner_receiver_decision_and_source(self):
        _,_,_,credit,port,_,_,_=one_run()
        by_id={record.identity:record for record in port.judgments}
        for ack in credit.credit_journal():
            with self.subTest(ack=ack['judgment_id']):
                record=by_id[ack['judgment_id']]
                emission=port.emissions[ack['source_emission']]
                self.assertEqual(ack['actor'],record.recipient)
                self.assertEqual(emission.sender,record.recipient)
                self.assertEqual(ack['receiver_issuer'],record.issuer)
                self.assertEqual(ack['decision'],record.decision)
                self.assertEqual(ack['response'],record.response)
                self.assertGreaterEqual(ack['serviced_tick'],record.due_tick)

    def test_actor_epoch_monotonic_credit_chain_replay(self):
        _,_,_,credit,_,_,_,_=one_run()
        roots={'A':ZERO_ROOT,'B':ZERO_ROOT,'C':ZERO_ROOT}
        sequences={'A':0,'B':0,'C':0}
        for ack in credit.credit_journal():
            actor=ack['actor']
            self.assertEqual(ack['chain_prev'],roots[actor])
            self.assertEqual(ack['seq'],sequences[actor]+1)
            self.assertEqual(ack['credit_after'],ack['credit_before']+ack['response'])
            roots[actor]=ack['chain_digest']
            sequences[actor]+=1
        self.assertEqual(credit.summary()['actor_credit_chain_roots'],roots)
        self.assertEqual(credit.summary()['actor_credit_event_epochs'],sequences)

    def test_modified_ack_digest_refuses_full_native_projection(self):
        _,integrated,_,credit,_,_,_,_=one_run()
        credit._acks[0]=replace(credit._acks[0],chain_digest='f'*64)
        with self.assertRaises(NativeForkError):
            credit.project_original_native_result(integrated)

    def test_modified_ack_semantic_credit_refuses_projection(self):
        _,integrated,_,credit,_,_,_,_=one_run()
        credit._acks[0]=replace(credit._acks[0],credit_after=99)
        with self.assertRaises(NativeForkError):
            credit.project_original_native_result(integrated)

    def test_duplicate_ack_or_reordered_ack_refuses_projection(self):
        for strategy in ('duplicate','reorder'):
            with self.subTest(strategy=strategy):
                _,integrated,_,credit,_,_,_,_=one_run()
                if strategy=='duplicate':
                    credit._acks.append(credit._acks[0])
                else:
                    credit._acks[0],credit._acks[1]=credit._acks[1],credit._acks[0]
                with self.assertRaises(NativeForkError):
                    credit.project_original_native_result(integrated)

    def test_zero_credit_capacity_withholds_all_delivered_without_tail(self):
        native,integrated,projected,credit,port,_,_,_=one_run(
            credit_plan=ActorCreditPlanV2l(max_abs_credit=0))
        self.assertEqual(native,projected)
        self.assertEqual(native,integrated)
        self.assertEqual(credit.credit_journal(),[])
        summary=credit.summary()
        self.assertEqual(summary['delivered_policy_blocked_pending'],4)
        self.assertEqual(summary['delivered_other_unconsumed_pending'],0)
        self.assertEqual(summary['new_derived_control_only_timeline_rows'],0)
        self.assertEqual(summary['actor_credit_register'],{'A':0,'B':0,'C':0})
        self.assertEqual(port.summary()['control_delivered'],4)
        self.assertEqual(summary['absence_certificates'],0)

    def test_one_credit_bound_obeys_fifo_and_exposes_pending(self):
        native,_,projected,credit,port,_,_,_=one_run(
            credit_plan=ActorCreditPlanV2l(max_abs_credit=1))
        self.assertEqual(native,projected)
        s=credit.summary()
        self.assertTrue(all(abs(v)<=1 for v in s['actor_credit_register'].values()))
        self.assertGreater(s['delivered_policy_blocked_pending'],0)
        self.assertEqual(s['delivered_controls'],4)
        self.assertEqual(s['derived_actor_credit_ack_count']+
                         s['unconsumed_delivered_controls'],4)
        self.assertEqual(s['absence_certificates'],0)

    def test_global_ack_quota_one_is_not_per_actor_quota(self):
        native,_,projected,credit,port,_,_,_=one_run(
            credit_plan=ActorCreditPlanV2l(max_actor_acks_total=1))
        self.assertEqual(native,projected)
        s=credit.summary()
        self.assertEqual(len(credit.credit_journal()),1)
        self.assertEqual(s['delivered_controls'],4)
        self.assertEqual(s['delivered_policy_blocked_pending'],3)

    def test_explicit_no_tail_can_defer_without_negative_certificate(self):
        native,_,projected,credit,_,_,_,_=one_run(
            port_kw={'latency':16},
            service_plan=ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=0))
        self.assertEqual(native,projected)
        s=credit.summary()
        self.assertEqual(s['derived_control_tail_grants'],0)
        self.assertEqual(s['new_derived_control_only_timeline_rows'],0)
        self.assertGreater(s['unconsumed_delivered_controls'],0)
        self.assertEqual(s['absence_certificates'],0)

    def test_transport_loss_fault_never_create_actor_credit(self):
        for label,opts in (
            ('loss',{'accept':lambda _:False}),
            ('fault',{'accept':lambda _:(_ for _ in ()).throw(
                RuntimeError('feedback callback fault'))}),
        ):
            with self.subTest(label=label):
                native,integrated,projected,credit,port,_,_,_=one_run(port_kw=opts)
                self.assertEqual(native,projected)
                self.assertEqual(native,integrated)
                self.assertFalse(credit.credit_journal())
                self.assertEqual(credit.summary()['delivered_controls'],0)
                self.assertEqual(credit.summary()['absence_certificates'],0)

    def test_receiver_overflow_is_not_an_ack_or_silence_proof(self):
        native,_,projected,credit,port,_,_,_=one_run(port_kw={'capacity':1})
        self.assertEqual(native,projected)
        self.assertTrue(port.summary()['queue_overflow'] or
                        port.summary()['mailbox_overflow'])
        self.assertLessEqual(len(credit.credit_journal()),
                             port.summary()['control_delivered'])
        self.assertEqual(credit.summary()['absence_certificates'],0)

    def test_real_negative_B_actor_credit_and_bound_withhold(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        negative=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        original,_,projected,credit,port,_,_,_=one_run(case=negative)
        self.assertEqual(original,projected)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual([a['response'] for a in credit.credit_journal()],[-1,-1])
        self.assertEqual(credit.summary()['actor_credit_register']['A'],-2)
        self.assertFalse(credit.summary()['native_learning_proven'])
        original2,_,projected2,capped,port2,_,_,_=one_run(
            case=negative,credit_plan=ActorCreditPlanV2l(max_abs_credit=1))
        self.assertEqual(original2,projected2)
        self.assertEqual(len(capped.credit_journal()),1)
        self.assertEqual(capped.summary()['actor_credit_register']['A'],-1)
        self.assertEqual(capped.summary()['delivered_policy_blocked_pending'],1)

    def test_invalid_policy_and_source_drift_fail_closed(self):
        port=ReceiverPortV2h()
        for plan in (ActorCreditPlanV2l(max_abs_credit=-1),
                     ActorCreditPlanV2l(max_actor_acks_total=513),
                     ActorCreditPlanV2l(strict_due_fifo=False)):
            with self.subTest(plan=plan),self.assertRaises(NativeForkError):
                DerivedActorCreditProtocolV2l(port,plan)
        with self.assertRaises(NativeForkError):
            DerivedActorCreditProtocolV2l(port,
                service_plan=ShadowServicePlanV2j(per_actor_per_tick=2))
        credit=DerivedActorCreditProtocolV2l(port)
        with self.assertRaises(NativeForkError):
            derive_actor_credit_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,credit,CallsiteObserver())

    def test_forged_mailbox_before_service_fails_closed(self):
        case,fabric,plans=fixture()
        port=ReceiverPortV2h(latency=16)
        credit=DerivedActorCreditProtocolV2l(port)
        derived,_,_,_=derive_actor_credit_executor(
            SOURCE.read_bytes(),execute_live_v0e,port,credit,CallsiteObserver())
        original_batch=port.batch
        injected={'done':False}
        def attack(actor,tick,items,outputs):
            original_batch(actor,tick,items,outputs)
            if port.judgments and not injected['done']:
                forged=replace(port.judgments[0],identity='evil-credit')
                port._mailboxes.setdefault(forged.recipient,[]).append(forged)
                injected['done']=True
        port.batch=attack
        with self.assertRaises(NativeForkError):
            derived(case,fabric,*plans,LiveBVPlanV0e())

    def test_all_15_recipes_have_exact_complete_native_projection(self):
        case,fabric,plans=fixture()
        source=SOURCE.read_bytes()
        for label,recipe in RECIPES:
            with self.subTest(recipe=label):
                changed=build_workload(case,recipe)
                port=ReceiverPortV2h()
                credit=DerivedActorCreditProtocolV2l(port)
                derived,_,_,_=derive_actor_credit_executor(
                    source,execute_live_v0e,port,credit,CallsiteObserver())
                native=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                integrated=derived(changed,fabric,*plans,LiveBVPlanV0e())
                self.assertEqual(credit.project_original_native_result(integrated),
                                 native)
                self.assertEqual(credit.summary()['derived_actor_credit_ack_count'],
                                 credit.summary()['derived_resource_grants_committed'])

    def test_signed_v2k_predecessor_tampering_is_rejected(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2k predecessor not mounted')
        previous=json.loads(raw)
        self.assertTrue(validate_v2k(previous,raw))
        for field,value in (
            ('full_native_projection_parity_cells',44),
            ('native_learning_proven',True),
            ('frozen_native_actor_resource_grant_commits_observed',True),
        ):
            with self.subTest(field=field):
                changed=dict(previous);changed[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2k(changed,canon(changed))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2k(previous,raw+b'\n')

    def test_full_45_cell_v2k_resource_and_native_projection_matrix(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('signed v2k predecessor not mounted')
        previous=json.loads(raw)
        self.assertEqual(build_report(previous,raw)['status'],CONTRACT_STATUS)
        result=experiment(previous,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['full_native_projection_parity_cells'],45)
        self.assertEqual(report['v2k_integrated_derived_resource_parity_cells'],45)
        self.assertEqual(report['actor_credit_totals']['derived_actor_credit_ack_count'],156)
        self.assertEqual(report['intervention_totals']['cap_zero']['ack_count'],0)
        self.assertEqual(report['intervention_totals']['cap_zero']['policy_blocked'],156)
        self.assertFalse(report['real_frozen_native_actor_acknowledgments_proven'])
        self.assertFalse(report['native_learning_proven'])
        self.assertEqual(canon(report),canon(json.loads(canon(report))))


if __name__=='__main__':
    unittest.main()
