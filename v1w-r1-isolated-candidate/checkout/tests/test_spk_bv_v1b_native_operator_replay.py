"""BV v1b: deterministic native batch microtrace alignment, no operator updates."""
from __future__ import annotations
import copy
from dataclasses import dataclass
import json
from pathlib import Path
import pytest

from spk_bv_research.off_on_v0t import InterventionError, snapshot, summarize
from spk_bv_research.native_operator_replay_v1b import (
    SCHEMA, STATUS, EXCLUSIONS, check_reference, replay, shape, valid_native_source,
)
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output

REAL=Path('/mnt/data')

@dataclass(frozen=True)
class Instr:
    kind: str
    operand: int

@dataclass(frozen=True)
class Neuron:
    initial_raw: int
    instructions: tuple

@dataclass(frozen=True)
class Case:
    events: tuple


def fixture():
    return (Case(('x',)),('fabric',), (1,2,3,4))


def admit(case, fabric):
    return ({'A':Neuron(0,(Instr('sum',1),)),
             'B':Neuron(0,(Instr('sum',1),Instr('emit',2))),
             'C':Neuron(0,(Instr('nop',0),))}, {'A':'P','B':'Q','C':'R'})


def compute(node, state, tick, channels):
    return state[0]+len(channels), len(node.instructions), tuple(ch+1 for ch in channels)


def off_result():
    return {'schema':'spk-bv-live-dual-event-scheduler/v0e','enabled':False,
        'policy':'forward-first',
        'forward':{'states':{'A':1,'B':2,'C':0},
          'batches':[{'tick':1,'node':'A','channels':[0], 'raw':1, 'outputs':[1]},
                     {'tick':2,'node':'B','channels':[1,1], 'raw':2,'outputs':[2,2]}],
          'emissions':[{'timestamp':1,'node_id':'A','channel':1},
                      {'timestamp':2,'node_id':'B','channel':2},
                      {'timestamp':2,'node_id':'B','channel':2}],
          'terminal':[{'timestamp':2,'node_id':'B','channel':2}],
          'processed_events':3,'processed_batches':2,
          'link_grants':[],'occurrences':[]},
        'feedback':{'assessments':[],'link_grants':[],'deliveries':[],
                    'unique_receiver_votes':0},
        'resources':{'timeline':[{'tick':1,'pe_service_total':1,
                      'memory_total':0,'link_total':0,'feedback_sends':0}],
                     'peak_cross_inflight':0,
                     'forward_link_grants':0,'bv_link_grants':0,
                     'bv_service_units':0,'bv_memory_units':0,
                     'forward_reserved_memory_units':0,'contention':{}}}


def run(inject=None,mutate_result=None):
    native=fixture(); off=off_result()
    if mutate_result:mutate_result(off)
    expected=summarize(off,enabled=False,priority='forward-first')
    fn=inject if inject is not None else compute
    return replay(native,admit,fn,off,expected,expected_fixture_sha256=snapshot(native))


def test_readonly_replay_matches_every_forward_batch():
    result=run()
    assert result['verified_forward_batches']==2
    assert result['native_off_result_sha256']==summarize(off_result(),enabled=False,priority='forward-first')['whole_result_sha256']
    assert [a['neuron_id'] for a in result['readonly_microtrace']]==['A','B']
    assert [a['poststate_raw'] for a in result['readonly_microtrace']]==[1,2]
    assert result['neuron_instruction_programs']['A']['instruction_count']==1
    assert result['neuron_instruction_programs']['C']['instruction_count']==1
    assert result['neuron_instruction_programs']['B']['instruction_shapes'][0]['operator_discriminants']=={'kind':'sum'}
    assert run()==result


def test_original_fixture_remains_untouched():
    nat=fixture();orig=snapshot(nat)
    off=off_result();expected=summarize(off,enabled=False,priority='forward-first')
    replay(nat,admit,compute,off,expected,expected_fixture_sha256=orig)
    assert snapshot(nat)==orig


@pytest.mark.parametrize('edit,match',[ 
    (lambda x:x['forward']['batches'][0].update(raw=19),'native kernel result'),
    (lambda x:x['forward']['batches'][0].update(outputs=[3]),'native kernel result'),
    (lambda x:x['forward']['batches'][0].update(node='NOBODY'),'unknown node'),
    (lambda x:x['forward']['batches'][0].update(channels=[True]),'invalid channels'),
    (lambda x:x['forward']['batches'][0].update(tick=-1),'backdated replay'),
    (lambda x:x['forward']['batches'][0].update(channels='x'),'invalid forward batch'),
    (lambda x:x['forward']['states'].update(B=0),'micro-replay terminal states'),
    (lambda x:x.update(enabled=True),'not an OFF'),
    (lambda x:x.update(policy='feedback-first'),'not an OFF'),
])
def test_bad_batch_refused(edit,match):
    off=off_result(); edit(off)
    # Rebind the whole-result reference for this synthetic adversarial case.
    # In the real CLI, the earlier frozen SHA check catches such edits first.
    if off.get('enabled') is False and off.get('policy')=='forward-first':
        expected=summarize(off,enabled=False,priority='forward-first')
    else:
        clean=off_result();expected=summarize(clean,enabled=False,priority='forward-first')
    with pytest.raises(InterventionError,match=match):
        replay(fixture(),admit,compute,off,expected,expected_fixture_sha256=snapshot(fixture()))


def test_frozen_fixture_digest_must_match():
    with pytest.raises(InterventionError,match='native fixture differs'):
        replay(fixture(),admit,compute,off_result(),summarize(off_result(),enabled=False,priority='forward-first'),
               expected_fixture_sha256='1'*64)


def test_off_anchor_must_match_exact():
    expected=summarize(off_result(),enabled=False,priority='forward-first')
    expected['whole_result_sha256']='0'*64
    with pytest.raises(InterventionError,match='native OFF reference mismatch'):
        replay(fixture(),admit,compute,off_result(),expected,
               expected_fixture_sha256=snapshot(fixture()))


def test_mutating_kernel_rejected():
    def bad(node,state,tick,channels):
        state[:]=[22,22]
        return compute(node,state,tick,channels)
    with pytest.raises(InterventionError,match='mutated its input argument'): run(bad)


def test_nondeterminism_rejected():
    counter=[0]
    def bad(node,state,tick,channels):
        counter[0]+=1
        return counter[0],0,[1]
    with pytest.raises(InterventionError,match='not deterministic'):
        run(bad)


def test_mutating_input_channels_rejected():
    def bad(node,state,tick,channels):
        result=compute(node,state,tick,channels)
        channels.append(99)
        return result
    with pytest.raises(InterventionError,match='mutated its input argument'):run(bad)

def test_wrong_state_type_rejected():
    def bad(node,state,tick,channels):return True,0,tuple(ch+1 for ch in channels)
    with pytest.raises(InterventionError,match='bad types'):
        run(bad)


def test_native_literal_string_instructions_are_supported_without_pretending_dataclass():
    node=Neuron(0,('load:0','add:1','emit:7'))
    result=shape(node)
    assert result['instruction_count']==3
    assert result['instruction_shapes'][0]['representation']=='str'
    assert result['instruction_shapes'][0]['operator_discriminants']=={'literal_token':'load:0'}
    assert result['canonical_instruction_program']['items']==['load:0','add:1','emit:7']
    assert result['instruction_program_sha256']==snapshot(node.instructions)


def test_native_tuple_instructions_have_lossless_operand_shapes():
    node=Neuron(0,(('load',0),('add',3),('emit',7)))
    result=shape(node)
    assert result['instruction_count']==3
    assert result['instruction_shapes'][1]['representation']=='tuple'
    assert result['instruction_shapes'][1]['operator_discriminants']=={'head_token':'add'}
    assert result['canonical_instruction_program']['items'][1]=={'$t':'tuple','items':['add',3]}
    assert result==shape(node)


def test_native_dict_instructions_are_only_syntactically_described():
    node=Neuron(0,({'op':'sum','operand':3},))
    result=shape(node)
    assert result['instruction_shapes'][0]['operator_discriminants']=={'op':'sum'}
    assert result['instruction_shapes'][0]['fields']==['op','operand']


def test_mixed_native_instruction_shapes_are_exact_and_bounded():
    node=Neuron(0,('load',Instr('sum',2),('emit',7)))
    result=shape(node)
    assert [r['representation'] for r in result['instruction_shapes']]==['str','dataclass','tuple']
    assert result['instruction_program_sha256']==snapshot(node.instructions)
    assert result['canonical_instruction_program']['items'][1]['$t']=='dataclass'


@pytest.mark.parametrize('instructions,match',[
    ([], 'no bounded instruction'),
    (tuple(), 'no bounded instruction'),
    ((object(),), 'unsupported native object type'),
    (('x',)*129, 'no bounded instruction'),
])
def test_invalid_instruction_rejected(instructions,match):
    with pytest.raises((InterventionError, ValueError),match=match):
        shape(type('Bad',(),{'instructions':instructions})())


@pytest.mark.parametrize('value,kind',[
    (42,'int'),(True,'bool'),(None,'NoneType'),
    ((1,2),'tuple'),(['an','instruction'],'list'),
])
def test_native_codec_supported_types_are_observed_not_semantically_rejected(value,kind):
    result=shape(Neuron(0,(value,)))
    assert result['instruction_count']==1
    assert result['instruction_shapes'][0]['representation']==kind
    assert result['instruction_program_sha256']==snapshot((value,))


def test_invalid_nested_unsupported_object_is_rejected_by_native_codec():
    with pytest.raises(ValueError,match='unsupported native object type'):
        shape(Neuron(0,((1,object()),)))


def test_literal_native_program_replay_preserves_all_existing_controls():
    native=fixture(); off=off_result()
    def literal_admit(case,fabric):
        nodes,owners=admit(case,fabric)
        # The native kernel uses length only in this test double. Never claim
        # real A1 operational equivalence to this synthetic representation.
        return {name:Neuron(neuron.initial_raw,tuple('op:'+str(i) for i in range(len(neuron.instructions))))
                for name,neuron in nodes.items()},owners
    out=replay(native,literal_admit,compute,off,
               summarize(off,enabled=False,priority='forward-first'),
               expected_fixture_sha256=snapshot(native))
    assert out['verified_forward_batches']==2
    assert out['neuron_instruction_programs']['A']['instruction_shapes'][0]['representation']=='str'


def test_function_custody_refuses_test_stub(tmp_path):
    (tmp_path/'spk_architecture_v1').mkdir()
    (tmp_path/'spk_architecture_v1'/'pe_execution_v1b.py').write_text('def _compute_local():pass')
    with pytest.raises(InterventionError,match='not bound'):
        valid_native_source(tmp_path,compute,'_compute_local')


def test_output_custody(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    x=tmp_path/'x.json';x.write_text('{}')
    assert safe_output(tmp_path/'new.json',root,[x])==tmp_path/'new.json'
    with pytest.raises(InterventionError,match='existing output'):
        safe_output(x,root,[])
    with pytest.raises(InterventionError,match='unsafe or existing output'):
        safe_output(root/'report.json',root,[])
    link=tmp_path/'link';link.symlink_to(x)
    with pytest.raises(InterventionError,match='symlinked input|unsafe or missing input'):
        safe_input(link,root)


def test_input_alias_and_repository_custody(tmp_path):
    root=tmp_path/'root';root.mkdir()
    (root/'notreference.json').write_text('{}')
    with pytest.raises(InterventionError,match='input in repository'):
        safe_input(root/'notreference.json',root)
    (tmp_path/'outside.json').write_text('{}')
    b,key=safe_input(tmp_path/'outside.json',root)
    assert b==b'{}' and len(key)==2


def test_real_v1a_and_v0w_reference_chain():
    p=REAL/'spk-bv-v1a-symbolic-holdout.json'
    w=REAL/'spk-bv-v0w-native-13.json'
    if not p.is_file() or not w.is_file():pytest.skip('optional native user captures not mounted')
    actual=check_reference(json.loads(p.read_bytes()),json.loads(w.read_bytes()),w.read_bytes())
    assert actual['whole_result_sha256'].startswith('4f090e')


@pytest.mark.parametrize('corrupt,match',[
    (lambda a,w:a.update(status='LEARNED'),'v1a wrong'),
    (lambda a,w:w.update(status='LEARNED'),'v0w wrong'),
    (lambda a,w:a.update(v0w_file_sha256='0'*64),'anchor drift'),
    (lambda a,w:a.update(native_operator_updates_applied=1),'misclaims'),
    (lambda a,w:a.update(observed_native_learning_benefit=True),'misclaims'),
    (lambda a,w:a.update(source_kind='real native'),'toy/native'),
    (lambda a,w:a.update(synthetic_demos=[]),'synthetic'),
    (lambda a,w:w.update(cells=[]),'baseline'),
    (lambda a,w:w.update(source_sha256={}),'producer pins'),
])
def test_real_reference_negative_guards(corrupt,match):
    p=REAL/'spk-bv-v1a-symbolic-holdout.json'
    q=REAL/'spk-bv-v0w-native-13.json'
    if not p.is_file() or not q.is_file():pytest.skip('optional native user captures not mounted')
    aa=json.loads(p.read_bytes());w=json.loads(q.read_bytes());corrupt(aa,w)
    with pytest.raises(InterventionError,match=match):
        check_reference(aa,w,q.read_bytes())


def test_status_boundaries_and_exclusions():
    assert 'READONLY' in SCHEMA.upper() and 'OBSERVED_ONLY' in STATUS
    assert 'no-native-learning-or-causal-utility' in EXCLUSIONS
