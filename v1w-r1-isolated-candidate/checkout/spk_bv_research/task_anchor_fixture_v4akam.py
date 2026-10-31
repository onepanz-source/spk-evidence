"""Convergent local history, divergent valid fork, and rollback counterexamples."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from search.spk_bv_v0e_live_evidence import fixture
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVPlanV0e, execute_live_v0e,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    TEST_VIEW_KEYS, project_actual_native,
)
from spk_bv_research.task_escrow_fixture_v4ahaj import round_message
from spk_bv_research.task_escrow_store_v4ahaj import DurableEscrow
from spk_bv_research.task_anchor_v4akam import (
    AnchorRejected, check_anchored_database, seal_state,
)

# Deliberately public test-only HMAC material: NEVER an identity credential.
TEST_ANCHOR_KEY = bytes.fromhex('25f3' * 16)
TEST_ANCHOR_KEY_OTHER = bytes.fromhex('d17a' * 16)
PARENT = '01211a6cdc2f8efc707514c56934b7c980f001bd22d4ed3df586ace2db5ff152'
REPORT_SHA = '8fd397a7b3b1cf693f1c5e3be3e78021f504609a0b2695b2bbe67e07d65f8674'
SOURCE = 'lab/offline-fork/no-production-scheduler'


def one_native_probe():
    case, fabric, plans = fixture(ticks=(1, 2))
    bv = LiveBVPlanV0e(enabled=False, priority='forward-first')
    original = execute_live_v0e(case, fabric, *plans, bv)
    projections, completed = project_actual_native(
        case, fabric, plans, bv, native_executor=execute_live_v0e)
    return projections, completed, snapshot(original), case.events[0].timestamp


def _add(db, projections, completed, original_sha, issued, round_no):
    message, tick = round_message(projections, SOURCE, original_sha,
                                 PARENT, issued, completed, round_no)
    with DurableEscrow.open(db, PARENT, TEST_VIEW_KEYS) as store:
        result = store.append(message, projections,
                              expected_parent=PARENT, source_key=SOURCE,
                              original_sha256=original_sha,
                              completed_tick=completed, decision_tick=tick)
    if not result['journaled']:
        raise ValueError('fork setup did not commit valid review')


def _state(db):
    with DurableEscrow.open(db, PARENT, TEST_VIEW_KEYS) as store:
        return store.verify()


def _veto(f, reason):
    try:
        f()
    except AnchorRejected:
        return True
    raise AssertionError('outside-head guard failed to reject ' + reason)


def fork_and_rollback_counterexample():
    """Both forks pass local SQLite integrity; only external custody separates.

    Runs on separately opened local DB files with distinct valid signed
    research reviews. This is a capability/counterexample, not a security
    claim against any adversary who can rewrite the witness too.
    """
    projections, completed, original_sha, issued = one_native_probe()
    with TemporaryDirectory(prefix='spk-bv-anchor-fork-') as dirname:
        a = Path(dirname) / 'valid-a.sqlite'
        b = Path(dirname) / 'valid-b.sqlite'
        rollback = Path(dirname) / 'valid-previous.sqlite'
        with DurableEscrow.create(a, PARENT, TEST_VIEW_KEYS):
            pass
        with DurableEscrow.create(b, PARENT, TEST_VIEW_KEYS):
            pass
        _add(a, projections, completed, original_sha, issued, 0)
        _add(b, projections, completed, original_sha, issued, 1)
        state_a, state_b = _state(a), _state(b)
        if state_a['head'] == state_b['head']:
            raise AssertionError('forks unexpectedly have identical head')
        capsule_a = canon(seal_state(state_a, REPORT_SHA, TEST_ANCHOR_KEY))
        capsule_b = canon(seal_state(state_b, REPORT_SHA, TEST_ANCHOR_KEY))
        external_sha = sha256(capsule_a).hexdigest()
        check_anchored_database(a, PARENT, capsule_a, TEST_ANCHOR_KEY,
                                expected_anchor_sha256=external_sha)
        check_anchored_database(b, PARENT, capsule_b, TEST_ANCHOR_KEY)
        veto_fork = _veto(lambda: check_anchored_database(
            b, PARENT, capsule_a, TEST_ANCHOR_KEY), 'valid alternate fork')
        veto_resigned_fork = _veto(lambda: check_anchored_database(
            b, PARENT, capsule_b, TEST_ANCHOR_KEY,
            expected_anchor_sha256=external_sha), 're-signed alternate fork')
        # Snapshot a valid prior chain, then extend and witness the new head.
        shutil.copy2(a, rollback)
        _add(a, projections, completed, original_sha, issued, 2)
        newer = _state(a)
        if _state(rollback) != state_a:
            raise AssertionError('self-contained rollback branch changed')
        newer_capsule = canon(seal_state(newer, REPORT_SHA, TEST_ANCHOR_KEY,
                                         serial=2,
                                         prior_anchor_sha256=external_sha))
        check_anchored_database(a, PARENT, newer_capsule, TEST_ANCHOR_KEY)
        veto_rollback = _veto(lambda: check_anchored_database(
            rollback, PARENT, newer_capsule, TEST_ANCHOR_KEY),
            'internally valid rollback')
        return {
            'same_parent_signed_native_fixture': True,
            'locally_valid_distinct_forks': 2,
            'different_valid_hash_heads': True,
            'valid_branch_passes_anchored_validation': True,
            'alternate_branch_rejected_by_retained_head': veto_fork,
            'public_key_resigned_branch_rejected_by_retained_capsule_digest':
                veto_resigned_fork,
            'valid_prior_history_rejected_after_new_head_published': veto_rollback,
            'ordinary_local_integrity_can_detect_this_fork': False,
            'real_external_issuer_identity': False,
            'native_program_adoptions': 0,
        }
