"""BV v1p synthetic and adversarial tests, native runtime NOT claimed."""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research import native_causal_locus_v1p as model
from search import spk_bv_v1p_native_causal_locus as cli


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


def native_fixture():
    a=Node('A',(('SHIFT',1),('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)))
    b=Node('B',(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)))
    c=Node('C',b.instructions)
    case=Case((a,b,c),(('external',1),('external',3)))
    fabric=Fabric((Route('A','B',7,0,'PE1',1),Route('B','C',7,0,'PE2',1)))
    return case,fabric,('budget-0','budget-1')


def arm_sample(node,mode):
    if node=='sham':counts=[2,2,2];edges=[2,2]
    elif node=='A_cmp2':counts=[0,0,0];edges=[0,0]
    elif node=='B_cmp2':counts=[2,0,0];edges=[2,0]
    else:counts=[2,2,0];edges=[2,2]
    forward={'batches':6 if node=='sham' else (2 if node=='A_cmp2' else 4),
       'emissions':sum(counts),'terminal':counts[-1],
       'occurrences':sum(edges),'link_grants':sum(edges),
       'states_sha256':'synthetic-'+node}
    return {'forward':forward,'edges':{'A->B:7->0':edges[0],
            'B->C:7->0':edges[1]},
        'emissions_by_neuron':dict(zip(('A','B','C'),counts)),
        'native_result_sha256':f'synthetic-{node}-{mode}',
        'feedback_assessments':0 if mode=='off' else (2 if node=='sham' else 0),
        'feedback_deliveries':0 if mode=='off' else (4 if node=='sham' else 0)}


def specimen():
    native=native_fixture()
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    sources={'frozen':'synthetic-not-native'}
    d={'selected_candidate_position':2,'selected_was_training_improvement':True,
       'native_updates_applied':0,'native_judgments_observed':0,
       'training':[{}, {}, {'original_program_sha256':pins['A']},
             {'original_program_sha256':pins['B']},{'original_program_sha256':pins['C']} ]}
    db=model.canon(d)
    h={'schema':model.H_SCHEMA,'status':model.H_STATUS,
       'reference_v1d_file_sha256':sha256(db).hexdigest(),
       'native_fixture_sha256':snapshot(native),'frozen_native_sources':sources,
       'real_variant_full_fabric_replay':True,'native_updates_applied':0,
       'native_learning_proven':False,
       'intervention':{'original_program_sha256':pins['A'],
        'variant_program_sha256':snapshot(native[0].nodes[0].instructions[:2]+(('CMP',2),)+native[0].nodes[0].instructions[3:])}}
    for mode in ('off','on'):
        h.setdefault('original',{})[mode]=arm_sample('sham',mode)['forward']
        h.setdefault('variant',{})[mode]=arm_sample('A_cmp2',mode)['forward']
        h['original'][mode+'_result_sha256']='synthetic-sham-'+mode
        h['variant'][mode+'_result_sha256']='synthetic-A_cmp2-'+mode
    hb=model.canon(h)
    m={'schema':model.M_SCHEMA,'status':model.M_STATUS,
       'reference_v1d_sha256':sha256(db).hexdigest(),
       'reference_v1h_sha256':sha256(hb).hexdigest(),
       'full_native_scheduler_runs_recomputed_in_this_run':4,
       'native_fixture_sha256':snapshot(native),'frozen_native_sources':sources,
       'sender_operator_updates':0,'recipient_access_to_sender_trace_demonstrated':False}
    mb=model.canon(m)
    o={'schema':model.O_SCHEMA,'status':model.O_STATUS,
       'native_v1n_recomputation_verified_in_this_run':True,
       'native_scheduler_arms_inherited':4,'reference_v1m_sha256':sha256(mb).hexdigest(),
       'native_fixture_sha256':snapshot(native),'frozen_native_sources':sources,
       'native_original_A_to_B':{'sender_emissions':2,'receiver_ingress':2},
       'native_variant_A_to_B':{'sender_emissions':0,'receiver_ingress':0},
       'native_authenticated_decision_records':0,'native_receiver_judgments':0,
       'native_sender_operator_updates':0,'native_learning_proven':False}
    ob=model.canon(o)
    runs={arm:{mode:{'enabled':mode=='on','policy':'forward-first','sample':arm_sample(arm,mode)}
                 for mode in ('off','on')} for arm,_,_,_ in model.PLAN}
    owners={'A':'PE0','B':'PE1','C':'PE2'}
    return o,ob,h,hb,m,mb,d,db,native,owners,sources,runs


def outcome(monkeypatch):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    return model.analyze(*specimen())


def test_bounded_source_pins():
    o,ob,h,hb,m,mb,d,db,*_=specimen()
    assert model.bounded_sources(o,ob,h,hb,m,mb,d,db)


def test_integration_synthetic(monkeypatch):
    r=outcome(monkeypatch)
    assert r['schema']==model.SCHEMA and r['status']==model.STATUS
    assert r['native_scheduler_executions_in_this_matrix']==8
    assert r['native_v1o_recomputation_verified_in_this_run'] is False
    assert r['native_matrix_repeatability_attested_in_this_run'] is False
    assert r['causal_prefix_negative_controls_pass'] is True
    assert len(r['paired_contrasts_off'])==3
    assert r['native_scored_receiver_judgments']==r['native_operator_updates']==0
    assert r['native_learning_proven'] is False
    assert r['native_receiver_decision_disclosure'] is False
    assert r['experiment_arms']['sham']['sham'] is True
    assert r['paired_contrasts_off'][0]['delta_emissions_by_neuron']=={'A':-2,'B':-2,'C':-2}
    assert r['paired_contrasts_off'][1]['delta_emissions_by_neuron']=={'A':0,'B':-2,'C':-2}
    assert r['paired_contrasts_off'][2]['delta_emissions_by_neuron']=={'A':0,'B':0,'C':-2}
    assert all(row['utility_or_credit_inferred'] is False for row in r['paired_contrasts_off'])


@pytest.mark.parametrize('arm,node,index',[
 ('sham','A',2),('A_cmp2','A',2),('B_cmp2','B',1),('C_cmp2','C',1)])
def test_copies_leave_original_untouched(arm,node,index):
    native=native_fixture(); initial=snapshot(native)
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    copy,info=model.copy_intervention(native,arm,pins)
    assert snapshot(native)==initial
    assert copy[1] is native[1] and copy[2] is native[2]
    assert copy[0].events==native[0].events
    assert info['node']==node and info['instruction_index']==index
    assert (snapshot(copy)==initial)==(arm=='sham')
    assert all(x is y for x,y in zip(native[0].nodes,copy[0].nodes) if x.node_id!=node)


@pytest.mark.parametrize('field,bad',[
 ('schema','wrong'),('status','NATIVE_LEARNING'),
 ('native_v1n_recomputation_verified_in_this_run',False),
 ('native_scheduler_arms_inherited',3),('reference_v1m_sha256','0'*64),
 ('native_fixture_sha256','none'),('frozen_native_sources',{}),
 ('native_original_A_to_B',{'sender_emissions':0,'receiver_ingress':0}),
 ('native_variant_A_to_B',{'sender_emissions':2,'receiver_ingress':2}),
 ('native_authenticated_decision_records',1),('native_receiver_judgments',1),
 ('native_sender_operator_updates',1),('native_learning_proven',True),
])
def test_v1o_reference_tampering_rejected(field,bad):
    o,_,h,hb,m,mb,d,db,*_=specimen();o[field]=bad
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.bounded_sources(o,model.canon(o),h,hb,m,mb,d,db)


@pytest.mark.parametrize('field,bad',[
 ('schema','other'),('status','other'),('reference_v1d_file_sha256','0'*64),
 ('native_fixture_sha256','foreign'),('real_variant_full_fabric_replay',False),
 ('native_updates_applied',1),('native_learning_proven',True)])
def test_v1h_source_tampering_rejected(field,bad):
    o,ob,h,_,m,mb,d,db,*_=specimen();h[field]=bad
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.bounded_sources(o,ob,h,model.canon(h),m,mb,d,db)


@pytest.mark.parametrize('field,bad',[
 ('reference_v1h_sha256','0'*64),('full_native_scheduler_runs_recomputed_in_this_run',3),
 ('recipient_access_to_sender_trace_demonstrated',True),('sender_operator_updates',1),
 ('native_fixture_sha256','other'),('status','native_monitor')])
def test_v1m_source_tampering_rejected(field,bad):
    o,ob,h,hb,m,_,d,db,*_=specimen();m[field]=bad
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.bounded_sources(o,ob,h,hb,m,model.canon(m),d,db)


@pytest.mark.parametrize('field,bad',[
 ('selected_candidate_position',3),('selected_was_training_improvement',False),
 ('native_updates_applied',1),('native_judgments_observed',1)])
def test_v1d_selection_tampering_rejected(field,bad):
    o,ob,h,hb,m,mb,d,_,*_=specimen();d[field]=bad
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.bounded_sources(o,ob,h,hb,m,mb,d,model.canon(d))


def test_noncanonical_input_rejected():
    o,ob,h,hb,m,mb,d,db,*_=specimen()
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.bounded_sources(o,ob+b' ',h,hb,m,mb,d,db)


def test_unknown_intervention_rejected():
    native=native_fixture(); pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.copy_intervention(native,'C_new',pins)


@pytest.mark.parametrize('node,index,bad',[
 ('A',2,('EMIT',7)),('B',1,('CMP',2)),('C',1,('SHIFT',0))])
def test_original_instruction_drift_rejected(node,index,bad):
    from dataclasses import replace
    native=native_fixture();case,fabric,plan=native
    nodes=tuple(replace(n,instructions=n.instructions[:index]+(bad,)+n.instructions[index+1:])
                if n.node_id==node else n for n in case.nodes)
    native=(replace(case,nodes=nodes),fabric,plan)
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    arm={'A':'A_cmp2','B':'B_cmp2','C':'C_cmp2'}[node]
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.copy_intervention(native,arm,pins)


def test_mismatched_program_pin_rejected():
    native=native_fixture();pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    pins['B']='0'*64
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.copy_intervention(native,'A_cmp2',pins)


@pytest.mark.parametrize('arm,which',[
 ('B_cmp2','A'),('C_cmp2','A'),('C_cmp2','B')])
def test_upstream_contamination_rejected(monkeypatch,arm,which):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());runs=deepcopy(args[-1]);runs[arm]['off']['sample']['emissions_by_neuron'][which]=999
    args[-1]=runs
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.analyze(*args)


@pytest.mark.parametrize('arm',('sham','A_cmp2','B_cmp2','C_cmp2'))
def test_forward_off_on_drift_rejected(monkeypatch,arm):
    monkeypatch.setattr(model,'native_arm',lambda run,edges:run['sample'])
    args=list(specimen());runs=deepcopy(args[-1]);runs[arm]['on']['sample']['forward']['states_sha256']='different'
    args[-1]=runs
    with pytest.raises((InterventionError,AssertionError,ValueError)):
        model.analyze(*args)


def test_canonical_report_and_zero_claims(monkeypatch):
    report=outcome(monkeypatch)
    assert json.loads(model.canon(report))==report
    assert not report['native_learning_proven']
    assert 'posthoc-scheduler-causal-contrast-not-receiver-readable-evidence' in report['claims_excluded']


def test_cli_names_match_predecessor():
    from search.spk_bv_v1o_decision_disclosure import NAMES as OLD
    assert cli.NAMES==('v1o',)+OLD
    assert len(cli.NAMES)==len(set(cli.NAMES))


def _cli_args(tmp_path,*,root):
    names={}
    for name in cli.NAMES:
        path=tmp_path/(name+'.json');path.write_text('{}\n')
        names[name]=path
    args=['--root',str(root)]
    for name in cli.NAMES:args+=['--'+name,str(names[name])]
    return args,names


def test_cli_rejects_aliased_input_before_native_import(tmp_path):
    root=tmp_path/'repository';root.mkdir()
    args,names=_cli_args(tmp_path,root=root)
    i=args.index('--v1o')
    args[i+1]=str(names['v1n'])
    assert cli.main(args+['--out',str(tmp_path/'result.json')])==2
    assert not (tmp_path/'result.json').exists()


def test_cli_rejects_existing_output_before_native_import(tmp_path):
    root=tmp_path/'repository';root.mkdir()
    args,names=_cli_args(tmp_path,root=root)
    out=tmp_path/'result.json';out.write_text('guard')
    assert cli.main(args+['--out',str(out)])==2
    assert out.read_text()=='guard'


def test_cli_rejects_in_repository_source_inputs(tmp_path):
    root=tmp_path/'repository';root.mkdir()
    args,names=_cli_args(tmp_path,root=root)
    bad=root/'v1o.json';bad.write_bytes(names['v1o'].read_bytes())
    i=args.index('--v1o');args[i+1]=str(bad)
    assert cli.main(args+['--out',str(tmp_path/'result.json')])==2
    assert not (tmp_path/'result.json').exists()
