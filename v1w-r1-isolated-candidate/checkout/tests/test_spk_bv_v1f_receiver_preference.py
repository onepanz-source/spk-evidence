"""BV v1f isolated contract tests. Native verification runs separately on fwork."""
from __future__ import annotations
import copy,json,hashlib
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.receiver_impact_v1e import SCHEMA as E_SCHEMA, STATUS as E_STATUS
from spk_bv_research.receiver_preference_v1f import (
    SCHEMA,STATUS,POLICIES,EXPECTED_EVAL,EXPECTED_RECEIVERS,EXCLUSIONS,
    analyze,build,_readout,
)
from search.spk_bv_v1f_receiver_preference import main


def ro(emit):
    return {'guard':bool(emit),'post_raw':0,'emitted_channels':emit,
            'result_sha256':hashlib.sha256(repr(emit).encode()).hexdigest()}

def sample():
    rows=[]
    for idx in (3,4,5):
        for rid in ('B','C'):
            changed=idx in (3,4)
            a=ro([7] if changed else []);b=ro([])
            row={'evaluation_domain_index':idx,'receiver_id':rid,'sender_id':'A',
                 'sender_original_emitted_channels':[7] if changed else [],
                 'sender_variant_emitted_channels':[],
                 'declared_original_ingress':[0] if changed else [],
                 'declared_variant_ingress':[],
                 'original_receiver_readout':a,'variant_receiver_readout':b,
                 'receiver_output_changed':a!=b,'receiver_guard_changed':a['guard']!=b['guard'],
                 'receiver_emission_changed':a['emitted_channels']!=b['emitted_channels'],
                 'classification':'DIFFERENT' if changed else 'SAME'}
            rows.append(row)
    return {'schema':E_SCHEMA,'status':E_STATUS,
            'native_receiver_kernels_executed':True,'frozen_original_nodes_immutable':True,
            'native_judgments_observed':0,'native_updates_applied':0,
            'native_learning_proven':False,'causal_credit_identified':False,
            'network_event_lineage_attested':False,
            'hypothetical_mapping':{'sender':'A','sender_channel':7,
             'receiver_channel':0,'conditional_receiver_ids':['B','C'],
             'network_route_attested':False,'native_feedback_packet_attested':False,
             'origin':'explicit_shadow_ingress_assumption_not_native_scheduler'},
            'receiver_probe':{'evaluation_domain_indices':[3,4,5],
             'recipient_timestamp':12,'recipient_prior_tick':11,
             'receiver_pairs':6,'different_pairs':4,
             'guard_different_pairs':4,'emission_different_pairs':4,'readouts':rows},
            'reference_v1d_sha256':'a'*64,'reference_v1c_sha256':'b'*64,
            'reference_v1b1_sha256':'c'*64,'reference_v0w_sha256':'d'*64,
            'native_fixture_sha256':'e'*64,'frozen_native_sources':{'test':'fixture'}}


def test_contract_explicit_boundaries():
    assert SCHEMA.endswith('/v1f') and 'NO_ENDOGENOUS_JUDGMENT' in STATUS
    assert EXPECTED_EVAL==(3,4,5) and EXPECTED_RECEIVERS==('B','C')
    assert POLICIES==('maximize_receiver_emission_count','minimize_receiver_emission_count')
    assert len(EXCLUSIONS)>=8 and any('route-attested' in x for x in EXCLUSIONS)


def test_polarity_is_reversed_on_same_evidence():
    a=analyze(sample())
    assert a['native_conditional_pairs']==6 and a['receiver_readout_difference_pairs']==4
    assert a['preference_polarity_reversed_on_different_pairs']==4
    assert a['declared_shared_sender_origin_groups']==3
    assert a['observations_per_declared_origin']==2
    maximize,minimize=a['policy_conditioned_shadow_preferences']
    assert (maximize['positive'],maximize['negative'],maximize['neutral'])==(0,4,2)
    assert (minimize['positive'],minimize['negative'],minimize['neutral'])==(4,0,2)
    assert [v['declared_policy_preference_sign'] for v in maximize['observations']]==[-1,-1,-1,-1,0,0]
    assert [v['declared_policy_preference_sign'] for v in minimize['observations']]==[1,1,1,1,0,0]
    assert a['independent_causal_votes_proven']==0 and a['native_judgments_observed']==0
    assert a['receiver_utility_identified'] is False and not a['native_learning_proven']


def test_report_contains_identical_native_source_anchor():
    x=sample();raw=json.dumps(x,sort_keys=True).encode()
    r=build(x,raw,copy.deepcopy(x))
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['reference_v1e_sha256']==hashlib.sha256(raw).hexdigest()
    assert r['reference_v1d_sha256']=='a'*64 and r['native_fixture_sha256']=='e'*64
    assert r['native_judgments_observed']==0 and r['native_updates_applied']==0
    assert r['native_learning_proven'] is False and r['receiver_utility_identified'] is False


def test_determinism_and_read_only():
    x=sample();before=copy.deepcopy(x)
    assert analyze(x)==analyze(x)
    assert x==before
    assert build(x,b'abc',x)==build(x,b'abc',x)


def test_forged_v1e_is_not_native_replay():
    x=sample();y=copy.deepcopy(x);y['receiver_probe']['readouts'][0]['original_receiver_readout']['post_raw']=11
    with pytest.raises(InterventionError,match='recomputation'):
        build(x,b'abc',y)

@pytest.mark.parametrize('name,alter',[
 ('schema','bogus'),('status','bogus'),('native_receiver_kernels_executed',False),
 ('frozen_original_nodes_immutable',False),('native_judgments_observed',1),
 ('native_updates_applied',1),('native_learning_proven',True),
 ('causal_credit_identified',True),('network_event_lineage_attested',True),
 ('native_judgments_observed',False),('native_updates_applied',True),
])
def test_forged_top_level_boundary(name,alter):
    x=sample();x[name]=alter
    with pytest.raises(InterventionError):analyze(x)

@pytest.mark.parametrize('key,bad',[
 ('sender','C'),('sender_channel',0),('sender_channel',True),
 ('receiver_channel',7),('conditional_receiver_ids',['C','B']),
 ('conditional_receiver_ids',['B','C','D']),('network_route_attested',True),
 ('native_feedback_packet_attested',True),('origin','native_scheduler'),
])
def test_forged_mapping(key,bad):
    x=sample();x['hypothetical_mapping'][key]=bad
    with pytest.raises(InterventionError):analyze(x)

@pytest.mark.parametrize('key,bad',[
 ('evaluation_domain_indices',[3,5,4]),('recipient_timestamp',13),
 ('recipient_prior_tick',12),('receiver_pairs',12),('receiver_pairs',True),
 ('different_pairs',5),('guard_different_pairs',5),('emission_different_pairs',5),
 ('different_pairs',True),('guard_different_pairs',True),
])
def test_forged_probe(key,bad):
    x=sample();x['receiver_probe'][key]=bad
    with pytest.raises(InterventionError):analyze(x)

@pytest.mark.parametrize('key,bad',[
 ('evaluation_domain_index',4),('receiver_id','C'),('sender_id','B'),
 ('sender_original_emitted_channels',[2]),('sender_variant_emitted_channels',[7]),
 ('declared_original_ingress',[]),('declared_variant_ingress',[0]),
 ('receiver_output_changed',False),('receiver_guard_changed',False),
 ('receiver_emission_changed',False),('classification','SAME'),
])
def test_forged_row(key,bad):
    x=sample();x['receiver_probe']['readouts'][0][key]=bad
    with pytest.raises(InterventionError):analyze(x)

@pytest.mark.parametrize('key,bad',[
 ('guard',1),('guard',None),('post_raw',True),('post_raw','0'),
 ('emitted_channels',[0]),('emitted_channels',[7,7]),
 ('emitted_channels',(7,)),('result_sha256','faked'),
])
def test_forged_readout(key,bad):
    x=sample();x['receiver_probe']['readouts'][0]['original_receiver_readout'][key]=bad
    with pytest.raises(InterventionError):analyze(x)


def test_readout_extra_field_rejected():
    x=sample();x['receiver_probe']['readouts'][0]['original_receiver_readout']['utility']=17
    with pytest.raises(InterventionError):analyze(x)


def test_reordered_or_dropped_recipient_rows():
    x=sample();x['receiver_probe']['readouts'].reverse()
    with pytest.raises(InterventionError):analyze(x)
    x=sample();x['receiver_probe']['readouts'].pop()
    with pytest.raises(InterventionError):analyze(x)


def test_uninformative_all_identical_rejected():
    x=sample()
    for r in x['receiver_probe']['readouts']:
        r['variant_receiver_readout']=copy.deepcopy(r['original_receiver_readout'])
        r['sender_variant_emitted_channels']=list(r['sender_original_emitted_channels'])
        r['declared_variant_ingress']=list(r['declared_original_ingress'])
        r['receiver_output_changed']=False;r['receiver_guard_changed']=False
        r['receiver_emission_changed']=False;r['classification']='SAME'
    x['receiver_probe']['different_pairs']=0
    x['receiver_probe']['guard_different_pairs']=0
    x['receiver_probe']['emission_different_pairs']=0
    with pytest.raises(InterventionError,match='uninformative'):analyze(x)


def _args(root,out,files):
    args=['--root',str(root)]
    for n,p in zip(('v1e','v1d','v1c','v1b1','v1a','v0w'),files):args.extend(('--'+n,str(p)))
    return args+['--out',str(out)]


def test_cli_nonexistent_sources_rejected_before_native_import(tmp_path,capsys):
    repo=tmp_path/'repo';repo.mkdir()
    paths=[tmp_path/('missing'+str(i)+'.json') for i in range(6)]
    out=tmp_path/'output.json'
    assert main(_args(repo,out,paths))==2
    assert not out.exists()
    assert 'REJECTED' in capsys.readouterr().err


def test_cli_hardlink_alias_rejected_before_native_import(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    src=tmp_path/'one.json';src.write_text('{}')
    aliases=[]
    for i in range(6):
        p=tmp_path/f'alias{i}.json';p.hardlink_to(src);aliases.append(p)
    out=tmp_path/'report.json'
    assert main(_args(repo,out,aliases))==2
    assert not out.exists()


def test_cli_existing_output_rejected_before_native_import(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    paths=[]
    for i in range(6):
        p=tmp_path/f'ref{i}.json';p.write_text('{}');paths.append(p)
    out=tmp_path/'report.json';out.write_text('original')
    assert main(_args(repo,out,paths))==2
    assert out.read_text()=='original'


def test_cli_symlink_reference_rejected_before_native_import(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    paths=[]
    for i in range(6):
        p=tmp_path/f'ref{i}.json';p.write_text('{}');paths.append(p)
    link=tmp_path/'link.json';link.symlink_to(paths[0]);paths[0]=link
    assert main(_args(repo,tmp_path/'out.json',paths))==2
