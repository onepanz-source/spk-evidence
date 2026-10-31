"""v1x reference observation-port conformance tests: NO native hook claims."""
from __future__ import annotations
import copy, json
from hashlib import sha256
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
import spk_bv_research.reference_observation_port_v1x as mod
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS, EXPECTED_PINS
from search.spk_bv_v1x_reference_observation_port import main, NAMES


def sample_w():
    names={'back_validation':2,'forward_route':0,'receiver_ingress':2,
           'scheduler_batch':0,'sender_emission':0}
    return {'schema':mod.W_SCHEMA,'status':mod.W_STATUS,
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


def test_valid_canonical_source():
    w=sample_w()
    assert mod.check_predecessor(w,canon(w)) is True
    assert len(mod.PORT_OBLIGATIONS)==10


@pytest.mark.parametrize('field,invalid',[
  ('schema','bogus'),('status','ACTIVE'),('source_kind','LIVE'),
  ('native_source_readonly_bytes_rechecked_in_this_run',False),
  ('inherited_native_v1v_recomputation_verified_in_this_run',False),
  ('source_files_modified',True),('native_event_callback_invoked',True),
  ('native_observation_message_delivered_to_B',True),
  ('native_authenticated_absence_coverage',True),
  ('native_receiver_scored_judgments',1),('native_operator_updates',1),
  ('native_learning_proven',True),('new_native_scheduler_executions_in_this_module',1),
  ('postreturn_trace_is_online_native_evidence',True),
  ('static_candidate_is_runtime_event_hook',True),
  ('design_port_name_only','native/hook-installed'),
  ('integration_path_selection','INSTALLED'),('reference_v1v_sha256','a'),
])
def test_refuses_warrantless_promotion(field,invalid):
    w=sample_w();w[field]=invalid
    with pytest.raises(InterventionError):mod.check_predecessor(w,canon(w))


@pytest.mark.parametrize('where',[
  'signature_name','signature_args','signature_callback','signature_yield',
  'proof_promoted','proof_missing','bad_category','bad_candidate',
  'bad_pin','fake_hook','source_declared','no_ast','too_many_sites',
  'bad_ref_format','missing_candidate_category',
])
def test_adversarial_w_reports(where):
    w=sample_w(); c=w['source_pinned_static_candidate_inventory']
    if where=='signature_name':w['confirmed_frozen_scheduler_signature']['name']='execute_streaming'
    elif where=='signature_args':w['confirmed_frozen_scheduler_signature']['positional'].append('callback')
    elif where=='signature_callback':w['confirmed_frozen_scheduler_signature']['possible_callback_name_hints']=['on_event']
    elif where=='signature_yield':w['confirmed_frozen_scheduler_signature']['generator_body_has_yield']=True
    elif where=='proof_promoted':w['proof_obligations_unmet'][0]['verified']=True
    elif where=='proof_missing':w['proof_obligations_unmet'].pop()
    elif where=='bad_category':c['candidate_count_by_category']['sender_emission']=1
    elif where=='bad_candidate':c['bounded_callsite_examples']['receiver_ingress'][0]['verified_hook']=True
    elif where=='bad_pin':c['source_file_sha256']['spk_architecture_v1/pe_execution_v1b.py']='0'*64
    elif where=='fake_hook':c['native_listener_or_callback_installed']=True
    elif where=='source_declared':c['candidate_extraction']='NATIVE_EXECUTED'
    elif where=='no_ast':c['native_event_semantics_established']=True
    elif where=='too_many_sites':c['bounded_callsite_examples']['receiver_ingress'].append({'verified_hook':False})
    elif where=='bad_ref_format':w['reference_v1v_sha256']=4
    elif where=='missing_candidate_category':c['bounded_callsite_examples'].pop('forward_route')
    with pytest.raises((InterventionError,KeyError,TypeError)):
        mod.check_predecessor(w,canon(w))


@pytest.mark.parametrize('case',mod.CASES)
def test_reference_noninterference_all_cases(case):
    for n in (0,1,2):
        o=mod.lab_episode(n,n,case)
        assert o['reference_noninterference_equal_bytes'] is True
        assert o['native_scheduler_callback_calls']==0
        assert o['source_owned_during_reference_execution'] is True
        assert o['receiver_view']['native_authority'] is False
        assert o['reference_callback_calls']==5+n


@pytest.mark.parametrize('case',mod.CASES)
def test_reference_zero_is_not_native_judgment(case):
    o=mod.lab_episode(0,0,case)
    assert o['receiver_view']['native_authority'] is False
    assert o['receiver_view']['receiver_scored_judgment'] is False
    assert o['receiver_view']['operator_update_committed'] is False
    assert o['receiver_view']['native_absence_certificate'] is False


@pytest.mark.parametrize('case,expected',[
  ('no_listener','NO_DELIVERED_EXPECTATION_UNKNOWN'),
  ('all_delivered','LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY'),
  ('sender_report_lost','INCOMPLETE_LAB_EVIDENCE_UNKNOWN'),
  ('expectation_lost','NO_DELIVERED_EXPECTATION_UNKNOWN'),
  ('coverage_lost','INCOMPLETE_LAB_EVIDENCE_UNKNOWN'),
  ('decision_lost','LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY'),
  ('channel_fault','NO_DELIVERED_EXPECTATION_UNKNOWN'),
  ('queue_overflow','CONTROL_OVERFLOW_UNKNOWN'),
  ('raising_listener','NO_DELIVERED_EXPECTATION_UNKNOWN'),
])
def test_fail_closed_zero_event_cases(case,expected):
    assert mod.lab_episode(0,0,case)['receiver_view']['classification']==expected


@pytest.mark.parametrize('case',('forged','replayed','wrong_episode','wrong_receiver','late','cross_world'))
def test_untrusted_packets_rejected(case):
    o=mod.lab_episode(2,2,case)
    assert o['lab_rejected_packets']>=1
    assert o['receiver_view']['native_authority'] is False


def test_original_and_variant_no_implicit_shared_event():
    assert mod.lab_episode(2,2,'all_delivered', 'lab.v1x.original.off')['receiver_view']['classification']=='LAB_INGRESS_OBSERVED'
    assert mod.lab_episode(0,0,'all_delivered','lab.v1x.variant.off')['receiver_view']['classification']=='LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY'


def test_interference_from_adversarial_callback_is_swallowed():
    x=[]
    def observer(*values):
        x.append(values)
        raise ValueError('listener error')
    assert mod.reference_execute(2,2,observer)==mod.reference_execute(2,2,None)
    assert len(x)==7


@pytest.mark.parametrize('sender,ingress',[(True,1),(-1,0),(17,17),(0,1),(2,-1),(2,3),(1,False)])
def test_invalid_reference_counts(sender,ingress):
    with pytest.raises(InterventionError):mod.reference_execute(sender,ingress)


def test_mailbox_sender_identity_episode_and_order():
    cap=object(); mailbox=mod.Mailbox('lab.v1x.original.off',cap)
    first=mod.Record(mod.PORT,'lab.v1x.original.off','B','expectation',0,0,2,cap)
    assert mailbox.deliver(first)
    assert mailbox.deliver(first) is False
    assert mailbox.deliver(mod.Record(mod.PORT,'lab.v1x.variant.off','B','decision',1,1,0,cap)) is False
    assert mailbox.deliver(mod.Record(mod.PORT,'lab.v1x.original.off','C','decision',1,1,0,cap)) is False
    assert mailbox.deliver(mod.Record('wrong','lab.v1x.original.off','B','decision',1,1,0,cap)) is False
    assert mailbox.deliver(mod.Record(mod.PORT,'lab.v1x.original.off','B','decision',1,1,0,object())) is False
    assert mailbox.deliver(mod.Record(mod.PORT,'lab.v1x.original.off','B','decision',1,1,0,cap))
    assert mailbox.rejected==5


def test_predecessor_bound_offline_audit():
    w=sample_w(); r=mod.analyze(w,canon(w))
    assert r['reference_v1w_sha256']==sha256(canon(w)).hexdigest()
    assert r['native_scheduler_executions_in_this_module']==0
    assert r['native_results_repeated_without_observer'] is False
    assert r['source_kind']=='PREDECESSOR_BOUND_REFERENCE_PORT_ONLY'
    assert r['reference_lab_session_count']==64
    assert r['native_callback_connected'] is False
    assert not any(x['verified'] for x in r['native_proof_obligations_unmet'])
    assert all(x['reference_noninterference_equal_bytes'] for x in r['reference_lab_sessions'])


def test_reference_only_cli(tmp_path,monkeypatch,capsys):
    root=tmp_path/'repo'; root.mkdir();inputs=tmp_path/'refs';inputs.mkdir()
    monkeypatch.chdir(root)
    p=inputs/'w.json';p.write_bytes(canon(sample_w()))
    out=tmp_path/'out.json'
    assert main(['--root',str(root),'--v1w',str(p),'--out',str(out),'--reference-only'])==0
    obj=json.loads(out.read_bytes());assert obj['reference_lab_session_count']==64
    assert obj['inherited_native_v1w_recomputation_verified_in_this_run'] is False
    assert main(['--root',str(root),'--v1w',str(p),'--out',str(out),'--reference-only'])==2
    assert out.read_bytes()==canon(obj)


def test_cli_rejects_source_inside_repo(tmp_path):
    root=tmp_path/'repo';root.mkdir();w=root/'w.json';w.write_bytes(canon(sample_w()))
    assert main(['--root',str(root),'--v1w',str(w),'--out',str(tmp_path/'outside.json'),
                 '--reference-only'])==2
    assert not (tmp_path/'outside.json').exists()


def test_cli_requires_entire_chain_for_native_mode(tmp_path):
    root=tmp_path/'repo';root.mkdir();w=tmp_path/'w.json';w.write_bytes(canon(sample_w()))
    assert main(['--root',str(root),'--v1w',str(w),'--out',str(tmp_path/'outside.json')])==2


def test_native_reference_matrix_is_not_hook_proof():
    w=sample_w()
    matrix={a:{m:{'sender':2 if a=='original' else 0,'ingress':2 if a=='original' else 0,
                  'result_sha256':'1'*64,'repeatability_identical':True}
               for m in ('on','off')} for a in ('original','variant')}
    r=mod.analyze(w,canon(w),native_reference=matrix,source_rechecked=True)
    assert r['native_scheduler_executions_in_this_module']==8
    assert r['native_results_repeated_without_observer'] is True
    assert r['native_baseline_equal_bytes_not_observer_on_off_proof'] is True
    assert r['native_observer_enabled_mode_executed'] is False
    assert r['native_receiver_B_received_control_messages']==0
    assert r['inherited_native_v1w_recomputation_verified_in_this_run'] is False


@pytest.mark.parametrize('change',('missing','promote','bad_counter','bad_repeatability'))
def test_native_reference_matrix_rejected_when_forged(change):
    w=sample_w()
    matrix={a:{m:{'sender':2 if a=='original' else 0,'ingress':2 if a=='original' else 0,
                  'result_sha256':'1'*64,'repeatability_identical':True}
               for m in ('on','off')} for a in ('original','variant')}
    if change=='missing':matrix['variant'].pop('on')
    elif change=='promote':matrix['original']['on']['extra_native_hook_proof']=True
    elif change=='bad_counter':matrix['variant']['off']['sender']=2
    else:matrix['variant']['on']['repeatability_identical']=False
    with pytest.raises((InterventionError,KeyError)):
        mod.analyze(w,canon(w),native_reference=matrix,source_rechecked=True)


def test_native_baseline_needs_source_recheck():
    with pytest.raises(InterventionError):
        mod.analyze(sample_w(),canon(sample_w()),native_reference={'original':{},'variant':{}})


def test_canonical_predecessor_bytes_required():
    with pytest.raises(InterventionError):
        mod.analyze(sample_w(),json.dumps(sample_w()).encode())


def test_no_import_from_prior_test_modules():
    # Avoid v1n's pytest --import-mode=importlib collection regression.
    import inspect
    from spk_bv_research import reference_observation_port_v1x
    assert 'from test_spk_' not in inspect.getsource(reference_observation_port_v1x)
