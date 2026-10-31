"""A3b real Compiler/host anchoring and sealed cross-process evidence."""
import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from search.spk_arch_a3b_causal_service_conformance_v1b import (
    SOURCE_SHA256, REGIMES, LATENCIES, evaluate_v1b,
)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_real_frozen_host_and_all_causal_service_regimes(scheme):
    effects = 0
    for cid, case in checked_catalog_v0():
        evaluation = evaluate_v1b(cid, case, scheme)
        assert len(evaluation['timings']) == len(REGIMES) * len(LATENCIES)
        for row in evaluation['timings']:
            if row['regime'] == 'ideal':
                assert row['matches_ideal']
                assert row['event_weighted_wait_ticks'] == 0
            else:
                effects += not row['matches_ideal']
    if scheme == 'single':
        assert effects > 0, 'one PE still competes for shared grants'
    else:
        assert effects > 0, 'finite grant capacity was not observable'


def test_pinned_source_fingerprint():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_forged_rehashed_evidence_rejected(monkeypatch):
    from search import spk_arch_a3b_causal_service_conformance_v1b as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648, 'a3a_ideal_comparisons': 1296,
               'causal_service_executions': 5184,
               'totals': {'ideal': {'executions': 1296}},
               'rows': [{'id': 'synthetic'}]}
    monkeypatch.setattr(m, 'report_v1b', lambda: fixture)
    doc = m.seal_v1b()
    assert m.verify_v1b(doc)['status'] == 'PASS'
    altered = json.loads(doc)
    altered['payload']['rows'][0]['id'] = 'attacker'
    altered['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(altered['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1b(canonical(altered))


def test_noncanonical_and_wrong_checksum_rejected(monkeypatch):
    from search import spk_arch_a3b_causal_service_conformance_v1b as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'compiled_host_comparisons': 648, 'a3a_ideal_comparisons': 1296,
               'causal_service_executions': 5184, 'totals': {}, 'rows': []}
    monkeypatch.setattr(m, 'report_v1b', lambda: fixture)
    doc = m.seal_v1b()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1b(doc + '\n')
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1b(canonical(obj))


def test_compiler_mismatch_cannot_be_silently_masked(monkeypatch):
    from search import spk_arch_a3b_causal_service_conformance_v1b as m
    cid, case = checked_catalog_v0()[1]
    true_reference = m.compiled_reference

    def poisoned(cid, case, scheme):
        reference = dict(true_reference(cid, case, scheme))
        reference['canonical_result_sha256'] = 'f' * 64
        return reference

    monkeypatch.setattr(m, 'compiled_reference', poisoned)
    with pytest.raises(AssertionError, match='frozen compiled host differs'):
        m.evaluate_v1b(cid, case, 'single')
