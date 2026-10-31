"""A4c real Compiler/host dual-witness cold promotion and replay controls."""
from dataclasses import replace
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4c_candidate_conformance_v1c import (
    SOURCE_SHA256, promotion_case_v1c,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme', SCHEMES)
def test_216_real_changed_candidates_have_compiler_and_mode_witness(scheme):
    catalog = checked_catalog_v0()
    for i, (cid, case) in enumerate(catalog):
        other_id, other_case = catalog[(i+36) % len(catalog)]
        row = promotion_case_v1c(cid, case, other_id, other_case, scheme,
                                 'TRAINING' if i%2 == 0 else 'REMODEL')
        assert row['from_context_sha256'] != row['to_context_sha256']
        assert row['revision'] == 1
        assert len(row['candidate_ideal_sha256']) == 64
        assert len(row['cold_result_sha256']) == 64


def test_frozen_source_unchanged():
    assert catalog_fingerprint_v0() == SOURCE_SHA256


def _fixture(m):
    return {'schema':m.SCHEMA,'source_cases':216,
            'compiled_baseline_witnesses':648,'compiled_candidate_witnesses':648,
            'independent_candidate_verifications':648,'explicit_promotions':648,
            'cold_executions':648,'rows':[{'id':'fixture'}]}


def test_recomputed_digest_cannot_forge_replay(monkeypatch):
    from search import spk_arch_a4c_candidate_conformance_v1c as m
    monkeypatch.setattr(m, 'report_v1c', lambda: _fixture(m))
    document=m.seal_v1c()
    assert m.verify_v1c(document)['status']=='PASS'
    forged=json.loads(document)
    forged['payload']['rows'][0]['id']='fraud'
    forged['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(forged['payload']))
    with pytest.raises(ValueError,match='semantic replay mismatch'):
        m.verify_v1c(canonical(forged))


def test_noncanonical_and_bad_checksum_rejected(monkeypatch):
    from search import spk_arch_a4c_candidate_conformance_v1c as m
    monkeypatch.setattr(m, 'report_v1c', lambda: _fixture(m))
    doc=m.seal_v1c()
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1c(doc+'\n')
    bad=json.loads(doc)
    bad['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1c(canonical(bad))


def test_forged_candidate_compiled_result_denied(monkeypatch):
    from search import spk_arch_a4c_candidate_conformance_v1c as m
    catalog=checked_catalog_v0()
    id0,case0=catalog[20]
    id1,case1=catalog[56]
    real=m.compiled_reference
    def tamper(*args):
        out=dict(real(*args))
        out['canonical_result_sha256']='f'*64
        return out
    monkeypatch.setattr(m,'compiled_reference',tamper)
    with pytest.raises(AssertionError,match='ideal PE differ'):
        m.promotion_case_v1c(id0,case0,id1,case1,'spread','TRAINING')


def test_false_a4b_baseline_provenance_denied(monkeypatch):
    from search import spk_arch_a4c_candidate_conformance_v1c as m
    id0,case0=checked_catalog_v0()[20]
    id1,case1=checked_catalog_v0()[56]
    real=m.mode_memory_case_v1b
    def bad(*args):
        output=dict(real(*args))
        output['execute_priority']=['P','E','S','O']
        return output
    monkeypatch.setattr(m,'mode_memory_case_v1b',bad)
    with pytest.raises(AssertionError,match='baseline authority'):
        m.promotion_case_v1c(id0,case0,id1,case1,'spread','TRAINING')
