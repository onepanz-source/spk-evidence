"""A3c integration checks require the REAL frozen Compiler and host.

No simulated backend is injected into these tests. Each scheme replays all 216
source cases; full canonical evidence is additionally replayed by shell gate.
"""
import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import (
    execute_causal_service_v1b, uniform_causal_service_plan_v1b,
)
from spk_architecture_v1.causal_memory_v1c import (
    uniform_causal_memory_plan_v1c, execute_causal_memory_v1c,
)
from search.spk_arch_a3c_memory_timing_conformance_v1c import (
    SOURCE_SHA256, evaluate_v1c, projected_hash,
)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_frozen_compiler_and_real_causal_memory_differential(scheme):
    changed = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1c(cid, case, scheme)
        assert len(row['runs']) == 4
        assert all(not r['changed_from_a3b'] for r in row['runs']
                   if r['mode'] == 'ideal')
        changed += sum(r['changed_from_a3b'] for r in row['runs']
                       if r['mode'] == 'memory_limited')
    assert changed > 0


def test_pinned_corpus_fingerprint():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_memory_quota_does_not_mutate_frozen_compiler_reference():
    cid, case = checked_catalog_v0()[3]
    from search.spk_arch_a3b_causal_service_conformance_v1b import compiled_reference
    frozen = compiled_reference(cid, case, 'spread')
    fabric = plan_v1a(case, 'spread')
    pe = uniform_causal_service_plan_v1b(fabric, pe_slots=128, fabric_slots_per_tick=128)
    actual = execute_causal_memory_v1c(
        case, fabric, TransportPlanV1a(0), pe,
        uniform_causal_memory_plan_v1c(fabric))
    assert projected_hash(actual['result']) == frozen['canonical_result_sha256']


def test_forged_rehashed_receipt_rejected(monkeypatch):
    from search import spk_arch_a3c_memory_timing_conformance_v1c as m
    fixture = {'schema': m.SCHEMA, 'compiled_host_comparisons': 648,
               'a3b_ideal_comparisons': 1296, 'causal_memory_executions': 2592,
               'totals': {'memory_limited': {'changed_from_a3b': 1}},
               'rows': [{'id': 'synthetic'}]}
    monkeypatch.setattr(m, 'report_v1c', lambda: fixture)
    doc = m.seal_v1c()
    assert m.verify_v1c(doc)['status'] == 'PASS'
    changed = json.loads(doc)
    changed['payload']['rows'][0]['id'] = 'forged'
    changed['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(changed['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1c(canonical(changed))


def test_noncanonical_and_wrong_checksum_rejected(monkeypatch):
    from search import spk_arch_a3c_memory_timing_conformance_v1c as m
    fixture = {'schema': m.SCHEMA, 'compiled_host_comparisons': 648,
               'a3b_ideal_comparisons': 1296, 'causal_memory_executions': 2592,
               'totals': {'memory_limited': {'changed_from_a3b': 1}}, 'rows': []}
    monkeypatch.setattr(m, 'report_v1c', lambda: fixture)
    doc = m.seal_v1c()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1c(doc + '\n')
    bad = json.loads(doc)
    bad['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1c(canonical(bad))


def test_compiler_forgery_not_hidden(monkeypatch):
    from search import spk_arch_a3c_memory_timing_conformance_v1c as m
    cid, case = checked_catalog_v0()[2]
    original = m.compiled_reference

    def forged(*args):
        doc = dict(original(*args))
        doc['canonical_result_sha256'] = 'f' * 64
        return doc

    monkeypatch.setattr(m, 'compiled_reference', forged)
    with pytest.raises(AssertionError, match='frozen compiled host differs'):
        m.evaluate_v1c(cid, case, 'single')
