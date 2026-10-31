"""Real-fwork negative conformance: frozen Compiler, manifest host and Network."""
import json

import pytest

from search import spk_24v_negative_conformance_v0 as audit
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24u_cross_layer_v0 import compile_case_v0
from search.spk_24v_negative_plan_v0 import identity_v0


@pytest.fixture(scope='module')
def document():
    return audit.seal_v0()


def test_all_negative_admission_and_observer_fault_domains(document):
    payload = json.loads(document)['payload']
    assert payload['source_manifest_count'] == 216
    assert payload['rejected_before_executor'] == 1512
    assert payload['observer_callback_faults'] == 82
    assert payload['observer_budget_corruptions'] == 36
    assert payload['unrelated_runtime_abortions'] == 6
    assert payload['compiler_source_rejections'] == 36
    assert payload['plan_sha256'] == identity_v0()
    assert len(payload['admission']) == 216
    assert len(payload['observer']) == 41
    assert len(payload['budget_observer']) == 36


def test_all_admission_mutations_rejected_before_frozen_execution(document):
    rows = json.loads(document)['payload']['admission']
    expected = set(audit.MUTATIONS)
    assert all(len(r['rejections']) == 7 and
               {k for k, _ in r['rejections']} == expected for r in rows)


def test_silent_batch_and_route_observer_corruption_is_not_a_receipt(document):
    rows = json.loads(document)['payload']['observer']
    for r in rows:
        faults = {x['kind']: x['error'] for x in r['faults']}
        assert faults.get('throw_batch', faults.get('throw_route')) == 'ObserverInjectedFaultV0'
        if 'drop_batch' in faults:
            assert faults['drop_batch'] == 'DifferentialMismatchV0'
        if 'drop_route' in faults:
            assert faults['drop_route'] == 'DifferentialMismatchV0'


def test_real_manifest_source_pin_is_checked_before_executor(monkeypatch):
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    _, case = catalog_v0()[0]
    manifest, pin = compile_case_v0(case)
    def must_not_run(*args, **kwargs):
        raise audit.ExecutorReachedV0('run must be denied')
    monkeypatch.setattr(host, '_attempt', must_not_run)
    with pytest.raises(ValueError, match='source-pin mismatch'):
        host.execute_manifest_v0(manifest + '\n', pin)


def test_error_on_callback_consumes_host_without_successful_receipt(monkeypatch):
    from search import spk_24t_diagnostic_manifest_host_v0 as host
    from search import spk_24p_network_application_host_v0 as backend
    _, case = next((cid, c) for cid, c in catalog_v0()
                   if cid == 'relays/single/at_zero')
    manifest, pin = compile_case_v0(case)
    def injected(self, entry):
        raise audit.ObserverInjectedFaultV0('expected callback failure')
    monkeypatch.setattr(backend._PassiveRecorder, 'on_batch', injected)
    obj = host.DiagnosticReferenceHostV0(manifest, pin)
    with pytest.raises(audit.ObserverInjectedFaultV0):
        obj.run()
    assert obj.phase == 'FAILED'
    with pytest.raises(RuntimeError, match='already consumed'):
        obj.run()


def test_verified_evidence_is_fully_replayed(document):
    report = audit.verify_v0(document)
    assert report['status'] == 'PASS'
    assert report['source_manifest_count'] == 216
    assert report['rejected_before_executor'] == 1512
    assert report['evidence_sha256'] == sha(document)


def test_resealed_forged_rejection_is_rejected_on_reexecution(document):
    obj = json.loads(document)
    obj['payload']['admission'][0]['rejections'][0][1] = 'MadeUpException'
    obj['payload_sha256'] = sha(audit.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        audit.verify_v0(canonical(obj))


def test_checksum_and_noncanonical_evidence_rejected_without_reexecution(document):
    obj = json.loads(document)
    obj['payload_sha256'] = '0'*64
    with pytest.raises(ValueError, match='checksum'):
        audit.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='noncanonical'):
        audit.verify_v0(' ' + document)
    with pytest.raises(ValueError, match='duplicate JSON'):
        audit.verify_v0(document[:-1] + ',"schema":"forged"}')
