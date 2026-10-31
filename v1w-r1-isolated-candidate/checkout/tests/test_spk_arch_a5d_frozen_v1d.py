"""A5d newly replayed cross-layer Compiler, temporal and custody witnesses."""
import json
from pathlib import Path
import pytest
from search.spk_24n_differential_evidence_v0 import canonical,sha
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.release_conformance_v1d import release_committed_v1d
from search import spk_arch_a5d_release_evidence_v1d as m


def test_frozen_source_and_nineteen_prior_certifications():
    inv=release_committed_v1d(Path.cwd())
    assert inv['predecessor_phases']==19 and inv['source_files']==121


@pytest.mark.parametrize('scheme',SCHEMES)
def test_new_full_vertical_metamorphic_adversarial_witnesses(scheme):
    from search.spk_arch_a5a_conformance_v1a import cross_witness_v1a
    from search.spk_arch_a5b_conformance_v1b import metamorphic_case_v1b
    from spk_architecture_v1.adversarial_boundaries_v1c import adversarial_case_v1c
    cases=checked_catalog_v0()
    for i in sampled_indices_v1a():
        cid,case=cases[i]
        x=cross_witness_v1a(cases,i,scheme)
        y=metamorphic_case_v1b(cid,case,scheme)
        z=adversarial_case_v1c(cid,case,scheme)
        assert x['id']==y['id']==z['id']==cid
        assert x['scheme']==y['scheme']==z['scheme']==scheme
        assert x['recovery_sha256'] and x['cold_activation_sha256']
        assert y['original_context_sha256']!=y['renamed_context_sha256']
        assert z['forged_custody_denied'] and z['failed_verify_faulted']


def tiny_report():
    return {'schema':m.SCHEMA,'release':{'head_commit':'0'*40,
        'predecessor_phases':19,'source_files':121},
        'rows':[{'source_id':'one','scheme':'single'}]}


def test_validly_rehashed_forgery_rejected_by_independent_replay(monkeypatch):
    monkeypatch.setattr(m,'report_v1d',lambda root:tiny_report())
    root=Path.cwd()
    receipt=m.seal_v1d(root)
    assert m.verify_v1d(receipt,root)['status']=='PASS'
    fake=json.loads(receipt)
    fake['payload']['rows'][0]['source_id']='other'
    fake['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(fake['payload']))
    with pytest.raises(ValueError,match='independent checkout replay mismatch'):
        m.verify_v1d(canonical(fake),root)
    fake=json.loads(receipt)
    fake['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1d(canonical(fake),root)
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1d(receipt+'\n',root)
