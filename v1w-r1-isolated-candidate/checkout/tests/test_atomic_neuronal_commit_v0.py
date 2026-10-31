"""Atomic routed STATE/OUTPUT integration with existing bounded SPK controller."""
from dataclasses import FrozenInstanceError, replace
import pytest
from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_network.model_v0 import NetworkEdgeV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionGroupV0
from spk_simulator.event_storage_v0 import RoutedOccurrenceV0
from spk_simulator.routing_binding_v0 import BoundRouteV0
from spk_simulator.owned_internal_reads_v0 import advance_owned_internal_reads_v0, audit_committed_internal_history_v0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
from spk_simulator.atomic_neuronal_commit_v0 import commit_atomic_neuronal_output_v0
from tests.test_owned_internal_state_commit_v0 import context


def scenario(*, fanout=1):
    arch, net, manifest, admission, requests, graph, state, ingress = context(quiet=False)
    assert fanout in (1, 2)
    routed_ids = tuple(range(13, 13 + fanout))
    added_routes = tuple(BoundRouteV0(i, 51, 1, RoutedOccurrenceV0(
        i, 'E0', 'B', 'PE1', 7, 'B', 'PE1', 0, 4, 5,
    )) for i in routed_ids)
    manifest = replace(manifest, routes=tuple(sorted(manifest.routes + added_routes,
                                                   key=lambda x: x.route_request_id)))
    capacity = next(pe.output_slots for pe in arch.pes if pe.pe_id == 'PE1')
    emission = AtomicEmissionGroupV0(3, 'PE1', 'B', 4, routed_ids, fanout, capacity)
    admission = replace(admission,
        groups=tuple(sorted(admission.groups + (emission,), key=lambda x: x.emission_request_id)),
        routed_occurrence_count=admission.routed_occurrence_count + fanout,
    )
    e = next(r for r in requests if r.request_id == 2)
    r = next(r for r in requests if r.request_id == 11)
    e_fields = {'requester_pe_id': 'PE1'} if hasattr(e, 'requester_pe_id') else {}
    r_fields = {'requester_pe_id': 'PE1'} if hasattr(r, 'requester_pe_id') else {}
    extras = (replace(e, request_id=3, target_pe_id='PE1', **e_fields,
                      target_id='outputs:B', event_time=4, quantity=1),) + tuple(
        replace(r, request_id=i, target_pe_id='PE1', event_time=4, **r_fields)
        for i in routed_ids
    )
    requests = tuple(sorted(requests + extras, key=lambda x: x.request_id))
    preds = {x.request_id: set(x.predecessor_ids if hasattr(x, 'predecessor_ids')
                               else x.predecessors) for x in graph.dependencies}
    preds[3] = {50}
    for i in routed_ids:
        preds[i] = {3}
        preds[51].add(i)
    graph = AccessDependencyGraphV0(tuple(
        AccessDependencyV0(i, tuple(sorted(v))) for i, v in sorted(preds.items())
    ))
    graph = serialize_internal_access_graph_v0(requests, graph).graph
    net = replace(net, edges=tuple(
        NetworkEdgeV0(
            route.occurrence.source_node_id, route.occurrence.source_channel,
            route.occurrence.target_node_id, route.occurrence.target_channel,
            route.occurrence.delivery_event_time-route.occurrence.emission_event_time,
        ) for route in manifest.routes
    ))
    state = replace(state, image=initialize_neuron_image_v0(net))
    return arch, net, manifest, admission, requests, graph, state, ingress


def tick(c):
    return advance_owned_internal_reads_v0(*c[:6], c[6], ingress=c[7])


def ready(c, limit=24):
    for i in range(limit):
        svc = c[6].owned.boundary.service
        waiting = {x.request_id for x in svc.awaiting_confirmation}
        active = {x.emission_request_id for x in c[6].owned.output.active}
        if {3, 80} <= waiting and 3 in active and c[6].prepared:
            return c
        try:
            state=tick(c).state
        except Exception as exc:
            print('NOTREADY',i, sorted(waiting), sorted(active), exc)
            raise
        c=(*c[:6],state,c[7])
    raise AssertionError('atomic ready not achieved')


def test_real_emission_and_state_commit():
    c = ready(scenario())
    output=commit_atomic_neuronal_output_v0(*c[:7],commit_request_id=80,emission_request_id=3,ingress=c[7])
    assert output.publication.route_request_ids == (13,)
    assert output.state.image.neurons[1].version == 1
    assert 13 in {r.event_id for r in output.state.owned.boundary.driver.boundary.storage.pending_output}
    assert {3,80} <= {x.request_id for x in output.state.owned.boundary.service.confirmed}


def act(c):
    return commit_atomic_neuronal_output_v0(
        *c[:7], commit_request_id=80, emission_request_id=3, ingress=c[7],
    )


def change_state(c, state):
    return (*c[:6], state, c[7])


def test_precommit_has_not_published_core_route():
    c=ready(scenario())
    assert 13 not in {x.event_id for x in c[6].owned.boundary.driver.boundary.storage.pending_output}
    assert 3 not in c[6].owned.output.completed_emission_ids


def test_atomic_boundary_is_not_neuronal_event_time():
    result=act(ready(scenario()))
    assert result.owner_tick.service_boundary == 6
    assert result.publication.event_time == 4


def test_same_snapshot_is_deterministic():
    c=ready(scenario())
    assert act(c)==act(c)


def test_neither_old_state_nor_ledger_is_modified():
    c=ready(scenario())
    previous=c[6]
    result=act(c)
    assert previous.image.neurons[1].version == 0
    assert previous.owned.output.completed_emission_ids == (1,2)
    assert 3 in result.state.owned.output.completed_emission_ids


def test_physical_output_publication_is_complete():
    result=act(ready(scenario()))
    before=result.state.owned.boundary.driver.boundary.storage
    occurrences=[x for x in before.pending_output if x.event_id==13]
    assert len(occurrences)==1
    assert occurrences[0].source_node_id == 'B'
    assert occurrences[0].emission_event_time == 4


def test_atomic_commit_cleans_preparation():
    result=act(ready(scenario()))
    assert not result.state.prepared
    assert result.state.commits[-1].emission_binding == result.publication


def test_historical_audit_reconstructs_emitting_state():
    c=ready(scenario())
    result=act(c)
    snapshots=audit_committed_internal_history_v0(
        c[1],result.state,c[4],c[5],architecture=c[0],manifest=c[2],admission=c[3],
    )
    assert snapshots[('B',1)].raw == 0
    assert snapshots[('B',1)].last_timestamp == 4


def test_audit_requires_output_context():
    c=ready(scenario())
    result=act(c)
    with pytest.raises(ValueError,match='requires architectural OUTPUT context'):
        audit_committed_internal_history_v0(c[1],result.state,c[4],c[5])


def test_precommit_cannot_claim_missing_reservation():
    c=ready(scenario())
    owned=replace(c[6].owned,output=replace(c[6].owned.output,active=()))
    with pytest.raises(ValueError,match='no live OUTPUT reservation'):
        act(change_state(c,replace(c[6],owned=owned)))


def test_cannot_commit_before_emission_service_finishes():
    c=ready(scenario())
    svc=c[6].owned.boundary.service
    altered=replace(svc,awaiting_confirmation=tuple(x for x in svc.awaiting_confirmation if x.request_id!=3))
    owned=replace(c[6].owned,boundary=replace(c[6].owned.boundary,service=altered))
    with pytest.raises(ValueError,match='service has not finished'):
        act(change_state(c,replace(c[6],owned=owned)))


def test_cannot_commit_before_state_service_finishes():
    c=ready(scenario())
    svc=c[6].owned.boundary.service
    altered=replace(svc,awaiting_confirmation=tuple(x for x in svc.awaiting_confirmation if x.request_id!=80))
    owned=replace(c[6].owned,boundary=replace(c[6].owned.boundary,service=altered))
    with pytest.raises(ValueError,match='service has not finished'):
        act(change_state(c,replace(c[6],owned=owned)))


def test_wrong_emission_request_cannot_be_used():
    c=ready(scenario())
    with pytest.raises(ValueError,match='target or EVENT_TIME mismatch'):
        commit_atomic_neuronal_output_v0(*c[:7],commit_request_id=80,emission_request_id=2,ingress=c[7])


def test_request_replay_is_rejected():
    c=ready(scenario())
    out=act(c)
    with pytest.raises(ValueError,match='service has not finished'):
        act(change_state(c,out.state))


def test_corrupt_output_evidence_is_detected_on_resume():
    c=ready(scenario())
    out=act(c)
    evidence=replace(out.state.commits[-1],emission_binding=replace(out.publication,route_request_ids=(999,)))
    bad=replace(out.state,commits=out.state.commits[:-1]+(evidence,))
    with pytest.raises(ValueError,match='historical OUTPUT binding mismatch'):
        audit_committed_internal_history_v0(c[1],bad,c[4],c[5],architecture=c[0],manifest=c[2],admission=c[3])


def test_missing_published_route_identity_fails_audit():
    c=ready(scenario())
    out=act(c)
    driver=out.state.owned.boundary.driver
    storage=driver.boundary.storage
    altered=replace(storage,pending_output=tuple(x for x in storage.pending_output if x.event_id != 13))
    new_driver=replace(driver,boundary=replace(driver.boundary,storage=altered))
    new_owner=replace(out.state.owned,boundary=replace(out.state.owned.boundary,driver=new_driver))
    bad=replace(out.state,owned=new_owner)
    with pytest.raises(ValueError,match='historical STATE commit lacks authenticated OUTPUT publication'):
        audit_committed_internal_history_v0(c[1],bad,c[4],c[5],architecture=c[0],manifest=c[2],admission=c[3])


def test_reject_forged_prepared_core_result():
    c=ready(scenario())
    prep=c[6].prepared[0]
    modified=replace(prep,transition=replace(prep.transition,after_raw=20))
    bad=replace(c[6],prepared=(modified,))
    with pytest.raises(ValueError,match='prepared transition disagrees|Core'):
        act(change_state(c,bad))


def test_wrong_commit_id_is_rejected():
    c=ready(scenario())
    with pytest.raises(ValueError,match='missing atomic'):
        commit_atomic_neuronal_output_v0(*c[:7],commit_request_id=999,emission_request_id=3,ingress=c[7])


def test_bad_atomic_input_type_rejected():
    c=ready(scenario())
    with pytest.raises(TypeError,match='invalid service requests'):
        commit_atomic_neuronal_output_v0(*c[:4],list(c[4]),c[5],c[6],commit_request_id=80,emission_request_id=3,ingress=c[7])


def test_returned_immutable_snapshot():
    c=ready(scenario())
    out=act(c)
    with pytest.raises((FrozenInstanceError,AttributeError)):
        out.state.image = None


def test_atomic_two_parallel_routes_are_published_together():
    c=ready(scenario(fanout=2))
    result=act(c)
    assert result.publication.route_request_ids==(13,14)
    assert result.publication.candidate_outputs==((4,7),)
    assert result.evidence.receipt.new_version==1
    assert {13,14} <= {x.event_id for x in result.state.owned.boundary.driver.boundary.storage.pending_output}


def test_atomic_parallel_routes_fail_closed_if_output_capacity_too_small():
    c=scenario(fanout=2)
    arch=replace(c[0], pes=tuple(replace(pe,output_slots=1) for pe in c[0].pes))
    # Both legacy groups on PE0 now exceed its capacity. This v0 admission
    # must reject the entire infeasible architecture, never truncate routes.
    with pytest.raises(ValueError):
        ready((arch,*c[1:]))


def test_wrong_target_epoch_rejected_before_storage_mutation():
    c=ready(scenario())
    bad_image=replace(c[6].image,epoch_id='OTHER')
    with pytest.raises(ValueError,match='epoch mismatch'):
        act(change_state(c,replace(c[6],image=bad_image)))


def test_prepared_base_version_cannot_be_modified():
    c=ready(scenario())
    prepared=c[6].prepared[0]
    forged=replace(prepared,transition=replace(prepared.transition,base_version=99))
    with pytest.raises(ValueError,match='stale or mismatched P/S'):
        act(change_state(c,replace(c[6],prepared=(forged,))))


def test_original_state_survives_rejected_atomic_commit():
    c=ready(scenario())
    original=c[6]
    with pytest.raises(ValueError):
        commit_atomic_neuronal_output_v0(*c[:7],commit_request_id=80,emission_request_id=999,ingress=c[7])
    assert c[6]==original


def test_missing_event_tombstone_rejected():
    c=ready(scenario())
    driver=c[6].owned.boundary.driver
    storage=replace(driver.boundary.storage,consumed_ids=())
    new_driver=replace(driver,boundary=replace(driver.boundary,storage=storage))
    owned=replace(c[6].owned,boundary=replace(c[6].owned.boundary,driver=new_driver))
    with pytest.raises(ValueError,match='missing actual EVENT consumption tombstone'):
        act(change_state(c,replace(c[6],owned=owned)))


def test_wrong_routed_candidate_channel_rejected():
    c=ready(scenario())
    routes=tuple(replace(route,occurrence=replace(route.occurrence,source_channel=99))
                 if route.route_request_id==13 else route for route in c[2].routes)
    with pytest.raises(ValueError,match='fan-out'):
        commit_atomic_neuronal_output_v0(c[0],c[1],replace(c[2],routes=routes),
             c[3],c[4],c[5],c[6],commit_request_id=80,emission_request_id=3,ingress=c[7])


def test_output_commit_history_cannot_be_omitted():
    c=ready(scenario())
    result=act(c)
    with pytest.raises(ValueError,match='missing authenticated commit history'):
        audit_committed_internal_history_v0(c[1],replace(result.state,commits=()),c[4],c[5],
               architecture=c[0],manifest=c[2],admission=c[3])


def test_failed_output_binding_does_not_forge_confirmation():
    c=ready(scenario())
    reqs=tuple(replace(r,target_id='outputs:A') if r.request_id==3 else r for r in c[4])
    with pytest.raises(ValueError,match='batch target'):
        commit_atomic_neuronal_output_v0(*c[:4],reqs,c[5],c[6],
                                          commit_request_id=80,emission_request_id=3,ingress=c[7])
    assert 3 not in {x.request_id for x in c[6].owned.boundary.service.confirmed}


def test_immutable_publication_receipt():
    result=act(ready(scenario()))
    with pytest.raises((FrozenInstanceError,AttributeError)):
        result.evidence.commit_request_id=1234


def test_emitting_commit_requires_serialized_graph():
    c=ready(scenario())
    from tests.test_serialized_internal_graph_v0 import fixture
    old=fixture()[2]
    # The unaugmented graph is missing the B4 -> B5 serialization chain.
    with pytest.raises(ValueError,match='serialized causal graph|incomplete'):
        commit_atomic_neuronal_output_v0(*c[:5],old,c[6],
                                          commit_request_id=80,emission_request_id=3,ingress=c[7])
