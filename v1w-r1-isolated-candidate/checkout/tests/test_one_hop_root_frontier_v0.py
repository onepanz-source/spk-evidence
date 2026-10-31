"""One-hop root emission cutoffs are owned; static-route delivery is separate."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_network.model_v0 import NetworkEdgeV0
from spk_simulator.one_hop_root_frontier_v0 import (
    OneHopDestinationQueryV0 as Q,
    analyze_one_hop_root_frontier_v0 as analyze,
)
from spk_simulator.owned_external_ingress_prefix_v0 import seal_finite_external_ingress_v0
from tests.test_owned_root_emission_frontier_v0 import fixture, root_input


def context(*, nonroot=False, external=False):
    c, seal = fixture()
    if external:
        c, seal = root_input(c, node='B', time=7, arrival_boundary=3)
    edges = (
        NetworkEdgeV0('A', 7, 'B', 0, 2),
        NetworkEdgeV0('C', 7, 'B', 0, 2),
        NetworkEdgeV0('C', 7, 'B', 0, 3),
    )
    if nonroot:
        edges += (NetworkEdgeV0('B', 7, 'C', 0, 2),)
    net = replace(c[1], edges=edges)
    c = (c[0], net, c[2], c[3], c[4], c[5],
         replace(c[6], image=replace(c[6].image, network=net)), c[7])
    seal = seal_finite_external_ingress_v0(c[0], net,
        c[6].owned.boundary.driver.boundary.ledger.ingress)
    return c, seal


def result(c=None, seal=None, *queries):
    if c is None:
        c, seal = context()
    return analyze(c[0], c[1], seal, c[2], c[3], c[4], c[5], c[6],
                   queries=tuple(Q(node, t) for node, t in queries))


def row(*queries):
    return result(None, None, *queries).destinations[0]


def test_positive_one_hop_prefix_after_all_static_manifest_delivery_times():
    x = row(('B', 7))
    assert x.status == 'ONE_HOP_STATIC_PRECONDITIONS_MET'
    assert x.upstream_prefix_authenticated
    assert x.static_known_deliveries_present
    assert x.static_manifest_route_ids == ()
    assert not x.supports_consume_admission


def test_no_premature_batch_consume_even_after_positive_prefix():
    r = result(None, None, ('B', 7))
    assert not r.supports_consume_admission
    assert not r.destinations[0].supports_consume_admission


def test_source_thresholds_preserve_parallel_edge_indices():
    x = row(('B', 5))
    assert [(e.edge_index, e.source_node_id, e.required_source_through)
            for e in x.edge_evidences] == [(0, 'A', 3), (1, 'C', 3), (2, 'C', 2)]
    assert all(e.source_is_root and e.authenticated_root_prefix for e in x.edge_evidences)


def test_absent_known_route_does_not_become_a_delivered_spike():
    x = row(('B', 4))
    assert x.static_manifest_route_ids == (10,)
    assert x.static_event_resident_ids == ()
    assert x.status == 'STATIC_ROUTE_NOT_RESIDENT'


def test_all_known_emissions_are_not_same_as_all_known_deliveries():
    x = row(('B', 5))
    assert x.upstream_prefix_authenticated
    assert x.static_manifest_route_ids == (11,)
    assert not x.static_known_deliveries_present


def test_nonroot_source_is_not_certified_by_a_root_cutoff():
    c, seal = context(nonroot=True)
    x = result(c, seal, ('B', 5)).destinations[0]
    assert x.status == 'NONROOT_SOURCE_UNPROVEN'
    assert not x.upstream_prefix_authenticated
    assert any(not e.source_is_root for e in x.edge_evidences)


def test_nonroot_source_negative_cutoff_is_vacuous():
    c, seal = context(nonroot=True)
    x = result(c, seal, ('B', 1)).destinations[0]
    assert all(e.vacuous_negative_time for e in x.edge_evidences)
    assert x.upstream_prefix_authenticated


def test_event_time_can_equal_service_time_without_becoming_service_cutoff():
    x = row(('B', 3))
    assert all(e.required_source_through == 3 - (2 if e.edge_index in (0, 1) else 3)
               for e in x.edge_evidences)


def test_pending_external_input_prevents_positive_prefix():
    c, seal = context(external=True)
    x = result(c, seal, ('B', 7)).destinations[0]
    assert x.status == 'EXTERNAL_PREFIX_PENDING'
    assert x.external_same_time_pending_ids == (0,)


def test_later_external_input_does_not_block_earlier_prefix():
    c, seal = context(external=True)
    x = result(c, seal, ('B', 6)).destinations[0]
    assert x.external_prefix_accounted
    assert x.upstream_prefix_authenticated


def test_no_extra_source_when_event_time_comes_before_all_route_delays():
    x = row(('B', 0))
    assert x.status == 'ONE_HOP_STATIC_PRECONDITIONS_MET'
    assert all(e.vacuous_negative_time for e in x.edge_evidences)


def test_query_order_is_canonical():
    c, s = context()
    assert result(c, s, ('B', 7), ('B', 4)) == result(c, s, ('B', 4), ('B', 7))


def test_multiple_event_time_obligations_not_collapsed():
    r = result(None, None, ('B', 4), ('B', 5), ('B', 6))
    assert tuple(x.event_time for x in r.destinations) == (4, 5, 6)
    assert tuple(x.static_manifest_route_ids for x in r.destinations) == ((10,), (11,), (12,))


def test_empty_queries_safe_and_do_not_generate_certificates():
    assert result().destinations == ()


def test_result_is_reproducible_without_mutations():
    c, s = context()
    before = repr((c, s))
    assert result(c, s, ('B', 7)) == result(c, s, ('B', 7))
    assert repr((c, s)) == before


def test_result_immutable():
    x = result(None, None, ('B', 7))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        x.destinations[0].status = 'CERTIFIED'


def test_unknown_target_rejected():
    c, s = context()
    with pytest.raises(ValueError, match='unknown one-hop target'):
        result(c, s, ('MISSING', 7))


def test_duplicate_queries_rejected():
    c, s = context()
    with pytest.raises(ValueError, match='duplicate one-hop query'):
        result(c, s, ('B', 7), ('B', 7))


@pytest.mark.parametrize('bad', ('', ' B', 'B ', 5, None, True))
def test_invalid_target_rejected(bad):
    with pytest.raises(ValueError, match='one-hop target'):
        Q(bad, 4)


@pytest.mark.parametrize('bad', (-1, None, 2.4, True, '2'))
def test_invalid_time_rejected(bad):
    with pytest.raises(ValueError, match='one-hop EVENT_TIME'):
        Q('B', bad)


def test_queries_must_be_tuple():
    c, s = context()
    with pytest.raises(TypeError, match='one-hop queries'):
        analyze(c[0], c[1], s, c[2], c[3], c[4], c[5], c[6], queries=[Q('B', 4)])


def test_queries_must_be_typed():
    c, s = context()
    with pytest.raises(TypeError, match='one-hop queries'):
        analyze(c[0], c[1], s, c[2], c[3], c[4], c[5], c[6], queries=('B',))


def test_missing_network_topology_route_rejected():
    c, s = context()
    net = replace(c[1], edges=(c[1].edges[0],))
    c = (c[0], net, c[2], c[3], c[4], c[5],
         replace(c[6], image=replace(c[6].image, network=net)), c[7])
    s = seal_finite_external_ingress_v0(c[0], net, c[6].owned.boundary.driver.boundary.ledger.ingress)
    with pytest.raises(ValueError, match='contradicts network'):
        result(c, s, ('B', 7))


def test_wrong_snapshot_network_rejected():
    c, s = context()
    with pytest.raises(ValueError, match='network/profile/epoch'):
        result((c[0], replace(c[1], edges=()), *c[2:]), s, ('B', 7))


def test_external_seal_modified_rejected():
    c, s = context(external=True)
    arrival = s.binding.arrivals[0]
    s = replace(s, binding=replace(s.binding, arrivals=(replace(arrival, event_time=8),)))
    with pytest.raises(ValueError, match='seal modified'):
        result(c, s, ('B', 7))


def test_uncommitted_root_history_rejected_by_authority():
    c, s = context()
    from tests.test_owned_internal_state_commit_v0 import one
    from dataclasses import replace
    _, step = one()
    c = (*c[:6], replace(c[6], commits=(step.evidence,)), c[7])
    with pytest.raises(ValueError, match='commit history'):
        result(c, s, ('B', 7))


def test_new_batch_can_never_be_admitted_by_this_component():
    r = result(None, None, ('B', 4), ('B', 7))
    assert all(x.supports_consume_admission is False for x in r.destinations)
    assert r.supports_consume_admission is False


def test_real_nonempty_external_consumption_cannot_be_readmitted():
    """After a real Core commit, a consumed destination occurrence stays historical."""
    from tests.test_owned_root_frontier_nonempty_conformance_v0 import (
        scenario, commit_one,
    )
    c, _ = scenario()
    c, _ = commit_one(c)
    net = replace(c[1], edges=(NetworkEdgeV0('A', 7, 'B', 0, 2),))
    state = replace(c[6], image=replace(c[6].image, network=net))
    c = (c[0], net, c[2], c[3], c[4], c[5], state, c[7])
    seal = seal_finite_external_ingress_v0(
        c[0], net, state.owned.boundary.driver.boundary.ledger.ingress,
    )
    x = result(c, seal, ('B', 4)).destinations[0]
    assert x.upstream_prefix_authenticated
    assert x.external_prefix_accounted
    assert x.external_same_time_consumed_ids == (0,)
    assert x.status == 'EXTERNAL_SAME_TIME_ALREADY_CONSUMED'
    assert not x.supports_consume_admission
