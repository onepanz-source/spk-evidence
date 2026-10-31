"""Cross-layer real Compiler/A4a/A2b witnesses and anti-forgery tests."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4b_mode_memory_conformance_v1b import (
    SOURCE_SHA256, mode_memory_case_v1b,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_compiled_manifest_mode_authority_and_a2b_reference_all_216(scheme):
    for cid, case in checked_catalog_v0():
        row = mode_memory_case_v1b(cid, case, scheme)
        assert row['execute_priority'] == ['E', 'S', 'P', 'O']
        assert row['verify_priority'] == ['P', 'S', 'E', 'O']
        assert row['stage_memory_denials'] == 2
        assert row['logical_units'] >= 0


def test_source_fingerprint_is_identical_to_predecessor():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def _fixture(m):
    return {'schema': m.SCHEMA, 'source_cases': 216,
            'compiled_host_comparisons': 648,
            'mode_logical_service_runs': 1296,
            'staging_memory_denials': 1296, 'rows': [{'id': 'fixture'}]}


def test_recomputed_checksum_does_not_validate_forged_evidence(monkeypatch):
    from search import spk_arch_a4b_mode_memory_conformance_v1b as m
    monkeypatch.setattr(m, 'report_v1b', lambda: _fixture(m))
    document = m.seal_v1b()
    assert m.verify_v1b(document)['status'] == 'PASS'
    forged = json.loads(document)
    forged['payload']['rows'][0]['id'] = 'forged'
    forged['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        m.verify_v1b(canonical(forged))


def test_wrong_checksum_and_noncanonical_payload_rejected(monkeypatch):
    from search import spk_arch_a4b_mode_memory_conformance_v1b as m
    monkeypatch.setattr(m, 'report_v1b', lambda: _fixture(m))
    original = m.seal_v1b()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1b(original + '\n')
    bad = json.loads(original)
    bad['payload_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1b(canonical(bad))


def test_wrong_frozen_compiler_manifest_is_rejected(monkeypatch):
    from search import spk_arch_a4b_mode_memory_conformance_v1b as m
    cid, case = checked_catalog_v0()[0]
    real = m.evaluate_v1b
    def forged(*args):
        obj = dict(real(*args))
        obj['manifest_sha256'] = 'f' * 64
        return obj
    monkeypatch.setattr(m, 'evaluate_v1b', forged)
    with pytest.raises(AssertionError, match='manifest mismatch'):
        m.mode_memory_case_v1b(cid, case, 'single')


def test_wrong_upstream_a2b_authorization_is_rejected(monkeypatch):
    from search import spk_arch_a4b_mode_memory_conformance_v1b as m
    cid, case = checked_catalog_v0()[0]
    real = m.evaluate_v1b
    def forged(*args):
        obj = dict(real(*args))
        obj['nominal_authorization_sha256'] = '0' * 64
        return obj
    monkeypatch.setattr(m, 'evaluate_v1b', forged)
    with pytest.raises(AssertionError, match='authorization mismatch'):
        m.mode_memory_case_v1b(cid, case, 'single')
