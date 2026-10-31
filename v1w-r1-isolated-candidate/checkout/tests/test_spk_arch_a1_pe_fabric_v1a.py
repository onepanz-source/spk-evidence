"""Pure A1a placement and logical route accounting; no frozen engines."""
from dataclasses import FrozenInstanceError
from dataclasses import replace
import pytest
from spk_architecture_v1.pe_fabric_v1a import (
    SCHEMES, plan_v1a, classify_routes_v1a,
)
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0
from search.spk_24n_independent_oracle_v0 import execute_v0, CaseV0, EdgeV0

SOURCE = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'


def test_original_corpus_is_pinned():
    assert catalog_fingerprint_v0() == SOURCE
    assert len(catalog_v0()) == 216


@pytest.mark.parametrize('scheme', SCHEMES)
def test_total_placement_and_ownership_for_216(scheme):
    cases = catalog_v0()
    for _, case in cases:
        fabric = plan_v1a(case, scheme)
        assert len(fabric.placement) == 3
        assert {p.node_id for p in fabric.placement} == {'A', 'B', 'C'}
        assert {p.pe_id for p in fabric.placement}.issubset(fabric.pe_ids)
        assert len(fabric.static_routes) == len(case.edges)
        assert (fabric.profile()['cross_pe_edges'] +
                fabric.profile()['local_edges'] == len(case.edges))


def test_three_placements_produce_distinct_ownership():
    case = catalog_v0()[0][1]
    fabrics = [plan_v1a(case, scheme) for scheme in SCHEMES]
    assert [len(f.pe_ids) for f in fabrics] == [1, 2, 3]
    assert [tuple(p.pe_id for p in f.placement) for f in fabrics] == [
        ('PE0','PE0','PE0'), ('PE0','PE1','PE1'), ('PE0','PE1','PE2')]


def test_static_cross_pe_parallel_routes_are_not_deduplicated():
    _, case = next((k, v) for k, v in catalog_v0() if '/parallel/' in k)
    spread = plan_v1a(case, 'spread')
    assert len(spread.static_routes) == 3
    assert len({(r.source_node, r.target_node, r.delay_ticks)
                for r in spread.static_routes}) == 2
    assert spread.profile()['cross_pe_edges'] == 3
    assert plan_v1a(case, 'single').profile()['cross_pe_edges'] == 0


def test_observer_route_labels_preserve_primitive_occurrences():
    _, case = next((k, v) for k, v in catalog_v0()
                   if '/parallel/duplicate' in k and k.startswith('relays/'))
    raw = execute_v0(case)['observations']['routes']
    assert len(raw) >= 3
    for scheme in SCHEMES:
        fabric = plan_v1a(case, scheme)
        result = classify_routes_v1a(fabric, raw)
        assert result['occurrences'] == len(raw)
        assert [r['logical'] for r in result['routes']] == raw
        assert (result['cross_pe_occurrences'] +
                result['local_occurrences'] == len(raw))
    assert classify_routes_v1a(plan_v1a(case, 'single'), raw)['cross_pe_occurrences'] == 0
    assert classify_routes_v1a(plan_v1a(case, 'spread'), raw)['cross_pe_occurrences'] == len(raw)


def test_unknown_node_and_scheme_fail_closed():
    case = catalog_v0()[0][1]
    with pytest.raises(ValueError):
        plan_v1a(case, 'unknown')
    with pytest.raises(ValueError, match='unplaced'):
        plan_v1a(case, 'single').owner('D')
    with pytest.raises(ValueError):
        plan_v1a(CaseV0(case.nodes[:-1], (), ()), 'single')


def test_nonpositive_delay_fails_closed():
    case = catalog_v0()[0][1]
    malformed = CaseV0(case.nodes, (EdgeV0('A', 7, 'B', 0, 0),), ())
    with pytest.raises(ValueError, match='delay'):
        plan_v1a(malformed, 'spread')


def test_route_without_static_edge_rejected():
    case = catalog_v0()[0][1]
    route = {'emission_timestamp':0,'source_node':'A','source_channel':7,
             'delivery_timestamp':1,'target_node':'B','target_channel':0,'delay_ticks':1}
    with pytest.raises(ValueError, match='admitted static edge'):
        classify_routes_v1a(plan_v1a(case,'single'), [route])


def test_tampered_route_time_rejected():
    _, case = next((k, v) for k, v in catalog_v0()
                   if '/parallel/duplicate' in k and k.startswith('relays/'))
    entry = dict(execute_v0(case)['observations']['routes'][0])
    entry['delivery_timestamp'] += 1
    with pytest.raises(ValueError, match='logical event timing'):
        classify_routes_v1a(plan_v1a(case,'split'), [entry])


def test_immutable_placement_records():
    item = plan_v1a(catalog_v0()[0][1], 'single').placement[0]
    with pytest.raises(FrozenInstanceError):
        item.pe_id = 'PE1'
