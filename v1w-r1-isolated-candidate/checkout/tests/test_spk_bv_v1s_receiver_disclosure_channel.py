"""BV v1s isolated channel and source-contract tests (no native runtime required)."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_allocation_boundary_v1r import allocate,canon
from spk_bv_research.receiver_disclosure_channel_v1s import (
    IsolatedBus,ReceiverMailbox,Packet,CASES,EPISODE,EVENT,KINDS,
    analyze,replay_lab,validate_r,SCHEMA,STATUS,
)
from search import spk_bv_v1s_receiver_disclosure_channel as cli

TABLE={
    'terminal':{'none':2,'A':0,'B':1,'C':1,'AB':0,'AC':0,'BC':0,'ABC':0},
    'A->B:7->0':{'none':2,'A':0,'B':2,'C':2,'AB':0,'AC':0,'BC':2,'ABC':0},
    'B->C:7->0':{'none':2,'A':0,'B':1,'C':2,'AB':0,'AC':0,'BC':1,'ABC':0},
}

def specimen_r():
    data={}
    for mode in ('off','on'):
        data[mode]={}
        for metric in (*TABLE,'feedback_assessments'):
            values=({a:(TABLE['terminal'][a] if mode=='on' else 0)
                     for a in TABLE['terminal']} if metric=='feedback_assessments' else TABLE[metric])
            data[mode][metric]={k:allocate(values,v) for k,v in
                                [('preserve_activity',1),('suppress_activity',-1)]}
    return {'schema':'spk-bv-posthoc-factorial-allocation-nonidentifiability/v1r',
            'status':'EXACT_COUNT_ACCOUNTING_NO_RECEIVER_CREDIT',
            'source_kind':'SOURCE_BOUND_NATIVE_FACTORIAL_POSTHOC_ONLY',
            'native_v1q_recomputation_verified_in_this_run':True,
            'new_native_scheduler_runs_in_this_module':0,
            'factored_native_matrix_runs_in_source':16,
            'allocation_order_variability_present':True,
            'receiver_exposed_to_allocation':False,
            'native_scored_receiver_judgments':0,'native_operator_updates':0,
            'native_learning_proven':False,'causal_credit_or_utility_identified':False,
            'reference_v1q_sha256':'a'*64,'native_fixture_sha256':'b'*64,
            'frozen_native_sources':{'synthetic':'not-verified'},
            'nonadditivity_diagnostics':{'off':{'terminal':{'nonadditive_correction':2}}},
            'posthoc_rational_allocation':data}


def test_report_contract_never_promotes_native():
    r=specimen_r();out=analyze(r,canon(r))
    assert out['schema']==SCHEMA and out['status']==STATUS
    assert out['inherited_native_v1r_recomputation_verified_in_this_run'] is False
    assert out['lab_case_count']==len(CASES)==20
    assert not out['native_separate_disclosure_channel_installed']
    assert out['native_receiver_authorized_absence_witnesses']==0
    assert out['native_receiver_judgments']==0 and not out['native_learning_proven']
    assert out['reference_v1r_sha256'] and out['reference_v1q_sha256']=='a'*64
    assert not out['sender_decision_causality_identified']
    assert out['lab_authentication_assumption']=='PYTHON_OBJECT_IDENTITY_ONLY_NOT_NATIVE_AUTHENTICATION'

@pytest.mark.parametrize('scenario,expected',[
    ('delivered','LOCAL_INGRESS_OBSERVED_NO_CAUSAL_JUDGMENT'),
    ('contradictory_ingress','CONFLICTING_LAB_PORT_DISCLOSURES_UNKNOWN'),
    ('port_silence','LAB_SENDER_PORT_SILENCE_WITH_BOTH_COVERAGES'),
    ('transport_gap','LAB_POSSIBLE_TRANSPORT_GAP_WITH_BOTH_COVERAGES'),
    ('no_expectation','NO_RECEIVED_PREDECISION_EXPECTATION'),
    ('control_lost','SENDER_PORT_INFORMATION_UNAVAILABLE'),
    ('sender_tap_lost','COVERAGE_INFORMATION_UNAVAILABLE'),
    ('receiver_tap_lost','COVERAGE_INFORMATION_UNAVAILABLE'),
    ('decision_not_disclosed','LAB_SENDER_PORT_SILENCE_WITH_BOTH_COVERAGES'),
    ('only_ingress','NO_RECEIVED_PREDECISION_EXPECTATION'),
    ('only_ingress_alternate_world','NO_RECEIVED_PREDECISION_EXPECTATION'),
])
def test_scenario_classifications(scenario,expected):
    obj=replay_lab(scenario)
    assert obj['classification']==expected
    assert not obj['native_authority'] and not obj['receiver_scored_judgment']
    assert not obj['sender_internal_cause_identified']

@pytest.mark.parametrize('scenario',[
    'untrusted_duplicate','untrusted_forgery','wrong_receiver_C',
    'wrong_event','stale_receipt','altered_payload','incorrect_issuer',
    'wrong_episode','untrusted_json',
])
def test_adversarial_packets_cannot_change_receipts(scenario):
    a=replay_lab(scenario);b=replay_lab('port_silence')
    assert a['rejected_untrusted_packets']==1
    assert a['received_evidence_kinds']==b['received_evidence_kinds']
    assert a['classification']==b['classification']


def test_two_hidden_worlds_same_receiver_projection():
    a=replay_lab('only_ingress');b=replay_lab('only_ingress_alternate_world')
    assert a['classification']==b['classification']
    assert a['received_evidence_kinds']==b['received_evidence_kinds']==[]


def test_visible_decision_is_not_causal_judgment():
    a=replay_lab('port_silence');b=replay_lab('decision_not_disclosed')
    assert a['classification']==b['classification']
    assert a['receiver_received_decision_record'] is True
    assert b['receiver_received_decision_record'] is False
    assert not a['sender_internal_cause_identified']


@pytest.mark.parametrize('kind',sorted(KINDS))
def test_received_packet_is_scope_bound_to_A_to_B(kind):
    bus=IsolatedBus();mb=ReceiverMailbox(bus,ingress=0)
    cases={
        'expectation':('expect:1',0,1),'sender_port':('emitted:0',7,8),
        'sender_coverage':('covered:0..6',7,8),
        'receiver_coverage':('covered:0..6',7,8),
        'decision':('selected:CMP2',3,4),
    }
    text,created,delivered=cases[kind]
    packet=bus.mint(kind,text,created_at=created,delivered_at=delivered)
    assert packet.issuer==KINDS[kind]
    mb.deliver(packet)
    assert kind in mb.received
    with pytest.raises(InterventionError):mb.deliver(packet)


@pytest.mark.parametrize('field,replacement',[
    ('source','C'),('receiver','C'),('episode','other.episode'),
    ('event_id','other.event'),('source_channel',0),('receiver_channel',7),
    ('issuer','receiver_tap'),('seal',object()),('created_at',10),
    ('delivered_at',10),('data','emitted:9'),('data','emitted:-1'),
])
def test_mutated_packet_is_rejected(field,replacement):
    bus=IsolatedBus();mb=ReceiverMailbox(bus,ingress=0)
    packet=bus.mint('sender_port','emitted:0',created_at=7,delivered_at=8)
    with pytest.raises(InterventionError):mb.deliver(replace(packet,**{field:replacement}))
    assert not mb.received


@pytest.mark.parametrize('created,delivered',[(-1,1),(2,1),(True,1),(3,1)])
def test_invalid_bus_timing_rejected(created,delivered):
    with pytest.raises(InterventionError):
        IsolatedBus().mint('expectation','expect:1',created_at=created,delivered_at=delivered)


@pytest.mark.parametrize('kind,data,created,delivered',[
    ('expectation','expect:1',3,4),('expectation','expect:1',0,10),('expectation','expect:1',0,3),
    ('expectation','expect:2',0,1),('sender_port','emitted:2',7,8),
    ('sender_port','emitted:0',3,4),('sender_coverage','covered:0..5',7,8),
    ('receiver_coverage','covered:0..7',7,8),('decision','selected:CMP3',3,4),
    ('decision','selected:CMP2',4,5),('decision','selected:CMP1',2,4),
])
def test_semantically_invalid_packet_rejected(kind,data,created,delivered):
    bus=IsolatedBus();mb=ReceiverMailbox(bus,ingress=0)
    with pytest.raises(InterventionError):
        mb.deliver(bus.mint(kind,data,created_at=created,delivered_at=delivered))
    assert not mb.received


@pytest.mark.parametrize('change',[
    ('native_v1q_recomputation_verified_in_this_run',False),
    ('factored_native_matrix_runs_in_source',15),
    ('new_native_scheduler_runs_in_this_module',1),
    ('receiver_exposed_to_allocation',True),
    ('native_scored_receiver_judgments',1),
    ('native_operator_updates',1),('native_learning_proven',True),
    ('causal_credit_or_utility_identified',True),
    ('allocation_order_variability_present',False),
    ('reference_v1q_sha256','not_a_hash'),
    ('source_kind','NATIVE_RECEIVER_CHANNEL'),
    ('schema','WRONG'),('status','WRONG'),
])
def test_untrusted_predecessor_metadata_rejected(change):
    r=specimen_r();r[change[0]]=change[1]
    with pytest.raises(InterventionError):validate_r(r,canon(r))


def test_noncanonical_predecessor_rejected():
    r=specimen_r()
    with pytest.raises(InterventionError):validate_r(r,json.dumps(r).encode())


def test_malformed_source_allocation_rejected():
    r=specimen_r();r['posthoc_rational_allocation']['off']['terminal']['suppress_activity']['equal_permutation_average']['A']='99'
    with pytest.raises(InterventionError):validate_r(r,canon(r))


def test_mismatched_policy_polarity_rejected():
    r=specimen_r();r['posthoc_rational_allocation']['off']['B->C:7->0']['preserve_activity']['equal_permutation_average']['A']='9/2'
    with pytest.raises(InterventionError):validate_r(r,canon(r))


def test_analysis_source_deterministic():
    r=specimen_r();b=canon(r)
    assert canon(analyze(r,b))==canon(analyze(json.loads(b),b))


def _cli_files(tmp_path,monkeypatch):
    root=tmp_path/'repo';root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    files={}
    for name in cli.NAMES:
        path=outside/(name+'.json')
        path.write_bytes(canon(specimen_r()) if name=='v1r' else b'{}\n')
        files[name]=path
    out=outside/'result.json'
    args=['--root',str(root)]
    for name in cli.NAMES:args+=['--'+name,str(files[name])]
    args+=['--out',str(out)]
    return files,out,args


def test_cli_success_only_when_replay_bytes_match(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    def replay(argv):
        Path(argv[-1]).write_bytes(files['v1r'].read_bytes())
        return 0
    monkeypatch.setattr(cli,'rmain',replay)
    assert cli.main(args)==0
    d=json.loads(out.read_bytes())
    assert d['inherited_native_v1r_recomputation_verified_in_this_run'] is True
    assert d['native_receiver_judgments']==0
    assert d['lab_case_count']==20


def test_cli_rejects_mismatched_predecessor_replay(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    def replay(argv):
        Path(argv[-1]).write_bytes(b'{}\n')
        return 0
    monkeypatch.setattr(cli,'rmain',replay)
    assert cli.main(args)==2
    assert not out.exists()


def test_cli_rejects_predecessor_replay_failure(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    monkeypatch.setattr(cli,'rmain',lambda argv:2)
    assert cli.main(args)==2
    assert not out.exists()


def test_cli_rejects_alias_of_report_paths(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    ix=args.index('--v1q')+1;args[ix]=str(files['v1r'])
    monkeypatch.setattr(cli,'rmain',lambda argv:0)
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_output_in_repo(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    out=tmp_path/'repo'/'output.json';args[-1]=str(out)
    assert cli.main(args)==2 and not out.exists()


def test_cli_rejects_existing_output(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    out.write_text('untouched')
    assert cli.main(args)==2 and out.read_text()=='untouched'


def test_cli_detects_mutated_source_after_replay(tmp_path,monkeypatch):
    files,out,args=_cli_files(tmp_path,monkeypatch)
    def replay(argv):
        Path(argv[-1]).write_bytes(files['v1r'].read_bytes())
        files['v1q'].write_bytes(b'{"changed":true}\n')
        return 0
    monkeypatch.setattr(cli,'rmain',replay)
    assert cli.main(args)==2 and not out.exists()
