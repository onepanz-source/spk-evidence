"""Frozen-runtime boundary tests. These run on fwork, not synthetic substitutes."""
import json

import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24q_limit_probe_plan_v0 import plan_v0
from search import spk_24q_failure_parity_v0 as matrix
from search.spk_24o_extended_differential_v0 import to_frozen_v0


@pytest.mark.parametrize('profile', (
    'relays', 'threshold', 'decay', 'double_emit', 'guard_overwrite', 'fractional',
))
def test_frozen_observer_and_oracle_parity_for_entire_profile(profile):
    count = 0
    for cid, case, probes in plan_v0():
        if not cid.startswith(profile + '/'):
            continue
        network, events = to_frozen_v0(case)
        for probe in probes:
            result = matrix.evaluate_probe_v0(case, network, events, probe)
            assert result['status'] == probe.expected_status
            assert result['reason'] == probe.expected_reason
            count += 1
    assert count > 36


def test_all_corpus_evidence_replay_and_canonical_sha():
    doc = matrix.seal_v0()
    obj = json.loads(doc)
    assert canonical(obj) == doc
    assert len(obj['payload']['rows']) == 558
    assert matrix.verify_v0(doc)['evidence_sha256'] == sha(doc)


def test_resealed_failure_reason_forgery_rejected_by_reexecution():
    obj = json.loads(matrix.seal_v0())
    i = next(i for i, r in enumerate(obj['payload']['rows'])
             if r['reason'] == 'max_events')
    obj['payload']['rows'][i]['reason'] = 'max_batches'
    obj['payload_sha256'] = sha(matrix.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        matrix.verify_v0(canonical(obj))


def test_resealed_closed_result_forgery_rejected_by_reexecution():
    obj = json.loads(matrix.seal_v0())
    i = next(i for i, r in enumerate(obj['payload']['rows'])
             if r['status'] == 'CLOSED')
    obj['payload']['rows'][i]['result_sha256'] = '0' * 64
    obj['payload_sha256'] = sha(matrix.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        matrix.verify_v0(canonical(obj))


def test_malformed_envelopes_rejected():
    doc = matrix.seal_v0()
    with pytest.raises(ValueError, match='noncanonical'):
        matrix.verify_v0(' ' + doc)
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        matrix.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='duplicate JSON'):
        matrix.verify_v0(doc[:-1] + ',"schema":"forged"}')


def test_status_divergence_cannot_pass(monkeypatch):
    cid, case, probes = next(x for x in plan_v0() if len(x[2]) > 1)
    network, events = to_frozen_v0(case)
    probe = probes[0]
    original = matrix._attempt_frozen
    def corrupt(net, ev, p, observed):
        status, value, recorder = original(net, ev, p, observed)
        if observed:
            return 'LIMIT_REACHED', 'max_events', recorder
        return status, value, recorder
    monkeypatch.setattr(matrix, '_attempt_frozen', corrupt)
    with pytest.raises(AssertionError, match='status disagreement'):
        matrix.evaluate_probe_v0(case, network, events, probe)


def test_limit_reason_divergence_cannot_pass(monkeypatch):
    cid, case, probes = next(x for x in plan_v0()
                              if any(p.expected_reason == 'max_events' for p in x[2]))
    probe = next(p for p in probes if p.expected_reason == 'max_events')
    network, events = to_frozen_v0(case)
    original = matrix._attempt_oracle
    def corrupt(c, p):
        status, _ = original(c, p)
        return status, 'max_batches'
    monkeypatch.setattr(matrix, '_attempt_oracle', corrupt)
    with pytest.raises(AssertionError, match='limit reason disagreement'):
        matrix.evaluate_probe_v0(case, network, events, probe)


def test_unexpected_runtime_exception_not_masqueraded_as_limit(monkeypatch):
    cid, case, probes = plan_v0()[0]
    network, events = to_frozen_v0(case)
    def broken(*a, **kw):
        raise RuntimeError('synthetic unexpected failure')
    monkeypatch.setattr(matrix, 'run_network_v0', broken)
    with pytest.raises(RuntimeError, match='unexpected failure'):
        matrix.evaluate_probe_v0(case, network, events, probes[0])
