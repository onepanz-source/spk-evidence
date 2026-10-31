"""Full frozen Compiler/Network comparison at zero transport latency only."""
import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3a_temporal_conformance_v1a import (
    SOURCE_SHA256, evaluate_v1a, seal_v1a, verify_v1a,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_compiled_reference_and_latency_variants_over_all_cases(scheme):
    changed = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1a(cid, case, scheme)
        assert len(row['timings']) == 3
        assert all(t['processed_events'] >= len(case.events) for t in row['timings'])
        if scheme == 'single':
            assert len({t['result_sha256'] for t in row['timings']}) == 1
        if row['timings'][0]['result_sha256'] != row['timings'][1]['result_sha256']:
            changed += 1
    if scheme != 'single':
        assert changed > 0, 'positive inter-PE latency did not causally change anything'


def test_pinned_catalog_matches_24o():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_forged_resealed_receipt_rejected(monkeypatch):
    from search import spk_arch_a3a_temporal_conformance_v1a as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_reference_comparisons': 648,
               'temporal_executions': 1944,
               'ideal_cross_pe_route_occurrences': 768,
               'rows': [{'id': 'fixture', 'timings': [{'extra_latency_ticks': 0}]}]}
    monkeypatch.setattr(m, 'report_v1a', lambda: fixture)
    doc = m.seal_v1a()
    assert m.verify_v1a(doc)['status'] == 'PASS'
    altered = json.loads(doc)
    altered['payload']['rows'][0]['id'] = 'forged'
    altered['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(altered['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1a(canonical(altered))


def test_checksum_and_noncanonical_rejected(monkeypatch):
    from search import spk_arch_a3a_temporal_conformance_v1a as m
    monkeypatch.setattr(m, 'report_v1a', lambda: {'schema': m.SCHEMA})
    doc = m.seal_v1a()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1a(doc + '\n')
    changed = json.loads(doc)
    changed['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1a(canonical(changed))


def test_frozen_mismatch_not_masked(monkeypatch):
    from search import spk_arch_a3a_temporal_conformance_v1a as m
    cid, case = checked_catalog_v0()[1]
    original = m.compiled_reference

    def broken(*args, **kwargs):
        result = dict(original(*args, **kwargs))
        result['canonical_result_sha256'] = 'f' * 64
        return result
    monkeypatch.setattr(m, 'compiled_reference', broken)
    with pytest.raises(AssertionError, match='zero-latency compiled reference mismatch'):
        m.evaluate_v1a(cid, case, 'single')
