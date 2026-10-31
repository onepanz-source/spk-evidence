"""Causal frontier tests use native Network/Architecture fixture constructors."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_frontier_v0 import classify_causal_service_frontier_v0 as frontier
from tests.test_release_aware_scheduler_v0 import (
    machine, req, graph, ingress, arrival, release,
)


def classify(requests=None, deps=None, *, boundary=0, completed=(), running=(), grants=(), binding=None):
    requests = (req(0), req(1, pe='PE1')) if requests is None else requests
    if deps is None:
        ids = sorted(r.request_id for r in requests)
        deps = graph(*((rid, ()) for rid in ids))
    return frontier(machine(), requests, deps, service_boundary=boundary,
                    completed_request_ids=completed, in_flight_request_ids=running,
                    granted_memory_request_ids=grants, ingress=binding)


def test_ready_independent_reads():
    x = classify()
    assert x.ready_request_ids == (0, 1)
    assert x.service_boundary == 0


def test_dependency_waits():
    x = classify(deps=graph((0, ()), (1, (0,))))
    assert x.ready_request_ids == (0,)
    assert x.waiting_dependency_ids == (1,)
    assert x.candidates[1].missing_predecessors == (0,)


def test_completed_releases_successor():
    x = classify(deps=graph((0, ()), (1, (0,))), completed=(0,))
    assert x.ready_request_ids == (1,)
    assert x.completed_request_ids == (0,)


def test_in_flight_not_reissued():
    x = classify(running=(0,))
    assert x.ready_request_ids == (1,)
    assert x.in_flight_request_ids == (0,)


def test_unfinished_predecessor_of_running_rejected():
    with pytest.raises(ValueError, match='unfinished'):
        classify(deps=graph((0, ()), (1, (0,))), running=(1,))


def test_unfinished_predecessor_of_completed_rejected():
    with pytest.raises(ValueError, match='unfinished'):
        classify(deps=graph((0, ()), (1, (0,))), completed=(1,))


def test_emission_without_memory_grant_waits():
    x = classify(requests=(req(0, kind=Kind.EMISSION_RECORD),), deps=graph((0, ())))
    assert x.waiting_memory_ids == (0,)


def test_route_without_memory_grant_waits():
    x = classify(requests=(req(0, kind=Kind.ROUTE_ENQUEUE),), deps=graph((0, ())))
    assert x.waiting_memory_ids == (0,)


def test_memory_grant_releases_emission():
    x = classify(requests=(req(0, kind=Kind.EMISSION_RECORD),), deps=graph((0, ())), grants=(0,))
    assert x.ready_request_ids == (0,)


def test_memory_grant_releases_route():
    x = classify(requests=(req(0, kind=Kind.ROUTE_ENQUEUE),), deps=graph((0, ())), grants=(0,))
    assert x.ready_request_ids == (0,)


def test_memory_grant_cannot_skip_dependency():
    x = classify(requests=(req(0), req(1, kind=Kind.ROUTE_ENQUEUE)),
                 deps=graph((0, ()), (1, (0,))), grants=(1,))
    assert x.waiting_dependency_ids == (1,)


def test_invalid_memory_grant_to_consume():
    with pytest.raises(ValueError, match='non-memory-gated'):
        classify(grants=(0,))


def test_external_arrival_is_service_time():
    bound = ingress((arrival(0, 7), arrival(1, 0, consume=1, pe='PE1')),
                    (release(0, 7, (0,)), release(1, 0, (1,))))
    x = classify(boundary=2, binding=bound)
    assert x.waiting_release_ids == (0,)
    assert x.ready_request_ids == (1,)
    assert x.candidates[0].release_boundary == 7
    assert x.candidates[0].kind is Kind.BATCH_CONSUME


def test_arrival_at_boundary_is_ready():
    bound = ingress((arrival(0, 7), arrival(1, 0, consume=1, pe='PE1')),
                    (release(0, 7, (0,)), release(1, 0, (1,))))
    assert classify(boundary=7, binding=bound).ready_request_ids == (0, 1)


def test_ingress_does_not_modify_event_time():
    x = req(0, event_time=2)
    bound = ingress((arrival(0, 9),), (release(0, 9, (0,)),))
    out = classify(requests=(x,), deps=graph((0, ())), binding=bound)
    assert out.waiting_release_ids == (0,)
    assert x.event_time == 2


def test_join_waits_for_predecessor_before_release():
    bound = ingress((arrival(0, 4, consume=1, pe='PE1'),),
                    (release(0, 0, ()), release(1, 4, (0,))))
    x = classify(deps=graph((0, ()), (1, (0,))), boundary=0, binding=bound)
    assert x.waiting_dependency_ids == (1,)
    y = classify(deps=graph((0, ()), (1, (0,))), boundary=0, completed=(0,), binding=bound)
    assert y.waiting_release_ids == (1,)


def test_invalid_batch_release_rejected():
    bound = ingress((arrival(0, 4),), (release(0, 3, (0,)), release(1, 0, ())))
    with pytest.raises(ValueError, match='release accounting'):
        classify(binding=bound)


def test_missing_batch_release_rejected():
    bound = ingress((arrival(0, 4),), (release(0, 4, (0,)),))
    with pytest.raises(ValueError, match='incomplete ingress'):
        classify(binding=bound)


def test_unknown_request_in_snapshot_rejected():
    with pytest.raises(ValueError, match='unknown request'):
        classify(completed=(99,))


def test_duplicate_completed_rejected():
    with pytest.raises(ValueError, match='invalid completed'):
        classify(completed=(0, 0))


def test_bool_request_id_rejected():
    with pytest.raises(ValueError):
        classify(completed=(True,))


def test_running_completed_overlap_rejected():
    with pytest.raises(ValueError, match='conflicting'):
        classify(completed=(0,), running=(0,))


def test_granted_completed_overlap_rejected():
    with pytest.raises(ValueError, match='conflicting'):
        classify(requests=(req(0, kind=Kind.EMISSION_RECORD),),
                 deps=graph((0, ())), completed=(0,), grants=(0,))


def test_unknown_pe_rejected():
    with pytest.raises(ValueError, match='invalid request'):
        classify(requests=(req(0, pe='PEZ'),), deps=graph((0, ())))


def test_graph_coverage_rejected():
    with pytest.raises(ValueError, match='coverage'):
        classify(deps=graph((0, ())))


def test_reordering_inputs_deterministic():
    x = (req(0), req(1, pe='PE1'))
    assert classify(requests=x) == classify(requests=x[::-1])


def test_immutable_result():
    x = classify()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        x.service_boundary = 99


def test_none_and_wrong_boundary_rejected():
    for value in (-1, True, '0'):
        with pytest.raises(ValueError, match='SERVICE_TIME'):
            classify(boundary=value)


def test_empty_request_set():
    x = classify(requests=(), deps=graph())
    assert x.candidates == x.ready_request_ids == ()


def test_no_mutation_of_inputs():
    r = (req(0), req(1, pe='PE1'))
    g = graph((0, ()), (1, (0,)))
    before = repr((r, g))
    classify(requests=r, deps=g)
    assert repr((r, g)) == before
