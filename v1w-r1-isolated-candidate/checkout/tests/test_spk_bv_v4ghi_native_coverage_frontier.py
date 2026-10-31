"""BV v4g-v4i exact interval solver and signed-native frontier adversarial tests."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_actor_coverage_frontier_v4ghi import (
    STATUS, PREVIOUS_REPORT_SHA, WINDOWS, EnvelopeRejected,
    cover_dp, evaluate, ready_runs, window_audit,
)
from search.spk_bv_v4ghi_native_coverage_frontier import CODE_SHA, main


class TestV4ghiNativeCoverageFrontier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

        def locate(name, env):
            options = ([Path(os.environ[env])] if os.environ.get(env) else [])
            options += [Path('/tmp')/name, cls.root.parent.parent/name]
            value = next((p for p in options if p.is_file()), None)
            if value is None:
                raise FileNotFoundError('v4g exact frontier source missing: '+name)
            return value

        cls.source_paths = [
            locate('spk-bv-v3tuv-grant-rank.json', 'SPK_V3TUV_REPORT'),
            locate('spk-bv-v4abc-native-contract-candidate.json', 'SPK_V4ABC_REPORT'),
            locate('spk-bv-v4def-native-capacity-envelope.json', 'SPK_V4DEF_REPORT'),
        ]
        cls.raw = [p.read_bytes() for p in cls.source_paths]
        cls.source = [json.loads(r) for r in cls.raw]
        cls.report = evaluate(cls.source[0], cls.raw[0], cls.source[1], cls.raw[1],
                              cls.source[2], cls.raw[2])

    def test_signed_source_and_full_native_pins(self):
        self.assertEqual(sha256(self.raw[2]).hexdigest(), PREVIOUS_REPORT_SHA)
        self.assertTrue(all(sha256((self.root/r).read_bytes()).hexdigest() == h
                            for r, h in CODE_SHA.items()))

    def test_still_eighteen_exact_native_replays_and_seventy_two_contexts(self):
        self.assertEqual(self.report['source_original_native_replays'], 18)
        self.assertEqual(self.report['source_derived_contexts'], 72)
        self.assertEqual(self.report['signed_v4def_sha256'], PREVIOUS_REPORT_SHA)

    def test_full_four_tick_rollup_and_no_spare_witness(self):
        w = self.report['window_frontiers']['4']
        self.assertEqual(w['complete_zero_grant_windows'], 1359)
        self.assertEqual(w['windows_without_any_native_spare'], 950)
        self.assertEqual(w['source_pending_runs'], 197)
        self.assertEqual(w['strict_spare_only_infeasible_contexts'], 50)
        self.assertEqual(w['strict_spare_only_feasible_contexts'], 22)
        self.assertEqual(w['unrestricted_minimum_cover_slots'], 399)
        self.assertEqual(w['optimistic_minimum_nonspare'], 280)
        self.assertEqual(w['optimistic_minimum_nonspare_slots'], 403)
        self.assertEqual(w['unrestricted_minimum_cover_nonspare'], 284)
        self.assertEqual(w['first_strict_infeasibility_case'][
            'window_inclusive_ticks'], [5, 8])

    def test_full_two_and_eight_tick_rollups(self):
        w2, w8 = (self.report['window_frontiers'][str(w)] for w in (2, 8))
        self.assertEqual((w2['complete_zero_grant_windows'],
                          w2['windows_without_any_native_spare'],
                          w2['strict_spare_only_infeasible_contexts'],
                          w2['unrestricted_minimum_cover_slots'],
                          w2['optimistic_minimum_nonspare']),
                         (1615, 1128, 64, 846, 610))
        self.assertEqual((w8['complete_zero_grant_windows'],
                          w8['windows_without_any_native_spare'],
                          w8['strict_spare_only_infeasible_contexts'],
                          w8['unrestricted_minimum_cover_slots'],
                          w8['optimistic_minimum_nonspare']),
                         (955, 708, 32, 161, 112))

    def test_full_exhaustive_solver_vs_reference_enumeration(self):
        # Independent brute force: source lengths 0..7, every capacity pattern,
        # two objective orders and strict/optimistic admission.
        checks = 0
        for n in range(8):
            for spare in product((False, True), repeat=n):
                for window in (1, 2, 3, 4):
                    feasible = []
                    for choices in product((False, True), repeat=n):
                        if all(any(choices[i:i+window])
                               for i in range(max(0, n-window+1))):
                            selected = tuple(i for i, val in enumerate(choices) if val)
                            nonspare = sum(not spare[i] for i in selected)
                            feasible.append((len(selected), nonspare, selected))
                    for strict in (False, True):
                        eligible = [v for v in feasible if not strict or v[1] == 0]
                        for conflict_first in (False, True):
                            found = cover_dp(spare, window, restrict_to_spare=strict,
                                             nonspare_first=conflict_first)
                            if not eligible:
                                self.assertIsNone(found)
                            else:
                                expected = min(eligible,
                                               key=lambda x: (x[1], x[0], x[2])
                                               if conflict_first else x)
                                self.assertEqual((found['placements'],
                                                  found['nonspare'],
                                                  tuple(found['local_indices'])), expected)
                            checks += 1
        self.assertGreaterEqual(checks, 4000)

    def test_coverage_math_obeys_complete_window_not_partial_horizon(self):
        # No complete W-window => no assertion, even if ready remains pending.
        self.assertEqual(cover_dp((False, False, False), 4,
                                  restrict_to_spare=True)['placements'], 0)
        self.assertIsNone(cover_dp((False, False, False, False), 4,
                                   restrict_to_spare=True))
        self.assertEqual(cover_dp((True, False, False, False), 4,
                                  restrict_to_spare=True)['local_indices'], [0])
        rows = [{'tick': 1+i, 'ready_control_count': 1,
                 'grant_prefix_count': 0} for i in range(5)]
        self.assertEqual(ready_runs(rows, (False,)*5), [(0, 5, (False,)*5)])
        self.assertEqual(window_audit(rows, (False,)*5, 4)[
            'windows_without_any_native_spare'], 2)

    def test_real_grants_break_streak_and_native_schedule_is_unmodified(self):
        rows = [{'tick': 1+i, 'ready_control_count': 1,
                 'grant_prefix_count': int(i == 3)} for i in range(9)]
        self.assertEqual([(a, b) for a, b, _ in ready_runs(rows, (False,)*9)],
                         [(0, 3), (4, 9)])
        self.assertEqual(window_audit(rows, (False,)*9, 4)[
            'complete_zero_grant_windows'], 2)
        self.assertFalse(self.report['native_v0e_modified'])

    def test_a_nominal_slot_is_not_service_authorization(self):
        self.assertEqual(self.report['status'], STATUS)
        model = self.report['coverage_model']
        self.assertFalse(model['actual_ACK_admission'])
        self.assertTrue(model['spare_does_not_imply_authorization_or_recipient_credit'])
        self.assertIsNone(model['preserves_actual_forward_deadlines_if_reserved'])
        self.assertFalse(self.report['reserved_native_ACK_arbiter_implemented'])
        self.assertFalse(self.report['universal_native_ACK_deadline_proven'])
        self.assertFalse(self.report['actor_learning_implemented'])

    def test_invalid_capacity_types_and_unbounded_horizon_rejected(self):
        for capacity, win in (([True, 1], 2), ([False]*129, 4),
                              ([False], 0), ([False], True)):
            with self.assertRaises(EnvelopeRejected):
                cover_dp(capacity, win, restrict_to_spare=True)
        with self.assertRaises(EnvelopeRejected):
            window_audit([{'tick': 5, 'ready_control_count': 1,
                           'grant_prefix_count': 0}], ('not boolean',), 2)

    def test_corrupt_previous_or_v3_source_fail_closed(self):
        bad_prev = deepcopy(self.source[2])
        bad_prev['source_native_observed_capacity'][
            'pending_no_grant_ticks'] += 1
        with self.assertRaises(ValueError):
            evaluate(self.source[0], self.raw[0], self.source[1], self.raw[1],
                     bad_prev, canon(bad_prev))
        bad_v3 = deepcopy(self.source[0])
        bad_v3['new_original_native_runs'] = 0
        with self.assertRaises(ValueError):
            evaluate(bad_v3, canon(bad_v3), self.source[1], self.raw[1],
                     self.source[2], self.raw[2])

    def test_fake_native_timeline_is_rejected_by_source_digest(self):
        def forged(*args, **kwargs):
            record = execute_live_v0e(*args, **kwargs)
            record['resources']['timeline'][0]['pe_service_total'] += 1
            return record
        with self.assertRaises(EnvelopeRejected):
            evaluate(self.source[0], self.raw[0], self.source[1], self.raw[1],
                     self.source[2], self.raw[2], native_executor=forged)

    def test_create_only_command_and_code_digest_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'result.json'
            argv = ['--root', str(self.root), '--v3tuv', str(self.source_paths[0]),
                    '--v4abc', str(self.source_paths[1]),
                    '--v4def', str(self.source_paths[2]), '--out', str(output)]
            self.assertEqual(main(argv), 0)
            self.assertEqual(output.read_bytes(), canon(self.report))
            self.assertEqual(main(argv), 2)
            rel = 'spk_bv_research/native_actor_coverage_frontier_v4ghi.py'
            with patch.dict(CODE_SHA, {rel: '0'*64}):
                self.assertEqual(main(argv[:-1]+[str(Path(tmp)/'different.json')]), 2)


if __name__ == '__main__':
    unittest.main()
