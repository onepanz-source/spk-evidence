"""A2d real frozen Compiler/host witness and canonical resource-failure replay."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2d_exhaustion_conformance_v1d import (
    SOURCE_SHA256, evaluate_v1d, seal_v1d, verify_v1d,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_full_compiled_corpus_memory_failure_adjudication(scheme):
    count = faults = denials = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1d(cid, case, scheme)
        assert row['manifest_sha256']
        assert row['exact_service_sha256']
        assert set(row['admission_rejections']) == {'P','S','E','O'}
        assert row['nominal_execution_status'] == 'CLOSED'
        if row['short'] is not None:
            assert row['short']['complete_service'] is None
        faults += row['fault'] is not None
        denials += len(row['admission_rejections'])
        count += 1
    assert (count, faults, denials) == (216, 168, 864)


def test_source_catalog_is_pinned():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_resealed_resource_evidence_cannot_replace_full_replay(monkeypatch):
    from search import spk_arch_a2d_exhaustion_conformance_v1d as m
    fixture = {'schema': m.SCHEMA, 'source_cases':216,
               'compiled_host_comparisons':648,
               'capacity_admission_rejections':2592,
               'nominal_service_exact_passes':648,
               'nominal_service_short_failures':500,
               'fault_prefix_exact_passes':504,
               'fault_prefix_short_failures':400,
               'short_budget_nonprobeable':252,
               'rows':[{'id':'fixture','required_service_ticks':2}]}
    monkeypatch.setattr(m, 'report_v1d', lambda: fixture)
    doc = m.seal_v1d()
    assert m.verify_v1d(doc)['status'] == 'PASS'
    fake = json.loads(doc)
    fake['payload']['rows'][0]['required_service_ticks'] = 1
    fake['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(fake['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1d(canonical(fake))


def test_noncanonical_receipt_is_rejected(monkeypatch):
    from search import spk_arch_a2d_exhaustion_conformance_v1d as m
    monkeypatch.setattr(m, 'report_v1d', lambda: {'schema':m.SCHEMA})
    doc = m.seal_v1d()
    with pytest.raises(ValueError, match='noncanonical'):
        m.verify_v1d(doc + '\n')


def test_payload_checksum_mismatch_is_rejected(monkeypatch):
    from search import spk_arch_a2d_exhaustion_conformance_v1d as m
    monkeypatch.setattr(m, 'report_v1d', lambda: {'schema':m.SCHEMA})
    fake = json.loads(m.seal_v1d())
    fake['payload_sha256'] = 'f'*64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1d(canonical(fake))
