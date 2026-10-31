"""Pure A1b engine must not call frozen engines or oracle as its implementation."""
from dataclasses import replace
import pytest

from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.pe_execution_v1b import (
    execute_on_pes_v1b, PEAdmissionErrorV1b, PELimitV1b)
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0
from search.spk_24n_independent_oracle_v0 import execute_v0
from search.spk_24n_differential_evidence_v0 import project_v0

PIN = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'


def projection(result):
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def test_source_identity():
    assert catalog_fingerprint_v0() == PIN
    assert len(catalog_v0()) == 216


@pytest.mark.parametrize('scheme', ['single', 'split', 'spread'])
def test_all_216_against_independent_oracle_and_local_state(scheme):
    for name, case in catalog_v0():
        fab = plan_v1a(case, scheme)
        actual = execute_on_pes_v1b(case, fab)
        oracle = execute_v0(case)
        assert projection(actual['result']) == projection(oracle), (name, scheme)
        assert actual['transport']['cross_pe_occurrences'] + actual['transport']['local_occurrences'] == len(actual['transport']['transfers'])
        assert len(actual['pe_snapshots']) == len(fab.pe_ids)
        assert sum(x['node_count'] for x in actual['pe_snapshots'].values()) == 3
        assert all(x['source_pe'] == fab.owner(x['source_node']) and
                   x['target_pe'] == fab.owner(x['target_node']) for x in actual['transport']['transfers'])
        if scheme == 'single':
            assert actual['transport']['cross_pe_occurrences'] == 0


def test_cross_pe_channel_multiplicity_and_delay():
    name, case = next((n, c) for n, c in catalog_v0()
                      if n.startswith('relays/') and '/parallel/duplicate' in n)
    result = execute_on_pes_v1b(case, plan_v1a(case, 'spread'))
    t = result['transport']['transfers']
    assert len(t) >= 3
    assert all(x['cross_pe'] for x in t)
    assert all(x['delivery_timestamp'] - x['emission_timestamp'] == x['delay_ticks'] for x in t)
    assert len(t) == len(result['result']['observations']['routes'])


def test_reject_mismatched_static_edge_without_starting_execution():
    _, case = next((cid, case) for cid, case in catalog_v0() if case.edges)
    fab = plan_v1a(case, 'split')
    modified = replace(fab, static_routes=fab.static_routes + fab.static_routes[:1])
    with pytest.raises(PEAdmissionErrorV1b, match='routing differs'):
        execute_on_pes_v1b(case, modified)


def test_reject_aliased_placement():
    case = catalog_v0()[0][1]
    fab = plan_v1a(case, 'spread')
    modified = replace(fab, placement=(fab.placement[0],) * 3)
    with pytest.raises(PEAdmissionErrorV1b, match='ownership'):
        execute_on_pes_v1b(case, modified)


def test_reject_inconsistent_pe_route_ownership():
    name, case = next((n, c) for n, c in catalog_v0() if c.edges)
    fab = plan_v1a(case, 'spread')
    altered = replace(fab, static_routes=(replace(fab.static_routes[0],
              source_pe='PE999'),) + fab.static_routes[1:])
    with pytest.raises(PEAdmissionErrorV1b, match='custody'):
        execute_on_pes_v1b(case, altered)


def test_finite_budget_classification():
    name, case = next((n, c) for n, c in catalog_v0()
                      if execute_v0(c)['processed_batches'] > 1 and
                         execute_v0(c)['processed_events'] > 1)
    fab = plan_v1a(case, 'split')
    with pytest.raises(PELimitV1b, match='max_batches'):
        execute_on_pes_v1b(case, fab, max_batches=1)
    with pytest.raises(PELimitV1b, match='max_events'):
        execute_on_pes_v1b(case, fab, max_events=1, max_batches=128)


def test_invalid_limits_fail_closed():
    case = catalog_v0()[0][1]
    fab = plan_v1a(case, 'single')
    for kw in ({'max_events':0}, {'max_batches':0}, {'max_events':True}):
        with pytest.raises(PEAdmissionErrorV1b):
            execute_on_pes_v1b(case, fab, **kw)


def test_engine_has_no_runtime_imports():
    from pathlib import Path
    import spk_architecture_v1.pe_execution_v1b as engine
    text = Path(engine.__file__).read_text()
    for forbidden in ('import spk_network', 'from spk_network', 'import spk_core',
                      'from spk_core', 'import spk_compiler', 'from spk_compiler',
                      'execute_v0(', 'execute_manifest_v0('):
        assert forbidden not in text
