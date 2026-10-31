import copy
import pytest

from spk_bv_research.native_capture_v0k import canonical_fixture
from spk_bv_research.paired_runs_v0o import PairError
from spk_bv_research.feedback_lineage_v0q import audit


def pair(policy,move=0):
    assessments=[{'id':'a1','observer':'C','input_occurrences':['o1'],'tick':2+move},
                 {'id':'a2','observer':'C','input_occurrences':['o2'],'tick':3+move}]
    delivs=[{'packet_id':'bv1','assessment_id':'a1','sender':'C','receiver':'B',
             'independent_receiver':True,'evidence_ids':['o1'],'tick':5+move},
            {'packet_id':'bv2','assessment_id':'a2','sender':'C','receiver':'A',
             'independent_receiver':True,'evidence_ids':['o2'],'tick':6+move}]
    grants=[{'packet_id':d['packet_id'],'assessment_id':d['assessment_id'],'sender':d['sender'],
             'receiver':d['receiver'],'tick':d['tick']-1,'delivered_at':d['tick'],
             'wait':1+move,'source_pe':'P0','target_pe':'P1'} for d in delivs]
    return {'enabled':True,'policy':policy,'feedback':{
        'deliveries':delivs,'link_grants':grants,'assessments':assessments}}


def f(x=None,y=None):
    x=x or pair('forward-first')
    y=y or pair('feedback-first',2)
    return canonical_fixture(('n','p','resources',x,y))


def test_only_time_shift_is_not_payload_mismatch():
    r=audit(f(),'fixture-test')
    assert r['packet_ids_not_semantically_equivalent_by_same_id']==[]
    assert r['packet_ids_both']==2
    assert r['packet_diagnostics'][0]['observed_tick_and_reported_wait_delta']['delivery_tick']==2


def test_assessment_swap_explains_delivery_and_grant_payload():
    x=pair('forward-first'); y=pair('feedback-first',2)
    y['feedback']['deliveries'][1]['assessment_id']='a1'
    y['feedback']['link_grants'][1]['assessment_id']='a1'
    report=audit(f(x,y),'test')
    assert report['delivery_payload_divergent_ids']==['bv2']
    assert report['grant_payload_divergent_ids']==['bv2']
    row=report['packet_diagnostics'][1]
    assert row['delivery_non_temporal_differences']['assessment_id']=={'first':'a2','second':'a1'}


def test_nested_evidence_ids_witness_is_visible():
    x=pair('forward-first'); y=pair('feedback-first',2)
    y['feedback']['deliveries'][1]['evidence_ids']=['o-new']
    report=audit(f(x,y),'test')
    assert report['delivery_payload_divergent_ids']==['bv2']
    assert report['grant_payload_divergent_ids']==[]
    assert report['packet_diagnostics'][1]['delivery_non_temporal_differences']['evidence_ids']['second']['items']==['o-new']


def test_assessment_input_provenance_shift_is_reported():
    y=pair('feedback-first',2)
    y['feedback']['assessments'][0]['input_occurrences']=['o3']
    report=audit(f(y=y),'test')
    assert report['assessment_non_temporal_changes'][0]['assessment_id']=='a1'

@pytest.mark.parametrize('bad',[('delivery','assessment_id','missing'),('delivery','receiver','E'),
                                ('grant','assessment_id','a2'),('grant','receiver','E'),
                                ('grant','delivered_at',22),('grant','wait',-1)])
def test_within_run_inconsistency_rejected(bad):
    y=pair('feedback-first',2)
    typ,key,value=bad
    target='deliveries' if typ=='delivery' else 'link_grants'
    y['feedback'][target][0][key]=value
    with pytest.raises(PairError):audit(f(y=y),'test')


def test_duplicate_packet_rejected():
    y=pair('feedback-first',2)
    y['feedback']['deliveries'].append(copy.deepcopy(y['feedback']['deliveries'][0]))
    with pytest.raises(PairError,match='duplicate'):
        audit(f(y=y),'test')


def test_extra_grant_rejected():
    y=pair('feedback-first',2)
    y['feedback']['link_grants'].append({**y['feedback']['link_grants'][0],'packet_id':'extra'})
    with pytest.raises(PairError,match='bijective'):
        audit(f(y=y),'test')


def test_distinct_packet_sets_are_not_falsely_matched():
    y=pair('feedback-first',2)
    y['feedback']['deliveries'][0]['packet_id']='new'
    y['feedback']['link_grants'][0]['packet_id']='new'
    result=audit(f(y=y),'test')
    assert result['packet_ids_both']==1
    assert {v['presence'] for v in result['packet_diagnostics']}=={'first-only','second-only','both'}


def test_wrong_policy_denied():
    y=pair('forward-first')
    with pytest.raises(PairError,match='policies'):
        audit(f(y=y),'test')


def test_off_case_denied():
    y=pair('feedback-first');y['enabled']=False
    with pytest.raises(PairError,match='both fixture'):
        audit(f(y=y),'test')


def test_wrong_fixture_denied():
    with pytest.raises(PairError,match='root'):
        audit(canonical_fixture(('n','p')),'test')


def test_packet_timing_not_inferred_as_hardware_latency():
    x=pair('forward-first');y=pair('feedback-first',2)
    y['feedback']['link_grants'][0]['wait']=10
    report=audit(f(x,y),'test')
    assert report['packet_diagnostics'][0]['observed_tick_and_reported_wait_delta']['wait']==9
    assert 'time-fields-and-native-wait-not-hardware-cost' in report['restrictions']


def _cli_observation(policy, terminal_tick, feedback_move, contention):
    """Standalone v0q test fixture; never import a sibling test module."""
    run = pair(policy, feedback_move)
    run['forward'] = {
        'states': {'A': 0}, 'processed_batches': 1, 'processed_events': 1,
        'batches': [{'node': 'A', 'tick': terminal_tick, 'ready': terminal_tick,
                     'raw': 1, 'channels': [0], 'parents': [], 'outputs': []}],
        'emissions': [{'node_id': 'A', 'channel': 0, 'timestamp': terminal_tick}],
        'terminal': [{'node_id': 'A', 'channel': 0, 'timestamp': terminal_tick}],
        'occurrences': [{'id': 'o1', 'channel': 0, 'delay': 1,
                         'source': 'A', 'target': 'B',
                         'source_pe': 'P0', 'target_pe': 'P1', 'parents': [],
                         'emitted_at': 1, 'delivered_at': terminal_tick}],
        'link_grants': [{'id': 'o1', 'source': 'A', 'target': 'B',
                         'source_pe': 'P0', 'target_pe': 'P1',
                         'tick': 2, 'delivered_at': terminal_tick, 'wait': 1}],
    }
    run['resources'] = {
        'contention': {'fabric_link': contention},
        'bv_link_grants': 2, 'bv_service_units': 2, 'bv_memory_units': 4,
        'forward_link_grants': 1, 'forward_reserved_memory_units': 16,
    }
    return run


def test_cli_replays_source_envelope_and_rejects_overwrite(tmp_path,monkeypatch):
    import json
    from spk_bv_research.paired_runs_v0o import capture
    from search import spk_bv_v0q_lineage_differential as cli
    a = _cli_observation('forward-first', 5, 0, 5)
    b = _cli_observation('feedback-first', 7, 2, 2)
    raw=('n','p','c',a,b)
    fakepins={'status':'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT',
              'source_sha256':{'tests/test_spk_bv_live_dual_scheduler_v0e.py':'a'*64,
                               'search/spk_bv_live_dual_scheduler_v0e.py':'b'*64}}
    envelope=capture(raw,fakepins)
    first=tmp_path/'first.json';second=tmp_path/'second.json'
    for path in (first,second):
        path.write_text(json.dumps(envelope))
    # A CLI smoke test must not claim that this artificial fixture is real.
    monkeypatch.setattr(cli,'EXPECTED_NATIVE_SHA',envelope['native_fixture_sha256'])
    monkeypatch.setattr(cli,'pins',lambda _:fakepins)
    out=tmp_path/'out.json'
    # The public CLI only writes under /tmp. pytest's tmp_path is normally in /tmp.
    rc=cli.main(['--capture-13',str(first),'--capture-811',str(second),'--out',str(out),
                 '--repo',str(__import__('pathlib').Path(__file__).resolve().parents[1])])
    assert rc==0
    assert json.loads(out.read_text())['v0p_outcome_conservation_recomputed']
    assert cli.main(['--capture-13',str(first),'--capture-811',str(second),'--out',str(out),
                     '--repo',str(__import__('pathlib').Path(__file__).resolve().parents[1])])==2
