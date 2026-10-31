"""Adversarial and source-replayed finite ready ACK gap discrimination."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from search.spk_bv_v3nop_native_ack_gap_cumulative import CODE_SHA, main
from spk_backvalidation_v0.a3d_shared_grants_v0d import SharedGrantRejected
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v2.derived_ack_wait_gap_v3n import audit_ready_gap
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_gap_integration_v3nop import (
    PREDECESSOR_SHA, NEW_SCHEDULES, STATUS, build_report, experiment,
    validate_v3klm,
)
from spk_bv_research.off_on_v0t import InterventionError


class TestV3nopSourceNativeAckGap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        candidates = ([Path(os.environ['SPK_V3KLM_REPORT'])] if
                      os.environ.get('SPK_V3KLM_REPORT') else [])
        candidates.extend((
            Path('/tmp/spk-bv-v3klm-native-ack-opportunity.json'),
            cls.root.parent.parent/'spk-bv-v3klm-native-ack-opportunity.json',
        ))
        cls.predecessor = next((p for p in candidates if p.is_file()), None)
        if cls.predecessor is None:
            raise FileNotFoundError('v3n-v3p signed v3klm precursor unavailable')
        cls.raw = cls.predecessor.read_bytes()
        cls.prev = json.loads(cls.raw)

    @staticmethod
    def sample(*, blocked=3, selected='native-ready', grant=True):
        """Unit-level synthetic verifier input, NOT a frozen native trace."""
        probes, ledger = [], []
        horizon = blocked+int(grant)
        for tick in range(1, horizon+1):
            done = bool(grant and tick == horizon)
            veto = selected == 'native-ready' and not done
            probes.append({'tick': tick,
                'selected': 'ACK-first' if done else selected,
                'ready_ACKs_before': 1,
                'pre_forward_ACK_grants': int(done),
                'native_source_priority_veto': veto,
                'ready_forward_before': int(veto),
                'ready_native_feedback_before': 0})
            ledger.append({'tick': tick, 'phase': 'native-slack',
                'native_service_used': 0, 'native_memory_used': 0,
                'shadow_control_receipts': int(done),
                'shadow_service_units': int(done),
                'shadow_memory_units': 2*int(done),
                'service_budget': 1, 'memory_budget': 64,
                'pe_service_caps': {'PE0': 2},
                'pe_memory_caps': {'PE0': 64},
                'domain_memory_caps': {'E': 64, 'O': 64}})
        acks = ([{'actor': 'A', 'seq': 1, 'serviced_tick': horizon,
                  'due_tick': 1, 'resource_phase': 'native-slack'}]
                if grant else [])
        summary = {'queue_priority_policy': (
                'bounded-turns' if selected == 'consumer-first' else 'ACK-first'),
            'native_operator_updates': 0,
            'frozen_actor_state_changed': False,
            'derived_control_tail_grants': 0,
            'derived_actor_credit_ack_count': len(acks),
            'concurrent_paid_applications': 0,
            'delivered_other_unconsumed_pending': 1-len(acks),
            'delivered_policy_blocked_pending': 0}
        receiver = {'control_delivered': 1, 'absence_certificates': 0}
        return (acks, [], probes, ledger, summary, receiver,
                {'policy': summary['queue_priority_policy'],
                 'global_quota': 1, 'native_PE_budget': 1})

    def audit(self, inputs):
        return audit_ready_gap(*inputs[:6], **inputs[6])

    def test_pinned_signed_canonical_predecessor(self):
        self.assertEqual(sha256(self.raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3klm(self.prev, self.raw))

    def test_predecessor_contract_and_count_mutations_fail_closed(self):
        for field, value in (
                ('new_original_native_runs', 53),
                ('sufficient_source_opportunities', 355),
                ('universal_ACK_liveness_or_native_learning_proven', True),
                ('next_gate', 'LIVENESS_PROVEN')):
            mutated = deepcopy(self.prev)
            mutated[field] = value
            with self.subTest(field=field), self.assertRaises(InterventionError):
                validate_v3klm(mutated, canon(mutated))
        with self.assertRaises(InterventionError):
            validate_v3klm(self.prev, self.raw+b' ')

    def test_exact_veto_partition_and_grant_after_wait(self):
        result = self.audit(self.sample(blocked=3))
        c = result['totals']
        self.assertEqual(c['native_ticks'], 4)
        self.assertEqual(c['ready_miss_ticks'], 3)
        self.assertEqual(c['native_veto_miss_ticks'], 3)
        self.assertEqual(c['grant_units'], 1)
        self.assertEqual(c['max_grant_ended_miss_ticks'], 3)
        self.assertEqual(result['miss_episodes'][0]['end_reason'], 'grant')
        self.assertFalse(result['per_actor_deadline_inferred'])

    def test_censored_end_not_a_negative_or_silence_proof(self):
        result = self.audit(self.sample(blocked=4, grant=False))
        self.assertEqual(result['totals']['censored_at_native_end'], 1)
        self.assertEqual(result['miss_episodes'][0]['end_reason'],
                         'native_horizon_censored')
        self.assertEqual(result['totals']['source_pending_not_negative'], 1)
        self.assertFalse(result['negative_judgment_or_silence_inferred'])

    def test_consumer_queue_miss_cannot_be_relabelled_veto(self):
        result = self.audit(self.sample(blocked=1,
                                        selected='consumer-first', grant=False))
        self.assertEqual(result['totals']['consumer_first_miss_ticks'], 1)
        candidate = list(self.sample(blocked=1,
                                     selected='consumer-first', grant=False))
        candidate[2][0]['native_source_priority_veto'] = True
        with self.assertRaises(NativeForkError):
            self.audit(candidate)

    def test_fake_grant_on_native_veto_and_future_due_refused(self):
        for mutation in ('veto_grant', 'future_due', 'wrong_actor_epoch'):
            candidate = list(self.sample(blocked=2))
            if mutation == 'veto_grant':
                candidate[2][-1]['native_source_priority_veto'] = True
            if mutation == 'future_due':
                candidate[0][0]['due_tick'] = 4
            if mutation == 'wrong_actor_epoch':
                candidate[0][0]['seq'] = 2
            with self.subTest(mutation=mutation), self.assertRaises(NativeForkError):
                self.audit(candidate)

    def test_mismatched_resource_and_tick_attribution_fail_closed(self):
        for key, value in (('tick', 77), ('shadow_control_receipts', 2),
                           ('memory_budget', 'free')):
            candidate = list(self.sample())
            candidate[3][-1][key] = value
            with self.subTest(field=key), self.assertRaises((NativeForkError, TypeError)):
                self.audit(candidate)

    def test_all_new_eight_event_schedules_are_source_admitted(self):
        self.assertEqual(len(NEW_SCHEDULES), 3)
        self.assertEqual(len({ticks for _, ticks in NEW_SCHEDULES}), 3)
        previous_ticks = {tuple(x['source_external_ticks'])
                          for x in self.prev['source_matrix']}
        for label, ticks in NEW_SCHEDULES:
            with self.subTest(schedule=label):
                c, _, _ = fixture(ticks=ticks)
                self.assertEqual(tuple(e.timestamp for e in c.events), ticks)
                self.assertEqual(len(ticks), 8)
                self.assertNotIn(ticks, previous_ticks)
        with self.assertRaises(SharedGrantRejected):
            fixture(ticks=tuple(range(1, 10)))
        with self.assertRaises(SharedGrantRejected):
            fixture(ticks=(1, 4, 8, 12, 16, 20, 24, 33))

    def test_all_inherited_and_new_code_SHA_pins(self):
        self.assertGreater(len(CODE_SHA), 30)
        for relative, digest in CODE_SHA.items():
            with self.subTest(source=relative):
                self.assertEqual(sha256((self.root/relative).read_bytes()).hexdigest(),
                                 digest)

    def test_contract_only_cannot_claim_actual_native_deadline(self):
        report = build_report(self.prev, self.raw)
        self.assertNotEqual(report['status'], STATUS)
        self.assertEqual(report['new_original_native_runs'], 0)
        self.assertFalse(report['source_only_finite_deadline_threshold_refutation'])
        self.assertTrue(report[
            'no_future_source_opportunity_rate_or_per_actor_deadline_proven'])
        self.assertFalse(report['native_actor_learning_observed'])

    def test_create_only_runner_and_tampered_code_pin_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'contract.json'
            args = ['--root', str(self.root), '--v3klm', str(self.predecessor),
                    '--out', str(output), '--contract-only']
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            with patch.dict(CODE_SHA, {
                    'spk_backvalidation_v2/derived_ack_wait_gap_v3n.py': '0'*64}):
                args[args.index(str(output))] = str(Path(temp)/'drift.json')
                self.assertEqual(main(args), 2)

    def test_source_three_new_workloads_twelve_policy_PEs_and_real_thresholds(self):
        result = experiment(self.prev, self.raw, root=self.root,
            fixture_fn=fixture, native_executor=execute_live_v0e,
            plan_type=LiveBVPlanV0e)
        self.assertEqual(result['new_original_native_runs'], 18)
        self.assertEqual(result['new_derived_gap_runs'], 72)
        self.assertEqual(result['new_causal_null_runs'], 36)
        self.assertEqual(result['policy_quota_comparisons'][
            'strict_native_parity_cells'], 72)
        self.assertEqual(result['missed_ready_tick_threshold_contexts'],
            {'1': 72, '2': 72, '4': 72, '8': 66, '16': 53, '32': 24})
        self.assertEqual(len(result['nonmonotone_new_quota_witnesses']), 3)
        biggest = max(result['long_ready_gap_source_witnesses'],
                      key=lambda x: x['ready_gap']['length'])
        self.assertEqual(biggest['ready_gap']['length'], 37)
        self.assertEqual(biggest['ready_gap']['miss_classes']['native_veto'], 37)
        self.assertEqual(biggest['ready_gap']['end_reason'], 'grant')
        self.assertGreater(biggest['source_delivered'], 0)
        self.assertTrue(result['strict_full_native_projection'])
        report = build_report(self.prev, self.raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertFalse(report['native_actor_learning_observed'])
        self.assertTrue(report[
            'no_future_source_opportunity_rate_or_per_actor_deadline_proven'])


if __name__ == '__main__':
    unittest.main()
