"""v3b-v3d real 2–8 source input episodes, finite ACK wait and nonanticipation."""
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
    NativeForkError, PINNED_SCHED, CallsiteObserver,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import ShadowServicePlanV2j
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_concurrent_consumer_v2s import ConcurrentConsumerPlan
from spk_backvalidation_v2.derived_actor_queue_fairness_v2v import (
    DerivedActorQueueFairnessV2v, ActorQueuePlanV2v,
    derive_queue_fairness_executor,
)
from spk_backvalidation_v2.derived_ack_wait_audit_v3b import (
    EpisodeWaitPlan, validate_episode_plan, audit_episode_wait,
    audit_source_acks_and_paid_receipts,
)
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.episode_wait_prefix_integration_v3bcd import (
    SCHEDULES, PREFIX_SEQUENCE, PREDECESSOR_SHA,
    STATUS, CONTRACT, validate_v2yza, experiment, build_report,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v2yza-burst-window-cumulative.json'),
           ROOT.parent.parent / 'spk-bv-v2yza-burst-window-cumulative.json')


def predecessor():
    env = os.environ.get('SPK_V2YZA_REPORT')
    for p in ([Path(env)] if env else []) + list(REPORTS):
        if p.is_file():
            return p.read_bytes()
    return None


def one_run(*, ticks=(1, 3, 5, 7, 9, 11, 13, 15),
            policy='bounded-turns', enabled=True, priority='forward-first',
            forward=False, bv=False, credit=None, receiver=None, changed=None):
    case, fabric, plans = fixture(ticks=ticks)
    if changed is not None:
        case = changed(case)
    plans = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
             plans[2], plans[3])
    control = LiveBVPlanV0e(enabled=enabled, priority=priority)
    port = ReceiverPortV2h(latency=2, **(receiver or {}))
    actor = DerivedActorQueueFairnessV2v(port,
        queue_plan=ActorQueuePlanV2v(policy),
        admission_plan=CausalAdmissionPlanV2o(forward, bv),
        credit_plan=credit or ActorCreditPlanV2l(),
        concurrent_plan=ConcurrentConsumerPlan(),
        service_plan=ShadowServicePlanV2j(max_per_tick=2))
    observer = CallsiteObserver()
    executor, _, semantic, anchors = derive_queue_fairness_executor(
        SOURCE.read_bytes(), execute_live_v0e, port, actor, observer)
    native = execute_live_v0e(case, fabric, *plans, control)
    derived = executor(case, fabric, *plans, control)
    projected = actor.project_original_native_result(derived)
    return native, derived, projected, actor, port, observer, semantic, anchors


class TestV3bcdEpisodeWaitPrefix(unittest.TestCase):
    def test_pinned_frozen_native_source_and_executor_anchors(self):
        native, derived, projection, actor, port, observer, semantic, anchors = one_run()
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        self.assertEqual(semantic, (('batch', 194), ('clock', 125),
                                    ('emission', 217), ('ingress', 136)))
        self.assertEqual(anchors, (158, 296, 307))
        self.assertEqual(observer.counts()['_admit'], 1)
        self.assertEqual(len(actor.credit_journal()), 16)
        self.assertEqual(port.summary()['source_owned_emissions'],
                         port.summary()['native_ingress_events'])
        self.assertNotIn('__v2k_admission', execute_live_v0e.__globals__)

    def test_admitted_extended_source_schedules_only(self):
        self.assertEqual(len(SCHEDULES), 6)
        self.assertEqual([len(t) for _, t in SCHEDULES], [2, 3, 4, 6, 8, 8])
        for _, ticks in SCHEDULES:
            case, fabric, plans = fixture(ticks=ticks)
            self.assertEqual(tuple(e.timestamp for e in case.events), ticks)
        for ticks in ((1, 3, 3), (1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 3), (4, 1)):
            with self.subTest(ticks=ticks):
                with self.assertRaises(ValueError):
                    fixture(ticks=ticks)

    def test_actor_ACK_due_to_service_wait_is_source_owned(self):
        _, _, _, actor, port, *_ = one_run()
        observed = audit_episode_wait(actor)
        self.assertEqual(observed['source_ACKs'], 16)
        self.assertEqual(observed['independently_paid_consumer_receipts'], 16)
        self.assertEqual(observed['max_ACK_due_to_service_wait_ticks'], 1)
        self.assertGreater(observed['bounded_turn_source_windows'], 0)
        self.assertEqual(port.summary()['absence_certificates'], 0)
        self.assertFalse(observed['universal_ACK_service_deadline_proven'])

    def test_local_window_reduces_wait_but_native_veto_breaks_one_tick(self):
        _, _, _, no_limit, *_ = one_run(policy='consumer-first')
        _, _, _, bounded, *_ = one_run(policy='bounded-turns')
        _, _, native_guarded, protected, *_ = one_run(
            policy='bounded-turns', forward=True, bv=True)
        a, b, c = (audit_episode_wait(x) for x in (no_limit, bounded, protected))
        self.assertEqual(a['max_ACK_due_to_service_wait_ticks'], 3)
        self.assertEqual(b['max_ACK_due_to_service_wait_ticks'], 1)
        self.assertGreater(c['max_ACK_due_to_service_wait_ticks'], 1)
        # Native-ready veto may prevent consumer turns altogether: the
        # conditional local bound cannot manufacture a global ACK deadline.
        self.assertLessEqual(c['max_competing_consumer_streak'], 1)

    def test_strict_full_native_parity_for_every_derived_queue_policy(self):
        for p in ('ACK-first', 'consumer-first', 'bounded-turns'):
            with self.subTest(policy=p):
                native, _, projected, actor, *_ = one_run(
                    policy=p, forward=True, bv=True)
                self.assertEqual(projected, native)
                self.assertEqual(len(actor.concurrent_journal()),
                                 len(actor.credit_journal()))

    def test_extended_source_episode_functional_result_parity(self):
        for label, ticks in SCHEDULES:
            with self.subTest(label=label):
                native, _, projected, actor, *_ = one_run(ticks=ticks)
                self.assertEqual(_payload(native['forward']),
                                 _payload(projected['forward']))
                self.assertEqual(len(actor.credit_journal()), 2*len(ticks))

    def test_future_input_cannot_rewrite_ACK_consumer_or_terminal_prefix(self):
        sequence = dict(SCHEDULES)
        for short, long in zip(PREFIX_SEQUENCE, PREFIX_SEQUENCE[1:]):
            with self.subTest(short=short, long=long):
                cut = sequence[long][len(sequence[short])]
                a = one_run(ticks=sequence[short])
                b = one_run(ticks=sequence[long])
                for name, fn, field in (
                        ('ACK', lambda result: result[3].credit_journal(), 'serviced_tick'),
                        ('paid', lambda result: result[3].concurrent_journal(), 'consume_tick'),
                        ('terminal', lambda result: result[2]['forward']['terminal'],
                         'timestamp')):
                    with self.subTest(kind=name):
                        self.assertEqual(
                            [x for x in fn(a) if x[field] < cut],
                            [x for x in fn(b) if x[field] < cut])

    def test_causal_null_loss_or_credit_zero_never_mints_acks(self):
        for options in ({'receiver': {'accept': lambda _: False}},
                        {'credit': ActorCreditPlanV2l(max_abs_credit=0)}):
            with self.subTest(options=options):
                native, _, projected, actor, port, *_ = one_run(**options)
                self.assertEqual(projected, native)
                self.assertFalse(actor.credit_journal())
                self.assertFalse(actor.concurrent_journal())
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_actual_negative_B_judgment_remains_A_local_in_long_episode(self):
        negative = (('ACC', (1, 0)), ('CMP', 100), ('EMIT', 7), ('RESET', 0))

        def modified(case):
            return replace(case, nodes=tuple(
                replace(n, instructions=negative) if n.node_id == 'B' else n
                for n in case.nodes))

        native, _, projected, actor, port, *_ = one_run(changed=modified)
        self.assertEqual(port.summary()['negative_judgments'], 8)
        self.assertEqual(actor.summary()['concurrent_consumer_credit']['A'], -8)
        self.assertEqual(_payload(native['forward']), _payload(projected['forward']))
        self.assertFalse(actor.summary()['frozen_actor_state_changed'])

    def test_wrong_ACK_receiver_due_tick_fails_before_projection(self):
        _, derived, _, actor, *_ = one_run()
        actor._acks[0] = replace(actor._acks[0], due_tick=0)
        with self.assertRaises(NativeForkError):
            actor.project_original_native_result(derived)

    def test_source_paid_consumer_custody_and_clock_forgery_refused(self):
        for kind in ('ack', 'receipt', 'resource'):
            with self.subTest(kind=kind):
                _, derived, _, actor, *_ = one_run()
                if kind == 'ack':
                    actor._acks[0] = replace(actor._acks[0], chain_digest='a'*64)
                elif kind == 'receipt':
                    actor._v2s_receipts[0] = replace(
                        actor._v2s_receipts[0], chain_digest='a'*64)
                else:
                    derived['resources']['timeline'][0]['pe_service_total'] += 1
                with self.assertRaises(NativeForkError):
                    actor.project_original_native_result(derived)

    def test_streak_and_native_priority_probes_cannot_be_forged(self):
        for kind in ('source', 'selection', 'streak'):
            with self.subTest(kind=kind):
                _, derived, _, actor, *_ = one_run()
                row = next(r for r in actor._v2v_probes
                           if r['consumer_priority_streak_before'] > 0 and
                              r['ready_ACKs_before'] > 0)
                if kind == 'source':
                    row['ready_forward_before'] += 1
                elif kind == 'selection':
                    row['selected'] = 'consumer-first'
                else:
                    row['consumer_priority_streak_before'] += 1
                with self.assertRaises(NativeForkError):
                    actor.project_original_native_result(derived)

    def test_typed_wait_plan_and_bogus_journal_rejected(self):
        self.assertEqual(validate_episode_plan(EpisodeWaitPlan()),
                         EpisodeWaitPlan())
        for plan in (EpisodeWaitPlan(feedback_latency_ticks=1),
                     EpisodeWaitPlan(ACK_max_per_tick=3),
                     EpisodeWaitPlan(global_PE_slots_per_tick=True),
                     EpisodeWaitPlan(max_source_external_events=9)):
            with self.subTest(plan=plan):
                with self.assertRaises(NativeForkError):
                    validate_episode_plan(plan)
        _, _, _, actor, *_ = one_run()
        ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
        forged = actor.queue_fairness_probes()
        witness = {'policy': actor.queue_plan.policy, 'ACK_count': len(ACKs),
                   'paid_consumer_count': len(paid),
                   'universal_queue_liveness_proven': False,
                   'native_actor_policy_modified': False,
                   'forced_ACK_preference_windows': 0,
                   'ACK_pre_forward_grants_on_forced_windows': 0,
                   'max_competing_consumer_streak': 1}
        paid[0]['ack_digest'] = 'b'*64
        with self.assertRaises(NativeForkError):
            audit_source_acks_and_paid_receipts(ACKs, paid, witness, 'bounded-turns')

    def test_signed_predecessor_and_contract_only_fail_closed(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('signed v2yza report not mounted')
        prev = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v2yza(prev, raw))
        self.assertEqual(build_report(prev, raw)['status'], CONTRACT)
        self.assertFalse(build_report(prev, raw)['universal_ACK_or_consumer_liveness_proven'])
        mutated = json.loads(raw)
        mutated['bounded_window_activated_cells'] = 0
        with self.assertRaises(ValueError):
            build_report(mutated, canon(mutated))
        with self.assertRaises(ValueError):
            build_report(prev, raw+b' ')

    def test_full_18_native_108_derived_36_null_and_72_prefix_matrix(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('signed v2yza report not mounted')
        prev = json.loads(raw)
        report = build_report(prev, raw, experiment(prev, raw,
            root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e))
        self.assertEqual(report['status'], STATUS)
        self.assertEqual(report['new_original_native_runs'], 18)
        self.assertEqual(report['new_derived_queue_runs'], 108)
        self.assertEqual(report['new_derived_null_runs'], 36)
        self.assertEqual(report['prefix_causal_nonanticipation']['comparisons'], 72)
        self.assertEqual(report['null_guard_bounded_max_ACK_wait_ticks'], 1)
        self.assertEqual(report['null_guard_unbounded_max_ACK_wait_ticks'], 3)
        self.assertEqual(report['strict_native_veto_max_ACK_wait_ticks'], 29)
        self.assertFalse(report['universal_ACK_or_consumer_liveness_proven'])


if __name__ == '__main__':
    unittest.main()
