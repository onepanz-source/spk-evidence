"""Dynamic destination inventory never confuses residency with batch closure."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.event_storage_v0 import (
    RoutedOccurrenceV0, RoutedStorageStateV0,
    offer_routed_output_v0, admit_routed_event_v0, consume_routed_event_v0,
)
from spk_simulator.dynamic_destination_inventory_v0 import (
    derive_dynamic_destination_inventory_v0 as derive,
)
from tests.test_owned_dynamic_service_registration_v0 import scenario, do


def context():
    c = scenario()
    registered = do(c).state
    storage = RoutedStorageStateV0(c[0].profile_id, 'E0')
    return c[0], registered, storage


def occurrences(registry):
    return tuple(route.occurrence for record in registry.registrations
                 for route in record.allocation.topology.routes)


def inv(arch, registry, storage):
    return derive(arch, registry, storage)


def batch(result, time):
    return next(x for x in result.batches if x.event_time == time)


def physical(arch, storage, route, stage):
    if stage == 'STAGED':
        return storage
    offered = offer_routed_output_v0(arch, storage, route)
    if stage == 'OUTPUT':
        return offered
    admitted = admit_routed_event_v0(arch, offered, route.event_id)
    if stage == 'EVENT':
        return admitted
    if stage == 'CONSUMED':
        return consume_routed_event_v0(
            arch, admitted, route.event_id, target_pe_id=route.target_pe_id,
        )
    raise AssertionError(stage)


def test_new_routes_are_staged_not_resident():
    a,r,s=context()
    result=inv(a,r,s)
    assert len(result.batches)==2
    assert tuple(x.event_time for x in result.batches)==(5,6)
    assert all(x.routes[0].stage=='STAGED' for x in result.batches)
    assert all(x.resident_channels==() for x in result.batches)
    assert result.supports_consume_admission is False


@pytest.mark.parametrize('stage', ('STAGED','OUTPUT','EVENT','CONSUMED'))
def test_individual_route_follows_physical_stage(stage):
    a,r,s=context()
    first=occurrences(r)[0]
    storage=physical(a,s,first,stage)
    result=inv(a,r,storage)
    assert batch(result,5).routes[0].stage==stage
    assert batch(result,6).routes[0].stage=='STAGED'
    assert batch(result,5).resident_channels==(first.target_channel,) if stage=='EVENT' else batch(result,5).resident_channels==()


def test_delivery_time_not_source_event_time():
    a,r,s=context()
    o=occurrences(r)[0]
    assert o.emission_event_time==3 and o.delivery_event_time==5
    assert batch(inv(a,r,s),5).event_time==5


def test_no_auto_close_when_every_known_route_arrived():
    a,r,s=context()
    for o in occurrences(r):
        s=physical(a,s,o,'EVENT')
    result=inv(a,r,s)
    assert all(x.closure_status=='OPEN_UNPROVEN' for x in result.batches)
    assert all(x.resident_route_request_ids for x in result.batches)
    assert not result.supports_consume_admission


def test_no_auto_close_when_all_known_routes_consumed():
    a,r,s=context()
    for o in occurrences(r):
        s=physical(a,s,o,'CONSUMED')
    result=inv(a,r,s)
    assert all(x.closure_status=='OPEN_UNPROVEN' for x in result.batches)
    assert all(not x.resident_route_request_ids for x in result.batches)


def test_partial_arrival_not_prematurely_processed():
    a,r,s=context()
    s=physical(a,s,occurrences(r)[0],'EVENT')
    x=inv(a,r,s)
    assert batch(x,5).resident_route_request_ids==(5,)
    assert batch(x,6).resident_route_request_ids==()


def test_pending_output_not_counted_as_destination_resident():
    a,r,s=context()
    s=physical(a,s,occurrences(r)[0],'OUTPUT')
    assert batch(inv(a,r,s),5).resident_channels==()


def test_consumed_route_is_not_counted_as_resident():
    a,r,s=context()
    s=physical(a,s,occurrences(r)[0],'CONSUMED')
    assert batch(inv(a,r,s),5).resident_channels==()


def test_route_identity_is_service_request_identity():
    a,r,s=context()
    expected={x.request_id for x in r.staged_requests if x.kind.value=='ROUTE_ENQUEUE'}
    found={y.route_request_id for x in inv(a,r,s).batches for y in x.routes}
    assert expected==found


def test_second_registration_keeps_both_sources():
    c=scenario(nodes=('A','B','C'))
    from spk_simulator.versioned_core_transition_v0 import prepare_core_transition_v0
    first=do(c).state
    prep=prepare_core_transition_v0(c[1],c[3],node_id='A',timestamp=2,channels=(0,))
    second=__import__('spk_simulator.owned_dynamic_service_registration_v0',fromlist=['register_owned_computed_emission_services_v0']).register_owned_computed_emission_services_v0(first,c[3],prep).state
    x=inv(c[0],second,RoutedStorageStateV0(c[0].profile_id,'E0'))
    assert tuple(y.event_time for y in x.batches)==(4,5,6)


def test_terminal_only_outputs_do_not_create_false_batch():
    c=scenario(nodes=('B',))
    registered=do(c,node='B').state
    result=inv(c[0],registered,RoutedStorageStateV0(c[0].profile_id,'E0'))
    assert result.batches==()
    assert result.terminal_candidate_count==1
    assert not result.supports_consume_admission


def test_storage_does_not_modify_owner_or_storage():
    a,r,s=context()
    before=(r,s)
    inv(a,r,s)
    assert (r,s)==before


def test_deterministic_repeat():
    a,r,s=context()
    assert inv(a,r,s)==inv(a,r,s)


def test_immutable_inventory():
    a,r,s=context()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        inv(a,r,s).batches=()


def test_mismatched_profile_rejected():
    a,r,s=context()
    with pytest.raises(ValueError,match='profile'):
        inv(a,r,replace(s,profile_id='OTHER'))


def test_mismatched_epoch_rejected():
    a,r,s=context()
    with pytest.raises(ValueError,match='epoch'):
        inv(a,r,replace(s,epoch_id='OTHER'))


def test_altered_route_channel_rejected():
    a,r,s=context()
    o=occurrences(r)[0]
    with pytest.raises(ValueError,match='provenance'):
        inv(a,r,replace(s,admitted_events=(replace(o,target_channel=999),)))


def test_altered_source_rejected():
    a,r,s=context()
    o=occurrences(r)[0]
    with pytest.raises(ValueError,match='provenance'):
        inv(a,r,replace(s,pending_output=(replace(o,source_channel=999),)))


def test_altered_delivery_time_rejected():
    a,r,s=context()
    o=occurrences(r)[0]
    with pytest.raises(ValueError,match='provenance'):
        inv(a,r,replace(s,admitted_events=(replace(o,delivery_event_time=7),)))


def test_unregistered_dynamic_identity_rejected():
    a,r,s=context()
    o=replace(occurrences(r)[0],event_id=r.allocation_ledger.next_request_id)
    with pytest.raises(ValueError,match='unknown dynamic'):
        inv(a,r,replace(s,admitted_events=(o,)))


def test_emission_request_id_cannot_be_used_as_route_id():
    a,r,s=context()
    o=replace(occurrences(r)[0],event_id=r.registrations[0].allocation.emission_request_id)
    with pytest.raises(ValueError,match='unknown dynamic'):
        inv(a,r,replace(s,admitted_events=(o,)))


def test_unregistered_dynamic_consumption_rejected():
    a,r,s=context()
    with pytest.raises(ValueError,match='unknown dynamic'):
        inv(a,r,replace(s,consumed_ids=(r.allocation_ledger.next_request_id,)))


def test_static_event_identity_is_kept_separate():
    a,r,s=context()
    o=replace(occurrences(r)[0],event_id=0)
    x=inv(a,r,replace(s,admitted_events=(o,)))
    assert x.untracked_static_storage_ids==(0,)
    assert all(y.routes[0].stage=='STAGED' for y in x.batches)


def test_static_consumption_tombstone_reported_separately():
    a,r,s=context()
    x=inv(a,r,replace(s,consumed_ids=(0,2)))
    assert x.untracked_static_storage_ids==(0,2)


def test_dynamic_consumption_tombstone_matches_owned_id():
    a,r,s=context()
    rid=occurrences(r)[0].event_id
    x=inv(a,r,replace(s,consumed_ids=(rid,)))
    assert batch(x,5).routes[0].stage=='CONSUMED'


def test_invalid_architecture_type_rejected():
    _,r,s=context()
    with pytest.raises(TypeError,match='architecture'):
        inv(None,r,s)


def test_invalid_registry_type_rejected():
    a,_,s=context()
    with pytest.raises(TypeError,match='registration'):
        inv(a,None,s)


def test_invalid_storage_type_rejected():
    a,r,_=context()
    with pytest.raises(TypeError,match='storage'):
        inv(a,r,None)


def test_snapshot_storage_capacity_must_be_valid():
    a,r,s=context()
    o=occurrences(r)[0]
    # create more physical identities than output slots, all in the static namespace
    over=tuple(replace(o,event_id=n) for n in range(a.pes[0].output_slots+1))
    with pytest.raises(ValueError,match='capacity'):
        inv(a,r,replace(s,pending_output=over))


def test_staged_and_resident_are_not_equivalent():
    a,r,s=context()
    a1=inv(a,r,s)
    a2=inv(a,r,physical(a,s,occurrences(r)[0],'EVENT'))
    assert a1!=a2


def test_event_time_is_preserved_even_if_storage_order_is_reversed():
    a,r,s=context()
    o1,o2=occurrences(r)
    s=replace(s,admitted_events=(o2,o1))
    result=inv(a,r,s)
    assert tuple(x.event_time for x in result.batches)==(5,6)


def test_resident_event_does_not_authorize_consumption():
    a,r,s=context()
    o=occurrences(r)[0]
    result=inv(a,r,physical(a,s,o,'EVENT'))
    assert result.supports_consume_admission is False
    assert result.batches[0].closure_status=='OPEN_UNPROVEN'


def parallel_same_time_context():
    """Rebuild actual Core-derived registration with equal-delay parallel edges."""
    from spk_simulator.versioned_core_transition_v0 import prepare_core_transition_v0
    from spk_simulator.owned_dynamic_service_registration_v0 import (
        initialize_owned_dynamic_services_v0 as initialize,
        register_owned_computed_emission_services_v0 as register,
    )
    c=scenario()
    net=replace(c[1],edges=tuple(
        replace(edge,delay_ticks=2) if index==2 else edge
        for index,edge in enumerate(c[1].edges)
    ))
    image=replace(c[3],network=net)
    registry=initialize(c[0],net,c[2],image,
                        c[5].base_requests,c[5].base_graph,c[5].cost_policy)
    prepared=prepare_core_transition_v0(net,image,node_id='C',timestamp=3,channels=(0,))
    registry=register(registry,image,prepared).state
    return c[0],registry,RoutedStorageStateV0(c[0].profile_id,'E0')


def test_parallel_routes_same_event_time_group_preserves_multiplicity():
    a,r,s=parallel_same_time_context()
    occurrences_=occurrences(r)
    assert len(occurrences_)==2
    for occurrence in occurrences_:
        s=physical(a,s,occurrence,'EVENT')
    inventory=inv(a,r,s)
    assert len(inventory.batches)==1
    target=inventory.batches[0]
    assert target.event_time==5
    assert target.resident_route_request_ids==(5,6)
    assert target.resident_channels==(0,0)
    assert target.closure_status=='OPEN_UNPROVEN'


def test_parallel_routes_one_resident_one_pending_does_not_close():
    a,r,s=parallel_same_time_context()
    one,two=occurrences(r)
    s=physical(a,s,one,'EVENT')
    s=physical(a,s,two,'OUTPUT')
    target=inv(a,r,s).batches[0]
    assert target.resident_route_request_ids==(5,)
    assert target.resident_channels==(0,)
    assert tuple(x.stage for x in target.routes)==('EVENT','OUTPUT')
    assert target.closure_status=='OPEN_UNPROVEN'
