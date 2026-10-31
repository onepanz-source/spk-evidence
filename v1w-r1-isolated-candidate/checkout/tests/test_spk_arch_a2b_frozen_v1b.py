"""Actual frozen Compiler -> PE-local -> memory projection -> A2b authorization."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_arch_a2b_access_conformance_v1b import (
    SOURCE_SHA256, evaluate_v1b, seal_v1b, verify_v1b,
)
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_all_compiled_cases_admit_and_authorize(scheme):
    count = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1b(cid, case, scheme)
        assert row['manifest_sha256']
        assert row['authority_sha256']
        assert row['nominal_authorization_sha256']
        assert row['nominal_logical_units'] >= 0
        count += 1
    assert count == 216


def test_frozen_baseline_source_pin():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_replay_forgery_rejected_with_recomputed_hash(monkeypatch):
    from search import spk_arch_a2b_access_conformance_v1b as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648, 'authorized_fault_prefixes': 504,
               'rows': [{'id':'fixture', 'nominal_logical_units': 1}]}
    monkeypatch.setattr(m, 'report_v1b', lambda: fixture)
    doc = m.seal_v1b()
    assert m.verify_v1b(doc)['status'] == 'PASS'
    forged = json.loads(doc)
    forged['payload']['rows'][0]['nominal_logical_units'] = 999
    forged['payload_sha256'] = sha(m.SCHEMA+'\n'+canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1b(canonical(forged))


def test_bad_checksum_denied(monkeypatch):
    from search import spk_arch_a2b_access_conformance_v1b as m
    monkeypatch.setattr(m, 'report_v1b', lambda: {'schema': m.SCHEMA, 'rows': []})
    obj = json.loads(m.seal_v1b())
    obj['payload_sha256'] = '0'*64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1b(canonical(obj))


def test_extra_document_field_denied(monkeypatch):
    from search import spk_arch_a2b_access_conformance_v1b as m
    monkeypatch.setattr(m, 'report_v1b', lambda: {'schema': m.SCHEMA, 'rows': []})
    obj = json.loads(m.seal_v1b())
    obj['priority'] = 'P0'
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1b(canonical(obj))
