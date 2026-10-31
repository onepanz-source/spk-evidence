"""Adversarial closure policy tests; none confers production learning authority."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.research_closure_v4anap import (
    CAPSULE_SHA, ClosureRejected, NATIVE_SHA, PREDECESSOR_SHA, REPORT_SHA,
    STATUS, _parse_exact, audit, validate_repository_pins,
)
from spk_bv_research.task_anchor_fixture_v4akam import TEST_ANCHOR_KEY
from spk_bv_research.task_anchor_v4akam import (
    AnchorRejected, check_anchored_database,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAMES = ('SPK_V4AEAG_REPORT', 'SPK_V4AHAJ_REPORT', 'SPK_V4AHAJ_DB',
                'SPK_V4AKAM_ANCHOR', 'SPK_V4AKAM_REPORT')


def sources():
    paths = [os.environ.get(key) for key in SOURCE_NAMES]
    if not all(paths):
        raise RuntimeError('closure test must run through its source-pinned gate')
    return [Path(name) for name in paths]


class TestV4anapClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = sources()
        cls.raw = [p.read_bytes() for p in cls.src]

    def _audit(self, *replacements):
        inputs = list(self.raw)
        for index, value in replacements:
            inputs[index] = value
        return audit(ROOT, inputs[0], inputs[1], self.src[2], inputs[3], inputs[4])

    def _repository_copy(self, temporary):
        dst = Path(temporary)
        manifest = json.loads((ROOT / 'docs/spk-bv-v4akam-release-manifest.json').read_bytes())
        names = set(manifest['pinned_existing_code_sha256']) | set(manifest['new_file_sha256'])
        names.add('docs/spk-bv-v4akam-release-manifest.json')
        for name in names:
            p = dst / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, p)
        return dst, manifest

    def test_01_pinned_manifest_and_15_source_fixture_hashes(self):
        pins = validate_repository_pins(ROOT)
        self.assertEqual(pins['verified_predecessor_source_and_fixture_pins'], 15)
        self.assertEqual(pins['inherited_tests_required_by_cumulative_gate'], 199)

    def test_02_frozen_native_unmodified_pin(self):
        self.assertEqual(sha256((ROOT / 'spk_backvalidation_v0/live_dual_scheduler_v0e.py').read_bytes()).hexdigest(), NATIVE_SHA)

    def test_03_canonical_pinned_reports(self):
        for i, digest in ((0, PREDECESSOR_SHA), (4, REPORT_SHA)):
            obj = _parse_exact(self.raw[i], 'reference', digest)
            self.assertEqual(canon(obj), self.raw[i])

    def test_04_full_audit_returns_only_bounded_research(self):
        report = self._audit()
        self.assertEqual(report['status'], STATUS)
        self.assertTrue(all(report['research_acceptance'].values()))
        self.assertTrue(not any(report['unmet_independent_validation'].values()))
        self.assertEqual(report['evidence_counts']['native_program_adoptions'], 0)

    def test_05_positive_native_and_transport_still_does_not_certify_task(self):
        report = self._audit()
        self.assertTrue(report['research_acceptance']['causal_native_forward_and_feedback_reexecuted_predecessor'])
        self.assertFalse(report['claim_policy']['back_validation_effective_on_external_tasks'])
        self.assertFalse(report['claim_policy']['native_self_learning_implemented'])

    def test_06_escrow_head_pinned_to_report_capsule_and_file(self):
        report = self._audit()
        state = check_anchored_database(self.src[2], PREDECESSOR_SHA, self.raw[3],
                                        TEST_ANCHOR_KEY, expected_anchor_sha256=CAPSULE_SHA)
        self.assertEqual(report['evidence_provenance']['escrow_head_sha256'], state['head'])

    def test_07_predecessor_byte_flip_refused(self):
        with self.assertRaises(ClosureRejected):
            self._audit((1, self.raw[1] + b' '))

    def test_08_observation_byte_flip_refused(self):
        with self.assertRaises(ClosureRejected):
            self._audit((4, self.raw[4] + b' '))

    def test_09_capsule_byte_flip_refused(self):
        with self.assertRaises(ClosureRejected):
            self._audit((3, self.raw[3] + b' '))

    def test_10_two_view_predecessor_byte_flip_refused(self):
        with self.assertRaises(ClosureRejected):
            self._audit((0, self.raw[0] + b' '))

    def test_11_manipulated_trust_claim_without_retained_SHA_refused(self):
        forged = json.loads(self.raw[4])
        forged['real_external_anchor_service'] = True
        with self.assertRaises(ClosureRejected):
            self._audit((4, canon(forged)))

    def test_12_unpinned_modified_source_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = self._repository_copy(tmp)
            target = root / 'spk_bv_research/task_anchor_v4akam.py'
            target.write_bytes(target.read_bytes() + b'# silent source change\n')
            with self.assertRaisesRegex(ClosureRejected, 'pinned release source'):
                validate_repository_pins(root)

    def test_13_unpinned_false_manifest_trust_claim_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest = self._repository_copy(tmp)
            manifest['experimental_witness']['real_trust_root_provisioned'] = True
            (root / 'docs/spk-bv-v4akam-release-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ClosureRejected, 'limitations incorrectly promoted'):
                validate_repository_pins(root)

    def test_14_manifest_arithmetic_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest = self._repository_copy(tmp)
            manifest['tests']['total_passed'] = 200
            (root / 'docs/spk-bv-v4akam-release-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ClosureRejected, 'test-count'):
                validate_repository_pins(root)

    def test_15_sqlite_tampering_not_hidden_by_signed_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'tampered.sqlite'
            shutil.copy2(self.src[2], db)
            self.assertEqual(check_anchored_database(db, PREDECESSOR_SHA,
                self.raw[3], TEST_ANCHOR_KEY,
                expected_anchor_sha256=CAPSULE_SHA)['entries'], 72)
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE journal SET entry_hash=? WHERE seq=(SELECT min(seq) FROM journal)", ('0'*64,))
            with self.assertRaises((AnchorRejected, sqlite3.DatabaseError, ValueError)):
                check_anchored_database(db, PREDECESSOR_SHA, self.raw[3],
                                        TEST_ANCHOR_KEY, expected_anchor_sha256=CAPSULE_SHA)

    def test_16_create_only_cli_and_exact_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'closure.json'
            cmd = [sys.executable, '-m', 'search.spk_bv_v4anap_research_closure',
                   '--root', str(ROOT), '--v4aeag', str(self.src[0]),
                   '--v4ahaj', str(self.src[1]), '--db', str(self.src[2]),
                   '--anchor', str(self.src[3]), '--v4akam', str(self.src[4]),
                   '--out', str(out)]
            result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_bytes())['status'], STATUS)
            refused = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(refused.returncode, 2)
            self.assertIn('existing output', refused.stderr)

    def test_17_cli_rejects_in_repo_output(self):
        cmd = [sys.executable, '-m', 'search.spk_bv_v4anap_research_closure',
               '--root', str(ROOT), '--v4aeag', str(self.src[0]),
               '--v4ahaj', str(self.src[1]), '--db', str(self.src[2]),
               '--anchor', str(self.src[3]), '--v4akam', str(self.src[4]),
               '--out', str(ROOT / 'docs/forbidden-closure.json')]
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unsafe', result.stderr)

    def test_18_cli_rejects_symlinked_signed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / 'untrusted.json'
            link.symlink_to(self.src[4])
            cmd = [sys.executable, '-m', 'search.spk_bv_v4anap_research_closure',
                   '--root', str(ROOT), '--v4aeag', str(self.src[0]),
                   '--v4ahaj', str(self.src[1]), '--db', str(self.src[2]),
                   '--anchor', str(self.src[3]), '--v4akam', str(link),
                   '--out', str(Path(tmp) / 'closure.json')]
            result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('unsafe source', result.stderr)

    def test_19_no_weights_topology_or_production_claim_sneaks_in(self):
        report = self._audit()
        self.assertFalse(report['claim_policy']['hardware_or_mesh_performance_demonstrated'])
        self.assertIn('source identity-dependent semantic weights', report['deferred_architecture'])
        self.assertNotIn('production', report['scope'].lower())


if __name__ == '__main__':
    unittest.main()
