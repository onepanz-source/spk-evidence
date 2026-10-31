"""Real-fwork versioned manifest host and evidence tampering regression."""

import json

import pytest

from search import spk_24t_diagnostic_manifest_host_v0 as host
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24t_diagnostic_contract_v0 import classify_v0
from search.spk_24n_differential_evidence_v0 import adapt_frozen_v0
from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0


@pytest.fixture(scope='module')
def demo():
    manifest, pin = host._demo_manifest()
    decoded = loads_compilation_manifest_v0(manifest)
    case = adapt_frozen_v0(decoded.network, decoded.initial_events)
    assert len(case.nodes) == 2 and len(case.edges) == 3
    return manifest, pin, case


def test_successful_compiled_multineuron_manifest(demo):
    manifest, pin, case = demo
    proof = classify_v0(case, max_batches=128, max_events=4096)
    assert proof.status == 'CLOSED'
    receipt = host.seal_v0(manifest, pin)
    result = host.verify_v0(receipt)
    assert result['status'] == 'CLOSED'
    assert result['adjudication'] == 'EXACT_PASS'
    assert result['eligible_reasons'] == []
    assert json.loads(receipt)['payload']['execution']['result']


def test_exact_budget_boundary_closed(demo):
    manifest, pin, case = demo
    proof = classify_v0(case, max_batches=128, max_events=4096)
    doc = host.seal_v0(manifest, pin, max_batches=proof.prior_batches,
                       max_events=proof.prior_events)
    assert host.verify_v0(doc)['status'] == 'CLOSED'


def test_dual_failure_is_accepted_with_observed_frozen_reason(demo):
    manifest, pin, case = demo
    # Single initial event; then one or more routed batches. Both limits
    # become insufficient at the first routed batch.
    proof = classify_v0(case, max_batches=1, max_events=1)
    assert proof.status == 'LIMIT_REACHED'
    assert proof.eligible == ('max_batches', 'max_events')
    doc = host.seal_v0(manifest, pin, max_batches=1, max_events=1)
    out = host.verify_v0(doc)
    assert out['status'] == 'LIMIT_REACHED'
    assert out['adjudication'] == 'AMBIGUOUS_TIE_PASS'
    assert out['selected_reason'] in out['eligible_reasons']
    assert json.loads(doc)['payload']['execution']['result'] is None


def test_isolated_event_and_batch_limits_exact(demo):
    manifest, pin, case = demo
    for mb, me, expected in ((128, 1, 'max_events'), (1, 4096, 'max_batches')):
        proof = classify_v0(case, max_batches=mb, max_events=me)
        assert proof.eligible == (expected,)
        receipt = host.seal_v0(manifest, pin, max_batches=mb, max_events=me)
        check = host.verify_v0(receipt)
        assert check['adjudication'] == 'EXACT_PASS'
        assert check['selected_reason'] == expected


def test_wrong_manifest_pin_rejected_before_execution(demo, monkeypatch):
    manifest, pin, _ = demo
    def should_not_run(*args, **kwargs):
        raise AssertionError('pin validated too late')
    monkeypatch.setattr(host, '_attempt', should_not_run)
    with pytest.raises(ValueError, match='source-pin mismatch'):
        host.seal_v0(manifest, '0' * 64)


def test_resealed_forgery_of_selected_reason_rejected(demo):
    manifest, pin, _ = demo
    obj = json.loads(host.seal_v0(manifest, pin, max_batches=1, max_events=1))
    obj['payload']['execution']['selected_reason'] = 'max_batches' if obj['payload']['execution']['selected_reason'] == 'max_events' else 'max_events'
    obj['payload_sha256'] = sha(host.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        host.verify_v0(canonical(obj))


def test_resealed_eligible_set_forgery_rejected(demo):
    manifest, pin, _ = demo
    obj = json.loads(host.seal_v0(manifest, pin, max_batches=1, max_events=1))
    obj['payload']['execution']['eligible_reasons'] = ['max_events']
    obj['payload_sha256'] = sha(host.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        host.verify_v0(canonical(obj))


def test_corrupted_receipt_and_duplicate_json_keys_rejected(demo):
    manifest, pin, _ = demo
    doc = host.seal_v0(manifest, pin)
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        host.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='noncanonical'):
        host.verify_v0(' ' + doc)
    with pytest.raises(ValueError, match='duplicate JSON'):
        host.verify_v0(doc[:-1] + ',"schema":"forged"}')


def test_observer_status_mismatch_is_detected(demo, monkeypatch):
    manifest, pin, _ = demo
    real = host._attempt
    def injected(net, events, budget, *, observed):
        if observed:
            return ('LIMIT_REACHED', 'max_events', None)
        return real(net, events, budget, observed=False)
    monkeypatch.setattr(host, '_attempt', injected)
    with pytest.raises(AssertionError, match='observer changed execution status'):
        host.seal_v0(manifest, pin)


def test_observer_choice_mismatch_is_detected(demo, monkeypatch):
    manifest, pin, _ = demo
    real = host._attempt
    def injected(net, events, budget, *, observed):
        status, value, watcher = real(net, events, budget, observed=observed)
        if observed and status == 'LIMIT_REACHED':
            value = 'max_batches' if value == 'max_events' else 'max_events'
        return status, value, watcher
    monkeypatch.setattr(host, '_attempt', injected)
    with pytest.raises(AssertionError, match='observer changed selected failure reason'):
        host.seal_v0(manifest, pin, max_batches=1, max_events=1)


def test_unknown_error_propagates_and_host_is_consumed(demo, monkeypatch):
    manifest, pin, _ = demo
    def injected(*args, **kwargs):
        raise RuntimeError('unknown runtime failure')
    monkeypatch.setattr(host, '_attempt', injected)
    instance = host.DiagnosticReferenceHostV0(manifest, pin)
    with pytest.raises(RuntimeError, match='unknown runtime failure'):
        instance.run()
    assert instance.phase == 'FAILED'
    with pytest.raises(RuntimeError, match='already consumed'):
        instance.run()


def test_successful_host_consumed_once(demo):
    manifest, pin, _ = demo
    instance = host.DiagnosticReferenceHostV0(manifest, pin)
    doc = instance.run()
    assert instance.phase == 'CLOSED'
    with pytest.raises(RuntimeError, match='already consumed'):
        instance.run()
    assert host.verify_v0(doc)['status'] == 'CLOSED'
