"""Deterministic SQLite research-only receipt/restart adversarial sequences."""
from __future__ import annotations

from copy import deepcopy

from spk_bv_research.task_disagreement_v4aeag import digest
from spk_bv_research.task_disagreement_fixture_v4aeag import (
    TEST_VIEW_KEYS, envelope, reseal,
)
from spk_bv_research.task_escrow_store_v4ahaj import (
    DurableEscrow, SimulatedCrash,
)

VARIANTS = (
    'consensus_saved', 'consensus_replay_after_reopen',
    'disagreement_saved', 'quarantined_replay_after_reopen',
    'abstention_saved', 'rollback_before_commit', 'same_receipt_recovered',
    'signed_stale_source_clock', 'tampered_review_not_saved',
    'wrong_parent_not_saved', 'co_signed_poison_not_saved',
)
EXPECT = {
    'consensus_saved': 'JOURNALED_CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
    'consensus_replay_after_reopen': 'VETO_PERSISTENT_REPLAY',
    'disagreement_saved': 'JOURNALED_QUARANTINE_REVIEWER_DISAGREEMENT',
    'quarantined_replay_after_reopen': 'VETO_PERSISTENT_REPLAY',
    'abstention_saved': 'JOURNALED_QUARANTINE_ABSTENTION',
    'rollback_before_commit': 'FAULT_INJECTED_ATOMIC_ROLLBACK',
    'same_receipt_recovered': 'JOURNALED_CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
    'signed_stale_source_clock': 'VETO_PERSISTENT_SOURCE_CLOCK',
    'tampered_review_not_saved': 'VETO_INVALID_ATTESTATION',
    'wrong_parent_not_saved': 'VETO_SOURCE_BINDING',
    'co_signed_poison_not_saved': 'VETO_TASK_CANARY_CONFLICT',
}


def round_message(projections, source_key, original_sha, parent,
                  issued, completed, round_no, *, nonce_suffix=''):
    """Later review rounds of one unchanged native probe, never more training."""
    message = envelope(projections, source_key, original_sha, parent,
                       issued, completed)
    shift = round_no * 10
    message['expires_tick'] += shift
    for view, review in message['reviews'].items():
        review['observed_tick'] += shift
        review['review_tick'] += shift
        review['nonce'] = digest(['V4AHAJ', parent, source_key, view,
                                  round_no, nonce_suffix])
    reseal(message)
    return message, completed + 3 + shift


def _post(path, projections, source_key, original_sha, parent,
          completed, decision_tick, message, *, fault=None):
    # A fresh connection per review is the deliberate restart/open witness.
    with DurableEscrow.open(path, parent, TEST_VIEW_KEYS) as store:
        return store.append(message, projections, expected_parent=parent,
                            source_key=source_key, original_sha256=original_sha,
                            completed_tick=completed,
                            decision_tick=decision_tick, fault=fault)


def run_sequence(path, projections, source_key, original_sha, parent,
                 issued, completed):
    result = []

    def record(variant, message, decision_tick, *, fault=None):
        if fault:
            with DurableEscrow.open(path, parent, TEST_VIEW_KEYS) as store:
                before = store.verify()
                try:
                    store.append(message, projections, expected_parent=parent,
                                 source_key=source_key,
                                 original_sha256=original_sha,
                                 completed_tick=completed,
                                 decision_tick=decision_tick, fault=fault)
                except SimulatedCrash:
                    after = store.verify()
                    if before != after:
                        raise ValueError('atomic rollback corrupted escrow custody')
                    verdict = 'FAULT_INJECTED_ATOMIC_ROLLBACK'
                else:
                    raise ValueError('injected atomic rollback unexpectedly committed')
            receipt = {'verdict': verdict, 'journaled': False}
        else:
            receipt = _post(path, projections, source_key, original_sha,
                            parent, completed, decision_tick, message)
        verdict = receipt['verdict']
        if verdict != EXPECT[variant]:
            raise ValueError('escrow fixture variant diverged: ' + variant +
                             ' got ' + verdict)
        result.append({'variant': variant, 'source_key': source_key,
                       'envelope_sha256': digest(message),
                       'decision_tick': decision_tick,
                       'verdict': verdict,
                       'journaled': receipt['journaled'],
                       'recorded_sequence': receipt.get('sequence'),
                       'head': receipt.get('head')})

    first, t0 = round_message(projections, source_key, original_sha,
                              parent, issued, completed, 0)
    record('consensus_saved', first, t0)
    record('consensus_replay_after_reopen', first, t0)

    disagree, t1 = round_message(projections, source_key, original_sha,
                                 parent, issued, completed, 1)
    disagree['reviews']['emission']['vote'] = 'REGRESSES'
    reseal(disagree)
    record('disagreement_saved', disagree, t1)
    record('quarantined_replay_after_reopen', disagree, t1)

    abstain, t2 = round_message(projections, source_key, original_sha,
                                parent, issued, completed, 2)
    abstain['reviews']['emission']['vote'] = 'ABSTAIN'
    reseal(abstain)
    record('abstention_saved', abstain, t2)

    recovered, t3 = round_message(projections, source_key, original_sha,
                                  parent, issued, completed, 3)
    record('rollback_before_commit', recovered, t3,
           fault='after_nonce_before_commit')
    record('same_receipt_recovered', recovered, t3)

    stale, ts = round_message(projections, source_key, original_sha,
                              parent, issued, completed, 2,
                              nonce_suffix='new_nonce_but_stale_clock')
    record('signed_stale_source_clock', stale, ts)

    tampered, tt = round_message(projections, source_key, original_sha,
                                 parent, issued, completed, 4)
    tampered['reviews']['endpoint']['vote'] = 'REGRESSES'
    record('tampered_review_not_saved', tampered, tt)

    wrong, tw = round_message(projections, source_key, original_sha,
                              parent, issued, completed, 5)
    wrong['parent_sha256'] = '0' * 64
    reseal(wrong)
    record('wrong_parent_not_saved', wrong, tw)

    poison, tp = round_message(projections, source_key, original_sha,
                               parent, issued, completed, 6)
    poison['task_labels'] = {'0': 0, '1': 1}
    reseal(poison)
    record('co_signed_poison_not_saved', poison, tp)
    return result
