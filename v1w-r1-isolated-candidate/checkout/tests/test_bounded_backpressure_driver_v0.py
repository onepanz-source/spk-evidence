"""S3.7d/3b2b2b: bounded driver, real native SPK boundary APIs."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.bounded_backpressure_driver_v0 import (
    BackpressureServiceFrameV0, BoundedBackpressureStateV0,
    advance_bounded_backpressure_v0, run_bounded_backpressure_v0,
)
from spk_simulator.backpressure_boundary_v0 import BoundaryCapacityDeniedV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionGroupV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from tests.test_atomic_emission_offer_plan_v0 import fixture


def ctx(*, output_slots=2, event_slots=3, count=0):
    arch, manifest, admission, state = fixture(output_slots=output_slots, count=count)
    arch = replace(arch, pes=tuple(replace(pe, event_slots=event_slots) for pe in arch.pes))
    return arch, manifest, admission, BoundedBackpressureStateV0(state)


def step(context, boundary, **kwargs):
    arch, manifest, admission, state = context
    after, result = advance_bounded_backpressure_v0(
        arch, manifest, admission, state,
        BackpressureServiceFrameV0(boundary, **kwargs),
    )
    return (*context[:3], after), result


def test_initial_empty_boundary_idle():
    new, result = step(ctx(), 0)
    assert result.status == 'IDLE'
    assert result.pending_emission_ids == ()
    assert new[3].boundary.arbiter.last_service_boundary == 0


def test_admit_single_atomic_group():
    new, result = step(ctx(), 0, new_ready_emission_ids=(2,))
    assert result.transition.admitted_emission_ids == (2,)
    assert result.status == 'PROGRESSED'
    assert tuple(e.event_id for e in new[3].boundary.storage.pending_output) == (11, 12)
    assert new[3].admitted_emission_ids == (2,)


def test_blocked_group_remains_in_identity_queue():
    new, result = step(ctx(), 0, new_ready_emission_ids=(2, 1))
    assert result.transition.admitted_emission_ids == (1,)
    assert result.pending_emission_ids == (2,)
    assert len(new[3].boundary.storage.pending_output) == 1


def test_automatic_retry_after_output_is_released():
    c, first = step(ctx(), 0, new_ready_emission_ids=(1, 2),
                    new_ready_route_ids=(10,))
    assert first.pending_emission_ids == (2,)
    c, second = step(c, 1, route_commits=(10,))
    assert second.pending_emission_ids == (2,)
    assert second.status == 'PROGRESSED'
    c, third = step(c, 2)
    assert third.transition.admitted_emission_ids == (2,)
    assert third.pending_emission_ids == ()
    assert set(e.event_id for e in c[3].boundary.storage.pending_output) == {11, 12}


def test_empty_waiting_cycle_does_not_claim_deadlock():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(1, 2))
    c, result = step(c, 1)
    assert result.status == 'WAITING'
    assert result.pending_emission_ids == (2,)


def test_route_arbiter_retries_without_reannouncing_route():
    c, first = step(ctx(event_slots=1), 0,
                    new_ready_emission_ids=(2,), new_ready_route_ids=(11, 12))
    assert first.transition.granted_route_ids == (11,)
    assert first.transition.waiting_route_ids == (12,)
    c, middle = step(c, 1, route_commits=(11,))
    assert middle.transition.waiting_route_ids == (12,)
    c, later = step(c, 2, route_consumptions=(11,))
    assert later.transition.granted_route_ids == (12,)
    assert later.transition.waiting_route_ids == ()
    c, _ = step(c, 3, route_commits=(12,))
    c, end = step(c, 4, route_consumptions=(12,))
    assert c[3].boundary.storage.consumed_ids == (11, 12)
    assert end.status == 'PROGRESSED'


def test_no_retry_duplication_of_admitted_emission():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(2,))
    c, second = step(c, 1)
    assert second.transition.offer_plan.routed_offers == ()
    assert len(c[3].boundary.storage.pending_output) == 2


def test_reannouncing_submission_rejected():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(2,))
    with pytest.raises(ValueError, match='readiness replayed'):
        step(c, 1, new_ready_emission_ids=(2,))


def test_reannouncing_waiting_emission_rejected():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(1, 2))
    with pytest.raises(ValueError, match='readiness replayed'):
        step(c, 1, new_ready_emission_ids=(2,))


def test_route_readiness_replay_rejected():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(2,), new_ready_route_ids=(11,))
    with pytest.raises(ValueError, match='route readiness replayed'):
        step(c, 1, new_ready_route_ids=(11,))


def test_unknown_emission_rejected():
    with pytest.raises(ValueError, match='unknown emission'):
        step(ctx(), 0, new_ready_emission_ids=(99,))


def test_unknown_route_rejected():
    with pytest.raises(ValueError, match='unknown route'):
        step(ctx(), 0, new_ready_route_ids=(99,))


def test_premature_route_start_refused_without_state_mutation():
    c = ctx()
    snapshot = repr(c)
    with pytest.raises(ValueError, match='lacks retained'):
        step(c, 0, new_ready_route_ids=(11,))
    assert repr(c) == snapshot


def test_nonconsecutive_boundary_rejected():
    c, _ = step(ctx(), 0)
    for invalid in (0, 2, 100):
        with pytest.raises(ValueError, match='consecutive'):
            step(c, invalid)


def test_first_boundary_must_be_zero():
    with pytest.raises(ValueError, match='consecutive'):
        step(ctx(), 1)


def test_full_run_multiple_steps():
    c = ctx()
    frames = (
        BackpressureServiceFrameV0(0, new_ready_emission_ids=(1, 2),
                                   new_ready_route_ids=(10,)),
        BackpressureServiceFrameV0(1, route_commits=(10,)),
        BackpressureServiceFrameV0(2),
        BackpressureServiceFrameV0(3, new_ready_route_ids=(11, 12)),
        BackpressureServiceFrameV0(4, route_commits=(11, 12)),
        BackpressureServiceFrameV0(5, route_consumptions=(10, 11, 12)),
    )
    run = run_bounded_backpressure_v0(*c, frames)
    assert len(run.steps) == 6
    assert run.steps[0].pending_emission_ids == (2,)
    assert run.steps[2].transition.admitted_emission_ids == (2,)
    assert run.state.boundary.storage.consumed_ids == (10, 11, 12)
    assert run.state.pending_emission_ids == ()
    assert run.steps[-1].status == 'PROGRESSED'


def test_runner_resume_is_equivalent_to_one_shot():
    c = ctx()
    frames = (BackpressureServiceFrameV0(0, new_ready_emission_ids=(2,)),
              BackpressureServiceFrameV0(1, new_ready_route_ids=(11, 12)),
              BackpressureServiceFrameV0(2, route_commits=(11, 12)))
    all_at_once = run_bounded_backpressure_v0(*c, frames)
    first = run_bounded_backpressure_v0(*c, frames[:2])
    rest = run_bounded_backpressure_v0(*c[:3], first.state, frames[2:])
    assert rest.state == all_at_once.state
    assert first.steps + rest.steps == all_at_once.steps


def test_runner_empty_frames():
    c = ctx()
    run = run_bounded_backpressure_v0(*c, ())
    assert run.steps == ()
    assert run.state == c[-1]


def test_frame_limit_is_explicit_not_deadlock():
    c = ctx()
    with pytest.raises(RuntimeError, match='FRAME_LIMIT'):
        run_bounded_backpressure_v0(*c, (
            BackpressureServiceFrameV0(0), BackpressureServiceFrameV0(1),
        ), max_frames=1)


@pytest.mark.parametrize('invalid', (0, -1, True, 1.0, None))
def test_bad_frame_limit_rejected(invalid):
    with pytest.raises(ValueError, match='max_frames'):
        run_bounded_backpressure_v0(*ctx(), (), max_frames=invalid)


def test_no_mutation_on_later_frame_failure():
    c = ctx()
    before = repr(c)
    frames = (BackpressureServiceFrameV0(0, new_ready_emission_ids=(2,)),
              BackpressureServiceFrameV0(1, new_ready_emission_ids=(2,)))
    with pytest.raises(ValueError):
        run_bounded_backpressure_v0(*c, frames)
    assert repr(c) == before


@pytest.mark.parametrize('invalid', (True, None, '0', -1))
def test_invalid_boundary_type_rejected(invalid):
    with pytest.raises(ValueError, match='SERVICE_TIME'):
        BackpressureServiceFrameV0(invalid)


@pytest.mark.parametrize('invalid', ([1], None, ('1',), (True,), (1, 1), (-1,)))
def test_bad_identity_lists_rejected(invalid):
    with pytest.raises(ValueError):
        BackpressureServiceFrameV0(0, new_ready_emission_ids=invalid)


def test_status_waiting_for_event_slot():
    c, _ = step(ctx(event_slots=1), 0,
                new_ready_emission_ids=(2,), new_ready_route_ids=(11, 12))
    c, result = step(c, 1)
    assert result.status == 'WAITING'
    assert result.transition.waiting_route_ids == (12,)


def test_missing_due_external_arrival_fails_closed():
    c = ctx()
    a, manifest, admission, driver = c
    ingress = ExternalIngressBindingV0((BoundExternalArrivalV0(
        0, 2, 'B', 0, 'PE1', 0, 500,
    ),), (BatchIngressReleaseV0(500, 0, (0,)),))
    driver = replace(driver, boundary=replace(driver.boundary,
                                             ledger=replace(driver.boundary.ledger, ingress=ingress)))
    c = (a, manifest, admission, driver)
    with pytest.raises(ValueError, match='external ingress'):
        step(c, 0)
    c, result = step(c, 0, external_arrivals=(0,))
    assert result.status == 'PROGRESSED'
    assert c[3].boundary.ledger.external_resident == (0,)


def test_storage_capacity_remains_finite():
    c, first = step(ctx(output_slots=2), 0, new_ready_emission_ids=(1, 2))
    assert first.pending_emission_ids == (2,)
    assert len(c[-1].boundary.storage.pending_output) == 1
    assert all(u.pending_output <= u.output_capacity for u in first.transition.boundary.pe_usage)


def test_replay_deterministic():
    c = ctx()
    frames = (BackpressureServiceFrameV0(0, new_ready_emission_ids=(2, 1)),
              BackpressureServiceFrameV0(1))
    assert run_bounded_backpressure_v0(*c, frames) == run_bounded_backpressure_v0(*c, frames)


def test_reordering_ready_identities_preserves_result():
    c = ctx()
    a = step(c, 0, new_ready_emission_ids=(1, 2))[1]
    b = step(c, 0, new_ready_emission_ids=(2, 1))[1]
    assert a == b


def test_driver_state_invalid_partition_rejected():
    c = ctx()
    with pytest.raises(ValueError, match='not conserved'):
        BoundedBackpressureStateV0(c[-1].boundary, pending_emission_ids=(1,))


def test_admitted_emission_evidence_checked():
    c, _ = step(ctx(), 0, new_ready_emission_ids=(2,))
    tampered = replace(c[-1], boundary=replace(c[-1].boundary,
                         storage=replace(c[-1].boundary.storage, pending_output=())))
    with pytest.raises(ValueError, match='missing owned route'):
        step(c[:3] + (tampered,), 1)


def test_immutable_records():
    c, result = step(ctx(), 0)
    with pytest.raises((AttributeError, FrozenInstanceError)):
        result.status = 'DEADLOCK'
    with pytest.raises((AttributeError, FrozenInstanceError)):
        c[-1].pending_emission_ids = (999,)


def test_event_time_is_not_converted():
    c = ctx()
    before = repr(c[1].routes)
    result = run_bounded_backpressure_v0(*c, (
        BackpressureServiceFrameV0(0, new_ready_emission_ids=(2,)),
        BackpressureServiceFrameV0(1),
    ))
    assert repr(c[1].routes) == before
    assert result.steps[1].service_boundary == 1
