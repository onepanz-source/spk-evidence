"""S3.7d/3b2b2k/9: no replay trace or predeclared route manifest is used."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_compiler.pe_admission_v0 import NodePlacementV0, admit_pe_mapping_v0
from spk_network.model_v0 import NetworkEdgeV0
from spk_simulator.computed_topology_routing_v0 import (
    ComputedFanoutCapacityV0, derive_computed_topology_routing_v0 as derive,
)
from spk_simulator.versioned_core_transition_v0 import (
    initialize_neuron_image_v0, prepare_core_transition_v0,
)
from tests.test_computed_emission_binding_v0 import case


def context(node='C', timestamp=3, *, cursor=100, edges=None):
    c = case(node, timestamp, 1 if node=='A' else 2)
    arch, net = c[0], c[1]
    if edges is not None:
        net = replace(net, edges=edges)
    image = initialize_neuron_image_v0(net)
    prepared = prepare_core_transition_v0(
        net, image, node_id=node, timestamp=timestamp, channels=(0,),
    )
    manifest = admit_pe_mapping_v0(net, arch, (
        NodePlacementV0('A','PE0'),
        NodePlacementV0('B','PE1'),
        NodePlacementV0('C','PE0'),
    ))
    return arch, net, manifest, image, prepared, cursor


def run(c, *, used=()):
    return derive(*c[:5], first_event_id=c[5], used_event_ids=used)


def change(c, index, value):
    return (*c[:index], value, *c[index+1:])


def candidate(c, **kwargs):
    return change(c,4,replace(c[4],**kwargs))


def test_core_route_one_to_one():
    x=run(context('A',2))
    assert len(x.routes)==1
    r=x.routes[0].occurrence
    assert (r.source_node_id,r.source_pe_id,r.source_channel)==('A','PE0',7)
    assert (r.target_node_id,r.target_pe_id,r.target_channel)==('B','PE1',0)
    assert (r.emission_event_time,r.delivery_event_time)==(2,4)


def test_one_to_many_parallel_edges():
    x=run(context())
    assert len(x.routes)==2
    assert [r.occurrence.event_id for r in x.routes]==[100,101]
    assert all(r.occurrence.target_node_id=='B' for r in x.routes)
    assert [r.edge_index for r in x.routes]==[1,2]


def test_parallel_physical_edges_have_distinct_route_identities_and_delays():
    x=run(context())
    assert x.routes[0].occurrence!=x.routes[1].occurrence
    assert (x.routes[0].occurrence.event_id,x.routes[1].occurrence.event_id)==(100,101)
    assert (x.routes[0].occurrence.delivery_event_time,x.routes[1].occurrence.delivery_event_time)==(5,6)


def test_fanout_is_derived_without_replay_manifest():
    x=run(context('B',4))
    assert x.routes==()
    assert len(x.terminal_outputs)==1
    assert x.terminal_outputs[0].node_id=='B'


def test_terminal_channels_are_not_materialized_as_routed_events():
    x=run(context('B',4))
    assert x.required_output_slots==0
    assert x.next_event_id==100
    assert x.terminal_outputs[0].channel==7


def test_terminal_output_retains_core_event_time():
    assert run(context('B',4)).terminal_outputs[0].timestamp==4


def test_route_event_time_is_not_service_time():
    x=run(context('A',2,cursor=37))
    assert (x.event_time,x.routes[0].occurrence.emission_event_time)==(2,2)
    assert x.routes[0].occurrence.delivery_event_time==4


def test_id_cursor_progression():
    x=run(context(cursor=20))
    assert (x.routes[0].occurrence.event_id,x.next_event_id)==(20,22)


def test_no_first_id_reuse_against_retained_history():
    with pytest.raises(ValueError,match='cursor overlaps'):
        run(context(cursor=100),used=(2,100))


def test_next_id_follows_retained_history():
    assert run(context(cursor=100),used=(0,99)).next_event_id==102


def test_empty_history_allowed():
    assert run(context(cursor=0)).routes[0].occurrence.event_id==0


def test_repeated_snapshot_is_deterministic():
    c=context()
    assert run(c)==run(c)


def test_no_image_mutation():
    c=context()
    old=c[3]
    run(c)
    assert c[3]==old


def test_immutable_result():
    x=run(context())
    with pytest.raises((FrozenInstanceError,AttributeError)):
        x.routes=()


def test_core_result_not_accepted_if_forged():
    c=context()
    with pytest.raises(ValueError,match='computed Core preparation mismatch'):
        run(candidate(c,candidate_outputs=((3,99),)))


def test_stale_core_version_not_accepted():
    c=context()
    with pytest.raises(ValueError,match='computed Core preparation mismatch'):
        run(candidate(c,base_version=9))


def test_wrong_raw_not_accepted():
    c=context()
    with pytest.raises(ValueError,match='computed Core preparation mismatch'):
        run(candidate(c,after_raw=99))


def test_invalid_cursor_bool_rejected():
    with pytest.raises(ValueError,match='identity cursor'):
        run(change(context(),5,True))


def test_invalid_cursor_negative_rejected():
    with pytest.raises(ValueError,match='identity cursor'):
        run(change(context(),5,-1))


@pytest.mark.parametrize('used',[(1,1),(2,1),(-1,),(True,),(1.0,),[1]])
def test_noncanonical_history_rejected(used):
    with pytest.raises(ValueError,match='noncanonical used'):
        run(context(),used=used)


def test_manifest_wrong_profile_rejected():
    c=context()
    with pytest.raises(ValueError,match='profile mismatch'):
        run(change(c,2,replace(c[2],profile_id='OTHER')))


def test_manifest_missing_one_node_rejected():
    c=context()
    with pytest.raises(ValueError):
        changed=replace(c[2],pe_usage=tuple(replace(p,node_ids=tuple(
            node for node in p.node_ids if node!='B')) for p in c[2].pe_usage))
        run(change(c,2,changed))


def test_manifest_duplicate_node_rejected():
    c=context()
    pe0,pe1=c[2].pe_usage
    with pytest.raises(ValueError):
        changed=replace(c[2],pe_usage=(replace(pe0,node_ids=pe0.node_ids+('B',)),pe1))
        run(change(c,2,changed))


def test_image_epoch_mismatch_rejected():
    c=context()
    with pytest.raises(ValueError,match='image/epoch'):
        run(change(c,3,replace(c[3],epoch_id='OTHER')))


def test_image_network_mismatch_rejected():
    c=context()
    with pytest.raises(ValueError,match='image/epoch'):
        run(change(c,3,replace(c[3],network=replace(c[1],edges=()))))


def test_output_capacity_blocks_unsplittable_fanout():
    c=context()
    arch=replace(c[0],pes=tuple(replace(pe,output_slots=1)for pe in c[0].pes))
    with pytest.raises(ComputedFanoutCapacityV0)as ex:
        run(change(c,0,arch))
    assert ex.value.required==2 and ex.value.capacity==1


def test_output_capacity_does_not_forbid_single_route():
    c=context('A',2)
    arch=replace(c[0],pes=tuple(replace(pe,output_slots=1)for pe in c[0].pes))
    assert run(change(c,0,arch)).required_output_slots==1


def test_two_routes_without_duplicate_edges():
    c=context()
    edges=c[1].edges[:2]
    c=context(edges=edges)
    x=run(c)
    assert x.required_output_slots==1


def test_add_destination_edge_changes_computed_route_set():
    c=context('A',2)
    net=c[1]
    extra=NetworkEdgeV0('A',7,'C',0,5)
    changed=context('A',2,edges=(net.edges[0],extra)+net.edges[1:])
    x=run(changed)
    assert {r.occurrence.target_node_id for r in x.routes}=={'B','C'}
    assert {r.occurrence.delivery_event_time for r in x.routes}=={4,7}


def test_unmatched_edge_is_terminal_output():
    c=context('A',2,edges=())
    x=run(c)
    assert len(x.terminal_outputs)==1 and x.routes==()


def test_all_nodes_planned_independently_of_route_manifest():
    assert run(context('B',4)).source_pe_id=='PE1'
    assert run(context('C',3)).source_pe_id=='PE0'


def test_identical_parallel_edges_remain_distinct_events():
    c=context('C',3)
    arch=replace(c[0],pes=tuple(replace(p,output_slots=3) for p in c[0].pes))
    net=replace(c[1],edges=c[1].edges+(c[1].edges[-1],))
    placement=admit_pe_mapping_v0(net,arch,(
        NodePlacementV0('A','PE0'),NodePlacementV0('B','PE1'),
        NodePlacementV0('C','PE0'),
    ))
    image=initialize_neuron_image_v0(net)
    prep=prepare_core_transition_v0(net,image,node_id='C',timestamp=3,channels=(0,))
    output=derive(arch,net,placement,image,prep,first_event_id=100)
    assert len(output.routes)==3
    assert tuple(r.occurrence.event_id for r in output.routes)==(100,101,102)
    assert replace(output.routes[1].occurrence,event_id=102)==output.routes[2].occurrence


def test_replay_same_cursor_yields_same_plan_not_a_committed_publication():
    c=context()
    original=run(c)
    repeated=run(c)
    assert original == repeated
    # A distinct future emission MUST use the advanced cursor supplied by its owner.
    following=run(change(c,5,original.next_event_id),used=(100,101))
    assert {r.occurrence.event_id for r in following.routes}=={102,103}
