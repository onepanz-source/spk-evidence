"""v1j research-only source-bound silence and observer-contract adversarial controls."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_feedback_silence_v1i import audit as audit_i
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA,STATUS as H_STATUS
from spk_bv_research.native_route_lineage_v1g import SCHEMA as G_SCHEMA,STATUS as G_STATUS
from spk_bv_research.receiver_silence_observability_v1j import audit,classify_silence,SCHEMA,STATUS
from search import spk_bv_v1j_silence_observability as cli

sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,indent=2).encode()+b'\n'
DB=b'synthetic valid v1d'  # Independent of architecture; an anchored contract double.

def scenario():
    g={'schema':G_SCHEMA,'status':G_STATUS,
       'original_forward_transport_grants_joined':True,
       'off_route_multiset_equal_on':True,
       'original_off_occurrences':4,'original_on_occurrences':4,
       'native_feedback_assessment_count':2,'native_reverse_delivery_count':4,
       'endogenous_receiver_judgments':0,'native_updates_applied':0,
       'static_routes':[
          dict(source_node='A',source_channel=7,target_node='B',target_channel=0,
               source_pe='PE0',target_pe='PE1',delay_ticks=1),
          dict(source_node='B',source_channel=7,target_node='C',target_channel=0,
               source_pe='PE1',target_pe='PE2',delay_ticks=1)],
       'original_off_occurrence_lineage':[
          dict(id='r1',source='A',target='B',sender_channel=7,receiver_channel=0,
               source_pe='PE0',target_pe='PE1',emitted_at=1,delivered_at=2,parents=[]),
          dict(id='r2',source='B',target='C',sender_channel=7,receiver_channel=0,
               source_pe='PE1',target_pe='PE2',emitted_at=2,delivered_at=3,parents=['r1']),
          dict(id='r3',source='A',target='B',sender_channel=7,receiver_channel=0,
               source_pe='PE0',target_pe='PE1',emitted_at=3,delivered_at=4,parents=[]),
          dict(id='r4',source='B',target='C',sender_channel=7,receiver_channel=0,
               source_pe='PE1',target_pe='PE2',emitted_at=4,delivered_at=5,parents=['r3'])],
       'native_reverse_deliveries':[
         dict(assessment_id='a1',sender='C',receiver='B',evidence_ids=['r2'],delivered_at=6,native_independent_receiver_flag=True),
         dict(assessment_id='a2',sender='C',receiver='B',evidence_ids=['r4'],delivered_at=7,native_independent_receiver_flag=True),
         dict(assessment_id='a1',sender='B',receiver='A',evidence_ids=['r1'],delivered_at=8,native_independent_receiver_flag=True),
         dict(assessment_id='a2',sender='B',receiver='A',evidence_ids=['r3'],delivered_at=9,native_independent_receiver_flag=True)],
       'conditional_receiver_route_audit':[
         dict(receiver_id='B',direct_static_route_7_to_0=True,
              direct_original_forward_occurrences=2,observed_original_forward_ancestry_from_A=True,
              v1e_variant_network_route_replayed=False,native_criterion_or_judgment_from_receiver=False),
         dict(receiver_id='C',direct_static_route_7_to_0=False,
              direct_original_forward_occurrences=0,observed_original_forward_ancestry_from_A=True,
              v1e_variant_network_route_replayed=False,native_criterion_or_judgment_from_receiver=False)]}
    gb=canon(g)
    def arm(original):
        return dict(batches=6 if original else 2,emissions=6 if original else 0,
                    link_grants=4 if original else 0,occurrences=4 if original else 0,
                    terminal=2 if original else 0,
                    edges={'A->B:7->0':2,'B->C:7->0':2} if original else {},
                    states_sha256=sha(b'origin' if original else b'variant'))
    def family(orig):
        v=arm(orig)
        return {'off':copy.deepcopy(v),'on':copy.deepcopy(v),
                'off_result_sha256':sha(b'run'+bytes([orig])+b'off'),
                'on_result_sha256':sha(b'run'+bytes([orig])+b'on')}
    h={'schema':H_SCHEMA,'status':H_STATUS,'real_variant_full_fabric_replay':True,
       'experiment_kind':'PRE_EPISODE_COPY_INTERVENTION',
       'conditional_direct_A_to_C':False,'v1e_hypothetical_A_to_C_direct_promoted':False,
       'variant_off_on_forward_outcomes_equal':True,
       'reference_v1g1_file_sha256':sha(gb),'reference_v1d_file_sha256':sha(DB),
       'frozen_native_sources':{'A1':'frozen'},'native_fixture_sha256':sha(b'fixture'),
       'intervention':{'sender':'A','instruction_index':2,'original_instruction':['CMP',1],
                       'variant_instruction':['CMP',2], 'original_nodes_unchanged':True,
                       'static_fabric_shared_immutable':True,'external_events_preserved':True},
       'native_scored_receiver_judgments':0,'native_updates_applied':0,
       'native_learning_proven':False,'network_utility_identified':False,
       'native_feedback_assessments':{'original_on':2,'variant_on':0},
       'native_feedback_deliveries':{'original_on':4,'variant_on':0},
       'original':family(True),'variant':family(False)}
    for a in ('off','on'):
        h[a+'_variant_minus_original']={k:h['variant'][a][k]-h['original'][a][k]
              for k in ('batches','emissions','link_grants','occurrences','terminal')}
    hb=canon(h)
    i=audit_i(h,hb,g_bytes=gb,d_bytes=DB)
    i['native_v1h_recomputation_verified_in_this_run']=True
    ib=canon(i)
    return i,ib,h,hb,g,gb

def run(s):
    i,ib,h,hb,g,gb=s
    return audit(i,ib,v1h=h,v1h_bytes=hb,v1g1=g,v1g1_bytes=gb,v1d_bytes=DB)

def test_valid_reconstructed_boundary():
    s=scenario(); old=copy.deepcopy(s);r=run(s)
    assert s==old and r['schema']==SCHEMA and r['status']==STATUS
    assert r['native_v1i_recomputation_verified_in_this_run'] is False
    assert r['original_native_routes_and_feedback_verified']
    assert r['original_assessments_native']==2
    assert r['original_reverse_deliveries_native']==4
    assert r['variant_native_assessments']==r['variant_native_reverse_deliveries']==0
    assert r['native_absence_witnesses']==0 and not r['shadow_absence_judgment_authorized']
    assert [x['relation_to_A'] for x in r['source_bound_observers']]==['DIRECT_A_TO_B','DESCENDANT_VIA_B']
    assert [x['native_observed_variant_incoming_occurrences'] for x in r['source_bound_observers']]==[0,0]
    assert all(x['variant_judgment']=='NOT_IDENTIFIABLE_FROM_EVENT_ONLY_OBSERVATION'
               for x in r['source_bound_observers'])
    assert not r['sender_update_or_learning_proven']

def test_shadow_classifications():
    assert classify_silence(received=1)=='OBSERVED_EVENTS_NO_UTILITY_INFERRED'
    assert classify_silence(received=0)=='SILENCE_WITHOUT_POSITIVE_EXPECTATION'
    assert classify_silence(received=0,expected=0)=='SILENCE_WITHOUT_POSITIVE_EXPECTATION'
    assert classify_silence(received=0,expected=2)=='UNRESOLVED_SHADOW_EXPECTATION_NO_DEADLINE'
    assert classify_silence(received=0,expected=2,deadline=5,observed_until=4,coverage_declared=True)=='PENDING_SHADOW_EXPECTATION'
    assert classify_silence(received=0,expected=2,deadline=5,observed_until=5)=='UNCOVERED_SHADOW_EXPECTATION'
    assert classify_silence(received=0,expected=2,deadline=5,observed_until=5,coverage_declared=True)=='MISSED_DECLARED_EXPECTATION_NOT_SOURCE_ATTESTED'

@pytest.mark.parametrize('kw',[{'received':True},{'received':-1},{'received':0,'expected':-1},
 {'received':0,'expected':1.1},{'received':0,'deadline':1},
 {'received':0,'coverage_declared':True},{'received':0,'expected':1,'deadline':1},
 {'received':0,'expected':1,'observed_until':1},
 {'received':0,'expected':1,'coverage_declared':1},
 {'received':0,'expected':None,'observed_until':0,'deadline':1},
 {'received':0,'expected':1,'deadline':-1,'observed_until':2},
 {'received':0,'expected':1,'deadline':2,'observed_until':-2}])
def test_bad_shadow_observer_contract(kw):
    with pytest.raises(InterventionError):classify_silence(**kw)

@pytest.mark.parametrize('key,bad',[('schema','forged'),('status','forged'),
 ('native_v1h_recomputation_verified_in_this_run',False),
 ('native_scored_receiver_judgments',1),('native_updates_applied',1),
 ('learning_proven',True),('variant_receiver_judgment_sign','POSITIVE'),
 ('reference_v1h_sha256','0'*64),('reference_v1g1_sha256','0'*64),
 ('reference_v1d_sha256','0'*64)])
def test_corrupt_v1i_rejected(key,bad):
    s=list(scenario());s[0][key]=bad
    with pytest.raises(InterventionError):run(s)

@pytest.mark.parametrize('field,bad',[('schema','forged'),('status','forged'),
 ('real_variant_full_fabric_replay',False),('native_feedback_assessments',{'original_on':2,'variant_on':1}),
 ('native_feedback_deliveries',{'original_on':4,'variant_on':1}),
 ('reference_v1g1_file_sha256','b'*64)])
def test_corrupt_v1h_rejected(field,bad):
    s=list(scenario());s[2][field]=bad
    with pytest.raises(InterventionError):run(s)

@pytest.mark.parametrize('field,bad',[('schema','forged'),('status','forged'),
 ('original_forward_transport_grants_joined',False),
 ('off_route_multiset_equal_on',False),('original_off_occurrences',3),
 ('native_feedback_assessment_count',3),('native_reverse_delivery_count',3),
 ('endogenous_receiver_judgments',1),('native_updates_applied',1),
 ('static_routes',[]),('original_off_occurrence_lineage',[]),
 ('native_reverse_deliveries',[])])
def test_corrupt_original_evidence_rejected(field,bad):
    s=list(scenario());s[4][field]=bad
    with pytest.raises(InterventionError):run(s)

@pytest.mark.parametrize('row,field,bad',[(0,'source','C'),(0,'parents',['r2']),
 (1,'parents',[]),(1,'parents',['r4']),(1,'emitted_at',1),
 (2,'id','r1'),(2,'delivered_at',0),(3,'receiver_channel',1)])
def test_corrupt_forward_lineage_rejected(row,field,bad):
    s=list(scenario());s[4]['original_off_occurrence_lineage'][row][field]=bad
    with pytest.raises(InterventionError):run(s)

@pytest.mark.parametrize('row,field,bad',[(0,'sender','A'),(0,'receiver','C'),
 (0,'evidence_ids',['r1']),(0,'delivered_at',2),
 (1,'assessment_id','a1'),(2,'sender','C'),(3,'evidence_ids',['r2'])])
def test_corrupt_reverse_lineage_rejected(row,field,bad):
    s=list(scenario());s[4]['native_reverse_deliveries'][row][field]=bad
    with pytest.raises(InterventionError):run(s)

@pytest.mark.parametrize('which', ['hbytes','gbytes','dbytes','ibytes'])
def test_corrupt_reference_bytes_rejected(which):
    i,ib,h,hb,g,gb=scenario()
    kwargs=dict(v1h=h,v1h_bytes=hb,v1g1=g,v1g1_bytes=gb,v1d_bytes=DB)
    if which=='hbytes':kwargs['v1h_bytes']=hb+b' '
    if which=='gbytes':kwargs['v1g1_bytes']=gb+b' '
    if which=='dbytes':kwargs['v1d_bytes']=DB+b' '
    if which=='ibytes':ib=b''
    with pytest.raises(InterventionError):audit(i,ib,**kwargs)


def test_determinism():assert run(scenario())==run(scenario())

def setup_cli(tmp_path):
    root=tmp_path/'checkout';root.mkdir();docs={}
    i,ib,h,hb,g,gb=scenario()
    content={'v1i':ib,'v1h':hb,'v1g1':gb,'v1d':DB}
    for name in cli.NAMES:
        p=tmp_path/(name+'.json');p.write_bytes(content.get(name,(name+' reference').encode()))
        docs[name]=p
    out=tmp_path/'output.json'
    args=['--root',str(root)]
    for name in cli.NAMES:args+=['--'+name,str(docs[name])]
    args+=['--out',str(out)]
    return docs,out,args

def stub_replay(monkeypatch,*,fail=False,alter=False):
    def fake(argv):
        if fail:return 2
        dest=Path(argv[argv.index('--out')+1])
        # v1i is not an argument to the nested v1i executor; an experiment double
        # can only reconstruct the recorded synthetic source by running our fixture.
        b=scenario()[1]
        dest.write_bytes(b+(b' ' if alter else b''));return 0
    monkeypatch.setattr(cli,'imain',fake)

def test_cli_valid_replay_and_refuse_overwrite(tmp_path,monkeypatch):
    docs,out,args=setup_cli(tmp_path);stub_replay(monkeypatch)
    assert cli.main(args)==0
    r=json.loads(out.read_bytes());assert r['native_v1i_recomputation_verified_in_this_run'] is True
    assert r['reference_v1i_sha256']==sha(docs['v1i'].read_bytes())
    prev=out.read_bytes();assert cli.main(args)==2 and out.read_bytes()==prev

@pytest.mark.parametrize('kind',['fail','alter','missing','symlink','hardlink','external','existing'])
def test_cli_fail_closed(tmp_path,monkeypatch,kind):
    docs,out,args=setup_cli(tmp_path);stub_replay(monkeypatch,fail=kind=='fail',alter=kind=='alter')
    if kind=='missing':docs['v1i'].unlink()
    if kind=='symlink':docs['v1h'].unlink();docs['v1h'].symlink_to(docs['v1i'])
    if kind=='hardlink':docs['v1h'].unlink();docs['v1h'].hardlink_to(docs['v1i'])
    if kind=='external':
        args[args.index('--out')+1]=str(tmp_path/'checkout'/'inside.json')
    if kind=='existing':out.write_text('KEEP')
    assert cli.main(args)==2
    assert not out.exists() or (kind=='existing' and out.read_text()=='KEEP')
