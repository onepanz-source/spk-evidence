"""BV v0f N-node live scheduler: oracle differential, custody and adversarial boundaries."""
from dataclasses import replace
from random import Random
import pytest

from search.spk_24n_independent_oracle_v0 import (
    CaseV0, NodeV0, EdgeV0, EventV0, execute_v0, OracleLimitV0)
from spk_architecture_v1.pe_fabric_v1a import FabricV1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_backvalidation_v0.n_node_scheduler_v0f import (
    LiveBVRejected, LiveBVPlanV0f, plan_n_v0f, layered_case_v0f,
    execute_n_v0f)

RELAY=(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0))

def plans_for(f, *, link=8192, max_outbox=8192, pe=8192,
              fabric_pe=8192, mem=131072, max_ticks=4096):
    return (TransportPlanV1a(0,16384),
            uniform_causal_service_plan_v1b(f,pe_slots=pe,
                                            fabric_slots_per_tick=fabric_pe,
                                            max_service_span_ticks=max_ticks),
            uniform_causal_memory_plan_v1c(f,pe_slots=mem,
                domain_slots=mem,fabric_slots_per_tick=mem,
                max_service_span_ticks=max_ticks),
            CausalLinkPlanV1d(link_slots_per_tick=link,
                fabric_slots_per_tick=link,max_outbox_per_pe=max_outbox,
                max_link_span_ticks=max_ticks))

@pytest.mark.parametrize('layers',[
    (1,), (1,1), (1,1,1,1), (2,3), (4,4,4), (1,2,3,4),
    (8,8,8), (16,16), (32,), (16,16,16,16),
])
@pytest.mark.parametrize('pe_category',['single','two','spread'])
def test_bv_disabled_n_nodes_match_independent_oracle_with_uncongested_budget(layers,pe_category):
    case,_=layered_case_v0f(layers,events_at=(0,))
    n=len(case.nodes)
    f=plan_n_v0f(case,{'single':1,'two':2,'spread':n}[pe_category])
    r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(enabled=False,
              max_batches=8192,max_events=16384,max_occurrences=16384,max_ticks=4096))
    oracle=execute_v0(case,max_batches=8192,max_events=16384)
    assert r['forward']['emissions']==oracle['emissions']
    assert r['forward']['terminal']==oracle['terminal_outputs']
    assert r['forward']['processed_batches']==oracle['processed_batches']
    assert r['forward']['processed_events']==oracle['processed_events']
    assert r['forward']['states']=={x['node_id']:x['raw'] for x in oracle['states']}
    assert r['resources']['bv_link_grants']==0
    assert r['resources']['bv_local_sends']==0


def test_parameterized_layers_generate_stable_topology_independent_of_pe_mapping():
    case,layers=layered_case_v0f((2,3,4))
    assert len(case.nodes)==9
    assert len(case.edges)==2*3+3*4
    assert len(layers)==3
    a=plan_n_v0f(case,1)
    b=plan_n_v0f(case,4)
    assert [tuple(vars(e).items())[:5] for e in a.static_routes]==[tuple(vars(e).items())[:5] for e in b.static_routes]
    assert a.profile()['cross_pe_edges']==0
    assert b.profile()['cross_pe_edges']>0


def test_n_node_live_feedback_through_mixed_local_and_remote_pe():
    case,_=layered_case_v0f((1,1,1,1))
    f=plan_n_v0f(case,2,mapping={'N0':'PE0','N1':'PE0','N2':'PE1','N3':'PE1'})
    r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(assessors=('N3',)))
    assert r['population']['neurons']==4
    assert r['resources']['bv_link_grants']==1
    assert r['resources']['bv_local_sends']==2
    assert len(r['feedback']['deliveries'])==3
    assert [(g['sender'],g['receiver']) for g in r['feedback']['link_grants']]==[
        ('N3','N2'),('N2','N1'),('N1','N0')]
    assert r['feedback']['unique_receiver_votes']==3


def test_local_bv_requires_service_memory_but_no_link():
    case,_=layered_case_v0f((1,1,1,1))
    f=plan_n_v0f(case,1)
    r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(assessors=('N3',)))
    assert r['resources']['bv_link_grants']==0
    assert r['resources']['bv_local_sends']==3
    assert r['resources']['bv_service_units']==3
    assert r['resources']['bv_memory_units']==6
    assert r['resources']['peak_cross_inflight']==0
    assert all(not g['cross_pe'] for g in r['feedback']['link_grants'])


def test_feedback_first_changes_live_forward_timing_under_link_contention():
    case,_=layered_case_v0f((1,1,1,1),events_at=(1,3))
    f=plan_n_v0f(case,2)
    pp=plans_for(f,link=1,pe=2,fabric_pe=4)
    fw=execute_n_v0f(case,f,*pp,LiveBVPlanV0f(assessors=('N3',),priority='forward-first'))
    bv=execute_n_v0f(case,f,*pp,LiveBVPlanV0f(assessors=('N3',),priority='feedback-first'))
    assert [x['timestamp'] for x in fw['forward']['terminal']]==[5,7]
    assert [x['timestamp'] for x in bv['forward']['terminal']]==[5,10]
    assert len(fw['feedback']['deliveries'])==6
    assert len(bv['feedback']['deliveries'])==6
    for run in (fw,bv):
        assert all(row['link_total']<=1 for row in run['resources']['timeline'])
        assert all(row['pe_service_total']<=4 for row in run['resources']['timeline'])


def test_parallel_routes_preserve_parent_occurrences_but_not_multiple_votes():
    case,_=layered_case_v0f((1,1))
    case=replace(case,edges=case.edges+case.edges)
    f=plan_n_v0f(case,2)
    r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(assessors=('N1',)))
    assert len(r['forward']['occurrences'])==2
    assert len(r['feedback']['assessments'])==1
    assert len(r['feedback']['link_grants'])==1
    assert r['feedback']['unique_receiver_votes']==1
    assert len(r['feedback']['link_grants'][0]['packet_id'])>0
    assert len(r['feedback']['deliveries'][0]['evidence_ids'])==2


def test_recurrent_graph_can_terminate_and_backward_ancestry_is_finite():
    case,_=layered_case_v0f((1,1,1,1))
    nodes=list(case.nodes)
    # The last neuron emits both a routed 7 (quiet feedback channel 1)
    # and a terminal 8 (the assessment); channel 1 is not read by N0.
    nodes[-1]=replace(nodes[-1],instructions=(('ACC',(1,0)),('CMP',1),
                                           ('EMIT',7),('EMIT',8),('RESET',0)))
    case=replace(case,nodes=tuple(nodes),edges=case.edges+(EdgeV0('N3',7,'N0',1,1),))
    f=plan_n_v0f(case,2)
    r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(
        assessors=('N3',),terminal_channel=8))
    oracle=execute_v0(case)
    assert r['forward']['terminal']==oracle['terminal_outputs']
    assert r['forward']['processed_batches']==oracle['processed_batches']
    assert len(r['feedback']['deliveries'])==3
    assert len(r['forward']['occurrences'])==4


def test_persistent_cycle_rejected_by_finite_batch_quota():
    case,_=layered_case_v0f((1,1,1))
    case=replace(case,edges=case.edges+(EdgeV0('N2',7,'N0',0,1),))
    f=plan_n_v0f(case,2)
    with pytest.raises(LiveBVRejected,match='batch/event'):
        execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(enabled=False,
                max_batches=5,max_ticks=128))
    with pytest.raises(OracleLimitV0):
        execute_v0(case,max_batches=5)


def test_explicit_mapping_and_route_custody_reject_forgery():
    case,_=layered_case_v0f((1,1,1,1))
    with pytest.raises(LiveBVRejected,match='mapping'):
        plan_n_v0f(case,2,mapping={'N0':'PE0'})
    with pytest.raises(LiveBVRejected,match='mapping'):
        plan_n_v0f(case,2,mapping={n.node_id:'PE8' for n in case.nodes})
    f=plan_n_v0f(case,2)
    bad_edge=replace(f.static_routes[0],target_pe='PE0' if f.static_routes[0].target_pe=='PE1' else 'PE1')
    bad=replace(f,static_routes=(bad_edge,)+f.static_routes[1:])
    with pytest.raises(LiveBVRejected,match='forged static route'):
        execute_n_v0f(case,bad,*plans_for(bad),LiveBVPlanV0f(enabled=False))


@pytest.mark.parametrize('invalid',[(0,),(-1,2),(),(1,True),('4',), (1025,)])
def test_bad_layer_population_is_rejected(invalid):
    with pytest.raises(LiveBVRejected):
        layered_case_v0f(invalid)


@pytest.mark.parametrize('field,value',[
    ('assessors',('missing',)),('assessors',('N1','N1')),
    ('assessors',('N1',True)),('priority','random'),('max_packets',True),
    ('hop_latency',0),('max_hops',0),('terminal_channel',-1),
])
def test_bad_feedback_plan_denied(field,value):
    case,_=layered_case_v0f((1,1))
    f=plan_n_v0f(case,2)
    with pytest.raises(LiveBVRejected):
        execute_n_v0f(case,f,*plans_for(f),replace(LiveBVPlanV0f(),**{field:value}))


@pytest.mark.parametrize('field,value,match',[
    ('max_packets',1,'max_packets'), ('max_hops',1,'max_hops'),
    ('max_ticks',2,'horizon'), ('max_occurrences',1,'occurrence'),
])
def test_bounds_fail_explicitly(field,value,match):
    case,_=layered_case_v0f((1,1,1,1))
    f=plan_n_v0f(case,4)
    with pytest.raises(LiveBVRejected,match=match):
        execute_n_v0f(case,f,*plans_for(f),replace(LiveBVPlanV0f(assessors=('N3',)),**{field:value}))


def test_admission_bounds_not_claimed_universal():
    case,_=layered_case_v0f((1,1,1,1))
    with pytest.raises(LiveBVRejected,match='bound'):
        plan_n_v0f(case,2,max_nodes=3)
    with pytest.raises(LiveBVRejected,match='bound'):
        plan_n_v0f(case,2,max_edges=2)
    with pytest.raises(LiveBVRejected):
        plan_n_v0f(case,True)


def test_collision_of_parallel_source_edges_is_not_silently_normalized():
    case,_=layered_case_v0f((1,1))
    case=replace(case,edges=case.edges+case.edges)
    f=plan_n_v0f(case,2)
    altered=replace(f,static_routes=f.static_routes[:-1])
    with pytest.raises(LiveBVRejected,match='multiplicity'):
        execute_n_v0f(case,altered,*plans_for(altered),LiveBVPlanV0f(enabled=False))


def test_old_three_neuron_v0e_projection_still_matches_v0f():
    from search.spk_bv_v0e_live_evidence import fixture
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    case,f,plans=fixture()
    nf=plan_n_v0f(case,len(f.pe_ids),mapping={n.node_id:f.owner(n.node_id) for n in case.nodes})
    old=execute_live_v0e(case,f,*plans,LiveBVPlanV0e(priority='feedback-first'))
    new=execute_n_v0f(case,nf,*plans,LiveBVPlanV0f(priority='feedback-first',assessors=('C',)))
    assert old['forward']['terminal']==new['forward']['terminal']
    assert old['forward']['emissions']==new['forward']['emissions']
    assert [(x['tick'],x['source']) for x in old['forward']['link_grants']]==[
        (x['tick'],x['source']) for x in new['forward']['link_grants']]
    assert [(x['tick'],x['sender'],x['receiver']) for x in old['feedback']['link_grants']]==[
        (x['tick'],x['sender'],x['receiver']) for x in new['feedback']['link_grants']]


def test_deterministic_seeded_graph_differential():
    # No precomputed expected outputs: frozen-independent oracle computes each.
    for seed in range(25):
        rnd=Random(seed)
        size=4+seed%9
        nodes=tuple(NodeV0(f'U{i}',16,0,0,RELAY) for i in range(size))
        edges=tuple(EdgeV0(f'U{i}',7,f'U{j}',0,1+rnd.randrange(3))
                    for i in range(size) for j in range(i+1,size)
                    if rnd.random()<0.22)
        events=tuple(EventV0(rnd.randrange(4),f'U{rnd.randrange(min(3,size))}',0)
                     for _ in range(1+seed%4))
        case=CaseV0(nodes,edges,events)
        expected=execute_v0(case,max_batches=1024,max_events=4096)
        f=plan_n_v0f(case,1+seed%4)
        r=execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(enabled=False,
                            max_batches=1024,max_events=4096,max_ticks=1024))
        assert r['forward']['terminal']==expected['terminal_outputs'],seed
        assert r['forward']['emissions']==expected['emissions'],seed
        assert r['forward']['states']=={x['node_id']:x['raw'] for x in expected['states']},seed


def test_independent_source_backed_replay():
    from search.spk_bv_v0f_n_node_evidence import seal,verify
    raw=seal()
    report=verify(raw)
    assert report['status']=='N_NODE_LIVE_BV_REPLAY_PASS'
    assert report['witnesses']==8
    assert report['max_neurons']==64
    assert report['forward_first_terminal']==[5,7]
    assert report['feedback_first_terminal']==[5,10]


def test_even_fully_rehashed_forgery_does_not_pass_replay():
    from spk_backvalidation_v0.contract_v0 import canonical,digest,strict_loads
    from search.spk_bv_v0f_n_node_evidence import seal,verify
    env=strict_loads(seal())
    env['payload']['witnesses'][0]['forward_emissions']+=1
    env['payload_sha256']=digest(env['payload'])
    with pytest.raises(LiveBVRejected,match='replay'):
        verify(canonical(env))


def test_noncanonical_envelope_cannot_pass():
    from search.spk_bv_v0f_n_node_evidence import seal,verify
    with pytest.raises((ValueError,LiveBVRejected)):
        verify(seal()+'\n')
