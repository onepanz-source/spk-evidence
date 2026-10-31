"""v4ae-v4ag: two-view, test-only adjudication of a synthetic task trial.

The two views are projections of the SAME frozen simulator run, not two
independent sources of real-world truth. HMAC fixture keys are public. Even
unanimity cannot authorize a program update, and disagreement is quarantined.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import hmac

from spk_bv_research.native_allocation_boundary_v1r import canon

SCHEMA = 'spk-bv-two-view-task-adjudication/research-v4ae-v4ag'
STATUS = 'TWO_CORRELATED_NATIVE_VIEWS_DISAGREEMENT_ESCROW_NO_NATIVE_LEARNING'
DOMAIN = b'SPK/BV/TWO-VIEW/V4AEAG\x00'
SCOPE = 'A/channel_event_to_C/terminal_channel_7'
VIEWS = ('endpoint', 'emission')
ORIGINS = {'endpoint': 'native.forward.terminal',
           'emission': 'native.forward.emissions.filtered_C_7'}
VOTES = ('IMPROVES', 'REGRESSES', 'ABSTAIN')
FIELDS = frozenset({'schema', 'scope', 'parent_sha256', 'source_key',
                    'original_native_sha256', 'task_labels', 'issued_tick',
                    'expires_tick', 'reviews'})
REVIEW_FIELDS = frozenset({'view', 'origin', 'projection_sha256',
                           'vote', 'observed_tick', 'review_tick', 'nonce', 'mac'})


@dataclass
class EscrowLedger:
    """Bounded in-memory replay guard; NOT persistent anti-replay custody."""
    seen: set[str] = field(default_factory=set)


def digest(obj):
    return sha256(canon(obj)).hexdigest()


def _signed_review(envelope, review):
    # Only the review's own signature is excluded; all task metadata is bound.
    return {**{k: envelope[k] for k in FIELDS if k != 'reviews'},
            'review': {k: review[k] for k in REVIEW_FIELDS if k != 'mac'}}


def lab_mac(key, envelope, review):
    if type(key) is not bytes or len(key) < 32:
        raise ValueError('test-only view key must contain at least 32 bytes')
    return hmac.new(key, DOMAIN + canon(_signed_review(envelope, review)),
                    sha256).hexdigest()


def projected_counts(projection):
    """Small typed score, independent from the previous objective's scorer."""
    if (type(projection) is not list or len(projection) != 4 or
            any(type(r) is not dict or set(r) !=
                {'stage', 'channel', 'count', 'evidence_sha256'} for r in projection)):
        raise ValueError('invalid four-probe projected observation')
    expected_order = (('base', 0), ('base', 1),
                      ('candidate', 0), ('candidate', 1))
    for record, (stage, channel) in zip(projection, expected_order):
        if (record['stage'] != stage or type(record['channel']) is not int or
                record['channel'] != channel or type(record['count']) is not int or
                record['count'] not in (0, 1) or
                type(record['evidence_sha256']) is not str or
                len(record['evidence_sha256']) != 64):
            raise ValueError('invalid probe evidence or order')
    return [record['count'] for record in projection]


def expected_vote(projection, labels):
    counts = projected_counts(projection)
    if type(labels) is not dict or set(labels) != {'0', '1'} or any(
            type(v) is not int or v not in (0, 1) for v in labels.values()):
        raise ValueError('invalid task labels')
    base_cost = 0
    candidate_cost = 0
    for i, channel in enumerate((0, 1)):
        expected = labels[str(channel)]
        base_cost += 5 * max(expected - counts[i], 0) + 4 * max(counts[i] - expected, 0)
        candidate_cost += (5 * max(expected - counts[i + 2], 0) +
                           4 * max(counts[i + 2] - expected, 0))
    return ('IMPROVES' if candidate_cost < base_cost else 'REGRESSES',
            base_cost, candidate_cost)


def adjudicate(envelope, projections, keys, *, expected_parent,
               source_key, original_sha256, precommitted_labels,
               completed_tick, decision_tick, ledger):
    """Fail-closed two-view escrow. Never installs or adapts an algorithm."""
    def result(verdict, *, checked=False, agree=False):
        return {
            'schema': SCHEMA, 'status': STATUS, 'verdict': verdict,
            'two_view_provenance_checked': checked,
            'reviewer_agreement': agree,
            'promotion_authorized': False,
            'program_adopted': False,
            'native_learning_implemented': False,
            'production_reviewer_authenticated': False,
            'independent_real_world_truth_available': False,
            'durable_escrow_implemented': False,
        }

    if type(envelope) is not dict or set(envelope) != FIELDS:
        return result('VETO_MALFORMED_ENVELOPE')
    if (envelope['schema'] != SCHEMA or type(envelope['scope']) is not str or
            type(envelope['parent_sha256']) is not str or
            type(envelope['source_key']) is not str or
            type(envelope['original_native_sha256']) is not str or
            type(envelope['issued_tick']) is not int or
            type(envelope['expires_tick']) is not int or
            envelope['issued_tick'] < 0 or
            envelope['expires_tick'] <= envelope['issued_tick'] or
            type(envelope['reviews']) is not dict or
            type(ledger) is not EscrowLedger):
        return result('VETO_INVALID_CONTRACT')
    reviews = envelope['reviews']
    if set(reviews) != set(VIEWS):
        return result('VETO_INCOMPLETE_TWO_VIEW')
    if (type(keys) is not dict or set(keys) != set(VIEWS) or
            any(type(keys[view]) is not bytes or len(keys[view]) < 32
                for view in VIEWS) or keys['endpoint'] == keys['emission']):
        return result('VETO_NO_SEPARATE_LAB_KEYS')
    for view in VIEWS:
        review = reviews[view]
        if (type(review) is not dict or set(review) != REVIEW_FIELDS or
                review['view'] != view or type(review['origin']) is not str or
                type(review['projection_sha256']) is not str or
                len(review['projection_sha256']) != 64 or
                type(review['vote']) is not str or review['vote'] not in VOTES or
                type(review['observed_tick']) is not int or
                type(review['review_tick']) is not int or
                type(review['nonce']) is not str or not review['nonce'] or
                type(review['mac']) is not str or len(review['mac']) != 64):
            return result('VETO_INVALID_REVIEW')
        if not hmac.compare_digest(review['mac'], lab_mac(keys[view], envelope, review)):
            return result('VETO_INVALID_ATTESTATION')
    if (envelope['parent_sha256'] != expected_parent or
            envelope['source_key'] != source_key or
            envelope['original_native_sha256'] != original_sha256):
        return result('VETO_SOURCE_BINDING')
    if envelope['scope'] != SCOPE:
        return result('VETO_SCOPE')
    if (type(decision_tick) is not int or type(completed_tick) is not int or
            completed_tick < envelope['issued_tick'] or
            decision_tick < envelope['issued_tick'] or
            decision_tick > envelope['expires_tick']):
        return result('VETO_DECISION_TIME')
    if (type(projections) is not dict or set(projections) != set(VIEWS)):
        return result('VETO_MISSING_NATIVE_PROJECTION')
    try:
        observed_votes = {v: expected_vote(projections[v], envelope['task_labels'])
                          for v in VIEWS}
    except (TypeError, ValueError, KeyError):
        return result('VETO_INVALID_PROJECTION')
    for view in VIEWS:
        review = reviews[view]
        if review['origin'] != ORIGINS[view]:
            return result('VETO_SHARED_OR_WRONG_EVIDENCE_ORIGIN')
        if digest(projections[view]) != review['projection_sha256']:
            return result('VETO_NATIVE_PROJECTION_MISMATCH')
        if not (completed_tick < review['observed_tick'] <
                review['review_tick'] < decision_tick):
            return result('VETO_CAUSAL_ORDER')
        if review['nonce'] in ledger.seen:
            return result('VETO_REPLAY')
    if reviews['endpoint']['nonce'] == reviews['emission']['nonce']:
        return result('VETO_SHARED_NONCE')
    if envelope['task_labels'] != precommitted_labels or precommitted_labels != {'0': 1, '1': 0}:
        return result('VETO_TASK_CANARY_CONFLICT', checked=True)
    votes = [reviews[v]['vote'] for v in VIEWS]
    if 'ABSTAIN' in votes:
        return result('QUARANTINE_ABSTENTION', checked=True)
    if votes[0] != votes[1]:
        return result('QUARANTINE_REVIEWER_DISAGREEMENT', checked=True)
    if (observed_votes['endpoint'] != observed_votes['emission'] or
            votes[0] != observed_votes['endpoint'][0]):
        return result('VETO_CONSENSUS_CONTRADICTS_OBSERVATION',
                      checked=True, agree=True)
    for view in VIEWS:
        ledger.seen.add(reviews[view]['nonce'])
    return result('CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
                  checked=True, agree=True)
