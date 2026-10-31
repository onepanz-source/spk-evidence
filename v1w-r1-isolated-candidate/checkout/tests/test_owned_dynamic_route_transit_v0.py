"""Dynamic route transport: service-finished is not route-delivered."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0, ServiceConfirmedV0, ServiceFinishedV0, ServiceWorkV0,
)
from spk_simulator.event_storage_v0 import (
    RoutedStorageStateV0, offer_routed_output_v0, admit_routed_event_v0,
)
from spk_simulator.owned_dynamic_route_transit_v0 import (
    OwnedDynamicRouteTransitStateV0 as State,
    advance_owned_dynamic_route_transit_v0 as step,
)
from tests.test_owned_dynamic_service_registration_v0 import scenario, do


def context(*, publication=True, awaiting=(), completed=(), partial=(), tick=4):
    c = scenario()
    registry = do(c).state
    emission = registry.registrations[0].allocation.emission_request_id
    routes = tuple(route.occurrence for route in registry.registrations[0].allocation.topology.routes)
    storage = RoutedStorageStateV0(c[0].profile_id, 'E0')
    if publication:
        for route in routes:
            storage = offer_routed_output_v0(c[0], storage, route)
    confirmed = tuple(ServiceConfirmedV0(rid, 1) for rid in sorted((0, 1, 2) + ((emission,) if publication else ()) + completed))
    quantum = ServiceQuantumStateV0(
        next_service_tick=tick,
        partial=tuple(ServiceWorkV0(rid, 1) for rid in sorted(partial)),
        awaiting_confirmation=tuple(ServiceFinishedV0(rid, 3) for rid in sorted(awaiting)),
        confirmed=confirmed,
    )
    return c[0], registry, routes, State(registry, storage, quantum)


def test_two_dynamic_routes_admitted_after_service():
    a, registry, routes, s = context(awaiting=(5, 6))
    result = step(s)
    assert result.delivered_route_request_ids == (5, 6)
    assert result.blocked_route_request_ids == ()
    assert result.status == 'PROGRESSED'
    assert set(x.event_id for x in result.state.storage.admitted_events) == {5, 6}
    assert result.state.storage.pending_output == ()
    assert {x.request_id for x in result.state.service.confirmed} >= {4, 5, 6}
    assert result.state.service.awaiting_confirmation == ()
    assert result.inventory.supports_consume_admission is False
    assert all(b.closure_status == 'OPEN_UNPROVEN' for b in result.inventory.batches)


def test_service_finished_does_not_mean_delivered_before_step():
    _, _, _, s = context(awaiting=(5, 6))
    assert {x.event_id for x in s.storage.pending_output} == {5, 6}
    assert {x.event_id for x in s.storage.admitted_events} == set()
    assert {x.request_id for x in s.service.awaiting_confirmation} == {5, 6}


def test_no_implicit_publication_or_grant():
    _, _, _, s = context(publication=False)
    r = step(s)
    assert r.status == 'IDLE'
    assert r.state == s


def test_publication_without_route_service_does_not_deliver():
    _, _, _, s = context()
    r = step(s)
    assert r.status == 'IDLE'
    assert len(r.state.storage.pending_output) == 2


def test_partial_route_service_does_not_deliver():
    _, _, _, s = context(partial=(5,))
    assert step(s).delivered_route_request_ids == ()


def test_one_finished_route_only():
    _, _, _, s = context(awaiting=(5,))
    r = step(s)
    assert r.delivered_route_request_ids == (5,)
    assert tuple(x.event_id for x in r.state.storage.pending_output) == (6,)


def test_repeated_step_idempotent_after_delivery():
    _, _, _, s = context(awaiting=(5, 6))
    once = step(s)
    twice = step(once.state)
    assert twice.status == 'IDLE'
    assert twice.state == once.state


def test_earlier_state_is_immutable():
    _, _, _, s = context(awaiting=(5, 6))
    before = s
    step(s)
    assert s == before
    assert len(s.storage.pending_output) == 2


def test_parallel_distinct_occurrences_retained():
    _, _, routes, s = context(awaiting=(5, 6))
    r = step(s)
    assert {e.event_id for e in r.state.storage.admitted_events} == {x.event_id for x in routes}
    assert len(r.inventory.batches) == 2


def test_wrong_epoch_rejected():
    _, _, _, s = context()
    with pytest.raises(ValueError, match='epoch'):
        replace(s, storage=replace(s.storage, epoch_id='WRONG'))


def test_wrong_profile_rejected():
    _, _, _, s = context()
    with pytest.raises(ValueError, match='profile'):
        replace(s, storage=replace(s.storage, profile_id='WRONG'))


def test_unregistered_dynamic_route_rejected():
    _, _, routes, s = context()
    bad = replace(routes[0], event_id=999)
    with pytest.raises(ValueError, match='unknown dynamic'):
        replace(s, storage=replace(s.storage, pending_output=(bad, routes[1])))


def test_wrong_occurrence_provenance_rejected():
    _, _, routes, s = context()
    bad = replace(routes[0], target_channel=999)
    with pytest.raises(ValueError, match='provenance'):
        replace(s, storage=replace(s.storage, pending_output=(bad, routes[1])))


def test_half_published_fanout_rejected():
    _, _, routes, s = context()
    with pytest.raises(ValueError, match='partial dynamic'):
        replace(s, storage=replace(s.storage, pending_output=(routes[0],)))


def test_published_without_source_service_confirmation_rejected():
    _, _, _, s = context()
    altered = replace(s.service, confirmed=tuple(x for x in s.service.confirmed if x.request_id != 4))
    with pytest.raises(ValueError, match='source emission'):
        replace(s, service=altered)


def test_route_finished_without_source_confirmation_rejected():
    _, _, _, s = context(awaiting=(5,))
    altered = replace(s.service, confirmed=tuple(x for x in s.service.confirmed if x.request_id != 4))
    with pytest.raises(ValueError):
        replace(s, service=altered)


def test_false_delivered_route_without_service_receipt_rejected():
    a, _, _, s = context()
    simulated = admit_routed_event_v0(a, s.storage, 5)
    with pytest.raises(ValueError, match='without confirmed service'):
        replace(s, storage=simulated)


def test_route_confirmed_but_still_pending_rejected():
    _, _, _, s = context()
    altered = replace(s.service, confirmed=tuple(sorted(s.service.confirmed + (ServiceConfirmedV0(5, 3),), key=lambda x: x.request_id)))
    with pytest.raises(ValueError, match='confirmed before'):
        replace(s, service=altered)


def test_route_service_before_output_rejected():
    _, _, _, s = context(publication=False)
    service = replace(s.service, awaiting_confirmation=(ServiceFinishedV0(5, 3),))
    with pytest.raises(ValueError, match='causal dependencies'):
        replace(s, service=service)


def test_earlier_route_consumption_is_not_allowed_without_confirmed_service():
    a, _, _, s = context()
    future = admit_routed_event_v0(a, s.storage, 5)
    future = replace(future, admitted_events=tuple(x for x in future.admitted_events if x.event_id != 5), consumed_ids=(5,))
    with pytest.raises(ValueError, match='without confirmed service'):
        replace(s, storage=future)


def test_finished_route_must_respect_boundary():
    _, _, _, s = context(awaiting=(5,))
    with pytest.raises(ValueError, match='future'):
        replace(s, service=replace(s.service, next_service_tick=2))


def test_static_ids_never_construed_dynamic():
    _, _, routes, s = context()
    alias = replace(routes[0], event_id=1)
    altered = replace(s.storage, consumed_ids=(alias.event_id,))
    state = replace(s, storage=altered)
    assert 1 in step(state).inventory.untracked_static_storage_ids


def test_cannot_change_frozen_snapshot_fields():
    _, _, _, s = context()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        s.storage = None


def test_invalid_input_type_rejected():
    with pytest.raises(TypeError, match='invalid transit state'):
        step(None)


def test_deterministic_transition():
    _, _, _, s = context(awaiting=(5, 6))
    assert step(s) == step(s)


def filled_static_event_slots(arch, state, count):
    routes = state.registry.registrations[0].allocation.topology.routes
    first = routes[0].occurrence
    added = tuple(replace(first, event_id=i) for i in range(count))
    return replace(state, storage=replace(state.storage, admitted_events=added))


def test_event_full_is_backpressure_not_false_delivery():
    a, _, _, s = context(awaiting=(5, 6))
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    s = filled_static_event_slots(a, s, capacity)
    r = step(s)
    assert r.status == 'BACKPRESSURE'
    assert r.delivered_route_request_ids == ()
    assert r.blocked_route_request_ids == (5, 6)
    assert r.state == s
    assert {x.request_id for x in r.state.service.awaiting_confirmation} == {5, 6}
    assert not r.inventory.supports_consume_admission


def test_only_available_event_slots_are_used():
    a, _, _, s = context(awaiting=(5, 6))
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    s = filled_static_event_slots(a, s, capacity-1)
    r = step(s)
    assert r.delivered_route_request_ids == (5,)
    assert r.blocked_route_request_ids == (6,)
    assert {x.request_id for x in r.state.service.awaiting_confirmation} == {6}
    assert {x.event_id for x in r.state.storage.pending_output} == {6}


def test_backpressure_retries_after_static_event_slot_is_freed():
    from spk_simulator.event_storage_v0 import consume_routed_event_v0
    a, _, _, s = context(awaiting=(5, 6))
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    blocked = step(filled_static_event_slots(a, s, capacity))
    freed = consume_routed_event_v0(a, blocked.state.storage, 0, target_pe_id='PE1')
    resumed = replace(blocked.state, storage=freed)
    result = step(resumed)
    assert result.delivered_route_request_ids == (5,)
    assert result.blocked_route_request_ids == (6,)
    assert {x.request_id for x in result.state.service.confirmed} >= {4, 5}


def test_backpressure_does_not_advance_service_time():
    a, _, _, s = context(awaiting=(5, 6))
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    blocked = step(filled_static_event_slots(a, s, capacity))
    assert blocked.state.service.next_service_tick == s.service.next_service_tick


def test_delivery_does_not_consume_any_event():
    _, _, _, s = context(awaiting=(5, 6))
    result = step(s)
    assert result.state.storage.consumed_ids == ()
    assert {x.stage for b in result.inventory.batches for x in b.routes} == {'EVENT'}


def test_service_finished_from_future_blocked_by_existing_quantum_contract():
    _, _, _, s = context(awaiting=(5,))
    with pytest.raises(ValueError, match='future'):
        replace(s.service, awaiting_confirmation=(ServiceFinishedV0(5, 999),))


def test_forged_confirmed_route_without_event_tombstone_rejected():
    _, _, _, s = context()
    forged = replace(s.service, confirmed=s.service.confirmed + (ServiceConfirmedV0(5, 3),))
    with pytest.raises(ValueError):
        replace(s, service=forged)


def test_event_capacity_invariant_is_checked_before_delivery():
    a, _, _, s = context(awaiting=(5, 6))
    capacity = next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    with pytest.raises(ValueError, match='capacity'):
        filled_static_event_slots(a, s, capacity+1)
