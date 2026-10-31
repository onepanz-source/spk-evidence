"""A3d integrated real frozen Compiler witness and independent replay checks."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from search.spk_arch_a3d_link_conformance_v1d import (
    SOURCE_SHA256, REGIMES, LATENCIES, evaluate_v1d,
)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_real_compiler_host_and_link_backpressure_full_corpus(scheme):
    blocked = changes = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1d(cid, case, scheme)
        assert len(row['runs']) == len(REGIMES) * len(LATENCIES)
        for run in row['runs']:
            if run['regime'] == 'ideal':
                assert not run['changed_from_a3c']
            else:
                blocked += run['source_blocked_ticks']
                changes += run['changed_from_a3c']
    if scheme == 'single':
        assert blocked == changes == 0
    else:
        assert blocked > 0 and changes > 0


def test_pinned_source_fingerprint():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_source_pinned_rehashed_forgery_rejected(monkeypatch):
    from search import spk_arch_a3d_link_conformance_v1d as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648, 'a3c_ideal_comparisons': 1296,
               'causal_link_executions': 3888, 'totals': {},
               'rows': [{'id': 'synthetic'}]}
    monkeypatch.setattr(m, 'report_v1d', lambda: fixture)
    doc = m.seal_v1d()
    assert m.verify_v1d(doc)['status'] == 'PASS'
    forged = json.loads(doc)
    forged['payload']['rows'][0]['id'] = 'forged'
    forged['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1d(canonical(forged))


def test_noncanonical_and_checksum_rejected(monkeypatch):
    from search import spk_arch_a3d_link_conformance_v1d as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648, 'a3c_ideal_comparisons': 1296,
               'causal_link_executions': 3888, 'totals': {}, 'rows': []}
    monkeypatch.setattr(m, 'report_v1d', lambda: fixture)
    doc = m.seal_v1d()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1d(doc + '\n')
    changed = json.loads(doc)
    changed['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1d(canonical(changed))


def test_compiler_forgery_visible(monkeypatch):
    from search import spk_arch_a3d_link_conformance_v1d as m
    cid, case = checked_catalog_v0()[0]
    original = m.compiled_reference

    def forged(*args):
        row = dict(original(*args))
        row['canonical_result_sha256'] = 'f' * 64
        return row

    monkeypatch.setattr(m, 'compiled_reference', forged)
    with pytest.raises(AssertionError, match='frozen compiled host differs'):
        m.evaluate_v1d(cid, case, 'single')
