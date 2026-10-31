"""S3.7d/3b2b2k/5: enforce commit-before-next-state-read for each neuron."""
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0 as serialize
from tests.test_owned_internal_reads_v0 import context, tick


def fixture():
    c = context()
    consumes = sorted((r for r in c[4] if r.kind is Kind.BATCH_CONSUME), key=lambda r: r.event_time)
    state_loads = sorted((r for r in c[4] if r.kind is Kind.STATE_LOAD), key=lambda r: r.event_time)
    assert len(consumes) == len(state_loads) == 3
    commits = tuple(replace(r, request_id=80+i, kind=Kind.STATE_COMMIT)
                    for i, r in enumerate(state_loads))
    requests = tuple(sorted(c[4]+commits, key=lambda r: r.request_id))
    deps = AccessDependencyGraphV0(tuple(sorted(
        c[5].dependencies + tuple(AccessDependencyV0(r.request_id, ()) for r in commits),
        key=lambda x: x.request_id,
    )))
    return c, requests, deps


def run_with(change=lambda c,r,g: (r,g)):
    c, requests, graph = fixture()
    requests, graph = change(c,requests,graph)
    return serialize(requests,graph)


def pred(graph, rid):
    record = next(x for x in graph.dependencies if x.request_id == rid)
    return (record.predecessor_ids if hasattr(record,'predecessor_ids') else record.predecessors)


def replace_req(requests, rid, **kwargs):
    return tuple(replace(r, **kwargs) if r.request_id == rid else r for r in requests)


def replace_deps(graph, rid, predecessors):
    return AccessDependencyGraphV0(tuple(AccessDependencyV0(x.request_id,
        tuple(sorted(predecessors)) if x.request_id == rid else pred(graph,x.request_id))
        for x in graph.dependencies))


def test_three_neuronal_batches_are_bound():
    result=run_with()
    assert tuple(b.consume_request_id for b in result.batches)==(50,51,52)


def test_state_commit_requires_p_s_and_consumption():
    result=run_with()
    for i, rid in enumerate((80,81,82)):
        assert {50+i,70+2*i,71+2*i} <= set(pred(result.graph,rid))


def test_subsequent_state_load_waits_for_previous_commit():
    result=run_with()
    assert 80 in pred(result.graph,73)
    assert 81 in pred(result.graph,75)


def test_first_state_load_is_not_needlessly_held():
    assert pred(run_with().graph,71)==()


def test_second_program_reference_not_blocked_by_previous_commit():
    result=run_with()
    assert 80 not in pred(result.graph,72)


def test_event_consumption_not_blocked_by_previous_commit():
    result=run_with()
    assert 80 not in pred(result.graph,51)


def test_exact_batch_record_metadata():
    batches=run_with().batches
    assert tuple(x.event_time for x in batches)==(4,5,6)
    assert tuple(x.node_id for x in batches)==('B','B','B')
    assert tuple(x.target_pe_id for x in batches)==('PE1','PE1','PE1')
    assert tuple(x.previous_commit_request_id for x in batches)==(None,80,81)


def test_added_edges_auditable_and_canonical():
    result=run_with()
    assert result.added_edges==tuple(sorted(set(result.added_edges)))
    assert (80,73) in result.added_edges
    assert (81,75) in result.added_edges


def test_does_not_change_original_graph():
    c,requests,graph=fixture()
    copy=tuple(graph.dependencies)
    serialize(requests,graph)
    assert graph.dependencies==copy


def test_preserves_existing_dependencies():
    c,requests,graph=fixture()
    old={x.request_id:set(pred(graph,x.request_id)) for x in graph.dependencies}
    result=serialize(requests,graph)
    assert all(values <= set(pred(result.graph,rid)) for rid,values in old.items())


def test_request_input_reordering_is_deterministic():
    c,requests,graph=fixture()
    assert serialize(requests,graph)==serialize(requests[::-1],graph)


def test_transform_is_idempotent_as_graph():
    c,requests,graph=fixture()
    first=serialize(requests,graph)
    again=serialize(requests,first.graph)
    assert first.graph==again.graph
    assert again.added_edges==()


def test_graph_is_canonical():
    result=run_with()
    ids=tuple(x.request_id for x in result.graph.dependencies)
    assert ids==tuple(sorted(set(ids)))
    assert all(pred(result.graph,rid)==tuple(sorted(set(pred(result.graph,rid)))) for rid in ids)


def test_real_service_does_not_prefetch_future_state_version():
    c,requests,graph=fixture()
    serialized=serialize(requests,graph)
    state=c[6]
    for _ in range(4):
        step=tick((*c[:4], requests, serialized.graph, state, c[7]))
        state=step.state
    ids={x.request_id for x in state.reads}
    assert 71 in ids
    assert 73 not in ids and 75 not in ids


def test_immutable_owner_does_not_commit_state():
    c,requests,graph=fixture()
    state=c[6]
    serialized=serialize(requests,graph)
    for _ in range(4):
        state=tick((*c[:4], requests, serialized.graph, state, c[7])).state
    assert all(n.version==0 for n in state.image.neurons)


def test_two_distinct_neurons_do_not_inherit_causal_edges():
    c,requests,graph=fixture()
    # Isolate last batch on A; retarget all its P/S and consume requests.
    changed=[]
    for r in requests:
        if r.request_id in (52,74,75,82):
            prefix=r.target_id.split(':',1)[0]
            changed.append(replace(r,target_id=f'{prefix}:A',target_pe_id='PE0'))
        else:
            changed.append(r)
    result=serialize(tuple(changed),graph)
    assert 81 not in pred(result.graph,75)
    assert 80 in pred(result.graph,73)


def test_empty_plan_is_valid():
    assert serialize((),AccessDependencyGraphV0(())).batches==()


def test_wrong_requests_type_rejected():
    c,requests,graph=fixture()
    with pytest.raises(TypeError,match='requests'):
        serialize(list(requests),graph)


def test_wrong_graph_type_rejected():
    c,requests,graph=fixture()
    with pytest.raises(TypeError,match='graph'):
        serialize(requests,None)


def test_duplicate_request_id_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError,match='duplicate'):
        serialize(requests+(requests[0],),graph)


def test_missing_graph_entry_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError,match='incomplete'):
        serialize(requests,AccessDependencyGraphV0(graph.dependencies[:-1]))


def test_graph_wrong_order_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError):
        serialize(requests,AccessDependencyGraphV0(graph.dependencies[::-1]))


def test_unknown_predecessor_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError):
        serialize(requests,replace_deps(graph,80,(100000,)))


def test_self_predecessor_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError):
        serialize(requests,replace_deps(graph,80,(80,)))


def test_cyclic_original_graph_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError):
        graph=replace_deps(graph,80,(81,))
        graph=replace_deps(graph,81,(80,))
        serialize(requests,graph)


def test_cycle_introduced_by_version_order_rejected():
    c,requests,graph=fixture()
    # First STATE_LOAD must wait for a commit of a later event: incompatible.
    with pytest.raises(ValueError):
        graph=replace_deps(graph,71,(81,))
        serialize(requests,graph)


def test_missing_state_commit_rejected():
    c,requests,graph=fixture()
    requests=tuple(r for r in requests if r.request_id!=80)
    graph=AccessDependencyGraphV0(tuple(d for d in graph.dependencies if d.request_id!=80))
    with pytest.raises(ValueError,match='missing'):
        serialize(requests,graph)


def test_duplicate_state_commit_for_one_batch_rejected():
    c,requests,graph=fixture()
    extra=replace(next(r for r in requests if r.request_id==80),request_id=99)
    graph=AccessDependencyGraphV0(tuple(sorted(graph.dependencies+(AccessDependencyV0(99,()),),key=lambda x:x.request_id)))
    with pytest.raises(ValueError,match='duplicated'):
        serialize(requests+(extra,),graph)


def test_orphan_state_load_rejected():
    c,requests,graph=fixture()
    extra=replace(next(r for r in requests if r.request_id==75),request_id=99,event_time=100)
    graph=AccessDependencyGraphV0(tuple(sorted(graph.dependencies+(AccessDependencyV0(99,()),),key=lambda x:x.request_id)))
    with pytest.raises(ValueError,match='orphan'):
        serialize(requests+(extra,),graph)


@pytest.mark.parametrize('field,value',[
    ('target_pe_id','PE0'),
    ('quantity',2),
    ('domain',Domain.EVENT),
])
def test_invalid_state_commit_binding_rejected(field,value):
    c,requests,graph=fixture()
    with pytest.raises(ValueError,match='incompatible'):
        serialize(replace_req(requests,80,**{field:value}),graph)


def test_invalid_state_commit_epoch_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError,match='missing or duplicated'):
        serialize(replace_req(requests,80,epoch_id='WRONG'),graph)


def test_duplicate_neuron_event_time_rejected():
    c,requests,graph=fixture()
    bad=replace_req(requests,51,event_time=4)
    with pytest.raises(ValueError,match='multiple batches'):
        serialize(bad,graph)


def test_invalid_batch_quantity_rejected():
    c,requests,graph=fixture()
    with pytest.raises(ValueError):
        serialize(replace_req(requests,50,quantity=0),graph)


def test_read_without_batch_rejected():
    c,requests,graph=fixture()
    requests=tuple(r for r in requests if r.request_id!=50)
    graph=AccessDependencyGraphV0(tuple(d for d in graph.dependencies if d.request_id!=50))
    with pytest.raises(ValueError,match='orphan'):
        serialize(requests,graph)


def test_neuron_pe_migration_without_protocol_rejected():
    c,requests,graph=fixture()
    modified=[]
    for req in requests:
        if req.request_id in (52,74,75,82):
            modified.append(replace(req,target_pe_id='PE0'))
        else:
            modified.append(req)
    with pytest.raises(ValueError,match='cannot migrate'):
        serialize(tuple(modified),graph)


def test_iterative_cycle_check_supports_long_linear_graph():
    from spk_simulator.serialized_internal_graph_v0 import _check_acyclic
    long_chain = {i: () if i == 0 else (i-1,) for i in range(2500)}
    assert _check_acyclic(long_chain) is None
