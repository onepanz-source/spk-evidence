"""BV v4j-v4l source-native typed donor arbitration and adversarial boundary."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_shadow_arbiter_v4jkl import (
    STATUS, FRONTIER_REPORT_SHA, EnvelopeRejected, candidate_slot,
    native_service_tokens, arbitrate_fixed_source, evaluate,
)
from search.spk_bv_v4jkl_native_ACK_shadow_arbiter import CODE_SHA, main


class TestV4jklNativeACKShadowArbiter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

        def locate(filename, environment):
            options = ([Path(os.environ[environment])] if os.environ.get(environment)
                       else []) + [Path('/tmp')/filename, cls.root.parent.parent/filename]
            found = next((p for p in options if p.is_file()), None)
            if found is None:
                raise FileNotFoundError('v4j-v4l signed source missing: '+filename)
            return found

        inputs = [
            ('spk-bv-v3tuv-grant-rank.json', 'SPK_V3TUV_REPORT'),
            ('spk-bv-v4abc-native-contract-candidate.json', 'SPK_V4ABC_REPORT'),
            ('spk-bv-v4def-native-capacity-envelope.json', 'SPK_V4DEF_REPORT'),
            ('spk-bv-v4ghi-exact-native-coverage-frontier.json', 'SPK_V4GHI_REPORT'),
        ]
        cls.paths = [locate(name, env) for name, env in inputs]
        cls.raw = [p.read_bytes() for p in cls.paths]
        cls.sources = [json.loads(b) for b in cls.raw]
        cls.report = evaluate(cls.sources[0], cls.raw[0],
                              cls.sources[1], cls.raw[1],
                              cls.sources[2], cls.raw[2],
                              cls.sources[3], cls.raw[3])

    def row(self, w, strategy, admission, preference='none'):
        return self.report['shadow_variants'][
            f'W{w}/{strategy}/{admission}/{preference}']

    def test_all_source_digests_exact_and_signed_frontier(self):
        self.assertEqual(sha256(self.raw[3]).hexdigest(), FRONTIER_REPORT_SHA)
        self.assertTrue(all(sha256((self.root/name).read_bytes()).hexdigest() == expected
                            for name, expected in CODE_SHA.items()))

    def test_source_native_original_18_replays_640_ticks_624_identified_services(self):
        self.assertEqual(self.report['source_original_native_replays'], 18)
        self.assertEqual(self.report['source_original_native_ticks'], 640)
        self.assertEqual(self.report['source_typed_native_service_units'], 624)
        self.assertEqual(self.report['source_derived_ACK_contexts'], 72)

    def test_W4_strict_native_deadline_policy_has_no_guarantee(self):
        strict = self.row(4, 'deadline-only', 'NATIVE_SPARE_ONLY')
        self.assertEqual(strict['contexts_with_complete_coverage'], 13)
        self.assertEqual(strict['contexts_with_missing_windows'], 59)
        self.assertEqual(strict['missing_full_source_windows'], 982)
        self.assertEqual(strict['native_service_units_would_be_displaced'], 0)

    def test_W4_opportunistic_spare_does_not_remove_strict_impossibility(self):
        strict = self.row(4, 'opportunistic-spare', 'NATIVE_SPARE_ONLY')
        self.assertEqual(strict['contexts_with_complete_coverage'], 22)
        self.assertEqual(strict['contexts_with_missing_windows'], 50)
        self.assertEqual(strict['synthetic_reservations'], 257)
        self.assertEqual(strict['native_service_units_would_be_displaced'], 0)

    def test_W4_conditional_donor_policy_shows_tradeoff(self):
        deadline = self.row(4, 'deadline-only',
                            'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-forward')
        eager = self.row(4, 'opportunistic-spare',
                         'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-forward')
        self.assertEqual((deadline['contexts_with_complete_coverage'],
                          deadline['synthetic_reservations'],
                          deadline['native_service_units_would_be_displaced']),
                         (72, 399, 291))
        self.assertEqual((eager['contexts_with_complete_coverage'],
                          eager['synthetic_reservations'],
                          eager['native_service_units_would_be_displaced']),
                         (72, 537, 280))
        self.assertIsNotNone(deadline['first_preempted_native_service']['donor']['identity'])

    def test_donor_preference_changes_forward_BV_witness_without_changing_slots(self):
        a = self.row(4, 'deadline-only',
                     'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-forward')
        b = self.row(4, 'deadline-only',
                     'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-BV')
        self.assertEqual(a['native_service_units_would_be_displaced'], 291)
        self.assertEqual(b['native_service_units_would_be_displaced'], 291)
        self.assertEqual(a['native_forward_units_would_be_displaced'], 190)
        self.assertEqual(b['native_forward_units_would_be_displaced'], 195)
        self.assertEqual(a['native_BV_units_would_be_displaced'], 101)
        self.assertEqual(b['native_BV_units_would_be_displaced'], 96)

    def test_W2_and_W8_shadow_deadline_sensitivity(self):
        short = self.row(2, 'deadline-only',
                         'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-forward')
        long = self.row(8, 'deadline-only',
                        'PE_REASSIGN_CONDITIONAL_MEMORY_GUARD', 'protect-forward')
        self.assertEqual((short['synthetic_reservations'],
                          short['native_service_units_would_be_displaced']), (846, 626))
        self.assertEqual((long['synthetic_reservations'],
                          long['native_service_units_would_be_displaced']), (161, 120))
        self.assertEqual(short['contexts_with_complete_coverage'], 72)
        self.assertEqual(long['contexts_with_complete_coverage'], 72)

    def test_exact_typed_donor_preference_and_PE_accounting(self):
        tick = {'tick': 1, 'pe_service_total': 2,
                'pe_service_by_pe': {'PE0': 1, 'PE1': 1},
                'memory_total': 0, 'memory_by_pe': {}, 'memory_by_domain': {}}
        ops = [{'kind': 'forward', 'identity': 'f', 'pe': 'PE0',
                'source_original_tick': 1},
               {'kind': 'BV', 'identity': 'b', 'pe': 'PE1',
                'source_original_tick': 1}]
        base = {'global_cap': 2, 'owner_cap': 2, 'owner_memory_cap': 64,
                'total_memory_cap': 64, 'O_cap': 64, 'E_cap': 64,
                'allow_PE_reassign': True}
        fp = candidate_slot(tick, ops, donor_preference='protect-forward', **base)
        bp = candidate_slot(tick, ops, donor_preference='protect-BV', **base)
        self.assertEqual(fp['donor']['identity'], 'b')
        self.assertEqual(bp['donor']['identity'], 'f')
        self.assertEqual(fp['slot_kind'], 'preempted-native-PE')
        no_auth = candidate_slot(tick, ops, donor_preference='protect-forward',
                                 **{**base, 'allow_PE_reassign': False})
        self.assertFalse(no_auth['accepted'])

    def test_full_owner_requires_same_PE_owner_donor(self):
        tick = {'tick': 2, 'pe_service_total': 2,
                'pe_service_by_pe': {'PE0': 1, 'PE1': 1},
                'memory_total': 0, 'memory_by_pe': {}, 'memory_by_domain': {}}
        native_ops = ({'kind': 'forward', 'identity': 'f', 'pe': 'PE0',
                       'source_original_tick': 2},
                      {'kind': 'BV', 'identity': 'b', 'pe': 'PE1',
                       'source_original_tick': 2})
        x = candidate_slot(tick, native_ops, global_cap=2, owner_cap=1,
                           total_memory_cap=64, owner_memory_cap=64,
                           O_cap=64, E_cap=64, allow_PE_reassign=True,
                           donor_preference='protect-forward')
        self.assertEqual(x['donor']['identity'], 'f')

    def test_independent_memory_denial_cannot_be_cured_by_PE_donor_only(self):
        tick = {'tick': 2, 'pe_service_total': 1,
                'pe_service_by_pe': {'PE0': 1},
                'memory_total': 64, 'memory_by_pe': {'PE0': 64},
                'memory_by_domain': {'O': 64, 'E': 0}}
        x = candidate_slot(tick, ({'kind': 'forward', 'identity': 'f',
                                   'pe': 'PE0', 'source_original_tick': 2},),
                           global_cap=1, owner_cap=2, total_memory_cap=64,
                           owner_memory_cap=64, O_cap=64, E_cap=64,
                           allow_PE_reassign=True,
                           donor_preference='protect-forward')
        self.assertFalse(x['accepted'])
        self.assertEqual(x['reason'], 'O_E_MEMORY_NOT_PROVEN')

    def test_single_run_deadline_marks_native_debt_but_not_reexecution(self):
        rows = [{'tick': t, 'ready_control_count': 1, 'grant_prefix_count': 0}
                for t in range(1, 5)]
        timeline = [{'tick': t, 'pe_service_total': 1,
                     'pe_service_by_pe': {'PE1': 1}, 'memory_total': 0,
                     'memory_by_pe': {}, 'memory_by_domain': {}}
                    for t in range(1, 5)]
        ops = {t: ({'identity': f'f{t}', 'kind': 'forward', 'pe': 'PE1',
                    'source_original_tick': t},) for t in range(1, 5)}
        r = arbitrate_fixed_source(rows, timeline, ops, window=4,
                                   strategy='deadline-only',
                                   allow_PE_reassign=True,
                                   donor_preference='protect-BV',
                                   global_cap=1, owner_cap=2,
                                   owner_memory_cap=64, total_memory_cap=64,
                                   O_cap=64, E_cap=64)
        self.assertEqual(r['synthetic_service_reservations'], 1)
        self.assertEqual(r['native_service_debt_ledger'][0]['identity'], 'f4')
        self.assertTrue(r['complete_source_window_coverage'])
        self.assertFalse(r['native_service_debt_reexecuted'])
        self.assertFalse(r['forward_or_BV_causal_timing_recomputed'])
        self.assertEqual(r['real_actor_ACK_deliveries'], 0)

    def test_bad_clock_or_forged_native_PE_service_fails_closed(self):
        with self.assertRaises(EnvelopeRejected):
            native_service_tokens({'resources': {'timeline': [{'tick': 1,
                'pe_service_by_pe': {'PE0': 1}, 'pe_service_total': 1,
                'forward_computations': 0, 'feedback_sends': 0}]},
                'forward': {'batches': []}, 'feedback': {'link_grants': []}},
                {'A': 'PE0'})
        bad = deepcopy(self.sources[3]); bad['source_derived_contexts'] = 0
        with self.assertRaises(ValueError):
            evaluate(self.sources[0], self.raw[0], self.sources[1], self.raw[1],
                     self.sources[2], self.raw[2], bad, canon(bad))

    def test_counterfeit_native_replay_digest_cannot_pass(self):
        def corrupted(*args, **kwargs):
            result = execute_live_v0e(*args, **kwargs)
            result['forward']['batches'][0]['tick'] += 1
            return result
        with self.assertRaises(EnvelopeRejected):
            evaluate(self.sources[0], self.raw[0], self.sources[1], self.raw[1],
                     self.sources[2], self.raw[2], self.sources[3], self.raw[3],
                     native_executor=corrupted)

    def test_explicit_no_policy_adoption_and_no_learning(self):
        self.assertEqual(self.report['status'], STATUS)
        self.assertFalse(self.report['native_v0e_modified'])
        self.assertFalse(self.report['actual_native_scheduler_rearbitration_implemented'])
        self.assertFalse(self.report['native_forward_completion_latency_measured'])
        self.assertFalse(self.report['native_actor_learning_implemented'])
        self.assertTrue(any('unresolved causal debt' in s for s in
                            self.report['limitations']))

    def test_create_only_runner_and_new_module_SHA_drift_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'out.json'
            options = ['--root', str(self.root), '--v3tuv', str(self.paths[0]),
                       '--v4abc', str(self.paths[1]), '--v4def', str(self.paths[2]),
                       '--v4ghi', str(self.paths[3]), '--out', str(out)]
            self.assertEqual(main(options), 0)
            self.assertEqual(out.read_bytes(), canon(self.report))
            self.assertEqual(main(options), 2)
            with patch.dict(CODE_SHA, {
                'spk_bv_research/native_ack_shadow_arbiter_v4jkl.py': '0'*64}):
                self.assertEqual(main(options[:-1]+[str(Path(d)/'second.json')]), 2)


if __name__ == '__main__':
    unittest.main()
