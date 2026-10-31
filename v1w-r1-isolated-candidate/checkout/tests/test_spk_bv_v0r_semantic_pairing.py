from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from spk_bv_research.native_capture_v0k import canonical_fixture
from spk_bv_research.native_capture_v0k import _sha
from spk_bv_research.paired_runs_v0o import PairError, capture
from spk_bv_research.semantic_pairing_v0r import compare


def _run(policy, order=('a1','a2'), offset=0):
    assessments=[{'id':'a1','observer':'C','input_occurrences':['r1'],'tick':1+offset},
                 {'id':'a2','observer':'C','input_occurrences':['r4'],'tick':2+offset}]
    meta={'a1':('B','A','PE1','PE0','r1'), 'a2':('C','B','PE2','PE1','r4')}
    delivs=[]; grants=[]
    for i,aid in enumerate(order,1):
        sender,receiver,spe,tpe,evid=meta[aid]
        pkt='bv'+str(i)
        delivery=4 + i + offset
        delivs.append({'packet_id':pkt,'assessment_id':aid,'sender':sender,
                       'receiver':receiver,'evidence_ids':[evid],
                       'independent_receiver':True,'tick':delivery})
        grants.append({'packet_id':pkt,'assessment_id':aid,'sender':sender,
                       'receiver':receiver,'source_pe':spe,'target_pe':tpe,
                       'tick':delivery-1,'delivered_at':delivery,'wait':i+offset})
    return {'enabled':True,'policy':policy,'feedback':{
        'assessments':assessments,'deliveries':delivs,'link_grants':grants}}


def _fixture(x=None,y=None):
    x = x if x is not None else _run('forward-first')
    y = y if y is not None else _run('feedback-first',('a2','a1'),2)
    return canonical_fixture(('network','placement','constraints',x,y))


def _compare(x=None,y=None):
    return compare(_fixture(x,y),'test-sha')


def test_swapped_run_local_packet_ids_are_recognized_without_reusing_id_as_identity():
    result=_compare()
    assert result['feedback_record_signature_multisets_equal']
    assert result['assessment_payload_multisets_equal']
    assert result['complete_unambiguous_structural_pairing']
    assert result['unique_cross_policy_pair_count']==2
    assert {(x['first_packet_id'],x['second_packet_id']) for x in result['relabelled_packet_pairs']}=={('bv1','bv2'),('bv2','bv1')}
    assert all(pair['deltas_second_minus_first']['delivery_tick'] in (1,3) for pair in result['relabelled_packet_pairs'])


def test_order_independent_signature_groups():
    a=_run('forward-first'); b=_run('feedback-first',('a2','a1'),2)
    ra=_compare(a,b)
    a['feedback']['deliveries'].reverse();a['feedback']['link_grants'].reverse()
    b['feedback']['deliveries'].reverse();b['feedback']['link_grants'].reverse()
    b['feedback']['assessments'].reverse()
    assert _compare(a,b)==ra


def test_timestamps_and_reported_wait_are_not_semantic_payload():
    a=_run('forward-first');b=_run('feedback-first',('a1','a2'),200)
    b['feedback']['link_grants'][0]['wait']=50
    assert _compare(a,b)['complete_unambiguous_structural_pairing']


def test_preserve_evidence_order_and_multiplicity():
    b=_run('feedback-first',('a1','a2'))
    b['feedback']['deliveries'][0]['evidence_ids']=['r1','r1']
    result=_compare(y=b)
    assert not result['feedback_record_signature_multisets_equal']
    assert result['unmatched_signatures_first']==1
    assert result['unmatched_signatures_second']==1


def test_assessment_semantic_change_not_silently_ignored():
    b=_run('feedback-first',('a1','a2'))
    b['feedback']['assessments'][0]['input_occurrences']=['forged']
    result=_compare(y=b)
    assert not result['assessment_payload_multisets_equal']
    assert not result['complete_unambiguous_structural_pairing']


def test_assessment_id_renumbering_does_not_force_mismatch():
    b=_run('feedback-first',('a1','a2'))
    b['feedback']['assessments'][0]['id']='renumbered'
    for x in ('deliveries','link_grants'):
        b['feedback'][x][0]['assessment_id']='renumbered'
    assert _compare(y=b)['complete_unambiguous_structural_pairing']


def test_duplicate_semantic_payloads_are_ambiguous_not_forced_pairs():
    a=_run('forward-first'); b=_run('feedback-first',('a1','a2'))
    # Two distinct packets with the same assessment and same sender/receiver/evidence,
    # but distinct local ids and time. This is a valid non-injective semantic signature.
    for run in (a,b):
        run['feedback']['deliveries'][1].update({k:copy.deepcopy(v) for k,v in run['feedback']['deliveries'][0].items() if k not in ('packet_id','tick')})
        run['feedback']['link_grants'][1].update({k:copy.deepcopy(v) for k,v in run['feedback']['link_grants'][0].items() if k not in ('packet_id','tick','delivered_at','wait')})
    result=_compare(a,b)
    assert result['feedback_record_signature_multisets_equal']
    assert result['ambiguous_signature_groups']==1
    assert result['unique_cross_policy_pair_count']==0
    assert not result['complete_unambiguous_structural_pairing']


def test_transport_pe_mutation_is_not_ignored():
    b=_run('feedback-first',('a1','a2'))
    b['feedback']['link_grants'][0]['target_pe']='OTHER'
    assert not _compare(y=b)['feedback_record_signature_multisets_equal']


def test_false_within_run_pairing_rejected():
    b=_run('feedback-first');b['feedback']['link_grants'][0]['receiver']='WRONG'
    with pytest.raises(PairError,match='discrepancy'):_compare(y=b)


def test_dangling_assessment_ref_rejected():
    b=_run('feedback-first');b['feedback']['link_grants'][0]['assessment_id']='missing';b['feedback']['deliveries'][0]['assessment_id']='missing'
    with pytest.raises(PairError,match='dangling'):_compare(y=b)


def test_duplicate_packet_ids_rejected():
    b=_run('feedback-first');b['feedback']['deliveries'][1]['packet_id']='bv1'
    with pytest.raises(PairError,match='duplicate'):_compare(y=b)


def test_grant_timestamp_mismatch_rejected():
    b=_run('feedback-first');b['feedback']['link_grants'][0]['delivered_at']=200
    with pytest.raises(PairError,match='tick mismatch'):_compare(y=b)


def test_negative_native_wait_rejected():
    b=_run('feedback-first');b['feedback']['link_grants'][0]['wait']=-1
    with pytest.raises(PairError,match='invalid'):_compare(y=b)


def test_wrong_run_configuration_rejected():
    b=_run('feedback-first');b['enabled']=False
    with pytest.raises(PairError,match='feedback-enabled'):_compare(y=b)


def test_wrong_policy_order_rejected():
    b=_run('forward-first')
    with pytest.raises(PairError,match='policy'):_compare(y=b)


def test_unsupported_root_rejected():
    with pytest.raises(PairError,match='five-element'):compare(canonical_fixture((1,2)),'x')


def test_research_exclusions_explicit():
    r=_compare()
    assert 'feedback-on-off-comparison' in r['claims_excluded']
    assert 'same-payload-proves-same-runtime-event' in r['claims_excluded']
    assert r['status'].endswith('_ONLY')


def test_repeat_determinism():
    fixture=_fixture()
    assert compare(fixture,'x')==compare(fixture,'x')


def test_hash_seed_invariance_in_subprocess():
    import os
    script='''import json
from tests_dummy import nothing
'''
    # Source installation path from the local test package, not a PYTHONPATH fixture hack.
    from spk_bv_research.native_capture_v0k import _json_bytes
    source=_json_bytes(_fixture()).decode()
    code='from spk_bv_research.semantic_pairing_v0r import compare;import json; print(json.dumps(compare(json.loads('+repr(source)+'),"x"),sort_keys=True))'
    env=os.environ.copy()
    out=[]
    for seed in ('13','811'):
        env['PYTHONHASHSEED']=seed
        proc=subprocess.run([sys.executable,'-c',code],env=env,check=True,capture_output=True,text=True)
        out.append(proc.stdout)
    assert out[0]==out[1]


def test_cli_fails_closed_if_output_exists(tmp_path):
    from search import spk_bv_v0r_semantic_pairing as cli
    dest=tmp_path/'existing.json';dest.write_text('{}')
    assert cli.main(['--capture-13',str(tmp_path/'missing'), '--capture-811',str(tmp_path/'missing2'), '--out',str(dest)])==2


def _cli_run(policy,tick,contention):
    run=_run(policy)
    run['forward']={'states':{'A':0},'processed_batches':1,'processed_events':1,
                    'batches':[{'node':'A','tick':tick,'ready':tick,'raw':0,'channels':[0],'parents':[],'outputs':[]}],
                    'emissions':[{'node_id':'A','channel':0,'timestamp':tick}],
                    'terminal':[{'node_id':'A','channel':0,'timestamp':tick}],
                    'occurrences':[{'id':'o1','channel':0,'delay':1,'source':'A','target':'B',
                                    'source_pe':'P0','target_pe':'P1','parents':[], 'emitted_at':1,'delivered_at':tick}],
                    'link_grants':[{'id':'o1','source':'A','target':'B','source_pe':'P0','target_pe':'P1',
                                    'tick':2,'delivered_at':tick,'wait':1}]}
    run['resources']={'contention':{'fabric_link':contention},'bv_link_grants':2,
                      'bv_service_units':2,'bv_memory_units':4,'forward_link_grants':1,
                      'forward_reserved_memory_units':16}
    return run


def test_cli_accepts_two_pinned_equal_independent_captures(tmp_path, monkeypatch):
    from search import spk_bv_v0r_semantic_pairing as cli
    a=_cli_run('forward-first',5,5)
    b=_cli_run('feedback-first',7,2)
    b['feedback']['deliveries'].reverse();b['feedback']['link_grants'].reverse()
    # Deliberately change IDs, retain payloads by full row identity.
    b['feedback']['deliveries'][0]['packet_id']='transposed2'
    b['feedback']['link_grants'][0]['packet_id']='transposed2'
    b['feedback']['deliveries'][1]['packet_id']='transposed1'
    b['feedback']['link_grants'][1]['packet_id']='transposed1'
    fakepins={'status':'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT',
              'producer_resolution':'STATIC_LOCAL_IMPORT_CLOSURE_NOT_RUNTIME_PROOF',
              'source_sha256':{'tests/test_spk_bv_live_dual_scheduler_v0e.py':'a'*64,
                               'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'b'*64}}
    envelope=capture(('network','placement','constraints',a,b),fakepins)
    srcs=[]
    for x in ('a','b'):
        f=tmp_path/(x+'.json');f.write_text(json.dumps(envelope));srcs.append(f)
    monkeypatch.setattr(cli,'EXPECTED_NATIVE_SHA',envelope['native_fixture_sha256'])
    monkeypatch.setattr(cli,'pins',lambda _:fakepins)
    output=tmp_path/'result.json'
    # output is below /tmp but not below the repository root.
    repo=Path(__file__).resolve().parents[1]
    assert cli.main(['--capture-13',str(srcs[0]),'--capture-811',str(srcs[1]),'--out',str(output),'--repo',str(repo)])==0
    result=json.loads(output.read_text())
    assert result['source_pins_reverified'] and result['inherited_v0p_outcome_conservation']
    assert result['complete_unambiguous_structural_pairing']
    assert cli.main(['--capture-13',str(srcs[0]),'--capture-811',str(srcs[1]),'--out',str(output),'--repo',str(repo)])==2


def test_v0q_style_four_packets_with_bv2_bv3_relabelled():
    a=_run('forward-first',('a1','a2'))
    # Extend to four distinct semantic signatures. Their assignment is local to each run.
    for j,(original,receiver) in enumerate(((0,'X'),(1,'Y')),3):
        d=copy.deepcopy(a['feedback']['deliveries'][original]);g=copy.deepcopy(a['feedback']['link_grants'][original])
        d.update(packet_id='bv'+str(j), receiver=receiver,tick=10+j)
        g.update(packet_id='bv'+str(j),receiver=receiver,tick=9+j,delivered_at=10+j)
        a['feedback']['deliveries'].append(d);a['feedback']['link_grants'].append(g)
    b=copy.deepcopy(a);b['policy']='feedback-first'
    # Equal semantic record bodies, but the scheduler enumerates bv2 and bv3 oppositely.
    for kind in ('deliveries','link_grants'):
        for d in b['feedback'][kind]:
            if d['packet_id']=='bv2': d['packet_id']='bv3'
            elif d['packet_id']=='bv3': d['packet_id']='bv2'
    report=_compare(a,b)
    assert report['complete_unambiguous_structural_pairing']
    assert report['unique_cross_policy_pair_count']==4
    assert {(p['first_packet_id'],p['second_packet_id']) for p in report['relabelled_packet_pairs']}=={('bv2','bv3'),('bv3','bv2')}


def test_zero_packet_counts_fail_closed():
    x=_run('forward-first');y=_run('feedback-first')
    for run in (x,y):
        run['feedback']['deliveries']=[]
        run['feedback']['link_grants']=[]
    with pytest.raises(PairError,match='empty'):_compare(x,y)
