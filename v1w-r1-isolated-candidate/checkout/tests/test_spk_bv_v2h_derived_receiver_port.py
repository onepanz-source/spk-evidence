"""BV v2h executable native-backed and adversarial contracts (stdlib unittest)."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, NativeForkError, PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ReceiverPortV2h, EmissionV2h, JudgmentV2h, derive_receiver_executor, PORT_VERSION,
)
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES, build_workload
from spk_bv_research.receiver_port_integration_v2h import (
    validate_v2g, experiment, build_report, STATUS, CONTRACT_STATUS,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from search.spk_bv_v0e_live_evidence import fixture

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORT_CANDIDATES = (
    Path('/tmp/spk-bv-v2g-derived-native-callsite-parity.json'),
    Path('/mnt/data/spk-bv-v2g-derived-native-callsite-parity.json'),
)


def report_raw():
    configured=os.environ.get('SPK_V2G_REPORT')
    if configured and Path(configured).is_file():
        return Path(configured).read_bytes()
    for p in REPORT_CANDIDATES:
        if p.is_file():
            return p.read_bytes()
    return None


def run_derived(case=None, plan=None, **port_options):
    fc, fabric, plans = fixture()
    if case is None:
        case = fc
    if plan is None:
        plan = LiveBVPlanV0e()
    port = ReceiverPortV2h(**port_options)
    watcher = CallsiteObserver()
    derived, calls, anchors = derive_receiver_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, watcher)
    original = execute_live_v0e(case, fabric, *plans, plan)
    actual = derived(case, fabric, *plans, plan)
    port.close()
    return original, actual, port, watcher, anchors


class TestV2hDerivedReceiverPort(unittest.TestCase):

    def test_source_pin_and_semantic_anchors(self):
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        base, der, port, obs, anchors = run_derived()
        self.assertEqual(base, der)
        self.assertEqual(dict(anchors), {'batch':194,'clock':125,
                                         'emission':217,'ingress':136})
        self.assertEqual(obs.counts(), {'_admit':1,'_admit_plan':1,
                                        'offer_feedback':6})
        self.assertEqual(port.summary()['port_version'], PORT_VERSION)
        self.assertEqual(port.summary()['control_delivered'], 4)
        self.assertEqual(port.summary()['credit_by_sender'], {'A':2,'B':2})
        self.assertFalse(port.summary()['frozen_actor_state_receives_feedback'])
        self.assertNotIn('__v2h_port', execute_live_v0e.__globals__)
        self.assertNotIn('__spk_v2g_wrap', execute_live_v0e.__globals__)

    def test_real_negative_B_judgment(self):
        case,_,_=fixture()
        block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
        altered=replace(case,nodes=tuple(
            replace(node,instructions=block) if node.node_id=='B' else node
            for node in case.nodes))
        base, der, port, _, _ = run_derived(case=altered)
        self.assertEqual(base, der)
        self.assertEqual(port.summary()['positive_judgments'],0)
        self.assertEqual(port.summary()['negative_judgments'],2)
        self.assertEqual(port.summary()['credit_by_sender'],{'A':-2})
        self.assertEqual(port.summary()['absence_certificates'],0)

    def test_off_and_on_bv_forward_result_parity(self):
        for enabled,priority in ((False,'forward-first'),
                                 (True,'forward-first'),(True,'feedback-first')):
            with self.subTest(enabled=enabled,priority=priority):
                a,b,port,_,_=run_derived(plan=LiveBVPlanV0e(
                    enabled=enabled,priority=priority))
                self.assertEqual(a,b)
                self.assertEqual(port.summary()['native_ingress_events'],4)
                self.assertEqual(port.summary()['receiver_local_judgments'],4)

    def test_15_native_workloads_remain_exactly_equal(self):
        case,fabric,plans=fixture()
        raw=SOURCE.read_bytes()
        for name,recipe in RECIPES:
            with self.subTest(name=name):
                changed=build_workload(case,recipe)
                box=ReceiverPortV2h()
                monitor=CallsiteObserver()
                derived,_,_=derive_receiver_executor(raw,execute_live_v0e,box,monitor)
                base=execute_live_v0e(changed,fabric,*plans,LiveBVPlanV0e())
                got=derived(changed,fabric,*plans,LiveBVPlanV0e())
                box.close()
                self.assertEqual(base,got)
                self.assertEqual(box.summary()['source_owned_emissions'],
                                 len(base['forward']['occurrences']))
                self.assertEqual(box.summary()['control_delivered'],
                                 len(base['forward']['occurrences']))

    def test_receiver_loss_and_overflow_are_not_silence_proofs(self):
        for label,options in (
            ('loss',{'accept':lambda _:False}),
            ('fault',{'accept':lambda _:(_ for _ in ()).throw(RuntimeError('offline'))}),
            ('overflow',{'capacity':1}),
            ('feedback_off',{'feedback':False}),
        ):
            with self.subTest(label=label):
                base,der,port,_,_=run_derived(**options)
                self.assertEqual(base,der)
                s=port.summary()
                self.assertEqual(s['receiver_local_judgments'],4)
                self.assertEqual(s['absence_certificates'],0)
                if label=='loss':
                    self.assertEqual(s['lost'],4)
                if label=='fault':
                    self.assertEqual(s['fault_lost'],4)
                if label=='overflow':
                    self.assertTrue(s['queue_overflow'] or s['mailbox_overflow'])
                if label=='feedback_off':
                    self.assertEqual(s['control_delivered'],0)

    def test_forgery_replay_and_wrong_actor_rejected(self):
        port=ReceiverPortV2h()
        occ={'id':'r1','source':'A','target':'B','channel':0,
             'emitted_at':1,'parents':()}
        port.emission(occ,1)
        with self.assertRaises(NativeForkError):port.emission(occ,1)
        with self.assertRaises(NativeForkError):port.ingress({**occ,'target':'C'},2)
        with self.assertRaises(NativeForkError):port.ingress(occ,1)
        port.ingress(occ,2)
        with self.assertRaises(NativeForkError):port.ingress(occ,2)
        with self.assertRaises(NativeForkError):port.batch('C',2,[(0,'r1')],[7])
        port.batch('B',2,[(0,'r1')],[7])
        with self.assertRaises(NativeForkError):port.batch('B',2,[(0,'r1')],[7])
        verdict=port.judgments[0]
        with self.assertRaises(NativeForkError):port._deliver(verdict)
        with self.assertRaises(NativeForkError):port._deliver(replace(verdict,recipient='C'))
        port.step(3)
        self.assertEqual(port.summary()['control_delivered'],1)
        with self.assertRaises(NativeForkError):port._deliver(verdict)
        port.close()
        with self.assertRaises(NativeForkError):port.step(4)

    def test_pin_drift_and_invalid_configuration_fail_closed(self):
        with self.assertRaises(NativeForkError):ReceiverPortV2h(capacity=True)
        with self.assertRaises(NativeForkError):ReceiverPortV2h(latency=0)
        with self.assertRaises(NativeForkError):ReceiverPortV2h(accept=1)
        with self.assertRaises(NativeForkError):derive_receiver_executor(
            SOURCE.read_bytes()+b'\n',execute_live_v0e,ReceiverPortV2h(),CallsiteObserver())

    def test_v2g_predecessor_mutations_fail_closed(self):
        raw=report_raw()
        if raw is None:self.skipTest('signed-off v2g predecessor not locally mounted')
        native=json.loads(raw)
        self.assertTrue(validate_v2g(native,raw))
        for field, forged in (
            ('full_native_report_parity_cells',44),
            ('native_receiver_endogenous_judgments',1),
            ('derived_scheduler_is_frozen_scheduler',True),
            ('new_derived_fault_and_overflow_runs',89),
        ):
            with self.subTest(field=field):
                changed=dict(native);changed[field]=forged
                with self.assertRaises((ValueError,TypeError)):
                    validate_v2g(changed,canon(changed))
        with self.assertRaises((ValueError,TypeError)):
            validate_v2g(native,raw+b'\n')

    def test_full_native_report_and_gate_determinism(self):
        raw=report_raw()
        if raw is None:self.skipTest('signed-off v2g predecessor not locally mounted')
        native=json.loads(raw)
        report=build_report(native,raw)
        self.assertEqual(report['status'],CONTRACT_STATUS)
        self.assertEqual(report['new_native_original_runs'],0)
        result=experiment(native,raw,root=ROOT,fixture_fn=fixture,
                          native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        full=build_report(native,raw,result)
        self.assertEqual(full['status'],STATUS)
        self.assertEqual(full['full_native_result_parity_cells'],45)
        self.assertEqual(full['new_native_original_runs'],45)
        self.assertEqual(full['new_derived_normal_runs'],45)
        self.assertEqual(full['new_derived_fault_runs'],135)
        self.assertEqual(full['actor_semantic_totals']['control_delivered'],156)
        self.assertEqual(full['negative_real_actor_judgments'],2)
        self.assertFalse(full['frozen_native_actor_receives_research_control'])
        self.assertFalse(full['native_learning_proven'])
        self.assertEqual(canon(full),canon(json.loads(canon(full))))


if __name__=='__main__':
    unittest.main()
