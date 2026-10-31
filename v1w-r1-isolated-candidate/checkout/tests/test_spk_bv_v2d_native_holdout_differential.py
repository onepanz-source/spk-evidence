"""Independent synthetic v2d contract fixtures; never native evidence in tests."""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import copy
import importlib.util
import json

import pytest
from spk_backvalidation_v2.observed_scheduler_v2a import BoundedCaseV2a, ObserverV2a
from spk_backvalidation_v2.explicit_input_executor_v2d import (
    EXECUTOR_VERSION, ExplicitInputsV2d, check_explicit_inputs, execute_explicit_v2d,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.workload_sensitivity_v0w import WORKLOADS, CAPACITY_PROFILES, SCHEMA as W_SCHEMA, STATUS as W_STATUS
from spk_bv_research.off_on_v0t import PINNED
from spk_bv_research.temporal_differential_v2c import analyze as replay_c
from spk_bv_research.native_holdout_differential_v2d import (
    SCHEMA, STATUS, analyze, compact_v0w, paired_micro,
)
from search.spk_bv_v2d_native_holdout_differential import main

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('spk_backvalidation_v2/observed_scheduler_v2a.py',
         'spk_backvalidation_v2/time_order_executor_v2c.py',
         'spk_backvalidation_v2/explicit_input_executor_v2d.py')
PINS=tuple(sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES)
PARENTS=('v2c','v0w','v2b','v2a','v1q','v1m','v1z','v1y','v1x')
TICKS={'baseline':[1,3], 'coincident':[1,1],
       'second_plus_1':[1,4], 'second_plus_3':[1,6],
       'repeated_episode':[1,3,9,11]}


def fixture():
    f=Path(__file__).with_name('test_spk_bv_v2c_temporal_differential.py')
    spec=importlib.util.spec_from_file_location('_v2c_fixture_for_v2d',f)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    predecessors=module.predecessor_fixtures()
    b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb=predecessors
    c=replay_c(*predecessors,*PINS[:2],frozen_custody=True)
    w={
        'schema':W_SCHEMA,'status':W_STATUS,
        'same_fixture_before_after_every_run':True,
        'variation_scope':'external_event_timestamps_and_episode_repetition_only',
        'resource_scope':'capacity_profiles_((1,4),(2,1),(2,4))_other_plans_unchanged',
        'source_sha256':PINNED,'original_fixture_sha256':q['native_fixture_sha256'],
        'workloads':list(WORKLOADS),
        'capacity_profiles':[{'fabric_slots_per_tick':cap,'max_inflight_occurrences':infl}
                             for cap,infl in CAPACITY_PROFILES],
        'v0v_reference_check':{'status':'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED',
                               'v0v_v0u_v0t_v0o_chain':True},'cells':[],
    }
    for workload in WORKLOADS:
        t=TICKS[workload]
        for cap,infl in CAPACITY_PROFILES:
            total=3 if workload=='coincident' else len(t)*3
            terminal=total//3
            runs={}
            for mode in ('off','on_forward_first','on_feedback_first'):
                h=sha256(f'{workload}/{cap}/{infl}/{mode}'.encode()).hexdigest()
                if workload=='baseline' and cap==1 and infl==4 and mode=='off':
                    h=x['native_run_reference_matrix']['original']['off']['result_sha256']
                runs[mode]={'enabled':mode!='off',
                            'priority':'feedback-first' if mode=='on_feedback_first' else 'forward-first',
                            'whole_result_sha256':h,
                            'metrics':{'forward_emissions':total,'forward_terminal':terminal}}
            w['cells'].append({'status':'COMPLETE_THREE_ARM_WORKLOAD_CELL',
                               'workload':workload,'stimulus_timestamps':t,
                               'stimulus_count':len(t),
                               'fabric_slots_per_tick':cap,
                               'max_inflight_occurrences':infl,'runs':runs})
    return (c,canon(c),w,compact_v0w(w),*predecessors)


def report(f=None,*,frozen=True):
    return analyze(*(fixture() if f is None else f),*PINS,frozen_custody=frozen)


def mutate(f,index,callback):
    f=list(f)
    f[index]=copy.deepcopy(f[index])
    callback(f[index])
    f[index+1]=compact_v0w(f[index]) if index==2 else canon(f[index])
    return tuple(f)


def basic_case(n=2,ops=('relay',)*3):
    return BoundedCaseV2a('explicit.synthetic',tuple(1 for _ in range(n)),ops)


def test_native_holdout_comparison_report_and_negative_evidence():
    r=report()
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['historical_native_count_equal_cells']==24
    assert r['historical_native_count_mismatch_cells']==6
    assert r['historical_native_comparison_cells']==30
    assert r['new_frozen_scheduler_executions']==0
    assert r['new_research_micro_executions']==20
    assert r['native_B_control_messages']==0 and not r['native_learning_proven']
    assert r['coincident_stimulus_count_contrast']['native_aggregation_mechanism_inferred'] is False
    assert all(row['workload']=='coincident' for row in r['native_micro_comparisons']
               if not row['aggregate_counts_equal'])


@pytest.mark.parametrize('workload,ticks,micro',[
    ('baseline',[1,3],(6,2)),('coincident',[1,1],(6,2)),
    ('second_plus_1',[1,4],(6,2)),('second_plus_3',[1,6],(6,2)),
    ('repeated_episode',[1,3,9,11],(12,4)),
])
def test_identical_input_timestamps_in_micro_not_posthoc(workload,ticks,micro):
    r,port=paired_micro(workload,ticks,'off')
    assert r['executor_version']==EXECUTOR_VERSION
    assert r['input_ticks']==ticks
    assert r['emission_ticks']['A']==ticks
    assert (sum(r['forward_emissions'].values()),r['forward_terminal_count'])==micro
    assert port.summary()['complete']
    assert len(port.events)==r['logical_event_count']
    assert port.events[-1].phase=='interval_coverage_close'


@pytest.mark.parametrize('ticks,reason',[((0,3),'invalid'),((1,1020),'invalid'),
                                         ((3,1),'invalid'),((True,2),'invalid'),
                                         ((1.0,2),'invalid'),((1,),'invalid'),
                                         ([1,3],'invalid'),('13','invalid')])
def test_invalid_input_schedule_rejected(ticks,reason):
    with pytest.raises((ValueError,AssertionError,TypeError)):
        execute_explicit_v2d(basic_case(),ExplicitInputsV2d(ticks))


def test_timing_duplicate_is_not_auto_merged_in_research_micro():
    r,p=paired_micro('coincident',[1,1],'off')
    assert r['emission_ticks']['A']==[1,1]
    assert r['emission_ticks']['B']==[2,2]
    assert r['emission_ticks']['C']==[3,3]
    assert sum(e.phase=='sender_port_emission' for e in p.events)==6
    assert not p.summary()['authentication_verified']
    assert p.summary()['native_receiver_B_control_messages']==0


@pytest.mark.parametrize('ops,emissions',[ (('relay','pair','relay'),(2,1,1)),
                                          (('block','relay','relay'),(0,0,0)),
                                          (('relay','relay','pair'),(2,2,1)) ])
def test_new_micro_operators_are_not_native_cmp(ops,emissions):
    case=basic_case(2,ops)
    r=execute_explicit_v2d(case,ExplicitInputsV2d((1,3)))
    assert tuple(r['forward_emissions'].values())==emissions
    assert r['native_feedback_assessments']==0


def test_listener_failure_and_overflow_do_not_change_micro_result():
    case=basic_case()
    sched=ExplicitInputsV2d((1,1))
    original=execute_explicit_v2d(case,sched)
    def boom(_): raise RuntimeError('listener exploded')
    port=ObserverV2a(sink=boom)
    assert execute_explicit_v2d(case,sched,observation_port=port)==original
    assert port.sink_fault and not port.summary()['complete']
    port=ObserverV2a(capacity=1)
    assert execute_explicit_v2d(case,sched,observation_port=port)==original
    assert port.overflow and len(port.events)==1


def test_port_reuse_rejected_after_detached():
    case=basic_case()
    port=ObserverV2a()
    execute_explicit_v2d(case,ExplicitInputsV2d((1,2)),observation_port=port)
    with pytest.raises((ValueError,AssertionError)):
        execute_explicit_v2d(case,ExplicitInputsV2d((1,2)),observation_port=port)


@pytest.mark.parametrize('change',[
    'source_c_missing','source_c_claim','source_c_hash','w0_bad_schema',
    'w0_native_fixture','w0_bad_producer','w0_count','w0_event','w0_bad_control',
    'w0_claim_anchor','w0_canonical','v1q_modified','v1x_modified',
])
def test_report_fails_closed_on_tampering(change):
    f=fixture()
    if change=='source_c_missing': f=mutate(f,0,lambda c:c.__setitem__('frozen_native_source_pins_rechecked_in_this_run',False))
    if change=='source_c_claim': f=mutate(f,0,lambda c:c.__setitem__('native_CMP_semantics_equivalent',True))
    if change=='source_c_hash': f=mutate(f,0,lambda c:c.__setitem__('reference_v2b_sha256','0'*64))
    if change=='w0_bad_schema': f=mutate(f,2,lambda w:w.__setitem__('schema','NATIVE_NOPE'))
    if change=='w0_native_fixture': f=mutate(f,2,lambda w:w.__setitem__('original_fixture_sha256','0'*64))
    if change=='w0_bad_producer': f=mutate(f,2,lambda w:w['source_sha256'].__setitem__(next(iter(PINNED)),'0'*64))
    if change=='w0_count': f=mutate(f,2,lambda w:w['cells'][3]['runs']['off']['metrics'].__setitem__('forward_emissions',4))
    if change=='w0_event': f=mutate(f,2,lambda w:w['cells'][3].__setitem__('stimulus_timestamps',[1,2]))
    if change=='w0_bad_control': f=mutate(f,2,lambda w:w['cells'][3]['runs']['off'].__setitem__('enabled',True))
    if change=='w0_claim_anchor': f=mutate(f,2,lambda w:w['v0v_reference_check'].__setitem__('status','UNKNOWN'))
    if change=='w0_canonical':
        f=list(f);f[3]=f[3]+b' ';f=tuple(f)
    if change=='v1q_modified':f=mutate(f,8,lambda q:q.__setitem__('native_fixture_sha256','0'*64))
    if change=='v1x_modified':f=mutate(f,16,lambda x:x['native_run_reference_matrix']['original']['off'].__setitem__('result_sha256','0'*64))
    with pytest.raises((ValueError,AssertionError,KeyError,TypeError,IndexError)):
        report(f)


def test_contract_only_report_does_not_claim_new_native_custody():
    r=report(frozen=False)
    assert r['frozen_native_source_pins_rechecked_in_this_run'] is False
    assert r['historical_native_comparison_cells']==30


def test_replay_bytes_independent_of_hash_seed():
    assert canon(report())==canon(report())


def isolated_cli(tmp_path):
    root=tmp_path/'repository';root.mkdir()
    src=root/'spk_backvalidation_v2';src.mkdir()
    for name in SOURCES:
        p=root/name;p.parent.mkdir(exist_ok=True,parents=True)
        p.write_bytes((ROOT/name).read_bytes())
    base=tmp_path/'inputs';base.mkdir()
    argv=[]
    for key,obj in zip(PARENTS,fixture()[::2]):
        path=base/(key+'.json')
        path.write_bytes(compact_v0w(obj) if key=='v0w' else canon(obj))
        argv.extend(('--'+key,str(path)))
    return root,base,argv


def test_cli_contract_only_no_overwrite(tmp_path,capsys):
    root,base,argv=isolated_cli(tmp_path)
    dest=base/'v2d.json'
    cmd=['--root',str(root),*argv,'--contract-only','--out',str(dest)]
    assert main(cmd)==0
    first=dest.read_bytes()
    assert json.loads(first)['historical_native_count_mismatch_cells']==6
    assert json.loads(first)['frozen_native_source_pins_rechecked_in_this_run'] is False
    assert main(cmd)==2
    assert dest.read_bytes()==first
    assert 'unsafe or existing output' in capsys.readouterr().err


def test_cli_predecessor_symlink_or_mutation_rejected(tmp_path):
    root,base,argv=isolated_cli(tmp_path)
    link=base/'link.json';link.symlink_to(base/'v2c.json')
    alias=list(argv);alias[alias.index('--v2c')+1]=str(link)
    assert main(['--root',str(root),*alias,'--contract-only','--out',str(base/'new.json')])==2
    (root/SOURCES[2]).write_text('# compromised')
    assert main(['--root',str(root),*argv,'--contract-only','--out',str(base/'new.json')])==2


def test_cli_needs_native_sources_without_contract_only(tmp_path):
    root,base,argv=isolated_cli(tmp_path)
    assert main(['--root',str(root),*argv,'--out',str(base/'new.json')])==2
    assert not (base/'new.json').exists()
