"""Integration proof: nonempty sealed root inputs, actual EVENT consumption and Core commit.

No output or dependency on functional trace. These tests exercise the existing
S3.7d/k15 frontier authority without altering its implementation.
"""
from dataclasses import replace
import pytest

from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.owned_external_ingress_prefix_v0 import seal_finite_external_ingress_v0
from spk_simulator.owned_root_emission_frontier_v0 import (
    RootEmissionFrontierQueryV0, analyze_owned_root_emission_frontier_v0,
)
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.owned_internal_reads_v0 import advance_owned_internal_reads_v0
from spk_simulator.owned_internal_state_commit_v0 import commit_owned_internal_state_v0
from tests.test_owned_internal_state_commit_v0 import context


def scenario(*, second=False, parallel=False, later_release=0):
    if second and parallel:
        raise ValueError('select one extension')
    architecture, network, manifest, admission, original, _, state, _ = context()
    ids = (50, 70, 71, 80) + ((51, 72, 73, 81) if second else ())
    requests = tuple(r for r in original if r.request_id in ids)
    if parallel:
        requests = tuple(replace(r, quantity=2) if r.request_id == 50 else r for r in requests)
    deps = AccessDependencyGraphV0(tuple(AccessDependencyV0(r.request_id, ()) for r in requests))
    graph = serialize_internal_access_graph_v0(requests, deps).graph
    manifest = replace(manifest, routes=())
    admission = replace(admission, groups=(), routed_occurrence_count=0)
    arrivals = [BoundExternalArrivalV0(0, 4, 'B', 0, 'PE1', 0, 50)]
    releases = [BatchIngressReleaseV0(50, 0, (0,))]
    if parallel:
        arrivals.append(BoundExternalArrivalV0(1, 4, 'B', 0, 'PE1', 0, 50))
        releases = [BatchIngressReleaseV0(50, 0, (0, 1))]
    if second:
        arrivals.append(BoundExternalArrivalV0(1, 5, 'B', 0, 'PE1', later_release, 51))
        releases.append(BatchIngressReleaseV0(51, later_release, (1,)))
    ingress = ExternalIngressBindingV0(tuple(arrivals), tuple(releases))
    boundary = state.owned.boundary.driver.boundary
    boundary = replace(boundary, ledger=replace(boundary.ledger, ingress=ingress))
    driver = replace(state.owned.boundary.driver, boundary=boundary)
    state = replace(state, owned=replace(state.owned, boundary=replace(state.owned.boundary, driver=driver)))
    seal = seal_finite_external_ingress_v0(architecture, network, ingress)
    return (architecture, network, manifest, admission, requests, graph, state, ingress), seal


def tick(c):
    step = advance_owned_internal_reads_v0(*c[:7], ingress=c[7])
    return (*c[:6], step.state, c[7])


def commit_one(c, request_id=80, limit=30):
    for _ in range(limit):
        pending = {x.request_id for x in c[6].owned.boundary.service.awaiting_confirmation}
        if request_id in pending:
            break
        c = tick(c)
    else:
        raise AssertionError(f'STATE_COMMIT {request_id} did not finish')
    result = commit_owned_internal_state_v0(c[1], c[2], c[4], c[5], c[6], commit_request_id=request_id)
    return (*c[:6], result.state, c[7]), result


def frontier(c, seal, *queries):
    return analyze_owned_root_emission_frontier_v0(
        c[0], c[1], seal, c[2], c[3], c[4], c[5], c[6],
        queries=tuple(RootEmissionFrontierQueryV0(node, t) for node, t in queries),
    )


def evidence(c, seal, t, node='B'):
    return frontier(c, seal, (node, t)).evidences[0]


def test_nonempty_external_input_is_truly_consumed_and_committed():
    c, seal = scenario()
    assert not evidence(c, seal, 4).source_emission_prefix_certified
    c, receipt = commit_one(c)
    assert receipt.evidence.receipt.old_version == 0
    assert receipt.evidence.receipt.new_version == 1
    assert c[6].owned.boundary.driver.boundary.ledger.external_consumed == (0,)
    row = evidence(c, seal, 4)
    assert row.status == 'SOURCE_PREFIX_CERTIFIED'
    assert row.source_emission_prefix_certified
    assert row.required_external_input_indices == (0,)
    assert row.consumed_external_input_indices == (0,)
    assert row.committed_batch_request_ids == (80,)
    assert not row.supports_consume_admission


def test_future_root_boundary_is_certified_after_actual_commit():
    c, seal = scenario()
    c, _ = commit_one(c)
    assert evidence(c, seal, 100).source_emission_prefix_certified


def test_prefix_before_first_event_does_not_claim_consumption():
    c, seal = scenario()
    row = evidence(c, seal, 3)
    assert row.source_emission_prefix_certified
    assert row.required_external_input_indices == ()
    assert row.committed_batch_request_ids == ()


def test_external_arrival_alone_is_not_a_source_frontier():
    c, seal = scenario()
    c = tick(c)
    assert not evidence(c, seal, 4).source_emission_prefix_certified


def test_after_physical_consume_before_state_commit_not_certified():
    c, seal = scenario()
    for _ in range(4):
        c = tick(c)
    assert 0 in c[6].owned.boundary.driver.boundary.ledger.external_consumed
    assert not evidence(c, seal, 4).source_emission_prefix_certified


def test_single_commit_preserves_root_certificate_under_replay():
    c, seal = scenario()
    c, _ = commit_one(c)
    assert frontier(c, seal, ('B',4), ('A',4)) == frontier(c, seal, ('A',4), ('B',4))


def test_external_parallel_occurrences_do_not_collapse():
    c, seal = scenario(parallel=True)
    c, receipt = commit_one(c)
    assert receipt.evidence.receipt.new_raw == 2
    row = evidence(c, seal, 4)
    assert row.source_emission_prefix_certified
    assert row.required_external_input_indices == (0,1)
    assert row.consumed_external_input_indices == (0,1)
    assert row.committed_batch_request_ids == (80,)


def test_two_nonempty_root_batches_commit_in_event_time_order():
    c, seal = scenario(second=True)
    c, first = commit_one(c, 80)
    assert first.evidence.receipt.new_version == 1
    assert not evidence(c, seal, 5).source_emission_prefix_certified
    assert evidence(c, seal, 4).source_emission_prefix_certified
    c, second = commit_one(c, 81)
    assert second.evidence.receipt.old_version == 1
    assert second.evidence.receipt.new_version == 2
    row = evidence(c, seal, 5)
    assert row.source_emission_prefix_certified
    assert row.required_external_input_indices == (0,1)
    assert row.committed_batch_request_ids == (80,81)


def test_later_service_arrival_does_not_block_prior_cut():
    c, seal = scenario(second=True, later_release=10)
    c, _ = commit_one(c, 80)
    assert evidence(c, seal, 4).source_emission_prefix_certified
    assert not evidence(c, seal, 5).source_emission_prefix_certified


def test_certificate_does_not_change_owner_snapshot():
    c, seal = scenario()
    c, _ = commit_one(c)
    before = repr(c)
    frontier(c, seal, ('B',4))
    assert repr(c) == before


def test_certificates_are_deterministic_from_same_snapshot():
    c, seal = scenario()
    c, _ = commit_one(c)
    assert frontier(c, seal, ('B',4)) == frontier(c, seal, ('B',4))


def test_certificate_does_not_require_network_observed_trace():
    c, seal = scenario()
    c, _ = commit_one(c)
    # Constructed solely from storage, Core, ingress and commit owner; no trace provided.
    assert frontier(c, seal, ('B',4)).evidences[0].source_emission_prefix_certified


def test_stale_snapshot_cannot_inherit_future_certificate():
    initial, seal = scenario()
    current, _ = commit_one(initial)
    assert not evidence(initial, seal, 4).source_emission_prefix_certified
    assert evidence(current, seal, 4).source_emission_prefix_certified


def test_missing_historical_commit_receipt_fails_closed():
    c, seal = scenario()
    c, _ = commit_one(c)
    forged = replace(c[6], commits=())
    with pytest.raises(ValueError, match='history|commit|confirmation'):
        evidence((*c[:6],forged,c[7]), seal, 4)


def test_tampered_consumed_input_identity_fails_closed():
    c, seal = scenario()
    c, _ = commit_one(c)
    ledger = c[6].owned.boundary.driver.boundary.ledger
    forged = replace(ledger, external_consumed=())
    bound = c[6].owned.boundary.driver.boundary
    drv = replace(c[6].owned.boundary.driver, boundary=replace(bound, ledger=forged))
    state = replace(c[6], owned=replace(c[6].owned, boundary=replace(c[6].owned.boundary,driver=drv)))
    with pytest.raises(ValueError):
        evidence((*c[:6],state,c[7]),seal,4)


def test_altered_external_seal_fails_closed():
    c, seal = scenario()
    c, _ = commit_one(c)
    original = seal.binding.arrivals[0]
    bad_arrival = replace(original, event_time=5)
    bad = replace(seal, binding=replace(seal.binding, arrivals=(bad_arrival,)))
    with pytest.raises(ValueError, match='seal modified'):
        evidence(c,bad,4)


def test_positive_frontier_never_authorizes_batch_consume():
    c, seal = scenario()
    c, _ = commit_one(c)
    result = frontier(c,seal,('B',4))
    assert not result.supports_consume_admission
    assert all(not e.supports_consume_admission for e in result.evidences)
