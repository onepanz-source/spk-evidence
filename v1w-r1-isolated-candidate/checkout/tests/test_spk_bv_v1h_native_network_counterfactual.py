"""BV v1h strict synthetic doubles. Native scheduler run is a separate fwork CLI."""
from __future__ import annotations
import copy
from dataclasses import dataclass,replace
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research.native_route_lineage_v1g import SCHEMA as G_SCHEMA,STATUS as G_STATUS
from spk_bv_research.native_criterion_v1d import SCHEMA as D_SCHEMA,STATUS as D_STATUS
from spk_bv_research.native_network_counterfactual_v1h import (
    SCHEMA,STATUS,variant_fixture,variant_forward_audit,evaluate,build)
from search.spk_bv_v1h_network_counterfactual import main,NAMES

PROGRAMS={
 'A':(('SHIFT',1),('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
 'B':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
 'C':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
}

@dataclass(frozen=True)
class Neuron:
    node_id:str
    instructions:tuple
    initial_raw:int=0

@dataclass(frozen=True)
class Event:
    timestamp:int
    node_id:str
    channel:int

@dataclass(frozen=True)
class Case:
    nodes:tuple
    events:tuple

@dataclass(frozen=True)
class Edge:
    source_node:str
    source_channel:int
    target_node:str
    target_channel:int
    target_pe:str
    delay_ticks:int=1

@dataclass(frozen=True)
class Fabric:
    static_routes:tuple

OWNERS={'A':'PE0','B':'PE1','C':'PE2'}

def samples():
    native=(Case(tuple(Neuron(n,PROGRAMS[n]) for n in ('A','B','C')),
                 (Event(1,'A',0),Event(3,'A',0))),
            Fabric((Edge('A',7,'B',0,'PE1'),Edge('B',7,'C',0,'PE2'))),
            ('tplan','pplan','mplan','lplan'))
    d={'schema':D_SCHEMA,'status':D_STATUS,'native_updates_applied':0,
       'native_judgments_observed':0,'selected_candidate_position':2,
       'selected_was_training_improvement':True,'frozen_native_sources':{'test':'pin'},
       'training':[{}, {}, {'candidate_position':2,
           'original_program_sha256':snapshot(PROGRAMS['A']),
           'candidate_program_sha256':snapshot(PROGRAMS['A'][:2]+(('CMP',2),)+PROGRAMS['A'][3:])}]}
    g={'schema':G_SCHEMA,'status':G_STATUS,'native_fixture_sha256':snapshot(native),
       'original_forward_transport_grants_joined':True,
       'off_route_multiset_equal_on':True,'endogenous_receiver_judgments':0,
       'native_updates_applied':0,'original_off_occurrences':4,
       'original_on_occurrences':4,
       'static_routes':[
           {'source_node':'A','source_channel':7,'target_node':'B',
            'target_channel':0,'source_pe':'PE0','target_pe':'PE1','delay_ticks':1},
           {'source_node':'B','source_channel':7,'target_node':'C',
            'target_channel':0,'source_pe':'PE1','target_pe':'PE2','delay_ticks':1},
       ],'frozen_native_sources':{'test':'pin'}}
    return native,d,g


def _trace(enabled,*,modified=False):
    if modified:
        batches=[{'tick':1,'node':'A','channels':[0],'parents':[]},
                 {'tick':3,'node':'A','channels':[0],'parents':[]}]
        emissions=[];terminal=[];occ=[];grants=[]
        states={'A':1,'B':0,'C':0}
    else:
        batches=[{'tick':1,'node':'A','channels':[0],'parents':[]},
                 {'tick':2,'node':'B','channels':[0],'parents':['r1']},
                 {'tick':3,'node':'A','channels':[0],'parents':[]},
                 {'tick':3,'node':'C','channels':[0],'parents':['r2']},
                 {'tick':4,'node':'B','channels':[0],'parents':['r3']},
                 {'tick':5,'node':'C','channels':[0],'parents':['r4']}]
        emissions=[{'timestamp':t,'node_id':n,'channel':7} for t,n in
                   [(1,'A'),(2,'B'),(3,'A'),(3,'C'),(4,'B'),(5,'C')]]
        terminal=[x for x in emissions if x['node_id']=='C']
        occ=[];grants=[]
        for ident,src,dst,sp,tp,em,arr,parents in [
           ('r1','A','B','PE0','PE1',1,2,[]),
           ('r2','B','C','PE1','PE2',2,3,['r1']),
           ('r3','A','B','PE0','PE1',3,4,[]),
           ('r4','B','C','PE1','PE2',4,5,['r3']),
        ]:
            occ.append({'id':ident,'source':src,'target':dst,'source_pe':sp,'target_pe':tp,
                 'channel':0,'delay':1,'emitted_at':em,'delivered_at':arr,'parents':parents})
            grants.append({'id':ident,'tick':em,'delivered_at':arr,
                 'source':src,'target':dst,'source_pe':sp,'target_pe':tp,'wait':0})
        states={'A':0,'B':0,'C':0}
    ass=[{'id':'a1'},{'id':'a2'}] if enabled and not modified else []
    dels=[{'assessment_id':'a1'},{'assessment_id':'a1'},
          {'assessment_id':'a2'},{'assessment_id':'a2'}] if enabled and not modified else []
    n=len(dels)
    return {'schema':'spk-bv-live-dual-event-scheduler/v0e',
        'policy':'forward-first','enabled':enabled,
        'forward':{'states':states,'batches':batches,'emissions':emissions,
                   'terminal':terminal,'occurrences':occ,'link_grants':grants,
                   'processed_batches':len(batches),'processed_events':len(batches)},
        'feedback':{'assessments':ass,'deliveries':dels,
                    'link_grants':[{'wait':0} for _ in range(n)],
                    'unique_receiver_votes':n},
        'resources':{'timeline':[{'tick':t,'pe_service_total':1,'memory_total':1,
                                  'link_total':0,'feedback_sends':0}
                                 for t in range(1,6) ],
                     'contention':{},'bv_link_grants':n,'bv_service_units':n,
                     'bv_memory_units':2*n,'forward_reserved_memory_units':0,
                     'peak_cross_inflight':1}}


def full():
    native,d,g=samples()
    modified,ident=variant_fixture(native,d)
    off=_trace(False);on=_trace(True)
    voff=_trace(False,modified=True);von=_trace(True,modified=True)
    return native,d,g,modified,off,on,voff,von


def test_realistic_two_hop_full_network_difference():
    n,d,g,m,o,on,vo,von=full(); before=copy.deepcopy((n,d,g,m,o,on,vo,von))
    got=evaluate(n,d,g,o,on,m,vo,von,OWNERS)
    assert got['original']['off']['occurrences']==4
    assert got['variant']['off']['occurrences']==0
    assert got['off_variant_minus_original']['occurrences']==-4
    assert got['off_variant_minus_original']['terminal']==-2
    assert got['native_feedback_assessments']=={'original_on':2,'variant_on':0}
    assert got['native_scored_receiver_judgments']==0
    assert got['native_updates_applied']==0 and not got['native_learning_proven']
    assert not got['conditional_direct_A_to_C']
    assert (n,d,g,m,o,on,vo,von)==before


def test_fixture_replacement_exact_one_instruction_and_revert():
    n,d,g=samples();pre=snapshot(n)
    modified,ident=variant_fixture(n,d)
    assert ident['original_instruction']==['CMP',1] and ident['variant_instruction']==['CMP',2]
    assert ident['external_events_preserved'] and ident['original_nodes_unchanged']
    assert modified[0].nodes[1] is n[0].nodes[1]
    assert modified[0].nodes[2] is n[0].nodes[2]
    assert modified[0].nodes[0].instructions[2]==('CMP',2)
    assert n[0].nodes[0].instructions[2]==('CMP',1) and snapshot(n)==pre

@pytest.mark.parametrize('change',[
 lambda d:d.update(selected_candidate_position=0),
 lambda d:d.update(selected_was_training_improvement=False),
 lambda d:d.update(native_updates_applied=1),
 lambda d:d.update(native_judgments_observed=1),
 lambda d:d.update(schema='fake'),
 lambda d:d['training'][2].update(original_program_sha256='f'*64),
 lambda d:d['training'][2].update(candidate_program_sha256='0'*64),
 lambda d:d['training'][2].update(candidate_position=3),
])
def test_corrupt_selected_intervention_rejected(change):
    n,d,_=samples();change(d)
    with pytest.raises(InterventionError):variant_fixture(n,d)

@pytest.mark.parametrize('mutate',[
 lambda n:replace(n[0],nodes=n[0].nodes[:2]),
 lambda n:replace(n[0],nodes=n[0].nodes+(n[0].nodes[0],)),
 lambda n:replace(n[0],nodes=tuple(replace(x,instructions=PROGRAMS['B'])
                  if x.node_id=='A' else x for x in n[0].nodes)),
 lambda n:replace(n[0],nodes=tuple(replace(x,node_id='A')
                  if x.node_id=='B' else x for x in n[0].nodes)),
])
def test_invalid_native_fixture_rejected(mutate):
    n,d,_=samples()
    with pytest.raises(InterventionError):variant_fixture((mutate(n),n[1],n[2]),d)

@pytest.mark.parametrize('change',[
 lambda x:x['forward']['emissions'].append({'timestamp':1,'node_id':'A','channel':7}),
 lambda x:x['forward']['batches'][0].update(parents=['r1']),
 lambda x:x['forward']['link_grants'].append({'id':'r1'}),
 lambda x:x['forward'].update(states={'A':0}),
 lambda x:x['forward'].update(occurrences=[{'id':'r1'}]),
])
def test_zero_occurrence_branch_rejects_forged_work(change):
    n,d,g,m,o,on,vo,von=full(); change(vo)
    with pytest.raises((InterventionError,TypeError,KeyError,IndexError)):
        evaluate(n,d,g,o,on,m,vo,von,OWNERS)

@pytest.mark.parametrize('change',[
 lambda x:x['forward']['occurrences'][0].update(source='C'),
 lambda x:x['forward']['occurrences'][0].update(delivered_at=1),
 lambda x:x['forward']['occurrences'][0].update(parents=['r1']),
 lambda x:x['forward']['link_grants'][0].update(delivered_at=8),
 lambda x:x['forward']['emissions'].pop(),
 lambda x:x['forward']['batches'][1].update(parents=[]),
])
def test_original_trace_forgery_rejected(change):
    n,d,g,m,o,on,vo,von=full(); change(o)
    with pytest.raises((InterventionError,TypeError,KeyError,IndexError)):
        evaluate(n,d,g,o,on,m,vo,von,OWNERS)

@pytest.mark.parametrize('key,bad',[
 ('status','forged'),('native_fixture_sha256','0'*64),
 ('original_off_occurrences',100),('original_forward_transport_grants_joined',False),
 ('endogenous_receiver_judgments',1),('native_updates_applied',1),
])
def test_v1g_reference_forgery_rejected(key,bad):
    n,d,g,m,o,on,vo,von=full(); g[key]=bad
    with pytest.raises(InterventionError):evaluate(n,d,g,o,on,m,vo,von,OWNERS)


def test_direct_A_C_route_cannot_be_invented():
    n,d,g,m,o,on,vo,von=full()
    g['static_routes'][1]['source_node']='A'
    with pytest.raises(InterventionError,match='route changed'):
        evaluate(n,d,g,o,on,m,vo,von,OWNERS)


def test_variant_on_outcome_differences_recorded_not_assumed():
    n,d,g,m,o,on,vo,von=full()
    von['forward']['states']['A']=15
    got=evaluate(n,d,g,o,on,m,vo,von,OWNERS)
    assert got['variant_off_on_forward_outcomes_equal'] is False


def test_bounded_output_and_source_anchor():
    n,d,g,m,o,on,vo,von=full()
    out=build(n,g,b'v1gbytes',d,b'v1dbytes',o,on,vo,von,OWNERS,{'test':'pin'})
    assert out['schema']==SCHEMA and out['status']==STATUS
    assert out['intervention']['variant_program_sha256']==snapshot(m[0].nodes[0].instructions)
    assert not out['network_utility_identified']
    assert out['reference_v1g1_file_sha256']!=out['reference_v1d_file_sha256']
    assert out['experiment_kind']=='PRE_EPISODE_COPY_INTERVENTION'


def test_forged_source_binding_rejected():
    n,d,g,m,o,on,vo,von=full()
    with pytest.raises(InterventionError,match='source'):
        build(n,g,b'v1g',d,b'v1d',o,on,vo,von,OWNERS,{'test':'changed'})


def _args(root,out,refs):
    a=['--root',str(root)]
    for n,p in zip(NAMES,refs):a+=['--'+n,str(p)]
    return a+['--out',str(out)]


def test_cli_refuses_missing_inputs_before_native_import(tmp_path,capsys):
    root=tmp_path/'repo';root.mkdir()
    files=[tmp_path/f'missing{i}.json' for i in range(len(NAMES))]
    out=tmp_path/'out.json'
    assert main(_args(root,out,files))==2 and not out.exists()
    assert 'REJECTED' in capsys.readouterr().err


def test_cli_refuses_existing_output(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    files=[]
    for i in range(len(NAMES)):
        f=tmp_path/f'ref{i}.json';f.write_text('{}');files.append(f)
    out=tmp_path/'out.json';out.write_text('preserved')
    assert main(_args(root,out,files))==2 and out.read_text()=='preserved'


def test_cli_refuses_hardlink_references(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    f=tmp_path/'ref.json';f.write_text('{}')
    refs=[]
    for i in range(len(NAMES)):
        p=tmp_path/f'alias{i}.json';p.hardlink_to(f);refs.append(p)
    assert main(_args(root,tmp_path/'out.json',refs))==2


def test_cli_refuses_symlink_reference(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    refs=[]
    for i in range(len(NAMES)):
        p=tmp_path/f'file{i}.json';p.write_text('{}');refs.append(p)
    symlink=tmp_path/'ref-link.json';symlink.symlink_to(refs[0]);refs[0]=symlink
    assert main(_args(root,tmp_path/'out.json',refs))==2


def test_stable_deterministic_synthetic_double():
    assert evaluate(*full()[:3],full()[4],full()[5],full()[3],full()[6],full()[7],OWNERS) == \
           evaluate(*full()[:3],full()[4],full()[5],full()[3],full()[6],full()[7],OWNERS)
