"""Finite source/queue opportunity conditions and adversarial boundary tests."""
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
from search.spk_bv_v3klm_native_ack_opportunity_cumulative import (
    CODE_SHA, main,
)
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v2.derived_native_opportunity_certificate_v3k import (
    audit_native_opportunities,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_opportunity_integration_v3klm import (
    PREDECESSOR_SHA, STATUS, build_report, experiment, validate_v3hij,
)
from spk_bv_research.off_on_v0t import InterventionError


class TestV3klmNativeAckOpportunity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        candidate = [Path(os.environ['SPK_V3HIJ_REPORT'])] if (
            os.environ.get('SPK_V3HIJ_REPORT')) else []
        candidate.extend((
            Path('/tmp/spk-bv-v3hij-ack-tail-opportunity.json'),
            cls.root.parent.parent/'spk-bv-v3hij-ack-tail-opportunity.json',
        ))
        cls.source = next((p for p in candidate if p.is_file()), None)
        if cls.source is None:
            raise FileNotFoundError('v3k-v3m signed v3hij predecessor unavailable')
        cls.raw = cls.source.read_bytes()
        cls.prev = json.loads(cls.raw)

    @staticmethod
    def witness(*, selected='ACK-first', ready=1, grant=0, veto=False,
                capacity=1):
        ACKs = ([{'actor': 'A', 'seq': 1, 'serviced_tick': 1,
                  'due_tick': 1, 'resource_phase': 'native-slack'}]
                if grant else [])
        probe = {'tick': 1, 'selected': selected,
                 'ready_ACKs_before': ready,
                 'pre_forward_ACK_grants': grant,
                 'native_source_priority_veto': veto,
                 'ready_forward_before': int(veto),
                 'ready_native_feedback_before': 0}
        ledger = {'tick': 1, 'phase': 'native-slack',
                  'native_service_used': 0, 'native_memory_used': 0,
                  'shadow_control_receipts': grant,
                  'shadow_service_units': grant,
                  'shadow_memory_units': grant*2,
                  'service_budget': capacity, 'memory_budget': 64,
                  'pe_service_caps': {'PE0': 2},
                  'pe_memory_caps': {'PE0': 64},
                  'domain_memory_caps': {'E': 64, 'O': 64}}
        summary = {'queue_priority_policy': 'bounded-turns'
                   if selected == 'consumer-first' else 'ACK-first',
                   'native_operator_updates': 0,
                   'frozen_actor_state_changed': False,
                   'derived_control_tail_grants': 0,
                   'derived_actor_credit_ack_count': grant,
                   'concurrent_paid_applications': 0,
                   'delivered_other_unconsumed_pending': 1-grant,
                   'delivered_policy_blocked_pending': 0}
        receiver = {'control_delivered': 1, 'absence_certificates': 0}
        policy = 'bounded-turns' if selected == 'consumer-first' else 'ACK-first'
        return (ACKs, [], [probe], [ledger], summary, receiver,
                {'policy': policy, 'global_quota': 1,
                 'native_PE_budget': capacity})

    def audit(self, arguments):
        return audit_native_opportunities(*arguments[:6], **arguments[6])

    def test_signed_canonical_source_predecessor(self):
        self.assertEqual(sha256(self.raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_v3hij(self.prev, self.raw))

    def test_changed_predecessor_count_and_exclusion_fail_closed(self):
        for field, mutation in [
            ('new_derived_budget_runs', 0),
            ('total_source_tail_prefix_comparisons', 453),
            ('universal_ACK_deadline_or_native_learning_proven', True),
        ]:
            prev = deepcopy(self.prev)
            prev[field] = mutation
            with self.subTest(field=field), self.assertRaises(InterventionError):
                validate_v3hij(prev, canon(prev))

    def test_noncanoical_signed_predecessor_fail_closed(self):
        with self.assertRaises(InterventionError):
            validate_v3hij(self.prev, self.raw+b' ')

    def test_weak_native_free_ready_ack_does_not_suffice(self):
        case = list(self.witness())
        with self.assertRaises(NativeForkError):
            self.audit(case)
        case[2][0]['selected'] = 'consumer-first'
        case[4]['queue_priority_policy'] = 'bounded-turns'
        case[6]['policy'] = 'bounded-turns'
        result = self.audit(case)
        self.assertEqual(result['weak_no_veto_ready_without_ACK_ticks'], 1)
        self.assertEqual(result['sufficient_feasible_ACK_first_ticks'], 0)

    def test_real_feasible_source_ack_requires_actual_grant(self):
        result = self.audit(self.witness(grant=1))
        self.assertEqual(result['sufficient_feasible_ACK_first_ticks'], 1)
        self.assertEqual(result['sufficient_feasible_ACK_first_progress_ticks'], 1)
        self.assertEqual(result['source_inline_ACKs'], 1)

    def test_native_ready_veto_cannot_be_relabelled_as_slack(self):
        case = list(self.witness(selected='native-ready', veto=True))
        result = self.audit(case)
        self.assertEqual(result['ready_native_veto_ticks'], 1)
        case[2][0]['pre_forward_ACK_grants'] = 1
        case[3][0]['shadow_control_receipts'] = 1
        case[3][0]['shadow_service_units'] = 1
        case[3][0]['shadow_memory_units'] = 2
        with self.assertRaises(NativeForkError):
            self.audit(case)

    def test_resource_shortage_does_not_mint_a_completion_proof(self):
        case = list(self.witness())
        case[3][0]['native_memory_used'] = 64
        result = self.audit(case)
        self.assertEqual(result['ACK_first_resource_unproven_ticks'], 1)
        self.assertFalse(result['native_learning_or_scheduler_contract_proven'])

    def test_actor_epoch_future_due_and_wrong_phase_fail_closed(self):
        for change in ({'due_tick': 2}, {'seq': 2},
                       {'resource_phase': 'post-native-tail'},
                       {'serviced_tick': 0}):
            case = list(self.witness(grant=1))
            case[0][0].update(change)
            with self.subTest(change=change), self.assertRaises(NativeForkError):
                self.audit(case)

    def test_forged_resource_clock_and_capacity_are_refused(self):
        for key, value in [('tick', 2), ('service_budget', 2),
                           ('shadow_control_receipts', 2)]:
            case = list(self.witness(grant=1))
            case[3][0][key] = value
            with self.subTest(key=key), self.assertRaises(NativeForkError):
                self.audit(case)

    def test_frozen_native_all_source_code_pins(self):
        self.assertGreater(len(CODE_SHA), 25)
        for relative, digest in CODE_SHA.items():
            with self.subTest(source=relative):
                path = self.root/relative
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), digest)

    def test_contract_only_does_not_claim_progress_or_native_learning(self):
        report = build_report(self.prev, self.raw, None)
        self.assertNotEqual(report['status'], STATUS)
        self.assertFalse(report['universal_ACK_liveness_or_native_learning_proven'])
        self.assertEqual(report['native_operator_updates'], 0)

    def test_runner_rejects_existing_target_and_source_pin_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'contract.json'
            self.assertEqual(main(['--root', str(self.root), '--v3hij',
                                   str(self.source), '--out', str(output),
                                   '--contract-only']), 0)
            self.assertEqual(main(['--root', str(self.root), '--v3hij',
                                   str(self.source), '--out', str(output),
                                   '--contract-only']), 2)
            with patch.dict(CODE_SHA, {
                    'spk_backvalidation_v2/derived_native_opportunity_certificate_v3k.py':
                    '0'*64}):
                self.assertEqual(main(['--root', str(self.root), '--v3hij',
                    str(self.source), '--out', str(Path(temp)/'drift.json'),
                    '--contract-only']), 2)

    def test_complete_real_native_PE_queue_quota_and_adversarial_matrix(self):
        result = experiment(self.prev, self.raw, root=self.root,
            fixture_fn=fixture, native_executor=execute_live_v0e,
            plan_type=LiveBVPlanV0e)
        self.assertEqual(result['new_original_native_runs'], 54)
        self.assertEqual(result['new_derived_policy_runs'], 216)
        self.assertEqual(result['new_causal_null_runs'], 108)
        self.assertEqual(result['sufficient_source_opportunities'], 356)
        self.assertEqual(result['unsafe_weak_no_veto_opportunities'], 44)
        contrasts = result['policy_and_global_resource_contrasts']
        self.assertEqual(contrasts['normal_native_projection_exact'], 216)
        self.assertEqual(contrasts['ACK_first_more_inline'], 15)
        self.assertEqual(contrasts['higher_quota_fewer_inline'], 7)
        self.assertEqual(contrasts['higher_quota_strictly_more_inline'], 31)
        self.assertEqual(len(result['nonmonotone_inline_quota_witnesses']), 7)
        self.assertTrue(result['frozen_source_pins_preserved'])
        report = build_report(self.prev, self.raw, result)
        self.assertEqual(report['status'], STATUS)
        self.assertTrue(report['strict_full_original_native_projection_preserved'])
        self.assertFalse(report['universal_ACK_liveness_or_native_learning_proven'])


if __name__ == '__main__':
    unittest.main()
