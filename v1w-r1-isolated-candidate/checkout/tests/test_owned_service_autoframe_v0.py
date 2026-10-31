"""Self-framed storage subset, using previously validated SPK integration fixtures."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0 as Service, ServiceFinishedV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.owned_service_autoframe_v0 import (
    derive_owned_storage_frame_v0 as frame,
    advance_autoframed_owned_tick_v0 as tick,
)
from tests.test_owned_service_tick_v0 import context
from tests.test_release_aware_scheduler_v0 import graph


def fixture(*, event_slots=None, ingress_tick=None, release_graph=True):
    architecture, manifest, admission, requests, _, initial = context()
    if event_slots is not None:
        architecture = replace(architecture, pes=tuple(
            replace(pe, event_slots=event_slots) for pe in architecture.pes
        ))
    deps = {r.request_id: () for r in requests}
    if release_graph:
        for emission in admission.groups:
            for route_id in emission.route_request_ids:
                deps[route_id] = (emission.emission_request_id,)
        for route in manifest.routes:
            deps[route.consume_request_id] = (route.route_request_id,)
    dependencies = graph(*((rid, deps[rid]) for rid in sorted(deps)))
    ingress = None
    if ingress_tick is not None:
        ingress = ExternalIngressBindingV0(
            (BoundExternalArrivalV0(0, 2, 'B', 0, 'PE1', ingress_tick, 50),),
            tuple(BatchIngressReleaseV0(rid, ingress_tick if rid == 50 else 0,
                                        (0,) if rid == 50 else ())
                  for rid in (50, 51, 52)),
        )
        old_driver = initial.boundary.driver
        new_ledger = replace(old_driver.boundary.ledger, ingress=ingress)
        initial = replace(initial, boundary=replace(initial.boundary,
                      driver=replace(old_driver,
                        boundary=replace(old_driver.boundary, ledger=new_ledger))))
    return architecture, manifest, admission, requests, dependencies, initial, ingress


def do(c, state=None):
    a, m, adm, reqs, deps, s, ingress = c
    return tick(a, m, adm, reqs, deps, s if state is None else state, ingress=ingress)


def get_frame(c, state=None):
    a, m, adm, reqs, deps, s, ingress = c
    return frame(a, m, adm, reqs, deps, s if state is None else state, ingress=ingress)


def run(c, max_ticks=20):
    state = c[5]
    steps = []
    for _ in range(max_ticks):
        item = do(c, state)
        steps.append(item)
        state = item.result.state
        if len(state.boundary.service.confirmed) == len(c[3]):
            break
    return tuple(steps)


def test_initial_frame_empty():
    f = get_frame(fixture())
    assert f.service_boundary == 0
    assert not f.new_ready_emission_ids
    assert not f.route_commits


def test_initial_tick_grants_output_with_no_caller_frame():
    out = do(fixture())
    assert out.result.output_start_decision.granted_emission_ids == (1,)
    assert out.frame.new_ready_emission_ids == ()


def test_first_emission_is_confirmed_automatically():
    c = fixture()
    t0 = do(c)
    t1 = do(c, t0.result.state)
    assert t1.frame.new_ready_emission_ids == (1,)
    assert t1.result.quantum.confirmed_request_ids == (1,)


def test_route_is_not_submitted_at_same_boundary_as_offer():
    c = fixture()
    t0 = do(c)
    t1 = do(c, t0.result.state)
    assert t1.frame.new_ready_route_ids == ()


def test_routing_is_started_from_resident_output():
    c = fixture()
    t0 = do(c)
    t1 = do(c, t0.result.state)
    t2 = do(c, t1.result.state)
    assert t2.frame.new_ready_route_ids == (10,)
    assert t2.result.quantum.work_finished_request_ids == (10,)


def test_route_requires_finish_before_commit():
    c = fixture()
    t0 = do(c)
    t1 = do(c, t0.result.state)
    t2 = do(c, t1.result.state)
    t3 = do(c, t2.result.state)
    assert t2.frame.route_commits == ()
    assert t3.frame.route_commits == (10,)
    assert 10 in t3.result.quantum.confirmed_request_ids


def test_batch_consumes_after_real_delivery():
    c = fixture()
    steps = run(c)
    t4 = steps[4]
    assert t4.frame.route_consumptions == (10,)
    assert 50 in t4.result.quantum.confirmed_request_ids


def test_full_storage_only_trace_self_frames():
    c = fixture()
    steps = run(c)
    last = steps[-1].result.state
    assert len(last.boundary.service.confirmed) == len(c[3]) == 8
    assert len(steps) == 9
    assert {x.event_id for x in last.boundary.driver.boundary.storage.pending_output} == set()
    assert set(last.boundary.driver.boundary.storage.consumed_ids) == {10, 11, 12}


def test_all_service_frames_are_monotone():
    steps = run(fixture())
    assert tuple(x.frame.service_boundary for x in steps) == tuple(range(len(steps)))


def test_no_duplicate_route_submission():
    steps = run(fixture())
    submissions = [r for s in steps for r in s.frame.new_ready_route_ids]
    assert sorted(submissions) == [10, 11, 12]


def test_no_duplicate_emission_effect():
    steps = run(fixture())
    offers = [r for s in steps for r in s.frame.new_ready_emission_ids]
    assert offers == [1, 2]


def test_no_event_time_mutation():
    c = fixture()
    old = tuple((r.request_id, r.event_time) for r in c[3])
    run(c)
    assert old == tuple((r.request_id, r.event_time) for r in c[3])


def test_repeated_run_deterministic():
    c = fixture()
    assert run(c) == run(c)


def test_reordered_requests_deterministic():
    c = fixture()
    inverted = (*c[:3], c[3][::-1], *c[4:])
    assert run(c) == run(inverted)


def test_immutable_state_result():
    out = do(fixture())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.frame = None


def test_mixed_external_arrival_not_skipped():
    c = fixture(ingress_tick=0)
    steps = run(c)
    assert steps[0].frame.external_arrivals == (0,)
    assert any(s.frame.external_consumptions == (0,) and s.frame.route_consumptions == (10,) for s in steps)
    assert len(steps[-1].result.state.boundary.service.confirmed) == 8


def test_delayed_external_ingress_at_exact_boundary():
    c = fixture(ingress_tick=2)
    steps = run(c)
    assert [s.frame.service_boundary for s in steps if s.frame.external_arrivals] == [2]


def artificial_time1(c, service):
    base = c[5]
    arb = replace(base.boundary.driver.boundary.arbiter, last_service_boundary=0)
    driver = replace(base.boundary.driver,
                     boundary=replace(base.boundary.driver.boundary, arbiter=arb))
    return replace(base, boundary=replace(base.boundary, service=service, driver=driver))


def test_late_missing_external_ingress_rejected():
    c = fixture(ingress_tick=0)
    state = artificial_time1(c, Service(next_service_tick=1))
    with pytest.raises(ValueError, match='missing external ingress'):
        get_frame(c, state)


def test_external_binding_is_required():
    c = fixture(ingress_tick=0)
    with pytest.raises(ValueError, match='ingress binding mismatch'):
        frame(*c[:6])


def test_external_binding_mismatch_rejected():
    c = fixture(ingress_tick=0)
    with pytest.raises(ValueError, match='ingress binding mismatch'):
        frame(*c[:6], ingress=ExternalIngressBindingV0((), ()))


def test_no_silent_blocked_route_commit():
    c = fixture(event_slots=1)
    # The reservation arbiter allows one route at a time, retries later.
    steps = run(c, 30)
    assert len(steps[-1].result.state.boundary.service.confirmed) == len(c[3])
    assert set(steps[-1].result.state.boundary.driver.boundary.storage.consumed_ids) == {10,11,12}


def test_at_capacity_ingress_can_block_forever_without_deadlock_claim():
    c = fixture(event_slots=1, ingress_tick=0)
    # This self-dependent flow cannot deliver route 10 while the external
    # occurrence occupies the sole event slot and its batch waits for route 10.
    steps = run(c, 8)
    assert len(steps) == 8
    assert len(steps[-1].result.state.boundary.service.confirmed) < len(c[3])
    assert all(s.result.quantum.status in ('PROGRESSED', 'WAITING', 'IDLE') for s in steps)


def test_wrong_state_fails_closed():
    c = fixture()
    with pytest.raises(TypeError, match='invalid owned service state'):
        get_frame(c, object())


def test_duplicate_service_request_fails_closed():
    c = fixture()
    broken = (*c[:3], c[3] + (c[3][0],), *c[4:])
    with pytest.raises(ValueError, match='duplicate request'):
        get_frame(broken)


def test_bad_graph_fails_closed_before_route():
    c = fixture()
    deps = graph((1, ()), (2, ()))
    with pytest.raises(ValueError, match='coverage'):
        get_frame((*c[:4], deps, *c[5:]))


def test_unfinished_emission_without_grant_fails_closed():
    c = fixture()
    s = artificial_time1(c, Service(next_service_tick=1,
                              awaiting_confirmation=(ServiceFinishedV0(1,1),)))
    with pytest.raises(ValueError, match='lacks OUTPUT start reservation'):
        get_frame(c, s)


def test_finished_route_without_event_reservation_fails_closed():
    c = fixture()
    s = artificial_time1(c, Service(next_service_tick=1,
                              awaiting_confirmation=(ServiceFinishedV0(10,1),)))
    with pytest.raises(ValueError, match='lacks EVENT reservation'):
        get_frame(c, s)


def test_unknown_internal_completion_fails_closed():
    internal = next((kind for kind in Kind if kind not in (
        Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE, Kind.BATCH_CONSUME,
    )), None)
    if internal is None:
        pytest.skip('local reduced compatibility harness has no internal memory intent')
    c = fixture()
    changed = tuple(replace(r,kind=internal) if r.request_id==50 else r for r in c[3])
    state = artificial_time1(c, Service(next_service_tick=1,
                       awaiting_confirmation=(ServiceFinishedV0(50,1),)))
    with pytest.raises(ValueError, match='unsupported internal service completion'):
        get_frame((*c[:3], changed, c[4], state, c[6]))


def test_no_work_before_dependency_confirmed():
    c = fixture()
    out = do(c)
    assert all(s.request_id not in (10,11,12,50,51,52) for s in out.result.quantum.slices)


def test_reference_result_retains_synthesized_frame():
    x = do(fixture())
    assert x.result.service_boundary == x.frame.service_boundary == 0
