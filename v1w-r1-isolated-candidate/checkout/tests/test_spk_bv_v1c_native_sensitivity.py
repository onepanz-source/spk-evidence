"""Strict isolated native-kernel sensitivity contract, with explicit test doubles."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import copy
import json
import pytest
from spk_bv_research.off_on_v0t import InterventionError, snapshot
from spk_bv_research.native_sensitivity_v1c import (
    SCHEMA, STATUS, DOMAIN, CANDIDATES, TIMESTAMP, EXCLUSIONS,
    _computed, sensitivity, validate_reference, build,
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

@dataclass(frozen=True)
class Case:
    nodes:tuple


def nodes():return {n:Node(n,0,p) for n,p in PROGRAMS.items()}
def admit(case,fabric):return {n:v for n,v in ((x.node_id,x) for x in case.nodes)},{}
def fixture():return (Case(tuple(nodes().values())),('fabric',),('plans',))


def kernel(node,state,tick,channels):
    assert tick==TIMESTAMP and state[1]==9
    acc=next(ins[1][0] for ins in node.instructions if ins[0]=='ACC')
    threshold=next(ins[1] for ins in node.instructions if ins[0]=='CMP')
    shift=next((ins[1] for ins in node.instructions if ins[0]=='SHIFT'),0)
    strength=state[0]+channels.count(0)*acc+shift
    return strength, strength>=threshold, (7,) if strength>=threshold else ()


def refs():
    w={'schema':'x'};wb=json.dumps(w,sort_keys=True).encode()
    a={}
    b={'schema':'spk-bv-native-readonly-compute-replay/v1b',
       'status':'SOURCE_BOUND_FROZEN_A1_LOCAL_COMPUTATION_OBSERVED_ONLY',
       'verified_forward_batches':6,'native_operator_substitutions':0,
       'native_judgments_observed':0,'native_learning_proven':False,
       'v0w_sha256':sha256(wb).hexdigest(),
       'native_fixture_sha256':snapshot(fixture()),
       'frozen_native_sources':{'frozen_a1_compute_source_sha256':'x'},
       'neuron_instruction_programs':{n:{'instruction_program_sha256':snapshot(p)}
                                      for n,p in PROGRAMS.items()}}
    bb=json.dumps(b,sort_keys=True).encode()
    return b,bb,a,w,wb


def test_native_fixture_program_shapes_are_explicit_and_bounded():
    assert len(CANDIDATES)==5 and len(DOMAIN)==6
    assert set(n for n,_,_ in CANDIDATES)=={'A','B','C'}
    assert all(type(inp) is tuple and all(type(c) is int for c in inp) for _,inp in DOMAIN)
    assert len({(n,i) for n,i,_ in CANDIDATES})==5


def test_local_kernel_pairing_and_no_source_mutation():
    original=nodes(); prior=snapshot(original)
    output=sensitivity(original,kernel,expected_programs=PROGRAMS)
    assert output['probe_pairs']==30
    assert output['candidate_count']==5 and output['input_cases_per_candidate']==6
    assert output['original_nodes_immutable']
    assert snapshot(original)==prior
    assert output['different_pairs']>0
    assert output['different_pairs']+output['same_pairs']+output['rejected_pairs']==30
    assert output==sensitivity(original,kernel,expected_programs=PROGRAMS)


def test_exact_cell_ledger_includes_paired_inputs_and_result_hashes():
    data=sensitivity(nodes(),kernel,expected_programs=PROGRAMS)
    assert len(data['candidates'])==5
    for n,c in enumerate(data['candidates']):
        assert c['instruction_index']==CANDIDATES[n][1]
        assert c['original_program_sha256']==snapshot(PROGRAMS[c['neuron_id']])
        assert c['original_program_sha256']!=c['candidate_program_sha256']
        assert [(x['raw'],x['channels']) for x in c['domain_outcomes']]==[
              (r,list(ch)) for r,ch in DOMAIN]
        assert all(len(x['baseline_result_sha256'])==64 for x in c['domain_outcomes'])


def test_status_never_calls_differential_a_benefit():
    data=sensitivity(nodes(),kernel,expected_programs=PROGRAMS)
    assert all(x['outcome'] in ('SAME','DIFFERENT','REJECTED')
               for c in data['candidates'] for x in c['domain_outcomes'])
    assert 'different-kernel-output-is-not-improved-output' in EXCLUSIONS


def test_constant_kernel_is_a_valid_no_difference_result():
    def const(node,state,tick,channels):return 0,False,()
    result=sensitivity(nodes(),const,expected_programs=PROGRAMS)
    assert result['different_pairs']==0 and result['same_pairs']==30


def test_variant_error_is_counted_not_silently_dropped():
    def rejects(node,state,tick,channels):
        if ('SHIFT',0) in node.instructions:
            raise ValueError('rejected alternative')
        return kernel(node,state,tick,channels)
    result=sensitivity(nodes(),rejects,expected_programs=PROGRAMS)
    assert result['rejected_pairs']==6
    assert result['candidates'][0]['domain_outcomes'][0]['rejection_exception_type']=='ValueError'
    assert result['probe_pairs']==30



def test_candidate_mutation_is_fatal_not_classified_as_rejected():
    def bad(node,state,tick,channels):
        if ('SHIFT',0) in node.instructions:
            state[0]=909
        return 0,False,()
    with pytest.raises(InterventionError,match='mutated isolated'):
        sensitivity(nodes(),bad,expected_programs=PROGRAMS)


def test_baseline_error_is_not_misclassified_as_variant_failure():
    def broken(node,state,tick,channels):raise ValueError('bad baseline')
    with pytest.raises(ValueError,match='bad baseline'):
        sensitivity(nodes(),broken,expected_programs=PROGRAMS)


def test_mutating_state_rejected():
    def bad(node,state,tick,channels):
        state[0]=100
        return 0,False,()
    with pytest.raises(InterventionError,match='mutated isolated'):
        sensitivity(nodes(),bad,expected_programs=PROGRAMS)


def test_mutating_channels_rejected():
    def bad(node,state,tick,channels):
        channels.append(42)
        return 0,False,()
    with pytest.raises(InterventionError,match='mutated isolated'):
        sensitivity(nodes(),bad,expected_programs=PROGRAMS)


def test_mutating_node_rejected():
    mutable={n:MutableNode(n,0,p) for n,p in PROGRAMS.items()}
    def bad(node,state,tick,channels):
        node.initial_raw=999
        return 0,False,()
    with pytest.raises(InterventionError,match='mutated isolated'):
        sensitivity(mutable,bad,expected_programs=PROGRAMS)


def test_nondeterministic_kernel_rejected():
    i=[0]
    def flip(node,state,tick,channels):
        i[0]+=1
        return i[0],True,()
    with pytest.raises(InterventionError,match='nondeterministic'):
        sensitivity(nodes(),flip,expected_programs=PROGRAMS)


@pytest.mark.parametrize('answer',[(True,False,()),(0,False,['7']),(0,False,0),(),(0,False,(),None)])
def test_invalid_kernel_results_rejected(answer):
    with pytest.raises(InterventionError,match='bad native kernel output'):
        _computed(lambda *args:answer,nodes()['A'],0,(0,))


@pytest.mark.parametrize('breakage,match',[
    (lambda ns:ns.pop('B'),'node set drift'),
    (lambda ns:setattr(ns['A'],'_bad','x'),'native admitted program drift'),
])
def test_bad_nodes_detected(breakage,match):
    ns=nodes()
    # frozen dataclass augmented extra attr does not change instructions, so use explicit control
    if match=='native admitted program drift':
        object.__setattr__(ns['A'],'instructions',(('CMP',1),))
    else:breakage(ns)
    with pytest.raises(InterventionError,match=match):
        sensitivity(ns,kernel,expected_programs=PROGRAMS)


def test_non_dataclass_refused():
    class NodeLike:
        def __init__(self,ins):self.instructions=ins
    ns={n:NodeLike(p) for n,p in PROGRAMS.items()}
    with pytest.raises(InterventionError,match='not safely replaceable'):
        sensitivity(ns,kernel,expected_programs=PROGRAMS)


def test_reference_and_build_attestation_no_learning_claims():
    b,bb,a,w,wb=refs()
    anchors=validate_reference(b,bb,a,w,wb)
    assert anchors['expected_programs']==PROGRAMS
    native=fixture(); original=snapshot(native)
    doc=build(b,bb,a,w,wb,b,native,admit,kernel)
    assert doc['schema']==SCHEMA and doc['status']==STATUS
    assert doc['reference_v1b1_sha256']==sha256(bb).hexdigest()
    assert doc['native_judgments_observed']==0 and doc['native_updates_applied']==0
    assert doc['native_utility_identified'] is False and doc['native_learning_proven'] is False
    assert doc['probe_pairs']==30 and snapshot(native)==original


@pytest.mark.parametrize('edit,match',[
  (lambda d:d.update(status='LEARNING'),'wrong v1b'),
  (lambda d:d.update(verified_forward_batches=5),'did not remain observational'),
  (lambda d:d.update(native_operator_substitutions=1),'did not remain observational'),
  (lambda d:d.update(v0w_sha256='z'*64),'file anchor drift'),
  (lambda d:d['neuron_instruction_programs'].pop('C'),'neuron inventory drift'),
  (lambda d:d['neuron_instruction_programs']['A'].update(instruction_program_sha256='x'*64),
   'native neuron program drift'),
])
def test_forged_reference_fails(edit,match):
    b,bb,a,w,wb=refs();edit(b)
    with pytest.raises(InterventionError,match=match):
        validate_reference(b,bb,a,w,wb)


def test_reconstructed_baseline_must_match_entire_attestation():
    b,bb,a,w,wb=refs();bad=copy.deepcopy(b);bad['native_operator_substitutions']=4
    with pytest.raises(InterventionError,match='reconstruction differs'):
        build(b,bb,a,w,wb,bad,fixture(),admit,kernel)


def test_source_fixture_digest_drift_refused():
    b,bb,a,w,wb=refs();nat=fixture()
    b['native_fixture_sha256']='0'*64
    with pytest.raises(InterventionError,match='fixture drift'):
        build(b,bb,a,w,wb,b,nat,admit,kernel)


def test_json_serialization_deterministic_across_calls():
    b,bb,a,w,wb=refs()
    left=build(b,bb,a,w,wb,b,fixture(),admit,kernel)
    right=build(b,bb,a,w,wb,b,fixture(),admit,kernel)
    assert json.dumps(left,sort_keys=True)==json.dumps(right,sort_keys=True)
