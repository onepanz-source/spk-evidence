"""Independent v4m-v4o causal reexecution parity, custody and attack tests."""
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

from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_causal_audit_v4mno import (
    SIGNED_V4JKL_SHA, evaluate, parity_without_requests,
    require_resource_conservation,
)
from spk_bv_research.native_ack_causal_replay_v4mno import (
    STATUS, CausalProbeRejected, SyntheticACKRequest, execute_causal_probe,
)
from search.spk_bv_v0e_live_evidence import fixture
from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v4mno_native_ACK_causal_replay import CODE_SHA, main


class TestV4mnoCausalACKResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

        def locate(filename, key):
            options = ([Path(os.environ[key])] if os.environ.get(key) else []) + [
                Path('/tmp') / filename, cls.root.parent.parent / filename,
            ]
            found = next((path for path in options if path.is_file()), None)
            if found is None:
                raise FileNotFoundError('v4m-v4o signed input unavailable: ' + filename)
            return found

        cls.paths = [
            locate('spk-bv-v3tuv-grant-rank.json', 'SPK_V3TUV_REPORT'),
            locate('spk-bv-v4jkl-shadow-arbiter.json', 'SPK_V4JKL_REPORT'),
        ]
        cls.raw3, cls.raw4 = (path.read_bytes() for path in cls.paths)
        cls.v3, cls.shadow = (json.loads(raw) for raw in (cls.raw3, cls.raw4))
        cls.report = evaluate(cls.v3, cls.raw3, cls.shadow, cls.raw4)

    def test_signed_custody_exact_v4jkl_and_frozen_executor(self):
        self.assertEqual(sha256(self.raw4).hexdigest(), SIGNED_V4JKL_SHA)
        self.assertTrue(all(sha256((self.root / file).read_bytes()).hexdigest() == digest
                            for file, digest in CODE_SHA.items()))

    def test_no_intervention_native_bitwise_parity_of_full_native_payload(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        bv = LiveBVPlanV0e(enabled=True, priority='feedback-first')
        original = execute_live_v0e(case, fabric, *plans, bv)
        changed = execute_causal_probe(case, fabric, *plans, bv, ())
        self.assertTrue(parity_without_requests(original, changed))
        require_resource_conservation(changed)
        self.assertEqual(changed['synthetic_ack']['requests'], 0)

    def test_all_original_18_and_72_reexecutions_are_proven_by_signed_native(self):
        totals = self.report['totals']
        self.assertEqual(totals['original_native_replays'], 18)
        self.assertEqual(totals['derived_scenarios'], 72)
        self.assertEqual(totals['source_shadow_debt_tokens'], 291)
        self.assertEqual(totals['exogenous_requests'], 399)
        self.assertEqual(totals['simulated_ack_deliveries'], 399)

    def test_native_causal_reexecution_observably_changes_forward_and_BV(self):
        totals = self.report['totals']
        self.assertEqual(totals['native_forward_changed_scenarios'], 59)
        self.assertEqual(totals['native_BV_changed_scenarios'], 48)
        self.assertEqual(totals['terminal_changed_scenarios'], 59)
        self.assertEqual(totals['final_state_changed_scenarios'], 0)
        self.assertEqual(totals['horizon_extended_scenarios'], 60)
        self.assertNotEqual(self.report['first_signed_reexecution_fingerprint'][
            'source_original_native_sha256'], self.report[
            'first_signed_reexecution_fingerprint']['derived_replay_sha256'])

    def test_actual_link_service_and_delivery_charged_before_native(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        ack = SyntheticACKRequest('approved-synthetic-intent', 3)
        derived = execute_causal_probe(case, fabric, *plans, LiveBVPlanV0e(), (ack,))
        require_resource_conservation(derived)
        grant = derived['synthetic_ack']['transport_grants'][0]
        self.assertEqual((grant['tick'], grant['delivered_at']), (3, 4))
        self.assertEqual(grant['source_pe'], 'PE0')
        self.assertEqual(grant['target_pe'], 'PE1')
        self.assertEqual(derived['synthetic_ack']['applied_actor_credits'], 0)
        row = next(r for r in derived['native']['resources']['timeline'] if r['tick'] == 3)
        self.assertGreaterEqual(row['memory_by_domain']['O'], 1)
        self.assertGreaterEqual(row['memory_by_domain']['E'], 1)
        self.assertIn(['PE0', 'PE1', 1], row['link_by_direction'])

    def test_invalid_identity_order_time_and_PE_custody_fail_closed(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        bv = LiveBVPlanV0e()
        examples = [
            [SyntheticACKRequest('wrong-container', 2)],
            (SyntheticACKRequest('replay', 1), SyntheticACKRequest('replay', 2)),
            (SyntheticACKRequest('late', 4), SyntheticACKRequest('early', 3)),
            (SyntheticACKRequest('before-source-clock', 0),),
            (SyntheticACKRequest('bool-tick', True),),
            (SyntheticACKRequest('unknown-PE', 2, 'PE0', 'PE999'),),
            (SyntheticACKRequest('same-PE', 2, 'PE0', 'PE0'),),
            (SyntheticACKRequest('fake-owner', 2, 'PE2', 'PE1'),),
        ]
        for requests in examples:
            with self.subTest(requests=requests), self.assertRaises(CausalProbeRejected):
                execute_causal_probe(case, fabric, *plans, bv, requests)

    def test_bounded_horizon_does_not_claim_delivery_when_unavailable(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        limited = replace(plans[1], max_service_span_ticks=8)
        with self.assertRaisesRegex(CausalProbeRejected, 'horizon exceeded'):
            execute_causal_probe(case, fabric, plans[0], limited, plans[2], plans[3],
                                 LiveBVPlanV0e(), (SyntheticACKRequest('too-late', 20),))

    def test_inadequate_O_E_memory_is_not_implicitly_borrowed(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        restricted = replace(plans[2], fabric_slots_per_tick=1)
        # No synthetic grant can fit two O/E units; the engine eventually
        # rejects the bounded run instead of emitting a fake ACK delivery.
        with self.assertRaisesRegex(CausalProbeRejected, 'horizon exceeded'):
            execute_causal_probe(case, fabric, plans[0], plans[1], restricted,
                                 plans[3], LiveBVPlanV0e(),
                                 (SyntheticACKRequest('memory-denied', 3),))

    def test_global_PE_1_and_shared_link_1_are_never_overcommitted(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        strict = replace(plans[1], fabric_slots_per_tick=1)
        replay = execute_causal_probe(case, fabric, plans[0], strict,
                                       plans[2], plans[3], LiveBVPlanV0e(),
                                       (SyntheticACKRequest('ack-1', 3),
                                        SyntheticACKRequest('ack-2', 4)))
        require_resource_conservation(replay)
        for row in replay['native']['resources']['timeline']:
            self.assertLessEqual(row['pe_service_total'], 1)
            self.assertLessEqual(row['link_total'], 1)
        self.assertEqual(len(replay['synthetic_ack']['transport_deliveries']), 2)

    def test_causal_replay_independent_determinism(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        requests = (SyntheticACKRequest('ack-a', 3), SyntheticACKRequest('ack-b', 4))
        first = execute_causal_probe(case, fabric, *plans, LiveBVPlanV0e(), requests)
        second = execute_causal_probe(case, fabric, *plans, LiveBVPlanV0e(), requests)
        self.assertEqual(canon(first), canon(second))

    def test_inconsistent_synthetic_transport_grant_fails_independent_conservation(self):
        case, fabric, plans = fixture(ticks=(1, 3))
        replay = execute_causal_probe(
            case, fabric, *plans, LiveBVPlanV0e(), (SyntheticACKRequest('ack-x', 3),))
        forged = deepcopy(replay)
        forged['native']['resources']['timeline'][2]['link_total'] -= 1
        with self.assertRaisesRegex(CausalProbeRejected, 'link conservation'):
            require_resource_conservation(forged)
        forged = deepcopy(replay)
        forged['synthetic_ack']['transport_deliveries'][0]['actor_credit_applied'] = True
        with self.assertRaisesRegex(CausalProbeRejected, 'misreported as actor'):
            require_resource_conservation(forged)

    def test_signed_source_rejects_forged_counterfactual_report(self):
        forged = deepcopy(self.shadow)
        forged['source_contexts'][0]['variants'][
            'W4/deadline-only/PE_REASSIGN_CONDITIONAL_MEMORY_GUARD/protect-forward'][
                'reservation_ledger'][0]['tick'] += 1
        with self.assertRaises(CausalProbeRejected):
            evaluate(self.v3, self.raw3, forged, canon(forged))
        with self.assertRaises(CausalProbeRejected):
            evaluate(self.v3, self.raw3, self.shadow, self.raw4 + b' ')

    def test_actor_credit_and_policy_adoption_explicitly_excluded(self):
        self.assertEqual(self.report['status'], STATUS)
        self.assertFalse(self.report['real_actor_ACK_credit_applied'])
        self.assertFalse(self.report['native_scheduler_policy_adopted'])
        self.assertFalse(self.report['native_v0e_modified'])
        self.assertTrue(any('291 prior donor tokens' in s for s in
                            self.report['claims_excluded']))

    def test_create_only_report_and_code_SHA_drift_rejection(self):
        with tempfile.TemporaryDirectory() as dirname:
            out = Path(dirname) / 'signed.json'
            args = ['--root', str(self.root), '--v3tuv', str(self.paths[0]),
                    '--v4jkl', str(self.paths[1]), '--out', str(out)]
            self.assertEqual(main(args), 0)
            self.assertEqual(out.read_bytes(), canon(self.report))
            self.assertEqual(main(args), 2)
            with patch.dict(CODE_SHA, {
                'spk_bv_research/native_ack_causal_replay_v4mno.py': '0' * 64}):
                self.assertEqual(main(args[:-1] + [str(Path(dirname) / 'new.json')]), 2)

    def test_cli_refuses_repository_output_and_symlinked_signed_input(self):
        with self.assertRaises(ValueError):
            safe_output(self.root / 'docs' / 'must-not-be-created.json',
                        self.root, tuple(self.paths))
        with tempfile.TemporaryDirectory() as dirname:
            symlink = Path(dirname) / 'signed.json'
            symlink.symlink_to(self.paths[1])
            result = Path(dirname) / 'not-written.json'
            args = ['--root', str(self.root), '--v3tuv', str(self.paths[0]),
                    '--v4jkl', str(symlink), '--out', str(result)]
            self.assertEqual(main(args), 2)
            self.assertFalse(result.exists())


if __name__ == '__main__':
    unittest.main()
