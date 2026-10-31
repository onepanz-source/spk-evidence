"""Adversarial source-native budget comparisons: no scheduler installation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_actor_capacity_envelope_v4def import (
    EnvelopeRejected, STATUS, V4_REPORT_SHA, evaluate, native_headroom,
)
from search.spk_bv_v4def_native_capacity_envelope import CODE_SHA, main
from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e


class TestV4defNativeCapacityEnvelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

        def locate(name, env):
            options = ([Path(os.environ[env])] if os.environ.get(env) else [])
            options += [Path('/tmp')/name, cls.root.parent.parent/name]
            found = next((p for p in options if p.is_file()), None)
            if found is None:
                raise FileNotFoundError('v4 capacity source missing: '+name)
            return found

        cls.v3_path = locate('spk-bv-v3tuv-grant-rank.json', 'SPK_V3TUV_REPORT')
        cls.v4_path = locate('spk-bv-v4abc-native-contract-candidate.json',
                             'SPK_V4ABC_REPORT')
        cls.v3_raw = cls.v3_path.read_bytes()
        cls.v4_raw = cls.v4_path.read_bytes()
        cls.v3 = json.loads(cls.v3_raw)
        cls.v4 = json.loads(cls.v4_raw)
        cls.report = evaluate(cls.v3, cls.v3_raw, cls.v4, cls.v4_raw)
        cls.totals = cls.report['source_native_observed_capacity']

    def test_signed_report_boundaries_and_native_source_pins(self):
        self.assertEqual(sha256(self.v4_raw).hexdigest(), V4_REPORT_SHA)
        self.assertTrue(all(sha256((self.root/rel).read_bytes()).hexdigest() == h
                            for rel, h in CODE_SHA.items()))
        self.assertFalse(self.v4['native_actor_service_policy_implemented'])

    def test_eighteen_exact_original_replays_seventy_two_contexts(self):
        self.assertEqual(self.totals['original_native_replays'], 18)
        self.assertEqual(self.totals['derived_source_contexts'], 72)
        self.assertEqual(self.totals['source_ticks'], 2560)
        self.assertEqual(self.totals['source_ACK_grants'], 329)

    def test_real_native_global_PE_busy_vs_remaining_spare(self):
        self.assertEqual(self.totals['pending_no_grant_ticks'], 1812)
        self.assertEqual(self.totals['pending_no_grant_global_PE_full'], 1294)
        self.assertEqual(self.totals['pending_no_grant_all_native_resources_spare'], 518)
        self.assertEqual(self.totals['pending_no_grant_owner_PE_full_after_global_spare'], 0)
        self.assertEqual(self.totals['pending_no_grant_memory_full_after_PE_spare'], 0)

    def test_four_tick_source_windows_capacity_lower_bound(self):
        self.assertEqual(self.totals['zero_grant_windows']['4'], 1359)
        self.assertEqual(self.totals['zero_grant_windows_with_no_native_resource_slot']['4'], 950)
        self.assertEqual(self.totals['zero_grant_windows_with_some_native_resource_slot']['4'], 409)

    def test_eight_tick_source_windows_are_overlapping_not_additive(self):
        self.assertEqual(self.totals['zero_grant_windows']['8'], 955)
        self.assertEqual(self.totals['zero_grant_windows_with_no_native_resource_slot']['8'], 708)
        self.assertEqual(self.totals['zero_grant_windows_with_some_native_resource_slot']['8'], 247)
        self.assertIn('overlapping windows are dependent and cannot be summed as service costs',
                      self.report['interpretation_limits'])

    def test_horizon_varies_and_W4_rank16_never_certified(self):
        self.assertEqual((self.totals['min_native_horizon_ticks'],
                          self.totals['max_native_horizon_ticks']), (17, 45))
        self.assertEqual(self.totals['horizon_rank_shortfall_ticks'],
                         {'4': 1274, '8': 1679})
        rows = self.report['conditional_reservation_envelope']
        self.assertTrue(all(x['native_replays_with_horizon_at_least_W_times_16'] == 0
                            for x in rows if x['window_ticks'] in (4, 8)))

    def test_PE_saturated_capacity_fraction_is_only_conditional(self):
        expected = {(2, 1): 50, (2, 2): 25,
                    (4, 1): 25, (4, 2): 12.5,
                    (8, 1): 12.5, (8, 2): 6.25}
        actual = {(row['window_ticks'], row['global_PE_capacity']):
                  row['fully_saturated_global_capacity_share_percent']
                  for row in self.report['conditional_reservation_envelope']}
        self.assertEqual(actual, expected)
        self.assertTrue(all(not row['real_native_reserved_ACK_policy_executed']
                            for row in self.report['conditional_reservation_envelope']))

    def test_real_native_temporal_and_resource_claims_remain_excluded(self):
        self.assertEqual(self.report['status'], STATUS)
        self.assertFalse(self.report['native_v0e_modified'])
        self.assertFalse(self.report['any_reserved_service_contract_implemented'])
        self.assertFalse(self.report['any_native_actor_liveness_or_learning_proven'])
        self.assertIn('no forward completion time/energy cost has been simulated',
                      self.report['interpretation_limits'])

    def test_false_extra_global_or_owner_PE_slot_rejected(self):
        tick = {'pe_service_total': 1, 'pe_service_by_pe': {'PE0': 1},
                'memory_total': 3, 'memory_by_pe': {'PE0': 3},
                'memory_by_domain': {'O': 1, 'E': 2}}
        base = dict(global_cap=1, owner_cap=2, owner_memory_cap=64,
                    total_memory_cap=64, O_cap=64, E_cap=64)
        self.assertFalse(native_headroom(tick, **base)['global_PE_free'])
        self.assertTrue(native_headroom(tick, **{**base, 'global_cap': 2})['all_free'])
        self.assertFalse(native_headroom(tick, **{**base, 'global_cap': 2,
                                                 'owner_cap': 1})['owner_PE_free'])

    def test_memory_is_an_independent_real_budget(self):
        tick = {'pe_service_total': 0, 'pe_service_by_pe': {'PE0': 0},
                'memory_total': 63, 'memory_by_pe': {'PE0': 63},
                'memory_by_domain': {'O': 63, 'E': 63}}
        r = native_headroom(tick, global_cap=2, owner_cap=2,
                            owner_memory_cap=64, total_memory_cap=64,
                            O_cap=64, E_cap=64)
        self.assertTrue(r['global_PE_free'] and r['owner_PE_free'])
        self.assertFalse(r['O_E_memory_free'] or r['all_free'])

    def test_forged_PE_counters_and_booleans_fail_closed(self):
        tick = {'pe_service_total': 3, 'pe_service_by_pe': {'PE0': 1},
                'memory_total': 0, 'memory_by_pe': {}, 'memory_by_domain': {}}
        with self.assertRaises(EnvelopeRejected):
            native_headroom(tick, global_cap=2, owner_cap=2,
                            owner_memory_cap=64, total_memory_cap=64,
                            O_cap=64, E_cap=64)
        with self.assertRaises(EnvelopeRejected):
            native_headroom(tick, global_cap=True, owner_cap=2,
                            owner_memory_cap=64, total_memory_cap=64,
                            O_cap=64, E_cap=64)

    def test_signed_source_mutation_of_rank_or_mode_rejected(self):
        altered = deepcopy(self.v3)
        altered['source_matrix'][0]['modes'][0]['capacities'][0][
            'derived_policies']['ACK-first']['1']['rank_audit'][
            'per_tick_fifo_prefix'][0]['tick'] = 999
        with self.assertRaises(ValueError):
            evaluate(altered, canon(altered), self.v4, self.v4_raw)
        altered4 = deepcopy(self.v4)
        altered4['candidate_modes']['NATIVE_COMPATIBLE']['proposal'][
            'full_original_native_timing_parity_claimed'] = False
        with self.assertRaises(ValueError):
            evaluate(self.v3, self.v3_raw, altered4, canon(altered4))

    def test_counterfeit_native_scheduler_result_is_rejected(self):
        def forged(*args, **kwargs):
            native = execute_live_v0e(*args, **kwargs)
            native['resources']['timeline'][0]['pe_service_total'] += 1
            return native
        with self.assertRaises(EnvelopeRejected):
            evaluate(self.v3, self.v3_raw, self.v4, self.v4_raw,
                     native_executor=forged)

    def test_create_only_CLI_and_code_drift_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'capacity.json'
            options = ['--root', str(self.root), '--v3tuv', str(self.v3_path),
                       '--v4abc', str(self.v4_path), '--out', str(out)]
            self.assertEqual(main(options), 0)
            self.assertEqual(json.loads(out.read_bytes()), self.report)
            self.assertEqual(main(options), 2)
            relative = 'spk_bv_research/native_actor_capacity_envelope_v4def.py'
            with patch.dict(CODE_SHA, {relative: '0'*64}):
                self.assertEqual(main(options[:-1]+[str(Path(d)/'new.json')]), 2)


if __name__ == '__main__':
    unittest.main()
