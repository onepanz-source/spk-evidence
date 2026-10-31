import copy
import pytest
from spk_bv_research.native_capture_v0k import canonical_fixture
from spk_bv_research.paired_runs_v0o import PairError
from spk_bv_research.policy_identity_v0p import compute, identity_report, multiset_report


def obs(policy, tick1, tick2, contention):
    f={'states':{'A':0},'processed_batches':2,'processed_events':2,
       'batches':[{'node':'A','raw':1,'ready':1,'channels':[0],'parents':[],'outputs':[],'tick':1},
                  {'node':'B','raw':1,'ready':tick1,'channels':[0],'parents':[],'outputs':[],'tick':tick1}],
       'emissions':[{'node_id':'A','channel':0,'timestamp':1},
                    {'node_id':'B','channel':0,'timestamp':tick1}],
       'terminal':[{'node_id':'B','channel':0,'timestamp':tick1}],
       'occurrences':[{'id':'o1','channel':0,'delay':1,'source':'A','target':'B',
                       'source_pe':'P0','target_pe':'P1','parents':[], 'emitted_at':1,'delivered_at':tick2}],
       'link_grants':[{'id':'o1','source':'A','target':'B','source_pe':'P0','target_pe':'P1',
                      'tick':2,'delivered_at':tick2,'wait':1}]}
    fb={'deliveries':[{'packet_id':'p1','assessment_id':'a1','sender':'B','receiver':'A',
                       'independent_receiver':True,'evidence_ids':[],'tick':tick2}],
        'link_grants':[{'packet_id':'p1','assessment_id':'a1','sender':'B','receiver':'A',
                        'source_pe':'P1','target_pe':'P0','tick':tick2-1,'delivered_at':tick2,
                        'wait':max(0,tick2-2)}]}
    return {'enabled':True,'policy':policy,'forward':f,'feedback':fb,
            'resources':{'contention':{'fabric_link':contention},'bv_link_grants':1,
                         'bv_service_units':1,'bv_memory_units':2,'forward_link_grants':1,
                         'forward_reserved_memory_units':16}}


def fixture():
    return canonical_fixture(('same-network', 'same-placement', 'same-resources',
                              obs('forward-first',5,6,5),obs('feedback-first',7,4,2)))


def test_comparison():
    report=compute(fixture(),fixture_sha='synthetic-only')
    assert report['status'].endswith('POLICY_IDENTITY_AUDIT_ONLY')
    assert report['resource_comparison']['fabric_link_contention']['second_minus_first']==-3
    assert report['time_distributions']['forward_terminal']['last_tick_delta']==2
    assert report['identity_joins']['feedback_delivery']['matched_immutable_payload_count']==1
    assert report['identity_joins']['feedback_delivery']['timestamp_shift_distributions']['tick']==[-2]
    assert report['identity_joins']['forward_occurrence']['timestamp_shift_distributions']['delivered_at']==[-2]
    assert report['conserved_outcomes_all']

@pytest.mark.parametrize('which', ['forward','feedback'])
def test_wrong_policy_rejected(which):
    orig=['forward-first','feedback-first']
    r1=obs(orig[0],5,6,5);r2=obs(orig[1],7,4,2)
    if which=='forward':r1['policy']='feedback-first'
    else:r2['policy']='forward-first'
    with pytest.raises(PairError):compute(canonical_fixture(('n','p','c',r1,r2)))

@pytest.mark.parametrize('which', [3,4])
def test_disabled_feedback_rejected(which):
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[which-3]['enabled']=False
    with pytest.raises(PairError):compute(canonical_fixture(('n','p','c',*r)))

@pytest.mark.parametrize('field', ['packet_id','assessment_id','sender','receiver','independent_receiver','evidence_ids'])
def test_payload_change_not_matched(field):
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    val={'packet_id':'p2','assessment_id':'a2','sender':'X','receiver':'Y',
         'independent_receiver':False,'evidence_ids':['other']}[field]
    r[1]['feedback']['deliveries'][0][field]=val
    data=compute(canonical_fixture(('n','p','c',*r)))
    join=data['identity_joins']['feedback_delivery']
    assert not join['all_identities_and_payloads_match']
    assert join['matched_immutable_payload_count']==0


def test_missing_packet_rejected_as_mismatch_not_paired():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['feedback']['deliveries']=[]
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert x['identity_joins']['feedback_delivery']['missing_in_second']==['p1']


def test_duplicate_packet_id_fail_closed():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['feedback']['deliveries'].append(copy.deepcopy(r[1]['feedback']['deliveries'][0]))
    with pytest.raises(PairError,match='duplicate identity'):
        compute(canonical_fixture(('n','p','c',*r)))


def test_forward_payload_changed_marks_unconserved():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['terminal'][0]['channel']=8
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert not x['conserved_outcomes_all']


def test_forward_state_changed_marks_unconserved():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['states']['A']=1
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert not x['conserved_outcomes_all']


def test_negative_timestamp_rejected():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['terminal'][0]['timestamp']=-2
    with pytest.raises(PairError):compute(canonical_fixture(('n','p','c',*r)))


def test_negative_budget_rejected():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['resources']['bv_service_units']=-1
    with pytest.raises(PairError):compute(canonical_fixture(('n','p','c',*r)))


def test_forward_duplicate_content_not_claimed_distinct():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[0]['forward']['emissions'].append(copy.deepcopy(r[0]['forward']['emissions'][0]))
    r[1]['forward']['emissions'].append(copy.deepcopy(r[1]['forward']['emissions'][0]))
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert x['payload_multisets']['forward_emissions']['same_multiset']
    assert x['payload_multisets']['forward_emissions']['duplicate_content_groups_first']==1


def test_nonmatching_forward_occurrence_id_not_assumed_equal():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['occurrences'][0]['id']='o-other'
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert not x['identity_joins']['forward_occurrence']['all_identities_and_payloads_match']


def test_forward_payload_mismatch_not_attributed_to_policy():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['occurrences'][0]['target']='C'
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert x['identity_joins']['forward_occurrence']['payload_mismatches']==['o1']


def test_wrong_root_rejected():
    with pytest.raises(PairError):compute(canonical_fixture(('n','p','c','bad')))


def test_wait_sum_treated_as_scheduler_report_not_latency():
    x=compute(fixture(),fixture_sha='synthetic-only')
    assert x['resource_comparison']['forward_feedback_grant_wait_sum'] == {
        'first':4, 'second':2, 'second_minus_first':-2}
    assert 'tick-counts-not-hardware-time-or-energy' in x['restrictions']


def test_missing_terminal_not_counted_as_equal():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['terminal']=[]
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert not x['conserved_outcomes_all']


def test_nonmatching_batch_contents_disclosed_without_identity_invention():
    r=[obs('forward-first',5,6,5),obs('feedback-first',7,4,2)]
    r[1]['forward']['batches'][1]['raw']=2
    x=compute(canonical_fixture(('n','p','c',*r)))
    assert not x['payload_multisets']['forward_batches']['same_multiset']
    assert x['payload_multisets']['forward_batches']['unmatched_first'] == 1
