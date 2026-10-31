"""S3.7d/3a: bounded single-owner route-claim arbitration and retry."""
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_simulator.backpressure_arbiter_v0 import (
    BackpressureArbiterStateV0, BackpressureArbitrationResultV0,
    arbitrate_routed_reservations_v0,
)
from spk_simulator.event_reservation_v0 import (
    arrive_external_event_slot_v0, consume_external_event_slot_v0,
    commit_routed_event_slot_v0, consume_reserved_routed_event_v0,
    event_reservation_usage_v0,
)
from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_simulator.event_storage_v0 import RoutedOccurrenceV0, RoutedStorageStateV0
from spk_simulator.routing_binding_v0 import (
    BoundRouteV0, RoutedBindingManifestV0, offer_bound_routed_event_v0,
)
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.event_reservation_v0 import EventReservationStateV0


def setup(*, capacity=1, count=2, same_pe=False):
    pe = ProcessingElementV0(
        pe_id='PE0', program_slots=8, state_slots=4,
        event_slots=capacity, output_slots=8, observation_slots=4,
        accesses_per_service_tick=2,
    )
    architecture = ArchitectureProfileV0(
        'arbiter-lab', (pe, replace(pe, pe_id='PE1')),
    )
    destination = 'PE0' if same_pe else 'PE1'
    routes = tuple(BoundRouteV0(
        route_request_id=10+i, consume_request_id=50+i,
        target_batch_index=i,
        occurrence=RoutedOccurrenceV0(
            event_id=10+i, epoch_id='E0', source_node_id='A',
            source_pe_id='PE0', source_channel=7,
            target_node_id='B', target_pe_id=destination,
            target_channel=0, emission_event_time=2,
            delivery_event_time=4+i,
        ),
    ) for i in range(3))
    manifest = RoutedBindingManifestV0('arbiter-lab', 'E0', routes)
    ingress = ExternalIngressBindingV0(
        arrivals=(BoundExternalArrivalV0(
            input_index=0, event_time=2, node_id='A', channel=0,
            target_pe_id=destination, arrival_boundary=0,
            consume_request_id=500,
        ),),
        batch_releases=(BatchIngressReleaseV0(
            consume_request_id=500, ready_boundary=0, input_indices=(0,),
        ),),
    )
    storage = RoutedStorageStateV0('arbiter-lab', 'E0')
    for item in routes[:count]:
        storage = offer_bound_routed_event_v0(
            architecture, storage, manifest, item.route_request_id,
        )
    ledger = EventReservationStateV0('arbiter-lab', 'E0', ingress)
    state = BackpressureArbiterStateV0('arbiter-lab', 'E0')
    return architecture, manifest, storage, ledger, state


def route(ctx, i=0):
    return ctx[1].routes[i].route_request_id


def run(ctx, *, boundary=0, ready=()):
    a, m, s, ledger, state = ctx
    return arbitrate_routed_reservations_v0(
        a, m, s, ledger, state,
        service_boundary=boundary, newly_ready_route_ids=ready,
    )


def ret(ctx, result):
    return ctx[:3] + (result.ledger, result.state)


def test_empty_boundary_is_valid():
    ctx = setup(count=0)
    out = run(ctx)
    assert out.granted_route_ids == () and out.denied == ()
    assert out.ledger is ctx[3]
    assert out.state.last_service_boundary == 0


def test_two_same_pe_routes_single_slot():
    ctx = setup()
    r0, r1 = route(ctx, 0), route(ctx, 1)
    out = run(ctx, ready=(r1, r0))
    assert out.granted_route_ids == (min(r0, r1),)
    assert tuple(d.route_request_id for d in out.denied) == (max(r0, r1),)
    assert out.state.waiting_route_ids == (max(r0, r1),)
    assert len(ctx[2].pending_output) == 2


def test_identity_not_deduplicated():
    ctx = setup(capacity=3, count=3)
    ids = tuple(route(ctx, i) for i in range(3))
    result = run(ctx, ready=ids[::-1])
    assert result.granted_route_ids == tuple(sorted(ids))
    assert len(result.ledger.reserved_routes) == 3
    assert result.state.waiting_route_ids == ()


def test_denial_contains_capacity_and_service_boundary():
    ctx = setup()
    out = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    denial, = out.denied
    assert (denial.target_pe_id, denial.claimed, denial.capacity, denial.service_boundary) == ('PE1', 1, 1, 0)


def test_denied_event_stays_source_owned():
    ctx = setup()
    out = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    denied_id = out.denied[0].route_request_id
    assert denied_id not in out.ledger.reserved_routes
    assert denied_id in {ev.event_id for ev in ctx[2].pending_output}
    assert ctx[2].admitted_events == ()


def test_retry_without_release_stays_blocked():
    ctx = setup()
    first = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    second = run(ret(ctx, first), boundary=1)
    assert len(second.denied) == 1
    assert second.granted_route_ids == ()
    assert second.state.waiting_route_ids == first.state.waiting_route_ids


def test_release_then_retry_succeeds():
    ctx = setup()
    first = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    a, m, s = ctx[:3]
    accepted = first.granted_route_ids[0]
    s, ledger = commit_routed_event_slot_v0(a, s, m, first.ledger, accepted)
    s = consume_reserved_routed_event_v0(
        a, s, m, ledger, accepted,
        consume_request_id=m.get(accepted).consume_request_id,
    )
    next_ctx = a, m, s, ledger, first.state
    again = run(next_ctx, boundary=1)
    assert again.granted_route_ids == first.state.waiting_route_ids
    assert not again.denied and not again.state.waiting_route_ids
    assert len(s.pending_output) == 1


def test_retry_cannot_start_same_boundary():
    ctx = setup()
    result = run(ctx)
    with pytest.raises(ValueError, match='strictly increasing'):
        run(ret(ctx, result), boundary=0)


def test_reverse_service_time_rejected():
    ctx = setup()
    result = run(ctx, boundary=9)
    with pytest.raises(ValueError, match='strictly increasing'):
        run(ret(ctx, result), boundary=8)


def test_waiters_first_without_starvation_from_new_work():
    ctx = setup(capacity=1, count=3)
    r0, r1, r2 = (route(ctx, i) for i in range(3))
    first = run(ctx, ready=(r0, r1))
    a, m, s = ctx[:3]
    s, ledger = commit_routed_event_slot_v0(a, s, m, first.ledger, r0)
    s = consume_reserved_routed_event_v0(
        a, s, m, ledger, r0, consume_request_id=m.get(r0).consume_request_id,
    )
    again = run((a, m, s, ledger, first.state), boundary=1, ready=(r2,))
    assert again.granted_route_ids == (r1,)
    assert again.state.waiting_route_ids == (r2,)


def test_no_phantom_capacity_on_failed_reservation():
    ctx = setup()
    out = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    usage = next(u for u in event_reservation_usage_v0(ctx[0], ctx[2], ctx[1], out.ledger) if u.pe_id == 'PE1')
    assert usage.claimed == 1 and usage.reserved == 1
    assert len(out.denied) == 1


def test_no_implicit_external_storage():
    ctx = setup(capacity=1, count=1, same_pe=True)
    a, m, s, ledger, state = ctx
    ledger = arrive_external_event_slot_v0(a, s, m, ledger, 0)
    out = run((a, m, s, ledger, state), ready=(route(ctx, 0),))
    assert not out.granted_route_ids and out.denied
    assert out.ledger.external_resident == (0,)


def test_external_consume_makes_retry_possible():
    ctx = setup(capacity=1, count=1, same_pe=True)
    a, m, s, ledger, state = ctx
    ledger = arrive_external_event_slot_v0(a, s, m, ledger, 0)
    first = run((a, m, s, ledger, state), ready=(route(ctx, 0),))
    consume_id = ledger.ingress.arrivals[0].consume_request_id
    ledger = consume_external_event_slot_v0(a, s, m, first.ledger, 0, consume_request_id=consume_id)
    second = run((a, m, s, ledger, first.state), boundary=1)
    assert second.granted_route_ids == (route(ctx, 0),)
    assert not second.denied


def test_incomplete_offer_rejected():
    a, m, s, ledger, state = setup(count=0)
    with pytest.raises(ValueError, match='retained source'):
        run((a, m, s, ledger, state), ready=(m.routes[0].route_request_id,))


def test_unknown_route_rejected():
    ctx = setup()
    with pytest.raises(ValueError, match='unknown route'):
        run(ctx, ready=(999999,))


def test_duplicate_new_routes_rejected():
    ctx = setup()
    with pytest.raises(ValueError, match='invalid newly'):
        run(ctx, ready=(route(ctx, 0), route(ctx, 0)))


def test_boolean_request_id_rejected():
    with pytest.raises(ValueError, match='invalid newly'):
        run(setup(), ready=(True,))


def test_wrong_ready_container_rejected():
    with pytest.raises(ValueError, match='invalid newly'):
        run(setup(), ready=[1])


def test_duplicate_waiter_resubmission_rejected():
    ctx = setup()
    out = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    with pytest.raises(ValueError, match='previous waiter'):
        run(ret(ctx, out), boundary=1, ready=out.state.waiting_route_ids)


def test_preexisting_reserved_rejected():
    ctx = setup()
    out = run(ctx, ready=(route(ctx, 0),))
    with pytest.raises(ValueError, match='already reserved'):
        run(ret(ctx, out), boundary=1, ready=(route(ctx, 0),))


def test_profile_mismatch_rejected():
    ctx = setup()
    with pytest.raises(ValueError, match='profile or epoch'):
        run(ctx[:4] + (replace(ctx[4], profile_id='wrong'),))


def test_epoch_mismatch_rejected():
    ctx = setup()
    with pytest.raises(ValueError, match='profile or epoch'):
        run(ctx[:4] + (replace(ctx[4], epoch_id='wrong'),))


def test_strict_boundary_type():
    with pytest.raises(ValueError, match='SERVICE_TIME'):
        run(setup(), boundary=True)
    with pytest.raises(ValueError, match='SERVICE_TIME'):
        run(setup(), boundary=-1)


def test_immutable_result():
    out = run(setup())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.granted_route_ids = (123,)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.state.last_service_boundary = 999


def test_deterministic_replay_and_input_order():
    ctx = setup(capacity=2, count=3)
    ids = tuple(route(ctx, i) for i in range(3))
    a = run(ctx, ready=ids)
    b = run(ctx, ready=ids[::-1])
    assert a == b


def test_invalid_snapshot_no_partial_state_mutation():
    ctx = setup()
    before = repr(ctx)
    with pytest.raises(ValueError, match='unknown route'):
        run(ctx, ready=(route(ctx, 0), 9876543))
    assert repr(ctx) == before


def test_source_output_capacity_is_respected():
    ctx = setup(capacity=3, count=3)
    r = run(ctx, ready=tuple(route(ctx, i) for i in range(3)))
    assert len(r.granted_route_ids) == 3
    assert ctx[2].pending_output == tuple(x.occurrence for x in ctx[1].routes)


def test_state_rejects_orphan_waiter():
    with pytest.raises(ValueError, match='initial state'):
        BackpressureArbiterStateV0('p', 'E0', waiting_route_ids=(1,))


def test_independent_destination_pe_can_progress():
    a, manifest, storage, ledger, state = setup(capacity=1, count=0)
    changed = replace(
        manifest.routes[2],
        occurrence=replace(manifest.routes[2].occurrence, target_pe_id='PE0'),
    )
    manifest = replace(manifest, routes=manifest.routes[:2] + (changed,))
    for item in manifest.routes:
        storage = offer_bound_routed_event_v0(a, storage, manifest, item.route_request_id)
    result = run((a, manifest, storage, ledger, state), ready=(10, 11, 12))
    assert result.granted_route_ids == (10, 12)
    assert tuple(item.route_request_id for item in result.denied) == (11,)
    assert {item.event_id for item in storage.pending_output} == {10, 11, 12}


def test_existing_resident_routed_event_blocks_reservation():
    ctx = setup()
    first = run(ctx, ready=(route(ctx, 0),))
    a, manifest, storage = ctx[:3]
    storage, ledger = commit_routed_event_slot_v0(
        a, storage, manifest, first.ledger, route(ctx, 0),
    )
    result = run((a, manifest, storage, ledger, first.state), boundary=1,
                 ready=(route(ctx, 1),))
    assert not result.granted_route_ids
    assert result.state.waiting_route_ids == (route(ctx, 1),)


def test_wrong_input_state_type_rejected():
    ctx = setup()
    with pytest.raises(TypeError, match='invalid arbiter state'):
        run(ctx[:4] + (None,))


def test_canonical_waiting_arbiter_state_reproducible():
    ctx = setup()
    original = run(ctx, ready=(route(ctx, 1), route(ctx, 0)))
    again = run(ctx, ready=(route(ctx, 0), route(ctx, 1)))
    assert original.state == again.state
    assert original.ledger == again.ledger
