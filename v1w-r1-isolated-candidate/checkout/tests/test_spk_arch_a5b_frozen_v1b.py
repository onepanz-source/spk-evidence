"""Real frozen Compiler witnesses and A5a committed predecessor scope."""
import json
from dataclasses import replace
from pathlib import Path
import pytest
from search.spk_24n_differential_evidence_v0 import sha, canonical
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3b_causal_service_conformance_v1b import compiled_reference, projected_hash
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a
from search import spk_arch_a5b_conformance_v1b as m
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d


def test_a5a_seventeen_phase_git_provenance():
    r=m.predecessor_v1b(Path.cwd())
    assert r['predecessor_phases']==17 and r['predecessor_files']==103
    assert r['a5a_recorded_evidence_sha256']==m.A5A_EVIDENCE


@pytest.mark.parametrize('scheme',SCHEMES)
def test_108_metamorphic_source_witnesses_match_frozen_compiler(scheme):
    catalog=checked_catalog_v0()
    for i in sampled_indices_v1a():
        cid,case=catalog[i]
        reference=compiled_reference(cid,case,scheme)
        args=m.ideal_args_v1b(case,scheme,256)
        zero=args[:2]+(replace(args[2],cross_pe_extra_ticks=0),)+args[3:]
        output=execute_causal_transport_v1d(*zero)
        assert projected_hash(output['result'])==reference['canonical_result_sha256']
        assert m.conservation_v1b(output,len(case.events))==output['transport']['cross_pe_occurrences']


def tiny_report():
    return {'schema':m.SCHEMA,'source_cases':216,'metamorphic_witnesses':648,
            'nonbinding_expansion_witnesses':648,'single_pe_remote_inert_witnesses':216,
            'cross_pe_occurrences':2,'predecessor':{'predecessor_phases':17},
            'rows':[{'id':'before'}]}


def test_recomputed_forgery_is_rejected_even_when_checksum_valid(monkeypatch):
    monkeypatch.setattr(m,'report_v1b',lambda root:tiny_report())
    root=Path.cwd()
    doc=m.seal_v1b(root)
    assert m.verify_v1b(doc,root)['status']=='PASS'
    fake=json.loads(doc)
    fake['payload']['rows'][0]['id']='altered'
    fake['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(fake['payload']))
    with pytest.raises(ValueError,match='independent replay mismatch'):
        m.verify_v1b(canonical(fake),root)
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1b(doc+'\n',root)
    fake=json.loads(doc)
    fake['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1b(canonical(fake),root)
