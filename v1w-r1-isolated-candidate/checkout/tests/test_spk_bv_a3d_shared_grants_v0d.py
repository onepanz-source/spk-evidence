"""Research cross-plane grant tests; A3d remains frozen and unmodified."""
import copy
import json
from dataclasses import replace
import pytest

from spk_backvalidation_v0.a3d_shared_grants_v0d import (
    SharedGrantRejected, actual_a3d_v0d, trace_from_a3d_v0d,
    shared_overlay_v0d, capture_v0d, seal_v0d, verify_v0d,
)
from spk_backvalidation_v0.simulator_evidence_v0b import NEW, OLD
from spk_backvalidation_v0.contract_v0 import canonical, digest, validate_trace


@pytest.fixture(scope='module')
def raw():
    return actual_a3d_v0d(NEW,(1,4))


@pytest.fixture(scope='module')
def bundle():
    return capture_v0d()


def test_actual_frozen_A3d_executes_two_events(raw):
    _,f,_,r=raw
    assert f.scheme == 'spread'
    assert [x['timestamp'] for x in r['result']['terminal_outputs']] == [3,6]
    assert len(r['transport']['link_grants']) == 4
    assert all(x['cross_pe'] for x in r['transport']['transfers'])


def test_A3d_observation_builds_structural_feedback(raw):
    trace=trace_from_a3d_v0d(raw[0],raw[1],raw[3])
    assert validate_trace(trace)['status']=='STRUCTURAL_PASS'
    assert len(trace['occurrences'])==4
    assert len(trace['assessments'])==2
    assert len(trace['propagations'])==2
    assert all(len(x['parent_ids'])==1 for x in trace['occurrences'] if x['source']=='B')


def test_two_assessments_are_not_duplicate_votes(bundle):
    trace=bundle['feedback_trace']
    assert len({a['id'] for a in trace['assessments']})==2
    assert bundle['overlay']['feedback_link_grants']==4
    assert len({(p['assessment_id'],p['receiver']) for p in bundle['overlay']['feedback_packets']})==4


def test_shared_fabric_is_contended(bundle):
    r=bundle['overlay']
    assert r['forward_link_grants']==4
    assert r['feedback_link_grants']==4
    assert r['conflict_ticks']['fabric_link']>0
    assert r['conflict_ticks']['pe_service']>0
    assert all(p['delivered_at']>p['send_at'] for p in r['feedback_packets'])


def test_forward_grants_immutable_and_A3d_digest_valid(raw,bundle):
    assert bundle['overlay']['forward_a3d_sha256']==digest(raw[3])
    assert bundle['overlay']['forward_grants_immutable'] is True
    assert bundle['overlay']['grant_policy']=='frozen-A3d-forward-first'


def test_all_feedback_hops_respect_previous_delivery(bundle):
    delivered={}
    for p in sorted(bundle['overlay']['feedback_packets'],key=lambda p:p['hop']):
        if p['hop']>1:
            assert p['send_at']>=delivered[(p['assessment_id'],p['hop']-1,p['sender'])]
        delivered[(p['assessment_id'],p['hop'],p['receiver'])]=p['delivered_at']


def test_all_shared_link_credits_bounded(raw,bundle):
    fw=raw[3]['transport']['link_grants']; bv=bundle['overlay']['feedback_packets']
    keys={x['tick'] for x in fw}|{x['send_at'] for x in bv}
    for t in keys:
        assert sum(x['tick']==t for x in fw)+sum(x['send_at']==t for x in bv)<=1


def test_combined_inflight_within_A3d_quota(raw,bundle):
    fw=raw[3]['transport']['link_grants']; bv=bundle['overlay']['feedback_packets']
    max_tick=max([x['delivery_timestamp'] for x in fw]+[x['delivered_at'] for x in bv])
    for t in range(max_tick+1):
        assert (sum(x['tick']<=t<x['delivery_timestamp'] for x in fw)+
                sum(x['send_at']<=t<x['delivered_at'] for x in bv))<=raw[2][0].max_inflight_occurrences


def test_costs_charged_only_to_overlay(bundle):
    r=bundle['overlay']
    assert r['service_units_spent']==4
    assert r['memory_units_spent']==8
    assert 'live-A3d-integration' in r['claims_excluded']
    assert 'general-N-node-runtime' in r['claims_excluded']


def test_one_terminal_has_two_feedback_hops():
    x=capture_v0d((1,))
    assert x['candidate_terminal_events']==1
    assert x['overlay']['forward_link_grants']==2
    assert x['overlay']['feedback_link_grants']==2


def test_baseline_does_not_invent_feedback():
    case,f,plans,result=actual_a3d_v0d(OLD,(1,4))
    trace=trace_from_a3d_v0d(case,f,result)
    overlay=shared_overlay_v0d(result,f,plans,trace)
    assert trace['assessments']==[]
    assert overlay['feedback_link_grants']==0
    assert overlay['forward_link_grants']==0


def test_short_feedback_wait_fails_closed(raw):
    trace=trace_from_a3d_v0d(raw[0],raw[1],raw[3])
    with pytest.raises(SharedGrantRejected,match='starvation'):
        shared_overlay_v0d(raw[3],raw[1],raw[2],trace,max_feedback_wait_ticks=1)


def test_invalid_budget_bool_fails_closed(raw):
    trace=trace_from_a3d_v0d(raw[0],raw[1],raw[3])
    with pytest.raises(SharedGrantRejected,match='invalid bounded'):
        shared_overlay_v0d(raw[3],raw[1],raw[2],trace,max_feedback_wait_ticks=True)


def test_invalid_resource_bool_fails_closed():
    with pytest.raises(SharedGrantRejected,match='invalid positive'):
        actual_a3d_v0d(link_slots=True)


def test_unadmitted_input_schedule_rejected():
    for ticks in ((4,1),(1,1),(),(0,),(33,),[1,4]):
        with pytest.raises(SharedGrantRejected):actual_a3d_v0d(NEW,ticks)


def test_tampered_A3d_forward_grant_denied(raw):
    case,f,plans,result=raw
    bad=copy.deepcopy(result)
    bad['transport']['link_grants'][0]['delivery_timestamp']+=1
    trace=trace_from_a3d_v0d(case,f,result)
    with pytest.raises(SharedGrantRejected,match='tampered'):
        shared_overlay_v0d(bad,f,plans,trace)


def test_fake_A3d_terminal_denied(raw):
    case,f,_,result=raw
    bad=copy.deepcopy(result)
    bad['result']['terminal_outputs'][0]['timestamp']+=100
    with pytest.raises(SharedGrantRejected,match='terminal'):
        trace_from_a3d_v0d(case,f,bad)


def test_ambiguous_coalesced_batch_rejected():
    case,f,plans,result=actual_a3d_v0d(NEW,(1,2,3,4))
    with pytest.raises(SharedGrantRejected,match='unambiguous|ambiguous'):
        trace_from_a3d_v0d(case,f,result)


def test_independent_sealed_replay():
    r=verify_v0d(seal_v0d())
    assert r['status']=='A3D_SHARED_GRANT_OVERLAY_REPLAY_PASS'
    assert r['forward_spike_grants']==4
    assert r['feedback_grants']==4


def test_rehashed_forgery_denied():
    item=json.loads(seal_v0d())
    item['payload']['overlay']['feedback_packets'][0]['send_at']+=1
    item['payload_sha256']=digest(item['payload'])
    with pytest.raises(SharedGrantRejected,match='independent replay'):
        verify_v0d(canonical(item))


def test_duplicate_json_or_pretty_json_rejected():
    with pytest.raises(ValueError):verify_v0d('{"payload":{},"payload":{},"payload_sha256":"x"}')
    with pytest.raises(SharedGrantRejected,match='noncanonical'):
        verify_v0d(json.dumps(json.loads(seal_v0d()),indent=2))


def test_proxy_cost_cannot_be_faked(raw):
    trace=trace_from_a3d_v0d(raw[0],raw[1],raw[3])
    with pytest.raises(SharedGrantRejected,match='unsupported shared-credit'):
        shared_overlay_v0d(raw[3],raw[1],raw[2],trace,cost_memory=1)
    with pytest.raises(SharedGrantRejected,match='unsupported shared-credit'):
        shared_overlay_v0d(raw[3],raw[1],raw[2],trace,cost_service=2)
