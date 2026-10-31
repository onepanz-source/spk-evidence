"""v2c tests. Synthetic v2b/v1q/v1m fixtures NEVER grant native authority."""
from __future__ import annotations
import copy
import importlib.util
import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import pytest
from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, ObservationV2a, PORT_VERSION,
)
from spk_backvalidation_v2.time_order_executor_v2c import (
    TemporalPolicyV2c, check_policy, execute_time_order_v2c, EXECUTOR_VERSION,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.temporal_differential_v2c import (
    SCHEMA, STATUS, SOURCE_KIND, analyze, paired, assert_stream,
)
from search.spk_bv_v2c_temporal_differential import main

ROOT=Path(__file__).resolve().parents[1]
SHA_A=sha256((ROOT/'spk_backvalidation_v2/observed_scheduler_v2a.py').read_bytes()).hexdigest()
SHA_C=sha256((ROOT/'spk_backvalidation_v2/time_order_executor_v2c.py').read_bytes()).hexdigest()


def predecessor_fixtures():
    path=Path(__file__).with_name('test_spk_bv_v2b_differential_boundary.py')
    spec=importlib.util.spec_from_file_location('_research_v2b_fixture',path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d=m.make_fixture()
    b=m.build(d, frozen=True)
    return (b,canon(b),*d)


def result(d=None, *,frozen=False):
    d=predecessor_fixtures() if d is None else d
    return analyze(*d,SHA_A,SHA_C,frozen_custody=frozen)


def mutate(d, ix, fn):
    d=list(d)
    d[ix]=copy.deepcopy(d[ix]);fn(d[ix]);d[ix+1]=canon(d[ix])
    return tuple(d)


def basic_case(name='time.test', operators=('relay',)*3,
               stimuli=(1,1), mode=False):
    return BoundedCaseV2a(name,stimuli,operators,mode)


def test_report_source_and_narrow_scope():
    report=result(frozen=True)
    assert report['schema']==SCHEMA and report['status']==STATUS
    assert report['source_kind']==SOURCE_KIND
    assert report['frozen_native_source_pins_rechecked_in_this_run']
    assert report['native_micro_count_projection_fit_count']==16
    assert report['original_mode_order_and_AB_tick_projection_fit_count']==2
    assert report['time_order_micro_scheduler_runs']==32
    assert report['new_frozen_scheduler_runs']==0
    assert report['native_BV_state_or_scheduling_equivalence_proven'] is False
    assert report['native_CMP_semantics_equivalent'] is False
    assert report['real_native_B_receives_micro_observer_events'] is False
    assert report['native_operator_updates']==0
    assert report['native_learning_proven'] is False
    assert len(report['finite_rows'])==16
    assert all(r['observer_off_on_typed_result_bytes_equal'] for r in report['finite_rows'])
    assert all(r['native_counts_equal_in_finite_fixture'] for r in report['finite_rows'])


def test_source_owned_event_times_and_ordinal():
    c=basic_case()
    r,p=paired(c,TemporalPolicyV2c(2,1))
    assert r['executor_version']==EXECUTOR_VERSION
    assert r['emission_ticks']=={'A':[1,3],'B':[2,4],'C':[3,5]}
    assert r['forward_terminal_count']==2
    assert r['forward_routes']=={'A->B':2,'B->C':2}
    assert len(p.events)==23
    assert ''.join(e.actor for e in p.events if e.phase=='sender_port_emission'
                   and e.actor in ('A','B'))=='ABAB'
    assert [e.ordinal for e in p.events]==list(range(len(p.events)))
    assert all(a.logical_tick<=b.logical_tick for a,b in zip(p.events,p.events[1:]))
    assert_stream(c,TemporalPolicyV2c(2,1),r,p)
    assert p.summary()['native_receiver_B_control_messages']==0
    with pytest.raises((FrozenInstanceError,AttributeError)):
        p.events[0].actor='INTRUDER'


@pytest.mark.parametrize('gap,expectedA,expectedB,order', [
    (1,[1,2],[2,3],'AABB'), (2,[1,3],[2,4],'ABAB'),
    (3,[1,4],[2,5],'ABAB'), (4,[1,5],[2,6],'ABAB')])
def test_exogenous_pacing_is_not_native_clock(gap,expectedA,expectedB,order):
    c=basic_case()
    r,p=paired(c,TemporalPolicyV2c(gap,1))
    assert r['emission_ticks']['A']==expectedA
    assert r['emission_ticks']['B']==expectedB
    assert ''.join(e.actor for e in p.events if e.phase=='sender_port_emission' and
                   e.actor in ('A','B'))==order


@pytest.mark.parametrize('delay', [1,2,3,8])
def test_bounded_hop_latency_affects_micro_ticks_only(delay):
    c=basic_case()
    policy=TemporalPolicyV2c(2,delay)
    r,p=paired(c,policy)
    assert r['emission_ticks']['A']==[1,3]
    assert r['forward_emissions']=={'A':2,'B':2,'C':2}
    assert r['forward_routes']=={'A->B':2,'B->C':2}
    assert all(t == a + delay for t,a in zip(r['arrival_ticks']['B'],r['emission_ticks']['A']))


@pytest.mark.parametrize('ops,expected', [
    (('relay','relay','relay'),(2,2,2)),
    (('block','relay','relay'),(0,0,0)),
    (('relay','pair','relay'),(2,1,1)),
    (('relay','relay','pair'),(2,2,1)),
    (('relay','pair','pair'),(2,1,0)),
    (('relay','block','relay'),(2,0,0)),
])
def test_operator_counts_are_explicit_new_micro_rules(ops,expected):
    c=basic_case(operators=ops)
    r,p=paired(c,TemporalPolicyV2c())
    assert tuple(r['forward_emissions'][n] for n in ('A','B','C'))==expected
    assert_stream(c,TemporalPolicyV2c(),r,p)


@pytest.mark.parametrize('bad', [
    TemporalPolicyV2c(0,1),TemporalPolicyV2c(9,1),
    TemporalPolicyV2c(2,0),TemporalPolicyV2c(2,9),
    TemporalPolicyV2c(True,1),TemporalPolicyV2c(2,False),
    TemporalPolicyV2c(2.0,1),None,2,'2/1',
])
def test_invalid_temporal_policies_rejected(bad):
    with pytest.raises((ValueError,AssertionError,TypeError)):
        check_policy(bad)
    with pytest.raises((ValueError,AssertionError,TypeError)):
        execute_time_order_v2c(basic_case(),policy=bad)


def test_emitter_sink_fault_and_capacity_fail_closed_without_changing_forward():
    c=basic_case()
    orig=execute_time_order_v2c(c)
    def boom(_): raise RuntimeError('sink failed')
    result,p=paired(c,TemporalPolicyV2c(),sink=boom)
    assert result==orig and p.summary()['sink_fault']
    result,p=paired(c,TemporalPolicyV2c(),capacity=1)
    assert result==orig and p.overflow and not p.summary()['complete']
    assert p.summary()['independent_absence_certificates']==0
    assert p.summary()['authentication_verified'] is False
    assert p.summary()['native_receiver_B_control_messages']==0
    with pytest.raises((ValueError,AssertionError)):
        assert_stream(c,TemporalPolicyV2c(),result,p)


@pytest.mark.parametrize('change', [
    'actor','episode','phase','ordinal','tick','source_token','unowned_ingress',
    'duplicate_close','emission_count','arrival_count','decision_selected',
    'decision_operator','decision_owner','routes','emission_tick',
    'time_policy','decision_missing','fake_native',
])
def test_mutated_micro_stream_or_result_rejected(change):
    c=basic_case()
    policy=TemporalPolicyV2c()
    r,p=paired(c,policy)
    r=copy.deepcopy(r)
    if change=='actor':p.events[2]=replace(p.events[2],actor='OTHER')
    if change=='episode':p.events[0]=replace(p.events[0],episode='other')
    if change=='phase':p.events[0]=replace(p.events[0],phase='fake')
    if change=='ordinal':p.events[3]=replace(p.events[3],ordinal=18)
    if change=='tick':p.events[5]=replace(p.events[5],logical_tick=-3)
    if change=='source_token':p.events[2]=replace(p.events[2],event_token='forged')
    if change=='unowned_ingress':
        idx=next(i for i,e in enumerate(p.events) if e.phase=='receiver_ingress')
        p.events[idx]=replace(p.events[idx],event_token='not-issued',parent_token='not-issued')
    if change=='duplicate_close':p.events[0]=replace(p.events[0],phase='interval_coverage_close')
    if change=='emission_count':r['forward_emissions']['A']=99
    if change=='arrival_count':r['forward_arrivals']['B']=99
    if change=='decision_selected':r['decisions'][0]['selected']=False
    if change=='decision_operator':r['decisions'][0]['operator']='unknown'
    if change=='decision_owner':r['decisions'][0]['node']='C'
    if change=='routes':r['forward_routes']['A->B']=3
    if change=='emission_tick':r['emission_ticks']['A']=[99,3]
    if change=='time_policy':r['policy']['hop_delay']=8
    if change=='decision_missing':r['decisions'].pop()
    if change=='fake_native':r['decisions'][0]['decision_id']='native.fake'
    with pytest.raises((ValueError,AssertionError,KeyError,IndexError,TypeError)):
        assert_stream(c,policy,r,p)


@pytest.mark.parametrize('change', [
    'b_false_source','b_count','b_false_equivalence','b_missing_custody',
    'a_modified','native_wrong_ts','native_false_authority',
    'v1y_wrong_hash','v1z_unblocked','v1x_modified','raw_notcanonical',
])
def test_source_bound_replay_refuses_tampering(change):
    d=predecessor_fixtures()
    if change=='b_false_source':d=mutate(d,0,lambda b:b.__setitem__('source_kind','NATIVE'))
    if change=='b_count':d=mutate(d,0,lambda b:b.__setitem__('count_projection_cells_equal',15))
    if change=='b_false_equivalence':d=mutate(d,0,lambda b:b.__setitem__('native_cmp_semantics_equivalence_proven',True))
    if change=='b_missing_custody':d=mutate(d,0,lambda b:b.__setitem__('frozen_native_source_pins_rechecked_in_this_run',False))
    if change=='a_modified':d=mutate(d,2,lambda a:a['micro_results'][0].__setitem__('forward_terminal_count',20))
    if change=='native_wrong_ts':d=mutate(d,6,lambda m:m['native_trace_projection']['original']['on']['edge_projections'][0].__setitem__('sender_emission_timestamps',[1,4]))
    if change=='native_false_authority':d=mutate(d,4,lambda q:q.__setitem__('native_operator_updates',1))
    if change=='v1y_wrong_hash':d=mutate(d,10,lambda y:y['native_probe_parity_matrix']['original']['on'].__setitem__('native_return_bytes_equal',False))
    if change=='v1z_unblocked':d=mutate(d,8,lambda z:z.__setitem__('native_gate_status','PASS'))
    if change=='v1x_modified':d=mutate(d,12,lambda x:x.__setitem__('native_run_reference_matrix',{}))
    if change=='raw_notcanonical':
        d=list(d);d[1]=d[1]+b' ';d=tuple(d)
    with pytest.raises((ValueError,AssertionError,KeyError,IndexError,TypeError)):
        result(d)


def test_contract_only_report_never_claims_native_source_recheck():
    report=result()
    assert report['frozen_native_source_pins_rechecked_in_this_run'] is False
    assert report['temporal_policy_experimenter_selected']['stimulus_gap']==2
    assert report['original_timestamp_controls'][0]['micro_A_emission_ticks']==[1,3]
    assert report['original_timestamp_controls'][0]['counterfactual_gap3_micro_A_ticks']==[1,4]
    assert report['input_gap_perturbation_disproves_generalized_timestamp_identity'] is True


def test_report_exact_bytes_independent_of_hash_seed():
    a=canon(result());b=canon(result())
    assert a==b


def isolated_cli(tmp_path):
    root=tmp_path/'repository';root.mkdir()
    src=root/'spk_backvalidation_v2';src.mkdir()
    for name in ('observed_scheduler_v2a.py','time_order_executor_v2c.py'):
        (src/name).write_bytes((ROOT/'spk_backvalidation_v2'/name).read_bytes())
    files=tmp_path/'inputs';files.mkdir()
    args=[]
    for k,obj in zip(('v2b','v2a','v1q','v1m','v1z','v1y','v1x'),
                     predecessor_fixtures()[::2]):
        p=files/(k+'.json');p.write_bytes(canon(obj))
        args.extend(('--'+k,str(p)))
    return root,files,args


def test_cli_contract_only_no_clobber_and_byte_identical(tmp_path,capsys):
    root,files,args=isolated_cli(tmp_path)
    out=files/'result.json'
    argv=['--root',str(root),*args,'--contract-only','--out',str(out)]
    assert main(argv)==0
    first=out.read_bytes()
    assert json.loads(first)['native_micro_count_projection_fit_count']==16
    assert json.loads(first)['frozen_native_source_pins_rechecked_in_this_run'] is False
    assert main(argv)==2
    assert out.read_bytes()==first
    assert 'unsafe or existing output' in capsys.readouterr().err


def test_cli_symlink_alias_and_source_mutation_fail_closed(tmp_path):
    root,files,args=isolated_cli(tmp_path)
    link=files/'link.json';link.symlink_to(files/'v1q.json')
    alias=list(args);alias[alias.index('--v1q')+1]=str(link)
    assert main(['--root',str(root),*alias,'--contract-only',
                 '--out',str(files/'unused.json')])==2
    assert main(['--root',str(root),*args,'--contract-only',
                 '--out',str(root/'bad.json')])==2
    (root/'spk_backvalidation_v2/time_order_executor_v2c.py').write_text('tampered')
    assert main(['--root',str(root),*args,'--contract-only',
                 '--out',str(files/'unused.json')])==2

@pytest.mark.parametrize('n', [1,2,3,5,8,16])
def test_bounded_stimulus_count_and_causal_capacity(n):
    case=basic_case(name='test.n'+str(n),stimuli=(1,)*n)
    r,p=paired(case,TemporalPolicyV2c(2,1))
    assert r['forward_emissions']=={'A':n,'B':n,'C':n}
    assert len(r['decisions'])==3*n
    assert r['forward_terminal_count']==n
    assert len(p.events)<=512
    assert_stream(case,TemporalPolicyV2c(2,1),r,p)


def test_same_tick_ties_are_explicit_and_finite():
    c=basic_case()
    r,p=paired(c,TemporalPolicyV2c(1,1))
    assert r['emission_ticks']['A']==[1,2]
    assert r['emission_ticks']['B']==[2,3]
    assert [e.actor for e in p.events if e.phase=='sender_port_emission' and
            e.actor in ('A','B')]==['A','A','B','B']
    assert_stream(c,TemporalPolicyV2c(1,1),r,p)


def test_observer_reuse_is_not_allowed():
    port=ObserverV2a()
    execute_time_order_v2c(basic_case(),observation_port=port)
    with pytest.raises((ValueError,AssertionError)):
        execute_time_order_v2c(basic_case('other'),observation_port=port)


@pytest.mark.parametrize('field,value',[
    ('receiver_B_control_packets',1),('native_feedback_assessments',1),
    ('operator_updates',1),('executor_version','SPK_NATIVE'),
    ('episode','another'),('bv_label_only',True),
])
def test_false_native_or_receiver_claims_fail_closed(field,value):
    c=basic_case()
    r,p=paired(c,TemporalPolicyV2c())
    r[field]=value
    with pytest.raises((ValueError,AssertionError)):
        assert_stream(c,TemporalPolicyV2c(),r,p)


@pytest.mark.parametrize('field,value',[
    ('actor','C'),('target','A'),('decision_id','invalid'),
    ('event_token','forged'),('logical_tick',-5),
])
def test_emission_actor_target_provenance_tamper_rejected(field,value):
    c=basic_case()
    r,p=paired(c,TemporalPolicyV2c())
    idx=next(i for i,e in enumerate(p.events) if e.phase=='sender_port_emission')
    p.events[idx]=replace(p.events[idx],**{field:value})
    with pytest.raises((ValueError,AssertionError)):
        assert_stream(c,TemporalPolicyV2c(),r,p)
