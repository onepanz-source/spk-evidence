"""Synthetic contract/adversarial checks. Live-native acceptance needs fwork CLI."""
from __future__ import annotations
import copy,hashlib,json
from dataclasses import dataclass
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot,summarize
from spk_bv_research.native_network_counterfactual_v1h import (
  variant_forward_audit,SCHEMA as H_SCHEMA,STATUS as H_STATUS)
from spk_bv_research.native_route_lineage_v1g import (
  _index_forward,_edge,SCHEMA as G_SCHEMA,STATUS as G_STATUS)
from spk_bv_research.observer_closed_world_v1l import SCHEMA as L_SCHEMA,STATUS as L_STATUS
from spk_bv_research.native_passive_trace_projection_v1m import analyze,_extract,ROUTES,SCHEMA,STATUS
from search import spk_bv_v1m_native_passive_projection as cli

sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()

@dataclass(frozen=True)
class Route:
    source_node:str
    source_channel:int
    target_node:str
    target_channel:int
    target_pe:str
    delay_ticks:int=1

@dataclass(frozen=True)
class Fabric:
    static_routes:tuple


def specimen():
    fabric=Fabric((Route('A',7,'B',0,'PE1'),Route('B',7,'C',0,'PE2')))
    native=(('opaque_case',),fabric,('opaque_plans',))
    owners={'A':'PE0','B':'PE1','C':'PE2'}
    edges=[_edge(e,owners) for e in fabric.static_routes]
    def original_fw():
        emissions=[{'node_id':n,'channel':7,'timestamp':t} for n,t in
                   [('A',1),('B',2),('A',3),('C',3),('B',4),('C',5)]]
        names=[('r1','A','B',1,2,[],'PE0','PE1'),
               ('r2','B','C',2,3,['r1'],'PE1','PE2'),
               ('r3','A','B',3,4,[],'PE0','PE1'),
               ('r4','B','C',4,5,['r3'],'PE1','PE2')]
        occ=[{'id':oid,'source':src,'target':dst,'source_pe':spe,
              'target_pe':tpe,'channel':0,'emitted_at':te,'delivered_at':td,
              'delay':1,'parents':ps} for oid,src,dst,te,td,ps,spe,tpe in names]
        grants=[{'id':o['id'],'source':o['source'],'target':o['target'],
                 'source_pe':o['source_pe'],'target_pe':o['target_pe'],
                 'tick':o['emitted_at'],'delivered_at':o['delivered_at'],'wait':0}
                 for o in occ]
        batches=[{'node':'A','tick':1,'channels':[0],'parents':[]},
                 {'node':'B','tick':2,'channels':[0],'parents':['r1']},
                 {'node':'A','tick':3,'channels':[0],'parents':[]},
                 {'node':'C','tick':3,'channels':[0],'parents':['r2']},
                 {'node':'B','tick':4,'channels':[0],'parents':['r3']},
                 {'node':'C','tick':5,'channels':[0],'parents':['r4']}]
        return {'batches':batches,'emissions':emissions,
          'terminal':[x.copy() for x in emissions if x['node_id']=='C'],
          'link_grants':grants,'occurrences':occ,
          'states':{'A':0,'B':0,'C':0},'processed_batches':6,'processed_events':6}
    def variant_fw():
        return {'batches':[{'node':'A','tick':1,'channels':[0],'parents':[]},
                           {'node':'A','tick':3,'channels':[0],'parents':[]}],
           'emissions':[],'terminal':[],'link_grants':[],'occurrences':[],
           'states':{'A':0,'B':0,'C':0},'processed_batches':2,'processed_events':2}
    def scheduler(fw,on):
        return {'schema':'spk-bv-live-dual-event-scheduler/v0e',
           'enabled':on,'policy':'forward-first','forward':fw,
           'feedback':{'assessments':[],'deliveries':[],'link_grants':[],
                        'unique_receiver_votes':0},
           'resources':{'timeline':[],'contention':{},'bv_link_grants':0,
                        'bv_service_units':0,'bv_memory_units':0,
                        'forward_reserved_memory_units':0,'peak_cross_inflight':0}}
    runs={'original':{'off':scheduler(original_fw(),False),
                      'on':scheduler(original_fw(),True)},
          'variant':{'off':scheduler(variant_fw(),False),
                     'on':scheduler(variant_fw(),True)}}
    # Synthetic reports used only in the test; never represent native evidence.
    sources={'frozen-synthetic-source':'test'}
    g={'schema':G_SCHEMA,'status':G_STATUS,
       'frozen_native_sources':sources.copy(),
       'native_fixture_sha256':snapshot(native),'static_routes':edges,
       'original_forward_transport_grants_joined':True,
       'off_route_multiset_equal_on':True,'native_updates_applied':0,
       'original_off_occurrence_lineage':_index_forward(runs['original']['off']['forward'],edges)[1]}
    h={'schema':H_SCHEMA,'status':H_STATUS,
       'real_variant_full_fabric_replay':True,'native_updates_applied':0,
       'native_scored_receiver_judgments':0,'network_utility_identified':False,
       'variant_off_on_forward_outcomes_equal':True,'conditional_direct_A_to_C':False,
       'native_fixture_sha256':snapshot(native),'frozen_native_sources':sources}
    d={'experiment':'synthetic_fixture'};db=canon(d)
    gb=canon(g);h['reference_v1g1_file_sha256']=sha(gb)
    h['reference_v1d_file_sha256']=sha(db)
    for branch in runs:
        h[branch]={}
        for mode in ('off','on'):
            run=runs[branch][mode]
            h[branch][mode]=variant_forward_audit(run['forward'],edges)
            h[branch][mode+'_result_sha256']=summarize(run,enabled=mode=='on',
                                  priority='forward-first')['whole_result_sha256']
    hb=canon(h)
    l={'schema':L_SCHEMA,'status':L_STATUS,
       'native_v1k_recomputation_verified_in_this_run':True,
       'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
       'native_updates_applied':0,'lab_cases_native_attested':0,
       'learning_or_causal_utility_identified':False,
       'reference_v1h_sha256':sha(hb),'reference_v1g1_sha256':sha(gb),
       'demo_lab_requested':True,'lab_cases':[{'lab_scenario':str(i)} for i in range(10)]}
    lb=canon(l)
    return (l,lb,h,hb,g,gb,d,db,native,runs,owners,sources)

def report(s):return analyze(*s)


def test_native_posthoc_contract_synthetic_source_is_not_native_attestation():
    s=specimen();r=report(s)
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['full_native_scheduler_runs_recomputed_in_this_run']==4
    assert r['native_coverage_certificates']==0 and not r['native_learning_proven']
    assert not r['recipient_access_to_sender_trace_demonstrated']
    assert not r['native_two_port_independent_observer_installed']
    for mode in ('off','on'):
        original=r['native_trace_projection']['original'][mode]['edge_projections']
        variant=r['native_trace_projection']['variant'][mode]['edge_projections']
        assert [z['sender_trace_emission_count'] for z in original]==[2,2]
        assert [z['receiver_ingress_occurrence_count'] for z in original]==[2,2]
        assert [z['receiver_consumed_occurrence_count'] for z in original]==[2,2]
        assert [z['sender_trace_emission_count'] for z in variant]==[0,0]
        assert [z['receiver_ingress_occurrence_count'] for z in variant]==[0,0]
        assert all(not z['independent_two_port_coverage_certificate'] for z in original+variant)
        assert all(not z['receiver_native_received_sender_port_attestation'] for z in original+variant)


def test_summary_cross_seed_and_pure_no_mutation():
    s=specimen();before=copy.deepcopy(s)
    assert canon(report(s))==canon(report(s)) and s==before

@pytest.mark.parametrize('idx,key,value',[
  (0,'native_absence_witnesses',1),(0,'native_scored_receiver_judgments',1),
  (0,'lab_cases_native_attested',1),(0,'native_updates_applied',1),
  (0,'native_v1k_recomputation_verified_in_this_run',False),
  (2,'real_variant_full_fabric_replay',False),(2,'network_utility_identified',True),
  (2,'native_scored_receiver_judgments',1),(2,'native_updates_applied',1),
  (2,'variant_off_on_forward_outcomes_equal',False),
  (2,'conditional_direct_A_to_C',True),(4,'original_forward_transport_grants_joined',False),
  (4,'off_route_multiset_equal_on',False),(4,'native_updates_applied',1),
])
def test_reject_authority_promotion(idx,key,value):
    s=list(specimen());s[idx][key]=value
    with pytest.raises(InterventionError):report(s)

@pytest.mark.parametrize('idx,mutate',[
  (1,lambda x:b'bad'+x),(3,lambda x:x+b'bad'),
  (5,lambda x:b'bad'+x),(7,lambda x:b'bad'+x),
])
def test_reject_content_id_mutation(idx,mutate):
    s=list(specimen());s[idx]=mutate(s[idx])
    with pytest.raises(ValueError):report(s)

@pytest.mark.parametrize('change',[
  ('original','off','forward','emissions'),
  ('original','on','forward','occurrences'),
  ('variant','off','forward','batches'),
  ('variant','on','forward','terminal'),
])
def test_reject_native_execution_mutations(change):
    s=list(specimen());br,mode,_,field=change
    fw=s[9][br][mode]['forward']
    if field=='terminal':fw[field].append({'node_id':'A','channel':7,'timestamp':1})
    elif field=='batches':fw[field].append({'node':'C','tick':12,'parents':[],'channels':[]})
    elif field=='occurrences':fw[field][0]['target']='A'
    else:fw[field][0]['timestamp']=100
    with pytest.raises((InterventionError,KeyError,ValueError)):report(s)

@pytest.mark.parametrize('field',('id','source','target','source_pe','target_pe','delivered_at'))
def test_reject_corrupted_native_link_grant_join(field):
    s=list(specimen());grant=s[9]['original']['off']['forward']['link_grants'][0]
    grant[field]=('bad' if field!='delivered_at' else 1)
    with pytest.raises(InterventionError):report(s)


def test_reject_unaccounted_routed_variant_emission():
    s=list(specimen());s[9]['variant']['off']['forward']['emissions'].append(
       {'node_id':'A','channel':7,'timestamp':1})
    with pytest.raises(InterventionError):report(s)


def test_reject_wrong_original_ancestry_without_altering_counts():
    s=list(specimen());s[9]['original']['off']['forward']['occurrences'][1]['parents']=[]
    with pytest.raises(InterventionError):report(s)


def test_reject_routes_and_mutated_frozen_source():
    s=list(specimen());s[10]['C']='PE12'
    with pytest.raises(InterventionError):report(s)
    s=list(specimen());s[11]['other']='unexpected'
    with pytest.raises(InterventionError):report(s)


def dummy_cli(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    paths={}
    for name in cli.NAMES:
        p=tmp_path/(name+'.json');p.write_text('{}');paths[name]=p
    out=tmp_path/'result.json'
    argv=['--root',str(root)]
    for n in cli.NAMES:argv+=['--'+n,str(paths[n])]
    return paths,out,argv+['--out',str(out)]


def test_cli_prevents_existing_output_before_any_replay(tmp_path,monkeypatch):
    paths,out,argv=dummy_cli(tmp_path);out.write_text('do not overwrite')
    called=[]
    monkeypatch.setattr(cli,'lmain',lambda _:called.append(1))
    assert cli.main(argv)==2 and not called and out.read_text()=='do not overwrite'


def test_cli_prevents_aliasing_input_and_replay(tmp_path,monkeypatch):
    paths,out,argv=dummy_cli(tmp_path)
    paths['v1i'].unlink();paths['v1i'].hardlink_to(paths['v1h'])
    called=[];monkeypatch.setattr(cli,'lmain',lambda _:called.append(1))
    assert cli.main(argv)==2 and not called


def test_cli_prevents_absent_demo_provenance(tmp_path,monkeypatch):
    paths,out,argv=dummy_cli(tmp_path)
    called=[];monkeypatch.setattr(cli,'lmain',lambda _:called.append(1))
    assert cli.main(argv)==2 and not called


def test_cli_requires_byte_identical_replay(tmp_path,monkeypatch):
    paths,out,argv=dummy_cli(tmp_path)
    l={'demo_lab_requested':True,'lab_cases':[{}]*10}
    paths['v1l'].write_bytes(canon(l))
    def replay(args):Path(args[-1]).write_text('{}');return 0
    monkeypatch.setattr(cli,'lmain',replay)
    called=[];monkeypatch.setattr(cli,'native_execution',lambda *args:called.append(1))
    assert cli.main(argv)==2 and not called and not out.exists()


def test_cli_with_mocked_replay_enforces_scope_and_exclusive_output(tmp_path,monkeypatch):
    paths,out,argv=dummy_cli(tmp_path)
    s=specimen()
    for n,obj in [('v1l',s[0]),('v1h',s[2]),('v1g1',s[4]),('v1d',s[6])]:
        paths[n].write_bytes(canon(obj))
    def replay(args):Path(args[-1]).write_bytes(paths['v1l'].read_bytes());return 0
    monkeypatch.setattr(cli,'lmain',replay)
    monkeypatch.setattr(cli,'native_execution',lambda *args:s[8:])
    assert cli.main(argv)==0
    result=json.loads(out.read_bytes())
    assert result['schema']==SCHEMA and result['native_coverage_certificates']==0
    assert cli.main(argv)==2  # exclusive out
