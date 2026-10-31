"""BV v2s-v2u cumulative source-backed concurrent actor service research gate."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, NativeForkError, PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import (
    ConcurrentConsumerPlan, DerivedConcurrentConsumer, derive_concurrent_executor,
)
from spk_bv_research.concurrent_consumer_cumulative_v2stu import (
    PREDECESSOR_SHA, CONTRACT, STATUS, validate_v2r, build_report,
    _negative_fixture, _bounded_horizon, experiment,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.native_allocation_boundary_v1r import canon

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORT_PATHS = (
    Path('/tmp/spk-bv-v2r-three-way-causal-priority.json'),
    ROOT.parent.parent / 'spk-bv-v2r-three-way-causal-priority.json',
)


def signed_v2r():
    env = os.environ.get('SPK_V2R_REPORT')
    for path in ([Path(env)] if env else []) + list(REPORT_PATHS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*, capacity=1, forward=True, bv=True, consumer=None,
            credit=None, receiver=None, case=None, max_ticks=256):
    initial, fabric, plans = fixture()
    plans = (plans[0], replace(plans[1], fabric_slots_per_tick=capacity),
             plans[2], plans[3])
    port = ReceiverPortV2h(**(receiver or {}))
    actor = DerivedConcurrentConsumer(port,
        concurrent_plan=consumer or ConcurrentConsumerPlan(),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        credit_plan=credit or ActorCreditPlanV2l())
    observer = CallsiteObserver()
    compiled, _, semantic, anchors = derive_concurrent_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, actor, observer)
    selected = initial if case is None else case
    bvplan = LiveBVPlanV0e(max_ticks=max_ticks)
    native = execute_live_v0e(selected, fabric, *plans, bvplan)
    derived = compiled(selected, fabric, *plans, bvplan)
    projected = actor.project_original_native_result(derived)
    return native, derived, projected, actor, port, observer, semantic, anchors


class TestV2stuConcurrentCumulative(unittest.TestCase):

    def test_source_pinned_and_frozen_native_unmodified(self):
        native, raw, proj, s, _, observer, semantic, anchors = one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        self.assertEqual(anchors, (158, 296, 307))
        self.assertEqual(semantic, (('batch', 194), ('clock', 125),
                                    ('emission', 217), ('ingress', 136)))
        self.assertEqual(observer.counts()['_admit'], 1)
        self.assertNotIn('__v2o_causal_admission', execute_live_v0e.__globals__)
        self.assertNotIn('__v2k_admission', execute_live_v0e.__globals__)
        self.assertEqual(proj, native)
        self.assertEqual(s.summary()['native_operator_updates'], 0)

    def test_strict_native_priority_and_independent_resource_custody(self):
        for capacity in (1, 3):
            with self.subTest(capacity=capacity):
                native, raw, projection, s, *_ = one_run(capacity=capacity)
                self.assertEqual(projection, native)
                self.assertEqual(len(s.credit_journal()), 4)
                self.assertEqual(len(s.concurrent_journal()), 4)
                self.assertEqual(s.summary()['concurrent_consumer_PE_units'], 4)
                self.assertEqual(s.summary()['concurrent_consumer_memory_units'], 8)
                self.assertEqual(s.summary()['derived_independent_consumer_PE_units'], 0)
                self.assertTrue(s.summary()['v2q_post_forward_lane_disabled'])

    def test_genuine_pre_forward_consumer_changes_source_timing(self):
        for forward, bv in ((False, True), (False, False)):
            with self.subTest(forward=forward, bv=bv):
                n, _, projection, s, *_ = one_run(forward=forward, bv=bv)
                _, _, no_consumer, disabled, *_ = one_run(forward=forward, bv=bv,
                    consumer=ConcurrentConsumerPlan(max_per_tick=0))
                self.assertNotEqual(projection['forward'], no_consumer['forward'])
                self.assertEqual(_payload(projection['forward']), _payload(n['forward']))
                self.assertGreater(s.summary()['concurrent_before_forward_applications'], 0)
                self.assertEqual(disabled.summary()['concurrent_paid_applications'], 0)
                self.assertEqual(disabled.summary()['concurrent_pending_acks'], 4)

    def test_pre_forward_is_its_true_receipt_phase_not_relabelled(self):
        _, _, _, actor, _, _, _, _ = one_run(forward=False, bv=False)
        receipts = actor.concurrent_journal()
        pre = [r for r in receipts if r['consume_phase'] == 'before-native-forward']
        self.assertEqual(len(pre), 4)
        self.assertTrue(all(r['consume_tick'] >= r['ack_service_tick'] for r in pre))
        self.assertTrue(all(r['pe_service_units'] == 1 and r['memory_units'] == 2
                            for r in receipts))
        self.assertTrue(all(r['consume_phase'] != 'after-native-forward'
                            for r in receipts))

    def test_15_native_workloads_across_two_capacity_regimes(self):
        case, _, _ = fixture()
        for label, recipe in RECIPES:
            chosen = build_workload(case, recipe)
            for capacity in (1, 3):
                with self.subTest(label=label, capacity=capacity):
                    native, _, projected, s, *_ = one_run(case=chosen, capacity=capacity)
                    self.assertEqual(projected, native)
                    self.assertEqual(len(s.concurrent_journal()), len(s.credit_journal()))

    def test_no_tail_defers_acks_not_negative_evidence(self):
        _, _, projected, s, port, *_ = one_run(
            consumer=ConcurrentConsumerPlan(max_tail_ticks=0))
        self.assertEqual(s.summary()['concurrent_consumer_tail_rows'], 0)
        self.assertGreaterEqual(s.summary()['concurrent_pending_acks'], 0)
        self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_zero_credit_and_transport_loss_are_causal_null_controls(self):
        for policy in ('loss', 'zero'):
            with self.subTest(policy=policy):
                options = {'receiver': {'accept': lambda _: False}} if policy == 'loss' else {
                    'credit': ActorCreditPlanV2l(max_abs_credit=0)}
                n, _, p, s, port, *_ = one_run(forward=False, bv=False, **options)
                self.assertEqual(p, n)
                self.assertFalse(s.credit_journal())
                self.assertFalse(s.concurrent_journal())
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_all_three_competing_classes_are_distinct(self):
        _, _, _, s, _, _, _, _ = one_run(capacity=3, forward=False, bv=False)
        self.assertGreater(s.summary()['pre_forward_actor_grants'], 0)
        self.assertGreater(s.summary()['concurrent_before_forward_applications'], 0)
        self.assertGreater(s.summary()['native_original_timeline_rows'], 0)
        self.assertEqual(s.summary()['derived_independent_consumer_PE_units'], 0)

    def test_receipt_digest_replay_and_actor_ownership_fail_closed(self):
        for mutation in ('digest', 'actor', 'phase', 'tick', 'resource', 'duplicate'):
            with self.subTest(mutation=mutation):
                _, result, _, s, *_ = one_run(forward=False, bv=False)
                receipts = s._v2s_receipts
                old = receipts[0]
                if mutation == 'digest':
                    receipts[0] = replace(old, chain_digest='f'*64)
                elif mutation == 'actor':
                    receipts[0] = replace(old, actor='C')
                elif mutation == 'phase':
                    receipts[0] = replace(old, consume_phase='after-native-forward')
                elif mutation == 'tick':
                    receipts[0] = replace(old, consume_tick=0)
                elif mutation == 'resource':
                    receipts[0] = replace(old, memory_units=0)
                else:
                    receipts.append(old)
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_trace_capacity_and_source_probes_tampering_rejected(self):
        for mutation in ('pe', 'domain', 'source', 'reason', 'receipt'):
            with self.subTest(mutation=mutation):
                _, result, _, s, *_ = one_run(forward=False, bv=False)
                target = next(x for x in s._v2s_trace if x['receipts'])
                if mutation == 'pe':
                    target['after']['pe_service_total'] += 1
                elif mutation == 'domain':
                    target['after']['memory_by_domain']['O'] += 1
                elif mutation == 'source':
                    target['source_PE_budget'] += 1
                elif mutation == 'reason':
                    target['reject_reason'] = 'invented'
                else:
                    target['receipts'][0] = 'f'*64
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_forged_receiver_mailbox_before_three_way_service_fails_closed(self):
        case, fabric, plans = fixture()
        port = ReceiverPortV2h(latency=16)
        actor = DerivedConcurrentConsumer(port,
            admission_plan=CausalAdmissionPlanV2o(False, False))
        compiled, *_ = derive_concurrent_executor(
            SOURCE.read_bytes(), execute_live_v0e, port, actor, CallsiteObserver())
        ordinary = port.batch
        injected = [False]

        def spoof(actor_id, tick, items, outputs):
            ordinary(actor_id, tick, items, outputs)
            if port.judgments and not injected[0]:
                record = port.judgments[0]
                port._mailboxes.setdefault(record.recipient, []).append(
                    replace(record, identity='forged-v2s-causal-mailbox'))
                injected[0] = True

        port.batch = spoof
        with self.assertRaises(NativeForkError):
            compiled(case, fabric, *plans, LiveBVPlanV0e())

    def test_modified_signed_ack_refused_before_consumer_projection(self):
        _, result, _, actor, *_ = one_run(forward=False, bv=False)
        actor._acks[0] = replace(actor._acks[0], chain_digest='e'*64)
        with self.assertRaises(NativeForkError):
            actor.project_original_native_result(result)

    def test_bounded_concurrent_one_turn_FIFO_and_paid_memory(self):
        _, _, _, s, _, _, _, _ = one_run(forward=False, bv=False)
        rows = s.concurrent_trace()
        self.assertTrue(all(len(row['receipts']) <= 1 for row in rows))
        self.assertEqual(sum(len(row['receipts']) for row in rows), 4)
        self.assertTrue(all(row['after']['pe_service_total'] -
                            row['before']['pe_service_total'] == len(row['receipts'])
                            for row in rows))
        self.assertTrue(all(row['after']['memory_total'] -
                            row['before']['memory_total'] == 2*len(row['receipts'])
                            for row in rows))

    def test_inline_and_tail_mutations_refuse_full_native_projection(self):
        for mutation in ('native', 'tail'):
            with self.subTest(mutation=mutation):
                _, result, _, s, *_ = one_run()
                if mutation == 'native':
                    result['resources']['timeline'][-len(s._v2s_tail)-1][
                        'pe_service_total'] += 1
                else:
                    result['resources']['timeline'][-1]['memory_total'] += 2
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_negative_B_is_real_actor_A_without_native_learning(self):
        case, fabric, plans = fixture()
        evidence = _negative_fixture(SOURCE.read_bytes(), case, fabric, plans,
                                     execute_live_v0e, LiveBVPlanV0e)
        self.assertEqual(evidence['real_negative_B_judgments'], 2)
        self.assertEqual(evidence['applied_to'], 'A')
        self.assertEqual(evidence['concurrent_credit_A'], -2)
        self.assertFalse(evidence['native_learning_observed'])

    def test_bounded_horizon_is_not_universal_liveness_certificate(self):
        case, fabric, plans = fixture()
        bound = _bounded_horizon(SOURCE.read_bytes(), case, fabric, plans,
                                 execute_live_v0e, LiveBVPlanV0e)
        self.assertEqual(bound['max_ticks'], 11)
        self.assertEqual(bound['guard_modes']['strict_native_ready'],
                         'EXACT_NATIVE_PARITY_IN_DERIVED_HORIZON')
        self.assertFalse(bound['universal_liveness_proven'])

    def test_invalid_policy_and_compiler_source_drift_fail_closed(self):
        for invalid in (ConcurrentConsumerPlan(max_per_tick=-1),
                        ConcurrentConsumerPlan(max_total=513),
                        ConcurrentConsumerPlan(max_tail_ticks=129),
                        ConcurrentConsumerPlan(max_per_tick=True)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(NativeForkError):
                    DerivedConcurrentConsumer(ReceiverPortV2h(), concurrent_plan=invalid)
        port = ReceiverPortV2h()
        actor = DerivedConcurrentConsumer(port)
        with self.assertRaises(NativeForkError):
            derive_concurrent_executor(SOURCE.read_bytes()+b'\n# mutation',
                execute_live_v0e, port, actor, CallsiteObserver())

    def test_signed_predecessor_contract_and_mutation_fail_closed(self):
        raw = signed_v2r()
        if raw is None:
            self.skipTest('signed v2r predecessor not available')
        previous = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v2r(previous, raw))
        contract = build_report(previous, raw)
        self.assertEqual(contract['status'], CONTRACT)
        self.assertFalse(contract['frozen_native_concurrent_three_way_arbiter_proven'])
        amended = json.loads(raw)
        amended['new_native_runs'] = 1
        with self.assertRaises(ValueError):
            build_report(amended, canon(amended))
        with self.assertRaises(ValueError):
            build_report(previous, raw+b' ')

    def test_cumulative_full_native_resource_matrix_report(self):
        raw = signed_v2r()
        if raw is None:
            self.skipTest('signed v2r predecessor not available')
        previous = json.loads(raw)
        result = experiment(previous, raw, root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(previous, raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertGreater(report['causal_consumer_forward_witness_cells'], 0)
        self.assertEqual(report['new_derived_three_way_guard_runs'], 360)
        self.assertEqual(report['new_derived_causal_intervention_runs'], 180)
        self.assertFalse(report['frozen_native_concurrent_three_way_arbiter_proven'])


if __name__ == '__main__':
    unittest.main()
