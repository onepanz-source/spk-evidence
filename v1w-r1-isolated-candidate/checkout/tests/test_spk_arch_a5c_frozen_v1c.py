"""A5c trusted Compiler/host witnesses and committed predecessor custody."""
import json
from dataclasses import replace
from pathlib import Path
import pytest
from search.spk_24n_differential_evidence_v0 import canonical,sha
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3b_causal_service_conformance_v1b import compiled_reference,projected_hash
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a
from search.spk_arch_a5b_conformance_v1b import ideal_args_v1b
from search import spk_arch_a5c_adversarial_conformance_v1c as m
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d


def test_eighteen_predecessor_phases_committed():
    result=m.predecessor_v1c(Path.cwd())
    assert result['predecessor_phases']==18 and result['predecessor_files']==109
    assert result['a5b_recorded_evidence_sha256']==m.A5B_EVIDENCE


@pytest.mark.parametrize('scheme',SCHEMES)
def test_108_independent_frozen_host_witnesses_still_match_ideal_a3d(scheme):
    catalog=checked_catalog_v0()
    for index in sampled_indices_v1a():
        cid,case=catalog[index]
        compiled=compiled_reference(cid,case,scheme)
        args=ideal_args_v1b(case,scheme,256)
        ideal=args[:2]+(replace(args[2],cross_pe_extra_ticks=0),)+args[3:]
        actual=execute_causal_transport_v1d(*ideal)
        assert projected_hash(actual['result'])==compiled['canonical_result_sha256']


def tiny_report():
    return {'schema':m.SCHEMA,'source_cases':216,'adversarial_runs':648,
            'cross_context_denials':648,'staging_execution_denials':648,
            'failed_replay_faults':648,'event_custody_tamper_denials':648,
            'fully_rehashed_snapshot_replay_denials':108,
            'predecessor':{'predecessor_phases':18},'rows':[{'id':'prior'}]}


def test_validly_rehashed_evidence_forgery_rejected_by_full_source_replay(monkeypatch):
    monkeypatch.setattr(m,'report_v1c',lambda root:tiny_report())
    root=Path.cwd()
    sealed=m.seal_v1c(root)
    assert m.verify_v1c(sealed,root)['status']=='PASS'
    altered=json.loads(sealed)
    altered['payload']['rows'][0]['id']='forged'
    altered['payload_sha256']=sha(m.SCHEMA+'\n'+canonical(altered['payload']))
    with pytest.raises(ValueError,match='independent replay mismatch'):
        m.verify_v1c(canonical(altered),root)
    with pytest.raises(ValueError,match='noncanonical'):
        m.verify_v1c(sealed+'\n',root)
    altered=json.loads(sealed)
    altered['payload_sha256']='0'*64
    with pytest.raises(ValueError,match='checksum mismatch'):
        m.verify_v1c(canonical(altered),root)
