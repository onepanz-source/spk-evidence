"""Real Compiler/host + A2c arbitration; executed on authoritative fwork."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2c_memory_service_conformance_v1c import (
    SOURCE_SHA256, evaluate_v1c, seal_v1c, verify_v1c,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_216_compiled_cases_each_have_memory_service_evidence(scheme):
    count = waits = faults = 0
    for cid, case in checked_catalog_v0():
        result = evaluate_v1c(cid, case, scheme)
        assert result['manifest_sha256']
        assert result['limited_service_sha256']
        assert result['unconstrained_service_sha256']
        assert result['nominal_units'] >= 0
        assert result['limited_weighted_wait'] >= 0
        assert result['limited_service_ticks'] >= result['unconstrained_service_ticks']
        waits += result['limited_weighted_wait']
        faults += result['fault_service_sha256'] is not None
        count += 1
    assert count == 216
    assert faults == 168
    assert waits > 0


def test_source_catalog_pin():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_sealed_replay_rejects_modified_grants_even_after_rehash(monkeypatch):
    from search import spk_arch_a2c_memory_service_conformance_v1c as m
    fixture = {'schema': m.SCHEMA, 'compiled_host_comparisons': 648,
               'nominal_service_runs': 1296, 'fault_service_runs': 504,
               'limited_total_weighted_wait': 20,
               'rows': [{'id': 'fixture', 'limited_weighted_wait': 20}]}
    monkeypatch.setattr(m, 'report_v1c', lambda: fixture)
    doc = m.seal_v1c()
    assert m.verify_v1c(doc)['status'] == 'PASS'
    forged = json.loads(doc)
    forged['payload']['rows'][0]['limited_weighted_wait'] = 0
    forged['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1c(canonical(forged))


def test_wrong_checksum_rejected(monkeypatch):
    from search import spk_arch_a2c_memory_service_conformance_v1c as m
    monkeypatch.setattr(m, 'report_v1c', lambda: {'schema': m.SCHEMA, 'rows': []})
    forged = json.loads(m.seal_v1c())
    forged['payload_sha256'] = '0'*64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1c(canonical(forged))


def test_unknown_priority_in_receipt_is_rejected(monkeypatch):
    from search import spk_arch_a2c_memory_service_conformance_v1c as m
    monkeypatch.setattr(m, 'report_v1c', lambda: {'schema': m.SCHEMA, 'rows': []})
    forged = json.loads(m.seal_v1c())
    forged['priority_claim'] = 'SYSTEM'
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1c(canonical(forged))
