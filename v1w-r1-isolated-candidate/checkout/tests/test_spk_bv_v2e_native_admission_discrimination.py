"""v2e independent research custody, adversarial controls, and synthetic executor tests."""
from __future__ import annotations
import copy,importlib.util,json
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
import pytest

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_holdout_differential_v2d import analyze as replay_d, compact_v0w
from spk_bv_research.off_on_v0t import snapshot,PINNED
from spk_bv_research.coincident_admission_discrimination_v2e import (
    analyze,validate_predecessors,build_workload,predictions,source_template_distinguishable,
    native_experiment,RECIPES,ANCHORS,SCHEMA,OFFLINE_STATUS,STATUS,
)
from search.spk_bv_v2e_native_admission_discrimination import main

ROOT=Path(__file__).resolve().parents[1]


def synthetic_predecessor():
    source=ROOT/'tests/test_spk_bv_v2d_native_holdout_differential.py'
    spec=importlib.util.spec_from_file_location('_v2d_v2e_synthetic_factory',source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture=module.fixture()
    v2d=replay_d(*fixture,*module.PINS,frozen_custody=True)
    w,wb=fixture[2:4]
    return v2d,canon(v2d),w,wb


@pytest.fixture(scope='module')
def prior():return synthetic_predecessor()


def test_predecessor_canonical_chain_and_default_negative_boundary(prior):
    d,db,w,wb=prior
    assert validate_predecessors(d,db,w,wb)
    r=analyze(d,db,w,wb)
    assert r['schema']==SCHEMA and r['status']==OFFLINE_STATUS
    assert len(r['predeclared_workload_recipes'])==15
    assert r['new_frozen_scheduler_executions']==0
    assert r['full_native_v0w_anchor_replay_count']==0
    assert r['native_matrix'] is None
    assert r['native_source_template_variants_distinguishable'] is None
    assert not r['native_CMP_semantics_or_scheduler_coalescence_identified']
    assert not r['native_learning_proven'] and r['native_B_control_messages']==0


def test_hypotheses_predeclared_are_different_and_not_authority():
    recipes=dict(RECIPES)
    assert set(ANCHORS)<=recipes.keys()
    assert len(recipes)==len(set(recipes))==15
    assert predictions(recipes['mixed_coincident'],templates_distinct=True)=={
        'independent_three_emissions_per_input':6,
        'one_three_emission_chain_per_tick':3,
        'one_three_emission_chain_per_template_tick':6}
    assert predictions(recipes['first_first_coincident'],templates_distinct=True)=={
        'independent_three_emissions_per_input':6,
        'one_three_emission_chain_per_tick':3,
        'one_three_emission_chain_per_template_tick':3}
    assert predictions(recipes['mixed_coincident'],templates_distinct=False)[
        'one_three_emission_chain_per_template_tick'] is None
    assert predictions(recipes['triple_mixed_coincident'],templates_distinct=True)[
        'independent_three_emissions_per_input']==9


@dataclass(frozen=True)
class Event:
    timestamp:int
    node_id:str
    channel:int
@dataclass(frozen=True)
class Case:
    events:tuple
    invariant:str='unchanged'


def native_case(distinct=True):
    return Case((Event(1,'A',0),Event(3,'A',1 if distinct else 0)))


@pytest.mark.parametrize('name,recipe',RECIPES)
def test_native_case_rewrites_only_external_events(name,recipe):
    original=native_case()
    modified=build_workload(original,recipe)
    assert tuple(e.timestamp for e in modified.events)==tuple(t for _,t in recipe)
    assert original.events==(Event(1,'A',0),Event(3,'A',1))
    assert modified.invariant==original.invariant
    assert len(modified.events)==len(recipe)
    assert len(set(id(x) for x in modified.events))==len(recipe)


@pytest.mark.parametrize('invalid', [(),((2,1),),((0,0),),((0,21),),((0,2),(1,1)),
                                      ((0,1),(1,2),(0,3),(1,4),(0,5)),
                                      ((0,True),),((0,1.0),),([0,1],),
                                      ((0,1,2),),'1,1',((0,1),[1,2])])
def test_invalid_native_workload_fail_closed(invalid):
    with pytest.raises((ValueError,TypeError,AssertionError,IndexError)):
        build_workload(native_case(),invalid)


def test_temporal_normalization_witness_scope():
    assert source_template_distinguishable(native_case(True))
    assert not source_template_distinguishable(native_case(False))
    assert native_case().events[0].timestamp==1


@pytest.mark.parametrize('alteration',[
    'bad_status','prior_d_noncanonical','prior_w_noncanonical','missing_chain',
    'promote_micro','missing_v0w','changed_v0w_source','changed_historical_count',
    'changed_anchor_capacity','v0w_hash','v2d_report_length','wrong_prior_counts',
])
def test_tampered_predecessors_rejected(prior,alteration):
    d,db,w,wb=prior
    d,w=copy.deepcopy(d),copy.deepcopy(w)
    if alteration=='bad_status':d['status']='ADMITTED'
    if alteration=='missing_chain':d['frozen_native_source_pins_rechecked_in_this_run']=False
    if alteration=='promote_micro':d['new_frozen_scheduler_executions']=1
    if alteration=='missing_v0w':w['cells']=w['cells'][:-1]
    if alteration=='changed_v0w_source':w['source_sha256'][next(iter(PINNED))]='0'*64
    if alteration=='changed_historical_count':d['historical_native_count_mismatch_cells']=0
    if alteration=='changed_anchor_capacity':w['cells'][0]['fabric_slots_per_tick']=9
    if alteration=='v0w_hash':d['reference_v0w_sha256']='0'*64
    if alteration=='v2d_report_length':d['native_micro_comparisons']=[{}]
    if alteration=='wrong_prior_counts':d['coincident_stimulus_count_contrast']['native_total_emissions']=6
    dr=canon(d);wr=compact_v0w(w)
    if alteration=='prior_d_noncanonical':dr+=b' '
    if alteration=='prior_w_noncanonical':wr+=b' '
    with pytest.raises((ValueError,TypeError,KeyError,AssertionError)):
        validate_predecessors(d,dr,w,wr)


@pytest.mark.parametrize('invalid',[
    {'native_runs':45,'full_result_anchor_cells':12,'cells':[], 'original_fixture_sha256':'x','pins':PINNED},
    {'native_runs':0,'full_result_anchor_cells':12,'cells':[{}]*15,'original_fixture_sha256':'x','pins':PINNED},
])
def test_fake_execution_cannot_be_promoted(prior,invalid):
    d,db,w,wb=prior
    with pytest.raises((ValueError,AssertionError)):
        analyze(d,db,w,wb,experimental=invalid,frozen_custody=True)
    with pytest.raises((ValueError,AssertionError)):
        analyze(d,db,w,wb,experimental=invalid,frozen_custody=False)


def test_canonical_report_repeat(prior):
    d,db,w,wb=prior
    assert canon(analyze(d,db,w,wb))==canon(analyze(d,db,w,wb))


def test_cli_contract_only_but_never_writes_into_repo(prior,tmp_path):
    d,db,w,wb=prior
    root=tmp_path/'checkout';root.mkdir()
    research=root/'spk_bv_research';research.mkdir()
    (research/'coincident_admission_discrimination_v2e.py').write_bytes(
        (ROOT/'spk_bv_research/coincident_admission_discrimination_v2e.py').read_bytes())
    inp=tmp_path/'inputs';inp.mkdir()
    dp=inp/'d.json';wp=inp/'w.json';dp.write_bytes(db);wp.write_bytes(wb)
    out=tmp_path/'safe.json'
    argv=['--root',str(root),'--v2d',str(dp),'--v0w',str(wp),'--out',str(out),'--contract-only']
    assert main(argv)==0
    assert out.read_bytes()==canon(analyze(d,db,w,wb))
    assert main(argv)==2
    assert main(argv[:-3]+['--out',str(root/'inside.json'),'--contract-only'])==2
    assert main(argv[:-3]+['--out',str(dp),'--contract-only'])==2


def test_cli_fails_closed_on_report_alias(prior,tmp_path):
    d,db,w,wb=prior
    root=tmp_path/'checkout';root.mkdir()
    research=root/'spk_bv_research';research.mkdir()
    (research/'coincident_admission_discrimination_v2e.py').write_bytes(
        (ROOT/'spk_bv_research/coincident_admission_discrimination_v2e.py').read_bytes())
    inp=tmp_path/'inputs';inp.mkdir()
    dp=inp/'d.json';dp.write_bytes(db)
    out=tmp_path/'out.json'
    assert main(['--root',str(root),'--v2d',str(dp),'--v0w',str(dp),
                 '--out',str(out),'--contract-only'])==2


def test_native_input_consistency_control_and_anchoring_boundaries():
    from spk_bv_research.coincident_admission_discrimination_v2e import _check_anchor
    run={x:{'whole_result_sha256':'x', 'metrics':{'forward_emissions':3}}
         for x,_,_ in (('off',False,'forward-first'),('on_forward_first',True,'forward-first'),('on_feedback_first',True,'feedback-first'))}
    dummy={'cells':[{'runs':copy.deepcopy(run)} for _ in range(15)]}
    assert _check_anchor('original_gap2',run,dummy) is None
    dummy['cells'][0]['runs']['off']['whole_result_sha256']='tampered'
    with pytest.raises(ValueError):_check_anchor('original_gap2',run,dummy)

@dataclass(frozen=True)
class DummyTransport:
    max_inflight_occurrences:int=4
    cross_pe_extra_ticks:int=1
@dataclass(frozen=True)
class DummyLinks:
    fabric_slots_per_tick:int=1
    link_slots_per_tick:int=1
    max_link_span_ticks:int=4
    max_outbox_per_pe:int=8
@dataclass(frozen=True)
class DummyControl:
    enabled:bool
    priority:str


def test_full_native_matrix_control_flow_with_restricted_synthetic_executor(monkeypatch,prior,tmp_path):
    import spk_bv_research.coincident_admission_discrimination_v2e as target
    d,db,w,wb=prior
    w=copy.deepcopy(w)
    fixture=(native_case(True),{},(DummyTransport(),None,None,DummyLinks()))
    w['original_fixture_sha256']=snapshot(fixture)
    counts={'calls':0}
    def fake_arm(executor,plan_type,case,fabric,plans,label,enabled,priority,cell_sha,input_case):
        counts['calls']+=1
        ticks=[e.timestamp for e in case.events]
        n=len(set(ticks))
        digest=sha256(f'{ticks}/{enabled}/{priority}'.encode()).hexdigest()
        return {'whole_result_sha256':digest,
                'metrics':{'forward_emissions':3*n,'forward_terminal':n,
                           'processed_batches':n,'processed_events':len(ticks)},
                'forward_states_sha256':digest,'forward_emission_payload_multiset_sha256':digest,
                'forward_terminal_payload_multiset_sha256':digest,
                'last_forward_terminal_tick':max(ticks),'last_feedback_delivery_tick':None}
    monkeypatch.setattr(target,'_arm',fake_arm)
    for name,recipe in RECIPES:
        if name not in ANCHORS: continue
        changed=build_workload(fixture[0],recipe)
        ref=w['cells'][('baseline','coincident','second_plus_1','second_plus_3','repeated_episode').index(ANCHORS[name])*3]
        ref['runs']={key:fake_arm(None,None,changed,None,None,None,on,pri,None,None)
                     for key,on,pri in (
                         ('off',False,'forward-first'),
                         ('on_forward_first',True,'forward-first'),
                         ('on_feedback_first',True,'feedback-first'))}
    counts['calls']=0
    result=native_experiment(lambda:fixture,lambda:None,DummyControl,w,
                             root=tmp_path,pin_sources=False)
    assert result['native_runs']==45 and result['full_result_anchor_cells']==12
    assert counts['calls']==45 and result['pins'] is None
    assert len(result['cells'])==15
    assert len([r for r in result['cells'] if r['was_v0w_full_result_replay_anchor']])==4
    pair=next(c for c in result['cells'] if c['label']=='mixed_coincident')
    assert pair['observed_total_emissions_per_control']==[3,3,3]
    assert pair['candidate_matches_per_control']['independent_three_emissions_per_input']==[False]*3
    assert not pair['native_mechanism_identified']
    w['cells'][3]['runs']['off']['whole_result_sha256']='0'*64
    with pytest.raises(ValueError):
        native_experiment(lambda:fixture,lambda:None,DummyControl,w,
                          root=tmp_path,pin_sources=False)
