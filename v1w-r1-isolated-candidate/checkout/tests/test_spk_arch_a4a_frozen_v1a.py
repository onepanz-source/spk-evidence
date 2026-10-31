"""A4a real Compiler/host witness and semantic replay contracts."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4a_mode_conformance_v1a import (
    SOURCE_SHA256, mode_case_v1a,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_real_compiler_a3d_and_mode_execution_all_corpus(scheme):
    for cid, case in checked_catalog_v0():
        row = mode_case_v1a(cid, case, scheme)
        assert row['epoch'] == 6
        assert row['status'] == 'QUIESCENT'
        assert row['transitions'] == 6
        assert row['staged_references'] == 2
        assert row['live_runs'] == row['verifications'] == 1


def test_source_fingerprint_remains_frozen():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_forged_recomputed_checksum_is_rejected(monkeypatch):
    from search import spk_arch_a4a_mode_conformance_v1a as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648,
               'mode_controlled_executions': 648,
               'independent_mode_replays': 648,
               'staged_candidate_references': 1296,
               'rows': [{'id': 'synthetic'}]}
    monkeypatch.setattr(m, 'report_v1a', lambda: fixture)
    doc = m.seal_v1a()
    assert m.verify_v1a(doc)['status'] == 'PASS'
    forged = json.loads(doc)
    forged['payload']['rows'][0]['id'] = 'forged'
    forged['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        m.verify_v1a(canonical(forged))


def test_noncanonical_and_bad_hash_are_rejected(monkeypatch):
    from search import spk_arch_a4a_mode_conformance_v1a as m
    monkeypatch.setattr(m, 'report_v1a', lambda: {
        'schema': m.SCHEMA, 'source_cases': 216,
        'compiled_host_comparisons': 648, 'mode_controlled_executions': 648,
        'independent_mode_replays': 648, 'staged_candidate_references': 1296,
        'rows': []})
    doc = m.seal_v1a()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1a(doc + '\n')
    bad = json.loads(doc)
    bad['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1a(canonical(bad))


def test_forged_compiler_reference_does_not_validate(monkeypatch):
    from search import spk_arch_a4a_mode_conformance_v1a as m
    cid, case = checked_catalog_v0()[0]
    def forged(*args):
        return {'manifest_sha256': 'f' * 64,
                'runs': [{'latency_ticks': 2, 'regime': 'link_limited',
                          'result_sha256': '0' * 64, 'cross_pe_occurrences': 0,
                          'source_blocked_ticks': 0}]}
    monkeypatch.setattr(m, 'evaluate_v1d', forged)
    with pytest.raises(AssertionError, match='differs from A3d witness'):
        m.mode_case_v1a(cid, case, 'single')
