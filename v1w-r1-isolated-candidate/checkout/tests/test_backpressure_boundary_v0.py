"""S3.7d/3b1: atomic bounded storage/claim controller at service boundaries."""
from dataclasses import FrozenInstanceError, replace
import pytest
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryActionsV0 as Actions,
    BackpressureBoundaryStateV0 as State,
    BoundaryCapacityDeniedV0,
    advance_backpressure_boundary_v0 as step,
)
from spk_simulator.event_reservation_v0 import event_reservation_usage_v0
from spk_simulator.event_storage_v0 import routed_storage_usage_v0
from tests.test_backpressure_arbiter_v0 import setup


def fixture(*, capacity=1, count=2, same_pe=False, external=False):
    a, m, storage, ledger, arbiter = setup(
        capacity=capacity, count=count, same_pe=same_pe,
    )
    if not external:
        ledger = replace(ledger, ingress=replace(ledger.ingress, arrivals=(), batch_releases=()))
    return a, m, State(storage, ledger, arbiter)


def advance(ctx, boundary, **kw):
    a, m, state = ctx
    return step(a, m, state, service_boundary=boundary, actions=Actions(**kw))


def next_ctx(ctx, result):
    return ctx[:2] + (result.state,)


def occupancy(result, pe='PE1'):
    return next(u for u in result.pe_usage if u.pe_id == pe)


def two_routes():
    ctx = fixture()
    first = advance(ctx, 0, newly_ready_routes=(11, 10))
    return ctx, first


def test_single_owner_first_reserve():
    ctx, result = two_routes()
    assert result.granted_route_ids == (10,)
    assert tuple(d.route_request_id for d in result.denied) == (11,)
    assert result.state.arbiter.waiting_route_ids == (11,)
    assert occupancy(result).claimed_events == 1
    assert occupancy(result).reserved_routes == 1
    assert occupancy(result, 'PE0').pending_output == 2


def test_denied_route_keeps_exact_output():
    ctx, result = two_routes()
    assert tuple(e.event_id for e in result.state.storage.pending_output) == (10, 11)
    assert result.state.storage.admitted_events == ()
    assert result.operations[-1].operation == 'WAIT'


def test_reserved_route_commits_without_free_slot():
    ctx, result = two_routes()
    done = advance(next_ctx(ctx, result), 1, route_commits=(10,))
    assert not done.state.ledger.reserved_routes
    assert len(done.state.storage.admitted_events) == 1
    assert occupancy(done).reserved_routes == 0
    assert occupancy(done).claimed_events == 1
    assert done.state.arbiter.waiting_route_ids == (11,)


def test_release_retries_denied_route():
    ctx, first = two_routes()
    second = advance(next_ctx(ctx, first), 1, route_commits=(10,))
    third = advance(next_ctx(ctx, second), 2, route_consumptions=(10,))
    assert third.granted_route_ids == (11,)
    assert third.state.arbiter.waiting_route_ids == ()
    assert set(third.state.storage.consumed_ids) == {10}
    assert occupancy(third).reserved_routes == 1


def test_all_events_reach_consumed_no_loss():
    ctx, one = two_routes()
    two = advance(next_ctx(ctx, one), 1, route_commits=(10,))
    three = advance(next_ctx(ctx, two), 2, route_consumptions=(10,))
    four = advance(next_ctx(ctx, three), 3, route_commits=(11,))
    five = advance(next_ctx(ctx, four), 4, route_consumptions=(11,))
    assert five.state.storage.consumed_ids == (10, 11)
    assert not five.state.storage.pending_output
    assert not five.state.storage.admitted_events
    assert not five.state.ledger.reserved_routes
    assert not five.state.arbiter.waiting_route_ids


def test_external_arrival_preempts_new_reservation():
    ctx = fixture(count=1, external=True)
    result = advance(ctx, 0, external_arrivals=(0,), newly_ready_routes=(10,))
    assert result.granted_route_ids == ()
    assert result.state.ledger.external_resident == (0,)
    assert result.state.arbiter.waiting_route_ids == (10,)
    assert [o.operation for o in result.operations] == ['ARRIVE_EXTERNAL', 'WAIT']


def test_external_consumption_allows_retry_same_boundary():
    ctx = fixture(count=1, external=True)
    first = advance(ctx, 0, external_arrivals=(0,), newly_ready_routes=(10,))
    second = advance(next_ctx(ctx, first), 1, external_consumptions=(0,))
    assert second.granted_route_ids == (10,)
    assert second.state.ledger.external_consumed == (0,)
    assert [o.operation for o in second.operations] == ['CONSUME_EXTERNAL', 'RESERVE']


def test_nonbackpressurable_external_overflow_fails_closed():
    ctx = fixture(count=1, external=True)
    # The externally supplied plan announces a non-backpressurable arrival at 1.
    a, m, state = ctx
    ingress = replace(state.ledger.ingress,
                      arrivals=(replace(state.ledger.ingress.arrivals[0], arrival_boundary=1),),
                      batch_releases=(replace(state.ledger.ingress.batch_releases[0], ready_boundary=1),))
    ctx = a, m, replace(state, ledger=replace(state.ledger, ingress=ingress))
    first = advance(ctx, 0, newly_ready_routes=(10,))
    before = first.state
    with pytest.raises(BoundaryCapacityDeniedV0) as caught:
        advance(next_ctx(ctx, first), 1, external_arrivals=(0,))
    assert caught.value.code == 'EXTERNAL_INGRESS_OVERFLOW'
    assert (caught.value.pe_id, caught.value.service_boundary) == ('PE1', 1)
    assert before.ledger.reserved_routes == (10,)
    assert before.storage.pending_output[0].event_id == 10


def test_external_arrival_must_match_bound_boundary():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='bound SERVICE_TIME'):
        advance(ctx, 1, external_arrivals=(0,))


def test_external_consume_before_arrival_rejected():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='not after'):
        advance(ctx, 0, external_consumptions=(0,))


def test_external_consume_requires_resident_event():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='missing, late|not at its bound'):
        advance(ctx, 1, external_consumptions=(0,))


def test_duplicate_action_rejected():
    with pytest.raises(ValueError, match='identities'):
        Actions(newly_ready_routes=(10, 10))


def test_wrong_action_type_rejected():
    with pytest.raises(ValueError, match='identities'):
        Actions(routed_offers=[10])


def test_new_and_completed_route_same_boundary_rejected():
    with pytest.raises(ValueError, match='start and complete'):
        Actions(newly_ready_routes=(10,), route_commits=(10,))


def test_route_commit_and_consume_same_boundary_rejected():
    with pytest.raises(ValueError, match='delivered and consumed'):
        Actions(route_commits=(10,), route_consumptions=(10,))


def test_external_arrive_and_consume_same_boundary_rejected():
    with pytest.raises(ValueError, match='arrive and be consumed'):
        Actions(external_arrivals=(0,), external_consumptions=(0,))


def test_empty_tick_advance_and_monotonicity():
    ctx = fixture(count=0)
    zero = advance(ctx, 0)
    assert not zero.operations
    one = advance(next_ctx(ctx, zero), 4)
    assert one.state.arbiter.last_service_boundary == 4
    with pytest.raises(ValueError, match='strictly'):
        advance(next_ctx(ctx, one), 4)


def test_unknown_route_rejected():
    ctx = fixture(count=0)
    with pytest.raises(ValueError, match='unknown route'):
        advance(ctx, 0, routed_offers=(999,))


def test_unknown_external_rejected():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='unknown external'):
        advance(ctx, 0, external_arrivals=(999,))


def test_can_offer_and_reserve_same_boundary():
    ctx = fixture(count=0)
    out = advance(ctx, 0, routed_offers=(10,), newly_ready_routes=(10,))
    assert out.granted_route_ids == (10,)
    assert [o.operation for o in out.operations] == ['OFFER', 'RESERVE']
    assert occupancy(out, 'PE0').pending_output == 1


def test_output_storage_is_bounded_and_fail_closed():
    a, m, s = fixture(count=0)
    a = replace(a, pes=tuple(replace(pe, output_slots=1) for pe in a.pes))
    ctx = a, m, s
    one = advance(ctx, 0, routed_offers=(10,))
    with pytest.raises(BoundaryCapacityDeniedV0) as caught:
        advance(next_ctx(ctx, one), 1, routed_offers=(11,))
    assert caught.value.code == 'OUTPUT_STORAGE_BLOCKED'
    assert caught.value.pe_id == 'PE0'
    assert tuple(e.event_id for e in one.state.storage.pending_output) == (10,)


def test_same_pe_ownership_transfers():
    ctx = fixture(capacity=1, count=1, same_pe=True)
    one = advance(ctx, 0, newly_ready_routes=(10,))
    two = advance(next_ctx(ctx, one), 1, route_commits=(10,))
    assert occupancy(two, 'PE0').pending_output == 0
    assert occupancy(two, 'PE0').claimed_events == 1
    three = advance(next_ctx(ctx, two), 2, route_consumptions=(10,))
    assert occupancy(three, 'PE0').claimed_events == 0


def test_same_boundary_consume_frees_before_reserve():
    ctx, first = two_routes()
    second = advance(next_ctx(ctx, first), 1, route_commits=(10,))
    third = advance(next_ctx(ctx, second), 2, route_consumptions=(10,))
    assert [o.operation for o in third.operations] == ['CONSUME_ROUTE', 'RESERVE']


def test_deterministic_independent_input_order():
    ctx = fixture(capacity=3, count=0)
    a = advance(ctx, 0, routed_offers=(12, 10, 11), newly_ready_routes=(11, 12, 10))
    b = advance(ctx, 0, routed_offers=(10, 11, 12), newly_ready_routes=(12, 10, 11))
    assert a == b
    assert a.granted_route_ids == (10, 11, 12)


def test_route_ids_remain_distinct():
    ctx = fixture(capacity=3, count=3)
    out = advance(ctx, 0, newly_ready_routes=(10, 11, 12))
    assert out.state.ledger.reserved_routes == (10, 11, 12)


def test_no_event_time_mutation():
    ctx = fixture(count=1)
    old = ctx[1].routes[0].occurrence
    out = advance(ctx, 0, newly_ready_routes=(10,))
    assert ctx[1].routes[0].occurrence == old
    assert out.state.storage.pending_output[0] == old


def test_inputs_not_mutated():
    ctx = fixture()
    baseline = repr(ctx)
    advance(ctx, 0, newly_ready_routes=(10, 11))
    assert repr(ctx) == baseline


def test_result_frozen():
    ctx = fixture(count=0)
    out = advance(ctx, 0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.granted_route_ids = (10,)


def test_wrong_epoch_fails_closed():
    a, m, s = fixture()
    with pytest.raises(ValueError, match='profile or epoch'):
        step(a, m, replace(s, arbiter=replace(s.arbiter, epoch_id='OTHER')), service_boundary=0)


def test_wrong_profile_fails_closed():
    a, m, s = fixture()
    with pytest.raises(ValueError, match='profile or epoch'):
        step(replace(a, profile_id='wrong'), m, s, service_boundary=0)


def test_invalid_action_object():
    ctx = fixture()
    with pytest.raises(TypeError, match='actions'):
        step(ctx[0], ctx[1], ctx[2], service_boundary=0, actions={})


def test_invalid_boundary_bool():
    ctx = fixture()
    with pytest.raises(ValueError, match='SERVICE_TIME'):
        step(ctx[0], ctx[1], ctx[2], service_boundary=True)


def test_route_commit_requires_previous_reservation():
    ctx = fixture(count=1)
    with pytest.raises(ValueError, match='requires a reservation'):
        advance(ctx, 0, route_commits=(10,))


def test_double_route_consumption_fails():
    ctx = fixture(count=1)
    one = advance(ctx, 0, newly_ready_routes=(10,))
    two = advance(next_ctx(ctx, one), 1, route_commits=(10,))
    three = advance(next_ctx(ctx, two), 2, route_consumptions=(10,))
    with pytest.raises(ValueError, match='not admitted|not found|already|consumed|missing|differs from binding'):
        advance(next_ctx(ctx, three), 3, route_consumptions=(10,))


def test_due_external_cannot_be_silently_omitted():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='missing, late|not at its bound'):
        advance(ctx, 0)


def test_cannot_jump_past_unreceived_external():
    ctx = fixture(count=0, external=True)
    with pytest.raises(ValueError, match='missing, late|not at its bound'):
        advance(ctx, 4)


def test_external_duplicate_arrival_across_boundaries_fails():
    ctx = fixture(count=0, external=True)
    first = advance(ctx, 0, external_arrivals=(0,))
    with pytest.raises(ValueError, match='missing, late|not at its bound'):
        advance(next_ctx(ctx, first), 1, external_arrivals=(0,))


def test_failure_leaves_source_state_unchanged_after_partial_actions():
    # First offer succeeds locally, second hits finite output capacity.
    a, m, s = fixture(count=0)
    a = replace(a, pes=tuple(replace(pe, output_slots=1) for pe in a.pes))
    ctx = a, m, s
    baseline = repr(ctx)
    with pytest.raises(BoundaryCapacityDeniedV0, match='OUTPUT_STORAGE_BLOCKED'):
        advance(ctx, 0, routed_offers=(10, 11))
    assert repr(ctx) == baseline
    assert not s.storage.pending_output
    assert not s.ledger.reserved_routes


def test_capacity_overflow_retains_stored_input_and_pending_output():
    ctx = fixture(capacity=1, count=1, external=True)
    one = advance(ctx, 0, external_arrivals=(0,), newly_ready_routes=(10,))
    u = occupancy(one)
    assert u.claimed_events == 1
    assert u.reserved_routes == 0
    assert u.pending_output == 0
    assert occupancy(one, 'PE0').pending_output == 1
