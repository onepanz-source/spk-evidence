"""Public, deterministic and deliberately correlated two-view research fixtures."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from spk_bv_research.native_actor_objective_v4yzaa import _probe_case, _set_cmp
from spk_bv_research.task_disagreement_v4aeag import (
    ORIGINS, SCHEMA, SCOPE, VIEWS, EscrowLedger, adjudicate,
    digest, expected_vote, lab_mac,
)

TEST_VIEW_KEYS = {
    view: sha256(('PUBLIC-SPK-V4AEAG-LAB-ONLY-' + view).encode()).digest()
    for view in VIEWS
}
VARIANTS = (
    'two_view_consistency', 'missing_view', 'reviewer_disagreement',
    'reviewer_abstains', 'unanimous_wrong_vote', 'co_signed_poisoned_task',
    'forged_shared_origin', 'shared_nonce', 'wrong_source', 'wrong_scope',
    'tampered_review', 'tampered_projection', 'causal_inversion',
    'replayed_view', 'single_shared_lab_key',
)
VERDICTS = {
    'two_view_consistency': 'CONSISTENT_CORRELATED_TEST_VIEWS_NO_EXTERNAL_TRUST',
    'missing_view': 'VETO_INCOMPLETE_TWO_VIEW',
    'reviewer_disagreement': 'QUARANTINE_REVIEWER_DISAGREEMENT',
    'reviewer_abstains': 'QUARANTINE_ABSTENTION',
    'unanimous_wrong_vote': 'VETO_CONSENSUS_CONTRADICTS_OBSERVATION',
    'co_signed_poisoned_task': 'VETO_TASK_CANARY_CONFLICT',
    'forged_shared_origin': 'VETO_SHARED_OR_WRONG_EVIDENCE_ORIGIN',
    'shared_nonce': 'VETO_SHARED_NONCE',
    'wrong_source': 'VETO_SOURCE_BINDING',
    'wrong_scope': 'VETO_SCOPE',
    'tampered_review': 'VETO_INVALID_ATTESTATION',
    'tampered_projection': 'VETO_NATIVE_PROJECTION_MISMATCH',
    'causal_inversion': 'VETO_CAUSAL_ORDER',
    'replayed_view': 'VETO_REPLAY',
    'single_shared_lab_key': 'VETO_NO_SEPARATE_LAB_KEYS',
}


def project_actual_native(case, fabric, plans, bv, *, native_executor):
    """Reexecute the candidate and base on both inputs on frozen v0e.

    Endpoint and emission records are two independent extractors of a single
    native simulation, NOT operationally independent observers.
    """
    base = _set_cmp(case, 1, 0)
    candidate = _set_cmp(case, 1, 1)
    result = {view: [] for view in VIEWS}
    last_tick = case.events[0].timestamp
    for stage, specimen in (('base', base), ('candidate', candidate)):
        for channel in (0, 1):
            native = native_executor(_probe_case(specimen, channel), fabric,
                                     *plans, bv)
            forward = native['forward']
            terminal = forward['terminal']
            emissions = [r for r in forward['emissions']
                         if r['node_id'] == 'C' and r['channel'] == 7]
            if (len(terminal) > 1 or len(emissions) > 1 or
                    any(r['node_id'] != 'C' or r['channel'] != 7
                        for r in terminal) or len(terminal) != len(emissions)):
                raise ValueError('two view native terminal/emission projection drift')
            for entry in forward['emissions'] + terminal:
                last_tick = max(last_tick, entry['timestamp'])
            for entry in native['resources']['timeline']:
                last_tick = max(last_tick, entry['tick'])
            for view, rows in (('endpoint', terminal), ('emission', emissions)):
                result[view].append({
                    'stage': stage, 'channel': channel,
                    'count': len(rows), 'evidence_sha256': digest(rows),
                })
    if (expected_vote(result['endpoint'], {'0': 1, '1': 0}) !=
            ('IMPROVES', 4, 0) or
            expected_vote(result['emission'], {'0': 1, '1': 0}) !=
            ('IMPROVES', 4, 0)):
        raise ValueError('previously pinned synthetic task improvement drift')
    return result, last_tick


def envelope(projections, source_key, original_sha, parent, issued, last_tick,
             *, task_labels=None):
    if task_labels is None:
        task_labels = {'0': 1, '1': 0}
    observed = last_tick + 1
    reviews = {}
    for view in VIEWS:
        reviews[view] = {
            'view': view, 'origin': ORIGINS[view],
            'projection_sha256': digest(projections[view]),
            'vote': 'IMPROVES', 'observed_tick': observed,
            'review_tick': observed + 1,
            'nonce': digest(['v4aeag', parent, source_key, view, issued]),
            'mac': '',
        }
    message = {
        'schema': SCHEMA, 'scope': SCOPE, 'parent_sha256': parent,
        'source_key': source_key, 'original_native_sha256': original_sha,
        'task_labels': task_labels, 'issued_tick': issued,
        'expires_tick': observed + 6, 'reviews': reviews,
    }
    reseal(message)
    return message


def reseal(message):
    for view in VIEWS:
        if view in message['reviews']:
            message['reviews'][view]['mac'] = lab_mac(
                TEST_VIEW_KEYS[view], message, message['reviews'][view])


def run_variant(projections, source_key, original_sha, parent, issued,
                last_tick, variant):
    if variant not in VARIANTS:
        raise ValueError('unsupported two view research variant')
    ledger = EscrowLedger()
    effective_projections = deepcopy(projections)
    message = envelope(projections, source_key, original_sha, parent,
                       issued, last_tick)
    keys = TEST_VIEW_KEYS
    decision_tick = last_tick + 3
    expected_source = source_key
    if variant == 'missing_view':
        message['reviews'].pop('emission')
    elif variant == 'reviewer_disagreement':
        message['reviews']['emission']['vote'] = 'REGRESSES'
        reseal(message)
    elif variant == 'reviewer_abstains':
        message['reviews']['emission']['vote'] = 'ABSTAIN'
        reseal(message)
    elif variant == 'unanimous_wrong_vote':
        for view in VIEWS:
            message['reviews'][view]['vote'] = 'REGRESSES'
        reseal(message)
    elif variant == 'co_signed_poisoned_task':
        message['task_labels'] = {'0': 0, '1': 1}
        reseal(message)
    elif variant == 'forged_shared_origin':
        message['reviews']['emission']['origin'] = ORIGINS['endpoint']
        reseal(message)
    elif variant == 'shared_nonce':
        message['reviews']['emission']['nonce'] = message['reviews']['endpoint']['nonce']
        reseal(message)
    elif variant == 'wrong_source':
        message['source_key'] = 'forged/source/1'
        reseal(message)
    elif variant == 'wrong_scope':
        message['scope'] = 'another/task'
        reseal(message)
    elif variant == 'tampered_review':
        message['reviews']['emission']['vote'] = 'REGRESSES'
    elif variant == 'tampered_projection':
        effective_projections['emission'][0]['count'] = 1 - effective_projections['emission'][0]['count']
    elif variant == 'causal_inversion':
        message['reviews']['emission']['review_tick'] = issued
        reseal(message)
    elif variant == 'replayed_view':
        initial = adjudicate(message, projections, keys,
                             expected_parent=parent, source_key=expected_source,
                             original_sha256=original_sha,
                             precommitted_labels={'0': 1, '1': 0},
                             completed_tick=last_tick,
                             decision_tick=decision_tick, ledger=ledger)
        if initial['verdict'] != VERDICTS['two_view_consistency']:
            raise ValueError('replay setup could not establish positive control')
    elif variant == 'single_shared_lab_key':
        keys = {view: TEST_VIEW_KEYS['endpoint'] for view in VIEWS}
    before = len(ledger.seen)
    decision = adjudicate(
        message, effective_projections, keys, expected_parent=parent,
        source_key=expected_source, original_sha256=original_sha,
        precommitted_labels={'0': 1, '1': 0},
        completed_tick=last_tick,
        decision_tick=decision_tick, ledger=ledger)
    if decision['verdict'] != VERDICTS[variant]:
        raise ValueError('two view variant unexpected adjudication: ' + variant +
                         ' got ' + decision['verdict'])
    return {
        'variant': variant, 'source_key': source_key,
        'projection_sha256': {v: digest(projections[v]) for v in VIEWS},
        'envelope_sha256': digest(message),
        'ledger_nonces_before': before, 'ledger_nonces_after': len(ledger.seen),
        'decision': decision,
    }
