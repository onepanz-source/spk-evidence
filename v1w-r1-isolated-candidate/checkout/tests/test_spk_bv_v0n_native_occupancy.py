"""Offline v0n source contract tests. Synthetic fixtures are NOT native v0h proofs."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from spk_bv_research.native_capture_v0k import capture_result
from spk_bv_research.native_dossier_v0l import native_dossier, load_capture
from spk_bv_research.native_packet_pairing_v0m import read_dossier, native_pairing
from spk_bv_research.native_occupancy_v0n import (
    SCHEMA, STATUS_NATIVE, STATUS_REPORT, OccupancyError, read_pairing,
    observe, observe_native, validate_report, verify_against_native, digest,
)

PINS = {
    'schema':'spk-bv-v0h-producer-pins/v0k', 'status':'PINNED_BYTES_ONLY',
    'probe_sha256':'a'*64,
    'source_sha256': {p:s*64 for p,s in (
        ('search/spk_bv_v0h_identified_evidence.py','b'),
        ('search/spk_bv_v0h_research_gate.sh','c'),
        ('tests/test_spk_bv_identified_v0h.py','d'))},
    'claims_excluded':['source-independence','BV-v0h-equivalence'],
}

def fixture():
    deliveries = [
        {'packet_id':'p1','assessment_id':'a1','sender':'N1','receiver':'N2',
         'tick':10,'independent_receiver':True,'evidence_ids':['e1']},
        {'packet_id':'p2','assessment_id':'a1','sender':'N1','receiver':'N3',
         'tick':10,'independent_receiver':True,'evidence_ids':['e1']},
        {'packet_id':'p3','assessment_id':'a1','sender':'N2','receiver':'N0',
         'tick':13,'independent_receiver':False,'evidence_ids':['e1']},
    ]
    grants = [
        {'packet_id':'p1','assessment_id':'a1','sender':'N1','receiver':'N2',
         'tick':9,'delivered_at':10,'wait':5,'source_pe':'PE0','target_pe':'PE0','cross_pe':False},
        {'packet_id':'p2','assessment_id':'a1','sender':'N1','receiver':'N3',
         'tick':9,'delivered_at':10,'wait':3,'source_pe':'PE0','target_pe':'PE0','cross_pe':False},
        {'packet_id':'p3','assessment_id':'a1','sender':'N2','receiver':'N0',
         'tick':12,'delivered_at':13,'wait':2,'source_pe':'PE0','target_pe':'PE1','cross_pe':True},
    ]
    return ({'nodes':['N0','N1','N2','N3']}, {'static_routes':[]}, (1,2),
            {'feedback':{'deliveries':deliveries,'link_grants':grants,
                         'assessments':[{'id':'a1','observer':'N1','tick':4,'batch_id':'b1',
                                         'terminal_emission_id':'e1','input_occurrences':[]}]},
             'forward':{'batches':[{'batch_id':'b1','node':'N1','tick':4}]}})


def bundle(tmp_path):
    obj = capture_result(fixture(), deepcopy(PINS))
    cap=tmp_path/'capture.json'
    cap.write_text(json.dumps(obj))
    loaded=load_capture(cap)
    dos=native_dossier(loaded, sample_values=2)
    dfile=tmp_path/'dossier.json'
    dfile.write_text(json.dumps(dos))
    pair=native_pairing(loaded,read_dossier(dfile))
    pfile=tmp_path/'pairing.json'
    pfile.write_text(json.dumps(pair))
    return cap,dfile,pfile,pair


def test_synthetic_observation_reconstructs_grant_occupancy(tmp_path):
    _,_,_,r=bundle(tmp_path)
    out=observe(r)
    assert out['status']==STATUS_REPORT and out['schema']==SCHEMA
    assert out['source_verified_by_recomputation'] is False
    assert out['delivery_grant_pairs']==3
    assert out['native_reported_wait_mean_fraction']==[10,3]
    assert out['end_of_tick_undelivered_grants_peak']==2
    assert out['bounded_grant_delivery_tick_area']==3
    assert out['within_tick_grant_first_peak_upper_bound']==2
    assert out['grant_and_delivery_coactive_tick_count']==0
    assert out['final_unmatched_grants']==0
    assert out['native_independent_receiver_true_flags']==2
    assert 'scheduler-causal-attribution' in out['claims_excluded']


def test_verified_mode_requires_recomputed_pairing(tmp_path):
    cap,dos,_,r=bundle(tmp_path)
    verify_against_native(r,cap,dos)
    out=observe_native(r,cap,dos)
    assert out['status']==STATUS_NATIVE
    assert out['source_verified_by_recomputation'] is True


def test_modified_joined_sha_not_accepted_by_native_mode(tmp_path):
    cap,dos,_,r=bundle(tmp_path)
    r['joined_pair_multiset_sha256']='f'*64
    with pytest.raises(OccupancyError,match='recomputation differs'):
        verify_against_native(r,cap,dos)


def test_witness_grant_first_upper_bound_is_only_bound(tmp_path):
    _,_,_,r=bundle(tmp_path)
    r['grants_by_tick']=[{'tick':9,'count':1},{'tick':10,'count':2}]
    r['deliveries_by_tick']=[{'tick':10,'count':1},{'tick':11,'count':2}]
    o=observe(r)
    assert o['end_of_tick_undelivered_grants_peak']==2
    assert o['within_tick_grant_first_peak_upper_bound']==3
    assert o['grant_and_delivery_coactive_tick_count']==1
    assert o['bounded_grant_delivery_tick_area']==3


def test_same_tick_full_completion_area_is_zero(tmp_path):
    _,_,_,r=bundle(tmp_path)
    r['grants_by_tick']=[{'tick':9,'count':3}]
    r['deliveries_by_tick']=[{'tick':9,'count':3}]
    o=observe(r)
    assert o['end_of_tick_undelivered_grants_peak']==0
    assert o['within_tick_grant_first_peak_upper_bound']==3
    assert o['bounded_grant_delivery_tick_area']==0


@pytest.mark.parametrize('modify,error',[
    (lambda r:r.update(status='PASS'), 'schema/status'),
    (lambda r:r.update(schema='other'), 'schema/status'),
    (lambda r:r.update(native_v0h_verified=True), 'claim flag'),
    (lambda r:r.update(claims_excluded=[]), 'claims scope'),
    (lambda r:r.update(native_fixture_sha256='x'*64), 'SHA256'),
    (lambda r:r.update(bound_dossier_sha256='a'), 'SHA256'),
    (lambda r:r.update(joined_pair_multiset_sha256=42), 'SHA256'),
    (lambda r:r.update(source_delivery_rows_sha256='z'*64), 'SHA256'),
    (lambda r:r.update(producer_pins={'status':'whatever'}), 'source pins'),
    (lambda r:r['producer_pins']['source_sha256'].pop('search/spk_bv_v0h_research_gate.sh'), 'source hashes'),
    (lambda r:r.update(selected_test='other'), 'pinned native'),
    (lambda r:r.update(paired_unique_packet_ids=2), 'cardinalities'),
    (lambda r:r.update(delivery_rows=4), 'cardinalities'),
    (lambda r:r.update(local_pe_grants=3), 'cardinalities'),
    (lambda r:r.update(native_independent_receiver_true_flags=4), 'cardinalities'),
    (lambda r:r.update(sum_native_reported_wait=-1), 'reported wait'),
    (lambda r:r.update(sum_native_reported_wait=True), 'reported wait'),
    (lambda r:r['grants_by_tick'].append({'tick':9,'count':1}), 'repeated or unsorted'),
    (lambda r:r['grants_by_tick'][0].update(count=0), 'non-positive'),
    (lambda r:r['grants_by_tick'][0].update(tick=True), 'invalid tick'),
    (lambda r:r['grants_by_tick'].reverse(), 'repeated or unsorted'),
    (lambda r:r['deliveries_by_tick'][0].update(count=1), 'series totals'),
    (lambda r:r['grants_by_tick'][0].update(count=1), 'series totals'),
    (lambda r:r.update(grants_by_tick=[{'tick':11,'count':3}]), 'precedes grant'),
    (lambda r:r.update(deliveries_by_tick=[{'tick':8,'count':3}]), 'precedes grant'),
    (lambda r:r.update(grants_by_tick='abc'), 'invalid series'),
    (lambda r:r['grants_by_tick'][0].update(extra='x'), 'per-tick series'),
])
def test_reject_inconsistent_reports(tmp_path,modify,error):
    _,_,_,r=bundle(tmp_path)
    modify(r)
    with pytest.raises((OccupancyError,ValueError),match=error):
        observe(r)


def run_cli(tmp_path, pfile, out, *, cap=None, dos=None, fixture_sha=None, seed=13):
    r=json.loads(pfile.read_text())
    cmd=[sys.executable,'-m','search.spk_bv_v0n_observe',
         '--pairing',str(pfile),'--out',str(out),
         '--expected-fixture-sha',fixture_sha or r['native_fixture_sha256']]
    if cap is not None: cmd+=['--capture',str(cap)]
    if dos is not None: cmd+=['--dossier',str(dos)]
    return subprocess.run(cmd,text=True,capture_output=True,
                          env=os.environ | {'PYTHONHASHSEED':str(seed)})


def test_cli_modes_and_hashseed_reproducibility(tmp_path):
    cap,dos,p,r=bundle(tmp_path)
    result=[]
    for s in (13,811):
        q=tmp_path/f'out-{s}.json'
        proc=run_cli(tmp_path,p,q,seed=s,cap=cap,dos=dos)
        assert proc.returncode==0, proc.stderr
        data=json.loads(q.read_text())
        assert data['status']==STATUS_NATIVE
        result.append(q.read_bytes())
    assert result[0]==result[1]
    q=tmp_path/'report-only.json'
    assert run_cli(tmp_path,p,q).returncode==0
    assert json.loads(q.read_text())['status']==STATUS_REPORT


def test_cli_no_overwrite(tmp_path):
    _,_,p,_=bundle(tmp_path)
    q=tmp_path/'output.json';q.write_text('sentinel')
    proc=run_cli(tmp_path,p,q)
    assert proc.returncode==2 and q.read_text()=='sentinel'


def test_cli_wrong_sha_rejected_no_file(tmp_path):
    _,_,p,_=bundle(tmp_path)
    q=tmp_path/'output.json'
    proc=run_cli(tmp_path,p,q,fixture_sha='f'*64)
    assert proc.returncode==2 and not q.exists()


def test_cli_incomplete_native_pair_rejected(tmp_path):
    cap,_,p,_=bundle(tmp_path)
    q=tmp_path/'output.json'
    proc=run_cli(tmp_path,p,q,cap=cap)
    assert proc.returncode==2 and not q.exists()


def test_cli_tampered_report_in_native_mode_rejected(tmp_path):
    cap,dos,p,r=bundle(tmp_path)
    r['sum_native_reported_wait']+=1
    p.write_text(json.dumps(r))
    q=tmp_path/'output.json'
    proc=run_cli(tmp_path,p,q,cap=cap,dos=dos)
    assert proc.returncode==2 and 'recomputation differs' in proc.stderr and not q.exists()


def test_read_pairing_rejects_duplicate_keys(tmp_path):
    p=tmp_path/'pairs.json';p.write_text('{"schema":0,"schema":1}')
    with pytest.raises(OccupancyError, match='bad report JSON'):
        read_pairing(p)


def test_read_pairing_rejects_symlink(tmp_path):
    _,_,p,_=bundle(tmp_path)
    link=tmp_path/'linked.json';link.symlink_to(p)
    with pytest.raises(OccupancyError,match='non-symlink'):
        read_pairing(link)


def test_native_observation_cannot_gain_verification_by_report_only(tmp_path):
    _,_,p,_=bundle(tmp_path)
    out=observe(read_pairing(p))
    assert not out['source_verified_by_recomputation']
    assert 'true-hardware-cost' not in out  # no field masquerades as hardware units
    assert 'BV-v0h-528-stress-equivalence' in out['claims_excluded']


def test_report_only_cannot_be_promoted_with_boolean(tmp_path):
    _,_,_,r=bundle(tmp_path)
    with pytest.raises(TypeError):
        observe(r, verified_native=True)
