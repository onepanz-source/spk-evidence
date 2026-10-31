"""Deterministic real escrow head verification and valid-fork counterexample."""
from __future__ import annotations

from hashlib import sha256

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_anchor_fixture_v4akam import (
    TEST_ANCHOR_KEY, fork_and_rollback_counterexample,
)
from spk_bv_research.task_anchor_v4akam import (
    SCHEMA, STATUS, _read_pinned_report, seal_reported_database,
    check_anchored_database,
)


def evaluate(raw_v4ahaj, db_path, *, issuer_key=TEST_ANCHOR_KEY):
    predecessor = _read_pinned_report(raw_v4ahaj)
    capsule = seal_reported_database(raw_v4ahaj, db_path, issuer_key)
    raw_anchor = canon(capsule)
    digest_anchor = sha256(raw_anchor).hexdigest()
    state = check_anchored_database(
        db_path, predecessor['signed_v4aeag_sha256'], raw_anchor,
        issuer_key, expected_anchor_sha256=digest_anchor)
    if state != predecessor['sqlite_logical_witness']:
        raise ValueError('SQLite witness drifted since last checkpoint')
    forks = fork_and_rollback_counterexample()
    if (forks['locally_valid_distinct_forks'] != 2 or
            any(forks[name] is not True for name in (
                'alternate_branch_rejected_by_retained_head',
                'public_key_resigned_branch_rejected_by_retained_capsule_digest',
                'valid_prior_history_rejected_after_new_head_published'))):
        raise ValueError('external-head counterexample not reproduced')
    report = {
        'schema': SCHEMA, 'status': STATUS,
        'signed_v4ahaj_sha256': sha256(raw_v4ahaj).hexdigest(),
        'separately_custodialized_capsule_sha256': digest_anchor,
        'capsule_body': capsule['body'],
        'sqlite_witness': state,
        'fork_and_rollback_counterexample': forks,
        'prior_pinned_counterfactual_native_probes': 72,
        'prior_pinned_native_source_replays': 18,
        'prior_persistent_review_attempts': 198,
        'prior_committed_sqlite_entries': 72,
        'external_custody': 'SIMULATED_DIFFERENT_ARTIFACT_NOT_A_REMOTE_TRUST_ROOT',
        'proof_limit': 'PINNED_EXTERNAL_DIGEST_DETECTS_VALID_FORK_BUT_PUBLIC_KEY_CANNOT_PROVE_ISSUER_IDENTITY',
        'independent_task_ground_truth': False,
        'real_identity_provisioning': False,
        'real_external_anchor_service': False,
        'native_v0e_modified': False,
        'architecture_v1_modified': False,
        'program_adoptions': 0,
        'native_learning_implemented': False,
        'claims_excluded': [
            'no trusted remote keeper of the signed anchor was deployed',
            'public research HMAC key is intentionally forgeable by code readers',
            'same-host custody is not an independent security principal',
            'correlated reviewers and synthetic labels are not real task truth',
            'not Byzantine consensus, rollback-proof storage or a live learner',
        ],
        'next_gate': 'EXTERNALLY_OWNED_ANCHOR_AND_INDEPENDENT_TASK_HOLDOUT',
    }
    return capsule, report
