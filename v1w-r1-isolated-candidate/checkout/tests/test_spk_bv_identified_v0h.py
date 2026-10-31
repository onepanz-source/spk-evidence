"""BV v0h independent batch/individual output identity; negative controls."""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from dataclasses import replace

import pytest
from spk_backvalidation_v0 import n_node_scheduler_v0f as old
from spk_backvalidation_v0 import identified_scheduler_v0h as new
from spk_backvalidation_v0.identified_audit_v0h import audit_identified_v0h,CausalAuditRejected
from spk_backvalidation_v0.context_aggregation_v0h import aggregate_context_v0h
from spk_backvalidation_v0.causal_audit_v0g import audit_closed_v0g,CausalAuditRejected as OldCausalRejected
from tests.test_spk_bv_n_node_scheduler_v0f import plans_for


def run_case(layers=(1,2,1),events=(0,2),pe=4,constrained=False,priority='forward-first',**kwargs):
    case,_=old.layered_case_v0f(layers,events_at=events)
    f=old.plan_n_v0f(case,pe)
    plans=plans_for(f, link=1 if constrained else 8192,
        pe=2 if constrained else 8192, fabric_pe=4 if constrained else 8192,max_ticks=1024)
    assessor=case.nodes[-1].node_id
    conf=dict(assessors=(assessor,),priority=priority,max_ticks=1024,
        max_packets=16384,max_occurrences=16384,max_batches=16384,
        max_events=16384,max_hops=128)
    conf.update(kwargs)
    bvo=old.LiveBVPlanV0f(**conf)
    bvn=new.LiveBVPlanV0h(**conf)
    actual=new.execute_identified_v0h(case,f,*plans,bvn)
    return case,f,plans,actual,(bvo,bvn)


def strip_identity(result):
    r=deepcopy(result)
    r['schema']='baseline'
    for name,keys in [('batches',('batch_id',)),
                      ('emissions',('batch_id','emission_id')),
                      ('terminal',('batch_id','emission_id')),
                      ('occurrences',('batch_id','emission_id'))]:
        for row in r['forward'][name]:
            for key in keys: row.pop(key,None)
    for row in r['feedback']['assessments']:
        row.pop('batch_id',None);row.pop('terminal_emission_id',None)
    return r


@pytest.mark.parametrize('layers,pe,constrained,priority',[
    ((1,2,1),1,False,'forward-first'),((1,2,1),4,False,'feedback-first'),
    ((1,2,1),4,True,'forward-first'),((1,2,1),4,True,'feedback-first'),
    ((1,2,2,1),1,True,'forward-first'),((1,2,2,1),2,True,'feedback-first'),
    ((2,3,2),4,True,'forward-first'),((2,3,2),4,True,'feedback-first'),
    ((8,8,8),4,False,'forward-first'),((16,16,16,16),8,False,'forward-first'),
])
def test_v0h_same_forward_and_feedback_behavior_as_frozen_v0f(layers,pe,constrained,priority):
    c,f,p,r,configs=run_case(layers,pe=pe,constrained=constrained,priority=priority)
    baseline=old.execute_n_v0f(c,f,*p,configs[0])
    assert strip_identity(r)==strip_identity(baseline)
    audited=audit_identified_v0h(c,f,r,*p)
    assert audited['status']=='IDENTIFIED_CAUSAL_AUDIT_PASS'
    assert audited['batches']==len(r['forward']['batches'])


def test_ambiguous_v0g_same_neuron_same_tick_becomes_verifiable():
    c,f,p,r,_=run_case((1,2,2,1),pe=1,constrained=True)
    repeated={x:n for x,n in Counter((b['node'],b['tick']) for b in r['forward']['batches']).items() if n>1}
    assert repeated
    with pytest.raises(OldCausalRejected,match='batch identity ambiguity'):
        audit_closed_v0g(c,f,{**strip_identity(r),'schema':old.SCHEMA},*p)
    audited=audit_identified_v0h(c,f,r,*p)
    assert audited['status']=='IDENTIFIED_CAUSAL_AUDIT_PASS'
    assert audited['assessments']>0
    assert len(set(x['batch_id'] for x in r['forward']['batches']))==len(r['forward']['batches'])
    assert len(set(x['emission_id'] for x in r['forward']['emissions']))==len(r['forward']['emissions'])


def test_context_aggregation_preserves_all_routes_and_per_receiver_judgment():
    c,f,p,r,_=run_case((1,2,1),events=(0,))
    a=aggregate_context_v0h(c,f,r,*p)
    summary=a['summary']
    assert summary['transport_packets']==4
    assert summary['assessment_receiver_groups']==3
    assert summary['duplicate_path_receptions']==1
    assert sum(row['packets'] for row in summary['rows'])==4
    assert len({(row['assessment_id'],row['receiver']) for row in summary['rows']})==3
    source=next(row for row in summary['rows'] if row['receiver']=='N0')
    assert source['packets']==2
    assert len(source['path_evidence_sets'])==2
    assert len(source['causal_evidence_ids'])==2
    assert 'communication savings' in summary['claims_excluded']


def test_large_convergence_has_observed_not_fabricated_cost():
    c,f,p,r,_=run_case((16,16,16,16),events=(0,),pe=8)
    a=aggregate_context_v0h(c,f,r,*p)['summary']
    assert a['transport_packets']==528
    assert a['assessment_receiver_groups']==33
    assert a['duplicate_path_receptions']==495
    assert sum(len(row['path_evidence_sets']) for row in a['rows'])==528
    assert all(len(set(row['packet_ids']))==row['packets'] for row in a['rows'])


@pytest.fixture
def real_trace():
    c,f,p,r,_=run_case((1,2,2,1),pe=1,constrained=True)
    return c,f,p,r


@pytest.mark.parametrize('mutation,expected',[
    ('missing_batch','batch identity'),
    ('duplicate_batch','batch identity'),
    ('bad_emission_batch','emission identity'),
    ('duplicated_emission','emission identity'),
    ('unknown_occurrence_emission','source emission'),
    ('wrong_occurrence_batch','source emission'),
    ('forged_occurrence_parent','ancestry mismatch'),
    ('fake_emission_channel','emission differs'),
    ('fake_terminal_identity','terminal identity'),
    ('forged_assessor_batch','assessment input ancestry'),
    ('forged_assessor_emission','assessment missing identified'),
    ('multiple_assessments_one_emission','assessment missing identified'),
    ('invented_receiver','feedback grant/delivery'),
    ('duplicate_vote','path multiplicity'),
    ('forged_memory','memory'),
])
def test_adversarial_identified_trace_is_rejected(real_trace,mutation,expected):
    c,f,p,r=real_trace
    x=deepcopy(r)
    if mutation=='missing_batch':
        x['forward']['batches'][0].pop('batch_id')
    elif mutation=='duplicate_batch':
        x['forward']['batches'][1]['batch_id']=x['forward']['batches'][0]['batch_id']
    elif mutation=='bad_emission_batch':
        x['forward']['emissions'][0]['batch_id']='b999'
    elif mutation=='duplicated_emission':
        x['forward']['emissions'][1]['emission_id']=x['forward']['emissions'][0]['emission_id']
    elif mutation=='unknown_occurrence_emission':
        x['forward']['occurrences'][0]['emission_id']='e999'
    elif mutation=='wrong_occurrence_batch':
        x['forward']['occurrences'][0]['batch_id']='b999'
    elif mutation=='forged_occurrence_parent':
        x['forward']['occurrences'][-1]['parents']=('fake',)
    elif mutation=='fake_emission_channel':
        x['forward']['emissions'][0]['channel']=99
    elif mutation=='fake_terminal_identity':
        x['forward']['terminal'][0]['emission_id']='e999'
    elif mutation=='forged_assessor_batch':
        x['feedback']['assessments'][0]['batch_id']='b1'
    elif mutation=='forged_assessor_emission':
        x['feedback']['assessments'][0]['terminal_emission_id']='e1'
    elif mutation=='multiple_assessments_one_emission':
        more=deepcopy(x['feedback']['assessments'][0]);more['id']='a999';x['feedback']['assessments'].append(more)
    elif mutation=='invented_receiver':
        x['feedback']['deliveries'][0]['receiver']='fake'
    elif mutation=='duplicate_vote':
        dupe=next(d for d in x['feedback']['deliveries'] if not d['independent_receiver'])
        dupe['independent_receiver']=True
    elif mutation=='forged_memory':
        x['resources']['timeline'][0]['memory_total']+=1
    with pytest.raises(CausalAuditRejected,match=expected):
        audit_identified_v0h(c,f,x,*p)


def test_context_aggregation_refuses_unverified_trace(real_trace):
    c,f,p,r=real_trace
    x=deepcopy(r)
    x['feedback']['deliveries'][0]['evidence_ids']=['r999']
    with pytest.raises(CausalAuditRejected):
        aggregate_context_v0h(c,f,x,*p)


def test_exhausted_admission_fails_closed():
    c,f,p,_,cfg=run_case((1,2,1),events=(0,))
    with pytest.raises(new.LiveBVRejected,match='occurrence quota'):
        new.execute_identified_v0h(c,f,*p,replace(cfg[1],max_occurrences=1))


def test_independent_source_replay_accepts_canonical_seal():
    from search.spk_bv_v0h_identified_evidence import seal,verify
    raw=seal()
    record=verify(raw)
    assert record['status']=='IDENTIFIED_BATCH_CONTEXT_REPLAY_PASS'
    assert record['witnesses']==10
    assert record['resolved_same_tick_extra_batches']>=1
    assert record['large_feedback_packets']==528


def test_independent_replay_rejects_validly_rehashed_trace_mutation():
    from search.spk_bv_v0h_identified_evidence import seal,verify
    from spk_backvalidation_v0.contract_v0 import strict_loads,canonical,digest
    raw=seal(); env=strict_loads(raw)
    env['payload']['witnesses'][0]['feedback_packets']+=1
    env['payload_sha256']=digest(env['payload'])
    with pytest.raises(CausalAuditRejected,match='replay mismatch'):
        verify(canonical(env))
