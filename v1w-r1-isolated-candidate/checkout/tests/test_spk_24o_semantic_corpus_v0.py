"""24o pure algebra/operational/metamorphic tests. No frozen SPK imports."""
from dataclasses import replace
from itertools import product

import pytest

from search.spk_24n_independent_oracle_v0 import (
    CaseV0, EdgeV0, EventV0, NodeV0, OracleDomainErrorV0,
    OracleLimitV0, execute_v0, relay_path_support_v0,
)
from search.spk_24o_semantic_corpus_v0 import (
    RELAY, PROFILES, GRAPHS, INPUTS, catalog_v0,
    catalog_fingerprint_v0, corpus_v0, relay_time_translation_v0,
)

CASES = catalog_v0()


def test_catalog_identity_and_versioned_fingerprint():
    assert len(CASES) == 216
    assert len(set(name for name, _ in CASES)) == 216
    assert catalog_fingerprint_v0() == 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
    assert tuple(corpus_v0()) == CASES


@pytest.mark.parametrize('pname', [x[0] for x in PROFILES])
def test_entire_profile_semantics_inside_declared_success_domain(pname):
    seen = 0
    for name, case in CASES:
        if not name.startswith(pname + '/'):
            continue
        result = execute_v0(case)
        assert result['processed_events'] >= len(case.events), name
        assert result['processed_batches'] <= result['processed_events'], name
        assert len(result['states']) == 3, name
        assert all(0 <= s['raw'] <= 255 for s in result['states']), name
        assert len(result['observations']['batches']) == result['processed_batches'], name
        seen += 1
    assert seen == 36


@pytest.mark.parametrize('graph', [x[0] for x in GRAPHS])
def test_input_order_permutation_cannot_change_execution(graph):
    seen = 0
    for name, case in CASES:
        if '/'+graph+'/' not in name:
            continue
        assert execute_v0(case) == execute_v0(replace(case, events=tuple(reversed(case.events)))), name
        seen += 1
    assert seen == 36


@pytest.mark.parametrize('graph_info', GRAPHS, ids=[g[0] for g in GRAPHS])
def test_relay_translation_covariance_for_each_dag(graph_info):
    _, graph = graph_info
    nodes = tuple(NodeV0(n, 8, 0, 0, RELAY) for n in 'ABC')
    edges = tuple(EdgeV0(src, 7, target, 0, delay) for src,target,delay in graph)
    for _, events in INPUTS:
        original = CaseV0(nodes, edges, tuple(EventV0(*e) for e in events))
        moved = relay_time_translation_v0(original, 11)
        old = execute_v0(original)
        new = execute_v0(moved)
        assert new['processed_events'] == old['processed_events']
        assert new['processed_batches'] == old['processed_batches']
        for category in ('emissions','terminal_outputs'):
            assert [{**e, 'timestamp':e['timestamp']+11} for e in old[category]] == new[category]
        # This check is distinct from event-queue simulation: path-delay support.
        if all(e.channel == 0 for e in original.events):
            support = relay_path_support_v0(original)
            shifted_support = relay_path_support_v0(moved)
            assert shifted_support == {n:tuple(t+11 for t in s) for n,s in support.items()}


def test_zero_event_case_never_invents_activity():
    idle = [(name, c) for name,c in CASES if name.endswith('/idle')]
    assert len(idle) == 36
    for name, case in idle:
        result = execute_v0(case)
        assert result['processed_events'] == result['processed_batches'] == 0, name
        assert result['emissions'] == result['terminal_outputs'] == [], name
        assert result['observations'] == {'batches':[], 'routes':[]}, name
        assert [(x['raw'],x['last_timestamp']) for x in result['states']] == [
            (n.initial_raw, 0) for n in case.nodes
        ], name


def test_observable_route_multiplicity_is_not_batch_multiplicity():
    name, case = next((n, c) for n,c in CASES if n == 'relays/parallel/at_zero')
    result = execute_v0(case)
    assert len(result['observations']['routes']) == 3
    assert result['processed_batches'] == 3
    assert result['processed_events'] == 4
    assert [b['channels'] for b in result['observations']['batches']] == [[0],[0,0],[0]]


def test_outside_domain_fails_explicitly():
    first = CASES[0][1]
    with pytest.raises(OracleDomainErrorV0, match='strictly positive'):
        execute_v0(replace(first, edges=(EdgeV0('A',7,'B',0,0),)))
    with pytest.raises(OracleDomainErrorV0, match='out-of-domain'):
        execute_v0(replace(first, nodes=(replace(first.nodes[0],instructions=(('MYSTERY', 5),)),)+first.nodes[1:]))
    with pytest.raises(ValueError, match='nonnegative'):
        relay_time_translation_v0(first, -1)
    with pytest.raises(ValueError, match='unit relays'):
        relay_time_translation_v0(next(c for n,c in CASES if n.startswith('decay/')),1)


def test_limit_is_not_a_successful_partial_trace():
    case = next(c for n,c in CASES if n == 'relays/parallel/at_zero')
    assert execute_v0(case, max_events=4)['processed_events'] == 4
    assert execute_v0(case, max_batches=3)['processed_batches'] == 3
    with pytest.raises(OracleLimitV0, match='max_events'):
        execute_v0(case, max_events=3)
    with pytest.raises(OracleLimitV0, match='max_batches'):
        execute_v0(case, max_batches=2)
