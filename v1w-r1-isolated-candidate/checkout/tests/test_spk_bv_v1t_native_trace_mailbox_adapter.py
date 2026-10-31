"""v1t self-contained source-contract, custody, finite mailbox and adversarial tests."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_trace_mailbox_adapter_v1t import (
 SCHEMA,STATUS,EDGE,PLANS,KINDS,TraceLabBus,LabPacket,BShadowMailbox,
 validate_inputs,analyze,session,
)
from search import spk_bv_v1t_native_trace_mailbox_adapter as cli


def specimens():
    frozen={'frozen-synthetic-marker':'synthetic-only'}
    s={'schema':'spk-bv-separated-receiver-disclosure-channel-shadow/v1s',
       'status':'SOURCE_BOUND_SHADOW_CHANNEL_NO_NATIVE_RECEIVER_AUTHORITY',
       'source_kind':'SOURCE_BOUND_V1R_PLUS_ISOLATED_IN_PROCESS_CHANNEL_LAB',
       'inherited_native_v1r_recomputation_verified_in_this_run':True,
       'lab_case_count':20,'lab_cases':[{'scenario':str(i)} for i in range(20)],
       'lab_control_loss_fails_closed':True,
       'native_separate_disclosure_channel_installed':False,
       'native_receiver_judgments':0,'native_receiver_authorized_absence_witnesses':0,
       'native_operator_updates':0,'native_learning_proven':False,
       'lab_authentication_assumption':'PYTHON_OBJECT_IDENTITY_ONLY_NOT_NATIVE_AUTHENTICATION',
       'reference_v1r_sha256':'a'*64,'reference_v1q_sha256':'b'*64,
       'native_fixture_sha256':'c'*64,'frozen_native_sources':frozen}
    def edge(arm,which):
        n=2 if arm=='original' else 0
        ids=['r1','r3'] if arm=='original' else []
        stamps=[1,3] if arm=='original' else []
        return {'edge':which,'sender':'A' if which==EDGE else 'B',
                'receiver':'B' if which==EDGE else 'C',
                'sender_channel':7,'receiver_channel':0,
                'independent_two_port_coverage_certificate':False,
                'receiver_native_received_sender_port_attestation':False,
                'sender_trace_emission_count':n,
                'receiver_ingress_occurrence_count':n,
                'receiver_consumed_occurrence_count':n,
                'ingress_occurrence_ids':ids,'sender_emission_timestamps':stamps,
                'posthoc_trace_classification':('ROUTED_EVENTS_IN_COMPLETE_RUN_TRACE' if n else
                                                  'NO_SOURCE_CHANNEL_EVENT_IN_BOUNDED_RUN_TRACE')}
    trace={}
    for arm in ('original','variant'):
        trace[arm]={}
        for mode in ('off','on'):
            trace[arm][mode]={'posthoc_simulator_trace_reader_only':True,
                 'native_external_observer_present':False,
                 'native_absence_certificate_count':0,'native_full_scheduler_executed':True,
                 'edge_projections':[edge(arm,EDGE),edge(arm,'B->C:7->0')]}
    m={'schema':'spk-bv-native-passive-two-port-trace-projection/v1m',
       'status':'NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER',
       'source_kind':'FROZEN_NATIVE_SCHEDULER_POSTHOC_TRACES',
       'full_native_scheduler_runs_recomputed_in_this_run':4,
       'inherited_native_v1l_recomputation_verified_in_this_run':True,
       'native_two_port_independent_observer_installed':False,
       'recipient_access_to_sender_trace_demonstrated':False,
       'endogenous_receiver_judgments':0,'native_coverage_certificates':0,
       'sender_operator_updates':0,'native_learning_proven':False,
       'native_fixture_sha256':'c'*64,'frozen_native_sources':frozen,
       'native_trace_projection':trace,
       'native_trace_source_emission_count_original_vs_variant':{'A':[2,0],'B':[2,0]}}
    return s,m


def test_basic_contract_and_counts():
    s,m=specimens()
    assert validate_inputs(s,canon(s),m,canon(m))=={
      a:{v:{'sender':n,'ingress':n,'consumed':n,'occurrence_count':n}
          for v in ('off','on')} for a,n in [('original',2),('variant',0)]}
    report=analyze(s,canon(s),m,canon(m))
    assert report['schema']==SCHEMA and report['status']==STATUS
    assert report['shadow_lab_session_count']==58 and len(report['shadow_lab_sessions'])==58
    assert report['inherited_native_v1s_recomputation_verified_in_this_run'] is False
    assert report['new_native_scheduler_runs_in_this_module']==0
    assert report['native_receiver_received_control_packets']==0
    assert report['native_independent_absence_certificates']==0
    assert report['native_scored_receiver_judgments']==0
    assert report['native_operator_updates']==0 and not report['native_learning_proven']
    assert not report['source_authenticated_to_receiver']


@pytest.mark.parametrize('arm,mode',[(a,m) for a in ('original','variant') for m in ('off','on')])
def test_shadow_only_views_are_separated_from_experimenter(arm,mode):
    s,m=specimens();report=analyze(s,canon(s),m,canon(m))
    views=[a for a in report['shadow_lab_sessions'] if a['arm']==arm and a['mode']==mode]
    assert len(views)==(15 if arm=='original' else 14)
    assert all(set(x['receiver_view'])=={
        'classification','receiver_ingress_count','received_kinds',
        'decision_declared_to_shadow_B','native_authority','sender_decision_cause_known',
        'independent_absence_certificate','receiver_scored_judgment'} for x in views)
    assert all(x['received_packets_native']==0 and not x['receiver_view']['native_authority']
               for x in views)
    assert all(x['episode_id_is_shadow_label_only']==f'shadow.native-trace.{arm}.{mode}'
               for x in views)


@pytest.mark.parametrize('plan',[p for p in PLANS if p!='contradictory_source_count'])
def test_variant_all_plans_fail_closed_when_control_unavailable(plan):
    obj=session('variant','off',plan,{'sender':0,'ingress':0,'consumed':0,'occurrence_count':0})
    assert obj['plan']==plan and obj['receiver_view']['receiver_scored_judgment'] is False
    if plan=='ingress_only':
        assert obj['receiver_view']['received_kinds']==[]
        assert obj['receiver_view']['classification']=='NO_PREDECLARED_EXPECTATION_RECEIVED'
    if plan in ('sender_only','sender_lost','sender_coverage_lost',
                'receiver_coverage_lost','expectation_lost'):
        assert obj['receiver_view']['classification']!=\
            'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY'
    if plan.startswith('packet_'):
        assert obj['malicious_attempts_rejected']==1
    assert obj['received_packets_native']==0


@pytest.mark.parametrize('mode',('off','on'))
def test_same_trace_different_control_delivery_changing_shadow_knowledge(mode):
    base={'sender':0,'ingress':0,'consumed':0,'occurrence_count':0}
    a=session('variant',mode,'ingress_only',base)['receiver_view']
    b=session('variant',mode,'all_disclosed',base)['receiver_view']
    c=session('variant',mode,'sender_lost',base)['receiver_view']
    assert a['receiver_ingress_count']==b['receiver_ingress_count']==c['receiver_ingress_count']==0
    assert len(a['received_kinds'])==0 and len(b['received_kinds'])==5
    assert b['classification']=='LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY'
    assert a['classification']=='NO_PREDECLARED_EXPECTATION_RECEIVED'
    assert c['classification']=='NO_SENDER_DISCLOSURE_UNKNOWN'
    assert a['sender_decision_cause_known']==b['sender_decision_cause_known']==False


@pytest.mark.parametrize('kind',list(KINDS))
def test_mailbox_accepts_only_valid_deliveries_for_each_kind(kind):
    bus=TraceLabBus();box=BShadowMailbox(bus,'episode.test',0)
    spec={'expectation':('declared:up-to-two',0,1),
          'sender_count':(2,7,8),
          'sender_coverage':('lab-window-0-6',7,8),
          'receiver_coverage':('lab-window-0-6',7,8),
          'decision':('experimenter:CMP2',3,4)}
    val,t0,t1=spec[kind]
    packet=bus.mint(kind,'episode.test',val,created_at=t0,delivered_at=t1)
    box.deliver(packet)
    with pytest.raises(InterventionError):box.deliver(packet)


@pytest.mark.parametrize('key,bad',[
    ('seal',object()),('issuer','plan'),('episode','other'),('link','B->C:7->0'),
    ('kind','not_a_packet_kind'),('delivered_at',11),('delivered_at',6),
    ('created_at',9),('datum',-1),('datum',3),('datum','0'),
])
def test_adversarial_packet_rejected(key,bad):
    bus=TraceLabBus();box=BShadowMailbox(bus,'episode.test',0)
    p=bus.mint('sender_count','episode.test',2,created_at=7,delivered_at=8)
    with pytest.raises((InterventionError,KeyError)):
        box.deliver(replace(p,**{key:bad}))
    assert box.received=={}


@pytest.mark.parametrize('created,delivered',[(True,1),(-1,0),(3,2),(0,False)])
def test_bus_rejects_timing(created,delivered):
    with pytest.raises(InterventionError):
        TraceLabBus().mint('expectation','epi','declared:up-to-two',
                           created_at=created,delivered_at=delivered)


@pytest.mark.parametrize('field,bad',[
    ('schema','wrong'),('status','wrong'),('source_kind','wrong'),
    ('inherited_native_v1r_recomputation_verified_in_this_run',False),
    ('lab_case_count',19),('lab_control_loss_fails_closed',False),
    ('native_separate_disclosure_channel_installed',True),
    ('native_receiver_judgments',1),('native_operator_updates',1),
    ('native_learning_proven',True),('native_receiver_authorized_absence_witnesses',1),
    ('reference_v1r_sha256','1234'),('reference_v1q_sha256','x'*64),
    ('native_fixture_sha256','d'*64),('frozen_native_sources',{}),
])
def test_s_input_tampering_rejected(field,bad):
    s,m=specimens();s[field]=bad
    with pytest.raises(InterventionError):validate_inputs(s,canon(s),m,canon(m))


@pytest.mark.parametrize('field,bad',[
    ('schema','bad'),('status','bad'),('source_kind','bad'),
    ('full_native_scheduler_runs_recomputed_in_this_run',2),
    ('inherited_native_v1l_recomputation_verified_in_this_run',False),
    ('native_two_port_independent_observer_installed',True),
    ('recipient_access_to_sender_trace_demonstrated',True),
    ('native_coverage_certificates',1),('endogenous_receiver_judgments',1),
    ('sender_operator_updates',1),('native_learning_proven',True),
    ('native_trace_source_emission_count_original_vs_variant',{'A':[1,0],'B':[2,0]}),
])
def test_m_input_tampering_rejected(field,bad):
    s,m=specimens();m[field]=bad
    with pytest.raises(InterventionError):validate_inputs(s,canon(s),m,canon(m))


@pytest.mark.parametrize('field,bad',[
    ('edge','A->C:7->0'),('sender','C'),('receiver','C'),('sender_channel',0),
    ('receiver_channel',7),('independent_two_port_coverage_certificate',True),
    ('receiver_native_received_sender_port_attestation',True),
    ('sender_trace_emission_count',1),('receiver_ingress_occurrence_count',1),
    ('receiver_consumed_occurrence_count',1),('sender_emission_timestamps',[1]),
    ('ingress_occurrence_ids',['r1','r1']),
    ('posthoc_trace_classification','INVALID'),
])
def test_native_A_to_B_edge_tampering_rejected(field,bad):
    s,m=specimens();m['native_trace_projection']['original']['off']['edge_projections'][0][field]=bad
    with pytest.raises((InterventionError,KeyError)):
        validate_inputs(s,canon(s),m,canon(m))


def test_native_downstream_B_to_C_bad_source_rejected():
    s,m=specimens();m['native_trace_projection']['original']['off']['edge_projections'][1]['sender']='A'
    with pytest.raises(InterventionError):validate_inputs(s,canon(s),m,canon(m))


def test_missing_arm_and_missing_mode_rejected():
    s,m=specimens();del m['native_trace_projection']['variant']
    with pytest.raises(InterventionError):validate_inputs(s,canon(s),m,canon(m))
    s,m=specimens();del m['native_trace_projection']['original']['off']
    with pytest.raises((InterventionError,KeyError)):
        validate_inputs(s,canon(s),m,canon(m))


def test_noncanonical_bytes_rejected():
    s,m=specimens()
    with pytest.raises(InterventionError):validate_inputs(s,json.dumps(s).encode(),m,canon(m))
    with pytest.raises(InterventionError):validate_inputs(s,canon(s),m,json.dumps(m).encode())


def test_analyst_result_deterministic():
    s,m=specimens();sr=canon(s);mr=canon(m)
    a=analyze(s,sr,m,mr);b=analyze(json.loads(sr),sr,json.loads(mr),mr)
    assert canon(a)==canon(b)


def _cli_fixtures(tmp_path):
    root=tmp_path/'repo';root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    s,m=specimens();files={}
    for name in cli.NAMES:
        p=outside/(name+'.json')
        p.write_bytes(canon(s if name=='v1s' else m if name=='v1m' else {'key':name}))
        files[name]=p
    args=['--root',str(root)]
    for n in cli.NAMES:args+=['--'+n,str(files[n])]
    out=outside/'output.json';args+=['--out',str(out)]
    return args,out,files


def test_cli_only_attests_on_byte_identical_native_chain(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    def replay(argv):
        Path(argv[-1]).write_bytes(files['v1s'].read_bytes())
        return 0
    monkeypatch.setattr(cli,'smain',replay)
    assert cli.main(args)==0
    data=json.loads(out.read_bytes())
    assert data['inherited_native_v1s_recomputation_verified_in_this_run'] is True
    assert data['new_native_scheduler_runs_in_this_module']==0
    assert data['native_receiver_received_control_packets']==0


def test_cli_denies_mismatched_chain(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    def mismatch(argv):
        Path(argv[-1]).write_bytes(b'{}\n');return 0
    monkeypatch.setattr(cli,'smain',mismatch)
    assert cli.main(args)==2 and not out.exists()


def test_cli_denies_failed_replay(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    monkeypatch.setattr(cli,'smain',lambda argv:2)
    assert cli.main(args)==2 and not out.exists()


def test_cli_denies_changed_predecessor_mid_replay(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    def mutating(argv):
        Path(argv[-1]).write_bytes(files['v1s'].read_bytes())
        files['v1m'].write_text('{"tampered":true}\n')
        return 0
    monkeypatch.setattr(cli,'smain',mutating)
    assert cli.main(args)==2 and not out.exists()


def test_cli_denies_alias(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    args[args.index('--v1m')+1]=str(files['v1s'])
    monkeypatch.setattr(cli,'smain',lambda argv:0)
    assert cli.main(args)==2 and not out.exists()


def test_cli_denies_repo_write(tmp_path,monkeypatch):
    args,out,files=_cli_fixtures(tmp_path)
    args[-1]=str(tmp_path/'repo'/'out.json')
    assert cli.main(args)==2


def test_cli_denies_overwrite(tmp_path):
    args,out,files=_cli_fixtures(tmp_path)
    out.write_text('KEEP')
    assert cli.main(args)==2 and out.read_text()=='KEEP'


def test_cli_denies_source_as_output(tmp_path):
    args,out,files=_cli_fixtures(tmp_path)
    args[-1]=str(files['v1s'])
    original=files['v1s'].read_bytes()
    assert cli.main(args)==2 and files['v1s'].read_bytes()==original


def test_lab_object_from_another_bus_is_rejected():
    bus=TraceLabBus();other=TraceLabBus();box=BShadowMailbox(bus,'test.episode',0)
    pkt=other.mint('sender_count','test.episode',0,created_at=7,delivered_at=8)
    with pytest.raises(InterventionError):box.deliver(pkt)


def test_mailbox_has_no_source_native_projection_reference():
    bus=TraceLabBus();box=BShadowMailbox(bus,'only.ingress',0)
    assert set(vars(box))=={'_bus','episode','ingress','received','verdict_at'}
    assert box.classify()['classification']=='NO_PREDECLARED_EXPECTATION_RECEIVED'


def test_cross_episode_packet_from_original_cannot_enter_variant():
    bus=TraceLabBus();box=BShadowMailbox(bus,'shadow.native-trace.variant.off',0)
    packet=bus.mint('sender_count','shadow.native-trace.original.off',2,created_at=7,delivered_at=8)
    with pytest.raises(InterventionError):box.deliver(packet)
