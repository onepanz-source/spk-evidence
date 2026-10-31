"""Self-contained v1u lab contract and adversarial tests; no prior test imports."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.incremental_shadow_channel_v1u import (
 SCHEMA,STATUS,PLANS,ROLES,LabChannel,BReceiver,LabEnvelope,
 run_lab,analyze,validate_source,
)
from search import spk_bv_v1u_incremental_shadow_channel as cli


def specimen():
    frozen={'compute_function_name':'_compute_local',
            'frozen_producer_sha256':{p:'a'*64 for p in (
            'search/spk_bv_v0e_live_evidence.py',
            'spk_backvalidation_v0/live_dual_scheduler_v0e.py',
            'tests/test_spk_bv_live_dual_scheduler_v0e.py')}}
    rows=[]
    for arm in ('original','variant'):
        n=2 if arm=='original' else 0
        for mode in ('off','on'):
            for plan in ('ingress_only','sender_only','all_disclosed','sender_lost',
                'sender_coverage_lost','receiver_coverage_lost','expectation_lost',
                'decision_lost','packet_forged','packet_replayed','packet_late',
                'packet_wrong_edge','packet_wrong_episode','packet_wrong_role',
                'contradictory_source_count'):
                if plan=='contradictory_source_count' and arm=='variant':continue
                rows.append({
                    'arm':arm,'mode':mode,'plan':plan,
                    'episode_id_is_shadow_label_only':f'shadow.native-trace.{arm}.{mode}',
                    'ingress_derived_from_posthoc_trace_not_live_B':True,
                    'received_packets_native':0,
                    'experimenter_posthoc_counts_not_receiver_visible':{
                        'sender':n,'ingress':n,'consumed':n,'occurrence_count':n},
                    'receiver_view':{
                        'classification':('INGRESS_OBSERVED_FROM_POSTHOC_PROJECTION'
                            if arm=='original' else
                            'LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY'),
                        'received_kinds':([] if plan=='ingress_only' else
                            list(sorted(ROLES)) if plan=='all_disclosed' else []),
                        'receiver_ingress_count':n,'native_authority':False,
                        'receiver_scored_judgment':False,
                        'sender_decision_cause_known':False,
                        'independent_absence_certificate':False,
                    }
                })
    return {
        'schema':'spk-bv-source-bound-native-trace-to-isolated-mailbox/v1t',
        'status':'POSTHOC_NATIVE_TRACE_BRIDGE_SHADOW_RECEIPTS_ONLY',
        'source_kind':'POSTHOC_NATIVE_V1M_TRACE_PLUS_ISOLATED_V1S_STYLE_MAILBOX',
        'inherited_native_v1s_recomputation_verified_in_this_run':True,
        'new_native_scheduler_runs_in_this_module':0,
        'source_native_scheduler_runs_in_v1m':4,
        'shadow_lab_session_count':58,'shadow_lab_sessions':rows,
        'native_receiver_received_control_packets':0,
        'native_independent_absence_certificates':0,
        'native_authenticated_producer_evidence':0,
        'native_decision_records_to_receiver':0,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'source_authenticated_to_receiver':False,
        'posthoc_producer_and_ingress_share_same_scheduler_trace':True,
        'injected_control_packets_are_shadow_only':True,
        'lab_control_loss_fails_closed':True,
        'counterfactual_episode_ids_not_shared_across_worlds':True,
        'declared_criterion_or_utility_identified':False,
        'reference_v1s_sha256':'a'*64,'reference_v1m_sha256':'b'*64,
        'reference_v1r_sha256':'c'*64,'native_fixture_sha256':'d'*64,
        'frozen_native_sources':frozen,
    }


def test_complete_source_and_report():
    t=specimen(); seeds=validate_source(t,canon(t))
    assert len(seeds)==4
    result=analyze(t,canon(t))
    assert result['schema']==SCHEMA and result['status']==STATUS
    assert len(result['lab_incremental_sessions'])==result['lab_incremental_session_count']==58
    assert result['inherited_native_v1t_recomputation_verified_in_this_run'] is False
    assert result['native_scheduler_callback_connected'] is False
    assert result['native_receiver_received_live_control_packets']==0
    assert result['native_scored_receiver_judgments']==0
    assert result['native_operator_updates']==0 and result['native_learning_proven'] is False
    assert result['producer_posthoc_counts_withheld_from_receiver'] is True
    assert result['lab_tick_is_simulated_not_native'] is True


@pytest.mark.parametrize('arm,mode,plan',[
    (a,m,p) for a in ('original','variant') for m in ('off','on')
    for p in PLANS if not(p=='contradictory_source' and a=='variant')
])
def test_each_incremental_scenario_lacks_native_authority(arm,mode,plan):
    n=2 if arm=='original' else 0
    session=run_lab(arm,mode,plan,{'sender':n,'ingress':n})
    view=session['receiver_view']
    assert not view['native_receiver'] and not view['native_authority']
    assert not view['native_absence_certificate'] and not view['receiver_scored_judgment']
    assert not view['operator_update_committed'] and not view['sender_decision_causal_role_known']
    assert session['native_stream_messages_delivered']==0
    assert session['lab_clock_not_native']
    if plan=='all_disclosed':
        assert view['classification']==('LAB_INGRESS_OBSERVED' if n else
                        'LAB_ZERO_SENDER_REPORT_CONDITIONAL_ONLY')
    if plan=='ingress_only' and not n:
        assert view['classification']=='NO_RECEIVED_EXPECTATION_UNKNOWN'
    if plan=='source_lost' and not n:
        assert view['classification']=='NO_SENDER_REPORT_UNKNOWN'
    if plan=='control_loss' or plan=='bounded_queue_overflow':
        assert view['classification']=='CONTROL_FAULT_UNKNOWN'
    if plan in ('forged','replayed','wrong_episode','late','out_of_order'):
        assert session['rejected_attack_packets']==1


@pytest.mark.parametrize('field,bad',[
 ('schema','other'),('status','other'),('source_kind','other'),
 ('shadow_lab_session_count',57),('new_native_scheduler_runs_in_this_module',1),
 ('inherited_native_v1s_recomputation_verified_in_this_run',False),
 ('native_receiver_received_control_packets',1),
 ('native_independent_absence_certificates',1),
 ('native_authenticated_producer_evidence',1),
 ('native_decision_records_to_receiver',1),
 ('native_scored_receiver_judgments',1),('native_operator_updates',1),
 ('native_learning_proven',True),('source_authenticated_to_receiver',True),
 ('lab_control_loss_fails_closed',False),
 ('posthoc_producer_and_ingress_share_same_scheduler_trace',False),
 ('injected_control_packets_are_shadow_only',False),
 ('counterfactual_episode_ids_not_shared_across_worlds',False),
 ('reference_v1s_sha256','x'*64),('native_fixture_sha256','not-a-hash'),
 ('frozen_native_sources',{}),
])
def test_drifted_source_rejected(field,bad):
    t=specimen();t[field]=bad
    with pytest.raises(InterventionError):validate_source(t,canon(t))


@pytest.mark.parametrize('change',('alias','missing','invalid_counts','native_authority',
       'receiver_claims','wrong_episode','forged_predecision','wrong_expected_class',
       'incomplete_control_kinds'))
def test_source_rows_tampering_rejected(change):
    t=specimen()
    r=t['shadow_lab_sessions'][0]
    if change=='alias':t['shadow_lab_sessions'][1]=deepcopy(r)
    elif change=='missing':t['shadow_lab_sessions'].pop()
    elif change=='invalid_counts':r['experimenter_posthoc_counts_not_receiver_visible']['sender']=3
    elif change=='native_authority':r['receiver_view']['native_authority']=True
    elif change=='receiver_claims':r['receiver_view']['receiver_scored_judgment']=True
    elif change=='wrong_episode':r['episode_id_is_shadow_label_only']='shadow.native-trace.other'
    elif change=='forged_predecision':r['received_packets_native']=1
    elif change=='wrong_expected_class':
        t['shadow_lab_sessions'][2]['receiver_view']['classification']='fake'
    elif change=='incomplete_control_kinds':
        t['shadow_lab_sessions'][2]['receiver_view']['received_kinds'].pop()
    with pytest.raises(InterventionError):validate_source(t,canon(t))


def test_noncanonical_bytes_rejected():
    t=specimen()
    with pytest.raises(InterventionError):validate_source(t,json.dumps(t).encode())


def test_receiver_no_access_to_hidden_experimenter_state():
    chan=LabChannel('ep')
    b=BReceiver(chan)
    assert not any(k in b.__dict__ for k in ('sender','source','trace','experimenter','posthoc'))
    with pytest.raises(InterventionError):b.view()
    b.close(10)
    assert b.view()['classification']=='NO_RECEIVED_EXPECTATION_UNKNOWN'


@pytest.mark.parametrize('clock',[(-1,0),(2,1),(11,9),(True,4)])
def test_clock_invalid(clock):
    first,second=clock
    c=LabChannel('ep');b=BReceiver(c)
    with pytest.raises(InterventionError):b.advance(first) if type(first) is bool or first<0 else (b.advance(first),b.advance(second))


def test_preclosure_and_no_silent_claim():
    ch=LabChannel('run');b=BReceiver(ch)
    b.advance(8)
    with pytest.raises(InterventionError):b.close(8)
    with pytest.raises(InterventionError):b.view()
    b.close(10)
    assert b.view()['classification']=='NO_RECEIVED_EXPECTATION_UNKNOWN'


@pytest.mark.parametrize('kind',tuple(ROLES))
def test_incremental_legitimate_delivery_envelopes(kind):
    ch=LabChannel('e');b=BReceiver(ch)
    specs={'expectation':('declared:up-to-two',0,1),
           'decision':('experimenter:CMP1',3,3),
           'sender_count':(0,7,8),'sender_coverage':('lab-window-0-6',7,8),
           'receiver_coverage':('lab-window-0-6',7,8)}
    value,start,arrive=specs[kind]
    p=ch.mint(kind,value,start,arrive)
    assert ch.enqueue(p)
    for tick in range(arrive+1):
        b.advance(tick);ch.flush(tick,b)
    assert b.messages[kind]==value
    with pytest.raises(InterventionError):b.accept(p,arrive)


@pytest.mark.parametrize('key,bad',[
 ('issuer','plan'),('edge','B->C:7->0'),('episode','not-ep'),
 ('sequence',0),('sequence',True),('generated_tick',9),('delivered_tick',11),
 ('capability','counterfeit'),('value',5),('value',True),('kind','unknown'),
])
def test_corrupt_source_packet_rejected(key,bad):
    ch=LabChannel('ep');b=BReceiver(ch)
    p=ch.mint('sender_count',0,7,8)
    for tick in range(9):b.advance(tick)
    with pytest.raises((InterventionError,KeyError)):
        b.accept(replace(p,**{key:bad}),8)
    assert not b.messages


def test_cross_episode_replay_fails_even_with_seal():
    ch=LabChannel('left');receiver=BReceiver(ch)
    p=ch.mint('sender_count',0,7,8)
    for tick in range(9):receiver.advance(tick)
    with pytest.raises(InterventionError):receiver.accept(replace(p,episode='right'),8)


def test_capacity_exhaustion_fail_closed_and_not_restore():
    ch=LabChannel('ep',capacity=1);b=BReceiver(ch)
    assert ch.enqueue(ch.mint('sender_count',0,7,8))
    assert not ch.enqueue(ch.mint('sender_coverage','lab-window-0-6',7,8))
    assert ch.failed and not ch.pending
    with pytest.raises(InterventionError):ch.enqueue(ch.mint('decision','experimenter:CMP1',3,8))
    b.close(10)
    assert b.view()['classification']=='CONTROL_FAULT_UNKNOWN'


def test_no_forged_native_source_knowledge_on_transport_gap():
    c=LabChannel('ep');b=BReceiver(c)
    packets=[c.mint('expectation','declared:up-to-two',0,1),
             c.mint('sender_count',1,7,8),
             c.mint('sender_coverage','lab-window-0-6',7,8),
             c.mint('receiver_coverage','lab-window-0-6',7,8)]
    for p in packets:assert c.enqueue(p)
    for tick in range(11):b.advance(tick);c.flush(tick,b)
    b.close(11)
    assert b.view()['classification']=='LAB_POSSIBLE_TRANSPORT_GAP_CONDITIONAL_ONLY'
    assert b.view()['native_authority'] is False


def test_cli_verifies_bytes_before_promoting_inherited_replay(tmp_path,monkeypatch):
    t=specimen()
    raw=canon(t)
    paths={}
    for name in cli.NAMES:
        path=tmp_path/f'{name}.json'
        path.write_bytes(raw if name=='v1t' else canon({'placeholder':name}))
        paths[name]=path
    root=Path.cwd().resolve()
    if root==tmp_path or root in tmp_path.parents:pytest.skip('temp input must be outside root')
    def stub(args):
        path=Path(args[args.index('--out')+1])
        path.write_bytes(raw)
        return 0
    monkeypatch.setattr(cli,'tmain',stub)
    argv=['--root',str(root)]
    for name in cli.NAMES:argv.extend(('--'+name,str(paths[name])))
    output=tmp_path/'v1u.json'
    argv.extend(('--out',str(output)))
    assert cli.main(argv)==0
    result=json.loads(output.read_bytes())
    assert result['inherited_native_v1t_recomputation_verified_in_this_run'] is True
    assert result['native_scheduler_callback_connected'] is False
    assert cli.main(argv)==2  # immutable output
    assert output.read_bytes()==canon(result)


def test_cli_byte_mismatch_rejects_before_write(tmp_path,monkeypatch):
    t=specimen();paths={}
    for name in cli.NAMES:
        p=tmp_path/f'{name}.json'
        p.write_bytes(canon(t) if name=='v1t' else canon({'placeholder':name}))
        paths[name]=p
    def stub(args):
        Path(args[args.index('--out')+1]).write_bytes(b'{}\n')
        return 0
    monkeypatch.setattr(cli,'tmain',stub)
    argv=['--root',str(Path.cwd().resolve())]
    for name in cli.NAMES:argv.extend(('--'+name,str(paths[name])))
    out=tmp_path/'no-output.json';argv.extend(('--out',str(out)))
    assert cli.main(argv)==2 and not out.exists()
