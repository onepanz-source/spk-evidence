"""Runs on fwork: real frozen Compiler/PE admission/manifest/host."""
import json
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_arch_a1_pe_fabric_v1a import (
    SCHEMES, evaluate_v1a, seal_v1a, verify_v1a, report_v1a,
)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_all_216_compiled_cases_per_placement(scheme):
    rows = [evaluate_v1a(cid, case, scheme) for cid, case in catalog_v0()]
    assert len(rows) == 216
    assert all(r['scheme'] == scheme and r['profile']['node_count'] == 3
               for r in rows)
    if scheme == 'single':
        assert all(r['profile']['cross_pe_edges'] == 0 for r in rows)


def test_pairwise_result_equivalence_on_multipe_reference():
    for cid, case in catalog_v0()[::6]:  # one case per profile/graph group
        results = [evaluate_v1a(cid, case, scheme) for scheme in SCHEMES]
        assert len({r['result_sha256'] for r in results}) == 1
        assert all(r['logical_route_count'] == results[0]['logical_route_count']
                   for r in results)


def test_full_648_case_report_structure():
    payload = report_v1a()
    assert payload['source_cases'] == 216
    assert payload['compiled_runs'] == 648
    assert len(payload['rows']) == 648
    assert payload['baseline_commit'] == 'a76ebaae49373a4c6b66f94465d78dbf1cf19f80'
    assert payload['cross_pe_route_occurrences'] >= 0


def test_forged_evidence_even_with_recomputed_digest_is_rejected(monkeypatch):
    # Small local replay fixture; full evidence canonical replay is performed
    # separately by the shell gate to avoid rerunning all 648 just for forgery.
    from search import spk_arch_a1_pe_fabric_v1a as m
    fixture = {'schema': m.SCHEMA, 'source_cases':216, 'compiled_runs':648,
               'cross_pe_route_occurrences':0, 'rows':[{'id':'A'}]}
    monkeypatch.setattr(m, 'report_v1a', lambda: fixture)
    doc = m.seal_v1a()
    assert m.verify_v1a(doc)['status'] == 'PASS'
    forged = json.loads(doc)
    forged['payload']['rows'][0]['id'] = 'FORGED'
    forged['payload_sha256'] = sha(m.SCHEMA + '\n' + canonical(forged['payload']))
    with pytest.raises(ValueError, match='replay'):
        m.verify_v1a(canonical(forged))


def test_underprovisioned_frozen_pe_rejected_before_execution():
    from search.spk_24o_extended_differential_v0 import to_frozen_v0
    from spk_architecture.profile_v0 import ProcessingElementV0, ArchitectureProfileV0
    from spk_compiler.network_ir_v0 import dumps_network_ir_v0
    from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
    from spk_compiler.resource_admission_v0 import ResourceProfileV0
    from spk_compiler.pe_admission_v0 import NodePlacementV0, PEAdmissionRejectedV0
    case = catalog_v0()[0][1]
    network, events = to_frozen_v0(case)
    pe = ProcessingElementV0(
        pe_id='PE0', program_slots=0, state_slots=0, event_slots=64,
        output_slots=64, observation_slots=64, accesses_per_service_tick=8)
    arch = ArchitectureProfileV0('spk-architecture-a1-negative', (pe,))
    with pytest.raises(PEAdmissionRejectedV0):
        compile_network_ir_v0(
            network_ir_json=dumps_network_ir_v0(network), initial_events=events,
            resource_profile=ResourceProfileV0(), architecture=arch,
            placements=tuple(NodePlacementV0(n.node_id, 'PE0') for n in case.nodes))
