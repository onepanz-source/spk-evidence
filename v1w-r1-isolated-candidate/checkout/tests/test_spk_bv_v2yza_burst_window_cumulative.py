"""Source-owned consecutive queue-contention, finite window and causal audit."""
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
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import ConcurrentConsumerPlan
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor,
)
from spk_backvalidation_v2.derived_actor_burst_window_v2y import (
    BurstWindowPressurePlan, validate_burst_pressure, audit_burst_window,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.burst_window_cumulative_v2yza import (
    PREDECESSOR_SHA, CONTRACT, STATUS, validate_v2vwx, build_report,
    experiment, _run_derived,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v2vwx-queue-precedence-cumulative.json'),
           ROOT.parent.parent / 'spk-bv-v2vwx-queue-precedence-cumulative.json')


def signed_previous():
    env = os.environ.get('SPK_V2VWX_REPORT')
    for path in ([Path(env)] if env else []) + list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*, policy='bounded-turns', chosen=None,
            enabled=True, priority='forward-first',
            forward=False, bv=False, ACK_quota=2, latency=2,
            consumer=None, credit=None, receiver=None):
    initial, fabric, plans = fixture()
    plans = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
             plans[2], plans[3])
    case = (build_workload(initial, RECIPES[7][1])
            if chosen is None else chosen)
    native_plan = LiveBVPlanV0e(enabled=enabled, priority=priority)
    port = ReceiverPortV2h(latency=latency, **(receiver or {}))
    actor = DerivedActorQueueFairnessV2v(port,
        queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        concurrent_plan=consumer or ConcurrentConsumerPlan(),
        credit_plan=credit or ActorCreditPlanV2l(),
        service_plan=ShadowServicePlanV2j(max_per_tick=ACK_quota))
    observer = CallsiteObserver()
    compiled, _, semantic, anchors = derive_queue_fairness_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, actor, observer)
    native = execute_live_v0e(case, fabric, *plans, native_plan)
    derived = compiled(case, fabric, *plans, native_plan)
    projected = actor.project_original_native_result(derived)
    return native, derived, projected, actor, port, observer, semantic, anchors


class TestV2yzaBurstQueueWindow(unittest.TestCase):
    def test_typed_source_window_plan_and_frozen_native_source(self):
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        self.assertEqual(validate_burst_pressure(BurstWindowPressurePlan()),
                         BurstWindowPressurePlan())
        for invalid in (BurstWindowPressurePlan(ACK_max_per_tick=1),
                        BurstWindowPressurePlan(feedback_latency=1),
                        BurstWindowPressurePlan(global_PE_slots_per_tick=3),
                        BurstWindowPressurePlan(consumer_max_per_tick=True),
                        BurstWindowPressurePlan(bounded_consecutive_consumer_turns=0)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(NativeForkError):
                    validate_burst_pressure(invalid)
        _, _, _, actor, _, observer, semantic, anchors = one_run()
        self.assertEqual(semantic, (('batch', 194), ('clock', 125),
                                    ('emission', 217), ('ingress', 136)))
        self.assertEqual(anchors, (158, 296, 307))
        self.assertEqual(observer.counts()['_admit'], 1)
        self.assertEqual(actor.summary()['native_operator_updates'], 0)
        self.assertNotIn('__v2k_admission', execute_live_v0e.__globals__)

    def test_source_owned_two_contending_consumer_turns_are_real(self):
        _, _, _, actor, port, *_ = one_run(policy='consumer-first')
        witness = audit_burst_window(actor)
        self.assertGreaterEqual(witness['max_competing_consumer_streak'], 2)
        self.assertGreater(witness['source_queue_collision_ticks'], 0)
        self.assertEqual(port.summary()['source_owned_emissions'],
                         port.summary()['native_ingress_events'])
        self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_finite_ACK_window_activates_and_accounts_actual_grants(self):
        _, _, _, actor, _, *_ = one_run(policy='bounded-turns')
        witness = audit_burst_window(actor)
        self.assertGreater(witness['eligible_bounded_turn_windows'], 0)
        self.assertGreater(witness['forced_ACK_preference_windows'], 0)
        self.assertGreater(witness['ACK_pre_forward_grants_on_forced_windows'], 0)
        self.assertLessEqual(witness['max_competing_consumer_streak'], 1)
        self.assertFalse(witness['universal_queue_liveness_proven'])

    def test_limit_changes_two_independent_causal_journals(self):
        native, _, unbounded, actor_a, *_ = one_run(policy='consumer-first')
        _, _, bounded, actor_b, *_ = one_run(policy='bounded-turns')
        self.assertNotEqual(actor_a.credit_journal(), actor_b.credit_journal())
        self.assertNotEqual(actor_a.concurrent_journal(), actor_b.concurrent_journal())
        self.assertEqual(_payload(unbounded['forward']), _payload(bounded['forward']))
        self.assertEqual(_payload(native['forward']), _payload(bounded['forward']))

    def test_strict_frozen_native_parity_all_three_priorities(self):
        for policy in ('ACK-first', 'consumer-first', 'bounded-turns'):
            with self.subTest(policy=policy):
                native, _, projected, actor, *_ = one_run(
                    policy=policy, forward=True, bv=True)
                self.assertEqual(native, projected)
                self.assertEqual(len(actor.credit_journal()),
                                 len(actor.concurrent_journal()))

    def test_ACK_quota_and_latency_ablate_long_streak_without_silence_claim(self):
        for options in ({'ACK_quota': 1}, {'latency': 1}):
            with self.subTest(options=options):
                _, _, _, actor, port, *_ = one_run(**options)
                self.assertLess(actor.summary()['max_observed_competing_consumer_streak'], 2)
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_loss_or_zero_credit_restores_entire_original_native(self):
        for options in ({'receiver': {'accept': lambda _: False}},
                        {'credit': ActorCreditPlanV2l(max_abs_credit=0)}):
            with self.subTest(options=options):
                native, _, projection, actor, port, *_ = one_run(**options)
                self.assertEqual(native, projection)
                self.assertFalse(actor.credit_journal())
                self.assertFalse(actor.concurrent_journal())
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_zero_consumer_preserves_pending_delivered_credit(self):
        _, _, _, actor, port, *_ = one_run(
            consumer=ConcurrentConsumerPlan(max_per_tick=0))
        self.assertTrue(actor.credit_journal())
        self.assertFalse(actor.concurrent_journal())
        self.assertEqual(actor.summary()['concurrent_pending_acks'],
                         len(actor.credit_journal()))
        self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_burst_window_forgery_and_replay_fail_closed(self):
        for mutation in ('choice', 'streak', 'backlog', 'source'):
            with self.subTest(mutation=mutation):
                _, derived, _, actor, *_ = one_run()
                row = next(r for r in actor._v2v_probes
                           if r['consumer_priority_streak_before'] > 0 and
                              r['ready_ACKs_before'] > 0)
                if mutation == 'choice':
                    row['selected'] = 'consumer-first'
                elif mutation == 'streak':
                    row['consumer_priority_streak_before'] += 1
                elif mutation == 'backlog':
                    row['consumer_backlog_before'] += 1
                else:
                    row['ready_forward_before'] += 1
                with self.assertRaises(NativeForkError):
                    actor.project_original_native_result(derived)

    def test_source_ACK_and_consumer_receipt_chain_forgery_rejected(self):
        for mutation in ('ACK', 'paid'):
            with self.subTest(mutation=mutation):
                _, derived, _, actor, *_ = one_run()
                if mutation == 'ACK':
                    actor._acks[0] = replace(actor._acks[0], chain_digest='8'*64)
                else:
                    actor._v2s_receipts[0] = replace(
                        actor._v2s_receipts[0], chain_digest='8'*64)
                with self.assertRaises(NativeForkError):
                    actor.project_original_native_result(derived)

    def test_real_resource_overcount_rejected_by_native_projection(self):
        _, derived, _, actor, *_ = one_run()
        derived['resources']['timeline'][0]['memory_total'] += 2
        with self.assertRaises(NativeForkError):
            actor.project_original_native_result(derived)

    def test_mailbox_injection_rejected_before_any_burst_grant(self):
        case, fabric, plans = fixture()
        plans = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                 plans[2], plans[3])
        port = ReceiverPortV2h(latency=2)
        actor = DerivedActorQueueFairnessV2v(port,
            queue_plan=ActorQueuePlanV2v('bounded-turns'),
            admission_plan=CausalAdmissionPlanV2o(False, False),
            service_plan=ShadowServicePlanV2j(max_per_tick=2))
        compiled, *_ = derive_queue_fairness_executor(
            SOURCE.read_bytes(), execute_live_v0e, port, actor, CallsiteObserver())
        original_batch = port.batch
        injected = [False]

        def forged_batch(source, tick, items, outputs):
            original_batch(source, tick, items, outputs)
            if port.judgments and not injected[0]:
                j = port.judgments[0]
                port._mailboxes.setdefault(j.recipient, []).append(
                    replace(j, identity='v2yza-forged-control'))
                injected[0] = True

        port.batch = forged_batch
        changed = build_workload(case, RECIPES[7][1])
        with self.assertRaises(NativeForkError):
            compiled(changed, fabric, *plans,
                     LiveBVPlanV0e(enabled=True, priority='forward-first'))

    def test_real_B_negative_judgment_remains_A_local_not_native_learning(self):
        initial, _, _ = fixture()
        negative = (('ACC', (1, 0)), ('CMP', 100), ('EMIT', 7), ('RESET', 0))
        changed = replace(initial, nodes=tuple(
            replace(n, instructions=negative) if n.node_id == 'B' else n
            for n in initial.nodes))
        native, _, projected, actor, port, *_ = one_run(
            chosen=changed, enabled=False, priority='forward-first')
        self.assertEqual(port.summary()['negative_judgments'], 2)
        self.assertEqual(actor.summary()['concurrent_consumer_credit']['A'], -2)
        self.assertEqual(_payload(native['forward']), _payload(projected['forward']))
        self.assertFalse(actor.summary()['frozen_actor_state_changed'])

    def test_signed_v2vwx_predecessor_and_contract_mutations_fail_closed(self):
        raw = signed_previous()
        if raw is None:
            self.skipTest('signed v2vwx predecessor unavailable')
        prev = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v2vwx(prev, raw))
        self.assertEqual(build_report(prev, raw)['status'], CONTRACT)
        self.assertFalse(build_report(prev, raw)[
            'universal_ACK_or_consumer_liveness_proven'])
        modified = json.loads(raw)
        modified['bounded_turn_limit_activated_cells'] = 1
        with self.assertRaises(ValueError):
            build_report(modified, canon(modified))
        with self.assertRaises(ValueError):
            build_report(prev, raw+b' ')

    def test_full_45_native_270_priority_225_causal_matrix(self):
        raw = signed_previous()
        if raw is None:
            self.skipTest('signed v2vwx predecessor unavailable')
        prev = json.loads(raw)
        report = build_report(prev, raw, experiment(prev, raw,
            root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e))
        self.assertEqual(report['status'], STATUS)
        self.assertEqual(report['bounded_window_activated_cells'], 7)
        self.assertEqual(report['bounded_window_activated_ticks'], 9)
        self.assertEqual(report['ACK_journal_bound_intervention_cells'], 7)
        self.assertEqual(report['bounded_overrun_cells'], 0)
        self.assertEqual(report['new_derived_ablation_runs'], 225)
        self.assertFalse(report['universal_ACK_or_consumer_liveness_proven'])


if __name__ == '__main__':
    unittest.main()
