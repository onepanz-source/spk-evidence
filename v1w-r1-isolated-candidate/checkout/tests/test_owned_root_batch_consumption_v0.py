"""SPK root-only closed finite-input service/physical EVENT consume integration."""
from dataclasses import FrozenInstanceError, replace
import pytest
from spk_simulator.owned_root_batch_consumption_v0 import (
    advance_owned_root_batch_consumption_v0 as tick,
)
from spk_simulator.owned_shared_event_cycle_v0 import (
    OwnedSharedEventCycleStateV0, SharedExternalIngressOverflowV0,
    owned_shared_event_usage_v0,
)
from spk_simulator.owned_sealed_root_batch_v0 import analyze_owned_sealed_root_batches_v0
from spk_simulator.owned_dynamic_route_transit_v0 import OwnedDynamicRouteTransitStateV0
from spk_simulator.owned_dynamic_route_service_cycle_v0 import OwnedDynamicRouteServiceCycleStateV0
from spk_simulator.owned_external_ingress_prefix_v0 import seal_finite_external_ingress_v0
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0, ServiceConfirmedV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from tests.test_owned_dynamic_service_registration_v0 import scenario


def seeded(*, start=4, arrivals=((4,3,0),), units=1, quantity=None,
           confirmed=(0,1)):
    arch, network, placement, image, prepared, registry = scenario()
    if quantity is None:
        quantity = len(arrivals)
    base = tuple(replace(r, service_units=units, quantity=quantity)
                 if r.request_id == 2 else r for r in registry.base_requests)
    registry = replace(registry, base_requests=base, staged_requests=base)
    service = ServiceQuantumStateV0(
        start, (), (), tuple(ServiceConfirmedV0(rid,1) for rid in confirmed)
    )
    transit = OwnedDynamicRouteTransitStateV0(
        registry, RoutedStorageStateV0(arch.profile_id,'E0'), service,
    )
    dynamic = OwnedDynamicRouteServiceCycleStateV0(transit)
    incoming = tuple(BoundExternalArrivalV0(
        i, event_time, 'C', channel, 'PE0', boundary, 2,
    ) for i,(boundary,event_time,channel) in enumerate(arrivals))
    latest = max((a.arrival_boundary for a in incoming),default=0)
    binding = ExternalIngressBindingV0(
        incoming, (BatchIngressReleaseV0(2,latest,tuple(range(len(incoming)))),)
    )
    seal = seal_finite_external_ingress_v0(arch, network, binding)
    return OwnedSharedEventCycleStateV0(dynamic, seal)


def pe(state,pe_id='PE0'):
    return next(x for x in owned_shared_event_usage_v0(state) if x.pe_id==pe_id)


def run2(s):
    a=tick(s)
    b=tick(a.state)
    return a,b


def test_single_input_first_boundary_is_service_only():
    s=seeded()
    a=tick(s)
    assert a.status=='SERVICE_PROGRESSED'
    assert a.admitted_external_input_indices==(0,)
    assert tuple(x.request_id for x in a.service_slices)==(2,)
    assert a.work_finished_consume_request_ids==(2,)
    assert not a.confirmed_consume_request_ids
    assert a.state.external_resident_input_indices==(0,)
    assert pe(a.state).external_resident==1


def test_single_input_second_boundary_consumes_atomically():
    a,b=run2(seeded())
    assert b.status=='CONSUMED'
    assert b.confirmed_consume_request_ids==(2,)
    assert b.newly_consumed_external_input_indices==(0,)
    assert b.state.external_resident_input_indices==()
    assert b.state.external_consumed_input_indices==(0,)
    assert pe(b.state).external_resident==0
    assert {x.request_id for x in b.state.dynamic.transit.service.confirmed} >= {0,1,2}
    assert a.state.external_consumed_input_indices==()


def test_no_early_consume_before_work_exhausted():
    s=seeded(units=4)
    a=tick(s)
    assert a.state.external_consumed_input_indices==()
    assert a.state.dynamic.transit.service.awaiting_confirmation==()
    assert a.status=='SERVICE_PROGRESSED'


def test_multiunit_service_requires_multiple_boundaries():
    s=seeded(units=4)
    slices=[]
    for _ in range(4):
        r=tick(s)
        slices.extend(r.service_slices)
        assert not r.confirmed_consume_request_ids
        s=r.state
        if r.work_finished_consume_request_ids:
            break
    assert sum(x.units for x in slices)==4
    b=tick(s)
    assert b.confirmed_consume_request_ids==(2,)


def test_multiple_external_instances_one_batch():
    s=seeded(arrivals=((4,3,0),(4,3,1)))
    a,b=run2(s)
    assert a.admitted_external_input_indices==(0,1)
    assert b.newly_consumed_external_input_indices==(0,1)
    assert b.state.external_consumed_input_indices==(0,1)


def test_same_channel_preserves_multiplicity():
    s=seeded(arrivals=((4,3,0),(4,3,0)))
    assert run2(s)[1].newly_consumed_external_input_indices==(0,1)


def test_later_arrival_blocks_early_service():
    s=seeded(arrivals=((4,3,0),(6,3,1)))
    first=tick(s)
    assert first.admitted_external_input_indices==(0,)
    assert first.service_slices==()
    second=tick(first.state)
    assert second.service_slices==()
    third=tick(second.state)
    assert third.admitted_external_input_indices==(1,)
    assert third.work_finished_consume_request_ids==(2,)
    fourth=tick(third.state)
    assert fourth.newly_consumed_external_input_indices==(0,1)


def test_mismatched_quantity_rejected_before_service():
    s=seeded(arrivals=((4,3,0),(4,3,1)), quantity=1)
    with pytest.raises(ValueError,match='identity mismatch'):
        tick(s)


def test_overflow_is_atomic():
    s=seeded(arrivals=tuple((4,3,i) for i in range(20)))
    with pytest.raises(SharedExternalIngressOverflowV0):
        tick(s)
    assert s.external_resident_input_indices==()


def test_duplicate_tombstone_rejected():
    b=run2(seeded())[1]
    with pytest.raises(ValueError,match='noncanonical'):
        replace(b.state, external_consumed_input_indices=(0,0))


def test_resident_and_consumed_overlap_rejected():
    b=run2(seeded())[1]
    with pytest.raises(ValueError,match='simultaneously'):
        replace(b.state,external_resident_input_indices=(0,))


def test_consumed_without_confirmed_service_rejected():
    a=tick(seeded())
    with pytest.raises(ValueError,match='confirmed batch'):
        replace(a.state, external_consumed_input_indices=(0,),
                external_resident_input_indices=())


def test_unknown_tombstone_rejected():
    b=run2(seeded())[1]
    with pytest.raises(ValueError,match='not in sealed'):
        replace(b.state,external_consumed_input_indices=(0,99))


def test_early_forged_consumption_rejected():
    s=seeded()
    with pytest.raises(ValueError,match='history'):
        replace(s,external_consumed_input_indices=(0,))


def test_preconfirmed_consume_without_physical_effect_rejected():
    s=seeded(confirmed=(0,1,2))
    with pytest.raises(ValueError,match='already confirmed'):
        tick(s)


def test_stale_root_is_not_reported_as_ready_after_consumption():
    b=run2(seeded())[1]
    candidate=analyze_owned_sealed_root_batches_v0(b.state).batches[0]
    assert candidate.status=='ROOT_INPUT_SET_CONSUMED'
    assert not candidate.sealed_input_set_complete


def test_next_step_refuses_unowned_state_commit():
    b=run2(seeded())[1]
    with pytest.raises(ValueError,match='unowned'):
        tick(b.state)


def test_pure_snapshot():
    s=seeded()
    before=s
    tick(s)
    assert s==before


def test_determinism():
    s=seeded()
    assert tick(s)==tick(s)


def test_route_fixture_with_incomplete_external_release_fails_closed():
    from tests.test_owned_shared_event_cycle_v0 import make
    _,s=make(arrivals=())
    with pytest.raises(ValueError,match='incomplete ingress release coverage'):
        tick(s)


def test_type_rejected():
    with pytest.raises(TypeError):
        tick(None)


def test_immutable_result():
    result=tick(seeded())
    with pytest.raises(FrozenInstanceError):
        result.status='BAD'


def test_output_event_time_distinct_from_service():
    a,b=run2(seeded())
    assert a.service_tick==4 and b.service_tick==5
    assert a.state.seal.binding.arrivals[0].event_time==3


def test_completing_service_does_not_consume_same_boundary():
    a=tick(seeded())
    assert a.work_finished_consume_request_ids==(2,)
    assert a.newly_consumed_external_input_indices==()


def test_immutable_external_seal():
    a,b=run2(seeded())
    assert a.state.seal is b.state.seal


def test_storage_preserved():
    s=seeded()
    b=run2(s)[1]
    assert b.state.dynamic.transit.storage==s.dynamic.transit.storage


def test_reservations_remain_intact():
    s=seeded()
    b=run2(s)[1]
    assert b.state.dynamic.reserved_route_request_ids==()


def test_root_batch_lifecycle_has_no_terminal_spike():
    b=run2(seeded())[1]
    assert b.state.dynamic.transit.storage.pending_output==()


def test_confirmed_at_boundary_after_finish():
    a,b=run2(seeded())
    work=a.state.dynamic.transit.service.awaiting_confirmation[0]
    receipt=next(x for x in b.state.dynamic.transit.service.confirmed if x.request_id==2)
    assert work.finish_boundary==5 and receipt.confirmation_boundary==5


def test_cannot_skip_due_event_with_later_service_tick():
    with pytest.raises(ValueError,match='history'):
        seeded(start=5,arrivals=((4,3,0),))


def test_external_consumption_updates_pe_budget():
    a,b=run2(seeded())
    assert pe(a.state).free+1==pe(b.state).free
