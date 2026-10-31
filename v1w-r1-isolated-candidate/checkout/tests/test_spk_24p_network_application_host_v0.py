"""24p integration against the real frozen Compiler and Network on fwork."""
from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from search import spk_24p_network_application_host_v0 as host
from search.spk_24n_differential_evidence_v0 import canonical, sha
from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0


@pytest.fixture(scope='module')
def admitted():
    text, digest = host._demo_manifest()
    compiled = loads_compilation_manifest_v0(text)
    assert len(compiled.network.nodes) == 2
    assert len(compiled.network.edges) == 3
    assert len(compiled.initial_events) == 1
    return text, digest


def test_real_compiler_to_multineuron_host_to_independent_oracle(admitted):
    text, digest = admitted
    payload = host.execute_manifest_v0(text, digest)
    assert payload['status'] == 'CLOSED'
    assert payload['reason'] is None
    assert payload['comparison'] == 'INDEPENDENT_PASS'
    assert payload['result']['processed_batches'] == 3
    assert payload['result']['processed_events'] == 4
    assert payload['observations'] == {'batch_count': 3, 'route_count': 3}
    assert payload['result']['terminal_outputs']


def test_success_receipt_is_canonical_and_replayed(admitted):
    document = host.seal_v0(*admitted)
    envelope = json.loads(document)
    assert canonical(envelope) == document
    assert envelope['payload']['execution']['status'] == 'CLOSED'
    assert host.verify_v0(document) == {
        'status': 'CLOSED', 'reason': None, 'manifest_sha256': admitted[1],
        'evidence_sha256': sha(document),
    }


@pytest.mark.parametrize('kind,budget,reason', [
    ('events', {'max_events': 3, 'max_batches': 128}, 'max_events'),
    ('batches', {'max_events': 4096, 'max_batches': 2}, 'max_batches'),
])
def test_limit_classification_agrees_with_independent_oracle(admitted, kind, budget, reason):
    receipt = host.seal_v0(*admitted, **budget)
    execution = json.loads(receipt)['payload']['execution']
    assert execution['status'] == 'LIMIT_REACHED'
    assert execution['reason'] == reason
    assert execution['result'] is None
    assert execution['comparison'] is None
    assert execution['observations'] is None
    assert host.verify_v0(receipt)['status'] == 'LIMIT_REACHED'


def test_exact_boundary_remains_successful(admitted):
    payload = host.execute_manifest_v0(*admitted, max_events=4, max_batches=3)
    assert payload['status'] == 'CLOSED'
    assert payload['result']['processed_events'] == 4
    assert payload['result']['processed_batches'] == 3


def test_source_pin_rejects_drift_before_loader(admitted, monkeypatch):
    def forbidden(_):
        pytest.fail('pin mismatch must fail before compiler manifest decoding')
    monkeypatch.setattr(host, 'loads_compilation_manifest_v0', forbidden)
    with pytest.raises(ValueError, match='source-pin'):
        host.execute_manifest_v0(admitted[0] + '\n', admitted[1])


@pytest.mark.parametrize('bad', [None, 123, True, '', '0'*63, 'Z'*64, 'A'*64])
def test_malformed_expected_digest_rejected(admitted, bad):
    with pytest.raises(ValueError, match='expected_manifest_sha256'):
        host.execute_manifest_v0(admitted[0], bad)


@pytest.mark.parametrize('name,value', [
    ('max_events', 0), ('max_batches', 0),
    ('max_events', -1), ('max_batches', True),
    ('max_events', 2.0), ('max_batches', '2'),
])
def test_invalid_budgets_are_not_silently_rounded(admitted, name, value):
    with pytest.raises(ValueError, match=name):
        host.execute_manifest_v0(*admitted, **{name: value})


def test_single_shot_host_closes_and_rejects_second_run(admitted):
    session = host.NetworkReferenceHostV0(*admitted)
    assert session.phase == 'NEW'
    doc = session.run()
    assert session.phase == 'CLOSED'
    assert host.verify_v0(doc)['status'] == 'CLOSED'
    with pytest.raises(RuntimeError, match='already consumed'):
        session.run()


def test_single_shot_limit_remains_terminal(admitted):
    session = host.NetworkReferenceHostV0(*admitted)
    assert host.verify_v0(session.run(max_events=3))['status'] == 'LIMIT_REACHED'
    assert session.phase == 'LIMIT_REACHED'
    with pytest.raises(RuntimeError, match='already consumed'):
        session.run()


def test_failed_host_does_not_rearm(admitted):
    session = host.NetworkReferenceHostV0(admitted[0] + '\n', admitted[1])
    with pytest.raises(ValueError, match='source-pin'):
        session.run()
    assert session.phase == 'FAILED'
    with pytest.raises(RuntimeError, match='already consumed'):
        session.run()


def test_concurrent_callers_cannot_both_consume_same_instance(admitted):
    session = host.NetworkReferenceHostV0(*admitted)
    def call(_):
        try:
            return host.verify_v0(session.run())['status']
        except RuntimeError:
            return 'REJECTED'
    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(call, range(6)))
    assert outcomes.count('CLOSED') == 1
    assert outcomes.count('REJECTED') == 5


def test_external_observer_is_not_injected_into_public_host(admitted):
    import inspect
    public = inspect.signature(host.execute_manifest_v0).parameters
    assert 'learning_observer' not in public
    assert 'observer' not in public


def test_callback_exception_is_not_silently_converted_to_success(admitted, monkeypatch):
    def fail_callback(self, _):
        raise RuntimeError('observer callback failed')
    monkeypatch.setattr(host._PassiveRecorder, 'on_batch', fail_callback)
    session = host.NetworkReferenceHostV0(*admitted)
    with pytest.raises(RuntimeError, match='observer callback failed'):
        session.run()
    assert session.phase == 'FAILED'


def test_synthetic_observer_outcome_disagreement_fails_closed(admitted, monkeypatch):
    original = host._attempt
    def divergent(net, events, budget, *, observed):
        if observed:
            return 'LIMIT_REACHED', 'max_events', host._PassiveRecorder()
        return original(net, events, budget, observed=False)
    monkeypatch.setattr(host, '_attempt', divergent)
    with pytest.raises(AssertionError, match='observer changed execution outcome'):
        host.seal_v0(*admitted)


def test_synthetic_oracle_limit_disagreement_fails_closed(admitted, monkeypatch):
    def invalid_success(*args, **kwargs):
        return {'invalid': True}
    monkeypatch.setattr(host, 'execute_v0', invalid_success)
    with pytest.raises(AssertionError, match='limit absent'):
        host.seal_v0(*admitted, max_events=3)


def test_resealed_result_forgery_rejected_by_reexecution(admitted):
    obj = json.loads(host.seal_v0(*admitted))
    obj['payload']['execution']['result']['processed_events'] += 1
    obj['payload_sha256'] = sha(host.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        host.verify_v0(canonical(obj))


def test_resealed_limit_reason_forgery_rejected(admitted):
    obj = json.loads(host.seal_v0(*admitted, max_events=3))
    obj['payload']['execution']['reason'] = 'max_batches'
    obj['payload_sha256'] = sha(host.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        host.verify_v0(canonical(obj))


def test_plain_checksum_and_noncanonical_encoding_rejected(admitted):
    doc = host.seal_v0(*admitted)
    obj = json.loads(doc)
    obj['payload_sha256'] = '0'*64
    with pytest.raises(ValueError, match='checksum'):
        host.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='noncanonical'):
        host.verify_v0(' ' + doc)
    with pytest.raises(ValueError, match='duplicate JSON'):
        host.verify_v0(doc[:-1] + ',"schema":"forged"}')


def test_independent_oracle_result_mutation_detected(admitted, monkeypatch):
    original = host.project_v0
    def corrupted(*args, **kwargs):
        value = original(*args, **kwargs)
        return {**value, 'processed_batches': value['processed_batches']+1}
    monkeypatch.setattr(host, 'project_v0', corrupted)
    with pytest.raises(AssertionError, match='projection differ'):
        host.seal_v0(*admitted)


def test_reject_unsupported_frozen_exception_not_packaged_as_limit(admitted, monkeypatch):
    def failure(*args, **kwargs):
        raise RuntimeError('unexpected runtime error')
    monkeypatch.setattr(host, 'run_network_v0', failure)
    with pytest.raises(RuntimeError, match='unexpected runtime error'):
        host.seal_v0(*admitted)
