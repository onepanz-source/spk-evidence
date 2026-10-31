"""Bounded self-framed storage execution: no manual frame or confirmation."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.autonomous_storage_run_v0 import run_autonomous_storage_v0 as run
from tests.test_owned_service_autoframe_v0 import fixture
from tests.test_release_aware_scheduler_v0 import graph


def execute(c, *, cap=20, state=None):
    a, m, adm, requests, deps, initial, ingress = c
    return run(a, m, adm, requests, deps, initial if state is None else state,
               ingress=ingress, max_service_ticks=cap)


def test_baseline_finishes():
    result = execute(fixture())
    assert result.status == 'COMPLETED'
    assert result.service_ticks == 9
    assert result.end_service_boundary == 9
    assert result.start_service_boundary == 0
    assert result.unfinished_request_ids == ()


def test_all_storage_completions_authenticated():
    result = execute(fixture())
    assert len(result.completed_request_ids) == 8
    assert set(result.state.boundary.driver.boundary.storage.consumed_ids) == {10, 11, 12}
    assert all(set(t.result.authenticated_effects.confirmed_request_ids) <=
               set(t.result.quantum.confirmed_request_ids) for t in result.steps)


def test_no_caller_frames_and_sequential_boundaries():
    result = execute(fixture())
    assert tuple(t.frame.service_boundary for t in result.steps) == tuple(range(9))


def test_initial_grant_before_emission():
    result = execute(fixture())
    assert result.steps[0].result.output_start_decision.granted_emission_ids == (1,)
    assert result.steps[0].frame.new_ready_emission_ids == ()


def test_route_starts_after_emission():
    result = execute(fixture())
    assert not result.steps[1].frame.new_ready_route_ids
    assert result.steps[2].frame.new_ready_route_ids == (10,)


def test_no_duplicate_routes():
    result = execute(fixture())
    starts = [rid for s in result.steps for rid in s.frame.new_ready_route_ids]
    assert sorted(starts) == [10, 11, 12]


def test_conserves_output():
    result = execute(fixture())
    assert not result.state.boundary.driver.boundary.storage.pending_output
    assert not result.state.output.active


def test_conserves_event():
    result = execute(fixture())
    assert not result.state.boundary.driver.boundary.storage.admitted_events
    assert not result.state.boundary.driver.boundary.ledger.external_resident


def test_limited_run_does_not_claim_deadlock():
    result = execute(fixture(), cap=2)
    assert result.status == 'TICK_LIMIT'
    assert result.service_ticks == 2
    assert result.unfinished_request_ids


def test_restarts_from_a_snapshot():
    c = fixture()
    short = execute(c, cap=3)
    continued = execute(c, cap=20, state=short.state)
    full = execute(c)
    assert continued.status == 'COMPLETED'
    assert continued.start_service_boundary == 3
    assert continued.steps == full.steps[3:]
    assert continued.state == full.state


def test_repeated_snapshots_deterministic():
    c = fixture()
    assert execute(c) == execute(c)


def test_shuffled_request_order_deterministic():
    c = fixture()
    shuffled = (*c[:3], tuple(reversed(c[3])), *c[4:])
    assert execute(c) == execute(shuffled)


def test_ingress_at_exact_tick():
    result = execute(fixture(ingress_tick=2))
    assert [x.frame.service_boundary for x in result.steps if x.frame.external_arrivals] == [2]
    assert result.status == 'COMPLETED'


def test_delayed_external_arrival_respected():
    result = execute(fixture(ingress_tick=12), cap=30)
    assert result.status == 'COMPLETED'
    assert [x.frame.service_boundary for x in result.steps if x.frame.external_arrivals] == [12]


def test_future_arrival_telemetry_when_horizon_expires():
    result = execute(fixture(ingress_tick=12), cap=3)
    assert result.status == 'TICK_LIMIT'
    assert result.future_external_boundaries == (12,)


def test_same_pe_capacity_one_progress():
    result = execute(fixture(event_slots=1), cap=40)
    assert result.status == 'COMPLETED'


def test_unschedulable_capacity_not_called_deadlock():
    result = execute(fixture(event_slots=1, ingress_tick=0), cap=12)
    assert result.status == 'TICK_LIMIT'
    assert result.service_ticks == 12
    assert result.unfinished_request_ids


def test_no_event_time_mutation():
    c = fixture()
    before = tuple((r.request_id, r.event_time) for r in c[3])
    execute(c)
    assert before == tuple((r.request_id, r.event_time) for r in c[3])


def test_result_immutable():
    result = execute(fixture())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.status = 'DEADLOCK'


@pytest.mark.parametrize('limit', (0, -1, True, 1.0, '2'))
def test_bad_service_tick_limit(limit):
    c = fixture()
    with pytest.raises(ValueError, match='max_service_ticks'):
        execute(c, cap=limit)


def test_unknown_internal_kind_fails_closed():
    internal = next((kind for kind in Kind if kind not in
                     (Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE, Kind.BATCH_CONSUME)), None)
    if internal is None:
        pytest.skip('reduced harness has no internal kind')
    c = fixture()
    requests = tuple(replace(req, kind=internal) if req.request_id == 50 else req
                     for req in c[3])
    with pytest.raises(ValueError, match='internal service kinds'):
        execute((*c[:3], requests, *c[4:]))


def test_invalid_initial_state_rejected():
    c = fixture()
    with pytest.raises(TypeError, match='invalid initial owned state'):
        execute(c, state=object())


def test_bad_dependency_graph_rejected():
    c = fixture()
    with pytest.raises(ValueError, match='coverage'):
        execute((*c[:4], graph((1, ()), (2, ())), *c[5:]))


def test_mismatched_external_binding_rejected():
    c = fixture(ingress_tick=2)
    with pytest.raises(ValueError, match='ingress binding mismatch'):
        run(*c[:6], max_service_ticks=2)


def test_exact_completion_horizon():
    c = fixture()
    assert execute(c, cap=8).status == 'TICK_LIMIT'
    assert execute(c, cap=9).status == 'COMPLETED'


def test_completed_snapshot_has_zero_new_steps():
    c = fixture()
    complete = execute(c).state
    result = execute(c, state=complete, cap=1)
    assert result.status == 'COMPLETED'
    assert result.service_ticks == 0
    assert result.steps == ()
    assert result.start_service_boundary == result.end_service_boundary == 9


def test_duplicate_request_rejected_before_execution():
    c = fixture()
    broken = (*c[:3], c[3] + (c[3][0],), *c[4:])
    with pytest.raises(ValueError, match='identity mismatch'):
        execute(broken)


def test_malformed_terminal_ownership_rejected():
    c = fixture()
    completed = execute(c).state
    still_pending = execute(c, cap=2).state.boundary.driver.boundary.storage.pending_output
    assert still_pending
    old_boundary = completed.boundary.driver.boundary
    broken_storage = replace(old_boundary.storage, pending_output=(replace(still_pending[0], event_id=999),))
    broken_driver = replace(completed.boundary.driver,
                            boundary=replace(old_boundary, storage=broken_storage))
    broken_state = replace(completed, boundary=replace(completed.boundary, driver=broken_driver))
    with pytest.raises(ValueError, match='live pending resource ownership'):
        execute(c, state=broken_state)


def test_unknown_confirmed_request_rejected_before_execution():
    c = fixture()
    finished = execute(c).state
    from spk_simulator.causal_service_quantum_v0 import ServiceConfirmedV0
    svc = finished.boundary.service
    corrupted = replace(svc, confirmed=svc.confirmed + (ServiceConfirmedV0(999, 9),))
    broken = replace(finished, boundary=replace(finished.boundary, service=corrupted))
    with pytest.raises(ValueError, match='identity mismatch'):
        execute(c, state=broken)
