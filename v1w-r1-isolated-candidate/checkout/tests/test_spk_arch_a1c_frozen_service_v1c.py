"""A1c resource service must preserve each independently compiled host result."""
import json

import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_arch_a1c_service_conformance_v1c import (
    evaluate_v1c, report_v1c, seal_v1c, verify_v1c, REGIMES,
)


@pytest.mark.parametrize('scheme', ('single', 'split', 'spread'))
def test_216_source_cases_frozen_compiler_host_and_four_resource_regimes(scheme):
    records = [evaluate_v1c(cid, case, scheme) for cid, case in catalog_v0()]
    assert len(records) == 216
    for record in records:
        assert len(record['service_regimes']) == 4
        assert tuple(v['regime'] for v in record['service_regimes']) == REGIMES
        assert len({v['result_sha256'] for v in record['service_regimes']}) == 1
        assert record['service_regimes'][-1]['service_wait_ticks'] == 0


def test_report_all_648_compiled_refs_and_2592_capacity_executions():
    report = report_v1c()
    assert report['source_cases'] == 216
    assert report['compiled_reference_comparisons'] == 648
    assert report['pe_service_executions'] == 2592
    assert len(report['rows']) == 648
    assert report['regime_totals']['pe_limited']['pe_stalls'] > 0
    assert report['regime_totals']['shared_limited']['fabric_stalls'] > 0
    assert report['regime_totals']['unconstrained'] == {
        'fabric_stalls': 0, 'pe_stalls': 0, 'service_wait_ticks': 0}


def test_forged_payload_even_resealed_is_rejected_by_full_reexecution(monkeypatch):
    from search import spk_arch_a1c_service_conformance_v1c as m
    fake = {'schema': m.SCHEMA, 'source_cases': 216,
            'compiled_reference_comparisons': 648,
            'pe_service_executions': 2592,
            'regime_totals': {}, 'rows': [{'case_id': 'A'}]}
    monkeypatch.setattr(m, 'report_v1c', lambda: fake)
    document = m.seal_v1c()
    assert m.verify_v1c(document)['status'] == 'PASS'
    modified = json.loads(document)
    modified['payload']['rows'][0]['case_id'] = 'FORGED'
    modified['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(modified['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1c(canonical(modified))


def test_host_digest_mutation_is_not_ignored(monkeypatch):
    from search import spk_arch_a1c_service_conformance_v1c as m
    cid, case = catalog_v0()[0]
    old = m.reference_v1b

    def forged(*args):
        record = dict(old(*args))
        record['canonical_result_sha256'] = '0' * 64
        return record

    monkeypatch.setattr(m, 'reference_v1b', forged)
    with pytest.raises(AssertionError, match='PE service changed logical computation'):
        m.evaluate_v1c(cid, case, 'single')


def test_compilation_failure_cannot_be_reclassified_as_valid(monkeypatch):
    from search import spk_arch_a1c_service_conformance_v1c as m
    cid, case = catalog_v0()[0]

    def reject(*args):
        raise ValueError('Compiler rejected source')

    monkeypatch.setattr(m, 'reference_v1b', reject)
    with pytest.raises(ValueError, match='Compiler rejected source'):
        m.evaluate_v1c(cid, case, 'single')


def test_noncanonical_evidence_is_rejected():
    with pytest.raises((ValueError, TypeError)):
        verify_v1c('{"schema":"x","schema":"x"}')
