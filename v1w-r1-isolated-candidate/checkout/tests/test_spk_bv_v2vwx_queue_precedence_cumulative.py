"""BV v2v-v2x signed native/ACK/consumer contention and negative controls."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, NativeForkError, PINNED_SCHED,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import ConcurrentConsumerPlan
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    POLICIES, ActorQueuePlanV2v, DerivedActorQueueFairnessV2v,
    derive_queue_fairness_executor,
)
from spk_bv_research.queue_precedence_pressure_integration_v2vwx import (
    PREDECESSOR_SHA, CONTRACT, STATUS, validate_v2stu, build_report, experiment,
)
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES, build_workload
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_priority_contention_integration_v2m import _payload

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v2stu-concurrent-cumulative.json'),
           ROOT.parent.parent / 'spk-bv-v2stu-concurrent-cumulative.json')


def previous_bytes():
    env = os.environ.get('SPK_V2STU_REPORT')
    for path in ([Path(env)] if env else []) + list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_run(*, policy='bounded-turns', capacity=1, forward=False, bv=False,
            latency=2, max_ACK_per_tick=1, consumer=None, credit=None,
            receiver=None, chosen=None):
    initial, fabric, plans = fixture()
    plans = (plans[0], replace(plans[1], fabric_slots_per_tick=capacity),
             plans[2], plans[3])
    port = ReceiverPortV2h(latency=latency, **(receiver or {}))
    actor = DerivedActorQueueFairnessV2v(port,
        queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        concurrent_plan=consumer or ConcurrentConsumerPlan(),
        credit_plan=credit or ActorCreditPlanV2l(),
        service_plan=ShadowServicePlanV2j(max_per_tick=max_ACK_per_tick))
    observer = CallsiteObserver()
    compiled, _, semantic, anchors = derive_queue_fairness_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, actor, observer)
    selected = initial if chosen is None else chosen
    native = execute_live_v0e(selected, fabric, *plans, LiveBVPlanV0e())
    raw = compiled(selected, fabric, *plans, LiveBVPlanV0e())
    projected = actor.project_original_native_result(raw)
    return native, raw, projected, actor, port, observer, semantic, anchors


class TestV2vwxQueuePrecedence(unittest.TestCase):

    def test_source_custody_three_way_and_frozen_native_unchanged(self):
        native, raw, projected, service, _, observer, semantic, anchors = one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        self.assertEqual(semantic, (('batch', 194), ('clock', 125),
                                    ('emission', 217), ('ingress', 136)))
        self.assertEqual(anchors, (158, 296, 307))
        self.assertEqual(observer.counts()['_admit'], 1)
        self.assertNotIn('__v2k_admission', execute_live_v0e.__globals__)
        self.assertEqual(service.summary()['native_operator_updates'], 0)

    def test_strict_source_priority_full_native_under_every_queue_policy(self):
        for capacity in (1, 3):
            for policy in POLICIES:
                with self.subTest(capacity=capacity, policy=policy):
                    native, raw, projected, s, *_ = one_run(
                        policy=policy, capacity=capacity, forward=True, bv=True)
                    self.assertEqual(projected, native)
                    self.assertEqual(len(s.credit_journal()), 4)
                    self.assertEqual(len(s.concurrent_journal()), 4)
                    self.assertEqual(s.summary()['concurrent_consumer_memory_units'], 8)

    def test_causal_queue_collisions_are_source_owned_not_synthetic_messages(self):
        case, _, _ = fixture()
        chosen = build_workload(case, ((0, 1),))
        _, _, _, s, port, *_ = one_run(policy='consumer-first', chosen=chosen)
        collisions = [r for r in s.queue_fairness_probes()
                      if r['consumer_backlog_before'] and r['ready_ACKs_before']]
        self.assertTrue(collisions)
        self.assertGreater(s.summary()['ready_ACK_candidates_withheld_pre_forward'], 0)
        self.assertEqual(port.summary()['source_owned_emissions'],
                         port.summary()['native_ingress_events'])
        self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_ACK_first_vs_consumer_first_causally_changes_ACK_journal(self):
        case, _, _ = fixture()
        chosen = build_workload(case, ((0, 1),))
        native, _, pa, ack, *_ = one_run(policy='ACK-first', chosen=chosen)
        _, _, pc, consumer, *_ = one_run(policy='consumer-first', chosen=chosen)
        self.assertNotEqual(ack.credit_journal(), consumer.credit_journal())
        self.assertEqual(len(ack.credit_journal()), len(consumer.credit_journal()))
        self.assertEqual(pa['forward'], pc['forward'])
        self.assertEqual(consumer.summary()['concurrent_consumer_PE_units'], 2)

    def test_bounded_turns_obeys_one_turn_preference_without_liveness_claim(self):
        _, _, _, s, *_ = one_run()
        rows = s.queue_fairness_probes()
        self.assertTrue(all(r['consumer_priority_streak_after'] <= 1 for r in rows))
        self.assertFalse(s.summary()['universal_ACK_or_consumer_liveness_proven'])
        self.assertFalse(s.summary()['frozen_native_queue_priority_modified'])

    def test_original_15_organic_workloads_strict_capacity_and_policy(self):
        initial, _, _ = fixture()
        for label, recipe in RECIPES:
            for capacity in (1, 3):
                with self.subTest(label=label, capacity=capacity):
                    chosen = build_workload(initial, recipe)
                    n, _, p, s, *_ = one_run(chosen=chosen, capacity=capacity,
                                               forward=True, bv=True)
                    self.assertEqual(p, n)
                    self.assertEqual(len(s.credit_journal()), len(s.concurrent_journal()))

    def test_loss_and_credit_zero_restore_original_native(self):
        for intervention in ('loss', 'zero'):
            with self.subTest(intervention=intervention):
                opts = ({'receiver': {'accept': lambda _: False}}
                        if intervention == 'loss' else
                        {'credit': ActorCreditPlanV2l(max_abs_credit=0)})
                n, _, p, s, port, *_ = one_run(policy='consumer-first', **opts)
                self.assertEqual(n, p)
                self.assertFalse(s.credit_journal())
                self.assertFalse(s.concurrent_journal())
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_zero_consumer_throughput_leaves_delivered_ACK_pending(self):
        n, _, p, s, port, *_ = one_run(
            policy='consumer-first', consumer=ConcurrentConsumerPlan(max_per_tick=0))
        self.assertFalse(s.concurrent_journal())
        self.assertEqual(s.summary()['concurrent_pending_acks'], len(s.credit_journal()))
        self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_queue_choice_probe_forgery_and_replay_fail_closed(self):
        for mutation in ('selection', 'withheld', 'streak', 'backlog', 'source'):
            with self.subTest(mutation=mutation):
                _, result, _, s, *_ = one_run(policy='consumer-first')
                target = next(p for p in s._v2v_probes
                              if p['consumer_backlog_before'] > 0)
                if mutation == 'selection':
                    target['selected'] = 'ACK-first'
                elif mutation == 'withheld':
                    target['suppressed_ready_ACKs'] += 1
                elif mutation == 'streak':
                    target['consumer_priority_streak_after'] += 1
                elif mutation == 'backlog':
                    target['consumer_backlog_before'] += 1
                else:
                    target['ready_forward_before'] += 1
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_consumer_receipt_and_ACK_chain_tamper_rejected(self):
        for mutation in ('ACK', 'consumer'):
            with self.subTest(mutation=mutation):
                _, result, _, s, *_ = one_run(policy='consumer-first')
                if mutation == 'ACK':
                    s._acks[0] = replace(s._acks[0], chain_digest='9'*64)
                else:
                    s._v2s_receipts[0] = replace(
                        s._v2s_receipts[0], chain_digest='9'*64)
                with self.assertRaises(NativeForkError):
                    s.project_original_native_result(result)

    def test_resource_counter_projection_tamper_fails_closed(self):
        _, result, _, s, *_ = one_run(policy='consumer-first')
        result['resources']['timeline'][0]['pe_service_total'] += 1
        with self.assertRaises(NativeForkError):
            s.project_original_native_result(result)

    def test_forged_receiver_control_mailbox_rejected_before_queue_service(self):
        case, fabric, plans = fixture()
        port = ReceiverPortV2h(latency=2)
        s = DerivedActorQueueFairnessV2v(port,
            queue_plan=ActorQueuePlanV2v('consumer-first'),
            admission_plan=CausalAdmissionPlanV2o(False, False),
            service_plan=ShadowServicePlanV2j(max_per_tick=1))
        compiled, *_ = derive_queue_fairness_executor(
            SOURCE.read_bytes(), execute_live_v0e, port, s, CallsiteObserver())
        regular = port.batch
        injected = [False]

        def forge(actor, tick, items, outputs):
            regular(actor, tick, items, outputs)
            if port.judgments and not injected[0]:
                j = port.judgments[0]
                port._mailboxes.setdefault(j.recipient, []).append(
                    replace(j, identity='v2vwx-false-control'))
                injected[0] = True

        port.batch = forge
        with self.assertRaises(NativeForkError):
            compiled(case, fabric, *plans, LiveBVPlanV0e())

    def test_invalid_policy_bound_and_source_pin_rejected(self):
        for invalid in (ActorQueuePlanV2v(policy='unbounded'),
                        ActorQueuePlanV2v(max_consecutive_consumer_turns_with_ready_ACK=-1),
                        ActorQueuePlanV2v(max_consecutive_consumer_turns_with_ready_ACK=True),
                        ActorQueuePlanV2v(max_consecutive_consumer_turns_with_ready_ACK=17)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(NativeForkError):
                    DerivedActorQueueFairnessV2v(ReceiverPortV2h(), queue_plan=invalid)
        port = ReceiverPortV2h()
        s = DerivedActorQueueFairnessV2v(port)
        with self.assertRaises(NativeForkError):
            derive_queue_fairness_executor(SOURCE.read_bytes()+b'# drift',
                execute_live_v0e, port, s, CallsiteObserver())

    def test_real_B_negative_judgment_remains_actor_A_only(self):
        initial, _, _ = fixture()
        negative = (('ACC', (1, 0)), ('CMP', 100), ('EMIT', 7), ('RESET', 0))
        changed = replace(initial, nodes=tuple(replace(node, instructions=negative)
                  if node.node_id == 'B' else node for node in initial.nodes))
        n, _, p, s, port, *_ = one_run(chosen=changed)
        self.assertEqual(port.summary()['negative_judgments'], 2)
        self.assertEqual(s.summary()['concurrent_consumer_credit']['A'], -2)
        self.assertEqual(len(s.concurrent_journal()), 2)
        self.assertEqual(s.summary()['concurrent_consumer_memory_units'], 4)
        self.assertEqual(_payload(n['forward']), _payload(p['forward']))

    def test_signed_v2stu_predecessor_and_contract_only_fail_closed(self):
        raw = previous_bytes()
        if raw is None:
            self.skipTest('signed v2stu predecessor unavailable')
        prev = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v2stu(prev, raw))
        contract = build_report(prev, raw)
        self.assertEqual(contract['status'], CONTRACT)
        self.assertFalse(contract['universal_ACK_fairness_or_starvation_freedom_proven'])
        manipulated = json.loads(raw)
        manipulated['new_native_runs'] = 1
        with self.assertRaises(ValueError):
            build_report(manipulated, canon(manipulated))
        with self.assertRaises(ValueError):
            build_report(prev, raw+b' ')

    def test_full_90_native_540_policy_135_causal_matrix(self):
        raw = previous_bytes()
        if raw is None:
            self.skipTest('signed v2stu predecessor unavailable')
        result = experiment(json.loads(raw), raw, root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(json.loads(raw), raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertGreater(report['ready_queue_collision_cells'], 0)
        self.assertGreater(report['distinct_ACK_journal_policy_cells'], 0)
        self.assertEqual(report['new_derived_policy_runs'], 540)
        self.assertEqual(report['new_derived_causal_intervention_runs'], 135)
        self.assertFalse(report['universal_ACK_fairness_or_starvation_freedom_proven'])


if __name__ == '__main__':
    unittest.main()
