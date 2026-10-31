"""BV v1n: adversarial finite knowledge boundary; native acceptance via fwork CLI."""
from __future__ import annotations
import copy,hashlib,json
from dataclasses import dataclass
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError, snapshot, summarize
from spk_bv_research.native_network_counterfactual_v1h import (
    variant_forward_audit, SCHEMA as H_SCHEMA, STATUS as H_STATUS)
from spk_bv_research.native_route_lineage_v1g import (
    _index_forward, _edge, SCHEMA as G_SCHEMA, STATUS as G_STATUS)
from spk_bv_research.observer_closed_world_v1l import (
    SCHEMA as L_SCHEMA, STATUS as L_STATUS)
from spk_bv_research.receiver_knowledge_disclosure_v1n import (
    analyze, _world, _project, _distinguishing_tier, TIERS,SCHEMA,STATUS)
from spk_bv_research.native_passive_trace_projection_v1m import analyze as m_analyze
from search import spk_bv_v1n_knowledge_disclosure as cli
# Private, deterministic fixture for the v1n tests. Never depend on another
# pytest test module being importable as a global Python module.
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


sha=lambda data:hashlib.sha256(data).hexdigest()

def specimen_n():
    prior=list(specimen())
    # Synthetic previous report supplies precisely the same negative claim as
    # the real v1h, with the correct content-linked reference updates.
    prior[2]['native_learning_proven']=False
    prior[3]=canon(prior[2])
    prior[0]['reference_v1h_sha256']=sha(prior[3])
    prior[1]=canon(prior[0])
    m=m_analyze(*prior);mb=canon(m)
    return [m,mb,prior[0],prior[1],prior[2],prior[3],
            prior[4],prior[5],prior[6],prior[7]]

def outcome(inputs=None):
    return analyze(*(specimen_n() if inputs is None else inputs))


def test_two_native_branches_bound_four_scheduler_arms():
    r=outcome()
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['native_traces_in_v1m']==4
    assert r['native_original_edge_A_B']=={'sender_emissions':2,'receiver_ingress':2}
    assert r['native_variant_edge_A_B']=={'sender_emissions':0,'receiver_ingress':0}
    assert r['attested_direct_A_to_B'] and not r['attested_direct_A_to_C']


def test_authority_never_claims_native_receiver_view():
    r=outcome()
    for flag in ('native_full_two_port_observer_present',
                 'native_disclosure_channel_to_receiver_present',
                 'native_receiver_can_identify_missing_sender_decision',
                 'native_learning_proven','native_v1m_recomputation_verified_in_this_run'):
        assert r[flag] is False
    for field in ('native_absence_witnesses','native_scored_receiver_judgments',
                  'native_operator_updates'):
        assert r[field]==0
    assert all(not tier['native_receiver_disclosure_available'] for tier in r['shadow_projection_tiers'])
    assert all(w['world_origin']=='HYPOTHETICAL_NOT_EXECUTED' for w in r['shadow_worlds'][2:])


def test_distinguishability_is_graded_not_truth():
    r=outcome()
    assert len(r['shadow_worlds'])==8 and len(r['shadow_projection_tiers'])==4
    assert [p['first_distinguishable_at'] for p in r['shadow_distinguishability_tests']]==[
        'T1_PLUS_SENDER_PORT_DISCLOSURE',
        'T1_PLUS_SENDER_PORT_DISCLOSURE',
        'T2_PLUS_PREDECISION_EXPECTATION',
        'T3_PLUS_INDEPENDENT_INTERVAL_COVERAGE',
        'NOT_DISTINGUISHABLE_THROUGH_T3']
    assert [len(p['equivalence_classes']) for p in r['shadow_projection_tiers']]==[2,3,5,6]


def test_native_ingress_has_indistinguishable_undelivered_shadow_world():
    r=outcome();lookup={w['world_id']:w for w in r['shadow_worlds']}
    assert _project(lookup['NATIVE_VARIANT_POSTHOC'],('ingress_count',))==_project(
        lookup['SHADOW_EMITTED_NOT_DELIVERED'],('ingress_count',))
    assert _project(lookup['NATIVE_VARIANT_POSTHOC'],('sender_port_count',))!=_project(
        lookup['SHADOW_EMITTED_NOT_DELIVERED'],('sender_port_count',))


def test_cause_remains_ambiguous_even_if_all_hypothetical_tiers_are_given():
    r=outcome();lookup={w['world_id']:w for w in r['shadow_worlds']}
    a=lookup['SHADOW_INTERNAL_CAUSE_A'];b=lookup['SHADOW_INTERNAL_CAUSE_B']
    assert a['hidden_decision_cause']!=b['hidden_decision_cause']
    assert all(_project(a,fields)==_project(b,fields) for _,fields in TIERS)
    assert _distinguishing_tier(a,b)=='NOT_DISTINGUISHABLE_THROUGH_T3'


def test_source_bound_pure_and_stable():
    inp=specimen_n();unchanged=copy.deepcopy(inp)
    assert canon(outcome(inp))==canon(outcome(inp)) and inp==unchanged


@pytest.mark.parametrize('index,key,value',[
   (0,'full_native_scheduler_runs_recomputed_in_this_run',3),
   (0,'inherited_native_v1l_recomputation_verified_in_this_run',False),
   (0,'native_coverage_certificates',1),
   (0,'endogenous_receiver_judgments',1),
   (0,'sender_operator_updates',1),
   (0,'native_learning_proven',True),
   (0,'recipient_access_to_sender_trace_demonstrated',True),
   (0,'native_two_port_independent_observer_installed',True),
   (0,'cross_world_occurrence_identity_claimed',True),
   (0,'causal_sender_decision_identified_by_receiver',True),
   (0,'native_trace_source_emission_count_original_vs_variant',{'A':[1,0],'B':[2,0]}),
   (0,'source_kind','RECEIVER_NATIVE'),
   (0,'native_fixture_sha256','0'*64),
   (0,'frozen_native_sources',{}),
   (2,'lab_cases_native_attested',1),
   (2,'native_absence_witnesses',1),
   (2,'native_scored_receiver_judgments',1),
   (2,'native_updates_applied',1),
   (2,'native_v1k_recomputation_verified_in_this_run',False),
   (4,'real_variant_full_fabric_replay',False),
   (4,'native_learning_proven',True),
   (4,'native_updates_applied',1),
   (4,'network_utility_identified',True),
   (4,'conditional_direct_A_to_C',True),
   (6,'original_forward_transport_grants_joined',False),
   (6,'native_updates_applied',1),
])
def test_reject_authority_and_identity_promotion(index,key,value):
    s=specimen_n();s[index][key]=value
    with pytest.raises(InterventionError):outcome(s)


@pytest.mark.parametrize('index', [1,3,5,7,9])
def test_reject_changed_source_bytes(index):
    s=specimen_n();s[index]=s[index]+b'\n'
    with pytest.raises((InterventionError,ValueError)):outcome(s)


@pytest.mark.parametrize('tag',[
    ('original','off','sender_trace_emission_count',3),
    ('original','on','receiver_ingress_occurrence_count',1),
    ('variant','off','sender_trace_emission_count',1),
    ('variant','on','receiver_consumed_occurrence_count',1),
    ('original','off','receiver_native_received_sender_port_attestation',True),
    ('variant','on','independent_two_port_coverage_certificate',True),
    ('original','off','posthoc_trace_classification','NO_SOURCE_CHANNEL_EVENT_IN_BOUNDED_RUN_TRACE'),
    ('variant','off','posthoc_trace_classification','ROUTED_EVENTS_IN_COMPLETE_RUN_TRACE'),
    ('original','off','sender','B'),
    ('original','off','receiver','C'),
    ('original','off','edge','A->C:7->0'),
    ('original','off','sender_channel',0),
    ('variant','off','receiver_channel',7),
    ('original','on','sender_emission_timestamps',[9,10]),
    ('original','on','ingress_occurrence_ids',['r1','r1']),
    ('original','on','sender_trace_emission_count',True),
])
def test_reject_tampered_endpoint_projection(tag):
    b,mode,key,value=tag;s=specimen_n()
    s[0]['native_trace_projection'][b][mode]['edge_projections'][0][key]=value
    with pytest.raises(InterventionError):outcome(s)


@pytest.mark.parametrize('branch,mode,key,value',[
    ('original','off','native_external_observer_present',True),
    ('variant','on','native_absence_certificate_count',1),
    ('original','on','native_full_scheduler_executed',False),
    ('variant','off','posthoc_simulator_trace_reader_only',False),
])
def test_reject_promoted_arm(branch,mode,key,value):
    s=specimen_n();s[0]['native_trace_projection'][branch][mode][key]=value
    with pytest.raises(InterventionError):outcome(s)


@pytest.mark.parametrize('w',[
    ('bad',-1,0,None,False,'x','y'),
    ('bad',1,0,None,False,'x','y'),
    ('bad',0,0,'false',False,'x','y'),
    ('bad',0,0,None,1,'x','y'),
    ('bad',True,1,None,False,'x','y'),
])
def test_reject_ill_typed_shadow_world(w):
    with pytest.raises(InterventionError):_world(*w)


def inputs_and_cli(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    paths={}
    for n in cli.NAMES:
        p=tmp_path/(n+'.json');p.write_text('{}');paths[n]=p
    out=tmp_path/'out.json'
    args=['--root',str(root)]
    for n in cli.NAMES:args+=['--'+n,str(paths[n])]
    args+=['--out',str(out)]
    return paths,out,args


def test_cli_exclusive_creation_before_replay(tmp_path,monkeypatch):
    paths,out,args=inputs_and_cli(tmp_path);out.write_text('keep')
    calls=[];monkeypatch.setattr(cli,'mmain',lambda _:calls.append('bad'))
    assert cli.main(args)==2 and out.read_text()=='keep' and not calls


def test_cli_rejects_aliases_and_symlinks(tmp_path,monkeypatch):
    paths,out,args=inputs_and_cli(tmp_path)
    paths['v1l'].unlink(); paths['v1l'].hardlink_to(paths['v1h'])
    calls=[];monkeypatch.setattr(cli,'mmain',lambda _:calls.append('bad'))
    assert cli.main(args)==2 and not calls
    paths['v1l'].unlink();paths['v1l'].symlink_to(paths['v1h'])
    assert cli.main(args)==2 and not calls


def test_cli_rejects_mismatched_prior_replay(tmp_path,monkeypatch):
    paths,out,args=inputs_and_cli(tmp_path)
    s=specimen_n()
    for name,item in [('v1m',s[0]),('v1l',s[2]),('v1h',s[4]),('v1g1',s[6]),('v1d',s[8])]:
        paths[name].write_bytes(canon(item))
    def wrong_replay(command):
        Path(command[-1]).write_text('{}');return 0
    monkeypatch.setattr(cli,'mmain',wrong_replay)
    assert cli.main(args)==2 and not out.exists()


def test_cli_mocked_replay_preserves_provenance_and_idempotent_output(tmp_path,monkeypatch):
    paths,out,args=inputs_and_cli(tmp_path)
    s=specimen_n()
    for name,item in [('v1m',s[0]),('v1l',s[2]),('v1h',s[4]),('v1g1',s[6]),('v1d',s[8])]:
        paths[name].write_bytes(canon(item))
    def reproduce(command):
        Path(command[-1]).write_bytes(paths['v1m'].read_bytes());return 0
    monkeypatch.setattr(cli,'mmain',reproduce)
    assert cli.main(args)==0
    r=json.loads(out.read_bytes())
    assert r['native_v1m_recomputation_verified_in_this_run'] is True
    assert r['native_absence_witnesses']==0
    assert cli.main(args)==2


def test_attestation_hash_format_and_synthetic_non_promotability():
    r=outcome()
    for n in ('v1m','v1l','v1h','v1g1','v1d'):
        value=r['reference_'+n+'_sha256']
        assert len(value)==64 and all(c in '0123456789abcdef' for c in value)
    assert r['shadow_tier_authority']=='COUNTERFACTUAL_DISCLOSURE_MODEL_ONLY'
    assert 'native-producer-owned-traces' not in r['source_kind']
    assert r['native_full_two_port_observer_present'] is False
