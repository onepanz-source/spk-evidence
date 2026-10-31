"""BV v1g bounded/negative contract tests, NOT a native fwork replay."""
from __future__ import annotations
import copy,hashlib,json
from dataclasses import dataclass
import pytest
from spk_bv_research.off_on_v0t import InterventionError,snapshot
from spk_bv_research.receiver_preference_v1f import SCHEMA as F_SCHEMA, STATUS as F_STATUS
from spk_bv_research.native_route_lineage_v1g import (
    SCHEMA,STATUS,_edge,_index_forward,_feedback,analyze,build)
from search.spk_bv_v1g_native_route_lineage import main,NAMES

@dataclass(frozen=True)
class Edge:
    source_node:str
    source_channel:int
    target_node:str
    target_channel:int
    target_pe:str
    delay_ticks:int=1

@dataclass(frozen=True)
class Fabric:
    static_routes:tuple


def sample():
    routes=(Edge('A',7,'B',0,'P',1),Edge('B',7,'C',0,'P',1))
    native=('case',Fabric(routes),('t','p','m','l'))
    owners={'A':'P','B':'P','C':'P'}
    occ=[{'id':'r1','source':'A','target':'B','source_pe':'P','target_pe':'P',
          'channel':0,'emitted_at':1,'delivered_at':2,'parents':[],'delay':1},
         {'id':'r2','source':'B','target':'C','source_pe':'P','target_pe':'P',
          'channel':0,'emitted_at':2,'delivered_at':3,'parents':['r1'],'delay':1}]
    batches=[{'tick':1,'node':'A','parents':[],'channels':[0]},
             {'tick':2,'node':'B','parents':['r1'],'channels':[0]},
             {'tick':3,'node':'C','parents':['r2'],'channels':[0]}]
    fw={'occurrences':occ,'batches':batches,'states':{'A':0,'B':0,'C':0},
        'emissions':[{'timestamp':i+1,'node_id':nid,'channel':7}
                     for i,nid in enumerate(('A','B','C'))],
        'terminal':[{'timestamp':3,'node_id':'C','channel':7}]}
    off={'enabled':False,'policy':'forward-first','forward':copy.deepcopy(fw)}
    on={'enabled':True,'policy':'forward-first','forward':copy.deepcopy(fw),
        'feedback':{'assessments':[{'id':'a1','observer':'C','tick':3,'input_occurrences':['r2']}],
                    'deliveries':[{'assessment_id':'a1','sender':'C','receiver':'B',
                                   'evidence_ids':['r2'],'tick':4,'independent_receiver':True},
                                  {'assessment_id':'a1','sender':'B','receiver':'A',
                                   'evidence_ids':['r1'],'tick':5,'independent_receiver':True}],
                    'link_grants':[]}}
    v1f={'schema':F_SCHEMA,'status':F_STATUS,'native_fixture_sha256':snapshot(native),
         'native_judgments_observed':0,'native_updates_applied':0,
         'network_event_lineage_attested':False}
    return native,off,on,owners,v1f

def test_positive_two_hop_route_and_feedback():
    native,off,on,owners,f=sample()
    original=copy.deepcopy((native,off,on,owners,f))
    got=analyze(native,off,on,owners,v1f=f)
    assert got['static_route_count']==2
    assert got['original_off_occurrences']==2
    assert got['native_feedback_assessment_count']==1
    assert got['native_reverse_delivery_count']==2
    b,c=got['conditional_receiver_route_audit']
    assert b['direct_static_route_7_to_0'] and b['direct_original_forward_occurrences']==1
    assert b['observed_original_forward_ancestry_from_A']
    assert not c['direct_static_route_7_to_0'] and c['direct_original_forward_occurrences']==0
    assert c['observed_original_forward_ancestry_from_A']
    assert not got['v1e_shadow_mapping_promoted_to_live_variant_route']
    assert not got['learning_or_receiver_utility_identified']
    assert (native,off,on,owners,f)==original


def test_build_requires_full_recomputed_v1f():
    native,off,on,owners,f=sample()
    blob=b'bytes';out=build(f,blob,copy.deepcopy(f),native,off,on,owners,{'example':'pinned'})
    assert out['schema']==SCHEMA and out['status']==STATUS
    assert out['reference_v1f_sha256']==hashlib.sha256(blob).hexdigest()
    with pytest.raises(InterventionError,match='recomputation'):
        build(f,blob,dict(f,status='altered'),native,off,on,owners,{})

@pytest.mark.parametrize('field,bad',[
    ('native_fixture_sha256','f'*64),('native_judgments_observed',1),
    ('native_updates_applied',1),('network_event_lineage_attested',True),
    ('schema','fake'),('status','fake'),
])
def test_reference_forgery_rejected(field,bad):
    n,o,one,owners,f=sample();f[field]=bad
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)

@pytest.mark.parametrize('field,bad',[
    ('source','C'),('target','A'),('channel',7),('target_pe','Q'),
    ('source_pe','Q'),('delay',2),('delivered_at',1),('parents',['r2']),
    ('id','r2'),
])
def test_occurrence_forgery_rejected(field,bad):
    n,o,one,owners,f=sample();o['forward']['occurrences'][0][field]=bad
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)

@pytest.mark.parametrize('field,bad',[
    ('node','C'),('tick',1),('channels',[7]),('parents',['r2']),
])
def test_batch_consumption_mismatch_rejected(field,bad):
    n,o,one,owners,f=sample();o['forward']['batches'][1][field]=bad
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)

@pytest.mark.parametrize('field,bad',[
    ('sender','A'),('receiver','C'),('evidence_ids',['r1']),('tick',2),
    ('assessment_id','fake'),('evidence_ids',[]),
])
def test_reverse_feedback_forgery_rejected(field,bad):
    n,o,one,owners,f=sample();one['feedback']['deliveries'][0][field]=bad
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)


def test_cannot_promote_C_to_direct_without_a_route():
    n,o,one,owners,f=sample();res=analyze(n,o,one,owners,v1f=f)
    assert res['conditional_receiver_route_audit'][1]['direct_original_forward_occurrences']==0
    assert res['native_reverse_deliveries'][1]['receiver']=='A'


def test_off_on_forward_conservation_required():
    n,o,one,owners,f=sample();one['forward']['states']['C']=9
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)


def test_no_unsupported_non_unique_static_edge():
    n,o,one,owners,f=sample();n=('case',Fabric(n[1].static_routes+(n[1].static_routes[0],)),n[2]);f['native_fixture_sha256']=snapshot(n)
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)


def test_cycle_or_invalid_ancestry_rejected():
    n,o,one,owners,f=sample();o['forward']['occurrences'][1]['parents']=['r2']
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)


def _args(root,out,paths):
    result=['--root',str(root)]
    for name,p in zip(NAMES,paths):result+=['--'+name,str(p)]
    return result+['--out',str(out)]


def test_cli_missing_files_rejected_before_native_import(tmp_path,capsys):
    root=tmp_path/'repo';root.mkdir()
    files=[tmp_path/f'none_{i}.json' for i in range(len(NAMES))]
    out=tmp_path/'out.json'
    assert main(_args(root,out,files))==2 and not out.exists()
    assert 'REJECTED' in capsys.readouterr().err


def test_cli_existing_output_preserved(tmp_path):
    root=tmp_path/'repo';root.mkdir();out=tmp_path/'out.json';out.write_text('preserve')
    paths=[]
    for i in range(len(NAMES)):
        p=tmp_path/f'ref_{i}.json';p.write_text('{}');paths.append(p)
    assert main(_args(root,out,paths))==2 and out.read_text()=='preserve'


def test_cli_hardlinks_and_symlinks_rejected(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    first=tmp_path/'origin.json';first.write_text('{}')
    links=[]
    for i in range(len(NAMES)):
        p=tmp_path/f'alias_{i}.json';p.hardlink_to(first);links.append(p)
    assert main(_args(root,tmp_path/'out.json',links))==2
    paths=[]
    for i in range(len(NAMES)):
        p=tmp_path/f'ref_{i}.json';p.write_text('{}');paths.append(p)
    symlink=tmp_path/'link.json';symlink.symlink_to(paths[0]);paths[0]=symlink
    assert main(_args(root,tmp_path/'out.json',paths))==2


def test_missing_route_occurrence_rejected_even_if_batches_adjusted():
    n,o,one,owners,f=sample()
    o['forward']['occurrences'].pop()
    o['forward']['batches'][2]['parents']=[]
    with pytest.raises(InterventionError,match='multiplicity'):
        analyze(n,o,one,owners,v1f=f)


def test_forged_extra_original_emission_requires_matching_route_occurrence():
    n,o,one,owners,f=sample()
    o['forward']['emissions'].append(copy.deepcopy(o['forward']['emissions'][0]))
    with pytest.raises(InterventionError,match='multiplicity'):
        analyze(n,o,one,owners,v1f=f)


def test_converging_ancestry_is_not_a_cycle():
    from spk_bv_research.native_route_lineage_v1g import _ancestors
    graph={'r1':{'parents':[]},'r2':{'parents':['r1']},
           'r3':{'parents':['r1']},'r4':{'parents':['r2','r3']}}
    assert _ancestors('r4',graph)=={'r1','r2','r3'}


def test_native_independent_receiver_flag_is_not_independent_vote():
    n,o,one,owners,f=sample()
    got=analyze(n,o,one,owners,v1f=f)
    assert got['native_packet_field_independence_is_not_causal_independence']
    assert all(x['native_independent_receiver_flag'] is True
               for x in got['native_reverse_deliveries'])
    assert got['endogenous_receiver_judgments']==0


def test_feedback_duplicate_evidence_ids_rejected():
    n,o,one,owners,f=sample()
    one['feedback']['deliveries'][0]['evidence_ids']=['r2','r2']
    with pytest.raises(InterventionError):analyze(n,o,one,owners,v1f=f)
