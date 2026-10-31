"""Fail-closed native-v1y provenance, reference-v2a event model, CLI and safety."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import pytest

from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_external_probe_v1y import SCHEMA as Y_SCHEMA, STATUS as Y_STATUS
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS
from spk_bv_research.native_observer_v2_boundary_v1z import (
    SCHEMA, STATUS, CAP, PHASES, ProposalEvent, ReferenceProposalPort,
    verify_native_y, execute_reference_v2a, reference_pair, analyze,
)
from search.spk_bv_v1z_native_observer_admission import main


def predecessor_pair():
    matrix_x = {}
    matrix_y = {}
    for arm, count in (('original', 2), ('variant', 0)):
        matrix_x[arm], matrix_y[arm] = {}, {}
        for mode in ('off', 'on'):
            h = hashlib.sha256(f'{arm}.{mode}'.encode()).hexdigest()
            matrix_x[arm][mode] = {
                'sender': count, 'ingress': count,
                'repeatability_identical': True, 'result_sha256': h,
            }
            hits = {'49': 1, '50': 1, '150': 4 if arm=='original' and mode=='on' else 0,
                    '206': 2 if arm=='original' and mode=='on' else 0}
            lines = 1010 + sum(hits.values())
            matrix_y[arm][mode] = {
                'no_probe_result_sha256': h, 'probe_result_sha256': h,
                'native_return_bytes_equal': True,
                'trace': {
                    'candidate_line_hits': hits,
                    'scope': 'PYTHON_INTERPRETER_FUNCTION_CODE_OBJECT_ONLY',
                    'python_target_call_events': 1, 'python_return_events': 1,
                    'python_line_events': lines, 'trace_events_seen': lines+2,
                    'trace_overflow': False, 'trace_error': False,
                    'trace_restored': True,
                    'semantic_spike_events_attested': 0,
                    'native_B_packets_delivered': 0,
                },
            }
    x = {'native_run_reference_matrix': matrix_x, 'reference_v1w_sha256': 'a'*64}
    y = {
        'schema': Y_SCHEMA, 'status': Y_STATUS,
        'source_kind': 'FROZEN_NATIVE_EXECUTION_EXTERNAL_PYTHON_PROBE',
        'source_pins_rechecked_in_this_run': True,
        'source_files_modified': False,
        'inherited_native_v1x_recomputation_verified_in_this_run': True,
        'interpreter_tracing_observed_scheduler_during_native_execution': True,
        'native_scheduler_executions_without_trace_in_this_module': 4,
        'native_scheduler_executions_with_trace_in_this_module': 4,
        'native_source_callback_invoked': False,
        'runtime_listener_interface_installed': False,
        'native_observer_ON_source_owned_mode_executed': False,
        'native_receiver_B_control_messages': 0,
        'native_producer_owned_observer_callback_calls': 0,
        'native_authenticated_producer_evidence': 0,
        'native_independent_absence_certificates': 0,
        'native_scored_receiver_judgments': 0,
        'native_operator_updates': 0,
        'native_learning_proven': False,
        'native_value_criterion_identified': False,
        'probe_has_independent_clock_or_coverage': False,
        'source_owned_native_semantic_events_attested': 0,
        'native_proof_obligations_unmet': [{'id':k,'verified':False} for k,_ in PORT_OBLIGATIONS],
        'reference_v1w_sha256': 'a'*64,
        'native_probe_parity_matrix': matrix_y,
    }
    y['reference_v1x_sha256'] = hashlib.sha256(canon(x)).hexdigest()
    return y, x


def test_source_bound_minimal_predecessor():
    y, x = predecessor_pair()
    assert verify_native_y(y, canon(y), x, canon(x)) is True


@pytest.mark.parametrize('field, value', [
    ('schema','pretend-native'),('status','NATIVE_BV_COMPLETE'),
    ('source_kind','NATIVE_PRODUCER_CALLBACK'),
    ('source_pins_rechecked_in_this_run',False),
    ('inherited_native_v1x_recomputation_verified_in_this_run',False),
    ('interpreter_tracing_observed_scheduler_during_native_execution',False),
    ('native_scheduler_executions_without_trace_in_this_module',3),
    ('native_scheduler_executions_with_trace_in_this_module',5),
    ('native_source_callback_invoked',True),
    ('native_observer_ON_source_owned_mode_executed',True),
    ('runtime_listener_interface_installed',True),
    ('native_receiver_B_control_messages',1),
    ('native_producer_owned_observer_callback_calls',1),
    ('native_authenticated_producer_evidence',1),
    ('native_independent_absence_certificates',1),
    ('native_scored_receiver_judgments',1),
    ('native_operator_updates',1),
    ('native_learning_proven',True),
    ('native_value_criterion_identified',True),
    ('probe_has_independent_clock_or_coverage',True),
    ('source_owned_native_semantic_events_attested',1),
    ('source_files_modified',True),
    ('reference_v1x_sha256','0'*64),
    ('reference_v1w_sha256','0'*64),
])
def test_native_promotion_refused(field, value):
    y, x = predecessor_pair()
    y[field] = value
    with pytest.raises(InterventionError): verify_native_y(y,canon(y),x,canon(x))


@pytest.mark.parametrize('corruption', [
    'missing_row','new_row','missing_mode','ref_sender','ref_ingress','ref_repeat',
    'digest_wrong','digest_bad_v1x','bytes_false','hits_missing','hits_negative',
    'hits_source_change','trace_scope','trace_calls','trace_return',
    'trace_line_zero','trace_count_wrong','trace_overflow','trace_error',
    'trace_not_restored','native_packets','semantic_spikes','proof_omitted',
    'proof_promoted','uncanonical_y','uncanonical_x',
])
def test_corrupt_native_trace_refused(corruption):
    y, x = predecessor_pair()
    r = y['native_probe_parity_matrix']['original']['on']
    t = r['trace']
    if corruption == 'missing_row': y['native_probe_parity_matrix'].pop('variant')
    elif corruption == 'new_row': y['native_probe_parity_matrix']['x'] = {}
    elif corruption == 'missing_mode': y['native_probe_parity_matrix']['variant'].pop('on')
    elif corruption == 'ref_sender': x['native_run_reference_matrix']['original']['off']['sender'] = 3
    elif corruption == 'ref_ingress': x['native_run_reference_matrix']['variant']['on']['ingress'] = 1
    elif corruption == 'ref_repeat': x['native_run_reference_matrix']['variant']['on']['repeatability_identical'] = False
    elif corruption == 'digest_wrong': r['probe_result_sha256'] = '0'*64
    elif corruption == 'digest_bad_v1x': x['native_run_reference_matrix']['original']['on']['result_sha256'] = '0'*64
    elif corruption == 'bytes_false': r['native_return_bytes_equal'] = False
    elif corruption == 'hits_missing': t['candidate_line_hits'].pop('150')
    elif corruption == 'hits_negative': t['candidate_line_hits']['206'] = -1
    elif corruption == 'hits_source_change': t['candidate_line_hits']['206'] = 0
    elif corruption == 'trace_scope': t['scope'] = 'NATIVE_SEMANTIC_SOURCE'
    elif corruption == 'trace_calls': t['python_target_call_events'] = 0
    elif corruption == 'trace_return': t['python_return_events'] = 0
    elif corruption == 'trace_line_zero': t['python_line_events'] = 0
    elif corruption == 'trace_count_wrong': t['trace_events_seen'] += 1
    elif corruption == 'trace_overflow': t['trace_overflow'] = True
    elif corruption == 'trace_error': t['trace_error'] = True
    elif corruption == 'trace_not_restored': t['trace_restored'] = False
    elif corruption == 'native_packets': t['native_B_packets_delivered'] = 1
    elif corruption == 'semantic_spikes': t['semantic_spike_events_attested'] = 2
    elif corruption == 'proof_omitted': y['native_proof_obligations_unmet'].pop()
    elif corruption == 'proof_promoted': y['native_proof_obligations_unmet'][0]['verified'] = True
    elif corruption == 'uncanonical_y':
        with pytest.raises(InterventionError): verify_native_y(y,canon(y)+b' ',x,canon(x))
        return
    elif corruption == 'uncanonical_x':
        with pytest.raises(InterventionError): verify_native_y(y,canon(y),x,canon(x)+b' ')
        return
    with pytest.raises(InterventionError): verify_native_y(y,canon(y),x,canon(x))


@pytest.mark.parametrize('seed,count', [(0,3),(1,5),(2,7)])
def test_non_native_reference_port(seed,count):
    seen = []
    result = reference_pair(seed,seen.append)
    assert result['reference_result_bytes_equal']
    assert result['port']['events'] == count
    assert result['port']['native_receiver_packets'] == 0
    assert result['port']['native_absence_certificates'] == 0
    assert result['port']['is_native_source_observer'] is False
    assert all(type(e) is ProposalEvent for e in seen)
    assert [e.ordinal for e in seen] == list(range(count))
    assert execute_reference_v2a(seed=seed) == execute_reference_v2a(seed=seed)


def test_listener_raises_and_forward_does_not_change():
    def failure(event): raise RuntimeError('sink fault')
    rec = reference_pair(2,failure)
    assert rec['reference_result_bytes_equal'] is True
    assert rec['port']['listener_failed'] is True
    assert rec['port']['events'] == 7


@pytest.mark.parametrize('episode,sink,capacity', [('',None,CAP),('x'*97,None,CAP),
    ('e',None,0),('e',None,CAP+1),('e',3,CAP),('e',None,True)])
def test_bad_port_parameters(episode,sink,capacity):
    with pytest.raises(InterventionError): ReferenceProposalPort(episode,sink,capacity)


@pytest.mark.parametrize('bad', [
    'phase','source','target','tick_negative','tick_bool','decision_blank','late_close',
    'repeat_tick','missing_expectation','missing_decision','cross_decision',
    'source_type','recipient_type',
])
def test_bad_phase_or_identity(bad):
    p = ReferenceProposalPort('episode')
    good = dict(source='A',target='B',tick=0,phase='predecision_expectation',decision='decision-1')
    if bad=='phase': good['phase']='native_authenticated_absence'
    elif bad=='source':good['source']='X'
    elif bad=='target':good['target']='C'
    elif bad=='tick_negative':good['tick']=-1
    elif bad=='tick_bool':good['tick']=True
    elif bad=='decision_blank':good['decision']=''
    elif bad=='missing_expectation':good['phase']='decision'
    elif bad=='missing_decision':good['phase']='sender_port_emission'
    elif bad=='source_type':good['source']=1
    elif bad=='recipient_type':good['target']=None
    elif bad=='late_close':
        reference_pair(0)
        p.emit(**good)
        p.emit(source='A',target='B',tick=1,phase='decision',decision='decision-1')
        p.emit(source='A',target='B',tick=2,phase='interval_coverage_close',decision='decision-1')
        good['tick']=3
    elif bad=='repeat_tick':
        p.emit(**good)
    elif bad=='cross_decision':
        p.emit(**good)
        good['phase']='decision';good['decision']='different';good['tick']=1
    with pytest.raises(InterventionError): p.emit(**good)


def test_reference_requires_close():
    p=ReferenceProposalPort('e')
    p.emit(source='A',target='B',tick=0,phase='predecision_expectation',decision='d')
    with pytest.raises(InterventionError):p.seal()


def test_reference_capacity_fails_closed():
    with pytest.raises(InterventionError):reference_pair(2,capacity=3)


def test_reference_invalid_seed():
    for s in (3,-1,True,'2',None):
        with pytest.raises(InterventionError): reference_pair(s)


def test_analyze_negative_authority():
    y,x=predecessor_pair()
    result=analyze(y,canon(y),x,canon(x))
    assert result['status']==STATUS and result['schema']==SCHEMA
    assert result['native_gate_status']=='BLOCKED_VERSIONED_NATIVE_EXECUTOR_NOT_PRESENT'
    assert result['new_native_scheduler_executions_in_this_module']==0
    assert result['native_B_control_messages_received']==0
    assert result['inherited_native_v1y_recomputation_verified_in_this_run'] is False
    assert all(not z['verified'] for z in result['native_promotion_obligations_unmet'])


def test_cli_canonical_output_and_existing_output_refusal(tmp_path):
    y,x=predecessor_pair()
    yfile=tmp_path/'sourcey.json';xfile=tmp_path/'sourcex.json';out=tmp_path/'out.json'
    yfile.write_bytes(canon(y));xfile.write_bytes(canon(x))
    root=Path(__file__).resolve().parents[1]
    cmd=['--root',str(root),'--v1y',str(yfile),'--v1x',str(xfile),'--out',str(out)]
    assert main(cmd)==0
    assert out.read_bytes()==canon(json.loads(out.read_bytes()))
    assert main(cmd)==2


def test_cli_rejects_alias_and_symlink(tmp_path):
    y,x=predecessor_pair(); root=Path(__file__).resolve().parents[1]
    yfile=tmp_path/'y'; yfile.write_bytes(canon(y))
    symlink=tmp_path/'link';symlink.symlink_to(yfile)
    cmd=['--root',str(root),'--v1y',str(yfile),'--v1x',str(symlink),'--out',str(tmp_path/'out')]
    assert main(cmd)==2
    cmd[5]=str(yfile)
    assert main(cmd)==2
