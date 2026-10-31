"""v0m offline fixtures are explicit synthetic tests; not native v0h equivalence."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from spk_bv_research.native_capture_v0k import capture_result
from spk_bv_research.native_dossier_v0l import load_capture, native_dossier
from spk_bv_research.native_packet_pairing_v0m import (
    SCHEMA, STATUS, PairingError, native_pairing, read_dossier,
)

PINS = {'schema':'spk-bv-v0h-producer-pins/v0k','status':'PINNED_BYTES_ONLY',
        'probe_sha256':'a'*64,
        'source_sha256': {'tests/test_spk_bv_identified_v0h.py':'b'*64}}
SHA = 'a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0'


def fixture():
    deliveries = [
        {'packet_id':'bv1','assessment_id':'a1','sender':'N5','receiver':'N3',
         'tick':10,'independent_receiver':True,'evidence_ids':['e9']},
        {'packet_id':'bv2','assessment_id':'a2','sender':'N5','receiver':'N4',
         'tick':10,'independent_receiver':True,'evidence_ids':['e12']},
        {'packet_id':'bv3','assessment_id':'a1','sender':'N3','receiver':'N0',
         'tick':13,'independent_receiver':False,'evidence_ids':['e9']},
    ]
    grants = [
        {'packet_id':'bv1','assessment_id':'a1','sender':'N5','receiver':'N3',
         'tick':9,'delivered_at':10,'wait':5,'source_pe':'PE0','target_pe':'PE0','cross_pe':False},
        {'packet_id':'bv2','assessment_id':'a2','sender':'N5','receiver':'N4',
         'tick':9,'delivered_at':10,'wait':3,'source_pe':'PE0','target_pe':'PE0','cross_pe':False},
        {'packet_id':'bv3','assessment_id':'a1','sender':'N3','receiver':'N0',
         'tick':12,'delivered_at':13,'wait':2,'source_pe':'PE0','target_pe':'PE1','cross_pe':True},
    ]
    assessments = [
        {'id':'a1','observer':'N5','tick':4,'batch_id':'b9',
         'terminal_emission_id':'e9','input_occurrences':[]},
        {'id':'a2','observer':'N5','tick':6,'batch_id':'b12',
         'terminal_emission_id':'e12','input_occurrences':[]},
    ]
    forward = [{'batch_id':'b9','node':'N5','tick':4},
               {'batch_id':'b12','node':'N5','tick':6}]
    return ({'nodes':['N0','N3','N4','N5']}, {'static_routes':[]},
            (1, 2), {'feedback':{'deliveries':deliveries,'link_grants':grants,
                               'assessments':assessments}, 'forward':{'batches':forward}})


def records(root, key):
    return root[3]['feedback'][key] if key != 'batches' else root[3]['forward']['batches']


def captured(root=None):
    return capture_result(fixture() if root is None else root, deepcopy(PINS))


def bound(tmp_path, doc=None, samples=2):
    doc = captured() if doc is None else doc
    p = tmp_path/'capture.json'
    p.write_text(json.dumps(doc, sort_keys=True))
    d = native_dossier(load_capture(p), sample_values=samples)
    q = tmp_path/'dossier.json'
    q.write_text(json.dumps(d, sort_keys=True))
    return p, q


def validate(tmp_path, obj=None):
    p, q = bound(tmp_path, captured(obj) if obj is not None else None)
    return native_pairing(load_capture(p), read_dossier(q))


def test_pairing_all_rows_by_actual_packet_id(tmp_path):
    r = validate(tmp_path)
    assert r['schema'] == SCHEMA and r['status'] == STATUS
    assert r['paired_unique_packet_ids'] == r['delivery_rows'] == r['grant_rows'] == 3
    assert r['assessment_rows'] == 2 and r['forward_batch_rows'] == 2
    assert r['cross_pe_grants'] == 1 and r['local_pe_grants'] == 2
    assert r['sum_native_reported_wait'] == 10
    assert r['native_independent_receiver_true_flags'] == 2
    assert r['native_v0h_verified'] is False
    assert 'v0i-reception-mapping' in r['claims_excluded']


def test_join_uses_packet_id_not_list_ordinal(tmp_path):
    root=fixture()
    records(root,'link_grants').reverse()
    r=validate(tmp_path,root)
    assert r['paired_unique_packet_ids']==3
    assert r['sum_native_reported_wait']==10


def test_pair_multiset_reorder_invariant(tmp_path):
    a=validate(tmp_path)
    root=fixture()
    records(root,'deliveries').reverse()
    records(root,'link_grants').reverse()
    b=validate(tmp_path,root)
    assert a['joined_pair_multiset_sha256']==b['joined_pair_multiset_sha256']
    assert a['native_fixture_sha256']!=b['native_fixture_sha256']


@pytest.mark.parametrize('samples',[0,1,2,3])
def test_dossier_sample_sizes(tmp_path,samples):
    p,q=bound(tmp_path,samples=samples)
    assert native_pairing(load_capture(p),read_dossier(q))['paired_unique_packet_ids']==3


@pytest.mark.parametrize('mutation, match', [
    (lambda x:records(x,'deliveries')[1].update(packet_id='bv1'),'duplicate packet_id'),
    (lambda x:records(x,'link_grants')[1].update(packet_id='bv1'),'duplicate packet_id'),
    (lambda x:records(x,'link_grants')[1].update(packet_id='alien'),'packet_id sets differ'),
    (lambda x:records(x,'link_grants').pop(),'cardinality mismatch'),
    (lambda x:records(x,'link_grants').append(deepcopy(records(x,'link_grants')[0])),'cardinality mismatch'),
    (lambda x:records(x,'deliveries')[0].update(assessment_id='a2'),'conflicting assessment'),
    (lambda x:records(x,'link_grants')[0].update(sender='N2'),'conflicting assessment'),
    (lambda x:records(x,'deliveries')[0].update(receiver='N2'),'conflicting assessment'),
    (lambda x:records(x,'link_grants')[0].update(delivered_at=11),'delivery tick'),
    (lambda x:records(x,'link_grants')[0].update(tick=11),'grant tick'),
    (lambda x:records(x,'link_grants')[0].update(wait=-1),'invalid nonnegative'),
    (lambda x:records(x,'link_grants')[0].update(cross_pe=True),'cross_pe contradicts'),
    (lambda x:records(x,'link_grants')[0].update(source_pe='PE1'),'cross_pe contradicts'),
    (lambda x:records(x,'deliveries')[0].update(independent_receiver=1),'required native bool'),
    (lambda x:records(x,'deliveries')[0].update(assessment_id='alien'), 'conflicting assessment'),
    (lambda x:records(x,'link_grants')[0].update(assessment_id='alien'), 'conflicting assessment'),
    (lambda x:records(x,'feedback_assessments') if False else records(x,'assessments')[0].update(id='a2'),'duplicate assessment'),
    (lambda x:records(x,'assessments')[0].update(batch_id='bogus'),'references absent forward'),
    (lambda x:records(x,'assessments')[0].update(tick=15),'before its assessment'),
    (lambda x:records(x,'batches')[1].update(batch_id='b9'),'ambiguous forward batch'),
    (lambda x:records(x,'deliveries')[0].pop('packet_id'),'native field missing'),
    (lambda x:records(x,'link_grants')[0].update(wait=True),'invalid nonnegative'),
])
def test_fail_closed_on_bad_native_pairs(tmp_path, mutation,match):
    obj=fixture()
    mutation(obj)
    with pytest.raises((PairingError,ValueError),match=match):
        validate(tmp_path,obj)


def test_reject_unreferenced_assessment_even_if_pair_consistent(tmp_path):
    root=fixture()
    records(root,'deliveries')[0]['assessment_id']='not-present'
    records(root,'link_grants')[0]['assessment_id']='not-present'
    with pytest.raises(PairingError,match='missing assessment'):
        validate(tmp_path,root)


def test_reject_empty_paired_trace(tmp_path):
    root=fixture()
    records(root,'deliveries').clear();records(root,'link_grants').clear()
    with pytest.raises(PairingError,match='nonempty'):
        validate(tmp_path,root)


def test_reject_modified_or_stale_dossier(tmp_path):
    p,q=bound(tmp_path)
    d=json.loads(q.read_text())
    d['groups']['feedback_deliveries']['native_rows']=7
    q.write_text(json.dumps(d))
    with pytest.raises(PairingError,match='fingerprint mismatch'):
        native_pairing(load_capture(p),read_dossier(q))


def test_reject_dossier_sample_tampering(tmp_path):
    p,q=bound(tmp_path)
    d=json.loads(q.read_text())
    d['groups']['feedback_deliveries']['scalar_samples'][0]['scalar_values']['packet_id']='evil'
    q.write_text(json.dumps(d))
    with pytest.raises(PairingError,match='sample contents mismatch'):
        native_pairing(load_capture(p),read_dossier(q))


def test_reject_changed_fixture(tmp_path):
    p,q=bound(tmp_path)
    new=fixture()
    records(new,'deliveries')[0]['tick']=19
    p.write_text(json.dumps(captured(new)))
    with pytest.raises(PairingError,match='fixture SHA mismatch'):
        native_pairing(load_capture(p),read_dossier(q))


def test_reject_changed_source_pins(tmp_path):
    p,q=bound(tmp_path)
    d=json.loads(q.read_text())
    d['producer_pins']['probe_sha256']='f'*64
    q.write_text(json.dumps(d))
    with pytest.raises(PairingError,match='source pins'):
        native_pairing(load_capture(p),read_dossier(q))


def test_reject_malformed_dossier_envelope(tmp_path):
    p,q=bound(tmp_path)
    d=json.loads(q.read_text());d['native_v0h_verified']=True
    q.write_text(json.dumps(d))
    with pytest.raises(PairingError,match='schema'):
        read_dossier(q)


def test_reject_symlink_dossier(tmp_path):
    p,q=bound(tmp_path)
    link=tmp_path/'link.json';link.symlink_to(q)
    with pytest.raises(PairingError,match='non-symlink'):
        read_dossier(link)


def test_reject_duplicate_json_dossier_key(tmp_path):
    p,q=bound(tmp_path)
    q.write_text('{"schema":1,"schema":2}')
    with pytest.raises(PairingError,match='invalid dossier'):
        read_dossier(q)


def cli(tmp_path, capture_path, dossier_path, output, seed):
    argv=[sys.executable,'-m','search.spk_bv_v0m_pairing',
          '--capture',str(capture_path),'--dossier',str(dossier_path),
          '--out',str(output),'--expected-fixture-sha',captured()['native_fixture_sha256']]
    return subprocess.run(argv, capture_output=True, text=True,
                          env=os.environ | {'PYTHONHASHSEED':str(seed)})


def test_cli_hashseed_independent(tmp_path):
    p,q=bound(tmp_path)
    data=[]
    for seed in (13,811):
        out=tmp_path/f'pair-{seed}.json'
        result=cli(tmp_path,p,q,out,seed)
        assert result.returncode==0,result.stderr
        obj=json.loads(out.read_text())
        assert obj['status']==STATUS
        data.append(out.read_bytes())
    assert data[0]==data[1]


def test_cli_no_overwrite(tmp_path):
    p,q=bound(tmp_path)
    dest=tmp_path/'existing.json';dest.write_text('sentinel')
    result=cli(tmp_path,p,q,dest,13)
    assert result.returncode==2 and dest.read_text()=='sentinel'


def test_cli_no_output_on_failure(tmp_path):
    p,q=bound(tmp_path)
    dest=tmp_path/'result.json'
    d=json.loads(q.read_text()); d['groups']['feedback_link_grants']['native_rows']=999
    q.write_text(json.dumps(d))
    result=cli(tmp_path,p,q,dest,13)
    assert result.returncode==2 and not dest.exists()


def test_cli_sha_pin_required(tmp_path):
    p,q=bound(tmp_path);dest=tmp_path/'result.json'
    args=[sys.executable,'-m','search.spk_bv_v0m_pairing',
          '--capture',str(p),'--dossier',str(q),'--out',str(dest),
          '--expected-fixture-sha','b'*64]
    result=subprocess.run(args,capture_output=True,text=True)
    assert result.returncode==2 and not dest.exists()
