"""Finite EVENT claims are granted from real OUTPUT residency and consumed on delivery."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.causal_service_quantum_v0 import (
    ServiceFinishedV0, ServiceConfirmedV0, ServiceWorkV0,
)
from spk_simulator.event_storage_v0 import consume_routed_event_v0
from spk_simulator.owned_dynamic_route_service_cycle_v0 import (
    OwnedDynamicRouteServiceCycleStateV0 as State,
    advance_owned_dynamic_route_service_cycle_v0 as tick,
)
from tests.test_owned_dynamic_route_transit_v0 import context, filled_static_event_slots


def fresh(*, reserved=(), **kwargs):
    a, registry, routes, transit = context(**kwargs)
    # Base STATE_COMMIT is owned by the internal Core authority, not this lane.
    # Model its service as already finished but not yet effect-confirmed.
    internal_finished = ServiceFinishedV0(3, 3)
    transit = replace(transit, service=replace(
        transit.service,
        awaiting_confirmation=tuple(sorted(
            transit.service.awaiting_confirmation + (internal_finished,),
            key=lambda item: item.request_id,
        )),
    ))
    return a, registry, routes, State(transit, reserved)


def drive(state, ticks):
    results = []
    for _ in range(ticks):
        result = tick(state)
        results.append(result)
        state = result.state
    return results


def test_two_routes_are_reserved_before_any_service():
    _, _, _, state = fresh()
    r = tick(state)
    assert r.newly_reserved_route_request_ids == (5, 6)
    assert r.state.reserved_route_request_ids == (5, 6)
    assert {s.request_id for s in r.service_slices} >= {5, 6}
    assert not r.delivered_route_request_ids


def test_routes_cost_three_service_ticks():
    _, _, _, s = fresh()
    r = drive(s, 3)
    assert [x.delivered_route_request_ids for x in r] == [(), (), (5, 6)]
    assert [x.finished_route_request_ids for x in r] == [(), (), (5, 6)]


def test_atomic_output_event_delivery_and_confirmation():
    _, _, _, s = fresh()
    result = drive(s, 3)[-1]
    assert not result.state.transit.storage.pending_output
    assert {x.event_id for x in result.state.transit.storage.admitted_events} == {5, 6}
    assert {x.request_id for x in result.state.transit.service.confirmed} >= {4, 5, 6}
    assert result.state.reserved_route_request_ids == ()


def test_no_duplicate_delivery_after_finished():
    _, _, _, s = fresh()
    final = drive(s, 3)[-1].state
    again = tick(final)
    assert again.delivered_route_request_ids == ()
    assert again.newly_reserved_route_request_ids == ()


def test_no_early_delivery():
    _, _, _, s = fresh()
    one = tick(s)
    assert {x.event_id for x in one.state.transit.storage.pending_output} == {5, 6}
    assert not one.state.transit.storage.admitted_events


def test_no_forged_service_confirmation():
    _, _, _, s = fresh()
    one = tick(s)
    assert {x.request_id for x in one.state.transit.service.confirmed} == {0, 1, 2, 4}


def test_service_time_increases_by_one():
    _, _, _, s = fresh()
    results = drive(s, 3)
    assert tuple(x.service_tick for x in results) == (4, 5, 6)
    assert results[-1].state.transit.service.next_service_tick == 7


def test_preserves_event_time():
    _, _, routes, s = fresh()
    final = drive(s, 3)[-1]
    assert {x.event_id: x.delivery_event_time for x in final.state.transit.storage.admitted_events} == {x.event_id: x.delivery_event_time for x in routes}


def test_repeatability():
    _, _, _, s = fresh()
    assert tick(s) == tick(s)


def test_pure_transition():
    _, _, _, s = fresh()
    original = s
    tick(s)
    assert s == original


def test_no_source_publication_means_no_dynamic_grant():
    _, _, _, s = fresh(publication=False)
    result = tick(s)
    assert not result.newly_reserved_route_request_ids
    assert not result.delivered_route_request_ids
    assert not result.state.reserved_route_request_ids


def test_full_event_buffer_blocks_reservation():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    full = replace(s, transit=replace(s.transit, storage=filled_static_event_slots(a, s.transit, capacity).storage))
    r = tick(full)
    assert r.newly_reserved_route_request_ids == ()
    assert r.waiting_capacity_route_request_ids == (5, 6)
    assert not r.state.reserved_route_request_ids
    assert not ({5, 6} & {x.request_id for x in r.service_slices})


def test_full_event_buffer_does_not_confirm_delivery():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    full = replace(s, transit=replace(s.transit, storage=filled_static_event_slots(a, s.transit, capacity).storage))
    r = tick(full)
    assert not r.delivered_route_request_ids
    assert {x.event_id for x in r.state.transit.storage.pending_output} == {5, 6}


def test_one_free_slot_limits_grant_count():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    near = replace(s, transit=replace(s.transit, storage=filled_static_event_slots(a, s.transit, capacity - 1).storage))
    r = tick(near)
    assert r.newly_reserved_route_request_ids == (5,)
    assert r.waiting_capacity_route_request_ids == (6,)
    assert r.state.reserved_route_request_ids == (5,)


def test_reservation_persists_through_partial_work():
    _, _, _, s = fresh()
    first, second = drive(s, 2)
    assert first.state.reserved_route_request_ids == (5, 6)
    assert second.state.reserved_route_request_ids == (5, 6)


def test_reservation_removed_on_delivery():
    _, _, _, s = fresh()
    assert drive(s, 3)[-1].state.reserved_route_request_ids == ()


def test_backpressure_recovers_after_event_consumed():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    full = replace(s, transit=replace(s.transit, storage=filled_static_event_slots(a, s.transit, capacity).storage))
    blocked = tick(full)
    freed_storage = consume_routed_event_v0(a, blocked.state.transit.storage, 0, target_pe_id='PE1')
    freed = replace(blocked.state, transit=replace(blocked.state.transit, storage=freed_storage))
    granted = tick(freed)
    assert granted.newly_reserved_route_request_ids == (5,)
    assert granted.waiting_capacity_route_request_ids == (6,)


def test_reject_reservation_without_physical_output():
    _, _, _, s = fresh(publication=False)
    with pytest.raises(ValueError, match='without pending'):
        State(s.transit, (5,))


def test_reject_reservation_for_unknown_route():
    _, _, _, s = fresh()
    with pytest.raises(ValueError, match='without pending'):
        State(s.transit, (999,))


def test_reject_reservation_for_emission_request_id():
    _, _, _, s = fresh()
    with pytest.raises(ValueError):
        State(s.transit, (4,))


def test_reject_duplicate_reservations():
    _, _, _, s = fresh()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.transit, (5, 5))


def test_reject_unsorted_reservations():
    _, _, _, s = fresh()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.transit, (6, 5))


def test_reject_negative_reservations():
    _, _, _, s = fresh()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.transit, (-1,))


def test_reject_non_tuple_reservations():
    _, _, _, s = fresh()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.transit, [5])


def test_reject_reserved_and_completed():
    _, _, _, s = fresh()
    completed = drive(s, 3)[-1].state
    with pytest.raises(ValueError, match='without pending'):
        State(completed.transit, (5,))


def test_reject_unreserved_partial_service():
    _, _, _, s = fresh(reserved=(5,), partial=(5,))
    with pytest.raises(ValueError, match='missing finite EVENT reservation'):
        State(s.transit)


def test_accept_reserved_partial_service():
    _, _, _, s = fresh(reserved=(5,), partial=(5,))
    assert s.reserved_route_request_ids == (5,)


def test_reject_unreserved_finished_service():
    _, _, _, s = fresh(reserved=(5,), awaiting=(5,))
    with pytest.raises(ValueError, match='missing finite EVENT reservation'):
        State(s.transit)


def test_accept_reserved_finished_service():
    _, _, _, s = fresh(reserved=(5,), awaiting=(5,))
    assert s.reserved_route_request_ids == (5,)


def test_delivery_of_previously_finished_route():
    _, _, _, s = fresh(reserved=(5,), awaiting=(5,))
    r = tick(s)
    assert r.delivered_route_request_ids == (5,)
    assert 5 not in r.state.reserved_route_request_ids


def test_reject_event_overcommit_with_reservation():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    full = filled_static_event_slots(a, s.transit, capacity)
    with pytest.raises(ValueError, match='exceeds physical capacity'):
        State(replace(s.transit, storage=full.storage), (5,))


def test_no_batch_consume_authorized():
    _, _, _, s = fresh()
    final = drive(s, 3)[-1]
    assert final.state.transit.storage.consumed_ids == ()
    assert not final.state.transit.registry.registrations[0].unbound_route_request_ids == ()


def test_destination_inventory_still_open():
    _, _, _, s = fresh()
    final = drive(s, 3)[-1]
    from spk_simulator.dynamic_destination_inventory_v0 import derive_dynamic_destination_inventory_v0
    inv = derive_dynamic_destination_inventory_v0(final.state.transit.registry.architecture, final.state.transit.registry, final.state.transit.storage)
    assert not inv.supports_consume_admission
    assert all(b.closure_status == 'OPEN_UNPROVEN' for b in inv.batches)


def test_wrong_transit_input_type():
    with pytest.raises(TypeError, match='invalid owned dynamic'):
        State(None)


def test_wrong_cycle_input_type():
    with pytest.raises(TypeError, match='invalid owned dynamic'):
        tick(None)


def test_frozen_state():
    _, _, _, s = fresh()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        s.transit = None


def test_no_implicit_emission_publication():
    _, _, _, s = fresh(publication=False)
    result = tick(s)
    assert result.state.transit.storage.pending_output == ()


def test_can_resume_from_immutable_partial_snapshot():
    _, _, _, s = fresh()
    one = tick(s)
    final1 = drive(one.state, 2)[-1]
    final2 = drive(s, 3)[-1]
    assert final1.state == final2.state


def test_reusing_old_snapshot_only_replays_same_result_not_new_ids():
    _, _, _, s = fresh()
    assert tick(s) == tick(s)


def test_other_base_service_is_not_falsely_confirmed():
    _, _, _, s = fresh()
    first = tick(s)
    assert 3 not in {x.request_id for x in first.state.transit.service.confirmed}
    assert 3 in {x.request_id for x in first.state.transit.service.awaiting_confirmation}


def test_terminal_output_does_not_invent_route_delivery():
    _, _, _, s = fresh(publication=False)
    result = tick(s)
    assert not result.delivered_route_request_ids


def test_service_budget_is_finite():
    a, _, _, s = fresh()
    r = tick(s)
    counts = {}
    for sl in r.service_slices:
        counts[sl.pe_id] = counts.get(sl.pe_id, 0) + sl.units
    for pe in a.pes:
        assert counts.get(pe.pe_id, 0) <= pe.accesses_per_service_tick


def test_service_does_not_claim_next_tick_without_running():
    _, _, _, s = fresh()
    first = tick(s)
    assert first.state.transit.service.next_service_tick == s.transit.service.next_service_tick + 1


def test_static_event_occupants_are_not_treated_as_reserved_route():
    a, _, _, s = fresh()
    full = filled_static_event_slots(a, s.transit, 1)
    new = State(replace(s.transit, storage=full.storage))
    assert new.reserved_route_request_ids == ()


def test_service_without_event_space_does_not_start_dynamic_route():
    a, _, _, s = fresh()
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    full = State(replace(s.transit, storage=filled_static_event_slots(a, s.transit, capacity).storage))
    result = tick(full)
    assert 5 not in {x.request_id for x in result.state.transit.service.partial + result.state.transit.service.awaiting_confirmation}
    assert 6 not in {x.request_id for x in result.state.transit.service.partial + result.state.transit.service.awaiting_confirmation}


def test_reject_unowned_internal_service_starts():
    _, _, _, state = fresh()
    # Remove the finished-state fixture for the unrelated STATE_COMMIT.
    bad_service = replace(state.transit.service, awaiting_confirmation=())
    bad = State(replace(state.transit, service=bad_service))
    with pytest.raises(ValueError, match='unowned non-route service'):
        tick(bad)
