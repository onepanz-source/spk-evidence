"""BV v1y: external interpreter observation cannot become native authority."""
from __future__ import annotations
import copy, json, sys
from hashlib import sha256
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError, snapshot
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.reference_observation_port_v1x import NATIVE_LIMITS
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS
from spk_bv_research.native_external_probe_v1y import (
    check_x, ScopedPythonProbe, observed_pair, analyze, NATIVE_ZERO, LIMIT, STATUS, SCHEMA,
)
from spk_bv_research.observation_seam_contract_v1w import EXPECTED_PINS
from spk_bv_research.reference_observation_port_v1x import W_SCHEMA, W_STATUS
from spk_bv_research.reference_observation_port_v1x import analyze as analyze_x
from search.spk_bv_v1y_native_external_probe import main,verify_source_digest_map


def sample_w():
    names={'back_validation':2,'forward_route':0,'receiver_ingress':2,
           'scheduler_batch':0,'sender_emission':0}
    return {'schema':W_SCHEMA,'status':W_STATUS,
        'source_kind':'FROZEN_NATIVE_AST_READONLY_CANDIDATES_NO_EVENT_TAP',
        'native_source_readonly_bytes_rechecked_in_this_run':True,
        'inherited_native_v1v_recomputation_verified_in_this_run':True,
        'source_files_modified':False,'native_event_callback_invoked':False,
        'native_observation_message_delivered_to_B':False,
        'native_authenticated_absence_coverage':False,
        'native_receiver_scored_judgments':0,'native_operator_updates':0,
        'native_learning_proven':False,'new_native_scheduler_executions_in_this_module':0,
        'postreturn_trace_is_online_native_evidence':False,
        'static_candidate_is_runtime_event_hook':False,
        'design_port_name_only':'spk-bv-observation-port/v1-proposal',
        'integration_path_selection':'VERSIONED_ADDITIVE_SOURCE_OWNED_OBSERVER_PORT_REQUIRED_NOT_INSTALLED',
        'confirmed_frozen_scheduler_signature':{'name':'execute_live_v0e',
           'positional':['case','fabric','tplan','pplan','mplan','lplan','bv'],
           'keyword_only':[],'possible_callback_name_hints':[],
           'async_function':False,'generator_body_has_yield':False},
        'reference_v1v_sha256':'a'*64,
        'proof_obligations_unmet':[{'id':k,'requirement':v,'verified':False}
                                   for k,v in PORT_OBLIGATIONS],
        'source_pinned_static_candidate_inventory': {
            'candidate_extraction':'STATIC_CALL_NAME_MATCHES_NOT_EXECUTION_OR_DATA_FLOW',
            'candidate_count_by_category':names,'bounded_callsite_examples':{
               k:[{'verified_hook':False,'line':1,'callee':'mock','file':'mock.py','function':'mock'}
                  for _ in range(n)] for k,n in names.items()},
            'native_event_semantics_established':False,
            'native_listener_or_callback_installed':False,
            'source_file_sha256':dict(sorted(EXPECTED_PINS.items()))}}



def xsource():
    w=sample_w()
    matrix={}
    for arm, n in (('original',2),('variant',0)):
        matrix[arm]={}
        for mode in ('off','on'):
            matrix[arm][mode]={'sender':n,'ingress':n,'repeatability_identical':True,
             'result_sha256':sha256(canon({'n':n,'mode':mode})).hexdigest()}
    x=analyze_x(w,canon(w),native_reference=matrix,source_rechecked=True)
    x['inherited_native_v1w_recomputation_verified_in_this_run']=True
    return x


def small_native(v):
    if v < 0:raise ValueError('bad')
    x=0
    for n in range(v):x+=n
    return {'x':x,'v':v}


def test_predecessor_accepts_complete_fixture():
    x=xsource(); assert check_x(x,canon(x))


@pytest.mark.parametrize('field,value',[
 ('status','NATIVE_INSTALLED'),('schema','invalid'),
 ('source_kind','NATIVE_STREAM'),('native_callback_connected',True),
 ('native_observer_enabled_mode_executed',True),('native_receiver_B_received_control_messages',1),
 ('native_coverage_certificates',1),('native_authenticated_producer_evidence',1),
 ('native_scored_receiver_judgments',1),('native_operator_updates',1),
 ('native_learning_proven',True),('source_files_modified',True),
 ('native_results_repeated_without_observer',False),
 ('native_source_readonly_bytes_rechecked_in_this_run',False),
 ('inherited_native_v1w_recomputation_verified_in_this_run',False),
 ('reference_port_is_native_scheduled_event_tap',True),
 ('reference_port_executed_during_reference_runtime',False),
 ('native_baseline_equal_bytes_not_observer_on_off_proof',False),
 ('reference_lab_session_count',63),('native_scheduler_executions_in_this_module',0),
])
def test_promoted_predecessor_rejected(field,value):
    x=xsource();x[field]=value
    with pytest.raises(InterventionError):check_x(x,canon(x))


@pytest.mark.parametrize('tamper',[
 'row_missing','arm_extra','mode_missing','sender_bool','sender_drift','ingress_drift',
 'repeat_false','hash_bad','row_extra','proof_promoted','proof_missing','case_missing',
 'case_duplicate','case_native_callback','case_judgment','case_authority',
 'case_absence','case_operator','case_no_ref_noninterference','case_wrong_plan',
 'noncanonical','w_hash_missing',
])
def test_adversarial_predecessor(tamper):
    x=xsource();matrix=x['native_run_reference_matrix']
    if tamper=='row_missing':matrix.pop('variant')
    elif tamper=='arm_extra':matrix['extra']={}
    elif tamper=='mode_missing':matrix['original'].pop('on')
    elif tamper=='sender_bool':matrix['original']['on']['sender']=True
    elif tamper=='sender_drift':matrix['original']['on']['sender']=0
    elif tamper=='ingress_drift':matrix['variant']['off']['ingress']=1
    elif tamper=='repeat_false':matrix['variant']['on']['repeatability_identical']=False
    elif tamper=='hash_bad':matrix['original']['off']['result_sha256']='z'*64
    elif tamper=='row_extra':matrix['variant']['off']['foo']=3
    elif tamper=='proof_promoted':x['native_proof_obligations_unmet'][0]['verified']=True
    elif tamper=='proof_missing':x['native_proof_obligations_unmet'].pop()
    elif tamper=='case_missing':x['reference_lab_sessions'].pop()
    elif tamper=='case_duplicate':x['reference_lab_sessions'][1]=x['reference_lab_sessions'][0]
    elif tamper=='case_native_callback':x['reference_lab_sessions'][0]['native_scheduler_callback_calls']=1
    elif tamper=='case_judgment':x['reference_lab_sessions'][0]['receiver_view']['receiver_scored_judgment']=True
    elif tamper=='case_authority':x['reference_lab_sessions'][0]['receiver_view']['native_authority']=True
    elif tamper=='case_absence':x['reference_lab_sessions'][0]['receiver_view']['native_absence_certificate']=True
    elif tamper=='case_operator':x['reference_lab_sessions'][0]['receiver_view']['operator_update_committed']=True
    elif tamper=='case_no_ref_noninterference':x['reference_lab_sessions'][0]['reference_noninterference_equal_bytes']=False
    elif tamper=='case_wrong_plan':x['reference_lab_sessions'][0]['plan']='hook_verified'
    elif tamper=='noncanonical':
        with pytest.raises(InterventionError):check_x(x,canon(x)+b' ')
        return
    elif tamper=='w_hash_missing':x['reference_v1w_sha256']=''
    with pytest.raises((InterventionError,TypeError,KeyError)):check_x(x,canon(x))


@pytest.mark.parametrize('n',range(7))
def test_external_trace_actual_runtime_function(n):
    value=observed_pair(small_native,(n,),small_native,[small_native.__code__.co_firstlineno+2],1000)
    assert value['native_return_bytes_equal']
    assert value['no_probe_result_sha256']==value['probe_result_sha256']
    assert value['trace']['python_target_call_events']==1
    assert value['trace']['python_return_events']==1
    assert value['trace']['python_line_events']>=3
    assert value['trace']['semantic_spike_events_attested']==0
    assert value['trace']['native_B_packets_delivered']==0
    assert sys.gettrace() is None


def test_trace_callback_exception_restores_original():
    with pytest.raises(ValueError):
        with ScopedPythonProbe(small_native) as s:small_native(-1)
    assert s.restored and sys.gettrace() is None


def test_trace_refuses_nested_tracer():
    with ScopedPythonProbe(small_native):
        with pytest.raises(InterventionError):
            with ScopedPythonProbe(small_native):pass
    assert sys.gettrace() is None


def test_trace_rejects_budget_overflow():
    with pytest.raises(InterventionError):observed_pair(small_native,(6,),small_native,cap=2)
    assert sys.gettrace() is None


@pytest.mark.parametrize('bad',[-1,0,True,1.2,LIMIT+1])
def test_trace_invalid_quota(bad):
    with pytest.raises(InterventionError):ScopedPythonProbe(small_native,max_events=bad)


@pytest.mark.parametrize('bad',[(0,),('5',),[-1],None,{'hello':4}])
def test_trace_invalid_line_ids(bad):
    with pytest.raises(InterventionError):ScopedPythonProbe(small_native,bad)


def test_trace_return_mismatch_rejected():
    n=[0]
    def mutable():
        n[0]+=1
        return {'value':n[0]}
    with pytest.raises(InterventionError):observed_pair(mutable,(),mutable)
    assert sys.gettrace() is None


def test_probe_rejects_wrong_target():
    with pytest.raises(InterventionError):observed_pair(small_native,(3,),lambda:None)
    assert sys.gettrace() is None


def test_trace_handles_candidate_locations_as_hints():
    c=small_native.__code__.co_firstlineno
    result=observed_pair(small_native,(3,),small_native,(c+2,999999))
    assert result['trace']['candidate_line_hits']['999999']==0


@pytest.mark.parametrize('location',[
 'row_extra','row_missing','row_false','return_bad','lines_zero','trace_overflow',
 'trace_error','not_restored','outcome_changed','sha_tampered','fake_native_B',
])
def test_analyzer_rejects_incorrect_native_parity(location):
    x=xsource();native={}
    for arm in ('original','variant'):
        native[arm]={}
        for mode in ('off','on'):
            h=x['native_run_reference_matrix'][arm][mode]['result_sha256']
            native[arm][mode]={'no_probe_result_sha256':h,'probe_result_sha256':h,
              'native_return_bytes_equal':True,'trace':{'python_target_call_events':1,
                 'python_return_events':1,'python_line_events':4,'trace_overflow':False,
                 'trace_error':False,'trace_restored':True,
                 'semantic_spike_events_attested':0,'native_B_packets_delivered':0}}
    row=native['original']['off']; t=row['trace']
    if location=='row_extra':row['invented']=1
    elif location=='row_missing':native['variant'].pop('off')
    elif location=='row_false':row['native_return_bytes_equal']=False
    elif location=='return_bad':t['python_return_events']=0
    elif location=='lines_zero':t['python_line_events']=0
    elif location=='trace_overflow':t['trace_overflow']=True
    elif location=='trace_error':t['trace_error']=True
    elif location=='not_restored':t['trace_restored']=False
    elif location=='outcome_changed':row['probe_result_sha256']='f'*64
    elif location=='sha_tampered':row['no_probe_result_sha256']='a'*64
    elif location=='fake_native_B':t['native_B_packets_delivered']=1
    with pytest.raises(InterventionError):analyze(x,canon(x),native_pairs=native,source_rechecked=True)


def test_offline_contract_report_makes_no_native_claims():
    x=xsource();r=analyze(x,canon(x))
    assert r['native_probe_parity_matrix'] is None
    assert r['inherited_native_v1x_recomputation_verified_in_this_run'] is False
    assert r['native_scheduler_executions_with_trace_in_this_module']==0
    assert r['interpreter_tracing_observed_scheduler_during_native_execution'] is False
    assert all(not v['verified'] for v in r['native_proof_obligations_unmet'])
    assert all(r[k]==v for k,v in NATIVE_ZERO.items())
    with pytest.raises(InterventionError):analyze(x,canon(x),native_pairs={},source_rechecked=False)


def test_local_cli_contract_only(tmp_path):
    x=xsource();ref=tmp_path/'v1x.json';ref.write_bytes(canon(x))
    out=tmp_path/'v1y.json'
    assert main(['--v1x',str(ref),'--contract-only','--out',str(out)])==0
    o=json.loads(out.read_bytes())
    assert o['schema']==SCHEMA and o['status']==STATUS
    assert o['native_probe_parity_matrix'] is None
    assert o['reference_v1x_sha256']==sha256(canon(x)).hexdigest()


def test_local_cli_fail_closed(tmp_path):
    x=xsource();ref=tmp_path/'v1x.json';ref.write_bytes(canon(x))
    out=tmp_path/'v1y.json'
    assert main(['--v1x',str(ref),'--contract-only','--out',str(ref)])==2
    assert ref.read_bytes()==canon(x)
    assert main(['--v1x',str(ref),'--out',str(out)])==2
    assert not out.exists()
    assert main(['--v1x',str(ref),'--contract-only','--out',str(out)])==0
    assert main(['--v1x',str(ref),'--contract-only','--out',str(out)])==2


def test_local_cli_rejects_noncanonical(tmp_path):
    x=xsource();ref=tmp_path/'v1x.json';ref.write_bytes(canon(x)+b' ')
    out=tmp_path/'v1y.json'
    assert main(['--v1x',str(ref),'--contract-only','--out',str(out)])==2
    assert not out.exists()


def test_positive_bounded_native_pair_contract_without_promoting_authority():
    x=xsource()
    pairs={}
    for arm in ('original','variant'):
        pairs[arm]={}
        for mode in ('off','on'):
            h=x['native_run_reference_matrix'][arm][mode]['result_sha256']
            pairs[arm][mode]={'no_probe_result_sha256':h,
                'probe_result_sha256':h,'native_return_bytes_equal':True,
                'trace':{'python_target_call_events':1,'python_return_events':1,
                    'python_line_events':7,'trace_overflow':False,'trace_error':False,
                    'trace_restored':True,'semantic_spike_events_attested':0,
                    'native_B_packets_delivered':0}}
    report=analyze(x,canon(x),native_pairs=pairs,source_rechecked=True)
    assert report['native_scheduler_executions_with_trace_in_this_module']==4
    assert report['native_scheduler_executions_without_trace_in_this_module']==4
    assert report['interpreter_tracing_observed_scheduler_during_native_execution'] is True
    assert report['native_source_callback_invoked'] is False
    assert all(v['verified'] is False for v in report['native_proof_obligations_unmet'])
    assert report['source_owned_native_semantic_events_attested']==0
    assert report['native_receiver_B_control_messages']==0


@pytest.mark.parametrize('change',('valid','wrong_digest','raw_bytes_instead','missing_source','different_source'))
def test_native_pinned_source_bytes_vs_json_digest_map(change):
    blobs={'scheduler.py':b'unchanged scheduler native code'}
    hashes={'scheduler.py':sha256(blobs['scheduler.py']).hexdigest()}
    if change=='wrong_digest':hashes['scheduler.py']='0'*64
    elif change=='raw_bytes_instead':hashes['scheduler.py']=blobs['scheduler.py']
    elif change=='missing_source':hashes.clear()
    elif change=='different_source':blobs['scheduler.py']=b'drifted source'
    if change=='valid':assert verify_source_digest_map(blobs,hashes)
    else:
        with pytest.raises(InterventionError):verify_source_digest_map(blobs,hashes)


# v1y.1 FWORK HOTFIX: the frozen v1p/v1x matrix uses snapshot(result),
# which encodes Python types before hashing. The research report canon()
# deliberately uses a different, pretty-printed JSON representation.
@pytest.mark.parametrize('input_value',[0,1,3,8])
def test_hotfix_native_digest_matches_frozen_v1x_snapshot(input_value):
    expected=snapshot(small_native(input_value))
    assert expected != sha256(canon(small_native(input_value))).hexdigest()
    measured=observed_pair(small_native,(input_value,),small_native)
    assert measured['no_probe_result_sha256']==expected
    assert measured['probe_result_sha256']==expected
    assert measured['native_return_bytes_equal'] is True
    assert measured['trace']['trace_restored'] is True


def test_hotfix_native_snapshot_is_lossless_for_tuple_vs_list():
    runs=[0]
    def alters_container_type():
        runs[0]+=1
        return {'items':(7,8) if runs[0]==1 else [7,8]}
    # Legacy JSON canon() erases the list/tuple distinction and wrongly passes.
    assert canon({'items':(7,8)})==canon({'items':[7,8]})
    with pytest.raises(InterventionError,match='native result changed'):
        observed_pair(alters_container_type,(),alters_container_type)
    assert sys.gettrace() is None


def test_hotfix_same_payload_digest_does_not_use_pretty_json():
    value={'schema':'spk-bv-live-dual-event-scheduler/v0e',
           'enabled':False, 'policy':'forward-first',
           'forward':{'emissions':[], 'terminal':[]},
           'feedback':{'assessments':[]}}
    def frozen_shape():return value
    pair=observed_pair(frozen_shape,(),frozen_shape)
    assert pair['no_probe_result_sha256']==snapshot(value)
    assert pair['no_probe_result_sha256']!=sha256(canon(value)).hexdigest()
