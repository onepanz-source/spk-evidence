"""Live two-event-class BV research scheduler: bounded conformance and negatives."""
from dataclasses import replace
import json
import pytest
from search.spk_24n_independent_oracle_v0 import EdgeV0
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    LiveBVRejected,LiveBVPlanV0e,execute_live_v0e)
from spk_backvalidation_v0.a3d_shared_grants_v0d import actual_a3d_v0d
from spk_backvalidation_v0.simulator_evidence_v0b import NEW,OLD
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from search.spk_bv_v0e_live_evidence import fixture,capture,seal,verify
from spk_backvalidation_v0.contract_v0 import canonical,digest

@pytest.fixture(scope='module')
def runs():
    case,f,plans=fixture()
    fw=execute_live_v0e(case,f,*plans,LiveBVPlanV0e(priority='forward-first'))
    bv=execute_live_v0e(case,f,*plans,LiveBVPlanV0e(priority='feedback-first'))
    return case,f,plans,fw,bv


def test_two_event_classes_are_live_not_posthoc(runs):
    _,_,_,forward,reverse=runs
    assert [x['timestamp'] for x in forward['forward']['terminal']]==[3,5]
    assert [x['timestamp'] for x in reverse['forward']['terminal']]==[3,7]
    assert [x['tick'] for x in forward['forward']['link_grants']]==[1,2,3,4]
    assert [x['tick'] for x in reverse['forward']['link_grants']]==[1,2,5,6]


def test_feedback_and_spike_share_fabric_link_tick_budget(runs):
    for result in runs[3:]:
        total={}
        for g in result['forward']['link_grants'] + result['feedback']['link_grants']:
            total[g['tick']]=total.get(g['tick'],0)+1
        assert max(total.values())==1
        assert len(total)==8


def test_live_feedback_uses_both_service_and_memory(runs):
    for r in runs[3:]:
        assert r['resources']['bv_link_grants']==4
        assert r['resources']['bv_service_units']==4
        assert r['resources']['bv_memory_units']==8
        assert r['resources']['forward_link_grants']==4
        assert r['resources']['peak_cross_inflight']<=4


def test_feedback_causes_forward_source_link_wait(runs):
    assert runs[4]['forward']['link_grants'][2]['wait']==2
    assert runs[3]['forward']['link_grants'][2]['wait']==0
    assert runs[4]['resources']['contention']['fabric_link']>0


def test_feedback_ancestry_from_actual_batches(runs):
    r=runs[4]
    table={x['id']:x for x in r['forward']['occurrences']}
    assert len(table)==4
    assert all(x['delivered_at'] is not None for x in table.values())
    for occ in table.values():
        for parent in occ['parents']:
            assert table[parent]['target']==occ['source']
            assert table[parent]['delivered_at']<=occ['emitted_at']
    assert all(a['input_occurrences'] for a in r['feedback']['assessments'])


def test_feedback_follows_real_reverse_sources(runs):
    assert [(g['sender'],g['receiver']) for g in runs[4]['feedback']['link_grants']]==[
       ('C','B'),('B','A'),('C','B'),('B','A')]
    assert runs[4]['feedback']['unique_receiver_votes']==4
    assert len({(d['assessment_id'],d['receiver']) for d in runs[4]['feedback']['deliveries']})==4


def test_no_feedback_disabled_matches_a3d_forward_on_admitted_case(runs):
    case,f,plans,_,_=runs
    frozen=execute_causal_transport_v1d(case,f,*plans,max_batches=128,max_events=256)
    live=execute_live_v0e(case,f,*plans,LiveBVPlanV0e(enabled=False))
    assert frozen['result']['terminal_outputs']==live['forward']['terminal']
    assert frozen['result']['emissions']==live['forward']['emissions']
    assert frozen['result']['processed_batches']==live['forward']['processed_batches']
    assert frozen['result']['processed_events']==live['forward']['processed_events']
    assert [(x['tick'],x['source_node'],x['target_node']) for x in frozen['transport']['link_grants']]==[
        (x['tick'],x['source'],x['target']) for x in live['forward']['link_grants']]
    assert not live['feedback']['link_grants']


@pytest.mark.parametrize('ticks',[(1,), (1,3),(1,4),(1,5)])
@pytest.mark.parametrize('program',[OLD,NEW])
def test_live_disabled_vs_frozen_a3d_on_bounded_fixture(program,ticks):
    case,f,plans=fixture(program,ticks)
    frozen=execute_causal_transport_v1d(case,f,*plans,max_batches=128,max_events=256)
    live=execute_live_v0e(case,f,*plans,LiveBVPlanV0e(enabled=False))
    assert frozen['result']['terminal_outputs']==live['forward']['terminal']
    assert [(x['tick'],x['source_node']) for x in frozen['transport']['link_grants']]==[
        (x['tick'],x['source']) for x in live['forward']['link_grants']]


def test_program_without_outputs_has_no_feedback():
    case,f,plans=fixture(OLD)
    r=execute_live_v0e(case,f,*plans,LiveBVPlanV0e())
    assert r['feedback']['link_grants']==[]
    assert r['forward']['link_grants']==[]
    assert r['forward']['terminal']==[]


def test_feedback_still_completes_with_link_inflight_one():
    case,f,plans=fixture()
    tp,pp,mp,lp=plans
    r=execute_live_v0e(case,f,replace(tp,max_inflight_occurrences=1),pp,mp,lp,
                       LiveBVPlanV0e(priority='feedback-first'))
    assert len(r['feedback']['deliveries'])==4
    assert r['resources']['peak_cross_inflight']==1


def test_provenance_survives_parallel_route_convergence():
    case,f,plans=fixture(NEW,(1,))
    case=replace(case,edges=case.edges+(EdgeV0('B',7,'C',0,1),))
    from spk_architecture_v1.pe_fabric_v1a import plan_v1a
    f=plan_v1a(case,'spread')
    tp,pp,mp,lp=plans
    r=execute_live_v0e(case,f,tp,pp,mp,replace(lp,link_slots_per_tick=2,fabric_slots_per_tick=2),
                       LiveBVPlanV0e())
    assert len(r['feedback']['assessments'])==1
    assert [(x['sender'],x['receiver']) for x in r['feedback']['link_grants']]==[
        ('C','B'),('B','A')]
    assert r['feedback']['unique_receiver_votes']==2
    assert len([x for x in r['forward']['occurrences'] if x['source']=='B'])==2


@pytest.mark.parametrize('params,match',[
    ({'max_hops':1},'max_hops'),
    ({'max_packets':1},'max_packets'),
    ({'max_ticks':2},'horizon'),
    ({'max_occurrences':1},'occurrence'),
])
def test_bounds_fail_closed(params,match):
    case,f,plans=fixture()
    with pytest.raises(LiveBVRejected,match=match):
        execute_live_v0e(case,f,*plans,LiveBVPlanV0e(**params))


@pytest.mark.parametrize('params',[
    {'priority':'random'}, {'hop_latency':0}, {'max_packets':True},
    {'assessor':'Z'}, {'terminal_channel':-1}, {'max_hops':0},
])
def test_invalid_admission_rejected(params):
    case,f,plans=fixture()
    with pytest.raises(LiveBVRejected):
        execute_live_v0e(case,f,*plans,LiveBVPlanV0e(**params))


def test_no_mem_allocation_is_not_fabricated():
    case,f,plans=fixture()
    tp,pp,mp,lp=plans
    mp=replace(mp,fabric_slots_per_tick=1)
    with pytest.raises(LiveBVRejected,match='horizon'):
        execute_live_v0e(case,f,tp,pp,mp,lp,
                         LiveBVPlanV0e(max_ticks=20))


def test_captured_replay_deterministic():
    s=seal()
    assert seal()==s
    assert verify(s)['status']=='LIVE_DUAL_EVENT_REPLAY_PASS'


def test_digest_rehashed_forgery_denied():
    doc=json.loads(seal())
    doc['payload']['feedback_first']['forward']['terminal'][1]['timestamp']=12345
    doc['payload_sha256']=digest(doc['payload'])
    with pytest.raises(LiveBVRejected,match='replay mismatch'):
        verify(canonical(doc))


def test_noncanonical_replay_denied():
    with pytest.raises(LiveBVRejected,match='noncanonical'):
        verify(json.dumps(json.loads(seal()),indent=2))


def test_bad_payload_hash_denied():
    doc=json.loads(seal());doc['payload_sha256']='0'*64
    with pytest.raises(LiveBVRejected,match='mismatched'):
        verify(canonical(doc))


def test_tick_ledgers_respect_same_quota_every_tick(runs):
    _,fabric,(tp,pp,mp,lp),*results=runs
    ps=dict(pp.pe_slots);mps=dict(mp.pe_slots);ds=dict(mp.domain_slots)
    for r in results:
        for row in r['resources']['timeline']:
            assert row['pe_service_total'] <= pp.fabric_slots_per_tick
            assert row['memory_total'] <= mp.fabric_slots_per_tick
            assert row['link_total'] <= lp.fabric_slots_per_tick
            assert row['cross_inflight_end_tick'] <= tp.max_inflight_occurrences
            assert row['pe_service_total'] == sum(row['pe_service_by_pe'].values())
            assert row['memory_total'] == sum(row['memory_by_domain'].values())
            assert all(v<=ps[p] for p,v in row['pe_service_by_pe'].items())
            assert all(v<=mps[p] for p,v in row['memory_by_pe'].items())
            assert all(v<=ds[d] for d,v in row['memory_by_domain'].items())
            assert all(n<=lp.link_slots_per_tick for _a,_b,n in row['link_by_direction'])


def test_string_instead_of_enabled_bool_denied():
    case,f,plans=fixture()
    with pytest.raises(LiveBVRejected,match='policy'):
        execute_live_v0e(case,f,*plans,LiveBVPlanV0e(enabled='false'))
