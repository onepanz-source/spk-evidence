"""Independent bounded v2a execution semantics, event evidence, fail-closed CLI."""
from __future__ import annotations
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path
import copy
import json
import pytest

from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObservationV2a, ObserverV2a, V2aBoundaryError,
    execute_live_v2a, MAX_OBSERVATIONS, PORT_VERSION, PHASES,
)
from spk_bv_research.versioned_executor_admission_v2a import (
    OPERATORS, EXPECTED, SCHEMA, STATUS, SOURCE_KIND, paired_case,
    assert_observation_stream, validate_z, analyze,
)
from spk_bv_research.native_observer_v2_boundary_v1z import (
    analyze as create_z, CAP,
)
from spk_bv_research.native_external_probe_v1y import SCHEMA as Y_SCHEMA, STATUS as Y_STATUS
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_capture_v0k import canonical_fixture, _json_bytes
from search.spk_bv_v2a_versioned_executor import main


def predecessors():
    """Self-contained synthetic native-report fixtures (never native evidence)."""
    xmatrix, ymatrix = {}, {}
    for arm, n in [('original',2),('variant',0)]:
        xmatrix[arm],ymatrix[arm] = {},{}
        for mode in ('off','on'):
            digest=sha256(f'{arm}/{mode}'.encode()).hexdigest()
            xmatrix[arm][mode] = {'sender': n, 'ingress': n,
                'repeatability_identical': True, 'result_sha256': digest}
            hits={'49':1,'50':1,'150':4 if arm=='original' and mode=='on' else 0,
                  '206':2 if arm=='original' and mode=='on' else 0}
            ymatrix[arm][mode] = {'no_probe_result_sha256':digest,
                'probe_result_sha256':digest,'native_return_bytes_equal':True,
                'trace':{'candidate_line_hits':hits,
                         'scope':'PYTHON_INTERPRETER_FUNCTION_CODE_OBJECT_ONLY',
                         'python_target_call_events':1,'python_return_events':1,
                         'python_line_events':1100,'trace_events_seen':1102,
                         'trace_overflow':False,'trace_error':False,
                         'trace_restored':True,'semantic_spike_events_attested':0,
                         'native_B_packets_delivered':0}}
    x={'native_run_reference_matrix':xmatrix,'reference_v1w_sha256':'a'*64}
    y={'schema':Y_SCHEMA,'status':Y_STATUS,
       'source_kind':'FROZEN_NATIVE_EXECUTION_EXTERNAL_PYTHON_PROBE',
       'source_pins_rechecked_in_this_run':True,
       'source_files_modified':False,
       'inherited_native_v1x_recomputation_verified_in_this_run':True,
       'interpreter_tracing_observed_scheduler_during_native_execution':True,
       'native_scheduler_executions_without_trace_in_this_module':4,
       'native_scheduler_executions_with_trace_in_this_module':4,
       'native_source_callback_invoked':False,
       'runtime_listener_interface_installed':False,
       'native_observer_ON_source_owned_mode_executed':False,
       'native_receiver_B_control_messages':0,
       'native_producer_owned_observer_callback_calls':0,
       'native_authenticated_producer_evidence':0,
       'native_independent_absence_certificates':0,
       'native_scored_receiver_judgments':0,
       'native_operator_updates':0,'native_learning_proven':False,
       'native_value_criterion_identified':False,
       'probe_has_independent_clock_or_coverage':False,
       'source_owned_native_semantic_events_attested':0,
       'native_proof_obligations_unmet':[{'id':k,'verified':False} for k,_ in PORT_OBLIGATIONS],
       'reference_v1w_sha256':'a'*64,
       'native_probe_parity_matrix':ymatrix}
    y['reference_v1x_sha256']=sha256(canon(x)).hexdigest()
    z=create_z(y,canon(y),x,canon(x))
    return z,y,x


@pytest.mark.parametrize('name,ops', OPERATORS.items())
@pytest.mark.parametrize('bv', [False,True])
def test_micro_real_execution_parity(name,ops,bv):
    c=BoundedCaseV2a('ep.'+name, (1,1),ops,bv)
    result=paired_case(c)
    assert result['observer_off_on_result_bytes_equal'] is True
    assert tuple(result['forward_emissions'][n] for n in 'ABC')==EXPECTED[name]
    assert result['observer']['complete']
    assert result['observer']['events_offered']==result['logical_events']
    assert result['observer']['native_receiver_B_control_messages']==0
    assert result['observer']['authentication_verified'] is False


@pytest.mark.parametrize('number', list(range(1,17)))
def test_bounded_input_cardinality(number):
    c=BoundedCaseV2a('cardinality', (1,)*number, ('relay','pair','relay'))
    result=paired_case(c)
    assert result['forward_emissions']['A']==number
    assert result['forward_emissions']['B']==number//2
    assert result['forward_emissions']['C']==number//2


@pytest.mark.parametrize('bad', [
    'bad_episode','bad_operators','bad_operator_code','list_operators',
    'bool_stimulus','empty_stimulus','many_stimuli','nonone_stimulus',
    'list_stimuli','bv_string','bad_case','long_episode','unicode_episode',
])
def test_invalid_micro_input_refused(bad):
    c=BoundedCaseV2a('valid',(1,1),('relay','relay','relay'))
    if bad=='bad_episode':c=replace(c,episode='')
    elif bad=='long_episode':c=replace(c,episode='a'*73)
    elif bad=='unicode_episode':c=replace(c,episode='é')
    elif bad=='bad_operators':c=replace(c,operators=('relay','relay'))
    elif bad=='bad_operator_code':c=replace(c,operators=('relay','CMP','relay'))
    elif bad=='list_operators':c=replace(c,operators=['relay','relay','relay'])
    elif bad=='bool_stimulus':c=replace(c,stimuli=(True,))
    elif bad=='empty_stimulus':c=replace(c,stimuli=())
    elif bad=='many_stimuli':c=replace(c,stimuli=(1,)*17)
    elif bad=='nonone_stimulus':c=replace(c,stimuli=(2,))
    elif bad=='list_stimuli':c=replace(c,stimuli=[1,1])
    elif bad=='bv_string':c=replace(c,bv_enabled='on')
    else:c=object()
    with pytest.raises(V2aBoundaryError):execute_live_v2a(c)


@pytest.mark.parametrize('capacity',[1,2,3,4,8,12])
def test_overflow_does_not_change_forward(capacity):
    c=BoundedCaseV2a('overflow',(1,1),('relay','relay','relay'))
    before=execute_live_v2a(c)
    p=ObserverV2a(capacity=capacity)
    after=execute_live_v2a(c,observation_port=p)
    assert before==after
    assert p.overflow and not p.summary()['complete']
    assert p.summary()['records_retained']==capacity
    assert p.summary()['events_offered']>capacity
    assert not p._attached


def test_sink_throws_without_forward_mutation():
    c=BoundedCaseV2a('fault',(1,1),('relay','relay','relay'))
    seen=[]
    def fail(ev):
        seen.append(ev)
        raise RuntimeError('observer failure')
    p=ObserverV2a(fail)
    assert execute_live_v2a(c,observation_port=p)==execute_live_v2a(c)
    assert p.sink_fault and len(seen)==1 and not p._attached
    assert not p.summary()['complete']


def test_immutable_event_and_live_happens_before():
    c=BoundedCaseV2a('live',(1,1),('relay','relay','relay'))
    seen=[]
    def sink(ev):
        assert ev.ordinal == len(seen)
        with pytest.raises(FrozenInstanceError):ev.phase='faked'
        seen.append(ev)
    p=ObserverV2a(sink)
    output=execute_live_v2a(c,observation_port=p)
    assert len(seen)>0 and len(seen)==output['logical_event_count']
    assert_observation_stream(c,p,output)
    assert [e.phase for e in seen if e.actor=='A'][:2]==['predecision_expectation','decision']


@pytest.mark.parametrize('capacity,sink', [(0,None),(-1,None),
    (MAX_OBSERVATIONS+1,None),(True,None),(2,'oops')])
def test_invalid_observer_setup(capacity,sink):
    with pytest.raises(V2aBoundaryError):ObserverV2a(sink,capacity)


def test_observer_cannot_be_reused_or_injected_while_active():
    case=BoundedCaseV2a('replay',(1,1),('relay','relay','relay'))
    p=ObserverV2a()
    execute_live_v2a(case,observation_port=p)
    with pytest.raises(V2aBoundaryError):execute_live_v2a(case,observation_port=p)
    with pytest.raises(V2aBoundaryError):p._publish(object())
    with pytest.raises(V2aBoundaryError):execute_live_v2a(case,observation_port=lambda _:None)


@pytest.mark.parametrize('alteration',[ 'remove_event','change_phase','tamper_episode',
    'tamper_ordinal','tamper_tick','forge_parent','duplicate_emission','change_actor',
    'missing_close','duplicate_close','tamper_result','tamper_route'])
def test_observer_stream_consistency_fail_closed(alteration):
    case=BoundedCaseV2a('tamper',(1,1),('relay','relay','relay'))
    p=ObserverV2a()
    out=execute_live_v2a(case,observation_port=p)
    if alteration=='remove_event':p.events.pop(1)
    elif alteration=='change_phase':p.events[0]=replace(p.events[0],phase='receiver_ingress')
    elif alteration=='tamper_episode':p.events[0]=replace(p.events[0],episode='alien')
    elif alteration=='tamper_ordinal':p.events[1]=replace(p.events[1],ordinal=99)
    elif alteration=='tamper_tick':p.events[1]=replace(p.events[1],logical_tick=1)
    elif alteration=='forge_parent':
        i=next(i for i,e in enumerate(p.events) if e.phase=='receiver_ingress')
        p.events[i]=replace(p.events[i],parent_token='forgery')
    elif alteration=='duplicate_emission':
        indices=[i for i,e in enumerate(p.events) if e.phase=='sender_port_emission']
        p.events[indices[1]]=replace(p.events[indices[1]],event_token=p.events[indices[0]].event_token)
    elif alteration=='change_actor':
        i=next(i for i,e in enumerate(p.events) if e.phase=='sender_port_emission')
        p.events[i]=replace(p.events[i],actor='X')
    elif alteration=='missing_close':p.events.pop()
    elif alteration=='duplicate_close':p.events[-2]=replace(p.events[-2],phase='interval_coverage_close')
    elif alteration=='tamper_result':out['forward_emissions']['A']+=1
    else:out['forward_routes']['A->B']+=1
    with pytest.raises((AssertionError,ValueError)):
        assert_observation_stream(case,p,out)


def test_predecessor_lineage_recomputable():
    z,y,x=predecessors()
    assert validate_z(z,canon(z),y,canon(y),x,canon(x))
    report=analyze(z,canon(z),y,canon(y),x,canon(x),
                   executor_sha256='a'*64)
    assert report['schema']==SCHEMA and report['status']==STATUS
    assert report['source_kind']==SOURCE_KIND
    assert report['micro_executor_pairs']==8
    assert not report['frozen_native_forward_equivalence_proven']
    assert not report['native_frozen_scheduler_observer_connected']
    assert report['native_recipient_B_received_control_messages']==0
    assert all(o['verified'] is False for o in report['ten_native_promotion_obligations_unmet'])


@pytest.mark.parametrize('fault', ['z_status','z_digest','z_tamper','z_noncanonical',
                                  'y_promote','x_count','z_promote','z_missing'])
def test_predecessor_forgery_rejected(fault):
    z,y,x=predecessors()
    if fault=='z_status':z['status']='NATIVE_V2A_PROMOTED'
    elif fault=='z_digest':z['reference_v1y_sha256']='0'*64
    elif fault=='z_tamper':z['reference_executor_examples'][0]['port']['events']=99
    elif fault=='z_noncanonical':
        with pytest.raises(Exception):validate_z(z,canon(z)+b' ',y,canon(y),x,canon(x))
        return
    elif fault=='y_promote':y['native_B_control_messages_received']=1
    elif fault=='x_count':x['native_run_reference_matrix']['original']['off']['sender']=3
    elif fault=='z_promote':z['native_promotion_obligations_unmet'][0]['verified']=True
    elif fault=='z_missing':z.pop('native_gate_status')
    with pytest.raises(Exception):validate_z(z,canon(z),y,canon(y),x,canon(x))


def test_cli_offline_against_synthetic_predecessor(tmp_path):
    z,y,x=predecessors()
    root=tmp_path/'repo';root.mkdir()
    target=root/'spk_backvalidation_v2'/'observed_scheduler_v2a.py'
    target.parent.mkdir()
    target.write_text('# unit-test contract copy\n')
    files=[]
    for name,doc in (('v1z',z),('v1y',y),('v1x',x)):
        f=tmp_path/(name+'.json');f.write_bytes(canon(doc));files.append(str(f))
    out=tmp_path/'result.json'
    cmd=['--root',str(root),'--v1z',files[0], '--v1y',files[1],
         '--v1x',files[2],'--out',str(out),'--contract-only']
    assert main(cmd)==0
    r=json.loads(out.read_bytes())
    assert r['frozen_native_source_pins_rechecked_in_this_run'] is False
    assert r['micro_executor_pairs']==8
    assert main(cmd)==2 # never overwrite


@pytest.mark.parametrize('fault',['missing_source','source_symlink','input_symlink',
                                 'output_inside_root','input_inside_root','missing_pins'])
def test_cli_boundaries(tmp_path,fault):
    z,y,x=predecessors()
    root=tmp_path/'repo';root.mkdir()
    module=root/'spk_backvalidation_v2'/'observed_scheduler_v2a.py'
    module.parent.mkdir()
    module.write_text('# copied micro-executor source\n')
    files=[]
    for name,doc in (('v1z',z),('v1y',y),('v1x',x)):
        p=tmp_path/(name+'.json');p.write_bytes(canon(doc));files.append(p)
    out=tmp_path/'result.json'
    cmd=['--root',str(root),'--v1z',str(files[0]),'--v1y',str(files[1]),
         '--v1x',str(files[2]),'--out',str(out),'--contract-only']
    if fault=='missing_source':module.unlink()
    elif fault=='source_symlink':
        module.unlink();module.symlink_to(files[0])
    elif fault=='input_symlink':
        new=tmp_path/'alias';new.symlink_to(files[0]);cmd[3]=str(new)
    elif fault=='output_inside_root':cmd[-2]=str(root/'output.json')
    elif fault=='input_inside_root':
        internal=root/'v1z.json';internal.write_bytes(files[0].read_bytes());cmd[3]=str(internal)
    elif fault=='missing_pins':cmd.remove('--contract-only')
    assert main(cmd)==2
    assert not out.exists()
