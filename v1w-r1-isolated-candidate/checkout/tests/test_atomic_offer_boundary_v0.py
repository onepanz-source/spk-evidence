"""Single-boundary coordination between OUTPUT admission and EVENT reservation."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.atomic_offer_boundary_v0 import (
    AtomicOfferBoundaryResultV0, advance_atomic_offer_boundary_v0,
)
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryActionsV0, BoundaryCapacityDeniedV0,
)
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionGroupV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from tests.test_atomic_emission_offer_plan_v0 import fixture


def advance(ctx, boundary=0, **opts):
    return advance_atomic_offer_boundary_v0(*ctx, service_boundary=boundary, **opts)


def next_ctx(ctx, result):
    return ctx[:3] + (result.boundary.state,)


def test_empty_cycle():
    out = advance(fixture())
    assert out.admitted_emission_ids == out.blocked_emission_ids == ()
    assert not out.boundary.operations
    assert out.boundary.state.arbiter.last_service_boundary == 0


def test_one_atomic_emission_publishes_exact_routes():
    out = advance(fixture(), ready_emission_ids=(2,))
    assert out.admitted_emission_ids == (2,)
    assert out.blocked_emission_ids == ()
    assert out.offer_plan.routed_offers == (11, 12)
    assert tuple(e.event_id for e in out.boundary.state.storage.pending_output) == (11, 12)
    assert [e.operation for e in out.boundary.operations] == ['OFFER', 'OFFER']


def test_two_competing_atomic_groups_no_partial_publication():
    out = advance(fixture(), ready_emission_ids=(2, 1))
    assert out.admitted_emission_ids == (1,)
    assert out.blocked_emission_ids == (2,)
    assert tuple(e.event_id for e in out.boundary.state.storage.pending_output) == (10,)


def test_preexisting_output_blocks_group_without_modifying_it():
    ctx = fixture(count=1)
    out = advance(ctx, ready_emission_ids=(2,))
    assert out.blocked_emission_ids == (2,)
    assert out.boundary.state.storage == ctx[3].storage


def test_blocked_emission_can_retry_after_source_output_transfer():
    ctx = fixture(count=1)
    out0 = advance(ctx, ready_emission_ids=(2,), newly_ready_route_ids=(10,))
    assert out0.blocked_emission_ids == (2,)
    assert out0.granted_route_ids == (10,)
    out1 = advance(next_ctx(ctx, out0), 1, route_commits=(10,), ready_emission_ids=(2,))
    assert out1.blocked_emission_ids == (2,)  # Conservative pre-boundary capacity.
    out2 = advance(next_ctx(ctx, out1), 2, ready_emission_ids=(2,))
    assert out2.admitted_emission_ids == (2,)
    assert tuple(e.event_id for e in out2.boundary.state.storage.pending_output) == (11, 12)


def test_new_routes_can_be_reserved_when_offer_is_accepted():
    out = advance(fixture(), ready_emission_ids=(2,), newly_ready_route_ids=(11, 12))
    assert out.granted_route_ids == (11, 12)
    assert out.waiting_route_ids == ()
    assert len(out.boundary.state.ledger.reserved_routes) == 2


def test_denied_route_remains_in_output_and_waiters():
    ctx = fixture()
    arch = replace(ctx[0], pes=tuple(replace(p, event_slots=1) for p in ctx[0].pes))
    ctx = (arch,) + ctx[1:]
    out = advance(ctx, ready_emission_ids=(2,), newly_ready_route_ids=(11, 12))
    assert out.granted_route_ids == (11,)
    assert out.waiting_route_ids == (12,)
    assert tuple(e.event_id for e in out.boundary.state.storage.pending_output) == (11, 12)


def test_denied_route_retry_after_consume():
    ctx = fixture()
    arch = replace(ctx[0], pes=tuple(replace(p, event_slots=1) for p in ctx[0].pes))
    ctx = (arch,) + ctx[1:]
    out0 = advance(ctx, ready_emission_ids=(2,), newly_ready_route_ids=(11, 12))
    out1 = advance(next_ctx(ctx, out0), 1, route_commits=(11,))
    assert out1.waiting_route_ids == (12,)
    out2 = advance(next_ctx(ctx, out1), 2, route_consumptions=(11,))
    assert out2.granted_route_ids == (12,)
    assert out2.waiting_route_ids == ()
    assert out2.boundary.state.storage.consumed_ids == (11,)


def test_route_start_for_blocked_group_rejected_before_any_transition():
    ctx = fixture()
    with pytest.raises(ValueError, match='lacks retained'):
        advance(ctx, ready_emission_ids=(1, 2), newly_ready_route_ids=(12,))
    assert not ctx[3].storage.pending_output


def test_unknown_route_cannot_start():
    with pytest.raises(ValueError, match='lacks retained'):
        advance(fixture(), newly_ready_route_ids=(999,))


def test_existing_retained_route_may_start_without_reoffer():
    out = advance(fixture(count=1), newly_ready_route_ids=(10,))
    assert out.granted_route_ids == (10,)
    assert not out.admitted_emission_ids


def test_no_republication_of_existing_group():
    with pytest.raises(ValueError, match='published'):
        advance(fixture(count=1), ready_emission_ids=(1,))


def test_unknown_emission_fails_closed():
    with pytest.raises(ValueError, match='unknown'):
        advance(fixture(), ready_emission_ids=(999,))


@pytest.mark.parametrize('bad', [None, [1], (1, 1), (True,), ('1',), (-1,)])
def test_bad_ready_emissions_rejected(bad):
    with pytest.raises(ValueError, match='ready emission'):
        advance(fixture(), ready_emission_ids=bad)


@pytest.mark.parametrize('bad', [None, [10], (10, 10), (True,), ('10',), (-1,)])
def test_bad_ready_routes_rejected(bad):
    with pytest.raises(ValueError, match='ready route'):
        advance(fixture(), newly_ready_route_ids=bad)


def with_ingress(ctx, *, capacity=3):
    arrival = BoundExternalArrivalV0(
        input_index=0, event_time=2, node_id='B', channel=0,
        target_pe_id='PE1', arrival_boundary=0, consume_request_id=500,
    )
    ingress = ExternalIngressBindingV0((arrival,), (
        BatchIngressReleaseV0(500, 0, (0,)),
    ))
    arch = replace(ctx[0], pes=tuple(replace(p, event_slots=capacity) for p in ctx[0].pes))
    state = replace(ctx[3], ledger=replace(ctx[3].ledger, ingress=ingress))
    return (arch,) + ctx[1:3] + (state,)


def test_no_skip_due_external_ingress():
    ctx = with_ingress(fixture())
    with pytest.raises(ValueError, match='external ingress'):
        advance(ctx, ready_emission_ids=(2,))


def test_due_external_ingress_admitted_at_bound_service_time():
    ctx = with_ingress(fixture())
    out = advance(ctx, external_arrivals=(0,), ready_emission_ids=(2,))
    assert out.boundary.state.ledger.external_resident == (0,)
    assert any(op.operation == 'ARRIVE_EXTERNAL' for op in out.boundary.operations)
    following = advance(next_ctx(ctx, out), 1, external_consumptions=(0,))
    assert following.boundary.state.ledger.external_consumed == (0,)


def test_nonbackpressurable_external_overflow_fails_closed():
    ctx = with_ingress(fixture(), capacity=1)
    before = repr(ctx)
    # The external event fills EVENT, so the simultaneous request to route
    # after its admission is denied, not silently dropped.
    out = advance(ctx, external_arrivals=(0,), ready_emission_ids=(2,),
                  newly_ready_route_ids=(11, 12))
    assert out.granted_route_ids == ()
    assert out.waiting_route_ids == (11, 12)
    assert repr(ctx) == before


def test_two_due_external_inputs_exceed_capacity_fail_closed():
    ctx = with_ingress(fixture(), capacity=1)
    incoming = ctx[3].ledger.ingress
    another = replace(incoming.arrivals[0], input_index=1, consume_request_id=501)
    another_release = BatchIngressReleaseV0(501, 0, (1,))
    new_ingress = replace(
        incoming,
        arrivals=incoming.arrivals + (another,),
        batch_releases=incoming.batch_releases + (another_release,),
    )
    state = replace(ctx[3], ledger=replace(ctx[3].ledger, ingress=new_ingress))
    changed = ctx[:3] + (state,)
    before = repr(changed)
    with pytest.raises(BoundaryCapacityDeniedV0) as err:
        advance(changed, external_arrivals=(0, 1))
    assert err.value.code == 'EXTERNAL_INGRESS_OVERFLOW'
    assert repr(changed) == before


def test_external_consumption_unlocks_awaiting_route():
    ctx = with_ingress(fixture(), capacity=1)
    out0 = advance(ctx, external_arrivals=(0,), ready_emission_ids=(2,),
                   newly_ready_route_ids=(11, 12))
    out1 = advance(next_ctx(ctx, out0), 1, external_consumptions=(0,))
    assert out1.granted_route_ids == (11,)
    assert out1.waiting_route_ids == (12,)


def test_boundary_replay_strict_increases():
    ctx = fixture()
    out = advance(ctx)
    with pytest.raises(ValueError, match='increase'):
        advance(next_ctx(ctx, out), boundary=0)


def test_failure_does_not_mutate_input_state():
    ctx = fixture()
    before = repr(ctx)
    with pytest.raises(ValueError, match='lacks retained'):
        advance(ctx, ready_emission_ids=(2,), newly_ready_route_ids=(10,))
    assert repr(ctx) == before


def test_empty_fanout_group_admission():
    ctx = fixture()
    zero = AtomicEmissionGroupV0(3, 'PE1', 'D', 6, (), 0, 2)
    admission = replace(ctx[2], groups=ctx[2].groups + (zero,), zero_fanout_emission_count=1)
    out = advance((ctx[0], ctx[1], admission, ctx[3]), ready_emission_ids=(3,))
    assert out.admitted_emission_ids == (3,)
    assert out.boundary.operations == ()


def test_pe_output_usage_never_exceeds_limit():
    out = advance(fixture(), ready_emission_ids=(2,))
    assert all(u.pending_output <= u.output_capacity for u in out.boundary.pe_usage)


def test_pe_event_claims_never_exceed_limit():
    out = advance(fixture(), ready_emission_ids=(2,), newly_ready_route_ids=(11, 12))
    assert all(u.claimed_events <= u.event_capacity for u in out.boundary.pe_usage)


def test_determinism_wrt_ready_order():
    ctx = fixture()
    assert advance(ctx, ready_emission_ids=(1, 2)) == advance(ctx, ready_emission_ids=(2, 1))


def test_result_immutable():
    out = advance(fixture())
    assert isinstance(out, AtomicOfferBoundaryResultV0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.blocked_emission_ids = ()


def test_event_time_untouched():
    ctx = fixture()
    before = repr(ctx[1].routes)
    advance(ctx, ready_emission_ids=(2,))
    assert before == repr(ctx[1].routes)


def test_existing_waiting_route_retries_automatically():
    ctx = fixture()
    arch = replace(ctx[0], pes=tuple(replace(p, event_slots=1) for p in ctx[0].pes))
    ctx = (arch,) + ctx[1:]
    out0 = advance(ctx, ready_emission_ids=(2,), newly_ready_route_ids=(11, 12))
    out1 = advance(next_ctx(ctx, out0), 1, route_commits=(11,))
    assert out1.waiting_route_ids == (12,)


def test_constructor_and_snapshot_types_are_checked():
    ctx = fixture()
    with pytest.raises(TypeError):
        advance((None,) + ctx[1:])
    with pytest.raises(TypeError):
        advance(ctx[:3] + (None,))


def test_zero_boundary_invalid_type():
    for bad in (True, '0', -1):
        with pytest.raises(ValueError):
            advance(fixture(), boundary=bad)
