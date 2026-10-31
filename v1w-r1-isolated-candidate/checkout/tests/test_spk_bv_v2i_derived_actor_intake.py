"""BV v2i: committed actor-batch intake contract and pinned replay tests."""
from __future__ import annotations

import json
import unittest
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
from spk_backvalidation_v2.derived_actor_intake_v2i import (
    ActorIntakeV2i, derive_actor_intake_executor,
)
from spk_bv_research.actor_intake_integration_v2i import (
    validate_v2h, experiment, build_report, STATUS, CONTRACT_STATUS,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v2h-derived-actor-feedback.json'),
           ROOT/'spk-bv-v2h-derived-actor-feedback.json')


def predecessor_bytes():
    import os
    configured = os.environ.get('SPK_V2H_REPORT')
    paths = ([Path(configured)] if configured else []) + list(REPORTS)
    for path in paths:
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*, case=None, plan=None, port_args=None, intake_args=None):
    default, fabric, plans = fixture()
    case = default if case is None else case
    plan = LiveBVPlanV0e() if plan is None else plan
    port = ReceiverPortV2h(**(port_args or {}))
    intake = ActorIntakeV2i(port, **(intake_args or {}))
    watcher = CallsiteObserver()
    derived, calls, anchors = derive_actor_intake_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, intake, watcher)
    before = execute_live_v0e(case, fabric, *plans, plan)
    after = derived(case, fabric, *plans, plan)
    port.close()
    return before, after, intake, port, watcher, calls, anchors


class TestV2iDerivedActorIntake(unittest.TestCase):

    def test_native_batch_intake_real_while_frozen_parity(self):
        before, after, intake, port, watcher, _, anchors = one_run()
        self.assertEqual(before, after)
        self.assertEqual(anchors, (('batch',194), ('clock',125),
                                   ('emission',217), ('ingress',136)))
        summary = intake.summary()
        self.assertEqual(summary['committed_actor_batch_visits'],6)
        self.assertEqual(summary['derived_actor_batch_receipts'],2)
        self.assertEqual(summary['unconsumed_delivered_controls'],2)
        self.assertEqual(summary['credit_by_actor'],{'A':1,'B':1,'C':0})
        self.assertEqual(summary['frozen_state_updates_from_control'],0)
        self.assertFalse(summary['frozen_actor_receives_control'])
        self.assertEqual(watcher.counts(),{'_admit':1,'_admit_plan':1,
                                          'offer_feedback':6})
        self.assertEqual(port.summary()['receiver_local_judgments'],4)
        self.assertEqual(len(intake.receipts('A')),1)
        self.assertNotIn('__v2h_port',execute_live_v0e.__globals__)

    def test_negative_receiver_credit_is_real_but_not_learning(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        negative=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        before,after,intake,port,_,_,_=one_run(case=negative)
        self.assertEqual(before,after)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(port.summary()['credit_by_sender'],{'A':-2})
        self.assertEqual(intake.summary()['derived_actor_batch_receipts'],1)
        self.assertEqual(intake.summary()['credit_by_actor']['A'],-1)
        self.assertEqual(intake.summary()['unconsumed_delivered_controls'],1)
        self.assertEqual(intake.summary()['operator_learning_updates'],0)

    def test_loss_has_no_intake_and_no_negative_certificate(self):
        a,b,intake,port,_,_,_=one_run(port_args={'accept':lambda _:False})
        self.assertEqual(a,b)
        self.assertEqual(port.summary()['lost'],4)
        self.assertEqual(intake.summary()['derived_actor_batch_receipts'],0)
        self.assertEqual(intake.summary()['credit_by_actor'],{'A':0,'B':0,'C':0})
        self.assertEqual(intake.summary()['absence_certificates'],0)

    def test_separate_intake_pressure_never_mutates_forward(self):
        a,b,intake,port,_,_,_=one_run(
            intake_args={'per_batch':1,'max_receipts':1})
        self.assertEqual(a,b)
        self.assertEqual(intake.summary()['derived_actor_batch_receipts'],1)
        self.assertTrue(intake.summary()['receipt_pressure'])
        self.assertEqual(intake.summary()['unconsumed_delivered_controls'],3)
        self.assertEqual(port.summary()['control_delivered'],4)

    def test_actor_binding_and_monotonic_batch_context_fail_closed(self):
        port=ReceiverPortV2h()
        intake=ActorIntakeV2i(port)
        with self.assertRaises(NativeForkError):
            intake.committed_actor_batch('A',1)
        with self.assertRaises(NativeForkError):
            intake.bind_admitted_actors({'A':SimpleNamespace(node_id='C')})
        intake.bind_admitted_actors({'A':SimpleNamespace(node_id='A')})
        with self.assertRaises(NativeForkError):
            intake.bind_admitted_actors({'A':SimpleNamespace(node_id='A')})
        with self.assertRaises(NativeForkError):
            intake.committed_actor_batch('C',1)
        intake.committed_actor_batch('A',2)
        with self.assertRaises(NativeForkError):
            intake.committed_actor_batch('A',1)
        port.close()
        with self.assertRaises(NativeForkError):
            intake.committed_actor_batch('A',3)
        self.assertEqual(intake.summary()['derived_actor_batch_receipts'],0)

    def test_record_custody_wrong_target_and_replay_rejected(self):
        port=ReceiverPortV2h()
        intake=ActorIntakeV2i(port)
        intake.bind_admitted_actors({'A':SimpleNamespace(node_id='A'),
                                     'B':SimpleNamespace(node_id='B')})
        occurrence={'id':'r1','source':'A','target':'B','channel':0,
                    'emitted_at':1,'parents':()}
        port.emission(occurrence,1)
        port.ingress(occurrence,2)
        port.batch('B',2,[(0,'r1')],[7])
        port.step(3)
        self.assertEqual(port.summary()['control_delivered'],1)
        intake.committed_actor_batch('B',3)
        self.assertEqual(len(intake.receipts('B')),0)
        intake.committed_actor_batch('A',3)
        self.assertEqual(len(intake.receipts('A')),1)
        intake.committed_actor_batch('A',3)
        self.assertEqual(len(intake.receipts('A')),1)
        with self.assertRaises(NativeForkError):
            port._deliver(port.judgments[0])
        port.close()
        self.assertEqual(intake.summary()['unconsumed_delivered_controls'],0)

    def test_injected_mailbox_record_fails_before_any_receipt(self):
        port=ReceiverPortV2h()
        intake=ActorIntakeV2i(port)
        intake.bind_admitted_actors({'A':SimpleNamespace(node_id='A'),
                                     'B':SimpleNamespace(node_id='B')})
        occurrence={'id':'r1','source':'A','target':'B','channel':0,
                    'emitted_at':1,'parents':()}
        port.emission(occurrence,1)
        port.ingress(occurrence,2)
        port.batch('B',2,[(0,'r1')],[7])
        port.step(3)
        forged=replace(port.judgments[0], identity='j-fake',recipient='B')
        port._mailboxes['A'].append(forged)
        with self.assertRaises(NativeForkError):
            intake.committed_actor_batch('A',3)
        self.assertEqual(intake.receipts('A'),())

    def test_post_native_delivery_is_not_relabelled_as_actor_intake(self):
        port=ReceiverPortV2h(latency=5)
        intake=ActorIntakeV2i(port)
        intake.bind_admitted_actors({'A':SimpleNamespace(node_id='A'),
                                     'B':SimpleNamespace(node_id='B')})
        occurrence={'id':'r1','source':'A','target':'B','channel':0,
                    'emitted_at':1,'parents':()}
        port.emission(occurrence,1)
        port.ingress(occurrence,2)
        port.batch('B',2,[(0,'r1')],[7])
        intake.committed_actor_batch('A',3)
        port.close()
        s=intake.summary()
        self.assertEqual(s['post_native_deliveries_not_native_intake'],1)
        self.assertEqual(s['derived_actor_batch_receipts'],0)
        self.assertEqual(s['unconsumed_delivered_controls'],1)
        self.assertEqual(s['delivered_during_native_unconsumed'],0)

    def test_configuration_and_pinned_source_drift_rejected(self):
        port=ReceiverPortV2h()
        for args in ({'max_receipts':True},{'max_receipts':0},
                     {'per_batch':0},{'per_batch':65}):
            with self.subTest(args=args):
                with self.assertRaises(NativeForkError):
                    ActorIntakeV2i(port,**args)
        intake=ActorIntakeV2i(port)
        with self.assertRaises(NativeForkError):
            derive_actor_intake_executor(SOURCE.read_bytes()+b'\n',
                execute_live_v0e,port,intake,CallsiteObserver())

    def test_15_native_recipe_parity(self):
        case,fabric,plans=fixture()
        for label,recipe in RECIPES:
            with self.subTest(label=label):
                changed=build_workload(case,recipe)
                port=ReceiverPortV2h()
                intake=ActorIntakeV2i(port)
                derived,_,_=derive_actor_intake_executor(
                    SOURCE.read_bytes(),execute_live_v0e,port,intake,CallsiteObserver())
                base=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                observed=derived(changed,fabric,*plans,LiveBVPlanV0e())
                port.close()
                self.assertEqual(base,observed)
                self.assertEqual(intake.summary()['delivered_controls'],
                                 len(base['forward']['occurrences']))

    def test_predecessor_tampering_fails_closed(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('v2h predecessor not mounted locally')
        obj=json.loads(raw)
        self.assertTrue(validate_v2h(obj,raw))
        for field,value in (('full_native_result_parity_cells',44),
                            ('frozen_native_actor_receives_research_control',True),
                            ('native_learning_proven',True)):
            with self.subTest(field=field):
                changed=dict(obj);changed[field]=value
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2h(changed,canon(changed))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2h(obj,raw+b'\n')

    def test_pinned_matrix_gate_and_canonical_report(self):
        raw=predecessor_bytes()
        if raw is None:self.skipTest('v2h predecessor not mounted locally')
        obj=json.loads(raw)
        self.assertEqual(build_report(obj,raw)['status'],CONTRACT_STATUS)
        result=experiment(obj,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(obj,raw,result)
        self.assertEqual(report['status'],STATUS)
        self.assertEqual(report['full_native_result_parity_cells'],45)
        self.assertEqual(report['actor_intake_totals']['delivered_controls'],156)
        self.assertEqual(report['actor_intake_totals']['derived_actor_batch_receipts'],52)
        self.assertEqual(report['actor_intake_totals']['unconsumed_delivered_controls'],104)
        self.assertEqual(report['actor_intake_totals']['delivered_during_native_unconsumed'],89)
        self.assertEqual(report['negative_native_fixture']['derived_actor_receipts'],1)
        self.assertFalse(report['frozen_native_actor_intake_observed'])
        self.assertFalse(report['native_learning_proven'])
        self.assertEqual(canon(report),canon(json.loads(canon(report))))


if __name__ == '__main__':
    unittest.main()
