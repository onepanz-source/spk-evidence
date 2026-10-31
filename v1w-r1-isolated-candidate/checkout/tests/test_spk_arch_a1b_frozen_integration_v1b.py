"""Execute the *real* compiled v0 host and new PE-local engine on fwork."""
import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_arch_a1b_pe_local_v1b import (
    evaluate_v1b, report_v1b, seal_v1b, verify_v1b,
)


@pytest.mark.parametrize('scheme', ('single', 'split', 'spread'))
def test_compiled_host_compared_with_real_pe_execution_on_all_216(scheme):
    results = [evaluate_v1b(case_id, case, scheme) for case_id, case in catalog_v0()]
    assert len(results) == 216
    external_events = {cid: len(case.events) for cid, case in catalog_v0()}
    assert all(r['scheme'] == scheme and
               r['processed_events'] == external_events[r['case_id']] +
               r['local_route_occurrences'] + r['cross_pe_route_occurrences']
               for r in results)
    if scheme == 'single':
        assert all(r['cross_pe_route_occurrences'] == 0 for r in results)


def test_full_corpus_report_has_648_compiled_comparisons_and_768_cross_pe_routes():
    payload = report_v1b()
    assert payload['source_cases'] == 216
    assert payload['compiled_host_comparisons'] == 648
    assert payload['cross_pe_route_occurrences'] == 768
    assert len(payload['rows']) == 648
    assert all(len({r['canonical_result_sha256'] for r in payload['rows'][i:i+3]}) == 1
               for i in range(0, len(payload['rows']), 3))


def test_recomputed_hash_forgery_does_not_pass_replay(monkeypatch):
    from search import spk_arch_a1b_pe_local_v1b as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216, 'compiled_host_comparisons': 648,
               'cross_pe_route_occurrences': 768, 'rows': [{'case_id': 'A'}]}
    monkeypatch.setattr(m, 'report_v1b', lambda: fixture)
    doc = m.seal_v1b()
    assert m.verify_v1b(doc)['status'] == 'PASS'
    changed = json.loads(doc)
    changed['payload']['rows'][0]['case_id'] = 'FORGED'
    changed['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(changed['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1b(canonical(changed))


def test_frozen_compilation_mismatch_is_not_silently_accepted(monkeypatch):
    from search import spk_arch_a1b_pe_local_v1b as m
    cid, case = catalog_v0()[0]
    original = m.evaluate_v1a

    def bad(*args, **kwargs):
        value = dict(original(*args, **kwargs))
        value['result_sha256'] = '0'*64
        return value

    monkeypatch.setattr(m, 'evaluate_v1a', bad)
    with pytest.raises(AssertionError, match='PE-local / frozen-host mismatch'):
        m.evaluate_v1b(cid, case, 'single')


def test_evidence_invalid_canonical_text_rejected():
    from search import spk_arch_a1b_pe_local_v1b as m
    with pytest.raises((ValueError, TypeError)):
        m.verify_v1b('{"schema":"x","schema":"x"}')
