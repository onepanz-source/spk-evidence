"""v3e-v3g adversarial source-native priority attribution and no-tail gates."""
from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import unittest

from tests.test_spk_bv_v3bcd_episode_wait_prefix import one_run
from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    NativeForkError, PINNED_SCHED, read_pinned_source,
)
from spk_backvalidation_v2.derived_actor_burst_window_v2y import audit_burst_window
from spk_backvalidation_v2.derived_native_veto_wait_audit_v3e import (
    CLASSES, audit_native_wait_overlap,
)
from spk_backvalidation_v2.derived_ack_wait_audit_v3b import audit_episode_wait
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_veto_attribution_v3efg import (
    ALL_SCHEDULES, ADDITIONAL_SCHEDULES, GUARD_FACTORIAL,
    PREDECESSOR_SHA, CONTRACT, STATUS,
    _run_no_tail, validate_v3bcd, experiment, build_report,
)
from spk_bv_research.actor_priority_contention_integration_v2m import _payload
from spk_bv_research.off_on_v0t import snapshot

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v3bcd-episode-wait-prefix.json'),
           ROOT.parent.parent / 'spk-bv-v3bcd-episode-wait-prefix.json')


def predecessor():
    env = os.environ.get('SPK_V3BCD_REPORT')
    for candidate in ([Path(env)] if env else []) + list(REPORTS):
        if candidate.is_file():
            return candidate.read_bytes()
    return None


def audited_run(*, forward=True, bv=True, policy='bounded-turns',
                ticks=(1, 3, 5, 7, 9, 11, 13, 15)):
    native, derived, projected, actor, port, observer, *_ = one_run(
        ticks=ticks, forward=forward, bv=bv, policy=policy)
    ACKs, paid = actor.credit_journal(), actor.concurrent_journal()
    witness = audit_burst_window(actor)
    observed = audit_native_wait_overlap(ACKs, paid,
        actor.queue_fairness_probes(), witness, policy=policy,
        protect_forward=forward, protect_feedback=bv)
    return native, derived, projected, actor, observed


class TestV3efgNativeVetoAttribution(unittest.TestCase):
    def test_source_pin_and_runtime_only_derived_observer(self):
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        native, derived, projected, actor, report = audited_run()
        self.assertEqual(projected, native)
        self.assertEqual(actor.summary()['native_operator_updates'], 0)
        self.assertNotIn('__v2o_causal_admission', execute_live_v0e.__globals__)

    def test_three_distinct_admitted_new_eight_episode_schedules(self):
        self.assertEqual(len(ALL_SCHEDULES), 9)
        self.assertEqual(len(ADDITIONAL_SCHEDULES), 3)
        self.assertEqual(len({t for _, t in ALL_SCHEDULES}), 9)
        for label, ticks in ADDITIONAL_SCHEDULES:
            with self.subTest(label=label):
                case, *_ = fixture(ticks=ticks)
                self.assertEqual(tuple(e.timestamp for e in case.events), ticks)

    def test_four_guard_factorial_is_two_independent_boolean_controls(self):
        self.assertEqual(len(GUARD_FACTORIAL), 4)
        self.assertEqual({(f, b) for _, f, b in GUARD_FACTORIAL},
                         {(True, True), (True, False), (False, True),
                          (False, False)})

    def test_actual_feedback_guard_native_ack_wait_counterexample(self):
        results = {name: audited_run(forward=f, bv=b)[-1]
                   for name, f, b in GUARD_FACTORIAL}
        self.assertEqual(results['both_native_guards']['ACK_wait_max_ticks'], 29)
        self.assertEqual(results['forward_only_guard']['ACK_wait_max_ticks'], 14)
        self.assertEqual(results['feedback_only_guard']['ACK_wait_max_ticks'], 29)
        self.assertEqual(results['no_native_guard']['ACK_wait_max_ticks'], 1)

    def test_native_guards_preserve_full_projection_all_queue_policies(self):
        for policy in ('ACK-first', 'consumer-first', 'bounded-turns'):
            with self.subTest(policy=policy):
                native, _, projected, actor, audit = audited_run(policy=policy)
                self.assertEqual(projected, native)
                self.assertEqual(audit['source_ACKs'], len(actor.credit_journal()))
                self.assertGreater(audit['ACK_wait_max_ticks'], 1)

    def test_guard_relaxation_only_asserts_functional_payload(self):
        for name, f, b in GUARD_FACTORIAL:
            with self.subTest(guard=name):
                native, _, projected, *_ = audited_run(forward=f, bv=b)
                self.assertEqual(_payload(projected['forward']),
                                 _payload(native['forward']))
                if name == 'both_native_guards':
                    self.assertEqual(projected, native)
                if name == 'no_native_guard':
                    self.assertNotEqual(projected, native)

    def test_wait_tick_partition_is_exact_exhaustive_and_noncausal(self):
        *_, observed = audited_run()
        self.assertEqual(set(observed['ACK_wait_tick_overlap_partition']), set(CLASSES))
        self.assertEqual(sum(observed['ACK_wait_tick_overlap_partition'].values()),
                         observed['ACK_wait_total_ticks'])
        self.assertGreater(observed['ACK_wait_tick_overlap_partition'][
            'feedback_only_veto'], 0)
        self.assertFalse(observed['causal_effect_of_each_individual_wait_tick_identified'])
        self.assertFalse(observed['global_ACK_service_deadline_proven'])

    def test_native_probe_partition_contains_no_fabricated_service(self):
        *_, actor, observed = audited_run()
        self.assertEqual(sum(observed['native_probe_tick_partition'].values()),
                         len(actor.queue_fairness_probes()))
        for row in actor.queue_fairness_probes():
            if row['native_source_priority_veto']:
                self.assertEqual(row['pre_forward_ACK_grants'], 0)

    def test_new_source_four_gap_schedule_remains_functionally_equal(self):
        ticks = dict(ADDITIONAL_SCHEDULES)['eight_four_gap']
        for guard, f, b in GUARD_FACTORIAL:
            with self.subTest(guard=guard):
                native, _, projected, _, audit = audited_run(
                    ticks=ticks, forward=f, bv=b)
                self.assertEqual(_payload(projected['forward']),
                                 _payload(native['forward']))
                self.assertEqual(audit['source_ACKs'], 16)

    def test_real_source_no_tail_retains_unconsumed_without_negative_proof(self):
        case, fabric, plans = fixture(ticks=(1, 3, 5, 7, 9, 11, 13, 15))
        adjusted = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
                    plans[2], plans[3])
        data = (case, fabric, adjusted)
        native = execute_live_v0e(case, fabric, *adjusted,
                                  LiveBVPlanV0e(priority='forward-first'))
        summary, ACKs, paid, projected, receiver = _run_no_tail(
            read_pinned_source(ROOT), execute_live_v0e, LiveBVPlanV0e,
            case, fabric, adjusted, True, 'forward-first', snapshot(data), data)
        self.assertEqual(projected, native)
        self.assertEqual(summary['derived_control_tail_grants'], 0)
        self.assertGreater(summary['delivered_other_unconsumed_pending'], 0)
        self.assertEqual(receiver['absence_certificates'], 0)
        self.assertLessEqual(len(paid), len(ACKs))

    def test_transport_loss_and_zero_credit_are_not_negative_judgments(self):
        from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
        for options in ({'receiver': {'accept': lambda _: False}},
                        {'credit': ActorCreditPlanV2l(max_abs_credit=0)}):
            with self.subTest(options=options):
                native, _, projection, actor, port, *_ = one_run(**options)
                self.assertEqual(projection, native)
                self.assertEqual(actor.credit_journal(), [])
                self.assertEqual(actor.concurrent_journal(), [])
                self.assertEqual(port.summary()['absence_certificates'], 0)

    def test_forged_veto_probe_is_refused_by_derived_source_audit(self):
        native, derived, projected, actor, observation = audited_run()
        row = actor._v2v_probes[3]
        row['ready_native_feedback_before'] += 1
        with self.assertRaises(NativeForkError):
            actor.project_original_native_result(derived)

    def test_forged_veto_or_duplicate_clock_is_refused_by_overlap_auditor(self):
        native, derived, projected, actor, observed = audited_run()
        acks, paid, probes = (actor.credit_journal(), actor.concurrent_journal(),
                              actor.queue_fairness_probes())
        witness = audit_burst_window(actor)
        variants = (
            lambda p: p[2].update(native_source_priority_veto=False),
            lambda p: p[2].update(pre_forward_ACK_grants=1),
            lambda p: p[2].update(tick=p[1]['tick']),
        )
        for change in variants:
            with self.subTest(change=change):
                forged = [dict(x) for x in probes]
                change(forged)
                with self.assertRaises(NativeForkError):
                    audit_native_wait_overlap(acks, paid, forged, witness,
                        policy='bounded-turns', protect_forward=True,
                        protect_feedback=True)

    def test_wrong_guard_flags_and_missing_due_ack_are_refused(self):
        native, derived, projected, actor, observed = audited_run()
        ACKs, paid, probes = (actor.credit_journal(), actor.concurrent_journal(),
                              actor.queue_fairness_probes())
        witness = audit_burst_window(actor)
        for forward, feedback in ((1, True), (True, 0), (False, True)):
            with self.subTest(forward=forward, feedback=feedback):
                with self.assertRaises(NativeForkError):
                    audit_native_wait_overlap(ACKs, paid, probes, witness,
                        policy='bounded-turns', protect_forward=forward,
                        protect_feedback=feedback)
        ACKs[0]['due_tick'] = 0
        with self.assertRaises(NativeForkError):
            audit_native_wait_overlap(ACKs, paid, probes, witness,
                policy='bounded-turns', protect_forward=True,
                protect_feedback=True)

    def test_signed_v3bcd_predecessor_mutation_fails_closed(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('signed v3bcd report not mounted')
        prev = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3bcd(prev, raw))
        self.assertEqual(build_report(prev, raw)['status'], CONTRACT)
        for key in ('strict_native_veto_max_ACK_wait_ticks',
                    'native_veto_global_deadline_counterexample_observed',
                    'new_derived_queue_runs', 'native_operator_updates'):
            with self.subTest(key=key):
                modified = json.loads(raw)
                modified[key] = 0 if key != 'native_operator_updates' else 1
                with self.assertRaises(ValueError):
                    validate_v3bcd(modified, canon(modified))
        with self.assertRaises(ValueError):
            validate_v3bcd(prev, raw+b' ')

    def test_full_27_native_324_factorial_54_null_27_tail(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('signed v3bcd report not mounted')
        prev = json.loads(raw)
        result = experiment(prev, raw, root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(prev, raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertEqual((report['new_native_runs'], report['new_derived_policy_runs'],
                          report['new_null_runs'], report['new_tail_off_runs']),
                         (27, 324, 54, 27))
        self.assertEqual(report['factorial_contrasts']['cells'], 81)
        self.assertGreater(report['factorial_contrasts'][
            'full_native_parity_lost_under_some_relaxation'], 0)
        self.assertEqual(report['tail_disabled_observations']['native_exact'], 27)
        self.assertFalse(report['universal_ACK_deadline_or_native_learning_proven'])


if __name__ == '__main__':
    unittest.main()
