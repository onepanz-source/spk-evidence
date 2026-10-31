"""BV v1d native-local score: test doubles, no faux claim of SPK native execution."""
from __future__ import annotations
import json
from dataclasses import dataclass
import copy
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research.native_sensitivity_v1c import sensitivity,CANDIDATES,DOMAIN
from spk_bv_research.native_criterion_v1d import (
    SCHEMA, STATUS, OBJECTIVE,TRAIN_INDEX,EVAL_INDEX,EVAL_TIMESTAMP,
    EVAL_PREVIOUS_TICK,target,observe,score_pair,analyze,
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

def nodes():return {n:Node(n,0,p) for n,p in PROGRAMS.items()}

def kernel(node,state,tick,channels):
    assert tick in (10,11) and state[1]==tick-1
    acc=next(x[1][0] for x in node.instructions if x[0]=='ACC')
    cmp=next(x[1] for x in node.instructions if x[0]=='CMP')
    shift=next((x[1] for x in node.instructions if x[0]=='SHIFT'),0)
    strength=state[0]+acc*channels.count(0)+shift
    guard=strength>=cmp
    return strength,guard,(7,) if guard else ()

def refs():
    output=sensitivity(nodes(),kernel,expected_programs=PROGRAMS)
    return json.loads(json.dumps({'schema':'spk-bv-native-isolated-operand-sensitivity/v1c',
       'status':'BOUNDED_NATIVE_KERNEL_COUNTERFACTUAL_NO_UTILITY_OR_LEARNING',**output}))

def analyze_ok(compute=kernel):
    return analyze(nodes(),compute,refs(),expected_programs=PROGRAMS)

def test_fixed_manifest_and_split():
    assert OBJECTIVE.startswith('declared.synthetic.')
    assert len(DOMAIN)==6 and TRAIN_INDEX==(0,1,2) and EVAL_INDEX==(3,4,5)
    assert set(TRAIN_INDEX).isdisjoint(EVAL_INDEX)
    assert EVAL_TIMESTAMP==11 and EVAL_PREVIOUS_TICK==10
    assert target((0,0)) is True
    assert target((0,)) is False
    assert target((0,1)) is False
    assert target((1,1)) is False
    assert target((0,0,1)) is True


def test_real_kernel_double_call_readout():
    a=nodes()['A']; h=snapshot(a)
    out=observe(kernel,a,0,(0,),timestamp=10,prior_tick=9)
    assert out['result_sha256']==snapshot(kernel(a,[0,9],10,[0]))
    assert type(out['guard']) is bool
    assert snapshot(a)==h


def test_train_selected_without_looking_at_eval():
    r=analyze_ok()
    assert r['native_updates_applied']==0 and r['native_judgments_observed']==0
    assert r['native_learning_proven'] is False and r['independent_truth_attested'] is False
    assert len(r['training'])==5
    assert all([x['domain_index'] for x in t['rows']]==[0,1,2] for t in r['training'])
    assert [x['domain_index'] for x in r['evaluation']['rows']]==[3,4,5]
    assert r['evaluation_classification'] in ('IMPROVES_DECLARED_GUARD_OBJECTIVE',
        'DEGRADES_DECLARED_GUARD_OBJECTIVE','TIES_DECLARED_GUARD_OBJECTIVE')
    assert r['selected_candidate_position']==max(range(5),key=lambda i:r['training'][i]['correct_count_delta'])
    assert r==analyze_ok()


def test_winner_and_score_math():
    r=analyze_ok(); idx=r['selected_candidate_position']
    tr=r['training'][idx];ev=r['evaluation']
    assert sum(x['baseline_correct'] for x in ev['rows'])==ev['baseline_correct']
    assert sum(x['candidate_correct'] for x in ev['rows'])==ev['candidate_correct']
    assert ev['correct_count_delta']==ev['candidate_correct']-ev['baseline_correct']
    assert tr['correct_count_delta']==tr['candidate_correct']-tr['baseline_correct']


def test_target_never_uses_kernel_results():
    assert target((0,0)) and not target((0,))
    with pytest.raises(InterventionError):target([0,0])
    with pytest.raises(InterventionError):target((True,0))


@pytest.mark.parametrize('bad',[(1,1),(0,6),(),('1',),(True,)])
def test_invalid_subset_fails(bad):
    a=nodes()['A']
    with pytest.raises(InterventionError):
        score_pair(kernel,a,a,bad,timestamp=10,prior_tick=9)


@pytest.mark.parametrize('tick,prior',[(10,10),(9,10),(11,11)])
def test_bad_temporal_args(tick,prior):
    with pytest.raises(InterventionError):
        observe(kernel,nodes()['A'],0,(0,),timestamp=tick,prior_tick=prior)


def test_kernel_cannot_mutate_arg_state():
    def bad(n,s,t,c):
        s[0]=22;return 0,True,(7,)
    with pytest.raises(InterventionError,match='mutated'):observe(bad,nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_kernel_cannot_mutate_arg_channels():
    def bad(n,s,t,c):
        c.append(3);return 0,True,(7,)
    with pytest.raises(InterventionError,match='mutated'):observe(bad,nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_type_rejects_integer_guard():
    with pytest.raises(InterventionError,match='bad native'):
        observe(lambda n,s,t,c:(0,1,(7,)),nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_type_rejects_float_raw():
    with pytest.raises(InterventionError,match='bad native'):
        observe(lambda n,s,t,c:(0.0,True,(7,)),nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_type_rejects_bad_outputs():
    with pytest.raises(InterventionError,match='bad native'):
        observe(lambda n,s,t,c:(0,True,('7',)),nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_nondeterminism_rejected():
    counter=[0]
    def bad(n,s,t,c):
        counter[0]+=1;return counter[0],True,(7,)
    with pytest.raises(InterventionError,match='nondeterministic'):
        observe(bad,nodes()['A'],0,(0,),timestamp=10,prior_tick=9)


def test_baseline_hash_mismatch_detected():
    ref=refs()['candidates'][0]['domain_outcomes'];ref=copy.deepcopy(ref)
    ref[0]['baseline_result_sha256']='f'*64
    node=nodes()['A']
    from dataclasses import replace
    variant=replace(node,instructions=(('SHIFT',0),)+node.instructions[1:])
    with pytest.raises(InterventionError,match='v1c paired'):
        score_pair(kernel,node,variant,(0,),timestamp=10,prior_tick=9,reference=ref)


def test_candidate_hash_mismatch_detected():
    r=refs();r['candidates'][0]['original_program_sha256']='a'*64
    with pytest.raises(InterventionError,match='v1c candidate'):
        analyze(nodes(),kernel,r,expected_programs=PROGRAMS)


def test_missing_v1c_cells_rejected():
    r=refs();r['probe_pairs']=29
    with pytest.raises(InterventionError,match='not complete'):
        analyze(nodes(),kernel,r,expected_programs=PROGRAMS)


def test_rejected_v1c_cell_refused():
    r=refs();r['rejected_pairs']=1
    with pytest.raises(InterventionError,match='not complete'):
        analyze(nodes(),kernel,r,expected_programs=PROGRAMS)


def test_unknown_v1c_schema_rejected():
    r=refs();r['schema']='tampered'
    with pytest.raises(InterventionError,match='wrong native'):
        analyze(nodes(),kernel,r,expected_programs=PROGRAMS)


def test_mutated_original_node_detected():
    values={n:MutableNode(n,0,p) for n,p in PROGRAMS.items()}
    def bad(node,state,tick,channels):
        node.initial_raw+=1
        return 0,True,(7,)
    with pytest.raises(InterventionError,match='mutated'):
        analyze(values,bad,refs(),expected_programs=PROGRAMS)


def test_corrupt_native_candidate_reference_rejected():
    r=refs();r['candidates'][0]['domain_outcomes'][0]['counterfactual_result_sha256']='0'*64
    with pytest.raises(InterventionError,match='v1c paired'):
        analyze(nodes(),kernel,r,expected_programs=PROGRAMS)


def test_native_derived_readouts_not_synthetic_truth():
    r=analyze_ok()
    assert 'independent-oracle' in r['criterion']['criterion_origin']
    assert 'synthetic' in r['criterion']['objective_id']
    assert r['evaluation_classification'].endswith('_DECLARED_GUARD_OBJECTIVE')


def test_selected_no_update_even_if_positive():
    r=analyze_ok()
    assert r['native_updates_applied']==0 and r['native_learning_proven'] is False


def test_split_input_hash_pinned_deterministic():
    a=analyze_ok()['criterion']['immutable_predeclared_design_sha256']
    assert len(a)==64 and a==analyze_ok()['criterion']['immutable_predeclared_design_sha256']


def test_actual_access_schedule_train_before_evaluation():
    touched=[]
    def tracer(n,state,tick,channels):
        touched.append(tick)
        return kernel(n,state,tick,channels)
    result=analyze_ok(tracer)
    assert touched[:60]==[10]*60
    assert touched[60:]==[11]*12
    assert len(touched)==72

@dataclass(frozen=True)
class FakeCase:
    nodes:tuple

def fake_fixture():
    return FakeCase(tuple(nodes().values())), ('fabric',), ('plans',)

def fake_admit(case,fabric):
    return {n.node_id:n for n in case.nodes},{}


def fake_full_references():
    from hashlib import sha256
    from spk_bv_research.native_sensitivity_v1c import build as v1c_build
    fixture=fake_fixture(); wb=json.dumps({'schema':'fake'},sort_keys=True).encode()
    v1b1={'schema':'spk-bv-native-readonly-compute-replay/v1b',
        'status':'SOURCE_BOUND_FROZEN_A1_LOCAL_COMPUTATION_OBSERVED_ONLY',
        'verified_forward_batches':6,'native_operator_substitutions':0,
        'native_judgments_observed':0,'native_learning_proven':False,
        'v0w_sha256':sha256(wb).hexdigest(),
        'native_fixture_sha256':snapshot(fixture),
        'frozen_native_sources':{'frozen_a1_compute_source_sha256':'test-fixture-only'},
        'neuron_instruction_programs':{n:{'instruction_program_sha256':snapshot(p)}
                                       for n,p in PROGRAMS.items()}}
    v1b1bytes=json.dumps(v1b1,sort_keys=True).encode()
    v1c=v1c_build(v1b1,v1b1bytes,{},json.loads(wb),wb,
                  v1b1,fixture,fake_admit,kernel)
    v1c=json.loads(json.dumps(v1c,sort_keys=True))
    v1cbytes=json.dumps(v1c,sort_keys=True).encode()
    return v1c,v1cbytes,v1b1,v1b1bytes,{},json.loads(wb),wb,fixture


def test_complete_build_with_json_roundtrip_nested_native_acc_operand():
    from spk_bv_research.native_criterion_v1d import build
    v1c,cb,b,bb,a,w,wb,fixture=fake_full_references()
    report=build(v1c,cb,b,bb,a,w,wb,b,fixture,fake_admit,kernel)
    assert report['schema']==SCHEMA and report['status']==STATUS
    assert report['recomputed_v1c_probe_pairs']==30
    assert report['selected_candidate_position'] in range(5)
    assert report['native_updates_applied']==0
    assert report['native_fixture_sha256']==snapshot(fixture)


def test_complete_build_refuses_modified_v1c_report():
    from spk_bv_research.native_criterion_v1d import build
    v1c,cb,b,bb,a,w,wb,fixture=fake_full_references()
    v1c['candidates'][2]['different']+=1
    with pytest.raises(InterventionError,match='full native v1c recomputation'):
        build(v1c,cb,b,bb,a,w,wb,b,fixture,fake_admit,kernel)
