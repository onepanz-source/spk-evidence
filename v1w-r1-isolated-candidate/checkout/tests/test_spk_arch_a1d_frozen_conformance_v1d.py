"""Real frozen Compiler/host integration and replayable A1d fail-stop witnesses."""
import json

import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_arch_a1d_fault_conformance_v1d import (
    evaluate_v1d, report_v1d, seal_v1d, verify_v1d, SCHEMA, REGIMES,
)


@pytest.mark.parametrize('scheme', ('single', 'split', 'spread'))
def test_compiled_reference_and_failstop_across_all_216_cases(scheme):
    rows = [evaluate_v1d(cid, case, scheme) for cid, case in catalog_v0()]
    assert len(rows) == 216
    assert all(tuple(v['regime'] for v in row['regimes']) == REGIMES for row in rows)
    assert sum(v['fault'] is not None for row in rows for v in row['regimes']) > 200


def test_complete_compiled_report_and_failstop_counts():
    result = report_v1d()
    assert len(result['rows']) == 648
    assert result['nominal_service_executions'] == 1296
    assert result['eligible_fault_executions'] > 600
    assert result['cross_pe_route_occurrences'] == 768


def test_resigned_forged_witness_is_rejected_by_full_reexecution(monkeypatch):
    from search import spk_arch_a1d_fault_conformance_v1d as m
    fixture = {'schema': SCHEMA, 'source_cases': 216,
               'compiled_reference_comparisons': 648,
               'nominal_service_executions': 1296,
               'eligible_fault_executions': 1008,
               'rows': [{'case_id': 'A'}]}
    monkeypatch.setattr(m, 'report_v1d', lambda: fixture)
    doc = m.seal_v1d()
    assert m.verify_v1d(doc)['status'] == 'PASS'
    altered = json.loads(doc)
    altered['payload']['rows'][0]['case_id'] = 'COUNTERFEIT'
    altered['payload_sha256'] = sha(SCHEMA + '\n' + canonical(altered['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        m.verify_v1d(canonical(altered))


def test_broken_compiled_host_is_not_treated_as_acceptable(monkeypatch):
    from search import spk_arch_a1d_fault_conformance_v1d as m
    case_id, case = catalog_v0()[0]
    old = m.compiled_reference
    def forged(*args):
        result = dict(old(*args))
        result['canonical_result_sha256'] = '0' * 64
        return result
    monkeypatch.setattr(m, 'compiled_reference', forged)
    with pytest.raises(AssertionError, match='A1c/frozen mismatch'):
        m.evaluate_v1d(case_id, case, 'single')


def test_compilation_rejection_is_not_silently_excluded(monkeypatch):
    from search import spk_arch_a1d_fault_conformance_v1d as m
    case_id, case = catalog_v0()[0]
    def refuse(*args):
        raise ValueError('frozen compiler rejected source')
    monkeypatch.setattr(m, 'compiled_reference', refuse)
    with pytest.raises(ValueError, match='frozen compiler rejected'):
        m.evaluate_v1d(case_id, case, 'spread')
