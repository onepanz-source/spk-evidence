"""Causal feedback closure/convergence/contestion verification, BV research v0g."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter
from dataclasses import replace
import pytest

from search.spk_24n_independent_oracle_v0 import EdgeV0, execute_v0, OracleLimitV0
from spk_backvalidation_v0.n_node_scheduler_v0f import (
    layered_case_v0f, plan_n_v0f, execute_n_v0f, LiveBVPlanV0f, LiveBVRejected,
)
from spk_backvalidation_v0.causal_audit_v0g import (
    audit_closed_v0g, CausalAuditRejected,
)
from tests.test_spk_bv_n_node_scheduler_v0f import plans_for


def make_run(layers=(1,2,1), events=(0,), pe=4, priority='forward-first',
             constrained=False, case=None, channel=7):
    if case is None:
        case,_=layered_case_v0f(layers,events_at=events)
    fabric=plan_n_v0f(case,pe)
    p=plans_for(fabric, link=1 if constrained else 8192,
                pe=2 if constrained else 8192,
                fabric_pe=4 if constrained else 8192,max_ticks=512)
    bv=LiveBVPlanV0f(assessors=(case.nodes[-1].node_id,),
        priority=priority,terminal_channel=channel,max_ticks=512,
        max_packets=4096,max_occurrences=4096,max_batches=8192,max_events=8192)
    run=execute_n_v0f(case,fabric,*p,bv)
    return case,fabric,p,bv,run


def verify_run(*args, **kwargs):
    case,fabric,p,bv,run=make_run(*args,**kwargs)
    audit=audit_closed_v0g(case,fabric,run,*p)
    assert audit['status']=='CAUSAL_CLOSURE_AUDIT_PASS'
    assert audit['neurons']==len(case.nodes)
    return case,fabric,p,bv,run,audit


@pytest.mark.parametrize('layers,pe,constrained,priority', [
    ((1,2,1),1,False,'forward-first'),
    ((1,2,1),4,False,'feedback-first'),
    ((1,2,1),4,True,'forward-first'),
    ((1,2,1),4,True,'feedback-first'),
    ((1,2,2,1),2,True,'forward-first'),
    ((1,2,2,1),2,True,'feedback-first'),
    ((2,3,2),4,True,'forward-first'),
    ((2,3,2),4,True,'feedback-first'),
])
def test_closed_convergent_networks_including_shared_link_contention(layers,pe,constrained,priority):
    case,fabric,p,bv,run,audit=verify_run(layers, (0,2),pe,priority,constrained)
    assert audit['assessments']>=1
    assert audit['feedback_packets']>=1
    assert run['resources']['bv_memory_units']==2*audit['feedback_packets']


def test_diamond_merges_two_independent_paths_but_duplicate_receiver_is_one_vote():
    _,_,_,_,r,a=verify_run()
    assert a['occurrences']==4
    assert a['feedback_packets']==4
    assert a['deliveries']==4
    assert a['unique_receiver_votes']==3
    assert a['duplicate_path_receptions']==1
    assert [x['independent_receiver'] for x in r['feedback']['deliveries']]==[True,True,True,False]


def test_parallel_edges_stay_distinct_with_one_aggregated_receiver_judgment():
    case,_=layered_case_v0f((1,1),events_at=(0,))
    case=replace(case,edges=case.edges+case.edges)
    _,_,_,_,r,a=verify_run(pe=2,case=case)
    assert a['occurrences']==2
    assert a['assessments']==1
    assert a['feedback_packets']==1
    assert a['unique_receiver_votes']==1
    assert len(r['feedback']['deliveries'][0]['evidence_ids'])==2


def test_recurrent_edge_can_be_executed_without_falsely_pretending_perpetual_feedback():
    case,_=layered_case_v0f((1,1,1,1),events_at=(0,))
    nodes=list(case.nodes)
    nodes[0]=replace(nodes[0], instructions=(('ACC',(1,0)),('SHIFT',1),('CMP',1),('EMIT',7),('RESET',0)))
    nodes[-1]=replace(nodes[-1], instructions=(('ACC',(1,0)),('CMP',1),('EMIT',7),('EMIT',8),('RESET',0)))
    case=replace(case,nodes=tuple(nodes),edges=case.edges+(EdgeV0('N3',7,'N0',0,1),))
    _,_,_,_,r,a=verify_run(pe=2,case=case,channel=8)
    oracle=execute_v0(case,max_batches=64,max_events=128)
    assert r['forward']['processed_batches']==oracle['processed_batches']
    assert r['forward']['terminal']==oracle['terminal_outputs']
    assert any(x['source']=='N3' and x['target']=='N0' for x in r['forward']['occurrences'])
    assert a['unique_receiver_votes']==3


def test_sustained_cycle_must_fail_closed_at_batch_budget():
    case,_=layered_case_v0f((1,1,1),events_at=(0,))
    case=replace(case,edges=case.edges+(EdgeV0('N2',7,'N0',0,1),))
    f=plan_n_v0f(case,2)
    with pytest.raises(LiveBVRejected,match='batch/event'):
        execute_n_v0f(case,f,*plans_for(f),LiveBVPlanV0f(enabled=False,max_batches=7,max_ticks=128))
    with pytest.raises(OracleLimitV0):
        execute_v0(case,max_batches=7)


def test_missing_batch_identity_raises_explicit_unverifiable_boundary():
    # Separate ready groups at a shared neuron may execute at one service tick.
    # BV v0f output has no distinct source-batch ID for emitted occurrences.
    case,f,p,bv,r=make_run((1,2,2,1),(0,2),1,constrained=True)
    assert len(r['forward']['terminal'])>0
    assert any(Counter(t for b in r['forward']['batches'] if b['node']==n
                       for t in [b['tick']]).most_common(1)[0][1]>1
               for n in {b['node'] for b in r['forward']['batches']})
    with pytest.raises(CausalAuditRejected,match='batch identity ambiguity'):
        audit_closed_v0g(case,f,r,*p)


# The adversarial tests operate on actual traces returned by the live runtime.
@pytest.fixture
def source_trace():
    case,f,p,bv,r=make_run()
    return case,f,p,r


@pytest.mark.parametrize('mutation,reason', [
    ('wrong_occurrence_target','custody|batch parent|routed occurrence'),
    ('invented_parent','source batch ancestry'),
    ('wrong_route_delay','routed occurrence multiplicity'),
    ('duplicate_consumed_event','batch parent'),
    ('fake_grant_pe','forward link custody'),
    ('duplicate_vote','path multiplicity'),
    ('falsify_receiver','feedback grant/delivery mismatch'),
    ('falsify_evidence','BV evidence'),
    ('forge_feedback_timing','feedback grant/delivery mismatch'),
    ('overcharge_link','link capacity accounting'),
    ('understate_memory','memory'),
    ('forge_assessor','assessment'),
])
def test_adversarial_trace_mutation_is_rejected(source_trace,mutation,reason):
    case,f,p,r=source_trace
    fake=deepcopy(r)
    if mutation=='wrong_occurrence_target':
        fake['forward']['occurrences'][0]['target']='N3'
    elif mutation=='invented_parent':
        fake['forward']['occurrences'][2]['parents']=('fabricated',)
    elif mutation=='wrong_route_delay':
        fake['forward']['occurrences'][0]['delay']=2
    elif mutation=='duplicate_consumed_event':
        fake['forward']['batches'][2]['parents']=[fake['forward']['batches'][2]['parents'][0]]*2
    elif mutation=='fake_grant_pe':
        fake['forward']['link_grants'][0]['target_pe']='PE0'
    elif mutation=='duplicate_vote':
        fake['feedback']['deliveries'][-1]['independent_receiver']=True
    elif mutation=='falsify_receiver':
        fake['feedback']['deliveries'][0]['receiver']='N0'
    elif mutation=='falsify_evidence':
        fake['feedback']['deliveries'][0]['evidence_ids']=['r1']
    elif mutation=='forge_feedback_timing':
        fake['feedback']['deliveries'][0]['tick']-=1
    elif mutation=='overcharge_link':
        fake['resources']['timeline'][0]['link_total']+=1
    elif mutation=='understate_memory':
        fake['resources']['timeline'][0]['memory_total']-=1
    elif mutation=='forge_assessor':
        fake['feedback']['assessments'][0]['observer']='N0'
    with pytest.raises(CausalAuditRejected,match=reason):
        audit_closed_v0g(case,f,fake,*p)


def test_feedback_first_genuinely_delays_forward_under_contention():
    a=verify_run((1,2,1),(0,),4,'forward-first',True)
    b=verify_run((1,2,1),(0,),4,'feedback-first',True)
    at=[e['timestamp'] for e in a[4]['forward']['terminal']]
    bt=[e['timestamp'] for e in b[4]['forward']['terminal']]
    assert at!=bt and bt[-1]>at[-1]
    assert a[5]['feedback_packets'] == b[5]['feedback_packets']


def test_bv_disabled_is_oracle_equal_on_uncongested_convergence():
    case,f,p,bv,r=make_run((1,2,2,1),(0,),3)
    disabled=execute_n_v0f(case,f,*p,replace(bv,enabled=False))
    oracle=execute_v0(case,max_batches=8192,max_events=8192)
    assert disabled['forward']['terminal']==oracle['terminal_outputs']
    assert disabled['forward']['emissions']==oracle['emissions']
    assert disabled['forward']['processed_batches']==oracle['processed_batches']
    assert audit_closed_v0g(case,f,disabled,*p)['feedback_packets']==0


@pytest.mark.parametrize('mutation,reason', [
    ('ready','scheduled ready group'),
    ('input_channel','scheduled neuron inputs'),
    ('external','unconsumed external'),
    ('extra_input','scheduled neuron inputs'),
])
def test_source_event_and_ready_group_forgery_is_rejected(source_trace,mutation,reason):
    case,f,p,r=source_trace
    fake=deepcopy(r)
    if mutation=='ready':
        fake['forward']['batches'][0]['ready']=9
    elif mutation=='input_channel':
        fake['forward']['batches'][0]['channels']=[99]
    elif mutation=='external':
        case=replace(case,events=case.events+(replace(case.events[0],timestamp=100),))
    elif mutation=='extra_input':
        fake['forward']['batches'][0]['channels'].append(0)
    with pytest.raises(CausalAuditRejected,match=reason):
        audit_closed_v0g(case,f,fake,*p)


def test_sealed_evidence_survives_external_replay_and_rejects_rehash_forgery():
    from spk_backvalidation_v0.contract_v0 import canonical,digest,strict_loads
    from search.spk_bv_v0g_causal_stress_evidence import seal,verify
    raw=seal()
    assert verify(raw)['status']=='CAUSAL_STRESS_REPLAY_PASS'
    envelope=strict_loads(raw)
    envelope['payload']['witnesses'][0]['neurons']=999
    envelope['payload_sha256']=digest(envelope['payload'])
    with pytest.raises(CausalAuditRejected,match='replay mismatch'):
        verify(canonical(envelope))


def test_canonical_evidence_rejects_duplicate_json_field():
    from search.spk_bv_v0g_causal_stress_evidence import verify
    from spk_backvalidation_v0.contract_v0 import BVContractRejected
    with pytest.raises(BVContractRejected,match='invalid JSON document'):
        verify('{"payload":{},"payload":{},"payload_sha256":"x"}')
