"""Root-only authentic cutoff: NEVER a general batch closure certificate."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.owned_external_ingress_prefix_v0 import seal_finite_external_ingress_v0
from spk_simulator.owned_root_emission_frontier_v0 import (
    RootEmissionFrontierQueryV0 as Q,
    analyze_owned_root_emission_frontier_v0 as analyze,
)
from tests.test_owned_internal_state_commit_v0 import context, all_three


def fixture():
    c = context()
    s = seal_finite_external_ingress_v0(c[0], c[1], c[6].owned.boundary.driver.boundary.ledger.ingress)
    return c, s


def run(c, seal, *args):
    return analyze(
        c[0], c[1], seal, c[2], c[3], c[4], c[5], c[6],
        queries=tuple(Q(node, t) for node, t in args),
    )


def root_input(c, *, time=2, arrival_boundary=3, node='A'):
    ingress = ExternalIngressBindingV0(
        (BoundExternalArrivalV0(0, time, node, 0, 'PE0', arrival_boundary, 50),),
        (BatchIngressReleaseV0(50, arrival_boundary, (0,)),),
    )
    b = c[6].owned.boundary.driver.boundary
    b2 = replace(b, ledger=replace(b.ledger, ingress=ingress))
    newstate = replace(c[6], owned=replace(c[6].owned,
        boundary=replace(c[6].owned.boundary,
            driver=replace(c[6].owned.boundary.driver, boundary=b2))))
    c = (*c[:6], newstate, c[7])
    seal = seal_finite_external_ingress_v0(c[0], c[1], ingress)
    return c, seal


def test_empty_sealed_root_source_is_certified_without_idle_heuristics():
    c, seal = fixture()
    e = run(c, seal, ('A', 500)).evidences[0]
    assert e.source_emission_prefix_certified
    assert e.status == 'SOURCE_PREFIX_CERTIFIED'
    assert e.required_external_input_indices == ()
    assert e.committed_batch_request_ids == ()


def test_other_empty_root_certified():
    c, seal = fixture()
    assert run(c, seal, ('C', 12)).evidences[0].source_emission_prefix_certified


def test_manifest_phantom_inbound_route_blocks_root_proof():
    c, seal = fixture()
    e = run(c, seal, ('B', 3)).evidences[0]
    assert not e.source_emission_prefix_certified
    assert e.status == 'INCONSISTENT_ROUTE_MANIFEST'


def test_sealed_source_prefix_is_not_batch_consume_permission():
    c, seal = fixture()
    x = run(c, seal, ('A', 9))
    assert not x.supports_consume_admission
    assert not x.evidences[0].supports_consume_admission


def test_sorted_queries_deterministic():
    c, seal = fixture()
    assert run(c, seal, ('C', 7), ('A', 2)) == run(c, seal, ('A', 2), ('C', 7))


def test_timing_not_inferred_from_service_tick():
    c, seal = fixture()
    assert run(c, seal, ('A', 2)).evidences[0].source_emission_prefix_certified
    assert c[6].owned.boundary.service.next_service_tick == 0


def test_preexisting_history_on_other_node_does_not_block_empty_root():
    c, _ = all_three()
    seal = seal_finite_external_ingress_v0(c[0], c[1], c[6].owned.boundary.driver.boundary.ledger.ingress)
    assert run(c, seal, ('A', 90)).evidences[0].source_emission_prefix_certified


def test_non_root_edge_blocks_source_proof():
    c, seal = fixture()
    from spk_network.model_v0 import NetworkEdgeV0
    edge = NetworkEdgeV0('A', 7, 'B', 0, 2)
    net = replace(c[1], edges=(edge,))
    # Preserve network/image identity for the test and rebuild seal.
    state = replace(c[6], image=replace(c[6].image, network=net))
    c = (c[0], net, c[2], c[3], c[4], c[5], state, c[7])
    seal = seal_finite_external_ingress_v0(c[0], net, state.owned.boundary.driver.boundary.ledger.ingress)
    assert run(c, seal, ('B', 5)).evidences[0].status == 'INBOUND_EDGES_UNPROVEN'


def test_pending_root_external_input_blocks_source():
    c, seal = root_input(context())
    e = run(c, seal, ('A', 2)).evidences[0]
    assert e.status == 'EXTERNAL_PREFIX_PENDING'
    assert e.required_external_input_indices == (0,)
    assert not e.source_emission_prefix_certified


def test_earlier_prefix_not_blocked_by_later_external_input():
    c, seal = root_input(context(), time=9)
    e = run(c, seal, ('A', 8)).evidences[0]
    assert e.status == 'SOURCE_PREFIX_CERTIFIED'


def test_cannot_treat_just_resident_external_input_as_committed():
    c, seal = root_input(context())
    b = c[6].owned.boundary.driver.boundary
    b = replace(b, ledger=replace(b.ledger, external_resident=(0,)),
                arbiter=replace(b.arbiter, last_service_boundary=3))
    s = replace(c[6], owned=replace(c[6].owned,
        boundary=replace(c[6].owned.boundary,
            service=replace(c[6].owned.boundary.service, next_service_tick=4),
            driver=replace(c[6].owned.boundary.driver, boundary=b))))
    e = run((*c[:6], s, c[7]), seal, ('A', 2)).evidences[0]
    assert e.status == 'EXTERNAL_EVENTS_UNCONSUMED'


def test_cannot_treat_consumed_external_as_committed_core():
    c, seal = root_input(context())
    b = c[6].owned.boundary.driver.boundary
    b = replace(b, ledger=replace(b.ledger, external_consumed=(0,)),
                arbiter=replace(b.arbiter, last_service_boundary=3))
    s = replace(c[6], owned=replace(c[6].owned,
        boundary=replace(c[6].owned.boundary,
            service=replace(c[6].owned.boundary.service, next_service_tick=4),
            driver=replace(c[6].owned.boundary.driver, boundary=b))))
    e = run((*c[:6], s, c[7]), seal, ('A', 2)).evidences[0]
    assert e.status == 'ROOT_INPUT_COMMIT_MISMATCH'


def test_root_evidence_is_frozen():
    c, seal = fixture()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        run(c, seal, ('A', 2)).evidences[0].status = 'FAKE'


def test_original_snapshot_is_unchanged():
    c, seal = fixture()
    before = (c, seal)
    run(c, seal, ('A', 2), ('C', 9))
    assert (c, seal) == before


def test_empty_query_collection_is_safe():
    c, seal = fixture()
    assert run(c, seal).evidences == ()


def test_unknown_source_rejected():
    c, seal = fixture()
    with pytest.raises(ValueError, match='unknown root frontier source'):
        run(c, seal, ('NONE', 2))


def test_duplicate_query_rejected():
    c, seal = fixture()
    with pytest.raises(ValueError, match='duplicate root frontier'):
        run(c, seal, ('A', 2), ('A', 2))


@pytest.mark.parametrize('bad', (-1, True, 1.5, None, '2'))
def test_invalid_query_timestamp_rejected(bad):
    with pytest.raises(ValueError, match='EVENT_TIME'):
        Q('A', bad)


@pytest.mark.parametrize('bad', ('', ' A', 'A ', 5, None))
def test_invalid_query_node_rejected(bad):
    with pytest.raises(ValueError, match='source node'):
        Q(bad, 2)


def test_query_list_rejected():
    c, seal = fixture()
    with pytest.raises(TypeError, match='queries'):
        analyze(c[0], c[1], seal, c[2], c[3], c[4], c[5], c[6], queries=[Q('A', 2)])


def test_query_item_type_rejected():
    c, seal = fixture()
    with pytest.raises(TypeError, match='queries'):
        analyze(c[0], c[1], seal, c[2], c[3], c[4], c[5], c[6], queries=('A',))


def test_wrong_epoch_rejected():
    c, seal = fixture()
    with pytest.raises(ValueError, match='epoch'):
        run(c, replace(seal, epoch_id='OTHER'), ('A', 2))


def test_wrong_profile_rejected():
    c, seal = fixture()
    with pytest.raises(ValueError, match='profile'):
        run(c, replace(seal, profile_id='OTHER'), ('A', 2))


def test_changed_sealed_external_binding_rejected():
    c, seal = fixture()
    altered, _ = root_input(c)
    with pytest.raises(ValueError, match='seal modified'):
        run(altered, seal, ('A', 2))


def test_false_commit_history_rejected_by_audit():
    c, seal = fixture()
    from spk_simulator.owned_internal_reads_v0 import OwnedInternalCommitEvidenceV0
    from tests.test_owned_internal_state_commit_v0 import one
    _, step = one()
    state = replace(c[6], commits=(step.evidence,))
    with pytest.raises(ValueError, match='commit history'):
        run((*c[:6], state, c[7]), seal, ('A', 2))


def test_untested_service_graph_fails_closed():
    c, seal = fixture()
    from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
    with pytest.raises(ValueError, match='dependency|serialized'):
        run((*c[:5], AccessDependencyGraphV0(()), *c[6:]), seal, ('A', 2))
