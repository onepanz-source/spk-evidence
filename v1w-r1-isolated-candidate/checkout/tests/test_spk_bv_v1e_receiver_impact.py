"""BV v1e synthetic doubles only. No frozen A1 kernel available in this environment."""
from __future__ import annotations
from dataclasses import dataclass
import copy, json
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research.native_sensitivity_v1c import sensitivity
from spk_bv_research.native_criterion_v1d import analyze as v1d_analyze
from spk_bv_research.receiver_impact_v1e import (
    SCHEMA,STATUS,RECEIVER_IDS,RECEIVER_TIMESTAMP,RECEIVER_PRIOR_TICK,
    EXCLUSIONS,ingress,analyze,build,
)

PROGRAMS={
 'A':(('SHIFT',1),('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
 'B':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
 'C':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
}

@dataclass(frozen=True)
class Node:
    node_id:str
    initial_raw:int
    instructions:tuple

@dataclass
class MutableNode:
    node_id:str
    initial_raw:int
    instructions:tuple


def nodes(klass=Node):return {n:klass(n,0,p) for n,p in PROGRAMS.items()}


def fake_kernel(node,state,tick,channels):
    assert tick in (10,11,12) and state[1]==tick-1
    a=next(x[1][0] for x in node.instructions if x[0]=='ACC')
    cmp_value=next(x[1] for x in node.instructions if x[0]=='CMP')
    s=next((x[1] for x in node.instructions if x[0]=='SHIFT'),0)
    strength=state[0]+a*channels.count(0)  # synthetic double: SHIFT is not ACC
    guard=strength>=cmp_value
    return strength,guard,(7,) if guard else ()


def reference():
    r=sensitivity(nodes(),fake_kernel,expected_programs=PROGRAMS)
    r={'schema':'spk-bv-native-isolated-operand-sensitivity/v1c',
       'status':'BOUNDED_NATIVE_KERNEL_COUNTERFACTUAL_NO_UTILITY_OR_LEARNING',**r}
    r=json.loads(json.dumps(r,sort_keys=True))
    d=v1d_analyze(nodes(),fake_kernel,r,expected_programs=PROGRAMS)
    return json.loads(json.dumps({'schema':'spk-bv-native-declared-guard-objective/v1d',
        'status':'NATIVE_LOCAL_GUARD_CRITERION_DECLARED_SYNTHETIC_ONLY',**d}))


def shadow_cmp_reference():
    from dataclasses import replace
    from spk_bv_research.native_criterion_v1d import score_pair,EVAL_INDEX,EVAL_TIMESTAMP,EVAL_PREVIOUS_TICK
    d=reference()
    a=nodes()['A']
    candidate=replace(a,instructions=a.instructions[:2]+(('CMP',2),)+a.instructions[3:])
    d['selected_candidate_position']=2
    d['evaluation']=score_pair(fake_kernel,a,candidate,EVAL_INDEX,
        timestamp=EVAL_TIMESTAMP,prior_tick=EVAL_PREVIOUS_TICK)
    return d


def run(k=fake_kernel):return analyze(nodes(),k,reference())


def test_manifest_explicit_uncertainty():
    assert SCHEMA.endswith('/v1e')
    assert 'HYPOTHETICAL' in STATUS
    assert RECEIVER_IDS==('B','C')
    assert RECEIVER_TIMESTAMP==12 and RECEIVER_PRIOR_TICK==11
    assert len(EXCLUSIONS)>=7
    assert any('not-frozen-network-route-attested' in x for x in EXCLUSIONS)


@pytest.mark.parametrize('sender,ing',[([],()),([7],(0,)),((),()),((7,),(0,))])
def test_declared_non_route_translation(sender,ing):
    assert ingress(sender)==ing


@pytest.mark.parametrize('value',[None,7,'7',[1],[7,7],(0,),['7'],[True],{7},(False,)])
def test_bad_or_unknown_sender_emissions_rejected(value):
    with pytest.raises(InterventionError):ingress(value)


def test_actual_shadows_are_local_and_bounded():
    r=run();p=r['receiver_probe'];rows=p['readouts']
    assert p['receiver_pairs']==6 and len(rows)==6
    assert [x['evaluation_domain_index'] for x in rows]==[3,3,4,4,5,5]
    assert [x['receiver_id'] for x in rows]==['B','C']*3
    assert p['different_pairs']==sum(x['classification']=='DIFFERENT' for x in rows)
    assert p['guard_different_pairs']==sum(x['receiver_guard_changed'] for x in rows)
    assert p['emission_different_pairs']==sum(x['receiver_emission_changed'] for x in rows)
    assert r['native_judgments_observed']==0 and r['native_learning_proven'] is False
    assert r['network_event_lineage_attested'] is False and r['native_updates_applied']==0
    assert r['hypothetical_mapping']['network_route_attested'] is False
    assert r['hypothetical_mapping']['native_feedback_packet_attested'] is False
    assert r['native_receiver_kernels_executed'] is True
    assert r['frozen_original_nodes_immutable'] is True
    assert all(len(x['original_receiver_readout']['result_sha256'])==64 for x in rows)


def test_recipient_impact_differs_but_never_judgment():
    r=analyze(nodes(),fake_kernel,shadow_cmp_reference())
    assert r['receiver_probe']['different_pairs']>0
    assert any(x['receiver_guard_changed'] for x in r['receiver_probe']['readouts'])
    assert r['native_judgments_observed']==0


def test_reproducible_independent_doubles():
    assert run()==run()
    assert snapshot(run())==snapshot(run())


def test_input_remains_immutable():
    n=nodes();before=snapshot(n)
    d=reference();pre=snapshot(d)
    analyze(n,fake_kernel,d)
    assert snapshot(n)==before and snapshot(d)==pre


@pytest.mark.parametrize('field,new',[
 ('schema','fake'),('status','invented'),('native_judgments_observed',1),
 ('native_updates_applied',1),('native_learning_proven',True),
 ('selected_candidate_position',4),('selected_candidate_position',-1),
 ('selected_candidate_position',True),
])
def test_invalid_v1d_provenance(field,new):
    v=reference();v[field]=new
    with pytest.raises(InterventionError):analyze(nodes(),fake_kernel,v)


def test_invalid_missing_result_rows():
    v=reference();v['evaluation']['rows'].pop()
    with pytest.raises(InterventionError):analyze(nodes(),fake_kernel,v)


def test_shuffled_evaluation_rows_fails():
    v=reference();v['evaluation']['rows'].reverse()
    with pytest.raises(InterventionError):analyze(nodes(),fake_kernel,v)


def test_changed_domain_input_fails():
    v=reference();v['evaluation']['rows'][0]['channels']=[1]
    with pytest.raises(InterventionError):analyze(nodes(),fake_kernel,v)


def test_spoofed_baseline_fails():
    v=reference();v['evaluation']['rows'][0]['baseline']['result_sha256']='0'*64
    with pytest.raises(InterventionError,match='native A v1d'):analyze(nodes(),fake_kernel,v)


def test_spoofed_candidate_fails():
    v=reference();v['evaluation']['rows'][1]['candidate']['emitted_channels']=[99]
    with pytest.raises(InterventionError,match='native A v1d'):analyze(nodes(),fake_kernel,v)


def test_unknown_neuron_fails():
    n=nodes();del n['C']
    with pytest.raises(InterventionError):analyze(n,fake_kernel,reference())


def test_immutable_native_program_needed():
    n=nodes();n['A']=Node('A',0,(('SHIFT',0),)+n['A'].instructions[1:])
    with pytest.raises(InterventionError,match='native A v1d selected program'):analyze(n,fake_kernel,reference())


def test_invalid_neuron_dataclass_type_fails():
    n=nodes();n['C']='not-node'
    with pytest.raises(InterventionError):analyze(n,fake_kernel,reference())


def test_receiver_kernel_guard_must_be_bool():
    def bad(n,s,t,c):
        r=fake_kernel(n,s,t,c)
        return (r[0],int(r[1]),r[2]) if t==12 else r
    with pytest.raises(InterventionError):run(bad)


def test_receiver_kernel_mutating_node_is_rejected():
    n=nodes(MutableNode)
    def bad(node,state,tick,channels):
        if tick==12:node.initial_raw=99
        return fake_kernel(node,state,tick,channels)
    with pytest.raises(InterventionError,match='mutated'):
        analyze(n,bad,reference())


def test_receiver_kernel_mutating_channels_rejected():
    def bad(n,s,t,c):
        if t==12:c.append(200)
        return fake_kernel(n,s,t,c)
    with pytest.raises(InterventionError,match='mutated'):
        run(bad)


def test_receiver_kernel_nondeterminism_rejected():
    calls=[0]
    def bad(n,s,t,c):
        r=fake_kernel(n,s,t,c)
        if t==12:
            calls[0]+=1
            return (r[0]+calls[0],r[1],r[2])
        return r
    with pytest.raises(InterventionError,match='nondeterministic'):run(bad)


def test_receiver_uses_own_initial_raw():
    n=nodes();n['B']=Node('B',1,n['B'].instructions)
    r=analyze(n,fake_kernel,reference())
    assert r['receiver_probe']['receiver_pairs']==6
    assert r['frozen_original_nodes_immutable']


def test_sender_not_promoted_to_receiver():
    r=run()
    assert all(x['receiver_id']!='A' and x['sender_id']=='A' for x in r['receiver_probe']['readouts'])


def test_unrelated_receiver_guard_change_not_classified_as_benefit():
    r=analyze(nodes(),fake_kernel,shadow_cmp_reference())
    assert r['receiver_probe']['different_pairs']>0
    assert 'utility' not in r and 'benefit' not in r
    assert r['causal_credit_identified'] is False


@dataclass(frozen=True)
class FakeCase:
    nodes:tuple

def fixture():return (FakeCase(tuple(nodes().values())),('fabric',),('plans',))

def admit(case,fabric):return {n.node_id:n for n in case.nodes},{}


def full_report():
    d=reference();d['native_fixture_sha256']=snapshot(fixture())
    d['reference_v1c_file_sha256']='a'*64
    d['reference_v1b1_file_sha256']='b'*64
    d['reference_v0w_file_sha256']='c'*64
    d['frozen_native_sources']={'compute':'fake only'}
    return d


def test_build_accepts_recomputed_v1d_and_binds_sha():
    d=full_report();db=json.dumps(d,sort_keys=True).encode()
    o=build(d,db,copy.deepcopy(d),fixture(),admit,fake_kernel)
    from hashlib import sha256
    assert o['schema']==SCHEMA and o['status']==STATUS
    assert o['reference_v1d_sha256']==sha256(db).hexdigest()
    assert o['reference_v1c_sha256']=='a'*64
    assert o['native_fixture_sha256']==d['native_fixture_sha256']
    assert o['receiver_probe']['receiver_pairs']==6
    assert o['native_judgments_observed']==0


def test_build_rejects_native_source_or_input_drift():
    d=full_report();db=json.dumps(d).encode()
    changed=copy.deepcopy(d);changed['training'][0]['correct_count_delta']=9
    with pytest.raises(InterventionError,match='full v1d'):
        build(d,db,changed,fixture(),admit,fake_kernel)


def test_build_rejects_altered_fixture():
    d=full_report();db=json.dumps(d).encode()
    n=nodes();n['B']=Node('B',1,n['B'].instructions)
    f=(FakeCase(tuple(n.values())),('fabric',),('plans',))
    with pytest.raises(InterventionError,match='fixture hash'):
        build(d,db,d,f,admit,fake_kernel)


def test_raw_observation_fails_on_bad_native_receiver_initial_state():
    n=nodes();n['B']=Node('B',True,n['B'].instructions)
    with pytest.raises(InterventionError,match='receiver initial'):
        analyze(n,fake_kernel,reference())


def test_all_inputs_two_output_copies_even_when_same():
    traces=[]
    def trace(n,s,t,c):
        traces.append((n.node_id,t,tuple(c)))
        return fake_kernel(n,s,t,c)
    r=run(trace)
    assert len([x for x in traces if x[1]==11])==12
    assert len([x for x in traces if x[1]==12])==24
    assert r['receiver_probe']['receiver_pairs']==6
