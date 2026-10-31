"""v2b self-contained synthetic reports are NOT native evidence.

This suite deliberately synthesizes v1q/v1m to test fail-closed behavior;
real fwork native records are verified separately by the CLI.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest

from spk_bv_research.native_allocation_boundary_v1r import canon, validate_q
from spk_bv_research.native_factorial_interaction_v1q import factorial_coefficients
from spk_bv_research.native_micro_differential_v2b import (
    SCHEMA,STATUS,SOURCE,ARMS,MODES,operators_for,validate_reports,compare,_native_order)
from spk_bv_research.versioned_executor_admission_v2a import analyze as create_a
from search.spk_bv_v2b_differential_boundary import main

SOURCE_FILE=Path(__file__).resolve().parents[1]/'spk_backvalidation_v2'/'observed_scheduler_v2a.py'
SOURCE_SHA=sha256(SOURCE_FILE.read_bytes()).hexdigest()


def predecessors():
    # Reuse upstream SELF-CONTAINED synthetic fixture helper, with no native files.
    f=Path(__file__).with_name('test_spk_bv_v2a_versioned_executor.py')
    spec=importlib.util.spec_from_file_location('_spk_v2a_synthetic_fixture',f)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.predecessors()


def native_counts(arm):
    if 'A' in arm:return (0,0,0)
    if 'B' in arm:return (2,1,0 if 'C' in arm else 1)
    return (2,2,1 if 'C' in arm else 2)


def make_fixture():
    z,y,x=predecessors()
    a=create_a(z,canon(z),y,canon(y),x,canon(x),
               frozen_source_custody=True,executor_sha256=SOURCE_SHA)
    pins={'frozen_fixture':'contract-test-only-not-real-source'}
    q={'schema':'spk-bv-native-exogenous-factorial-interactions/v1q',
       'status':'FROZEN_NATIVE_FULL_FACTORIAL_INTERACTION_NO_ENDOGENOUS_CREDIT',
       'source_kind':'FROZEN_NATIVE_SCHEDULER_EXOGENOUS_FULL_FACTORIAL',
       'native_v1p_recomputation_verified_in_this_run':True,
       'native_factorial_repeatability_attested_in_this_run':True,
       'native_scheduler_executions_in_matrix':16,
       'factorial_prefix_negative_control_pairs_verified':16,
       'event_count_interaction_present':True,
       'native_receiver_exposed_to_full_matrix':False,
       'native_independent_absence_certificates':0,
       'native_scored_receiver_judgments':0,
       'native_operator_updates':0,'native_learning_proven':False,
       'network_utility_identified':False,
       'interaction_coefficients_are_utility_or_credit':False,
       'native_fixture_sha256':'a'*64,'frozen_native_sources':pins,
       'reference_v1p_sha256':'a'*64,
       'factorial_runs':{},'interventions':{},
       'factorial_observed_counts':{},'factorial_mobius_count_coefficients':{}}
    for arm in ARMS:
        aa,bb,cc=native_counts(arm)
        q['interventions'][arm]={'arm':arm,
            'changed_nodes':list(arm) if arm!='none' else [],
            'mutations':{n:{'placeholder':'synthetic'} for n in arm if n in 'ABC'}}
        q['factorial_runs'][arm]={}
        for mode in MODES:
            e={'A->B:7->0':aa,'B->C:7->0':bb}
            label=('original' if arm=='none' else 'variant')
            if arm in ('none','A'):
                digest=y['native_probe_parity_matrix'][label][mode]['probe_result_sha256']
            else:digest=sha256((arm+mode).encode()).hexdigest()
            q['factorial_runs'][arm][mode]={
                'emissions_by_neuron':{'A':aa,'B':bb,'C':cc},
                'edges':e,'feedback_assessments':cc if mode=='on' else 0,
                'feedback_deliveries':2*cc if mode=='on' else 0,
                'native_result_sha256':digest,
                'forward':{'batches':2 if 'A' in arm else 5 if 'B' in arm else 6,
                           'emissions':aa+bb+cc,'occurrences':aa+bb,
                           'link_grants':aa+bb,'terminal':cc,
                           'states_sha256':'a'*64}}
    for mode in MODES:
        count={}
        for key in ('terminal','A->B:7->0','B->C:7->0','feedback_assessments'):
            count[key]={}
            for arm in ARMS:
                r=q['factorial_runs'][arm][mode]
                count[key][arm]=(r['forward']['terminal'] if key=='terminal' else
                                 r['feedback_assessments'] if key=='feedback_assessments' else
                                 r['edges'][key])
        q['factorial_observed_counts'][mode]=count
        q['factorial_mobius_count_coefficients'][mode]={
            k:factorial_coefficients(v) for k,v in count.items()}
    m={'schema':'spk-bv-native-passive-two-port-trace-projection/v1m',
       'status':'NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER',
       'source_kind':'FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES',
       'native_fixture_sha256':q['native_fixture_sha256'],
       'frozen_native_sources':pins,
       'full_native_scheduler_runs_recomputed_in_this_run':4,
       'native_two_port_independent_observer_installed':False,
       'native_coverage_certificates':0,'endogenous_receiver_judgments':0,
       'sender_operator_updates':0,'native_learning_proven':False,
       'cross_world_occurrence_identity_claimed':False,
       'native_trace_projection':{}}
    for origin,arm in (('original','none'),('variant','A')):
        m['native_trace_projection'][origin]={}
        for mode in MODES:
            edges=[]
            for src,dst,edge,times in [('A','B','A->B:7->0',[1,3]),
                                        ('B','C','B->C:7->0',[2,4])]:
                times=times if origin=='original' else []
                edges.append({'edge':edge,'sender':src,'receiver':dst,
                    'sender_emission_timestamps':times,
                    'sender_trace_emission_count':len(times),
                    'receiver_ingress_occurrence_count':len(times),
                    'receiver_consumed_occurrence_count':len(times),
                    'receiver_native_received_sender_port_attestation':False,
                    'independent_two_port_coverage_certificate':False})
            m['native_trace_projection'][origin][mode]={
                'native_full_scheduler_executed':True,
                'posthoc_simulator_trace_reader_only':True,
                'native_external_observer_present':False,
                'native_absence_certificate_count':0,
                'edge_projections':edges}
    return (a,canon(a),q,canon(q),m,canon(m),z,canon(z),y,canon(y),x,canon(x))


def build(d=None,*,frozen=False):
    d=make_fixture() if d is None else d
    return compare(*d,SOURCE_SHA,frozen_custody=frozen)


def alter(d,index,change):
    d=list(d)
    d[index]=copy.deepcopy(d[index])
    change(d[index])
    d[index+1]=canon(d[index])
    return tuple(d)


def test_finite_count_alignment_and_temporal_counterexample():
    report=build(frozen=True)
    assert report['schema']==SCHEMA and report['status']==STATUS
    assert report['source_kind']==SOURCE
    assert report['count_projection_cells_equal']==16
    assert len(report['count_alignment'])==16
    assert report['micro_off_on_executions_in_v2b']==32
    assert report['new_native_scheduler_executions_in_v2b']==0
    assert {r['native_posthoc_sender_order'] for r in report['original_temporal_counterexample']}=={'ABAB'}
    assert {r['micro_live_sender_order'] for r in report['original_temporal_counterexample']}=={'AABB'}
    assert all(not r['order_equal'] for r in report['original_temporal_counterexample'])
    assert not report['native_cmp_semantics_equivalence_proven']
    assert not report['native_state_equivalence_proven']
    assert report['native_receiver_B_control_packets']==0


@pytest.mark.parametrize('arm',ARMS)
def test_declared_operator_mapping_is_count_fitting_only(arm):
    op=operators_for(arm)
    assert op[0]==('block' if 'A' in arm else 'relay')
    assert op[1]==('pair' if 'B' in arm else 'relay')
    assert op[2]==('pair' if 'C' in arm else 'relay')


@pytest.mark.parametrize('bad', ['x','a','a ','ab','none ',None,5,('A',)])
def test_unsupported_native_mask_rejected(bad):
    with pytest.raises((ValueError,AssertionError,TypeError)):
        operators_for(bad)


@pytest.mark.parametrize('mutation', [
    'native_terminal','native_edge','native_assessment','native_interaction',
    'q_false_native','q_unauthorized_feedback','micro_sha','micro_no_custody',
    'micro_claim_spk_equivalence','micro_count','micro_wrong_source_kind',
    'native_bad_status','native_false_origin','native_cross_world','native_port_claim',
    'native_empty_timestamp','native_duplicate_timestamp','native_swapped_time',
    'native_wrong_sender','native_wrong_native_count','native_mismatched_fixture',
    'native_wrong_frozen_sources','native_bad_coverage','native_bad_other_mode',
    'native_modified_type','report_extra_noncanonical','native_timing_tie',
    'parent_y_baseline_hash','parent_z_rebuild','parent_x_changed',
])
def test_malformed_or_promoted_reports_rejected(mutation):
    d=make_fixture()
    if mutation=='native_terminal':d=alter(d,2,lambda q:q['factorial_runs']['B']['on']['forward'].__setitem__('terminal',500))
    elif mutation=='native_edge':d=alter(d,2,lambda q:q['factorial_runs']['BC']['off']['edges'].__setitem__('A->B:7->0',500))
    elif mutation=='native_assessment':d=alter(d,2,lambda q:q['factorial_runs']['none']['on'].__setitem__('feedback_assessments',0))
    elif mutation=='native_interaction':d=alter(d,2,lambda q:q['factorial_mobius_count_coefficients']['on']['terminal'].__setitem__('BC',999))
    elif mutation=='q_false_native':d=alter(d,2,lambda q:q.__setitem__('native_scheduler_executions_in_matrix',0))
    elif mutation=='q_unauthorized_feedback':d=alter(d,2,lambda q:q.__setitem__('native_operator_updates',1))
    elif mutation=='micro_sha':d=alter(d,0,lambda a:a.__setitem__('versioned_executor_file_sha256','0'*64))
    elif mutation=='micro_no_custody':d=alter(d,0,lambda a:a.__setitem__('frozen_native_source_pins_rechecked_in_this_run',False))
    elif mutation=='micro_claim_spk_equivalence':d=alter(d,0,lambda a:a.__setitem__('frozen_native_forward_equivalence_proven',True))
    elif mutation=='micro_count':d=alter(d,0,lambda a:a['micro_results'][0]['forward_emissions'].__setitem__('A',99))
    elif mutation=='micro_wrong_source_kind':d=alter(d,0,lambda a:a.__setitem__('source_kind','NATIVE'))
    elif mutation=='native_bad_status':d=alter(d,4,lambda m:m.__setitem__('status','NATIVE_DELIVERY'))
    elif mutation=='native_false_origin':d=alter(d,4,lambda m:m['native_trace_projection']['original']['off'].__setitem__('native_full_scheduler_executed',False))
    elif mutation=='native_cross_world':d=alter(d,4,lambda m:m.__setitem__('cross_world_occurrence_identity_claimed',True))
    elif mutation=='native_port_claim':d=alter(d,4,lambda m:m['native_trace_projection']['original']['on']['edge_projections'][0].__setitem__('receiver_native_received_sender_port_attestation',True))
    elif mutation=='native_empty_timestamp':d=alter(d,4,lambda m:m['native_trace_projection']['original']['off']['edge_projections'][0].__setitem__('sender_emission_timestamps',[]))
    elif mutation=='native_duplicate_timestamp':d=alter(d,4,lambda m:m['native_trace_projection']['original']['on']['edge_projections'][0].__setitem__('sender_emission_timestamps',[1,1]))
    elif mutation=='native_swapped_time':d=alter(d,4,lambda m:m['native_trace_projection']['original']['on']['edge_projections'][0].__setitem__('sender_emission_timestamps',[2,1]))
    elif mutation=='native_wrong_sender':d=alter(d,4,lambda m:m['native_trace_projection']['original']['off']['edge_projections'][1].__setitem__('sender','A'))
    elif mutation=='native_wrong_native_count':d=alter(d,4,lambda m:m['native_trace_projection']['original']['off']['edge_projections'][0].__setitem__('sender_trace_emission_count',1))
    elif mutation=='native_mismatched_fixture':d=alter(d,4,lambda m:m.__setitem__('native_fixture_sha256','b'*64))
    elif mutation=='native_wrong_frozen_sources':d=alter(d,4,lambda m:m.__setitem__('frozen_native_sources',{'other':'no'}))
    elif mutation=='native_bad_coverage':d=alter(d,4,lambda m:m.__setitem__('native_coverage_certificates',1))
    elif mutation=='native_bad_other_mode':d=alter(d,4,lambda m:m['native_trace_projection']['variant']['on'].__setitem__('native_absence_certificate_count',1))
    elif mutation=='native_modified_type':d=alter(d,4,lambda m:m['native_trace_projection']['original']['on']['edge_projections'][0].__setitem__('sender_emission_timestamps',[True,3]))
    elif mutation=='report_extra_noncanonical':
        d=list(d);d[1]=d[1]+b' ';d=tuple(d)
    elif mutation=='native_timing_tie':d=alter(d,4,lambda m:m['native_trace_projection']['original']['off']['edge_projections'][1].__setitem__('sender_emission_timestamps',[1,4]))
    elif mutation=='parent_y_baseline_hash':d=alter(d,8,lambda y:y['native_probe_parity_matrix']['original']['off'].__setitem__('probe_result_sha256','b'*64))
    elif mutation=='parent_z_rebuild':d=alter(d,6,lambda z:z.__setitem__('native_gate_status','PASS'))
    elif mutation=='parent_x_changed':d=alter(d,10,lambda x:x.__setitem__('native_run_reference_matrix',{}))
    with pytest.raises((ValueError,AssertionError,TypeError,KeyError,IndexError)):
        build(d)


def test_native_timestamp_ties_rejected_instead_of_invented_order():
    with pytest.raises((ValueError,AssertionError)):
        _native_order([{'sender':'A','sender_emission_timestamps':[1]},
                       {'sender':'B','sender_emission_timestamps':[1]}])


def test_hardcoded_original_order_is_counterexample_not_native_clock():
    r=build()
    assert r['original_trace_order_equivalence_disproven_in_fixture']
    assert not r['frozen_native_source_pins_rechecked_in_this_run']
    assert all(x['native_state_semantics_equal'] is None for x in r['count_alignment'])


def test_cli_synthetic_contract_only_rejects_output_clobber(tmp_path,capfd):
    root=tmp_path/'checkout'; root.mkdir()
    p=root/'spk_backvalidation_v2'; p.mkdir()
    (p/'observed_scheduler_v2a.py').write_bytes(SOURCE_FILE.read_bytes())
    inputs=tmp_path/'reports';inputs.mkdir()
    files=[]
    for key,obj in zip(('v2a','v1q','v1m','v1z','v1y','v1x'),make_fixture()[::2]):
        path=inputs/(key+'.json');path.write_bytes(canon(obj));files+=['--'+key,str(path)]
    output=tmp_path/'differential.json'
    flags=['--root',str(root),*files,'--out',str(output),'--contract-only']
    assert main(flags)==0
    first=output.read_bytes()
    assert json.loads(first)['count_projection_cells_equal']==16
    assert main(flags)==2
    assert output.read_bytes()==first
    assert 'unsafe or existing output' in capfd.readouterr().err


def test_cli_rejects_symlink_and_input_alias(tmp_path):
    root=tmp_path/'checkout';root.mkdir()
    source=root/'spk_backvalidation_v2';source.mkdir()
    (source/'observed_scheduler_v2a.py').write_bytes(SOURCE_FILE.read_bytes())
    inp=tmp_path/'files';inp.mkdir()
    args=[]
    for key,obj in zip(('v2a','v1q','v1m','v1z','v1y','v1x'),make_fixture()[::2]):
        f=inp/(key+'.json');f.write_bytes(canon(obj));args.extend(['--'+key,str(f)])
    f=inp/'alias.json';f.symlink_to(inp/'v1q.json')
    args_bad=list(args);args_bad[args_bad.index('--v1q')+1]=str(f)
    args_bad+=['--root',str(root),'--out',str(inp/'no-output.json'),'--contract-only']
    assert main(args_bad)==2
    args.append('--root');args.append(str(root))
    args+=['--out',str(root/'in-repo.json'),'--contract-only']
    assert main(args)==2
