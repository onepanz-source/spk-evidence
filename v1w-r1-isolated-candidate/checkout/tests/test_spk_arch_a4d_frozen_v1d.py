"""A4d real Compiler/host dual witnesses, state custody and sealed replay."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a4d_custody_conformance_v1d import (
    SOURCE_SHA256, custody_case_v1d,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES


@pytest.mark.parametrize('scheme',SCHEMES)
def test_216_real_compiler_witnesses_and_quiescent_custody(scheme):
    catalog=checked_catalog_v0()
    for i,(cid,case) in enumerate(catalog):
        target_id,target_case=catalog[(i+36)%216]
        row=custody_case_v1d(cid,case,target_id,target_case,scheme,
                             'TRAINING' if i%2==0 else 'REMODEL')
        assert row['revision']==1
        assert row['source_context_sha256']!=row['target_context_sha256']
        assert row['snapshot_sha256'] and row['cold_activation_sha256']


def test_source_catalog_is_exact_frozen_source():
    assert catalog_fingerprint_v0()==SOURCE_SHA256


def fake(m):
    return {'schema':m.SCHEMA, 'source_cases':216,
            'frozen_baseline_witnesses':648,
            'frozen_candidate_witnesses':648,
            'closed_state_snapshots':648,
            'same_context_replay_recoveries':648,
            'stale_revision_recovery_denials':648,
            'cold_reset_activations':648,
            'rows':[{'id':'fixture'}]}


def test_recomputed_checksum_cannot_forge_semantic_replay(monkeypatch):
    from search import spk_arch_a4d_custody_conformance_v1d as m
    monkeypatch.setattr(m,'report_v1d',lambda:fake(m))
    doc=m.seal_v1d()
    assert m.verify_v1d(doc)['status']=='PASS'
    forged=json.loads(doc)
    forged['payload']['rows'][0]['id']='forged'
    forged['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(forged['payload']))
    with pytest.raises(ValueError,match='full replay mismatch'):
        m.verify_v1d(canonical(forged))


def test_wrong_checksum_and_noncanonical_serialization_are_denied(monkeypatch):
    from search import spk_arch_a4d_custody_conformance_v1d as m
    monkeypatch.setattr(m,'report_v1d',lambda:fake(m))
    doc=m.seal_v1d()
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1d(doc+'\n')
    corrupt=json.loads(doc);corrupt['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1d(canonical(corrupt))


def test_forged_candidate_ideal_compiler_witness_rejected(monkeypatch):
    from search import spk_arch_a4d_custody_conformance_v1d as m
    cid,case=checked_catalog_v0()[20]
    tid,target=checked_catalog_v0()[56]
    actual=m.compiled_reference
    def wrong(*a):
        witness=dict(actual(*a))
        witness['canonical_result_sha256']='f'*64
        return witness
    monkeypatch.setattr(m,'compiled_reference',wrong)
    with pytest.raises(AssertionError,match='semantic provenance'):
        m.custody_case_v1d(cid,case,tid,target,'spread','TRAINING')


def test_forged_a4b_mode_authority_rejected(monkeypatch):
    from search import spk_arch_a4d_custody_conformance_v1d as m
    cid,case=checked_catalog_v0()[20]
    tid,target=checked_catalog_v0()[56]
    actual=m.mode_memory_case_v1b
    def wrong(*a):
        authority=dict(actual(*a))
        authority['execute_priority']=['O','P','S','E']
        return authority
    monkeypatch.setattr(m,'mode_memory_case_v1b',wrong)
    with pytest.raises(AssertionError,match='semantic provenance'):
        m.custody_case_v1d(cid,case,tid,target,'spread','TRAINING')
