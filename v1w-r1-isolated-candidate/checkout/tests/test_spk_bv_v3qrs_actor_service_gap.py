"""Source-backed per-actor ACK progress; no universal fairness leap."""
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
from search.spk_bv_v3qrs_actor_service_gap_cumulative import CODE_SHA, main
from spk_backvalidation_v0.a3d_shared_grants_v0d import SharedGrantRejected
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v2.derived_actor_service_gap_v3q import audit_actor_service_gap
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_service_gap_integration_v3qrs import (
    PREDECESSOR_SHA, NEW_SCHEDULES, STATUS, build_report, experiment,
    validate_v3nop,
)
from spk_bv_research.off_on_v0t import InterventionError


class TestV3qrsActorSourceProgress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        candidates = ([Path(os.environ['SPK_V3NOP_REPORT'])] if
                      os.environ.get('SPK_V3NOP_REPORT') else [])
        candidates.extend((Path('/tmp/spk-bv-v3nop-native-ack-gap.json'),
                           cls.root.parent.parent/'spk-bv-v3nop-native-ack-gap.json'))
        cls.predecessor = next((p for p in candidates if p.is_file()), None)
        if cls.predecessor is None:
            raise FileNotFoundError('v3q-v3s signed v3nop predecessor unavailable')
        cls.raw = cls.predecessor.read_bytes()
        cls.prev = json.loads(cls.raw)

    @staticmethod
    def sample(*, grant=True):
        # This tiny synthetic verifier unit is NOT a source-native run.
        tick = 1
        records = [{
            'identity': 'jA', 'recipient': 'A', 'issuer': 'B',
            'source_emission': 'sA', 'created_tick': 0, 'due_tick': 1,
            'response': 1,
        }, {
            'identity': 'jB', 'recipient': 'B', 'issuer': 'C',
            'source_emission': 'sB', 'created_tick': 0, 'due_tick': 1,
            'response': -1,
        }]
        acks = ([{'actor': 'A', 'judgment_id': 'jA', 'receiver_issuer': 'B',
                  'source_emission': 'sA', 'created_tick': 0, 'due_tick': 1,
                  'response': 1, 'serviced_tick': 1, 'seq': 1,
                  'resource_phase': 'native-slack'}] if grant else [])
        veto = not grant
        probes = [{
            'tick': tick, 'selected': 'native-ready' if veto else 'ACK-first',
            'ready_ACKs_before': 2, 'pre_forward_ACK_grants': len(acks),
            'native_source_priority_veto': veto,
            'ready_forward_before': int(veto),
            'ready_native_feedback_before': 0,
        }]
        ledger = [{
            'tick': tick, 'phase': 'native-slack',
            'native_service_used': 0, 'native_memory_used': 0,
            'shadow_control_receipts': len(acks),
            'shadow_service_units': len(acks),
            'shadow_memory_units': 2*len(acks),
            'service_budget': 1, 'memory_budget': 64,
            'pe_service_caps': {'PE0': 1},
            'pe_memory_caps': {'PE0': 64},
            'domain_memory_caps': {'O': 64, 'E': 64},
        }]
        summary = {
            'queue_priority_policy': 'ACK-first',
            'native_operator_updates': 0,
            'frozen_actor_state_changed': False,
            'derived_control_tail_grants': 0,
            'derived_actor_credit_ack_count': len(acks),
            'concurrent_paid_applications': 0,
            'delivered_other_unconsumed_pending': 2-len(acks),
            'delivered_policy_blocked_pending': 0,
        }
        receiver = {
            'control_delivered': 2, 'absence_certificates': 0,
            'post_native_deliveries': 0,
            'delivered_by_sender': {'A': 1, 'B': 1},
        }
        return [acks, [], probes, ledger, summary, receiver, records]

    def audit(self, candidate):
        return audit_actor_service_gap(*candidate,
            policy='ACK-first', global_quota=1, native_PE_budget=1)

    def test_canonical_signed_v3nop_source_boundary(self):
        self.assertEqual(sha256(self.raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3nop(self.prev, self.raw))

    def test_predecessor_semantic_claim_and_signed_json_mutations_rejected(self):
        for field, value in (
                ('new_derived_gap_runs', 71),
                ('native_operator_updates', 1),
                ('no_future_source_opportunity_rate_or_per_actor_deadline_proven', False),
                ('next_gate', 'FAIR_SCHEDULER_PROVEN')):
            altered = deepcopy(self.prev)
            altered[field] = value
            with self.subTest(field=field), self.assertRaises(InterventionError):
                validate_v3nop(altered, canon(altered))
        with self.assertRaises(InterventionError):
            validate_v3nop(self.prev, self.raw+b' ')

    def test_real_peer_miss_even_while_global_ACK_advanced(self):
        result = self.audit(self.sample())
        self.assertEqual(result['source_ack_count'], 1)
        self.assertEqual(result['source_global_gap_max'], 0)
        self.assertEqual(result['global_grant_with_unserved_actor_ticks'], 1)
        self.assertEqual(result['actor_totals']['B']['peer_progress_actor_misses'], 1)
        self.assertEqual(result['first_global_progress_actor_miss_witness'], {
            'tick': 1, 'ready_actors': ['A', 'B'],
            'serviced_actors': ['A'], 'unserviced_actors': ['B']})
        self.assertFalse(result['native_universal_actor_liveness_proven'])

    def test_censored_actor_ready_is_not_a_negative_receiver_vote(self):
        result = self.audit(self.sample(grant=False))
        self.assertEqual(result['actor_ready_misses'], 2)
        self.assertEqual(result['global_grant_with_unserved_actor_ticks'], 0)
        self.assertEqual(result['actor_totals']['A'][
            'unserved_at_native_end_censored'], 1)
        self.assertEqual(result['actor_totals']['B'][
            'unserved_at_native_end_censored'], 1)
        self.assertFalse(result['native_learning_proven'])

    def test_wrong_actor_mismatched_causal_emission_or_early_ACK_rejected(self):
        for field, value in (('actor', 'B'), ('judgment_id', 'missing'),
                             ('source_emission', 'forged'),
                             ('due_tick', 2), ('serviced_tick', 0)):
            bad = deepcopy(self.sample())
            bad[0][0][field] = value
            with self.subTest(field=field), self.assertRaises(NativeForkError):
                self.audit(bad)

    def test_duplicate_actor_ACK_and_tick_grant_replay_rejected(self):
        bad = deepcopy(self.sample())
        bad[0].append(deepcopy(bad[0][0]))
        with self.assertRaises(NativeForkError):
            self.audit(bad)

    def test_delivery_scope_and_post_native_censor_tampering_rejected(self):
        for mutation in ('swap_recipient', 'duplicate_record', 'bad_post_native',
                         'bad_delivered_owner'):
            bad = deepcopy(self.sample())
            if mutation == 'swap_recipient':
                bad[6][0]['recipient'] = 'C'
            elif mutation == 'duplicate_record':
                bad[6][1]['identity'] = 'jA'
            elif mutation == 'bad_post_native':
                bad[5]['post_native_deliveries'] = 1
            else:
                bad[5]['delivered_by_sender']['B'] = 2
            with self.subTest(mutation=mutation), self.assertRaises(NativeForkError):
                self.audit(bad)

    def test_three_new_source_admitted_nonreplayed_eight_event_workloads(self):
        seen = {tuple(row['source_external_ticks']) for row in self.prev['source_matrix']}
        self.assertEqual(len(NEW_SCHEDULES), 3)
        for label, ticks in NEW_SCHEDULES:
            with self.subTest(label=label):
                self.assertNotIn(ticks, seen)
                self.assertEqual(len(ticks), 8)
                case, _, _ = fixture(ticks=ticks)
                self.assertEqual(tuple(e.timestamp for e in case.events), ticks)
        with self.assertRaises(SharedGrantRejected):
            fixture(ticks=tuple(range(1, 10)))

    def test_source_sha_pins_and_original_native_pinned(self):
        self.assertGreater(len(CODE_SHA), 35)
        for name, digest in CODE_SHA.items():
            with self.subTest(source=name):
                self.assertEqual(sha256((self.root/name).read_bytes()).hexdigest(), digest)

    def test_contract_only_does_not_claim_actor_fairness(self):
        report = build_report(self.prev, self.raw)
        self.assertNotEqual(report['status'], STATUS)
        self.assertEqual(report['new_derived_actor_runs'], 0)
        self.assertFalse(report['native_individual_actor_deadline_proven'])
        self.assertFalse(report['native_learning_observed'])

    def test_create_only_output_and_pinned_source_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'contract.json'
            args = ['--root', str(self.root), '--v3nop', str(self.predecessor),
                    '--out', str(path), '--contract-only']
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            with patch.dict(CODE_SHA, {
                    'spk_backvalidation_v2/derived_actor_service_gap_v3q.py': '0'*64}):
                args[args.index(str(path))] = str(Path(tmp)/'drift.json')
                self.assertEqual(main(args), 2)

    def test_full_source_actor_matrix_and_causal_nulls(self):
        result = experiment(self.prev, self.raw, root=self.root,
            fixture_fn=fixture, native_executor=execute_live_v0e,
            plan_type=LiveBVPlanV0e)
        t = result['actor_progress_totals']
        self.assertEqual((t['native_original_runs'], t['derived_actor_runs']), (18, 72))
        self.assertEqual(result['causal_nulls']['runs'], 36)
        self.assertEqual(t['full_native_projection_cells'], 72)
        self.assertEqual(t['source_peer_progress_actor_misses'], 71)
        self.assertEqual(t['global_grant_with_unserved_actor_ticks'], 71)
        self.assertEqual(t['contexts_with_global_progress_peer_miss'], 47)
        self.assertEqual(t['maximum_actor_ready_miss_streak'], 37)
        self.assertEqual(t['native_ready_actor_ticks'],
                         t['native_missed_actor_ticks']+t['native_inline_ACKs'])
        self.assertGreater(t['post_native_deliveries'], 0)
        self.assertGreater(t['native_horizon_censored_records'], 0)
        witness = result['global_progress_not_actor_progress_witnesses'][0]
        self.assertEqual(witness['witness']['ready_actors'], ['A', 'B'])
        self.assertEqual(witness['witness']['serviced_actors'], ['A'])
        self.assertEqual(witness['witness']['unserviced_actors'], ['B'])
        report = build_report(self.prev, self.raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertFalse(report['native_individual_actor_deadline_proven'])


if __name__ == '__main__':
    unittest.main()
