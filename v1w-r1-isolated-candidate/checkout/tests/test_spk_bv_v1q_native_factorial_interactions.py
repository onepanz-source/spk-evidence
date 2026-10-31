"""BV v1q adversarial synthetic contract tests. NO native scheduler execution here."""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research import native_factorial_interaction_v1q as model
from spk_bv_research.native_causal_locus_v1p import copy_intervention as singleton_copy
from search import spk_bv_v1q_native_factorial_interactions as cli


@dataclass(frozen=True)
class Node:
    node_id:str
    instructions:tuple

@dataclass(frozen=True)
class Case:
    nodes:tuple
    events:tuple

@dataclass(frozen=True)
class Route:
    source_node:str
    target_node:str
    source_channel:int
    target_channel:int
    target_pe:str
    delay_ticks:int

@dataclass(frozen=True)
class Fabric:
    static_routes:tuple


def fixture():
    a=Node('A',(('SHIFT',1),('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)))
    b=Node('B',(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)))
    c=Node('C',b.instructions)
    return (Case((a,b,c),(('external',1),('external',3))),
        Fabric((Route('A','B',7,0,'PE1',1),Route('B','C',7,0,'PE2',1))),
        ('resource0','resource1'))


def sample(arm,mode):
    counts={
        'none':(2,2,2),'A':(0,0,0),'B':(2,1,1),'C':(2,2,1),
        'AB':(0,0,0),'AC':(0,0,0),'BC':(2,1,0),'ABC':(0,0,0),
    }[arm]
    a,b,c=counts
    return {'forward':{
       'batches':2+a+b+c,'emissions':a+b+c,'terminal':c,
       'occurrences':a+b,'link_grants':a+b,
       'states_sha256':'synthetic-'+arm},
       'edges':{'A->B:7->0':a,'B->C:7->0':b},
       'emissions_by_neuron':{'A':a,'B':b,'C':c},
       'native_result_sha256':'synthetic-'+arm+'-'+mode,
       'feedback_assessments':c if mode=='on' else 0,
       'feedback_deliveries':2*c if mode=='on' else 0}


def specimen():
    native=fixture();pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    predecessor={'schema':model.P_SCHEMA,'status':model.P_STATUS,
        'source_kind':'NATIVE_FROZEN_SCHEDULER_EXOGENOUS_INTERVENTION_MATRIX',
        'native_v1o_recomputation_verified_in_this_run':True,
        'native_matrix_repeatability_attested_in_this_run':True,
        'native_scheduler_executions_in_this_matrix':8,
        'causal_prefix_negative_controls_pass':True,
        'original_and_A_variant_replayed_against_v1h':True,
        'intervention_selector':'EXPERIMENTER_PRE_EPISODE_COPY',
        'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'native_receiver_decision_disclosure':False,'network_utility_identified':False,
        'native_fixture_sha256':snapshot(native),
        'frozen_native_sources':{'synthetic-fixture':'not-native'},
        'experiment_arms':{},'intervention_runs':{}}
    for arm,tag in model.SINGLE.items():
        _,info=singleton_copy(native,tag,pins)
        predecessor['experiment_arms'][tag]=info
        predecessor['intervention_runs'][tag]={mode:sample(arm,mode) for mode in ('off','on')}
    runs={arm:{mode:{'enabled':mode=='on','policy':'forward-first',
        'sample':sample(arm,mode)} for mode in ('off','on')} for arm in model.ARMS}
    return (predecessor,model.canon(predecessor),native,
            {'A':'PE0','B':'PE1','C':'PE2'},predecessor['frozen_native_sources'],runs)


def evaluate(monkeypatch):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    return model.analyze(*specimen())


def test_synthetic_full_matrix(monkeypatch):
    report=evaluate(monkeypatch)
    assert report['schema']==model.SCHEMA and report['status']==model.STATUS
    assert report['native_scheduler_executions_in_matrix']==16
    assert report['factorial_prefix_negative_control_pairs_verified']==16
    assert report['factorial_mobius_count_coefficients']['off']['terminal']['AB']==1
    assert report['factorial_mobius_count_coefficients']['off']['terminal']['AC']==1
    assert report['factorial_mobius_count_coefficients']['off']['terminal']['BC']==0
    assert report['event_count_interaction_present'] is True
    assert report['native_v1p_recomputation_verified_in_this_run'] is False
    assert report['native_factorial_repeatability_attested_in_this_run'] is False
    assert report['native_scored_receiver_judgments']==0
    assert report['native_operator_updates']==0 and not report['native_learning_proven']
    assert report['interaction_coefficients_are_utility_or_credit'] is False
    assert json.loads(model.canon(report))==report


@pytest.mark.parametrize('arm',model.ARMS)
def test_copy_detached_only_requested_programs(arm):
    native=fixture(); before=snapshot(native)
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    copy,info=model.clone(native,arm,pins)
    assert snapshot(native)==before
    assert copy[1] is native[1] and copy[2] is native[2]
    assert copy[0].events==native[0].events
    assert info['changed_nodes']==([] if arm=='none' else list(arm))
    assert set(info['mutations'])==(set() if arm=='none' else set(arm))
    assert (snapshot(copy)==before)==(arm=='none')
    assert all((x is y)==(x.node_id not in arm)
               for x,y in zip(native[0].nodes,copy[0].nodes))


@pytest.mark.parametrize('arm',('none','A','B','C'))
def test_singleton_cases_equal_v1p(arm):
    p,_,native,_,_,_=specimen()
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    _,newinfo=model.clone(native,arm,pins)
    assert newinfo['case_sha256']==p['experiment_arms'][model.SINGLE[arm]]['case_sha256']


@pytest.mark.parametrize('bad',('','BA','ACB','AA','noneA','Aq','a','ABCABC','AABB'))
def test_invalid_factorial_subset_rejected(bad):
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.subsets(bad)


@pytest.mark.parametrize('bad',('unexpected','ab','ABCD'))
def test_unknown_combination_rejected(bad):
    native=fixture();pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.clone(native,bad,pins)


def test_inclusion_exclusion_detects_overlap():
    x={arm:sample(arm,'off')['forward']['terminal'] for arm in model.ARMS}
    result=model.factorial_coefficients(x)
    assert result=={'none':2,'A':-2,'B':-1,'C':-1,
                    'AB':1,'AC':1,'BC':0,'ABC':0}
    assert all(sum(result[s] for s in model.subsets(arm))==x[arm]
        for arm in model.ARMS if arm!='none')


@pytest.mark.parametrize('bad',(-1,2.5,True,None,'1'))
def test_invalid_factorial_count_rejected(bad):
    x={arm:1 for arm in model.ARMS};x['BC']=bad
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.factorial_coefficients(x)


@pytest.mark.parametrize('field,bad',[
    ('schema','other'),('status','NATIVE_LEARNING'),
    ('source_kind','receiver'),('native_v1o_recomputation_verified_in_this_run',False),
    ('native_matrix_repeatability_attested_in_this_run',False),
    ('native_scheduler_executions_in_this_matrix',7),
    ('causal_prefix_negative_controls_pass',False),
    ('original_and_A_variant_replayed_against_v1h',False),
    ('intervention_selector','NEURON'),
    ('native_absence_witnesses',1),('native_scored_receiver_judgments',1),
    ('native_operator_updates',1),('native_learning_proven',True),
    ('native_receiver_decision_disclosure',True),('network_utility_identified',True),
    ('native_fixture_sha256','other'),('frozen_native_sources',{}),
])
def test_predecessor_tampering_rejected(field,bad):
    p,_,*_=specimen();p[field]=bad
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.validate_predecessor(p,model.canon(p))


def test_noncanonical_predecessor_rejected():
    p,raw,*_=specimen()
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.validate_predecessor(p,raw+b' ')


def test_singleton_report_swap_rejected(monkeypatch):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1])
    args[-1]['B']['off']['sample']['emissions_by_neuron']['B']=99
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


@pytest.mark.parametrize('combination,baseline,field,key',[
    ('BC','B','emissions_by_neuron','A'),
    ('AC','A','emissions_by_neuron','B'),
    ('ABC','AB','edges','B->C:7->0'),
    ('AB','A','edges','A->B:7->0'),
])
def test_prefix_contamination_rejected(monkeypatch,combination,baseline,field,key):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1])
    args[-1][combination]['off']['sample'][field][key]+=1
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


@pytest.mark.parametrize('field,key',[
    ('forward','terminal'),('edges','B->C:7->0'),
    ('emissions_by_neuron','C'),
])
def test_forward_off_on_interference_rejected(monkeypatch,field,key):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1])
    args[-1]['BC']['on']['sample'][field][key]+=1
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


@pytest.mark.parametrize('field',('feedback_assessments','feedback_deliveries'))
def test_off_feedback_in_combination_rejected(monkeypatch,field):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1])
    args[-1]['BC']['off']['sample'][field]=1
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


@pytest.mark.parametrize('field,value',[
    ('enabled',True),('policy','feedback-first')])
def test_invalid_arm_run_metadata_rejected(monkeypatch,field,value):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1]);args[-1]['AB']['off'][field]=value
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


def test_missing_combination_rejected(monkeypatch):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-1]=deepcopy(args[-1]);args[-1].pop('ABC')
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


def test_wrong_source_and_owners_rejected(monkeypatch):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());args[-2]={}
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.analyze(*args)


def test_copy_requires_original_programs():
    native=fixture();pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    pins['C']='0'*64
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.clone(native,'AB',pins)


def test_altered_native_instruction_refused():
    from dataclasses import replace
    native=fixture(); case,fabric,plans=native
    altered=replace(case.nodes[1],instructions=(('ACC',(1,0)),('CMP',2),('EMIT',7),('RESET',0)))
    native=(replace(case,nodes=(case.nodes[0],altered,case.nodes[2])),fabric,plans)
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    with pytest.raises((InterventionError,ValueError,AssertionError,TypeError)):
        model.clone(native,'ABC',pins)


def test_cli_inherits_exact_predecessor_names():
    from search.spk_bv_v1p_native_causal_locus import NAMES as previous
    assert cli.NAMES==('v1p',)+previous
    assert len(cli.NAMES)==len(set(cli.NAMES))


def make_cli_args(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    args=['--root',str(root)];names={}
    for n in cli.NAMES:
        path=tmp_path/(n+'.json');path.write_text('{}\n')
        names[n]=path;args+=['--'+n,str(path)]
    return root,args,names


def test_cli_rejects_alias_before_native_import(tmp_path):
    root,args,names=make_cli_args(tmp_path)
    args[args.index('--v1p')+1]=str(names['v1o'])
    out=tmp_path/'report.json'
    assert cli.main(args+['--out',str(out)])==2
    assert not out.exists()


def test_cli_rejects_existing_output_before_native_import(tmp_path):
    root,args,_=make_cli_args(tmp_path)
    out=tmp_path/'report.json';out.write_text('must-stay')
    assert cli.main(args+['--out',str(out)])==2
    assert out.read_text()=='must-stay'


def test_cli_rejects_source_inside_checkout(tmp_path):
    root,args,names=make_cli_args(tmp_path)
    inside=root/'v1p.json';inside.write_bytes(names['v1p'].read_bytes())
    args[args.index('--v1p')+1]=str(inside)
    out=tmp_path/'report.json'
    assert cli.main(args+['--out',str(out)])==2
    assert not out.exists()
