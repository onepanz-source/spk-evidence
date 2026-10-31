"""Integrated, ledger-authorized OUTPUT grants and witnessed service quantum."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.authenticated_service_bridge_v0 import AuthenticatedServiceBoundaryStateV0
from spk_simulator.bounded_backpressure_driver_v0 import (
    BackpressureServiceFrameV0 as Frame, advance_bounded_backpressure_v0
)
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0 as Service, ServiceFinishedV0, ServiceConfirmedV0
)
from spk_simulator.output_start_reservation_v0 import OutputStartLedgerV0
from spk_simulator.owned_service_tick_v0 import (
    OwnedServiceTickStateV0 as Owned,
    advance_owned_service_tick_v0 as step,
)
from tests.test_service_effect_authority_v0 import setting
from tests.test_release_aware_scheduler_v0 import graph


def context(*, dependencies=None, capacity=None, service=None, driver=None, output=None):
    arch, manifest, admission, requests, baseline = setting()
    if capacity is not None:
        arch = replace(arch, pes=tuple(replace(pe, output_slots=capacity) for pe in arch.pes))
        admission = replace(admission, groups=tuple(
            replace(g, output_capacity=capacity) for g in admission.groups
        ))
    if driver is None:
        driver = baseline
    if service is None:
        service = Service()
    if output is None:
        output = OutputStartLedgerV0(arch.profile_id, admission.epoch_id)
    deps = dependencies if dependencies is not None else graph(*((r.request_id, ()) for r in requests))
    return arch, manifest, admission, requests, deps, Owned(
        AuthenticatedServiceBoundaryStateV0(service, driver), output,
    )


def run(ctx, boundary, **kwargs):
    return step(*ctx, Frame(boundary, **kwargs))


def test_first_boundary_automatically_grants_one_finite_bundle():
    out = run(context(), 0)
    assert out.output_start_decision.granted_emission_ids == (1,)
    assert out.output_start_decision.blocked_emission_ids == (2,)
    assert tuple(r.emission_request_id for r in out.state.output.active) == (1,)
    assert all(e.event_id not in (10, 11, 12) for e in out.state.boundary.driver.boundary.storage.pending_output)


def test_first_quantum_serves_only_output_granted_emission():
    out = run(context(), 0)
    served = {x.request_id for x in out.quantum.slices}
    assert 1 in served
    assert 2 not in served
    assert out.quantum.confirmed_request_ids == ()


def test_service_does_not_imply_output_publication():
    out = run(context(), 0)
    assert 1 in {x.request_id for x in out.state.boundary.service.awaiting_confirmation}
    assert out.state.output.completed_emission_ids == ()


def test_publication_requires_previously_reserved_start():
    arch, manifest, admission, requests, initial = setting()
    driver = advance_bounded_backpressure_v0(arch, manifest, admission, initial, Frame(0))[0]
    ctx = context(service=Service(next_service_tick=1, awaiting_confirmation=(ServiceFinishedV0(1, 1),)),
                  driver=driver)
    with pytest.raises(ValueError, match='in-flight emission without OUTPUT start grant'):
        run(ctx, 1, new_ready_emission_ids=(1,))


def test_second_tick_publication_confirms_first_bundle():
    out0 = run(context(), 0)
    out1 = run((*context()[:5], out0.state), 1, new_ready_emission_ids=(1,))
    assert out1.authenticated_effects.confirmed_request_ids == (1,)
    assert out1.quantum.confirmed_request_ids == (1,)
    assert out1.state.output.completed_emission_ids == (1,)
    assert tuple(r.emission_request_id for r in out1.state.output.active) == ()
    assert {e.event_id for e in out1.state.boundary.driver.boundary.storage.pending_output} == {10}
    assert out1.output_start_decision.blocked_emission_ids == (2,)


def test_waiting_bundle_retries_automatically_after_route_commit():
    c = context()
    t0 = run(c, 0)
    c1 = (*c[:5], t0.state)
    t1 = run(c1, 1, new_ready_emission_ids=(1,), new_ready_route_ids=(10,))
    # At tick 1 a route may be reserved and consumes work; no instant delivery.
    assert 10 not in t1.authenticated_effects.confirmed_request_ids
    # OUTPUT capacity freed at tick 2 must not be granted at tick 2 itself.
    c2 = (*c[:5], t1.state)
    t2 = run(c2, 2, route_commits=(10,))
    assert 2 in t2.output_start_decision.blocked_emission_ids
    assert 10 in t2.authenticated_effects.confirmed_request_ids
    # Tick 3 sees newly freed slot: group 2 requires two, and PE0 has two.
    c3 = (*c[:5], t2.state)
    t3 = run(c3, 3)
    assert t3.output_start_decision.granted_emission_ids == (2,)
    assert 2 in {x.request_id for x in t3.quantum.slices}


def test_output_start_grants_remain_unique_after_wait():
    first = run(context(), 0)
    second = run((*context()[:5], first.state), 1)
    assert second.output_start_decision.granted_emission_ids == ()
    assert second.output_start_decision.blocked_emission_ids == (2,)
    assert tuple(r.emission_request_id for r in second.state.output.active) == (1,)


def test_released_capacity_not_reused_at_same_boundary():
    first = run(context(), 0)
    second = run((*context()[:5], first.state), 1, new_ready_emission_ids=(1,))
    assert 2 not in second.output_start_decision.granted_emission_ids


def test_wrong_boundary_rejected():
    with pytest.raises(ValueError, match='SERVICE_TIME'):
        run(context(), 4)


def test_invalid_frame_type_rejected():
    with pytest.raises(TypeError, match='invalid service frame'):
        step(*context(), None)


def test_invalid_state_type_rejected():
    c = context()
    with pytest.raises(TypeError, match='invalid owned tick state'):
        step(*c[:5], None, Frame(0))


def test_causal_dependency_prevents_early_output_grant():
    c = context()
    pairs = tuple((r.request_id, (50,) if r.request_id == 2 else ()) for r in c[3])
    c = (*c[:4], graph(*pairs), c[-1])
    first = run(c, 0)
    assert first.output_start_decision.blocked_emission_ids == ()
    assert 2 not in first.output_start_decision.granted_emission_ids


def test_output_grant_is_not_route_grant():
    out = run(context(), 0)
    assert not any(x.request_id in (10, 11, 12) for x in out.quantum.slices)


def test_no_silent_state_mutation_on_invalid_effect():
    c = context()
    first = run(c, 0)
    cc = (*c[:5], first.state)
    before = repr(first.state)
    with pytest.raises(ValueError):
        run(cc, 1, route_commits=(10,))
    assert repr(first.state) == before


def test_state_is_immutable():
    result = run(context(), 0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.state.output = result.state.output


def test_repeat_from_same_snapshot_deterministic():
    c = context()
    assert run(c, 0) == run(c, 0)


def test_reordering_request_tuple_deterministic():
    c = context()
    inverse = (c[0], c[1], c[2], c[3][::-1], c[4], c[5])
    assert run(c, 0) == run(inverse, 0)


def test_bad_graph_fails_closed():
    c = context()
    with pytest.raises(ValueError):
        run((*c[:4], graph((1, ()), (2, ())), c[-1]), 0)


def test_unknown_emission_in_admission_rejected():
    c = context()
    bad = replace(c[2], groups=(replace(c[2].groups[0], emission_request_id=999),) + c[2].groups[1:])
    with pytest.raises(ValueError, match='coverage mismatch'):
        run((*c[:2], bad, *c[3:]), 0)


def test_invalid_ledger_profile_rejected():
    c = context()
    bad_state = Owned(c[-1].boundary, OutputStartLedgerV0('invalid', c[2].epoch_id))
    with pytest.raises(ValueError, match='profile'):
        run((*c[:5], bad_state), 0)


def test_frame_cannot_fabricate_completion():
    c = context()
    with pytest.raises(ValueError, match='prior start grant'):
        run(c, 0, new_ready_emission_ids=(1,))


def test_no_implicit_event_time_mutation():
    c = context()
    before = tuple((r.request_id, r.event_time) for r in c[3])
    run(c, 0)
    assert tuple((r.request_id, r.event_time) for r in c[3]) == before


def test_multiunit_emission_keeps_start_grant_until_publication():
    c = context()
    slow_requests = tuple(replace(r, service_units=3) if r.request_id == 1 else r
                          for r in c[3])
    c = (*c[:3], slow_requests, *c[4:])
    first = run(c, 0)
    assert any(x.request_id == 1 for x in first.state.boundary.service.partial)
    assert first.state.output.active[0].emission_request_id == 1
    second = run((*c[:5], first.state), 1)
    assert second.state.output.active[0].emission_request_id == 1
    assert 1 in {x.request_id for x in second.state.boundary.service.awaiting_confirmation}
    third = run((*c[:5], second.state), 2, new_ready_emission_ids=(1,))
    assert third.authenticated_effects.confirmed_request_ids == (1,)
    assert third.state.output.completed_emission_ids == (1,)


def test_route_start_does_not_bypass_unfinished_emission_dependency():
    c = context()
    depends = graph(*((r.request_id, (1,) if r.request_id == 10 else ())
                      for r in c[3]))
    c = (*c[:4], depends, c[-1])
    initial = run(c, 0)
    before = repr(initial.state)
    with pytest.raises(ValueError):
        run((*c[:5], initial.state), 1, new_ready_route_ids=(10,))
    assert repr(initial.state) == before


def test_previous_confirmed_emission_needs_ledger_evidence():
    c = context(service=Service(confirmed=(ServiceConfirmedV0(1, 0),)))
    with pytest.raises(ValueError, match='confirmation mismatch'):
        run(c, 0)


def test_reservation_capacity_unaffected_by_requested_order():
    c = context()
    a = run(c, 0)
    assert a.output_start_decision.granted_emission_ids == (1,)
    assert a.output_start_decision.blocked_emission_ids == (2,)


def test_no_post_effect_capacity_borrowed_for_new_start():
    c = context()
    t0 = run(c, 0)
    t1 = run((*c[:5], t0.state), 1, new_ready_emission_ids=(1,), new_ready_route_ids=(10,))
    t2 = run((*c[:5], t1.state), 2, route_commits=(10,))
    assert t2.output_start_decision.granted_emission_ids == ()
    assert t2.state.output.active == ()
    t3 = run((*c[:5], t2.state), 3)
    assert t3.output_start_decision.granted_emission_ids == (2,)
