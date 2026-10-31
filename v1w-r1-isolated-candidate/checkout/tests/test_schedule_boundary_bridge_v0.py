"""S3.7d/3b2a: boundary bridge behavior, with validated upstream replays stubbed.

The upstream services have independent tests; these cases exercise the bridge
without requiring Network/Compiler internals in this isolated fixture.
"""
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

import spk_simulator.schedule_boundary_bridge_v0 as bridge
from spk_simulator.backpressure_arbiter_v0 import BackpressureArbiterStateV0
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryActionsV0, BackpressureBoundaryStateV0,
    advance_backpressure_boundary_v0,
)
from spk_simulator.causal_scheduler_v0 import CausalScheduleResultV0
from spk_simulator.event_reservation_v0 import EventReservationStateV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from tests.test_backpressure_arbiter_v0 import setup


def make(monkeypatch, *, routes=1, capacity=2, ext_boundary=None, external_consume=4):
    architecture, full_manifest, _, old_ledger, _ = setup(capacity=capacity, count=0)
    manifest = replace(full_manifest, routes=full_manifest.routes[:routes])
    ingress = ExternalIngressBindingV0((), ())
    if ext_boundary is not None:
        arrival = replace(old_ledger.ingress.arrivals[0], arrival_boundary=ext_boundary)
        ingress = ExternalIngressBindingV0((arrival,), ())
    ledger = EventReservationStateV0(manifest.profile_id, manifest.epoch_id, ingress)
    storage = RoutedStorageStateV0(manifest.profile_id, manifest.epoch_id)
    arbiter = BackpressureArbiterStateV0(manifest.profile_id, manifest.epoch_id)
    state = BackpressureBoundaryStateV0(storage, ledger, arbiter)

    routeids = tuple(r.route_request_id for r in manifest.routes)
    # Offer/reserve at 0, commit at 1, consume at 2; one event per bound route.
    transitions = tuple(SimpleNamespace(
        service_boundary=boundary, operation=operation, route_request_id=rid)
        for boundary, operation in ((0, 'OFFER'), (1, 'ADMIT'), (2, 'CONSUME'))
        for rid in routeids
    )
    done = () if ext_boundary is None else (
        SimpleNamespace(request_id=500, completion_tick=external_consume),
    )
    slices = tuple(SimpleNamespace(service_tick=0, request_id=rid) for rid in routeids)
    schedule = CausalScheduleResultV0('p', slices, done, (), 0, 10)

    # Build an *independent* reference state, not by invoking the bridge.
    current = state
    last = max(2 if routes else 0, external_consume if ext_boundary is not None else 0)
    for boundary in range(last+1):
        result = advance_backpressure_boundary_v0(
            architecture, manifest, current, service_boundary=boundary,
            actions=BackpressureBoundaryActionsV0(
                routed_offers=routeids if boundary == 0 else (),
                newly_ready_routes=routeids if boundary == 0 else (),
                route_commits=routeids if boundary == 1 else (),
                route_consumptions=routeids if boundary == 2 else (),
                external_arrivals=(0,) if ext_boundary == boundary else (),
                external_consumptions=(0,) if ext_boundary is not None and
                                     external_consume == boundary else (),
            ),
        )
        current = result.state

    monkeypatch.setattr(bridge, 'gate_service_reservations_v0', lambda *args: SimpleNamespace(
        final_storage=current.storage, final_ledger=current.ledger,
    ))
    monkeypatch.setattr(bridge, 'replay_routed_service_ownership_v0', lambda *args: SimpleNamespace(
        transitions=transitions,
    ))
    return (architecture, manifest, LogicalAccessPlanV0(manifest.epoch_id, None, ()), (), schedule, ingress), current


def test_single_route_timeline(monkeypatch):
    args, end = make(monkeypatch)
    output = bridge.verify_schedule_boundaries_v0(*args)
    assert output.checked_route_count == 1
    assert output.checked_external_count == 0
    assert output.final_state == end
    assert tuple(x.service_boundary for x in output.frames) == (0, 1, 2)


def test_offer_and_reserve_in_same_boundary(monkeypatch):
    args, _ = make(monkeypatch)
    output = bridge.verify_schedule_boundaries_v0(*args)
    assert [x.operation for x in output.frames[0].result.operations] == ['OFFER', 'RESERVE']


def test_route_commit_and_consume_follow(monkeypatch):
    args, _ = make(monkeypatch)
    output = bridge.verify_schedule_boundaries_v0(*args)
    assert [x.operation for x in output.frames[1].result.operations] == ['COMMIT']
    assert [x.operation for x in output.frames[2].result.operations] == ['CONSUME_ROUTE']


def test_distinct_parallel_routes(monkeypatch):
    args, end = make(monkeypatch, routes=3, capacity=3)
    result = bridge.verify_schedule_boundaries_v0(*args)
    assert result.checked_route_count == 3
    assert result.final_state.storage.consumed_ids == (10, 11, 12)
    assert result.final_state == end


def test_no_phantom_capacity_accepted(monkeypatch):
    args, _ = make(monkeypatch, routes=2, capacity=2)
    result = bridge.verify_schedule_boundaries_v0(*args)
    assert result.frames[0].result.pe_usage[1].claimed_events == 2


def test_missing_route_reservation_rejected(monkeypatch):
    args, _ = make(monkeypatch)
    schedule = replace(args[4], slices=())
    with pytest.raises(ValueError, match='missing route'):
        bridge.verify_schedule_boundaries_v0(*args[:4], schedule, args[5])


def test_no_spikes(monkeypatch):
    args, _ = make(monkeypatch, routes=0)
    result = bridge.verify_schedule_boundaries_v0(*args)
    assert result.checked_route_count == 0
    assert result.final_state.storage.consumed_ids == ()


def test_external_delayed(monkeypatch):
    args, end = make(monkeypatch, routes=0, ext_boundary=3, external_consume=4)
    result = bridge.verify_schedule_boundaries_v0(*args)
    assert result.checked_external_count == 1
    assert result.frames[3].result.operations[0].operation == 'ARRIVE_EXTERNAL'
    assert result.frames[4].result.operations[0].operation == 'CONSUME_EXTERNAL'
    assert result.final_state == end


def test_external_arrives_at_zero(monkeypatch):
    args, _ = make(monkeypatch, routes=0, ext_boundary=0, external_consume=4)
    result = bridge.verify_schedule_boundaries_v0(*args)
    assert result.frames[0].actions.external_arrivals == (0,)


def test_replay_limit_is_finite(monkeypatch):
    args, _ = make(monkeypatch, routes=0, ext_boundary=3, external_consume=4)
    with pytest.raises(ValueError, match='limit'):
        bridge.verify_schedule_boundaries_v0(*args, max_boundaries=4)


def test_invalid_limit(monkeypatch):
    args, _ = make(monkeypatch)
    for bad in (0, -1, True, '10'):
        with pytest.raises(ValueError, match='max_boundaries'):
            bridge.verify_schedule_boundaries_v0(*args, max_boundaries=bad)


def test_inputs_unchanged(monkeypatch):
    args, _ = make(monkeypatch)
    before = repr(args)
    bridge.verify_schedule_boundaries_v0(*args)
    assert repr(args) == before


def test_result_frozen(monkeypatch):
    args, _ = make(monkeypatch)
    result = bridge.verify_schedule_boundaries_v0(*args)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.frames = ()


def test_repeat_deterministic(monkeypatch):
    args, _ = make(monkeypatch)
    assert bridge.verify_schedule_boundaries_v0(*args) == bridge.verify_schedule_boundaries_v0(*args)


def test_mismatch_final_state_is_rejected(monkeypatch):
    args, end = make(monkeypatch)
    monkeypatch.setattr(bridge, 'gate_service_reservations_v0', lambda *unused: SimpleNamespace(
        final_storage=RoutedStorageStateV0(end.storage.profile_id, end.storage.epoch_id),
        final_ledger=end.ledger,
    ))
    with pytest.raises(ValueError, match='disagree'):
        bridge.verify_schedule_boundaries_v0(*args)


def test_wrong_input_types(monkeypatch):
    args, _ = make(monkeypatch)
    for idx in (0, 1, 2, 4, 5):
        corrupted = list(args)
        corrupted[idx] = None
        with pytest.raises(TypeError):
            bridge.verify_schedule_boundaries_v0(*corrupted)


def test_denied_route_cannot_start_service(monkeypatch):
    args, _ = make(monkeypatch, routes=2, capacity=2)
    architecture = replace(args[0], pes=tuple(
        replace(pe, event_slots=1) for pe in args[0].pes
    ))
    with pytest.raises(bridge.ScheduledRouteWithoutReservationV0) as caught:
        bridge.verify_schedule_boundaries_v0(architecture, *args[1:])
    assert caught.value.code == 'SCHEDULED_ROUTE_WITHOUT_RESERVATION'
    assert caught.value.service_boundary == 0
    assert caught.value.route_ids == (11,)


def test_external_priority_denies_routing_service(monkeypatch):
    args, _ = make(monkeypatch, routes=1, capacity=2,
                   ext_boundary=0, external_consume=4)
    architecture = replace(args[0], pes=tuple(
        replace(pe, event_slots=1) for pe in args[0].pes
    ))
    # External arrival is at PE1; the route also needs PE1.
    with pytest.raises(bridge.ScheduledRouteWithoutReservationV0):
        bridge.verify_schedule_boundaries_v0(architecture, *args[1:])


def test_output_capacity_is_finite(monkeypatch):
    from spk_simulator.backpressure_boundary_v0 import BoundaryCapacityDeniedV0
    args, _ = make(monkeypatch, routes=2, capacity=2)
    architecture = replace(args[0], pes=tuple(
        replace(pe, output_slots=1) for pe in args[0].pes
    ))
    with pytest.raises(BoundaryCapacityDeniedV0) as caught:
        bridge.verify_schedule_boundaries_v0(architecture, *args[1:])
    assert caught.value.code == 'OUTPUT_STORAGE_BLOCKED'


def test_peripheral_event_time_preserved(monkeypatch):
    args, _ = make(monkeypatch)
    original = args[1].routes[0].occurrence
    bridge.verify_schedule_boundaries_v0(*args)
    assert args[1].routes[0].occurrence == original
