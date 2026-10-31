"""BV v4a-v4c proposal only: source exposure, theorem and fail-closed plans."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from search.spk_bv_v4abc_native_actor_contract_candidate import CODE_SHA, main
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_actor_service_contract_candidate_v4abc import (
    CandidateRejected, PREDECESSOR_SHA, STATUS, analyze_predecessor,
    exhaustive_window_rank_check, profiles, source_row_gaps,
    validate_candidate, validate_signed_v3tuv,
)


class TestV4abcNativeActorContractDraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        paths = ([Path(os.environ['SPK_V3TUV_REPORT'])] if
                 os.environ.get('SPK_V3TUV_REPORT') else [])
        paths += [Path('/tmp/spk-bv-v3tuv-grant-rank.json'),
                  cls.root.parent.parent/'spk-bv-v3tuv-grant-rank.json']
        cls.reference = next((p for p in paths if p.is_file()), None)
        if cls.reference is None:
            raise FileNotFoundError('v4 signed v3tuv predecessor unavailable')
        cls.raw = cls.reference.read_bytes()
        cls.source = json.loads(cls.raw)

    def test_canonical_v3tuv_predecessor_sha_and_scope(self):
        self.assertEqual(sha256(self.raw).hexdigest(), PREDECESSOR_SHA)
        self.assertTrue(validate_signed_v3tuv(self.source, self.raw))
        self.assertFalse(self.source['universal_native_tick_deadline_proven'])

    def test_mutated_predecessor_rejected_before_new_contract_claim(self):
        for field, value in (
                ('new_derived_rank_runs', 71),
                ('native_operator_updates', 1),
                ('universal_native_tick_deadline_proven', True),
                ('status', 'NATIVE_FAIRNESS_PROVEN')):
            bad = deepcopy(self.source)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(CandidateRejected):
                analyze_predecessor(bad, canon(bad))
        with self.assertRaises(CandidateRejected):
            analyze_predecessor(self.source, self.raw+b' ')

    def test_source_observed_ungranted_pending_windows_not_new_native_proof(self):
        result = analyze_predecessor(self.source, self.raw)
        counts = result['source_exposure']
        self.assertEqual(counts['contexts'], 72)
        self.assertEqual(counts['real_global_ACK_grants'], 329)
        self.assertEqual(counts['real_grant_ticks'], 286)
        self.assertEqual(counts['source_ticks'], 2560)
        self.assertEqual(counts['maximum_pending_no_grant_streak'], 36)
        self.assertEqual(counts['contexts_with_zero_grant_window'],
                         {'1': 72, '2': 72, '4': 65, '8': 56})
        self.assertEqual(counts['overlapping_zero_grant_windows'],
                         {'1': 1812, '2': 1615, '4': 1359, '8': 955})
        self.assertEqual(result['status'], STATUS)
        self.assertFalse(result['native_actor_service_policy_implemented'])
        self.assertFalse(result['any_new_native_liveness_guarantee_proven'])

    def test_four_tick_adversarial_source_window_exposes_rate_absence(self):
        rows = [{'tick': i, 'ready_control_count': 3,
                 'grant_prefix_count': 0, 'oldest_ready_identity': 'j1'}
                for i in range(1, 6)]
        check = source_row_gaps(rows)
        self.assertEqual(check['windows_with_ready_ACK_but_zero_grants']['4'], 2)
        self.assertEqual(check['max_consecutive_pending_no_grant_ticks'], 5)
        self.assertEqual(check['real_global_ACK_grants'], 0)

    def test_tampered_clock_or_impossible_grant_rejected(self):
        for mutation in ('clock_duplicate', 'grant_over_ready',
                         'pending_disappears_without_grant'):
            trace = [{'tick': 1, 'ready_control_count': 2,
                      'grant_prefix_count': 0},
                     {'tick': 2, 'ready_control_count': 3,
                      'grant_prefix_count': 0}]
            if mutation == 'clock_duplicate':
                trace[1]['tick'] = 1
            elif mutation == 'grant_over_ready':
                trace[1]['grant_prefix_count'] = 4
            else:
                trace[1]['ready_control_count'] = 0
            with self.subTest(mutation=mutation), self.assertRaises(CandidateRejected):
                source_row_gaps(trace)

    def test_native_compatible_mode_deliberately_makes_no_deadline_claim(self):
        accepted = validate_candidate(profiles()['NATIVE_COMPATIBLE'])
        self.assertTrue(accepted['candidate_accepted_as_draft'])
        self.assertIsNone(accepted['conditional_deadline_offset_ticks'])
        self.assertFalse(accepted['implemented_on_native_scheduler'])

    def test_reserved_four_tick_profile_is_only_conditional(self):
        candidate = profiles()['RESERVED_ACK_WINDOW_4']
        result = validate_candidate(candidate)
        self.assertEqual(result['conditional_deadline_offset_ticks'], 63)
        self.assertFalse(result['rate_assumption_proven_by_admission'])
        self.assertFalse(result['native_fairness_or_learning_proven'])

    def test_missing_PE_owner_or_global_reservations_rejected(self):
        for field in ('owner_PE_preemption_authorized',
                      'global_PE_preemption_authorized',
                      'O_and_E_memory_reservation_admitted'):
            bad = deepcopy(profiles()['RESERVED_ACK_WINDOW_4'])
            bad[field] = False
            with self.subTest(field=field), self.assertRaises(CandidateRejected):
                validate_candidate(bad)

    def test_no_double_claim_of_native_parity_and_bounded_actor_priority(self):
        bad = deepcopy(profiles()['RESERVED_ACK_WINDOW_4'])
        bad['full_original_native_timing_parity_claimed'] = True
        with self.assertRaises(CandidateRejected):
            validate_candidate(bad)
        bad = deepcopy(profiles()['NATIVE_COMPATIBLE'])
        bad['minimum_oldest_ACK_grants_per_window'] = 1
        with self.assertRaises(CandidateRejected):
            validate_candidate(bad)

    def test_separate_consumer_charge_and_bool_as_int_rejected(self):
        for key, value in (
                ('consumer_resource_charge_is_separate', False),
                ('window_ticks', True),
                ('max_admitted_due_queue_rank', True),
                ('minimum_oldest_ACK_grants_per_window', True),
                ('max_native_horizon_ticks', True)):
            bad = deepcopy(profiles()['RESERVED_ACK_WINDOW_4'])
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(CandidateRejected):
                validate_candidate(bad)

    def test_horizon_and_queue_rank_bound_require_explicit_admission(self):
        for field, value in (
                ('max_native_horizon_ticks', 63),
                ('max_admitted_due_queue_rank', 513),
                ('window_ticks', 0),
                ('window_ticks', 65)):
            bad = deepcopy(profiles()['RESERVED_ACK_WINDOW_4'])
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(CandidateRejected):
                validate_candidate(bad)

    def test_conditional_finite_lemma_and_impossibility_counterexample(self):
        result = exhaustive_window_rank_check()
        self.assertEqual(result['enumerated_finite_grant_streams'], 682)
        self.assertEqual(result['conditional_FIFO_rank_window_lemma_counterexamples'], 0)
        self.assertTrue(result[
            'one_global_PE_strict_native_timing_and_same_tick_ACK_impossible'])
        self.assertTrue(result[
            'without_rate_assumption_all_zero_grants_can_defer_indefinitely'])

    def test_pinned_inherited_new_source_and_frozen_native_unchanged(self):
        self.assertGreater(len(CODE_SHA), 40)
        for path, digest in CODE_SHA.items():
            with self.subTest(path=path):
                self.assertEqual(sha256((self.root/path).read_bytes()).hexdigest(), digest)
        self.assertEqual(sha256((self.root/
            'spk_backvalidation_v0/live_dual_scheduler_v0e.py').read_bytes()).hexdigest(),
            '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9')

    def test_runner_create_only_and_source_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'draft.json'
            args = ['--root', str(self.root), '--v3tuv', str(self.reference),
                    '--out', str(out)]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 2)
            with patch.dict(CODE_SHA, {
                    'spk_bv_research/native_actor_service_contract_candidate_v4abc.py':
                    '0'*64}):
                args[args.index(str(out))] = str(Path(d)/'drift.json')
                self.assertEqual(main(args), 2)


if __name__ == '__main__':
    unittest.main()
