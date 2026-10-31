"""24r frozen Network tests. Require authoritative fwork checkout."""
import json

import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24r_dual_limit_plan_v0 import plan_v0
from search import spk_24r_dual_limit_characterization_v0 as boundary


@pytest.mark.parametrize('profile', (
    'relays', 'threshold', 'decay', 'double_emit', 'guard_overwrite', 'fractional',
))
def test_simultaneous_failure_and_observer_noninterference(profile):
    rows = [(case, p) for cid, case, p in plan_v0()
            if cid.startswith(profile + '/')]
    assert rows
    for case, probe in rows:
        row = boundary.evaluate_v0(case, probe)
        assert row['status'] == 'LIMIT_REACHED'
        assert row['result_sha256'] is None
        assert row['both_eligible'] is True
        assert row['frozen_reason'] in {'max_events', 'max_batches'}


def test_canonical_receipt_and_complete_replay():
    doc = boundary.seal_v0()
    obj = json.loads(doc)
    assert canonical(obj) == doc
    result = boundary.verify_v0(doc)
    assert result['dual_limit_probes'] == 168
    assert sum(result['frozen_reason_counts'].values()) == 168
    assert result['evidence_sha256'] == sha(doc)


def test_resealed_priority_forgery_rejected():
    doc = boundary.seal_v0()
    obj = json.loads(doc)
    first = obj['payload']['rows'][0]
    first['frozen_reason'] = ('max_events' if first['frozen_reason'] == 'max_batches'
                              else 'max_batches')
    obj['payload_sha256'] = sha(boundary.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        boundary.verify_v0(canonical(obj))


def test_noncanonical_duplicate_keys_and_checksum_rejected():
    doc = boundary.seal_v0()
    with pytest.raises(ValueError, match='noncanonical'):
        boundary.verify_v0(' ' + doc)
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        boundary.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='duplicate JSON'):
        boundary.verify_v0(doc[:-1] + ',"schema":"forged"}')


def test_observer_reason_mutation_detected(monkeypatch):
    _, case, p = plan_v0()[0]
    original = boundary._attempt_frozen
    def bad(net, ev, pair, observed):
        status, reason, recorder = original(net, ev, pair, observed)
        if observed:
            reason = 'max_events' if reason == 'max_batches' else 'max_batches'
        return status, reason, recorder
    monkeypatch.setattr(boundary, '_attempt_frozen', bad)
    with pytest.raises(AssertionError, match='observer changed limit priority'):
        boundary.evaluate_v0(case, p)


def test_false_success_on_dual_exhaustion_detected(monkeypatch):
    _, case, p = plan_v0()[0]
    original = boundary._attempt_frozen
    def bad(net, ev, pair, observed):
        status, reason, recorder = original(net, ev, pair, observed)
        if not observed:
            status = 'CLOSED'
        return status, reason, recorder
    monkeypatch.setattr(boundary, '_attempt_frozen', bad)
    with pytest.raises(AssertionError, match='not reported as limit'):
        boundary.evaluate_v0(case, p)


def test_unexpected_errors_are_not_reclassified(monkeypatch):
    _, case, p = plan_v0()[0]
    def unexpected(*args, **kwargs):
        raise RuntimeError('synthetic unexpected exception')
    monkeypatch.setattr(boundary, '_attempt_frozen', unexpected)
    with pytest.raises(RuntimeError, match='unexpected exception'):
        boundary.evaluate_v0(case, p)
