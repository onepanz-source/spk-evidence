"""Adversarial tests for conditional source grant-rank; never native learning."""
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
from search.spk_bv_v3tuv_grant_rank_cumulative import CODE_SHA, main
from spk_backvalidation_v0.a3d_shared_grants_v0d import SharedGrantRejected
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e, LiveBVPlanV0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v2.derived_actor_service_gap_v3q import audit_actor_service_gap
from spk_backvalidation_v2.derived_grant_rank_certificate_v3t import audit_grant_rank
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.grant_rank_integration_v3tuv import (
    PREDECESSOR_SHA, NEW_SCHEDULES, STATUS, build_report, experiment,
    validate_v3qrs,
)
from spk_bv_research.off_on_v0t import InterventionError


class TestV3tuvFiniteSourceRank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        options = ([Path(os.environ['SPK_V3QRS_REPORT'])] if
                   os.environ.get('SPK_V3QRS_REPORT') else [])
        options.extend((Path('/tmp/spk-bv-v3qrs-actor-service-gap.json'),
                        cls.root.parent.parent/'spk-bv-v3qrs-actor-service-gap.json'))
        cls.predecessor = next((p for p in options if p.is_file()), None)
        if cls.predecessor is None:
            raise FileNotFoundError('signed v3qrs predecessor unavailable')
        cls.raw = cls.predecessor.read_bytes()
        cls.prev = json.loads(cls.raw)

    @staticmethod
    def sample():
        # Controlled adversarial microcase, not one of the source native runs.
        records = [
            {'identity': 'jA', 'recipient': 'A', 'issuer': 'B',
             'source_emission': 'sA', 'created_tick': 0, 'due_tick': 1,
             'response': 1},
            {'identity': 'jB', 'recipient': 'B', 'issuer': 'C',
             'source_emission': 'sB', 'created_tick': 0, 'due_tick': 1,
             'response': -1},
        ]
        acks = [{'actor': 'A', 'judgment_id': 'jA', 'receiver_issuer': 'B',
                 'source_emission': 'sA', 'created_tick': 0, 'due_tick': 1,
                 'response': 1, 'serviced_tick': 1, 'seq': 1,
                 'resource_phase': 'native-slack'}]
        probes = [{'tick': 1, 'selected': 'ACK-first',
                   'ready_ACKs_before': 2, 'pre_forward_ACK_grants': 1,
                   'native_source_priority_veto': False,
                   'ready_forward_before': 0,
                   'ready_native_feedback_before': 0}]
        ledger = [{'tick': 1, 'phase': 'native-slack',
                   'native_service_used': 0, 'native_memory_used': 0,
                   'shadow_control_receipts': 1, 'shadow_service_units': 1,
                   'shadow_memory_units': 2, 'service_budget': 1,
                   'memory_budget': 64, 'pe_service_caps': {'PE0': 1},
                   'pe_memory_caps': {'PE0': 64},
                   'domain_memory_caps': {'O': 64, 'E': 64}}]
        summary = {'queue_priority_policy': 'ACK-first',
                   'native_operator_updates': 0, 'frozen_actor_state_changed': False,
                   'derived_control_tail_grants': 0,
                   'derived_actor_credit_ack_count': 1,
                   'concurrent_paid_applications': 0,
                   'delivered_other_unconsumed_pending': 1,
                   'delivered_policy_blocked_pending': 0}
        receiver = {'control_delivered': 2, 'absence_certificates': 0,
                    'post_native_deliveries': 0,
                    'delivered_by_sender': {'A': 1, 'B': 1}}
        return [acks, [], probes, ledger, summary, receiver, records]

    @staticmethod
    def audit(sample):
        return audit_grant_rank(*sample, policy='ACK-first',
                                global_quota=1, native_PE_budget=1)

    def test_signed_predecessor_and_semantics(self):
        self.assertEqual(sha256(self.raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3qrs(self.prev, self.raw))

    def test_signed_predecessor_alterations_fail_closed(self):
        for field, altered in (
                ('new_derived_actor_runs', 71),
                ('native_operator_updates', 1),
                ('native_individual_actor_deadline_proven', True),
                ('next_gate', 'FAIRNESS_PROVEN')):
            changed = deepcopy(self.prev)
            changed[field] = altered
            with self.subTest(field=field), self.assertRaises(InterventionError):
                validate_v3qrs(changed, canon(changed))
        with self.assertRaises(InterventionError):
            validate_v3qrs(self.prev, self.raw+b' ')

    def test_FIFO_prefix_and_exact_served_and_censored_grant_ranks(self):
        audit = self.audit(self.sample())
        self.assertEqual(audit['totals']['source_grant_units'], 1)
        self.assertEqual(audit['totals']['source_serviced_controls'], 1)
        self.assertEqual(audit['totals']['native_horizon_censored_controls'], 1)
        self.assertEqual(audit['totals']['sum_due_rank_censored'], 2)
        self.assertEqual(audit['totals']['global_grant_with_other_actor_waiting_ticks'], 1)
        self.assertEqual(audit['per_tick_fifo_prefix'][0]['oldest_ready_identity'], 'jA')
        self.assertFalse(audit['future_grant_arrival_or_tick_deadline_proven'])

    def test_semantically_causal_but_FIFO_bypassing_actor_ack_rejected(self):
        changed = self.sample()
        changed[0][0].update({'actor': 'B', 'judgment_id': 'jB',
                              'receiver_issuer': 'C', 'source_emission': 'sB',
                              'response': -1})
        # The inherited per-actor audit checks causal custody, not global FIFO.
        self.assertEqual(audit_actor_service_gap(*changed,
            policy='ACK-first', global_quota=1,
            native_PE_budget=1)['source_ack_count'], 1)
        with self.assertRaises(NativeForkError):
            self.audit(changed)

    def test_duplicate_ACK_resource_counter_and_due_tampering_rejected(self):
        cases = ('duplicate_ACK', 'grant_count', 'wrong_due', 'wrong_owner')
        for case in cases:
            changed = deepcopy(self.sample())
            if case == 'duplicate_ACK':
                changed[0].append(deepcopy(changed[0][0]))
            elif case == 'grant_count':
                changed[2][0]['pre_forward_ACK_grants'] = 0
            elif case == 'wrong_due':
                changed[6][0]['due_tick'] = 2
            else:
                changed[0][0]['actor'] = 'B'
            with self.subTest(case=case), self.assertRaises(NativeForkError):
                self.audit(changed)

    def test_no_grant_does_not_certify_negative_or_absence(self):
        changed = self.sample()
        changed[0].clear()
        changed[2][0].update({'selected': 'native-ready',
                               'pre_forward_ACK_grants': 0,
                               'native_source_priority_veto': True,
                               'ready_forward_before': 1})
        changed[3][0].update({'shadow_control_receipts': 0,
                              'shadow_service_units': 0,
                              'shadow_memory_units': 0})
        changed[4].update({'derived_actor_credit_ack_count': 0,
                           'delivered_other_unconsumed_pending': 2})
        audited = self.audit(changed)
        self.assertEqual(audited['totals']['native_horizon_censored_controls'], 2)
        self.assertEqual(audited['totals']['source_grant_units'], 0)

    def test_post_native_delivery_excluded_from_native_ready(self):
        changed = self.sample()
        changed[6].append({'identity': 'jLate', 'recipient': 'C',
                           'issuer': 'A', 'source_emission': 'sLate',
                           'created_tick': 1, 'due_tick': 2, 'response': -1})
        changed[5]['control_delivered'] = 3
        changed[5]['post_native_deliveries'] = 1
        changed[5]['delivered_by_sender']['C'] = 1
        changed[4]['delivered_other_unconsumed_pending'] = 2
        audited = self.audit(changed)
        self.assertEqual(audited['totals']['post_native_deliveries_not_native_ready'], 1)
        self.assertEqual(audited['totals']['native_horizon_censored_controls'], 1)

    def test_three_nonreplayed_admitted_schedules_and_ninth_rejected(self):
        prior = {tuple(item['source_external_ticks']) for item in self.prev['source_matrix']}
        self.assertEqual(len(NEW_SCHEDULES), 3)
        for label, ticks in NEW_SCHEDULES:
            with self.subTest(label=label):
                self.assertNotIn(ticks, prior)
                self.assertEqual(tuple(e.timestamp for e in fixture(ticks=ticks)[0].events), ticks)
        with self.assertRaises(SharedGrantRejected):
            fixture(ticks=tuple(range(1, 10)))

    def test_source_immutability_pins(self):
        self.assertGreater(len(CODE_SHA), 38)
        for name, digest in CODE_SHA.items():
            with self.subTest(path=name):
                self.assertEqual(sha256((self.root/name).read_bytes()).hexdigest(), digest)

    def test_contract_only_has_no_universal_liveness_claim(self):
        report = build_report(self.prev, self.raw)
        self.assertNotEqual(report['status'], STATUS)
        self.assertEqual(report['new_derived_rank_runs'], 0)
        self.assertFalse(report['universal_native_tick_deadline_proven'])
        self.assertFalse(report['native_actor_learning_observed'])

    def test_create_only_collision_and_source_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'contract.json'
            args = ['--root', str(self.root), '--v3qrs', str(self.predecessor),
                    '--out', str(output), '--contract-only']
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            with patch.dict(CODE_SHA, {
                    'spk_backvalidation_v2/derived_grant_rank_certificate_v3t.py':
                    '0'*64}):
                args[args.index(str(output))] = str(Path(d)/'drift.json')
                self.assertEqual(main(args), 2)

    def test_real_source_full_rank_matrix_and_all_causal_nulls(self):
        result = experiment(self.prev, self.raw, root=self.root,
            fixture_fn=fixture, native_executor=execute_live_v0e,
            plan_type=LiveBVPlanV0e)
        t = result['grant_rank_totals']
        self.assertEqual((t['new_original_native_runs'],
                          t['new_derived_FIFO_rank_runs'],
                          t['new_causal_null_runs']), (18, 72, 36))
        self.assertEqual((t['source_native_grant_ticks'],
                          t['source_native_grant_units']), (286, 329))
        self.assertEqual(t['source_native_eligible_controls'], 1096)
        self.assertEqual(t['served_exact_rank_certificates'], 329)
        self.assertEqual(t['censored_rank_below_threshold_certificates'], 767)
        self.assertEqual(t['post_native_deliveries_excluded'], 56)
        self.assertEqual(t['global_grant_with_waiting_other_actor_ticks'], 162)
        self.assertEqual(t['context_with_peer_waiting_and_global_grant'], 49)
        self.assertEqual(t['maximum_due_rank'], 16)
        self.assertEqual(t['sum_due_rank_serviced'], 904)
        self.assertEqual(t['sum_due_rank_censored'], 6054)
        self.assertEqual(t['full_original_native_projection_cells'], 72)
        self.assertEqual(result['causal_nulls']['source_runs'], 36)
        self.assertEqual(build_report(self.prev, self.raw, result)['status'], STATUS)


if __name__ == '__main__':
    unittest.main()
