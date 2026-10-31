"""v3h-v3j real source-derived ACK tail opportunity and adversarial tests."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import unittest

from search.spk_bv_v0e_live_evidence import fixture
from search.spk_bv_v3hij_ack_tail_opportunity_cumulative import CODE_SHA
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import (
    NativeForkError, PINNED_SCHED, read_pinned_source,
)
from spk_backvalidation_v2.derived_ack_tail_envelope_v3h import (
    audit_tail_envelope,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.ack_tail_opportunity_integration_v3hij import (
    EXPLICIT_LIMITS, QUOTAS, NULLS, PREDECESSOR_SHA,
    CONTRACT, STATUS, _run_budget, _prefix_from_full,
    validate_v3efg, experiment, build_report,
)
from spk_bv_research.native_veto_attribution_v3efg import ALL_SCHEDULES
from tests.test_spk_bv_v3bcd_episode_wait_prefix import one_run

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
REPORTS = (Path('/tmp/spk-bv-v3efg-native-veto-attribution.json'),
           ROOT.parent.parent / 'spk-bv-v3efg-native-veto-attribution.json')


def predecessor():
    env = os.environ.get('SPK_V3EFG_REPORT')
    for path in ([Path(env)] if env else []) + list(REPORTS):
        if path.is_file():
            return path.read_bytes()
    return None


def one_budget(*, ticks=(1, 3, 5, 7, 9, 11, 13, 15), quota=2,
               cap=32, enabled=True, priority='forward-first',
               intervention='normal', changed=None):
    case, fabric, plans = fixture(ticks=ticks)
    if changed is not None:
        case = changed(case)
    altered = (plans[0], replace(plans[1], fabric_slots_per_tick=2),
               plans[2], plans[3])
    data = (case, fabric, altered)
    native = execute_live_v0e(case, fabric, *altered,
                              LiveBVPlanV0e(enabled=enabled, priority=priority))
    actual = _run_budget(read_pinned_source(ROOT), execute_live_v0e,
        LiveBVPlanV0e, case, fabric, altered, enabled, priority,
        snapshot(data), data, tail_limit=cap, quota=quota,
        intervention=intervention)
    return native, *actual


class TestV3hijAckTailOpportunity(unittest.TestCase):
    def test_source_pin_and_all_new_inherited_code_pins(self):
        self.assertEqual(sha256(SOURCE.read_bytes()).hexdigest(), PINNED_SCHED)
        for name, expected in CODE_SHA.items():
            with self.subTest(name=name):
                self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(), expected)

    def test_true_one_vs_two_global_ACK_slots_per_tick(self):
        results = {q: one_budget(quota=q) for q in QUOTAS}
        for quota, result in results.items():
            native, acks, paid, witness, projected, _, _ = result
            self.assertEqual(native, projected)
            self.assertEqual(len(acks), len(paid))
            self.assertTrue(witness['complete_delivered_control_service'])
            self.assertEqual(witness['tail_global_grants_per_tick_cap'], quota)
        self.assertEqual(results[1][3]['tail_last_actual_grant_offset_ticks'], 15)
        self.assertEqual(results[2][3]['tail_last_actual_grant_offset_ticks'], 7)

    def test_zero_tail_is_a_real_causal_defer_not_negative_judgment(self):
        for quota, expected_inline in ((1, 1), (2, 2)):
            with self.subTest(quota=quota):
                native, acks, paid, w, projected, summary, receiver = one_budget(
                    quota=quota, cap=0)
                self.assertEqual(native, projected)
                self.assertEqual(len(acks), expected_inline)
                self.assertEqual(w['tail_ACKs'], 0)
                self.assertEqual(w['delivered_source_controls'], 16)
                self.assertEqual(w['delivered_pending_not_negative'],
                                 16-expected_inline)
                self.assertEqual(receiver['absence_certificates'], 0)

    def test_minimal_observed_H_and_H_minus_one_are_discriminating(self):
        for quota, H in ((1, 15), (2, 7)):
            with self.subTest(quota=quota):
                low = one_budget(quota=quota, cap=H-1)
                high = one_budget(quota=quota, cap=H)
                self.assertGreater(low[3]['delivered_pending_not_negative'], 0)
                self.assertTrue(high[3]['complete_delivered_control_service'])
                self.assertEqual(low[0], low[4])
                self.assertEqual(high[0], high[4])

    def test_exact_ACK_journal_is_a_prefix_across_tail_budgets(self):
        for quota in QUOTAS:
            with self.subTest(quota=quota):
                full = one_budget(quota=quota, cap=32)
                last = full[3]['source_native_last_tick']
                for cap in (0, 1, 2, 4, 8, 16):
                    limited = one_budget(quota=quota, cap=cap)
                    self.assertEqual(limited[1], _prefix_from_full(full[1], last, cap))
                    self.assertEqual(limited[4], full[4])

    def test_source_four_gap_and_late_episodes_native_projection(self):
        for label, ticks in ALL_SCHEDULES[-3:]:
            with self.subTest(schedule=label):
                native, acks, paid, witness, projected, *_ = one_budget(
                    ticks=ticks, quota=2, cap=32)
                self.assertEqual(projected, native)
                self.assertEqual(witness['source_ACK_count'], 16)
                self.assertEqual(witness['delivered_pending_not_negative'], 0)

    def test_native_BV_three_source_modes_and_tight_capacity(self):
        modes = ((False, 'forward-first'), (True, 'forward-first'),
                 (True, 'feedback-first'))
        for enabled, priority in modes:
            with self.subTest(mode=(enabled, priority)):
                native, acks, paid, witness, projection, *_ = one_budget(
                    ticks=(1, 3, 5, 7), quota=1, cap=32,
                    enabled=enabled, priority=priority)
                self.assertEqual(projection, native)
                self.assertEqual(len(acks), 8)
                self.assertTrue(witness['complete_delivered_control_service'])

    def test_transport_loss_and_zero_credit_are_distinct_causal_nulls(self):
        for kind in NULLS:
            with self.subTest(kind=kind):
                native, acks, paid, witness, projection, summary, receiver = (
                    one_budget(intervention=kind))
                self.assertEqual(projection, native)
                self.assertEqual(acks, [])
                self.assertEqual(paid, [])
                self.assertEqual(receiver['absence_certificates'], 0)
                if kind == 'transport_loss':
                    self.assertEqual(witness['delivered_source_controls'], 0)
                else:
                    self.assertGreater(witness['delivered_policy_blocked_pending'], 0)

    def test_actual_negative_receiver_credit_is_not_frozen_learning(self):
        negative_B = (('ACC', (1, 0)), ('CMP', 100),
                      ('EMIT', 7), ('RESET', 0))

        def modified(case):
            return replace(case, nodes=tuple(replace(n, instructions=negative_B)
                if n.node_id == 'B' else n for n in case.nodes))

        native, ACKs, paid, witness, projection, summary, receiver = one_budget(
            changed=modified)
        self.assertEqual(projection, native)
        self.assertEqual(receiver['negative_judgments'], 8)
        self.assertEqual(sum(a['response'] == -1 for a in ACKs), 8)
        self.assertFalse(summary['frozen_actor_state_changed'])
        self.assertEqual(summary['native_operator_updates'], 0)

    def test_forged_resource_phase_seq_and_due_tick_fail_closed(self):
        _, ACKs, paid, witness, _, summary, receiver = one_budget(cap=32)
        # Genuine queue probes must come from a source-derived run; the
        # independent auditor checks the copied, already compiled journals.
        native, _, _, actor, *_ = one_run(forward=True, bv=True)
        probes = actor.queue_fairness_probes()
        original = [dict(a) for a in ACKs]
        mutations = (
            lambda a: a[2].update(resource_phase='native-slack'),
            lambda a: a[2].update(seq=81),
            lambda a: a[2].update(due_tick=999),
            lambda a: a[2].update(actor='spoof'),
        )
        for change in mutations:
            with self.subTest(change=change):
                bad = [dict(a) for a in original]
                change(bad)
                with self.assertRaises(NativeForkError):
                    audit_tail_envelope(bad, paid, probes, summary, receiver,
                        tail_limit=32, per_tick_quota=2)

    def test_forged_oversubscribed_global_or_per_actor_tail_refused(self):
        _, ACKs, paid, _, _, summary, receiver = one_budget(cap=32)
        probes = one_run(forward=True, bv=True)[3].queue_fairness_probes()
        first_tail = next(a for a in ACKs
                          if a['resource_phase'] == 'post-native-tail')
        for kind in ('global', 'actor'):
            with self.subTest(kind=kind):
                bad = [dict(a) for a in ACKs]
                tail_indices = [i for i, a in enumerate(bad)
                                if a['resource_phase'] == 'post-native-tail']
                if kind == 'global':
                    # Put a third tail grant into a two-grant tick.
                    bad[tail_indices[2]]['serviced_tick'] = first_tail['serviced_tick']
                else:
                    # Put the same owner's next grant into its earlier tick.
                    idx = next(i for i in tail_indices
                               if bad[i]['actor'] == first_tail['actor'] and
                               bad[i]['serviced_tick'] > first_tail['serviced_tick'])
                    bad[idx]['serviced_tick'] = first_tail['serviced_tick']
                with self.assertRaises(NativeForkError):
                    audit_tail_envelope(bad, paid, probes, summary, receiver,
                        tail_limit=32, per_tick_quota=2)

    def test_invalid_budget_typed_and_custody_drift_refused(self):
        _, ACKs, paid, _, _, summary, receiver = one_budget(cap=32)
        probes = one_run(forward=True, bv=True)[3].queue_fairness_probes()
        for cap, quota in ((True, 2), (33, 2), (2, 3), (2, False)):
            with self.subTest(cap=cap, quota=quota):
                with self.assertRaises(NativeForkError):
                    audit_tail_envelope(ACKs, paid, probes, summary, receiver,
                        tail_limit=cap, per_tick_quota=quota)
        forged = dict(summary)
        forged['delivered_other_unconsumed_pending'] += 1
        with self.assertRaises(NativeForkError):
            audit_tail_envelope(ACKs, paid, probes, forged, receiver,
                tail_limit=32, per_tick_quota=2)

    def test_signed_v3efg_predecessor_mutations_refuse_contract(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('v3efg signed predecessor not mounted')
        previous = json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3efg(previous, raw))
        self.assertEqual(build_report(previous, raw)['status'], CONTRACT)
        for key in ('new_derived_policy_runs',
                    'universal_ACK_deadline_or_native_learning_proven',
                    'native_operator_updates'):
            with self.subTest(key=key):
                altered = json.loads(raw)
                altered[key] = 1 if key != 'new_derived_policy_runs' else 0
                with self.assertRaises(ValueError):
                    validate_v3efg(altered, canon(altered))
        with self.assertRaises(ValueError):
            validate_v3efg(previous, raw+b' ')

    def test_cumulative_27_native_454_budget_54_null_54_exact_cutover(self):
        raw = predecessor()
        if raw is None:
            self.skipTest('v3efg signed predecessor not mounted')
        previous = json.loads(raw)
        result = experiment(previous, raw, root=ROOT, fixture_fn=fixture,
            native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(previous, raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertEqual((report['new_native_runs'],
                          report['new_derived_budget_runs'],
                          report['new_causal_null_runs']), (27, 454, 54))
        self.assertEqual(report['total_source_tail_prefix_comparisons'], 454)
        self.assertEqual(report['total_source_capacity_monotonicity_comparisons'], 400)
        self.assertEqual(report['exact_finite_cutovers'], 54)
        self.assertEqual(report['per_global_ACK_tick_quota_totals']['1'][
            'max_tail_ticks_needed'], 16)
        self.assertEqual(report['per_global_ACK_tick_quota_totals']['2'][
            'max_tail_ticks_needed'], 8)
        self.assertTrue(all(v['lower_bound_tight_contexts'] == 27 for v in
            report['per_global_ACK_tick_quota_totals'].values()))
        self.assertFalse(report['universal_ACK_deadline_or_native_learning_proven'])


if __name__ == '__main__':
    unittest.main()
