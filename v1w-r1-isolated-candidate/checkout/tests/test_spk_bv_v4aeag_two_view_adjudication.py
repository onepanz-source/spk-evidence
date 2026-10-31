"""Adversarial, source-backed v4ae-v4ag two-view disagreement research tests."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v0e_live_evidence import fixture
from search.spk_bv_v4aeag_two_view_adjudication import CODE_SHA, main
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.native_ack_causal_replay_v4mno import CausalProbeRejected
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_disagreement_v4aeag import (
    EscrowLedger, ORIGINS, VIEWS, adjudicate, expected_vote,
)
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    TEST_VIEW_KEYS, VARIANTS, VERDICTS, envelope, project_actual_native,
    reseal, run_variant,
)
from spk_bv_research.task_disagreement_audit_v4aeag import audit_row, evaluate

ROOT = Path(__file__).resolve().parents[1]
PARENT = 'a' * 64
KEY = 'schedule/mode/1'


class TestV4aeagTwoViewDisagreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3 = Path(os.environ.get('SPK_V3TUV_REPORT',
            '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4 = Path(os.environ.get('SPK_V4ABAD_REPORT',
            str(ROOT / 'docs/spk-bv-v4abad-oracle-custody-observation.json')))
        cls.raw3 = cls.v3.read_bytes()
        cls.raw4 = cls.v4.read_bytes()

    def setUp(self):
        case, fabric, plans = fixture(ticks=(1, 2))
        bv = LiveBVPlanV0e(enabled=False, priority='forward-first')
        self.source_sha = snapshot(execute_live_v0e(case, fabric, *plans, bv))
        self.projections, self.last_tick = project_actual_native(
            case, fabric, plans, bv, native_executor=execute_live_v0e)
        self.issued = case.events[0].timestamp

    def specimen(self):
        return envelope(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick)

    def adjudication(self, specimen, *, projections=None, ledger=None,
                     decision_tick=None, keys=None):
        return adjudicate(
            specimen, self.projections if projections is None else projections,
            TEST_VIEW_KEYS if keys is None else keys,
            expected_parent=PARENT, source_key=KEY,
            original_sha256=self.source_sha,
            precommitted_labels={'0': 1, '1': 0},
            completed_tick=self.last_tick,
            decision_tick=self.last_tick + 3 if decision_tick is None else decision_tick,
            ledger=EscrowLedger() if ledger is None else ledger)

    def test_source_signed_original_18_and_72_reexecuted_probes(self):
        r = evaluate(json.loads(self.raw3), self.raw3,
                     json.loads(self.raw4), self.raw4)
        self.assertEqual((r['totals']['signed_native_replays'],
                          r['totals']['counterfactual_native_probe_executions'],
                          r['totals']['adjudication_scenarios']), (18, 72, 270))
        self.assertEqual(r['reviewer_conflicts_quarantined'], 18)
        self.assertEqual(r['reviewer_abstentions_quarantined'], 18)
        self.assertEqual(r['program_adoptions'], 0)
        self.assertFalse(r['native_learning_implemented'])

    def test_distinct_extractors_agree_on_same_native_execution(self):
        a = self.projections['endpoint']
        b = self.projections['emission']
        self.assertEqual(expected_vote(a, {'0': 1, '1': 0}), ('IMPROVES', 4, 0))
        self.assertEqual(expected_vote(b, {'0': 1, '1': 0}), ('IMPROVES', 4, 0))
        self.assertEqual([x['count'] for x in a], [x['count'] for x in b])
        self.assertIn('terminal', ORIGINS['endpoint'])
        self.assertIn('emissions', ORIGINS['emission'])

    def test_same_observation_cannot_identify_task_ground_truth(self):
        a = self.projections['endpoint']
        self.assertEqual(expected_vote(a, {'0': 1, '1': 0}), ('IMPROVES', 4, 0))
        self.assertEqual(expected_vote(a, {'0': 0, '1': 1}), ('REGRESSES', 4, 9))
        # No observation or attestation distinguishes which task was intended.
        self.assertEqual(self.projections['endpoint'], self.projections['emission'])

    def test_unanimity_is_correlated_research_only_not_truth(self):
        verdict = self.adjudication(self.specimen())
        self.assertEqual(verdict['verdict'],
            'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST')
        self.assertTrue(verdict['reviewer_agreement'])
        for flag in ('promotion_authorized', 'program_adopted',
                     'native_learning_implemented',
                     'independent_real_world_truth_available',
                     'production_reviewer_authenticated',
                     'durable_escrow_implemented'):
            self.assertFalse(verdict[flag])

    def test_every_variant_has_deterministic_review_and_independent_rebuild(self):
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                r = run_variant(self.projections, KEY, self.source_sha,
                                PARENT, self.issued, self.last_tick, variant)
                r2 = run_variant(self.projections, KEY, self.source_sha,
                                 PARENT, self.issued, self.last_tick, variant)
                self.assertEqual(r, r2)
                self.assertEqual(r['decision']['verdict'], VERDICTS[variant])
                audit_row(r, self.projections, KEY, self.source_sha,
                          PARENT, self.issued, self.last_tick)

    def test_disagreement_cannot_promote_even_correct_correction(self):
        r = run_variant(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick, 'reviewer_disagreement')
        self.assertEqual(r['decision']['verdict'],
                         'QUARANTINE_REVIEWER_DISAGREEMENT')
        self.assertFalse(r['decision']['promotion_authorized'])

    def test_abstention_cannot_be_relabelled_as_agreement(self):
        r = run_variant(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick, 'reviewer_abstains')
        self.assertEqual(r['decision']['verdict'], 'QUARANTINE_ABSTENTION')

    def test_agreeing_false_votes_veto_even_with_valid_public_mac(self):
        r = run_variant(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick, 'unanimous_wrong_vote')
        self.assertEqual(r['decision']['verdict'],
                         'VETO_CONSENSUS_CONTRADICTS_OBSERVATION')
        self.assertTrue(r['decision']['reviewer_agreement'])

    def test_two_valid_attestations_cannot_rewrite_precommitted_task(self):
        r = run_variant(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick, 'co_signed_poisoned_task')
        self.assertEqual(r['decision']['verdict'], 'VETO_TASK_CANARY_CONFLICT')

    def test_missing_reviewer_is_not_quorum(self):
        self.assertEqual(run_variant(self.projections, KEY, self.source_sha,
            PARENT, self.issued, self.last_tick, 'missing_view')['decision']['verdict'],
            'VETO_INCOMPLETE_TWO_VIEW')

    def test_distinct_roles_cannot_share_origin_or_nonce(self):
        for variant, verdict in (
            ('forged_shared_origin', 'VETO_SHARED_OR_WRONG_EVIDENCE_ORIGIN'),
            ('shared_nonce', 'VETO_SHARED_NONCE')):
            self.assertEqual(run_variant(self.projections, KEY, self.source_sha,
                PARENT, self.issued, self.last_tick, variant)['decision']['verdict'],
                verdict)

    def test_role_separation_is_key_separation_not_production_identity(self):
        self.assertNotEqual(TEST_VIEW_KEYS['endpoint'], TEST_VIEW_KEYS['emission'])
        v = run_variant(self.projections, KEY, self.source_sha, PARENT,
                        self.issued, self.last_tick, 'single_shared_lab_key')
        self.assertEqual(v['decision']['verdict'], 'VETO_NO_SEPARATE_LAB_KEYS')
        self.assertFalse(v['decision']['production_reviewer_authenticated'])

    def test_authenticated_wrong_source_and_scope_still_veto(self):
        for variant, verdict in (('wrong_source', 'VETO_SOURCE_BINDING'),
                                 ('wrong_scope', 'VETO_SCOPE')):
            self.assertEqual(run_variant(self.projections, KEY, self.source_sha,
                PARENT, self.issued, self.last_tick, variant)['decision']['verdict'],
                verdict)

    def test_tamper_vetoes_authenticated_review_and_native_projection(self):
        for variant, verdict in (
            ('tampered_review', 'VETO_INVALID_ATTESTATION'),
            ('tampered_projection', 'VETO_NATIVE_PROJECTION_MISMATCH')):
            self.assertEqual(run_variant(self.projections, KEY, self.source_sha,
                PARENT, self.issued, self.last_tick, variant)['decision']['verdict'],
                verdict)

    def test_review_cannot_precede_native_observation(self):
        msg = self.specimen()
        msg['reviews']['endpoint']['observed_tick'] = self.last_tick
        reseal(msg)
        self.assertEqual(self.adjudication(msg)['verdict'], 'VETO_CAUSAL_ORDER')

    def test_late_decision_and_boolean_time_rejected(self):
        msg = self.specimen()
        self.assertEqual(self.adjudication(msg, decision_tick=True)['verdict'],
                         'VETO_DECISION_TIME')
        self.assertEqual(self.adjudication(msg, decision_tick=self.last_tick+20)['verdict'],
                         'VETO_DECISION_TIME')

    def test_replay_is_in_memory_only_and_not_persistent(self):
        msg = self.specimen()
        ledger = EscrowLedger()
        self.assertEqual(self.adjudication(msg, ledger=ledger)['verdict'],
                         'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST')
        self.assertEqual(self.adjudication(msg, ledger=ledger)['verdict'], 'VETO_REPLAY')
        self.assertEqual(len(ledger.seen), 2)
        # New invocation has no durable replay memory: known limitation.
        self.assertEqual(self.adjudication(msg)['verdict'],
                         'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST')

    def test_failed_review_does_not_consume_replay_nonces(self):
        msg = self.specimen()
        ledger = EscrowLedger()
        msg['reviews']['emission']['vote'] = 'ABSTAIN'
        reseal(msg)
        self.assertEqual(self.adjudication(msg, ledger=ledger)['verdict'],
                         'QUARANTINE_ABSTENTION')
        self.assertFalse(ledger.seen)

    def test_wrong_projection_order_rejected(self):
        projections = deepcopy(self.projections)
        projections['emission'].reverse()
        self.assertEqual(self.adjudication(self.specimen(),projections=projections)['verdict'],
                         'VETO_INVALID_PROJECTION')

    def test_no_evidence_projections_rejected(self):
        self.assertEqual(self.adjudication(self.specimen(),projections={})['verdict'],
                         'VETO_MISSING_NATIVE_PROJECTION')

    def test_bool_probe_counts_rejected(self):
        projections = deepcopy(self.projections)
        projections['endpoint'][0]['count'] = True
        self.assertEqual(self.adjudication(self.specimen(),projections=projections)['verdict'],
                         'VETO_INVALID_PROJECTION')

    def test_independent_audit_rejects_forged_row(self):
        r = run_variant(self.projections,KEY,self.source_sha,PARENT,
                        self.issued,self.last_tick,'reviewer_disagreement')
        r['decision']['reviewer_agreement'] = True
        with self.assertRaises(CausalProbeRejected):
            audit_row(r,self.projections,KEY,self.source_sha,PARENT,
                      self.issued,self.last_tick)

    def test_tampered_predecessor_rejected_before_native(self):
        prev = json.loads(self.raw4)
        prev['program_adoptions'] = 1
        with self.assertRaises(CausalProbeRejected):
            evaluate(json.loads(self.raw3),self.raw3,prev,
                     json.dumps(prev,sort_keys=True).encode())

    def test_create_only_and_byte_exact_observation(self):
        with TemporaryDirectory() as temp:
            dest = Path(temp) / 'report.json'
            args = ['--root', str(ROOT), '--v3tuv', str(self.v3),
                    '--v4abad', str(self.v4), '--out', str(dest)]
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
                args[-1] = str(ROOT / 'docs/v4aeag-unsafe-output.json')
                self.assertEqual(main(args),2)
            self.assertEqual(dest.read_bytes(),
                (ROOT / 'docs/spk-bv-v4aeag-two-view-observation.json').read_bytes())

    def test_sha_drift_fails_closed_without_output(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / 'out.json'
            changed = {**CODE_SHA,
                       'spk_bv_research/task_oracle_custody_v4abad.py': '0'*64}
            with patch.dict(CODE_SHA,changed), redirect_stderr(io.StringIO()):
                code = main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4abad',str(self.v4),'--out',str(target)])
            self.assertEqual(code,2)
            self.assertFalse(target.exists())

    def test_symlinked_predecessor_rejected(self):
        with TemporaryDirectory() as temp:
            link = Path(temp) / 'parent.json'
            link.symlink_to(self.v4)
            target = Path(temp) / 'out.json'
            with redirect_stderr(io.StringIO()):
                code = main(['--root',str(ROOT),'--v3tuv',str(self.v3),
                             '--v4abad',str(link),'--out',str(target)])
            self.assertEqual(code,2)
            self.assertFalse(target.exists())
