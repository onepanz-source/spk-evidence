"""Authoritative-fwork tests: independent three-way controls against Network v0."""
import json

import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24s_budget_triads_v0 import plan_v0
from search import spk_24s_causal_failure_evidence_v0 as evidence


@pytest.mark.parametrize('profile', ('relays', 'threshold', 'decay', 'double_emit', 'guard_overwrite', 'fractional'))
def test_all_causal_triples_and_passive_observer_noninterference(profile):
    relevant = [(case, cs) for cid, case, cs in plan_v0() if cid.startswith(profile + '/')]
    assert relevant
    for case, cs in relevant:
        rows = evidence.evaluate_triad_v0(case, cs)
        assert len(rows) == 3
        assert all(r['status'] == 'LIMIT_REACHED' for r in rows)
        assert all(r['result_sha256'] is None for r in rows)
        assert rows[0]['frozen_reason'] in ('max_events', 'max_batches')
        assert rows[1]['frozen_reason'] == 'max_events'
        assert rows[2]['frozen_reason'] == 'max_batches'
        # A different tie winner is permissible without a normative contract.


def test_complete_receipt_with_full_reexecution():
    doc = evidence.seal_v0()
    out = evidence.verify_v0(doc)
    assert out['status'] == 'PASS'
    assert out['triad_count'] == 168
    assert out['control_probes'] == 504
    assert out['singleton_exact_agreement'] == 336
    assert sum(out['observed_tie_reason_counts'].values()) == 168
    assert out['evidence_sha256'] == sha(doc)


def test_changed_tie_reason_resealed_still_fails_replay():
    obj = json.loads(evidence.seal_v0())
    r = obj['payload']['rows'][0]
    assert r['condition'] == 'both'
    r['frozen_reason'] = 'max_events' if r['frozen_reason'] == 'max_batches' else 'max_batches'
    r['independent_selection_differs'] = (r['frozen_reason'] != r['independent_reason'])
    obj['payload_sha256'] = sha(evidence.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        evidence.verify_v0(canonical(obj))


def test_changed_singleton_resealed_still_fails_replay():
    obj = json.loads(evidence.seal_v0())
    r = obj['payload']['rows'][1]
    assert r['condition'] == 'events_only'
    r['frozen_reason'] = 'max_batches'
    obj['payload_sha256'] = sha(evidence.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        evidence.verify_v0(canonical(obj))


def test_noncanonical_and_bad_checksum_fails():
    doc = evidence.seal_v0()
    with pytest.raises(ValueError, match='noncanonical'):
        evidence.verify_v0(' ' + doc)
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        evidence.verify_v0(canonical(obj))


def test_observer_priority_mutation_is_detected(monkeypatch):
    _, case, cs = plan_v0()[0]
    old = evidence._attempt_frozen
    def divergent(net, events, probe, on):
        status, reason, recorder = old(net, events, probe, on)
        if on:
            reason = 'max_events' if reason == 'max_batches' else 'max_batches'
        return status, reason, recorder
    monkeypatch.setattr(evidence, '_attempt_frozen', divergent)
    with pytest.raises(AssertionError, match='observer changed failure reason'):
        evidence.evaluate_triad_v0(case, cs)


def test_singleton_false_priority_mutation_is_detected(monkeypatch):
    _, case, cs = plan_v0()[0]
    old = evidence._attempt_frozen
    def divergent(net, events, probe, on):
        status, reason, recorder = old(net, events, probe, on)
        if probe.condition == 'events_only':
            reason = 'max_batches'
        return status, reason, recorder
    monkeypatch.setattr(evidence, '_attempt_frozen', divergent)
    with pytest.raises(AssertionError, match='noneligible failure reason'):
        evidence.evaluate_triad_v0(case, cs)


def test_false_success_is_detected(monkeypatch):
    _, case, cs = plan_v0()[0]
    old = evidence._attempt_frozen
    def false_success(net, events, probe, on):
        status, reason, recorder = old(net, events, probe, on)
        if not on and probe.condition == 'both':
            status = 'CLOSED'
        return status, reason, recorder
    monkeypatch.setattr(evidence, '_attempt_frozen', false_success)
    with pytest.raises(AssertionError, match='reported success'):
        evidence.evaluate_triad_v0(case, cs)
