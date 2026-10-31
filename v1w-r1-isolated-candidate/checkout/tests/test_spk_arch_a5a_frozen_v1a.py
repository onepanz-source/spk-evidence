"""Full architectural vertical witness on bounded stratified frozen source."""
import json
from pathlib import Path
import pytest
from search.spk_24n_differential_evidence_v0 import sha, canonical
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.conformance_inventory_v1a import CORPUS_SHA256,PHASES,manifest_v1a
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from search import spk_arch_a5a_conformance_v1a as m


def test_prior_committed_16_phase_git_inventory():
    doc=manifest_v1a(Path(__file__).resolve().parents[1])
    assert doc['phase_count']==16 and doc['tracked_source_files']==97
    assert catalog_fingerprint_v0()==CORPUS_SHA256
    assert all(p['reported_gate_evidence_sha256']==PHASES[p['phase']][0]
               for p in doc['phases'])


def test_sample_stratification_exact():
    indices=m.sampled_indices_v1a()
    assert len(indices)==36 and len(set(indices))==36
    assert {(i//36,(i%36)//6) for i in indices}=={
        (p,g) for p in range(6) for g in range(6)}
    assert {i%6 for i in indices}==set(range(6))


@pytest.mark.parametrize('scheme',SCHEMES)
def test_real_frozen_compiler_a3d_direct_and_a4d_custody_witnesses(scheme):
    cases=checked_catalog_v0()
    for i in m.sampled_indices_v1a():
        row=m.cross_witness_v1a(cases,i,scheme)
        assert row['scheme']==scheme and row['source_checkpoint_sha256']
        assert row['recovery_sha256'] and row['cold_activation_sha256']
        assert row['baseline_manifest_sha256']!=row['candidate_manifest_sha256']


def fake_report():
    return {'schema':m.SCHEMA,'prior_phases':16,'prior_source_files':97,
            'sampled_cases':36,'cross_layer_witnesses':108,'rows':[{'id':'test'}]}


def test_canonical_digest_and_recomputed_forgery_rejected(monkeypatch):
    monkeypatch.setattr(m,'report_v1a',lambda root:fake_report())
    root=Path.cwd()
    doc=m.seal_v1a(root)
    assert m.verify_v1a(doc,root)['status']=='PASS'
    altered=json.loads(doc);altered['payload']['rows'][0]['id']='forged'
    altered['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(altered['payload']))
    with pytest.raises(ValueError,match='independent replay mismatch'):
        m.verify_v1a(canonical(altered),root)
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1a(doc+'\n',root)
    altered=json.loads(doc);altered['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1a(canonical(altered),root)
