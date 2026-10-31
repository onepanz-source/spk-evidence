"""BV v0l: fixture morphology only. Does not execute BV v0h."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from spk_bv_research.native_capture_v0k import capture_result, _sha, shape_report
from spk_bv_research.native_dossier_v0l import (
    DossierError, DOSSIER_SCHEMA, _validate_typed, load_capture,
    native_dossier, typed_path, group_report,
)

PINS={'schema':'spk-bv-v0h-producer-pins/v0k','status':'PINNED_BYTES_ONLY',
      'probe_sha256':'a'*64,'source_sha256':{'tests/test_spk_bv_identified_v0h.py':'b'*64}}


def document(duplicate=False):
    forward=[{'batch_id':'b1','birth_tick':3},{'batch_id':'b2','birth_tick':3}]
    deliveries=[{'packet_id':'P1','tick':8,'receiver':'n2','path':{'link_id':'L1'}},
                {'packet_id':'P2','tick':8,'receiver':'n3','path':{'link_id':'L2'}}]
    if duplicate:
        deliveries[1]=deepcopy(deliveries[0])
    grants=[{'grant_id':'G1','tick':8}, {'grant_id':'G2','tick':8}]
    a=({'nodes':['n1','n2']},{'static_routes':[]},(1,2),
       {'feedback':{'deliveries':deliveries,'link_grants':grants,'assessments':[{'id':'A1'}]},
        'forward':{'batches':forward}})
    return capture_result(a, deepcopy(PINS))


def write(tmp_path,doc=None):
    p=tmp_path/'capture.json'
    p.write_text(json.dumps(doc or document(),sort_keys=True))
    return p


def test_derived_real_group_cardinalities(tmp_path):
    report=native_dossier(load_capture(write(tmp_path)))
    assert report['status']=='NATIVE_TYPED_GROUPS_INSPECTED_NOT_PACKET_MAPPING'
    assert report['groups']['feedback_deliveries']['native_rows']==2
    assert report['groups']['feedback_link_grants']['native_rows']==2
    assert report['groups']['feedback_assessments']['native_rows']==1
    assert report['groups']['forward_batches']['native_rows']==2
    assert not report['native_v0h_verified']


def test_structure_of_rows_and_nested_fields(tmp_path):
    g=native_dossier(load_capture(write(tmp_path)))['groups']['feedback_deliveries']
    fields={x['path']:x for x in g['field_coverage']}
    assert fields['path/link_id']['rows']==2
    assert fields['packet_id']['scalar_types']==['str']
    assert g['unique_full_row_content']==2


def test_duplicate_content_not_deduped(tmp_path):
    g=native_dossier(load_capture(write(tmp_path,document(True))))['groups']['feedback_deliveries']
    assert g['native_rows']==2 and g['unique_full_row_content']==1
    assert g['repeated_full_row_content']==1


def test_native_row_permutation_changes_ordered_not_multiset(tmp_path):
    a=document(); b=deepcopy(a)
    deliveries=typed_path(b['native_fixture'],(3,'feedback','deliveries'))['items']
    deliveries.reverse()
    b['native_fixture_sha256']=_sha(b['native_fixture'])
    b['structure']=shape_report(b['native_fixture'])
    ra=native_dossier(load_capture(write(tmp_path,a)))['groups']['feedback_deliveries']
    (tmp_path/'capture.json').write_text(json.dumps(b))
    rb=native_dossier(load_capture(tmp_path/'capture.json'))['groups']['feedback_deliveries']
    assert ra['ordered_native_rows_sha256']!=rb['ordered_native_rows_sha256']
    assert ra['native_row_multiset_sha256']==rb['native_row_multiset_sha256']


def test_scalar_values_opt_in_only(tmp_path):
    doc=load_capture(write(tmp_path))
    assert native_dossier(doc)['groups']['feedback_deliveries']['scalar_samples']==[]
    s=native_dossier(doc,sample_values=2)['groups']['feedback_deliveries']['scalar_samples']
    assert len(s)==2 and s[0]['scalar_values']['packet_id']=='P1'
    assert s[0]['scalar_values']['path/link_id']=='L1'

@pytest.mark.parametrize('n',[-1,4,True,1.1])
def test_sample_bounds(tmp_path,n):
    with pytest.raises(DossierError,match='sample_values'):
        native_dossier(load_capture(write(tmp_path)),sample_values=n)


def test_check_expected_sha(tmp_path):
    doc=load_capture(write(tmp_path))
    assert native_dossier(doc,expected_sha=doc['native_fixture_sha256'])['native_fixture_sha256']==doc['native_fixture_sha256']
    with pytest.raises(DossierError,match='unexpected'):
        native_dossier(doc,expected_sha='c'*64)


def test_reject_mismatched_capture_sha(tmp_path):
    d=document();d['native_fixture_sha256']='a'*64
    with pytest.raises(DossierError,match='SHA mismatch'):
        load_capture(write(tmp_path,d))


def test_reject_forged_shape_report(tmp_path):
    d=document();d['structure']['candidate_sequences']=[]
    with pytest.raises(DossierError,match='shape report'):
        load_capture(write(tmp_path,d))


def test_reject_duplicate_json_keys(tmp_path):
    p=tmp_path/'capture.json';p.write_text('{"schema":1,"schema":2}')
    with pytest.raises(DossierError,match='invalid capture'):
        load_capture(p)

@pytest.mark.parametrize('field,value',[
    ('schema','unknown'),('status','RESEARCH_VERIFIED'),('native_v0h_verified',True),
    ('producer_pins',None),('selected_test',None),
])
def test_reject_false_capture_envelope(tmp_path,field,value):
    d=document();d[field]=value
    with pytest.raises(DossierError):
        load_capture(write(tmp_path,d))


def test_reject_root_path_absent(tmp_path):
    x=document();x['native_fixture']['items'].pop()
    with pytest.raises(DossierError,match='indexed native path absent'):
        typed_path(x['native_fixture'],(3,'feedback','deliveries'))


def test_reject_missing_feedback_sequence(tmp_path):
    d=document();node=typed_path(d['native_fixture'],(3,'feedback'))
    node['pairs']=[p for p in node['pairs'] if p[0]!='deliveries']
    d['native_fixture_sha256']=_sha(d['native_fixture']);d['structure']=shape_report(d['native_fixture'])
    with pytest.raises(DossierError,match='missing'):
        native_dossier(load_capture(write(tmp_path,d)))


def test_reject_wrong_sequence_type(tmp_path):
    d=document();feedback=typed_path(d['native_fixture'],(3,'feedback'))
    next(p for p in feedback['pairs'] if p[0]=='deliveries')[1].update({'$t':'dict','pairs':[]})
    d['native_fixture_sha256']=_sha(d['native_fixture']);d['structure']=shape_report(d['native_fixture'])
    with pytest.raises(DossierError):
        native_dossier(load_capture(write(tmp_path,d)))


def test_reject_noncanonical_dict_key_order(tmp_path):
    d=document();d['native_fixture']['items'][3]['pairs'].reverse()
    with pytest.raises(DossierError,match='keys not unique and sorted'):
        load_capture(write(tmp_path,d))


def test_reject_inconsistent_typed_set():
    with pytest.raises(DossierError,match='typed set'):
        _validate_typed({'$t':'set','items':[1,1]})


def test_reject_unexpected_float():
    with pytest.raises(DossierError,match='float'):
        _validate_typed({'$t':'float','v':'nan'})


def test_reject_tag_collision():
    with pytest.raises(DossierError,match='bad typed dict'):
        _validate_typed({'$t':'dict','pairs':[], 'hidden':'poison'})


def test_reject_symlinked_capture(tmp_path):
    actual=write(tmp_path)
    link=tmp_path/'capture-link.json';link.symlink_to(actual)
    with pytest.raises(DossierError,match='regular non-symlink'):
        load_capture(link)


def test_reject_blank_sequence_on_bad_path(tmp_path):
    d=document()
    node=typed_path(d['native_fixture'],(3,'feedback','deliveries'))
    node['items']=[]
    d['native_fixture_sha256']=_sha(d['native_fixture']);d['structure']=shape_report(d['native_fixture'])
    g=native_dossier(load_capture(write(tmp_path,d)))
    assert g['groups']['feedback_deliveries']['native_rows']==0
    assert not g['native_v0h_verified']


def test_cli_success_new_file_and_stable_hashseed(tmp_path):
    src=write(tmp_path)
    outputs=[]
    for seed in (13,811):
        out=tmp_path/f'report-{seed}.json'
        argv=[sys.executable,'-m','search.spk_bv_v0l_dossier','--capture',str(src),
              '--out',str(out),'--expected-fixture-sha',document()['native_fixture_sha256']]
        proc=subprocess.run(argv,capture_output=True,text=True,env=os.environ|{'PYTHONHASHSEED':str(seed)})
        assert proc.returncode==0,proc.stderr
        report=json.loads(out.read_text())
        assert report['schema']==DOSSIER_SCHEMA and report['native_v0h_verified'] is False
        outputs.append(out.read_bytes())
    assert outputs[0]==outputs[1]


def test_cli_no_overwrite(tmp_path):
    src=write(tmp_path);out=tmp_path/'existing.json';out.write_text('sentinel')
    result=subprocess.run([sys.executable,'-m','search.spk_bv_v0l_dossier',
        '--capture',str(src),'--out',str(out)],capture_output=True,text=True)
    assert result.returncode==2 and out.read_text()=='sentinel'


def test_cli_bad_capture_never_publishes(tmp_path):
    src=write(tmp_path);out=tmp_path/'out.json'
    d=json.loads(src.read_text());d['native_fixture_sha256']='a'*64
    src.write_text(json.dumps(d))
    result=subprocess.run([sys.executable,'-m','search.spk_bv_v0l_dossier',
        '--capture',str(src),'--out',str(out)],capture_output=True,text=True)
    assert result.returncode==2 and not out.exists()


def test_cli_values_remain_explicit_opt_in(tmp_path):
    src=write(tmp_path);out=tmp_path/'out.json'
    result=subprocess.run([sys.executable,'-m','search.spk_bv_v0l_dossier',
        '--capture',str(src),'--out',str(out), '--sample-values','1'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(out.read_text())['groups']['feedback_deliveries']['scalar_samples'][0]['scalar_values']['packet_id']=='P1'


def test_equal_grant_cardinality_does_not_claim_pairing(tmp_path):
    r=native_dossier(load_capture(write(tmp_path)))
    assert r['group_cardinality_equal_not_bijection'] is True
    assert 'delivery-grant-pairing' in r['claim_exclusions']


def test_huge_string_rejected():
    with pytest.raises(DossierError,match='oversized string'):
        _validate_typed('a'*500001)


def test_mutated_native_row_detected_by_sha(tmp_path):
    a=document();b=deepcopy(a)
    typed_path(b['native_fixture'],(3,'feedback','deliveries'))['items'][0]['pairs'][0][1]='changed'
    b['native_fixture_sha256']=_sha(b['native_fixture']);b['structure']=shape_report(b['native_fixture'])
    x=native_dossier(load_capture(write(tmp_path,a)))
    (tmp_path/'capture.json').write_text(json.dumps(b))
    y=native_dossier(load_capture(tmp_path/'capture.json'))
    assert x['groups']['feedback_deliveries']['native_row_multiset_sha256']!=y['groups']['feedback_deliveries']['native_row_multiset_sha256']
