"""v4ak-v4am valid-fork/rollback and separately pinned lab-head tests."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from search.spk_bv_v4akam_external_anchor import CODE_SHA, main
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_anchor_audit_v4akam import evaluate
from spk_bv_research.task_anchor_fixture_v4akam import (
    TEST_ANCHOR_KEY, TEST_ANCHOR_KEY_OTHER, PARENT, REPORT_SHA,
    fork_and_rollback_counterexample, one_native_probe, SOURCE,
)
from spk_bv_research.task_anchor_v4akam import (
    AnchorRejected, GENESIS, REQUIRED_REPORT_SHA, SCHEMA,
    check_anchored_database, seal_reported_database, seal_state,
    verify_capsule,
)
from spk_bv_research.task_escrow_audit_v4ahaj import evaluate as old_evaluate
from spk_bv_research.task_escrow_fixture_v4ahaj import round_message
from spk_bv_research.task_escrow_store_v4ahaj import DurableEscrow
from spk_bv_research.task_disagreement_fixture_v4aeag import TEST_VIEW_KEYS

ROOT = Path(__file__).resolve().parents[1]


class TestV4akamSeparateHeadWitness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory(prefix='spk-anchor-reference-')
        cls.v3 = Path(os.environ.get('SPK_V3TUV_REPORT',
                        '/tmp/spk-bv-v3tuv-grant-rank.json'))
        cls.v4aeag = Path(os.environ.get('SPK_V4AEAG_REPORT',
                        str(ROOT/'docs/spk-bv-v4aeag-two-view-observation.json')))
        cls.raw3, cls.raw4 = cls.v3.read_bytes(), cls.v4aeag.read_bytes()
        cls.baseline = Path(cls.tmp.name)/'baseline.sqlite'
        old = old_evaluate(json.loads(cls.raw3), cls.raw3,
                           json.loads(cls.raw4), cls.raw4,
                           db_path=cls.baseline)
        cls.report_raw = canon(old)
        assert sha256(cls.report_raw).hexdigest() == REQUIRED_REPORT_SHA

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        temp = TemporaryDirectory(prefix='spk-anchor-case-')
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.db = self.dir/'escrow.sqlite'
        shutil.copy2(self.baseline, self.db)
        self.signed = self.dir/'signed-v4ahaj.json'
        self.signed.write_bytes(self.report_raw)
        self.raw = canon(seal_reported_database(self.report_raw,
                                                self.db, TEST_ANCHOR_KEY))
        self.expected_sha = sha256(self.raw).hexdigest()

    def state(self):
        with DurableEscrow.open(self.db, PARENT, TEST_VIEW_KEYS) as store:
            return store.verify()

    def check(self, raw=None, *, anchor_sha=None, key=TEST_ANCHOR_KEY, db=None):
        return check_anchored_database(db or self.db, PARENT,
            self.raw if raw is None else raw, key,
            expected_anchor_sha256=anchor_sha)

    def test_pinned_signed_predecessor_and_reference_bytes(self):
        self.assertEqual(sha256(self.report_raw).hexdigest(), REPORT_SHA)
        self.assertEqual(self.raw,
            (ROOT/'docs/spk-bv-v4akam-anchor-fixture.json').read_bytes())

    def test_baseline_72_entries_144_nonces_signed_and_anchored(self):
        state = self.check(anchor_sha=self.expected_sha)
        self.assertEqual((state['entries'],state['persisted_unique_nonces']),
                         (72,144))

    def test_anchor_serial_genesis_and_domain_are_typed(self):
        body = verify_capsule(self.raw, TEST_ANCHOR_KEY)
        self.assertEqual((body['serial'],body['schema'],body['previous_anchor_sha256']),
                         (1,SCHEMA,GENESIS))

    def test_external_anchor_wrong_digest_fails_even_when_valid(self):
        with self.assertRaises(AnchorRejected):
            self.check(anchor_sha='f'*64)

    def test_wrong_issuer_key_fails(self):
        with self.assertRaises(AnchorRejected):
            self.check(key=TEST_ANCHOR_KEY_OTHER)

    def test_wrong_parent_fails(self):
        with self.assertRaises(AnchorRejected):
            check_anchored_database(self.db,'c'*64,self.raw,TEST_ANCHOR_KEY)

    def test_tampered_mac_fails(self):
        body = json.loads(self.raw)
        body['mac_sha256'] = '0'*64
        with self.assertRaises(AnchorRejected):
            self.check(canon(body))

    def test_noncanonical_anchor_fails(self):
        with self.assertRaises(AnchorRejected):
            self.check(json.dumps(json.loads(self.raw),indent=2).encode())

    def test_anchor_body_edit_fails(self):
        body = json.loads(self.raw)
        body['body']['serial'] = 9
        with self.assertRaises(AnchorRejected):
            self.check(canon(body))

    def test_invalid_schema_fails(self):
        body = json.loads(self.raw)
        body['body']['schema'] = 'rewritten'
        with self.assertRaises(AnchorRejected):
            self.check(canon(body))

    def test_unknown_issuer_fails_even_with_public_key_resign(self):
        body = json.loads(self.raw)['body']
        with self.assertRaises(AnchorRejected):
            seal_state(body['sqlite_witness'], REPORT_SHA,TEST_ANCHOR_KEY,
                       issuer='FORGED_ROLE')

    def test_boolean_sequence_rejected(self):
        with self.assertRaises(AnchorRejected):
            seal_state(self.state(), REPORT_SHA,TEST_ANCHOR_KEY,serial=True)

    def test_stale_or_invalid_prior_lineage_rejected(self):
        with self.assertRaises(AnchorRejected):
            seal_state(self.state(),REPORT_SHA,TEST_ANCHOR_KEY,
                       prior_anchor_sha256='not-sha')

    def test_invalid_key_type_and_length_rejected(self):
        for key in ('public-key',b'short'):
            with self.subTest(key=key), self.assertRaises(AnchorRejected):
                seal_state(self.state(),REPORT_SHA,key)

    def test_public_fixture_key_can_sign_other_valid_head(self):
        # An independent digest/pin, not the public lab HMAC, is decisive.
        from spk_bv_research.task_anchor_fixture_v4akam import _state
        self.assertEqual(self.check(),self.state())
        alt = canon(seal_state(self.state(),REPORT_SHA,TEST_ANCHOR_KEY,serial=2))
        self.assertEqual(self.check(alt),self.state())
        with self.assertRaises(AnchorRejected):
            self.check(alt,anchor_sha=self.expected_sha)

    def test_fork_counterexample_two_locally_valid_states(self):
        proof = fork_and_rollback_counterexample()
        self.assertEqual(proof['locally_valid_distinct_forks'],2)
        self.assertTrue(proof['alternate_branch_rejected_by_retained_head'])
        self.assertFalse(proof['ordinary_local_integrity_can_detect_this_fork'])

    def test_rollback_counterexample_valid_old_db_rejected(self):
        proof = fork_and_rollback_counterexample()
        self.assertTrue(proof['valid_prior_history_rejected_after_new_head_published'])
        self.assertFalse(proof['real_external_issuer_identity'])

    def test_resigned_valid_fork_rejected_only_if_outside_digest_pinned(self):
        proof = fork_and_rollback_counterexample()
        self.assertTrue(proof['public_key_resigned_branch_rejected_by_retained_capsule_digest'])

    def test_one_legal_extension_is_rejected_until_new_head_custody(self):
        projections, completed, original_sha, issued = one_native_probe()
        msg, tick = round_message(projections,SOURCE,original_sha,PARENT,
                                  issued,completed,0)
        with DurableEscrow.open(self.db,PARENT,TEST_VIEW_KEYS) as store:
            result = store.append(msg, projections,expected_parent=PARENT,
                                  source_key=SOURCE,original_sha256=original_sha,
                                  completed_tick=completed,decision_tick=tick)
        self.assertTrue(result['journaled'])
        self.assertEqual(self.state()['entries'],73)
        with self.assertRaises(AnchorRejected):
            self.check()

    def test_sqlite_row_mutation_rejected_even_without_anchor(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE metadata SET value='f' || substr(value,2) WHERE name='head'")
        with self.assertRaises(AnchorRejected):
            self.check()

    def test_unauthorized_new_anchor_not_task_learning(self):
        _capsule, report = evaluate(self.report_raw,self.db)
        self.assertFalse(report['independent_task_ground_truth'])
        self.assertFalse(report['real_identity_provisioning'])
        self.assertEqual(report['program_adoptions'],0)
        self.assertFalse(report['native_learning_implemented'])

    def test_reference_report_byte_exact(self):
        _capsule, report = evaluate(self.report_raw,self.db)
        self.assertEqual(canon(report),
            (ROOT/'docs/spk-bv-v4akam-external-anchor-observation.json').read_bytes())

    def test_cli_create_only_report_and_anchor_reference_exact(self):
        a, r = self.dir/'anchor.json',self.dir/'report.json'
        argv = ['--root',str(ROOT),'--v4ahaj',str(self.signed),
                '--db',str(self.db),'--anchor-out',str(a),'--out',str(r)]
        with redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv),0)
            self.assertEqual(main(argv),2)
        self.assertEqual(a.read_bytes(),self.raw)
        self.assertEqual(r.read_bytes(),
             (ROOT/'docs/spk-bv-v4akam-external-anchor-observation.json').read_bytes())
        self.assertEqual(a.stat().st_mode&0o777,0o600)

    def test_cli_pinned_code_drift_fails_closed(self):
        a,r=self.dir/'anchor.json',self.dir/'report.json'
        altered={**CODE_SHA,'spk_bv_research/task_anchor_v4akam.py':'0'*64}
        with patch.dict(CODE_SHA,altered),redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(self.signed),
                         '--db',str(self.db),'--anchor-out',str(a),'--out',str(r)])
        self.assertEqual(status,2)
        self.assertFalse(a.exists())
        self.assertFalse(r.exists())

    def test_cli_symlinked_predecessor_fails_closed(self):
        link=self.dir/'linked-report.json'
        link.symlink_to(self.signed)
        with redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(link),
                         '--db',str(self.db),'--anchor-out',str(self.dir/'a.json'),
                         '--out',str(self.dir/'r.json')])
        self.assertEqual(status,2)

    def test_cli_database_symlink_fails_closed(self):
        link=self.dir/'linked-db.sqlite'
        link.symlink_to(self.db)
        with redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(self.signed),
                         '--db',str(link),'--anchor-out',str(self.dir/'a.json'),
                         '--out',str(self.dir/'r.json')])
        self.assertEqual(status,2)

    def test_cli_rejects_repo_outputs(self):
        with redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(self.signed),
                         '--db',str(self.db),
                         '--anchor-out',str(ROOT/'docs/test-anchor-forbidden.json'),
                         '--out',str(self.dir/'r.json')])
        self.assertEqual(status,2)

    def test_cli_rejects_same_anchor_and_report_path(self):
        both=self.dir/'both.json'
        with redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(self.signed),
                         '--db',str(self.db),'--anchor-out',str(both),
                         '--out',str(both)])
        self.assertEqual(status,2)

    def test_predecessor_one_byte_mutation_rejected_before_anchor(self):
        corrupted=deepcopy(json.loads(self.report_raw))
        corrupted['program_adoptions']=1
        self.signed.write_bytes(canon(corrupted))
        a,r=self.dir/'a.json',self.dir/'r.json'
        with redirect_stderr(io.StringIO()):
            status=main(['--root',str(ROOT),'--v4ahaj',str(self.signed),
                         '--db',str(self.db),'--anchor-out',str(a),
                         '--out',str(r)])
        self.assertEqual(status,2)
        self.assertFalse(a.exists())
        self.assertFalse(r.exists())


if __name__ == '__main__':
    unittest.main()
