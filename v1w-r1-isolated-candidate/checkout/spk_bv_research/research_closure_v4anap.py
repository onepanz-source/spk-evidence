"""Bounded BV research closure audit. No new neuron authority or learning.

This is a release *evidence* check, not an issuer, external oracle, or runtime
component. In particular, the reference key and retained digest are public.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_anchor_fixture_v4akam import (
    TEST_ANCHOR_KEY, fork_and_rollback_counterexample,
)
from spk_bv_research.task_anchor_v4akam import (
    REQUIRED_REPORT_SHA, check_anchored_database, verify_capsule,
)

SCHEMA = 'spk-bv-research-closure-v4an-v4ap/v1'
STATUS = 'BOUNDED_RESEARCH_PROTOCOL_CLOSED_EXTERNAL_VALIDATION_PENDING'
REPORT_SHA = '36dc505c9758e83173246f1f106389a121332119603431cf661d210f7758c1af'
CAPSULE_SHA = '1654e88d8c7dd8d88aac656f58ce0838e10f25d4f1b4b956a1af876a3ad593a0'
PREDECESSOR_SHA = '01211a6cdc2f8efc707514c56934b7c980f001bd22d4ed3df586ace2db5ff152'
NATIVE_SHA = '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
RELEASE_MANIFEST = 'docs/spk-bv-v4akam-release-manifest.json'


class ClosureRejected(ValueError):
    pass


def _require(condition, why):
    if not condition:
        raise ClosureRejected(why)


def _parse_exact(raw: bytes, label: str, expected_sha: str):
    _require(type(raw) is bytes and sha256(raw).hexdigest() == expected_sha,
             label + ': byte SHA-256 differs from retained reference')
    try:
        result = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ClosureRejected(label + ': malformed JSON') from exc
    _require(type(result) is dict and canon(result) == raw,
             label + ': noncanonical JSON')
    return result


def validate_repository_pins(root: Path):
    """Check every source and fixture pinned by the prior release manifest."""
    root = root.resolve(strict=True)
    raw_manifest = (root / RELEASE_MANIFEST).read_bytes()
    manifest = json.loads(raw_manifest)
    _require(manifest.get('schema') == 'spk-bv-v4akam-research-milestone-manifest/v1',
             'unexpected release manifest')
    pins = dict(manifest['pinned_existing_code_sha256'])
    pins.update(manifest['new_file_sha256'])
    _require(len(pins) == 15, 'missing/extra required previous milestone pins')
    _require(pins['spk_backvalidation_v0/live_dual_scheduler_v0e.py'] == NATIVE_SHA,
             'frozen native pin changed')
    _require(pins['docs/spk-bv-v4akam-external-anchor-observation.json'] == REPORT_SHA,
             'reference report pin changed')
    _require(pins['docs/spk-bv-v4akam-anchor-fixture.json'] == CAPSULE_SHA,
             'reference capsule pin changed')
    for name, expected in sorted(pins.items()):
        path = root / name
        _require(not path.is_symlink() and path.is_file() and
                 path.resolve(strict=True) == path and
                 sha256(path.read_bytes()).hexdigest() == expected,
                 'pinned release source/fixture changed: ' + name)
    tests = manifest['tests']
    _require(tests['total_passed'] == 199 and
             sum(n for name, n in tests.items() if name != 'total_passed') == 199,
             'prior release test-count contract inconsistent')
    witness = manifest['experimental_witness']
    _require(witness['reference_external_capsule_sha256'] == CAPSULE_SHA and
             witness['real_trust_root_provisioned'] is False and
             witness['independent_task_ground_truth'] is False and
             witness['native_program_adoptions'] == 0 and
             witness['native_learning_updates'] == 0,
             'previous research limitations incorrectly promoted')
    return {'manifest_sha256': sha256(raw_manifest).hexdigest(),
            'verified_predecessor_source_and_fixture_pins': len(pins),
            'inherited_tests_required_by_cumulative_gate': tests['total_passed']}


def audit(root: Path, raw_v4aeag: bytes, raw_v4ahaj: bytes,
          db_path: Path, raw_capsule: bytes, raw_v4akam: bytes):
    pins = validate_repository_pins(root)
    _parse_exact(raw_v4aeag, 'v4aeag predecessor', PREDECESSOR_SHA)
    parent = _parse_exact(raw_v4ahaj, 'v4ahaj predecessor', REQUIRED_REPORT_SHA)
    last = _parse_exact(raw_v4akam, 'v4akam observation', REPORT_SHA)
    capsule = _parse_exact(raw_capsule, 'v4akam capsule', CAPSULE_SHA)
    parent_head = parent.get('sqlite_logical_witness')
    _require(type(parent_head) is dict and parent_head.get('parent_sha256') == PREDECESSOR_SHA,
             'escrow parent is not the pinned two-view predecessor')
    _require(parent.get('signed_v4aeag_sha256') == PREDECESSOR_SHA,
             'signed v4aeag lineage changed')
    _require(last.get('signed_v4ahaj_sha256') == REQUIRED_REPORT_SHA and
             last.get('separately_custodialized_capsule_sha256') == CAPSULE_SHA,
             'signed escrow/anchor lineage changed')
    body = verify_capsule(raw_capsule, TEST_ANCHOR_KEY,
                          expected_anchor_sha256=CAPSULE_SHA)
    _require(body == capsule['body'] and
             body['source_report_sha256'] == REQUIRED_REPORT_SHA and
             body['signer_kind'] == 'PUBLIC_RESEARCH_FIXTURE_NO_REAL_IDENTITY',
             'anchor fixture or signing role misrepresented')
    state = check_anchored_database(db_path, PREDECESSOR_SHA,
                                    raw_capsule, TEST_ANCHOR_KEY,
                                    expected_anchor_sha256=CAPSULE_SHA)
    _require(state == parent_head == body['sqlite_witness'] == last['sqlite_witness'],
             'retained head, report, and reopened SQLite not identical')
    _require(state['entries'] == 72 and state['persisted_unique_nonces'] == 144,
             'escrow cardinality changed')
    forks = fork_and_rollback_counterexample()
    for field in ('alternate_branch_rejected_by_retained_head',
                  'public_key_resigned_branch_rejected_by_retained_capsule_digest',
                  'valid_prior_history_rejected_after_new_head_published',
                  'different_valid_hash_heads'):
        _require(forks.get(field) is True and
                 last['fork_and_rollback_counterexample'].get(field) is True,
                 'fork/rollback negative witness absent: ' + field)
    _require(forks['locally_valid_distinct_forks'] == 2 and
             last['fork_and_rollback_counterexample'] == forks,
             'valid divergent branch experiment changed')
    for flag in ('native_v0e_modified', 'architecture_v1_modified',
                 'native_learning_implemented', 'independent_task_ground_truth',
                 'real_identity_provisioning', 'real_external_anchor_service'):
        _require(last.get(flag) is False,
                 'research-only claim promoted without new evidence: ' + flag)
    _require(last.get('program_adoptions') == 0 and
             last.get('prior_pinned_counterfactual_native_probes') == 72 and
             last.get('prior_pinned_native_source_replays') == 18 and
             last.get('prior_persistent_review_attempts') == 198,
             'native replay/adoption research boundary changed')

    return {
        'schema': SCHEMA, 'status': STATUS,
        'scope': 'FROZEN_NATIVE_RESEARCH_ONLY_CAUSAL_BV_AND_ADVERSARIAL_EVIDENCE',
        'evidence_provenance': {
            **pins,
            'frozen_native_v0e_sha256': NATIVE_SHA,
            'v4aeag_sha256': PREDECESSOR_SHA,
            'v4ahaj_sha256': REQUIRED_REPORT_SHA,
            'v4akam_capsule_sha256': CAPSULE_SHA,
            'v4akam_report_sha256': REPORT_SHA,
            'escrow_head_sha256': state['head'],
        },
        'research_acceptance': {
            'pinned_frozen_native_and_release_sources': True,
            'causal_native_forward_and_feedback_reexecuted_predecessor': True,
            'bounded_actor_ACK_credit_priority_fairness_tested_predecessor': True,
            'escrow_72_signed_records_144_nonces_verified': True,
            'local_valid_fork_detected_by_retained_digest': True,
            'valid_rollback_detected_by_retained_digest': True,
            'deterministic_research_observation_reproduced': True,
            'zero_native_program_adoptions': True,
        },
        'evidence_counts': {
            'inherited_tests': 199,
            'prior_native_baseline_replays': 18,
            'prior_derived_counterfactual_replays': 72,
            'prior_escrow_review_attempts': 198,
            'persisted_entries': 72,
            'unique_persisted_nonces': 144,
            'valid_distinct_local_forks': 2,
            'native_program_adoptions': 0,
        },
        'unmet_independent_validation': {
            'externally_owned_monotonic_anchor_service': False,
            'separately_provisioned_signing_identities': False,
            'independent_task_holdout_and_ground_truth': False,
            'noncorrelated_observer_evidence': False,
            'production_learning_or_policy_adoption': False,
        },
        'claim_policy': {
            'research_protocol_reproducible': True,
            'back_validation_effective_on_external_tasks': False,
            'real_external_trust_attested': False,
            'native_self_learning_implemented': False,
            'hardware_or_mesh_performance_demonstrated': False,
        },
        'deferred_architecture': [
            'separate aggregation Sigma and activation sigma',
            'source identity-dependent semantic weights',
            'transport quality, jitter, delay, noise, loss and mesh topology',
            'real external identity, custody and learner adoption policy',
        ],
        'handoff': 'NEW_VALIDATION_PHASE_REQUIRES_EXTERNAL_OWNER_AND_TASK_TRUTH',
    }
