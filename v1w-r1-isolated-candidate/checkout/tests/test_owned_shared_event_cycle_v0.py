"""Mixed EVENT budget: external ingress and Core-generated routed spikes."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.owned_external_ingress_prefix_v0 import (
    seal_finite_external_ingress_v0,
)
from spk_simulator.owned_shared_event_cycle_v0 import (
    OwnedSharedEventCycleStateV0 as State,
    SharedExternalIngressOverflowV0 as Overflow,
    advance_owned_shared_event_cycle_v0 as tick,
    owned_shared_event_usage_v0 as usage,
)
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0
from tests.test_owned_dynamic_route_service_cycle_v0 import fresh


def make(*, arrivals=(), capacity=None, dynamic=None, resident=()):
    a, registry, routes, original = fresh()
    dyn = original if dynamic is None else dynamic
    if capacity is not None:
        assert capacity == next(p.event_slots for p in a.pes if p.pe_id == 'PE1')
    members = tuple(BoundExternalArrivalV0(
        i, event_time, node, channel, pe, boundary, 2,
    ) for i, (boundary, pe, node, event_time, channel) in enumerate(arrivals))
    batches = tuple(BatchIngressReleaseV0(2, b, (i,))
                    for i, (b, *_rest) in enumerate(arrivals))
    binding = ExternalIngressBindingV0(members, batches)
    seal = seal_finite_external_ingress_v0(
        a, registry.allocation_ledger.network, binding,
    )
    return a, State(dyn, seal, resident)


def an_input(tick_number=4, pe='PE1', node='B', event_time=8, channel=0):
    return tick_number, pe, node, event_time, channel


def run(state, number):
    steps = []
    for _ in range(number):
        outcome = tick(state)
        steps.append(outcome)
        state = outcome.state
    return steps


def pe(state, identifier='PE1'):
    return next(x for x in usage(state) if x.pe_id == identifier)


def test_empty_input_equivalent_route_ownership():
    _,s=make()
    r=tick(s)
    assert r.newly_reserved_route_request_ids == (5,6)
    assert r.admitted_external_input_indices == ()
    assert pe(r.state).routed_reserved == 2


def test_single_external_takes_shared_slot_first():
    _,s=make(arrivals=(an_input(),))
    r=tick(s)
    assert r.admitted_external_input_indices == (0,)
    assert r.newly_reserved_route_request_ids == (5,6)
    assert pe(r.state).claimed == 3
    assert pe(r.state).external_resident == 1
    assert pe(r.state).routed_reserved == 2


def test_two_external_inputs_leave_only_one_dynamic_route_claim():
    _,s=make(arrivals=(an_input(channel=0),an_input(channel=1)))
    r=tick(s)
    assert r.admitted_external_input_indices == (0,1)
    assert r.newly_reserved_route_request_ids == (5,)
    assert r.waiting_capacity_route_request_ids == (6,)
    assert pe(r.state).free == 0


def test_three_external_inputs_block_both_route_claims():
    _,s=make(arrivals=tuple(an_input(channel=i) for i in range(3)))
    r=tick(s)
    assert r.newly_reserved_route_request_ids == ()
    assert r.waiting_capacity_route_request_ids == (5,6)
    assert pe(r.state).external_resident == 3


def test_four_external_inputs_overflow_atomically():
    _,s=make(arrivals=tuple(an_input(channel=i) for i in range(4)))
    with pytest.raises(Overflow, match='EXTERNAL_INGRESS_OVERFLOW') as exc:
        tick(s)
    assert exc.value.input_index == 3
    assert exc.value.service_boundary == 4
    assert s.external_resident_input_indices == ()
    assert s.dynamic.reserved_route_request_ids == ()


def test_future_external_input_not_counted_early():
    _,s=make(arrivals=(an_input(tick_number=6),))
    r=tick(s)
    assert not r.admitted_external_input_indices
    assert r.newly_reserved_route_request_ids == (5,6)


def test_future_external_overflow_if_route_claims_persist():
    _,s=make(arrivals=(an_input(tick_number=5),an_input(tick_number=5)))
    first=tick(s)
    assert first.state.dynamic.reserved_route_request_ids == (5,6)
    with pytest.raises(Overflow):
        tick(first.state)
    assert first.state.external_resident_input_indices == ()


def test_routing_with_external_resident_can_finish():
    _,s=make(arrivals=(an_input(),))
    end=run(s,3)[-1]
    assert end.delivered_route_request_ids == (5,6)
    assert end.state.external_resident_input_indices == (0,)
    assert pe(end.state).routed_resident == 2
    assert pe(end.state).routed_reserved == 0
    assert pe(end.state).claimed == 3


def test_service_partial_retains_claim_and_external_slot():
    _,s=make(arrivals=(an_input(),))
    first,second=run(s,2)
    assert first.state.dynamic.reserved_route_request_ids == (5,6)
    assert second.state.dynamic.reserved_route_request_ids == (5,6)
    assert second.state.external_resident_input_indices == (0,)


def test_second_external_arrival_overflows_when_slot_reserved():
    _,s=make(arrivals=(an_input(),an_input(tick_number=5)))
    first=tick(s)
    with pytest.raises(Overflow) as exc:
        tick(first.state)
    assert exc.value.input_index == 1


def test_external_on_other_pe_does_not_block_routes():
    _,s=make(arrivals=(an_input(pe='PE0',node='C'),))
    r=tick(s)
    assert r.newly_reserved_route_request_ids == (5,6)
    assert pe(r.state,'PE0').external_resident == 1
    assert pe(r.state).external_resident == 0


def test_external_event_time_never_confused_with_service_time():
    _,s=make(arrivals=(an_input(event_time=99),))
    r=tick(s)
    assert r.service_tick == 4
    assert r.state.seal.binding.arrivals[0].event_time == 99


def test_same_logical_time_multiplicity_kept():
    _,s=make(arrivals=(an_input(event_time=7,channel=0),an_input(event_time=7,channel=0)))
    r=tick(s)
    assert r.state.external_resident_input_indices == (0,1)
    assert r.state.seal.binding.arrivals[0].event_time == r.state.seal.binding.arrivals[1].event_time


def test_no_external_consumption_is_fabricated():
    _,s=make(arrivals=(an_input(),))
    end=run(s,5)[-1]
    assert end.state.external_resident_input_indices == (0,)
    assert end.state.dynamic.transit.storage.consumed_ids == ()


def test_later_due_external_preserves_initial_count():
    _,s=make(arrivals=(an_input(),an_input(tick_number=6,pe='PE0',node='C')))
    r1,r2,r3=run(s,3)
    assert r1.state.external_resident_input_indices == (0,)
    assert r2.state.external_resident_input_indices == (0,)
    assert r3.state.external_resident_input_indices == (0,1)


def test_past_due_external_missing_rejected():
    with pytest.raises(ValueError, match='history'):
        make(arrivals=(an_input(tick_number=3),))


def test_past_due_external_accepted_when_resident():
    _,t=make(arrivals=(an_input(tick_number=3),), resident=(0,))
    assert pe(t).external_resident == 1


def test_future_external_fabrication_rejected():
    _,s=make(arrivals=(an_input(tick_number=10),))
    with pytest.raises(ValueError, match='history'):
        State(s.dynamic,s.seal,(0,))


def test_unknown_external_identity_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='not in sealed'):
        State(s.dynamic,s.seal,(12,))


def test_duplicate_external_indices_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.dynamic,s.seal,(0,0))


def test_noncanonical_external_indices_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.dynamic,s.seal,(1,0))


def test_invalid_external_indices_type_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.dynamic,s.seal,[0])


def test_negative_external_index_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='noncanonical'):
        State(s.dynamic,s.seal,(-1,))


def test_wrong_profile_seal_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='profile'):
        State(s.dynamic,replace(s.seal,profile_id='WRONG'))


def test_wrong_epoch_seal_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='epoch'):
        State(s.dynamic,replace(s.seal,epoch_id='WRONG'))


def test_seal_node_ids_tampering_rejected():
    _,s=make()
    with pytest.raises(ValueError, match='altered'):
        State(s.dynamic,replace(s.seal,node_ids=('WRONG',)))


def test_invalid_seal_type_rejected():
    _,s=make()
    with pytest.raises(TypeError, match='sealed external'):
        State(s.dynamic, None)


def test_invalid_dynamic_type_rejected():
    _,s=make()
    with pytest.raises(TypeError, match='dynamic route service'):
        State(None,s.seal)


def test_invalid_tick_input_type_rejected():
    with pytest.raises(TypeError, match='owned shared EVENT cycle'):
        tick(None)


def test_invalid_usage_input_type_rejected():
    with pytest.raises(TypeError, match='owned shared EVENT state'):
        usage(None)


def test_shared_capacity_overcommit_at_initialization_rejected():
    a,s=make(arrivals=(an_input(tick_number=3),an_input(tick_number=3)), resident=(0,1))
    from spk_simulator.owned_dynamic_route_service_cycle_v0 import OwnedDynamicRouteServiceCycleStateV0
    already=OwnedDynamicRouteServiceCycleStateV0(s.dynamic.transit,(5,6))
    with pytest.raises(ValueError, match='shared EVENT capacity exceeded'):
        State(already,s.seal,(0,1))


def test_repeated_tick_on_unchanged_snapshot_is_deterministic():
    _,s=make(arrivals=(an_input(),))
    assert tick(s) == tick(s)


def test_cycle_does_not_mutate_input():
    _,s=make(arrivals=(an_input(),))
    before=s
    tick(s)
    assert s==before


def test_state_dataclass_is_immutable():
    _,s=make()
    with pytest.raises((FrozenInstanceError,AttributeError)):
        s.dynamic=None


def test_event_capacity_usage_balances():
    _,s=make(arrivals=(an_input(),))
    r=tick(s)
    for row in r.pe_usage:
        assert row.claimed == row.external_resident + row.routed_resident + row.routed_reserved
        assert row.claimed + row.free == row.event_capacity


def test_late_extra_ingress_in_seal_fails_closed():
    _,s=make(arrivals=(an_input(),))
    first=tick(s)
    altered=replace(first.state.seal.binding,arrivals=())
    with pytest.raises(ValueError):
        State(first.state.dynamic,replace(first.state.seal,binding=altered), (0,))


def test_strict_next_tick_service_progress():
    _,s=make(arrivals=(an_input(),))
    seq=run(s,3)
    assert tuple(x.service_tick for x in seq)==(4,5,6)
    assert seq[-1].state.dynamic.transit.service.next_service_tick==7


def test_no_destination_batch_closure_authorized():
    _,s=make(arrivals=(an_input(),))
    result=run(s,3)[-1]
    assert not result.state.dynamic.transit.storage.consumed_ids
    assert not result.state.dynamic.transit.storage.pending_output
    assert result.state.dynamic.transit.storage.admitted_events


def test_external_event_on_source_pe_with_route_on_other_pe_is_valid():
    _,s=make(arrivals=tuple(an_input(pe='PE0',node='C',channel=i) for i in range(3)))
    r=tick(s)
    assert pe(r.state,'PE0').external_resident==3
    assert r.newly_reserved_route_request_ids==(5,6)


def test_external_not_admitted_twice_after_first_boundary():
    _,s=make(arrivals=(an_input(),))
    first,second=run(s,2)
    assert first.admitted_external_input_indices==(0,)
    assert second.admitted_external_input_indices==()


def test_external_capacity_failure_does_not_spend_service():
    _,s=make(arrivals=tuple(an_input(channel=i) for i in range(4)))
    original_service=s.dynamic.transit.service
    with pytest.raises(Overflow):
        tick(s)
    assert s.dynamic.transit.service==original_service


def test_prefix_includes_due_event_with_later_event_time():
    _,s=make(arrivals=(an_input(event_time=100),))
    r=tick(s)
    assert r.admitted_external_input_indices==(0,)
    assert r.state.seal.binding.arrivals[0].event_time==100


def test_requests_not_for_route_rejected_before_physical_effect():
    a,_,_,dyn=fresh(publication=False)
    service=dyn.transit.service
    service=replace(service,
                    confirmed=tuple(x for x in service.confirmed if x.request_id not in (0,4)),
                    awaiting_confirmation=())
    changed=replace(dyn,transit=replace(dyn.transit,service=service))
    _,s=make(dynamic=changed)
    with pytest.raises(ValueError):
        tick(s)
