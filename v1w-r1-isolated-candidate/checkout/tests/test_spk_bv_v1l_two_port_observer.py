"""BV v1l: bounded witness counterexamples and strict custody tests."""
from __future__ import annotations
import copy,hashlib,json
from dataclasses import replace
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.observer_closed_world_v1l import (
  Episode,validate_ep,run_lab,experiment_cases,audit,SCHEMA,STATUS)
from spk_bv_research.receiver_witness_boundary_v1k import (
  SCHEMA as K_SCHEMA,STATUS as K_STATUS,example_protocol)
from search import spk_bv_v1l_two_port_observer as cli

sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()

def provenance():
    jb,ib,hb,gb=[b'dummy '+s.encode() for s in ('v1j','v1i','v1h','v1g1')]
    k={'schema':K_SCHEMA,'status':K_STATUS,
       'native_v1j_recomputation_verified_in_this_run':True,
       'native_absence_witnesses':0,'endogenous_receiver_judgments':0,
       'native_updates_applied':0,'causal_credit_or_learning_proven':False,
       'shadow_scenarios_native_attested':0,'shadow_plan_supplied':False,
       'shadow_scenarios':[],
       'witness_authority_barrier':'UNTRUSTED_JSON_CANNOT_CERTIFY_NATIVE_EVENT_ABSENCE',
       'receiver_local_direct_scope':{
           'B':{'source':'A','direct':True,'missing_witnesses':True},
           'C':{'source':'B','direct_from_A':False,'missing_witnesses':True}},
       'reference_v1j_sha256':sha(jb),'reference_v1i_sha256':sha(ib),
       'reference_v1h_sha256':sha(hb),'reference_v1g1_sha256':sha(gb)}
    return k,canon(k),jb,ib,hb,gb

def test_demo_cases_cover_all_distinct_outcomes():
    rows=[run_lab(e) for e in experiment_cases()]
    assert len(rows)==10 and len(set(z['lab_scenario'] for z in rows))==10
    assert [z['classification'] for z in rows]==[
      'DELIVERED','SENDER_PORT_SILENCE','TRANSPORT_GAP','COVERAGE_LOSS',
      'COVERAGE_LOSS','COVERAGE_LOSS','PENDING','NO_EXPECTATION',
      'LATE_ACK','MISMATCHED_INGRESS']
    assert all(z['native_absence_witness'] is False and
               z['endogenous_value_judgment'] is False and
               z['sender_decision_cause_known_to_receiver'] is False for z in rows)

def test_same_receiver_projection_opposite_causes_without_two_port_taps():
    silence=run_lab(Episode('silent'))
    transport=run_lab(Episode('lost',sender_emit=True,receiver_ingress=False))
    assert silence['receiver_tap_saw_event'] is transport['receiver_tap_saw_event'] is False
    assert silence['classification']=='SENDER_PORT_SILENCE'
    assert transport['classification']=='TRANSPORT_GAP'
    assert silence['sender_tap_saw_event'] is False
    assert transport['sender_tap_saw_event'] is True

def test_control_independence_noninterference_and_control_channel_failure():
    base=Episode('a')
    other=replace(base,name='b',sender_emit=True)
    assert run_lab(base)['complete_independent_two_port_coverage_in_lab']
    assert run_lab(other)['complete_independent_two_port_coverage_in_lab']
    fail=replace(other,name='c',control_coverage_independent=False)
    assert run_lab(fail)['classification']=='COVERAGE_LOSS'
    assert run_lab(fail)['sender_tap_saw_event'] is None

def test_coverage_loss_blocks_false_absence_even_for_hidden_silence():
    for fld in ('sender_tap_covered','receiver_tap_covered','control_coverage_independent'):
        x=run_lab(replace(Episode('sample'),**{fld:False}))
        assert x['classification']=='COVERAGE_LOSS'
        assert x['missing_from_receiver_in_lab'] is None

def test_deadline_and_predecision_ack_rules_are_prioritized():
    assert run_lab(Episode('a',until_tick=9))['classification']=='PENDING'
    assert run_lab(Episode('b',receiver_ack_before_decision=False))['classification']=='LATE_ACK'
    assert run_lab(Episode('c',expectation_before_decision=False))['classification']=='NO_EXPECTATION'

def test_transport_gap_is_not_sender_suppression():
    x=run_lab(Episode('x',sender_emit=True))
    assert x['missing_from_receiver_in_lab'] is True
    assert x['classification']=='TRANSPORT_GAP'

def test_mismatched_id_or_ingress_without_emission_refuses_delivery():
    for x in (Episode('a',receiver_ingress=True),
              Episode('b',sender_emit=True,receiver_ingress=True,receiver_event_id='alien')):
        assert run_lab(x)['classification']=='MISMATCHED_INGRESS'

def test_reflexive_replay_is_pure():
    e=Episode('one',sender_emit=True,receiver_ingress=True)
    cp=copy.deepcopy(e)
    assert run_lab(e)==run_lab(e) and e==cp

@pytest.mark.parametrize('field,bad',[
    ('until_tick',False),('until_tick',-1),('until_tick',100001),
    ('until_tick','12'),('deadline_tick',3),('deadline_tick',3.3),
    ('name',''),('name','whitespace not allowed'),('name','ß'),
    ('sender_event_id',''),('sender_event_id','invalid id'),
    ('receiver_event_id',''),('receiver_event_id','invalid id'),
    ('expectation_before_decision',1),('receiver_ack_before_decision',None),
    ('sender_tap_covered',1),('receiver_tap_covered',None),
    ('control_coverage_independent','True'),('sender_emit',1),('receiver_ingress',None),
])
def test_reject_noncanonical_episode(field,bad):
    with pytest.raises(InterventionError):validate_ep(replace(Episode('valid'),**{field:bad}))

def test_no_dict_promoted_to_trusted_run():
    with pytest.raises(InterventionError):run_lab({'sender_emit':False,'authority':'NATIVE'})

def test_chain_audit_no_native_witness_or_learning_and_immutability():
    source=provenance();old=copy.deepcopy(source)
    r=audit(source[0],source[1],jbytes=source[2],ibytes=source[3],
            hbytes=source[4],gbytes=source[5],demo=True)
    assert source==old and r['schema']==SCHEMA and r['status']==STATUS
    assert r['native_absence_witnesses']==0 and r['native_scored_receiver_judgments']==0
    assert not r['native_v1k_recomputation_verified_in_this_run']
    assert not r['learning_or_causal_utility_identified']
    assert r['lab_cases_native_attested']==0 and len(r['lab_cases'])==10
    assert r['reference_v1k_sha256']==sha(source[1])

def test_audit_without_demo_has_no_lab_claim():
    k,kb,jb,ib,hb,gb=provenance()
    r=audit(k,kb,jbytes=jb,ibytes=ib,hbytes=hb,gbytes=gb)
    assert r['lab_cases']==[] and r['demo_lab_requested'] is False

@pytest.mark.parametrize('field,bad',[
    ('schema','counterfeit'),('status','counterfeit'),
    ('native_v1j_recomputation_verified_in_this_run',False),
    ('native_absence_witnesses',1),('endogenous_receiver_judgments',1),
    ('native_updates_applied',1),('causal_credit_or_learning_proven',True),
    ('shadow_scenarios_native_attested',1),
    ('witness_authority_barrier','PROMOTED'),
    ('receiver_local_direct_scope',{}),
    ('shadow_plan_supplied',1),
    ('reference_v1j_sha256','f'*64),('reference_v1h_sha256','f'*64),
    ('reference_v1g1_sha256','f'*64),('reference_v1i_sha256','f'*64),
])
def test_audit_reject_invalid_k(field,bad):
    k,kb,jb,ib,hb,gb=provenance();k[field]=bad
    with pytest.raises(InterventionError):audit(k,canon(k),jbytes=jb,ibytes=ib,hbytes=hb,gbytes=gb)

@pytest.mark.parametrize('idx',range(1,6))
def test_audit_reject_invalid_reference_bytes(idx):
    s=list(provenance());s[idx]+=b'changed'
    with pytest.raises((InterventionError,ValueError)):audit(s[0],s[1],jbytes=s[2],ibytes=s[3],hbytes=s[4],gbytes=s[5])

def test_audit_reject_forged_native_authority_even_if_source_bytes_agree():
    k,kb,jb,ib,hb,gb=provenance()
    k['native_absence_witnesses']=1
    with pytest.raises(InterventionError):audit(k,canon(k),jbytes=jb,ibytes=ib,hbytes=hb,gbytes=gb)

@pytest.mark.parametrize('wrong', [1,'true',[],None])
def test_audit_reject_invalid_demo_flag(wrong):
    s=provenance()
    with pytest.raises(InterventionError):audit(s[0],s[1],jbytes=s[2],ibytes=s[3],hbytes=s[4],gbytes=s[5],demo=wrong)


def fake_setup(tmp_path):
    k,kb,jb,ib,hb,gb=provenance()
    root=tmp_path/'project';root.mkdir()
    paths={}
    for n in cli.NAMES:
        path=tmp_path/(n+'.json')
        path.write_bytes({'v1k':kb,'v1j':jb,'v1i':ib,'v1h':hb,'v1g1':gb}.get(n,('mock '+n).encode()))
        paths[n]=path
    args=['--root',str(root)]
    for n in cli.NAMES:args+=['--'+n,str(paths[n])]
    out=tmp_path/'out.json'
    return k,paths,out,args+['--out',str(out)]

def test_cli_refuses_output_existing_before_native_replay(tmp_path,monkeypatch):
    k,paths,out,args=fake_setup(tmp_path);out.write_text('original')
    called=[]
    monkeypatch.setattr(cli,'kmain',lambda _:called.append(1) or 0)
    assert cli.main(args)==2 and not called and out.read_text()=='original'

def test_cli_refuses_aliased_source(tmp_path,monkeypatch):
    k,paths,out,args=fake_setup(tmp_path)
    # Both file names now refer to identical inode.
    paths['v1j'].unlink()
    paths['v1j'].hardlink_to(paths['v1i'])
    called=[];monkeypatch.setattr(cli,'kmain',lambda _:called.append(1) or 0)
    assert cli.main(args)==2 and not called

def test_cli_refuses_shadow_replay_if_not_exact_builtin_demo(tmp_path,monkeypatch):
    k,paths,out,args=fake_setup(tmp_path)
    k['shadow_plan_supplied']=True
    k['shadow_scenarios']=[{'shadow_protocol_sha256':'unexpected'}]
    paths['v1k'].write_bytes(canon(k))
    called=[];monkeypatch.setattr(cli,'kmain',lambda _:called.append(1) or 0)
    assert cli.main(args)==2 and not called

def test_cli_requires_byte_identical_v1k_rerun(tmp_path,monkeypatch):
    k,paths,out,args=fake_setup(tmp_path)
    monkeypatch.setattr(cli,'kmain',lambda argv:(Path(argv[-1]).write_text('{}') or 0))
    assert cli.main(args)==2 and not out.exists()

def test_cli_fake_replay_emits_restricted_report(tmp_path,monkeypatch):
    k,paths,out,args=fake_setup(tmp_path)
    def fake(argv):
        Path(argv[-1]).write_bytes(paths['v1k'].read_bytes())
        return 0
    monkeypatch.setattr(cli,'kmain',fake)
    assert cli.main(args+['--demo-lab'])==0
    j=json.loads(out.read_bytes())
    assert j['native_v1k_recomputation_verified_in_this_run'] is True
    assert len(j['lab_cases'])==10 and j['lab_cases_native_attested']==0
    assert j['native_scored_receiver_judgments']==0
    assert cli.main(args+['--demo-lab'])==2  # must not overwrite


def test_cross_seed_canonicalization_not_hidden_oracular_vote():
    s=provenance()
    a=audit(s[0],s[1],jbytes=s[2],ibytes=s[3],hbytes=s[4],gbytes=s[5],demo=True)
    b=audit(s[0],s[1],jbytes=s[2],ibytes=s[3],hbytes=s[4],gbytes=s[5],demo=True)
    assert canon(a)==canon(b)
    assert all(not x['sender_decision_cause_known_to_receiver'] for x in a['lab_cases'])
