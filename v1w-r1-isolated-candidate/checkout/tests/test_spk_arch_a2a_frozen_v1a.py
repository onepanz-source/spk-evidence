import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2a_memory_conformance_v1a import (
    SOURCE_SHA256, evaluate_v1a, seal_v1a, verify_v1a,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_216_compiled_memory_projections_per_scheme(scheme):
    n = 0
    for cid, case in checked_catalog_v0():
        row = evaluate_v1a(cid, case, scheme)
        assert row['manifest_sha256']
        assert row['memory_reservation_sha256']
        assert row['memory_projection_sha256']
        n += 1
    assert n == 216


def test_real_corpus_source_pin():
    from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def test_authentic_evidence_replay(monkeypatch):
    # This small fixture tests the exact replay protocol without rerunning
    # all 648 frozen Compiler calls. Shell gate does the full replay.
    from search import spk_arch_a2a_memory_conformance_v1a as m
    fixture = {'schema': m.SCHEMA, 'source_cases': 216,
               'rows': [{'id': 'one'}]}
    monkeypatch.setattr(m, 'report_v1a', lambda: fixture)
    doc = m.seal_v1a()
    assert m.verify_v1a(doc)['status'] == 'PASS'
    obj = json.loads(doc)
    obj['payload']['rows'][0]['id'] = 'forged'
    obj['payload_sha256'] = sha(m.SCHEMA+'\n'+canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1a(canonical(obj))


def test_hash_mismatch_rejected(monkeypatch):
    from search import spk_arch_a2a_memory_conformance_v1a as m
    monkeypatch.setattr(m, 'report_v1a', lambda: {'schema':m.SCHEMA,'rows':[]})
    obj=json.loads(m.seal_v1a())
    obj['payload_sha256']='0'*64
    with pytest.raises(ValueError, match='checksum'):
        m.verify_v1a(canonical(obj))
