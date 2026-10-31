"""Conservative structural temporal obligations; NEVER a closure certificate."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.dynamic_batch_closure_obligations_v0 import (
    EventTimeClaimV0 as Claim,
    analyze_dynamic_batch_closure_v0 as analyze,
)
from tests.test_dynamic_destination_inventory_v0 import (
    context, physical, occurrences, parallel_same_time_context,
)


def run(a=None, r=None, s=None, *, claims=()):
    if a is None:
        a, r, s = context()
    return analyze(a, r, s, frontier_claims=claims)


def b(result, t):
    return next(x for x in result.batches if x.event_time == t)


def source(node, t):
    return Claim('SOURCE_EMISSION', node, t)


def ingress(node, t):
    return Claim('EXTERNAL_INGRESS', node, t)


def full_claims():
    return (source('A', 10), source('C', 10), ingress('B', 10))


def all_resident(a,r,s):
    for occ in occurrences(r):
        s=physical(a,s,occ,'EVENT')
    return s


def test_two_destination_times_obligations():
    x=run()
    assert tuple(t.event_time for t in x.batches)==(5,6)
    assert all(t.status=='OPEN_UNPROVEN' for t in x.batches)
    assert not x.supports_consume_admission


def test_uses_frozen_topology_from_registry():
    x=run()
    for batch in x.batches:
        assert batch.target_node_id=='B'
        assert all(edge.source_node_id in {'A','C'} for edge in batch.edge_obligations)


def test_source_threshold_is_target_time_minus_edge_delay():
    x=run()
    five=b(x,5)
    six=b(x,6)
    assert {(e.source_node_id,e.delay_ticks,e.required_source_settled_through) for e in five.edge_obligations} == {
        ('A',2,3),('C',2,3),('C',3,2),
    }
    assert {(e.source_node_id,e.delay_ticks,e.required_source_settled_through) for e in six.edge_obligations} == {
        ('A',2,4),('C',2,4),('C',3,3),
    }


def test_external_requirement_is_per_target_time():
    x=run()
    assert b(x,5).required_external_settled_through==5
    assert b(x,6).required_external_settled_through==6


def test_no_claims_never_closes_even_if_all_routes_resident():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s))
    assert all(t.all_registered_routes_resident for t in x.batches)
    assert all(not t.declared_preconditions_met for t in x.batches)
    assert all(not t.supports_consume_admission for t in x.batches)


def test_strong_claims_no_resident_still_not_ready():
    x=run(claims=full_claims())
    assert all(t.source_requirements_claimed for t in x.batches)
    assert all(t.ingress_requirement_claimed for t in x.batches)
    assert all(not t.declared_preconditions_met for t in x.batches)


def test_fully_claimed_resident_remains_unproven():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s),claims=full_claims())
    assert all(t.declared_preconditions_met for t in x.batches)
    assert all(t.status=='OPEN_UNPROVEN' for t in x.batches)
    assert not x.supports_consume_admission
    assert all(not t.supports_consume_admission for t in x.batches)


def test_missing_external_claim_never_closes():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s),claims=(source('A',100),source('C',100)))
    assert all(t.source_requirements_claimed for t in x.batches)
    assert all(not t.ingress_requirement_claimed for t in x.batches)


def test_missing_a_source_claim_never_closes():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s),claims=(source('C',100),ingress('B',100)))
    assert all(not t.source_requirements_claimed for t in x.batches)


def test_insufficient_source_frontier_for_only_later_batch():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s),claims=(source('A',3),source('C',3),ingress('B',6)))
    assert b(x,5).source_requirements_claimed
    assert not b(x,6).source_requirements_claimed


def test_insufficient_external_frontier_for_only_later_batch():
    a,r,s=context()
    x=run(a,r,all_resident(a,r,s),claims=(source('A',100),source('C',100),ingress('B',5)))
    assert b(x,5).ingress_requirement_claimed
    assert not b(x,6).ingress_requirement_claimed


@pytest.mark.parametrize('stage',('STAGED','OUTPUT','EVENT','CONSUMED'))
def test_storage_stage_reconciliation(stage):
    a,r,s=context()
    o=occurrences(r)[0]
    x=run(a,r,physical(a,s,o,stage),claims=full_claims())
    five=b(x,5)
    assert five.route_request_ids==(o.event_id,)
    assert (five.resident_route_request_ids==(o.event_id,))==(stage=='EVENT')
    assert (five.blocking_route_request_ids==(o.event_id,))==(stage in ('STAGED','OUTPUT'))
    assert (five.already_consumed_route_request_ids==(o.event_id,))==(stage=='CONSUMED')
    assert not five.supports_consume_admission


def test_consumed_identity_never_readmitted():
    a,r,s=context()
    o=occurrences(r)[0]
    result=run(a,r,physical(a,s,o,'CONSUMED'),claims=full_claims())
    assert not b(result,5).declared_preconditions_met


def test_route_identities_preserved_and_sorted():
    a,r,s=parallel_same_time_context()
    x=run(a,r,all_resident(a,r,s),claims=full_claims())
    assert len(x.batches)==1
    z=x.batches[0]
    assert z.route_request_ids==(5,6)
    assert z.resident_route_request_ids==(5,6)
    assert len(z.edge_obligations)==3
    assert z.declared_preconditions_met
    assert not z.supports_consume_admission


def test_parallel_edge_obligations_preserve_indices():
    a,r,s=parallel_same_time_context()
    z=run(a,r,s).batches[0]
    assert len({e.edge_index for e in z.edge_obligations})==3
    assert len([e for e in z.edge_obligations if e.source_node_id=='C'])==2


def test_claim_is_not_timestamp_of_storage_service():
    x=run(claims=(source('C',5),))
    assert x.batches[0].edge_obligations
    # A *claim* in EVENT_TIME is not a SERVICE_TIME counter or a certificate.
    assert not x.supports_consume_admission


def test_inventories_unchanged_by_analysis():
    a,r,s=context()
    before=(a,r,s)
    run(a,r,s,claims=full_claims())
    assert (a,r,s)==before


def test_deterministic():
    a,r,s=context()
    assert run(a,r,s,claims=full_claims())==run(a,r,s,claims=full_claims())


def test_immutable_result():
    with pytest.raises((AttributeError,FrozenInstanceError)):
        run().batches=()


def test_immutable_batch():
    with pytest.raises((AttributeError,FrozenInstanceError)):
        run().batches[0].status='CLOSED'


@pytest.mark.parametrize('bad', [Claim('SOURCE_EMISSION','A',1),Claim('EXTERNAL_INGRESS','A',1)])
def test_claim_types_are_valid(bad):
    assert bad.node_id=='A'


@pytest.mark.parametrize('kind', ('', 'SOURCE','external', 7, None))
def test_invalid_claim_kind(kind):
    with pytest.raises(ValueError,match='kind'):
        Claim(kind,'A',1)


@pytest.mark.parametrize('node', ('',' A','A ',7,None))
def test_invalid_claim_node(node):
    with pytest.raises(ValueError,match='node'):
        Claim('SOURCE_EMISSION',node,1)


@pytest.mark.parametrize('time',(-2,True,1.2,'3',None))
def test_invalid_claim_time(time):
    with pytest.raises(ValueError,match='time'):
        Claim('SOURCE_EMISSION','A',time)


def test_minus_one_frontier_represents_nothing_settled():
    x=run(claims=(source('C',-1),))
    assert not x.batches[0].source_requirements_claimed


def test_duplicate_claim_rejected():
    with pytest.raises(ValueError,match='duplicate'):
        run(claims=(source('A',4),source('A',5)))


def test_unknown_node_claim_rejected():
    with pytest.raises(ValueError,match='unknown'):
        run(claims=(source('MISSING',3),))


def test_independent_kind_for_same_node_allowed():
    assert run(claims=(source('B',9),ingress('B',9))).batches


@pytest.mark.parametrize('bad',(None,[],[source('C',3)],(1,),))
def test_invalid_claim_collection_rejected(bad):
    with pytest.raises(TypeError,match='claims'):
        run(claims=bad)


def test_wrong_architecture_rejected():
    a,r,s=context()
    with pytest.raises(TypeError,match='architecture'):
        analyze(None,r,s)


def test_wrong_registry_rejected():
    a,r,s=context()
    with pytest.raises(TypeError,match='registration'):
        analyze(a,None,s)


def test_wrong_storage_rejected():
    a,r,s=context()
    with pytest.raises(TypeError,match='storage'):
        analyze(a,r,None)


def test_unknown_dynamic_event_rejected_by_inventory():
    a,r,s=context()
    o=occurrences(r)[0]
    with pytest.raises(ValueError,match='unknown dynamic'):
        run(a,r,replace(s,admitted_events=(replace(o,event_id=999),)))


def test_wrong_epoch_rejected_by_inventory():
    a,r,s=context()
    with pytest.raises(ValueError,match='epoch'):
        run(a,r,replace(s,epoch_id='WRONG'))


def test_no_route_batches_does_not_invent_closure():
    from tests.test_owned_dynamic_service_registration_v0 import scenario, do
    from spk_simulator.event_storage_v0 import RoutedStorageStateV0
    c=scenario(nodes=('B',))
    state=do(c,node='B').state
    result=run(c[0],state,RoutedStorageStateV0(c[0].profile_id,'E0'))
    assert result.batches==()
    assert not result.supports_consume_admission


def test_vacuous_edge_if_delivery_precedes_minimal_edge_delay():
    from spk_network.model_v0 import NetworkEdgeV0
    from spk_simulator.versioned_core_transition_v0 import (
        initialize_neuron_image_v0, prepare_core_transition_v0,
    )
    from spk_simulator.owned_dynamic_service_registration_v0 import (
        initialize_owned_dynamic_services_v0 as initialize,
        register_owned_computed_emission_services_v0 as register,
    )
    from spk_simulator.event_storage_v0 import RoutedStorageStateV0
    from tests.test_owned_dynamic_service_registration_v0 import scenario
    c=scenario()
    # Extra incoming edge is from A, while this scenario computes C's output.
    # No newly registered route is caused by the additional slow A -> B edge.
    net=replace(c[1],edges=c[1].edges+(
        NetworkEdgeV0('A',7,'B',0,99),
    ))
    image=initialize_neuron_image_v0(net)
    owner=initialize(c[0],net,c[2],image,
                     c[5].base_requests,c[5].base_graph,c[5].cost_policy)
    prepared=prepare_core_transition_v0(net,image,node_id='C',timestamp=3,channels=(0,))
    registry=register(owner,image,prepared).state
    x=run(c[0],registry,RoutedStorageStateV0(c[0].profile_id,'E0'))
    slow=[e for e in b(x,5).edge_obligations if e.delay_ticks==99]
    assert len(slow)==1
    assert slow[0].required_source_settled_through==-94
    assert slow[0].claim_covers_requirement
    assert not x.supports_consume_admission


def test_claims_do_not_override_physical_provenance():
    a,r,s=context()
    o=occurrences(r)[0]
    with pytest.raises(ValueError,match='provenance'):
        run(a,r,replace(s,admitted_events=(replace(o,source_channel=3),)),
            claims=full_claims())


def test_route_pending_in_output_blocks_even_if_other_resident():
    a,r,s=parallel_same_time_context()
    first,second=occurrences(r)
    s=physical(a,s,first,'EVENT')
    s=physical(a,s,second,'OUTPUT')
    z=run(a,r,s,claims=full_claims()).batches[0]
    assert z.resident_route_request_ids==(first.event_id,)
    assert z.blocking_route_request_ids==(second.event_id,)
    assert not z.declared_preconditions_met
    assert not z.supports_consume_admission


def test_future_arrival_not_ruled_out_by_current_inventory():
    a,r,s=context()
    s=all_resident(a,r,s)
    z=run(a,r,s).batches[0]
    assert z.all_registered_routes_resident
    assert not z.source_requirements_claimed
    assert z.status=='OPEN_UNPROVEN'


def test_claim_order_does_not_change_result():
    a,r,s=context()
    assert run(a,r,s,claims=full_claims()) == run(a,r,s,claims=full_claims()[::-1])
