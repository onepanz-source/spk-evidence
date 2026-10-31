"""Computed Core fan-out must match a complete declared OUTPUT group.

Uses real repository fixtures; constructs a coherent Network topology from the
known source/target routes without changing the frozen Network implementation.
"""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_network.model_v0 import NetworkEdgeV0
from spk_simulator.computed_emission_binding_v0 import bind_computed_emission_v0 as bind
from spk_simulator.versioned_core_transition_v0 import (
    initialize_neuron_image_v0, prepare_core_transition_v0,
)
from tests.test_owned_internal_state_commit_v0 import context


def case(node='C', timestamp=3, emission_id=2):
    c = context(quiet=False)
    net = replace(c[1], edges=tuple(
        NetworkEdgeV0(
            r.occurrence.source_node_id, r.occurrence.source_channel,
            r.occurrence.target_node_id, r.occurrence.target_channel,
            r.occurrence.delivery_event_time - r.occurrence.emission_event_time,
        ) for r in c[2].routes
    ))
    image = initialize_neuron_image_v0(net)
    trans = prepare_core_transition_v0(net, image, node_id=node,
                                      timestamp=timestamp, channels=(0,))
    reqs = tuple(replace(r, target_id=f'outputs:{node}',
                         event_time=timestamp, quantity=len(trans.candidate_outputs))
                 if r.request_id == emission_id else r for r in c[4])
    return c[0], net, image, trans, c[2], c[3], reqs, emission_id


def run(c):
    return bind(*c[:7], emission_request_id=c[7])


def change(c, index, value):
    return (*c[:index], value, *c[index+1:])


def change_req(c, **fields):
    reqs = tuple(replace(r, **fields) if r.request_id == c[7] else r for r in c[6])
    return change(c, 6, reqs)


def change_route(c, route_id, **occ):
    routes = tuple(replace(r, occurrence=replace(r.occurrence, **occ))
                   if r.route_request_id == route_id else r for r in c[4].routes)
    return change(c, 4, replace(c[4], routes=routes))


def test_one_to_one_fanout():
    result = run(case('A', 2, 1))
    assert result.route_request_ids == (10,)
    assert result.candidate_outputs == ((2, 7),)
    assert result.required_output_slots == 1


def test_one_to_many_fanout():
    result = run(case())
    assert result.route_request_ids == (11, 12)
    assert result.required_output_slots == 2


def test_parallel_routes_keep_multiplicity():
    result = run(case())
    assert len(result.route_request_ids) == 2
    assert len(result.candidate_outputs) == 1


def test_event_time_from_core_not_service_tick():
    assert run(case()).event_time == 3


def test_output_source_is_real_core_node():
    assert run(case()).source_node_id == 'C'


def test_same_snapshot_deterministic():
    c = case()
    assert run(c) == run(c)


def test_request_reordering_is_deterministic():
    c = case()
    assert run(c) == run(change(c, 6, c[6][::-1]))


def test_returned_receipt_is_immutable():
    with pytest.raises((FrozenInstanceError, AttributeError)):
        run(case()).source_node_id = 'ALTERED'


def test_caller_image_not_modified():
    c = case()
    original = c[2]
    run(c)
    assert c[2] == original


def test_core_emitting_node_missing_from_upstream_manifest_is_rejected():
    # Historical replay manifest contains A and C; B actually emits, but was
    # never registered as an OUTPUT source. Do NOT grant it a fake publication.
    c = case('B', 4, 1)
    with pytest.raises(ValueError, match='identity mismatch'):
        run(c)


def test_no_matching_emission_request_rejected():
    c = case()
    with pytest.raises(ValueError, match='no declared'):
        run((*c[:7], 999))


def test_core_computed_route_not_declared_rejected():
    c = case()
    net = replace(c[1], edges=c[1].edges[:-1])
    image = initialize_neuron_image_v0(net)
    prep = prepare_core_transition_v0(net, image, node_id='C', timestamp=3, channels=(0,))
    with pytest.raises(ValueError, match='fan-out'):
        run((c[0], net, image, prep, *c[4:]))


def test_unexpected_network_edge_rejected():
    c = case()
    extra = NetworkEdgeV0('C', 7, 'A', 0, 4)
    net = replace(c[1], edges=c[1].edges + (extra,))
    image = initialize_neuron_image_v0(net)
    prep = prepare_core_transition_v0(net, image, node_id='C', timestamp=3, channels=(0,))
    with pytest.raises(ValueError, match='fan-out'):
        run((c[0], net, image, prep, *c[4:]))


@pytest.mark.parametrize('modification', [
    {'source_channel': 3},
    {'target_channel': 9},
    {'delivery_event_time': 10},
])
def test_route_occurrence_disagrees_with_frozen_network(modification):
    c = change_route(case(), 11, **modification)
    with pytest.raises(ValueError, match='fan-out'):
        run(c)


def test_source_pe_mismatch_rejected():
    with pytest.raises(ValueError, match='source/PE'):
        run(change_route(case(), 11, source_pe_id='PE1'))


def test_group_emission_time_mismatch_rejected():
    c = case()
    groups = tuple(replace(g, emission_event_time=4) if g.emission_request_id == 2 else g
                   for g in c[5].groups)
    with pytest.raises(ValueError, match='identity mismatch'):
        run(change(c, 5, replace(c[5], groups=groups)))


def test_group_source_node_mismatch_rejected():
    c = case()
    groups = tuple(replace(g, source_node_id='A') if g.emission_request_id == 2 else g
                   for g in c[5].groups)
    with pytest.raises(ValueError, match='identity mismatch'):
        run(change(c, 5, replace(c[5], groups=groups)))


@pytest.mark.parametrize('modification', [
    {'target_id': 'events:C'},
    {'event_time': 5},
    {'quantity': 2},
    {'target_pe_id': 'PE1'},
    {'epoch_id': 'OTHER'},
])
def test_mismatched_emission_request_rejected(modification):
    with pytest.raises(ValueError, match='identity mismatch'):
        run(change_req(case(), **modification))


def test_wrong_kind_rejected():
    with pytest.raises(ValueError, match='identity mismatch'):
        run(change_req(case(), kind=Kind.STATE_LOAD))


def test_missing_route_identity_rejected():
    c = case()
    groups = tuple(replace(g, route_request_ids=(11,), required_output_slots=1)
                   if g.emission_request_id == 2 else g for g in c[5].groups)
    with pytest.raises(ValueError, match='coverage'):
        run(change(c, 5, replace(c[5], groups=groups)))


def test_duplicate_route_group_claim_rejected():
    c = case()
    groups = tuple(replace(g, route_request_ids=(10, 11, 12), required_output_slots=3)
                   if g.emission_request_id == 2 else g for g in c[5].groups)
    with pytest.raises(ValueError, match='coverage|capacity'):
        run(change(c, 5, replace(c[5], groups=groups)))


def test_capacity_exceeded_rejected():
    c = case()
    arch = replace(c[0], pes=tuple(replace(pe, output_slots=1) for pe in c[0].pes))
    groups = tuple(replace(g, output_capacity=1) for g in c[5].groups)
    with pytest.raises(ValueError, match='capacity'):
        run((arch, *c[1:5], replace(c[5], groups=groups), *c[6:]))


def test_profile_mismatch_rejected():
    c = case()
    with pytest.raises(ValueError, match='profile'):
        run(change(c, 4, replace(c[4], profile_id='INCOMPATIBLE')))


def test_epoch_mismatch_rejected():
    c = case()
    with pytest.raises(ValueError, match='epoch'):
        run(change(c, 2, replace(c[2], epoch_id='INCOMPATIBLE')))


def test_altered_computed_core_output_rejected():
    c = case()
    bad = replace(c[3], candidate_outputs=((3, 999),))
    with pytest.raises(ValueError, match='Core result'):
        run(change(c, 3, bad))


def test_altered_core_raw_rejected():
    c = case()
    with pytest.raises(ValueError, match='Core result'):
        run(change(c, 3, replace(c[3], after_raw=23)))


def test_wrong_core_base_version_rejected():
    c = case()
    with pytest.raises(ValueError, match='Core result'):
        run(change(c, 3, replace(c[3], base_version=4)))


def test_missing_core_outputs_rejected():
    from spk_core.isa import CoreCmp, CoreProgram
    c = case()
    node = next(n for n in c[1].nodes if n.node_id == 'C')
    program = CoreProgram(tuple(replace(op, threshold_raw=100)
                                if isinstance(op, CoreCmp) else op
                                for op in node.program.instructions))
    net = replace(c[1], nodes=tuple(replace(n, program=program) if n.node_id=='C'
                                    else n for n in c[1].nodes))
    image = initialize_neuron_image_v0(net)
    prep = prepare_core_transition_v0(net,image,node_id='C',timestamp=3,channels=(0,))
    with pytest.raises(ValueError, match='no computed'):
        run((c[0],net,image,prep,*c[4:]))


def test_terminal_emission_without_route_has_explicit_channel():
    c = case('A', 2, 1)
    net = replace(c[1], edges=())
    image = initialize_neuron_image_v0(net)
    prep = prepare_core_transition_v0(net,image,node_id='A',timestamp=2,channels=(0,))
    manifest = replace(c[4], routes=())
    group = replace(c[5].groups[0], route_request_ids=(), required_output_slots=0)
    admission = replace(c[5],groups=(group,), routed_occurrence_count=0,
                        zero_fanout_emission_count=1)
    assert run((c[0],net,image,prep,manifest,admission,c[6],1)).terminal_channels == (7,)


def test_invalid_emission_id_rejected():
    c = case()
    with pytest.raises(ValueError, match='emission request ID'):
        run((*c[:7], '2'))


def test_invalid_core_preparation_type_rejected():
    with pytest.raises(TypeError, match='invalid Core'):
        run(change(case(),3,object()))


def test_invalid_request_collection_rejected():
    c=case()
    with pytest.raises(TypeError, match='requests'):
        run(change(c,6,list(c[6])))


def test_replay_plan_is_not_a_publication_receipt():
    receipt=run(case())
    assert not hasattr(receipt,'state')
    assert not hasattr(receipt,'confirmed_request_ids')
    assert not hasattr(receipt,'publication_boundary')
