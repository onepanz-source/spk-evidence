"""BV v1k: strict negative authority controls and replay-oriented CLI tests."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.receiver_witness_boundary_v1k import (
   audit,example_protocol,validate_shadow_protocol,shadow_classification,
   SCHEMA,STATUS,SHADOW_SCHEMA)
from spk_bv_research.receiver_silence_observability_v1j import SCHEMA as J_SCHEMA,STATUS as J_STATUS
from search import spk_bv_v1k_witness_authority as cli
sha=lambda x:hashlib.sha256(x).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,indent=2,ensure_ascii=True).encode()+b'\n'

def fixture():
    ib,bh,bg=b'v1i synthetic content',b'v1h synthetic content',b'v1g1 synthetic content'
    j={'schema':J_SCHEMA,'status':J_STATUS,'native_v1i_recomputation_verified_in_this_run':True,
       'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
       'shadow_absence_judgment_authorized':False,
       'sender_update_or_learning_proven':False,
       'absence_feedback_recoverable_from_variant_stream':False,
       'reference_v1i_sha256':sha(ib),'reference_v1h_sha256':sha(bh),
       'reference_v1g1_sha256':sha(bg),
       'source_bound_observers':[
         {'receiver':n,'relation_to_A':role,
          'native_observed_original_incoming_occurrences':2,
          'native_observed_variant_incoming_occurrences':0,
          'predeclared_expectation_evidence_available':False,
          'coverage_and_deadline_witness_available':False,
          'native_criterion_available':False,
          'variant_judgment':'NOT_IDENTIFIABLE_FROM_EVENT_ONLY_OBSERVATION',
          'independent_causal_vote':False}
         for n,role in (('B','DIRECT_A_TO_B'),('C','DESCENDANT_VIA_B'))]}
    return j,canon(j),ib,bh,bg

def run(f=None,shadow=None):
    j,jb,ib,hb,gb=f or fixture()
    return audit(j,jb,v1i_bytes=ib,v1h_bytes=hb,v1g1_bytes=gb,shadow=shadow)

def test_valid_report_no_upgrade_and_immutability():
    f=fixture();old=copy.deepcopy(f)
    r=run(f)
    assert f==old and r['schema']==SCHEMA and r['status']==STATUS
    assert not r['native_v1j_recomputation_verified_in_this_run']
    assert r['native_absence_witnesses']==r['endogenous_receiver_judgments']==0
    assert r['shadow_scenarios']==[] and not r['shadow_plan_supplied']
    assert r['receiver_local_direct_scope']['B']['direct'] is True
    assert r['receiver_local_direct_scope']['C']['direct_from_A'] is False
    assert r['witness_authority_barrier']=='UNTRUSTED_JSON_CANNOT_CERTIFY_NATIVE_EVENT_ABSENCE'
    assert not r['causal_credit_or_learning_proven']

def test_shadow_experiment_four_distinct_cases():
    shadow=[example_protocol(expectation_id='miss'),
            example_protocol(expectation_id='pending',deadline_tick=9),
            example_protocol(expectation_id='gap',coverage_end_tick=7),
            example_protocol(expectation_id='seen',observed_ids=['shadow.future.event.1'])]
    r=run(shadow=shadow)
    assert [x['classification'] for x in r['shadow_scenarios']]==[
        'DECLARED_EXPECTATION_MISSED_NO_NATIVE_CAUSAL_AUTHORITY',
        'DECLARED_EXPECTATION_PENDING','DECLARED_COVERAGE_GAP',
        'DECLARED_EVENTS_SEEN_WITHOUT_NATIVE_AUTHORITY']
    assert r['shadow_plan_supplied'] and r['shadow_scenarios_native_attested']==0
    assert all(not x['native_expected_event_authenticated'] and not x['native_coverage_proof_available']
               and not x['causal_sender_decision_identified'] and not x['native_judgment_authorized']
               for x in r['shadow_scenarios'])
    assert not r['causal_credit_or_learning_proven']

def test_shadow_deterministic_and_no_mutation():
    ps=[example_protocol()];copy_ps=copy.deepcopy(ps)
    assert run(shadow=ps)==run(shadow=ps) and ps==copy_ps

def test_observations_do_not_attest_producer():
    p=example_protocol(observed_ids=['shadow.future.event.1'])
    assert shadow_classification(p)=='DECLARED_EVENTS_SEEN_WITHOUT_NATIVE_AUTHORITY'
    assert not run(shadow=[p])['shadow_scenarios'][0]['native_expected_event_authenticated']

@pytest.mark.parametrize('field,bad',[
 ('schema','false'),('authority','NATIVE_ATTESTED'),('authority','SOURCE_SIGNED'),
 ('authority','RECEIVER_ATTESTED'),('sender','C'),('receiver','C'),
 ('sender_channel',0),('receiver_channel',7),('expected_count',0),('expected_count',17),
 ('expected_count',True),('expected_count',1.5),('decision_tick',0),('decision_tick',2),
 ('commit_tick',3),('receiver_ack_tick',3),('deadline_tick',3),('deadline_tick',8.5),
 ('observed_until_tick',-1),('coverage_start_tick',10),('coverage_end_tick',9),
 ('coverage_end_tick',True),('monitor_id','A'),('monitor_id','B'),
 ('expectation_id','not valid'),('criterion_id',''),('observed_ids',['shadow.future.event.1','shadow.future.event.1']),
 ('observed_ids',['x','y']),('observed_ids',('x',)),('observed_ids',[3]),
 ('expected_event_ids',[]),('expected_event_ids',['x','y']),
 ('expected_event_ids',['x','x']),('expected_event_ids',[False])])
def test_shadow_invalid_protocol_rejected(field,bad):
    p=example_protocol();p[field]=bad
    with pytest.raises(InterventionError):validate_shadow_protocol(p)

@pytest.mark.parametrize('field', ['episode_id','decision_id','receiver_ack_tick','coverage_end_tick','expected_event_ids','authority'])
def test_missing_shadow_field_rejected(field):
    p=example_protocol();p.pop(field)
    with pytest.raises(InterventionError):validate_shadow_protocol(p)

def test_unexpected_shadow_field_rejected():
    p=example_protocol();p['signed_witness']=True
    with pytest.raises(InterventionError):validate_shadow_protocol(p)

@pytest.mark.parametrize('field,bad',[
 ('schema','forged'),('status','forged'),('native_v1i_recomputation_verified_in_this_run',False),
 ('native_absence_witnesses',1),('native_scored_receiver_judgments',1),
 ('shadow_absence_judgment_authorized',True),('sender_update_or_learning_proven',True),
 ('absence_feedback_recoverable_from_variant_stream',True),('reference_v1i_sha256','1'*64),
 ('reference_v1h_sha256','1'*64),('reference_v1g1_sha256','1'*64)])
def test_j_report_tamper_rejected(field,bad):
    f=list(fixture());f[0][field]=bad
    with pytest.raises(InterventionError):run(f)

@pytest.mark.parametrize('which', ['v1i','v1h','v1g1','missing'])
def test_reference_bytes_tampered(which):
    f=list(fixture())
    if which=='missing':f[1]=b''
    else:f[{'v1i':2,'v1h':3,'v1g1':4}[which]]+=b'tampered'
    with pytest.raises(InterventionError):run(f)

@pytest.mark.parametrize('row,field,bad',[
 (0,'receiver','C'),(0,'relation_to_A','DESCENDANT_VIA_B'),
 (0,'native_observed_variant_incoming_occurrences',1),
 (0,'predeclared_expectation_evidence_available',True),
 (0,'coverage_and_deadline_witness_available',True),
 (0,'native_criterion_available',True),
 (0,'variant_judgment','APPROVES'),
 (1,'independent_causal_vote',True),
 (1,'relation_to_A','DIRECT_A_TO_B'),
 (1,'native_observed_original_incoming_occurrences',3),
 ])
def test_receiver_evidence_tampering_rejected(row,field,bad):
    f=list(fixture());f[0]['source_bound_observers'][row][field]=bad
    with pytest.raises(InterventionError):run(f)

@pytest.mark.parametrize('shadow', [[],[example_protocol(),example_protocol()],
    [example_protocol(receiver='C')],list(range(9)), 'not list'])
def test_shadow_list_safety(shadow):
    with pytest.raises(InterventionError):run(shadow=shadow)


def cli_setup(tmp_path):
    root=tmp_path/'checkout';root.mkdir()
    fake=fixture();src={'v1j':fake[1],'v1i':fake[2],'v1h':fake[3],'v1g1':fake[4]}
    paths={}
    for name in cli.NAMES:
        p=tmp_path/(name+'.json');p.write_bytes(src.get(name,('reference '+name).encode()));paths[name]=p
    out=tmp_path/'report.json'
    args=['--root',str(root)]
    for name in cli.NAMES:args+=['--'+name,str(paths[name])]
    args+=['--out',str(out)]
    return paths,out,args

def stub_replay(monkeypatch,*,error=False,corrupt=False):
    def fake(args):
        if error:return 2
        dest=Path(args[args.index('--out')+1]);b=fixture()[1];dest.write_bytes(b+(b'\n' if corrupt else b''));return 0
    monkeypatch.setattr(cli,'jmain',fake)

def test_cli_replay_and_existing_output_rejected(tmp_path,monkeypatch):
    paths,out,args=cli_setup(tmp_path);stub_replay(monkeypatch)
    assert cli.main(args)==0
    r=json.loads(out.read_bytes())
    assert r['native_v1j_recomputation_verified_in_this_run'] is True
    assert r['reference_v1j_sha256']==sha(paths['v1j'].read_bytes())
    before=out.read_bytes();assert cli.main(args)==2 and out.read_bytes()==before

def test_cli_demo_invariant(tmp_path,monkeypatch):
    paths,out,args=cli_setup(tmp_path);stub_replay(monkeypatch)
    assert cli.main(args+['--demo-shadow'])==0
    r=json.loads(out.read_bytes());assert len(r['shadow_scenarios'])==4
    assert r['native_absence_witnesses']==r['shadow_scenarios_native_attested']==0

@pytest.mark.parametrize('kind',['error','corrupt','missing','symlink','hardlink','existing','inside','both','badshadow'])
def test_cli_fails_closed(tmp_path,monkeypatch,kind):
    paths,out,args=cli_setup(tmp_path);stub_replay(monkeypatch,error=kind=='error',corrupt=kind=='corrupt')
    if kind=='missing':paths['v1j'].unlink()
    if kind=='symlink':paths['v1i'].unlink();paths['v1i'].symlink_to(paths['v1j'])
    if kind=='hardlink':paths['v1i'].unlink();paths['v1i'].hardlink_to(paths['v1j'])
    if kind=='existing':out.write_text('KEEP')
    if kind=='inside':args[args.index('--out')+1]=str(tmp_path/'checkout'/'inside.json')
    if kind=='both':args+=['--demo-shadow']
    if kind in ('both','badshadow'):
        f=tmp_path/'shadow.json';f.write_text('[]' if kind=='badshadow' else '[]')
        args+=['--shadow-protocol',str(f)]
    assert cli.main(args)==2
    assert not out.exists() or (kind=='existing' and out.read_text()=='KEEP')

def test_cli_external_protocol_never_native(tmp_path,monkeypatch):
    paths,out,args=cli_setup(tmp_path);stub_replay(monkeypatch)
    p=tmp_path/'shadow.json';p.write_text(json.dumps([example_protocol()]))
    assert cli.main(args+['--shadow-protocol',str(p)])==0
    r=json.loads(out.read_bytes())
    assert len(r['shadow_scenarios'])==1
    assert r['shadow_scenarios'][0]['classification'].startswith('DECLARED_EXPECTATION_MISSED')
    assert r['shadow_scenarios_native_attested']==0
