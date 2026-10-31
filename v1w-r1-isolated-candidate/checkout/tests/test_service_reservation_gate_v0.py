"""S3.7d/2: service-time reservation replay, real shared SPK fixtures."""
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_network.events_v0 import NetworkEventV0
from spk_simulator.routing_binding_v0 import bind_network_routes_v0
from spk_simulator.event_reservation_v0 import EventSlotUnavailableV0
import spk_simulator.service_reservation_gate_v0 as service_gate
from spk_simulator.service_reservation_gate_v0 import (
    ServiceReservationDeniedV0, ServiceReservationGateResultV0,
    gate_service_reservations_v0,
)
from tests.test_ownership_consistency_v0 import context, dynamic


def scenario(*, events=3, output=3, same_pe=False, boundary=0, initial=None):
    ctx = context(events=events, output=output, same_pe=same_pe, initial=initial)
    ctx, ingress = dynamic(ctx, boundary)
    network, observed, placement, architecture, plan, provenance, initial_events, requests, schedule = ctx
    binding = bind_network_routes_v0(
        network, observed, placement, plan, provenance, initial_events, architecture,
    )
    return architecture, binding, plan, requests, schedule, ingress


def run(args):
    return gate_service_reservations_v0(*args)


def usages(result):
    return {x.pe_id: x for x in result.peaks}


def test_real_network_fixture_success():
    result = run(scenario())
    assert isinstance(result, ServiceReservationGateResultV0)
    assert not result.final_ledger.reserved_routes
    assert not result.final_ledger.external_resident
    assert not result.final_storage.pending_output
    assert not result.final_storage.admitted_events


def test_complete_route_multiplicity():
    args = scenario()
    result = run(args)
    n = len(args[1].routes)
    assert n == 3
    assert len([t for t in result.transitions if t.operation == 'RESERVE']) == n
    assert len([t for t in result.transitions if t.operation == 'COMMIT']) == n
    assert len([t for t in result.transitions if t.operation == 'CONSUME_ROUTE']) == n
    assert len(result.final_storage.consumed_ids) == n


def test_external_occurrences_not_merged():
    args = scenario()
    result = run(args)
    arrived = [t.occurrence_id for t in result.transitions if t.operation == 'ARRIVE_EXTERNAL']
    consumed = [t.occurrence_id for t in result.transitions if t.operation == 'CONSUME_EXTERNAL']
    assert arrived == consumed == [0]
    assert result.final_ledger.external_consumed == (0,)


def test_every_reservation_precedes_commit():
    result = run(scenario())
    events = result.transitions
    for item in [t for t in events if t.operation == 'RESERVE']:
        assert any(t.operation == 'COMMIT' and t.occurrence_id == item.occurrence_id
                   and t.service_boundary > item.service_boundary for t in events)


def test_external_arrival_precedes_consumption():
    result = run(scenario())
    arrivals = {t.occurrence_id: t.service_boundary for t in result.transitions
                if t.operation == 'ARRIVE_EXTERNAL'}
    for consumed in (t for t in result.transitions if t.operation == 'CONSUME_EXTERNAL'):
        assert arrivals[consumed.occurrence_id] < consumed.service_boundary


def test_reservations_claim_finite_capacity():
    args = scenario()
    result = run(args)
    pe = {p.pe_id: p for p in args[0].pes}
    for usage in result.peaks:
        assert usage.peak_claimed <= pe[usage.pe_id].event_slots
        assert usage.peak_pending_output <= pe[usage.pe_id].output_slots
    assert usages(result)['PE1'].peak_reserved >= 1


def test_route_pending_retained_through_reservation():
    result = run(scenario())
    reserve = [t for t in result.transitions if t.operation == 'RESERVE']
    assert all(t.reserved_after > 0 for t in reserve)
    offers = {t.occurrence_id: t.service_boundary for t in result.transitions
              if t.operation == 'OFFER'}
    assert all(offers[t.occurrence_id] <= t.service_boundary for t in reserve)


def test_final_event_ownership_conserved():
    args = scenario()
    result = run(args)
    assert len(result.final_storage.consumed_ids) == len(args[1].routes)
    assert len(result.final_ledger.external_consumed) == len(args[5].arrivals)


def test_delayed_ingress_release_works():
    args = scenario(boundary=5)
    result = run(args)
    arrivals = [t for t in result.transitions if t.operation == 'ARRIVE_EXTERNAL']
    assert arrivals and all(t.service_boundary == 5 for t in arrivals)


def test_same_pe_routing_and_external_capacity():
    result = run(scenario(same_pe=True))
    assert usages(result)['PE0'].peak_claimed > 0
    assert usages(result)['PE1'].peak_claimed == 0


def test_empty_initial_events():
    result = run(scenario(initial=()))
    assert result.transitions == ()
    assert result.final_storage.consumed_ids == ()
    assert result.final_ledger.external_consumed == ()


def test_deterministic_replay():
    args = scenario()
    assert run(args) == run(args)


def test_input_is_immutable():
    args = scenario()
    before = repr(args)
    run(args)
    assert repr(args) == before


def test_output_is_immutable():
    result = run(scenario())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.transitions = ()


def test_requires_ingress():
    args = scenario()
    with pytest.raises(TypeError, match='ingress'):
        run(args[:-1] + (None,))


def test_reject_late_external_consumption():
    args = scenario()
    schedule = args[4]
    arrival = args[5].arrivals[0]
    consume_tick = next(c.completion_tick for c in schedule.completions
                        if c.request_id == arrival.consume_request_id)
    forged = replace(args[5], arrivals=(replace(arrival, arrival_boundary=consume_tick),))
    with pytest.raises(ValueError, match='arrival|release'):
        run(args[:-1] + (forged,))


def test_reject_unbound_external_consumer():
    args = scenario()
    bad = replace(args[5], arrivals=(replace(args[5].arrivals[0], consume_request_id=999),))
    with pytest.raises(ValueError, match='batch consume'):
        run(args[:-1] + (bad,))


def test_reject_duplicate_external_identity():
    args = scenario()
    entries = args[5].arrivals
    bad = replace(args[5], arrivals=(entries[0], entries[0]))
    with pytest.raises(ValueError, match='duplicate'):
        run(args[:-1] + (bad,))


def test_reject_corrupt_route_service_slice():
    args = scenario()
    schedule = args[4]
    bad = replace(schedule, slices=schedule.slices[:-1])
    with pytest.raises(ValueError, match='missing service slices'):
        run(args[:4] + (bad, args[5]))


def test_reject_wrong_epoch():
    args = scenario()
    with pytest.raises(ValueError, match='epoch'):
        run((args[0], replace(args[1], epoch_id='OTHER'), *args[2:]))


def test_reject_missing_external_arrival():
    args = scenario()
    bad = replace(args[5], arrivals=())
    with pytest.raises(ValueError, match='release|occurrence|identity'):
        run(args[:-1] + (bad,))


def test_service_time_not_event_time():
    args = scenario(boundary=5)
    original = tuple((r.occurrence.emission_event_time, r.occurrence.delivery_event_time)
                     for r in args[1].routes)
    result = run(args)
    assert tuple((r.occurrence.emission_event_time, r.occurrence.delivery_event_time)
                 for r in args[1].routes) == original
    assert result.transitions[0].service_boundary == 5


def test_route_capacity_denial_reported_with_exact_boundary(monkeypatch):
    args = scenario()
    route_id = args[1].routes[0].route_request_id
    start = min(s.service_tick for s in args[4].slices
                if s.request_id == route_id)
    original = service_gate.reserve_routed_event_slot_v0

    def denied(architecture, storage, binding, ledger, event_id):
        if event_id == route_id:
            raise EventSlotUnavailableV0('PE1', 3, 3)
        return original(architecture, storage, binding, ledger, event_id)

    monkeypatch.setattr(service_gate, 'reserve_routed_event_slot_v0', denied)
    with pytest.raises(ServiceReservationDeniedV0) as caught:
        run(args)
    err = caught.value
    assert (err.code, err.service_boundary, err.occurrence_id, err.pe_id) == (
        'ROUTE_RESERVATION_BLOCKED', start, route_id, 'PE1',
    )
    assert (err.claimed, err.capacity) == (3, 3)


def test_external_capacity_denial_is_not_backpressure(monkeypatch):
    args = scenario()

    def denied(*unused):
        raise EventSlotUnavailableV0('PE0', 3, 3)

    monkeypatch.setattr(service_gate, 'arrive_external_event_slot_v0', denied)
    with pytest.raises(ServiceReservationDeniedV0) as caught:
        run(args)
    assert caught.value.code == 'EXTERNAL_INGRESS_OVERFLOW'
    assert caught.value.service_boundary == 0
    assert caught.value.occurrence_id == 0
