"""Self-contained tests: no frozen native implementation required for contract gate."""
import copy
import hashlib
from dataclasses import replace

import pytest

from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES,SCHEMA as ES,STATUS as ST
from spk_bv_research.vertical_slice_integration_v2f import (
    validate_evidence,run_integrated,SCHEMA,STATUS,
)
from spk_backvalidation_v2.batched_feedback_executor_v2f import (
    BatchCaseV2f,FeedbackV2f,MailboxV2f,execute_batch_v2f,
    forward_projection,validate_case,
)
from spk_backvalidation_v2.observed_scheduler_v2a import ObserverV2a


def case(recipe=((0,1),(1,3)),ops=('relay','relay','relay'),episode='test.v2f'):
    return BatchCaseV2f(episode,tuple(recipe),tuple(ops))


def fake_native_evidence():
    rows=[]
    for name,recipe in RECIPES:
        n=len(recipe);k=len({t for _,t in recipe})
        metrics={'forward_emissions':3*k,'forward_terminal':k,
                 'processed_batches':3*k,'processed_events':n+2*k,
                 'forward_occurrences':2*k,'forward_batches':3*k}
        runs={mode:{'metrics':metrics,'whole_result_sha256':'0'*64} for mode in
              ('off','on_forward_first','on_feedback_first')}
        rows.append({'label':name,'recipe_template_index_and_tick':[list(x) for x in recipe],
                     'external_input_ticks':[t for _,t in recipe], 'event_count':n,
                     'native_mechanism_identified':False,'runs':runs,
                     'observed_total_emissions_per_control':[3*k]*3,
                     'observed_terminal_per_control':[k]*3,
                     'candidate_matches_per_control':{'one_three_emission_chain_per_tick':[True]*3}})
    return {'schema':ES,'status':ST,
            'source_kind':'READONLY_FROZEN_V0E_NEW_PREDECLARED_NATIVE_ADMISSION_INTERVENTIONS',
            'frozen_native_source_pins_rechecked_in_this_run':True,
            'native_semantic_probe_executed':True,'new_frozen_scheduler_executions':45,
            'full_native_v0w_anchor_replay_count':12,
            'native_source_template_variants_distinguishable':False,
            'native_CMP_semantics_or_scheduler_coalescence_identified':False,
            'native_B_control_messages':0,'native_learning_proven':False,
            'reference_v0w_sha256':'3d383897163e32e46a062575bf8b9fa4713800e68d36316ee3dba4db7f0a5f59',
            'reference_v2d_sha256':hashlib.sha256(b'v2d-test').hexdigest(),
            'native_matrix':rows}

@pytest.mark.parametrize('name,recipe', RECIPES)
def test_all_fifteen_native_patterns_have_equal_five_forward_measures(name,recipe):
    r=execute_batch_v2f(case(recipe,episode='case.'+name))
    n=len(recipe);k=len({t for _,t in recipe})
    assert r['processed_batches']==3*k
    assert r['processed_forward_events']==n+2*k
    assert sum(r['forward_emissions'].values())==3*k
    assert r['forward_terminal_count']==k
    assert sum(r['forward_routes'].values())==2*k

@pytest.mark.parametrize('name,recipe', RECIPES)
def test_actual_source_owned_observer_and_feedback_do_not_change_forward(name,recipe):
    c=case(recipe,episode='obs.'+name)
    base=execute_batch_v2f(c)
    observer=ObserverV2a()
    observed=execute_batch_v2f(c,observe=observer)
    box=MailboxV2f()
    feedback=execute_batch_v2f(c,feedback=True,mailbox=box)
    assert forward_projection(base)==forward_projection(observed)==forward_projection(feedback)
    assert len(observer.events)==base['observer_records_offered']
    assert box.summary()['research_delivered_total']==2*len({t for _,t in recipe})
    assert feedback['research_score_by_sender']['A']==len({t for _,t in recipe})
    assert feedback['research_score_by_sender']['B']==len({t for _,t in recipe})

@pytest.mark.parametrize('name,recipe', RECIPES)
def test_parent_lineage_and_batch_decision_ids(name,recipe):
    r=execute_batch_v2f(case(recipe,episode='line.'+name))
    assert len({d['id'] for d in r['decisions']})==len(r['decisions'])
    assert sum(len(d['parents']) for d in r['decisions'])==r['processed_forward_events']
    assert r['batch_admissions']=={'A':len({t for _,t in recipe}),
                                   'B':len({t for _,t in recipe}),
                                   'C':len({t for _,t in recipe})}

@pytest.mark.parametrize('recipe', (
    ((0,1),(1,1)),((0,1),(1,1),(0,1)),((0,1),(1,1),(0,3),(1,3))))
def test_duplicate_clock_batching_while_individual_admissions_remain_countable(recipe):
    r=execute_batch_v2f(case(recipe))
    assert r['batch_admissions']['A']==len(set(t for _,t in recipe))
    assert sum(len(d['parents']) for d in r['decisions'] if d['actor']=='A')==len(recipe)

@pytest.mark.parametrize('ops,expected_A,expected_B',(
    (('relay','block','relay'),-2,0),
    (('relay','relay','block'),2,-2),
    (('relay','relay','relay'),2,2)))
def test_recipient_scoring_is_local_to_real_actor_decision(ops,expected_A,expected_B):
    box=MailboxV2f();r=execute_batch_v2f(case(ops=ops),feedback=True,mailbox=box)
    assert r['research_score_by_sender']['A']==expected_A
    assert r['research_score_by_sender']['B']==expected_B
    assert not box.summary()['authentication_verified']
    assert box.summary()['absence_certificates']==0

@pytest.mark.parametrize('cap', (1,2,3))
def test_capacity_overflow_is_not_false_absence(cap):
    box=MailboxV2f(capacity=cap)
    r=execute_batch_v2f(case(),feedback=True,mailbox=box)
    assert r['research_receiver_local_judgments']==4
    assert r['research_feedback_delivered']['research_delivered_total']==cap
    assert r['research_feedback_delivered']['research_overflow'] is True
    assert r['research_feedback_delivered']['absence_certificates']==0

@pytest.mark.parametrize('policy', (
    lambda _:False,
    lambda _:None,
    lambda _:(_ for _ in ()).throw(RuntimeError('lost'))))
def test_failing_delivery_cannot_modify_forward(policy):
    c=case()
    box=MailboxV2f(accept=policy)
    with_control=execute_batch_v2f(c,feedback=True,mailbox=box)
    assert forward_projection(with_control)==forward_projection(execute_batch_v2f(c))
    assert box.summary()['research_lost']==4
    assert box.summary()['research_delivered_total']==0

@pytest.mark.parametrize('bad', (
  BatchCaseV2f('bad',((0,2),(1,1))),
  BatchCaseV2f('bad',((0,0),)),
  BatchCaseV2f('bad',((2,1),)),
  BatchCaseV2f('bad',((0,1),),('relay','relay','CMP')),
  BatchCaseV2f('bad/episode',((0,1),)),
  BatchCaseV2f('bad',((0,1),),hop_delay=0),
  BatchCaseV2f('bad',((0,1),),hop_delay=True),
  BatchCaseV2f('bad',((True,1),)),
))
def test_invalid_boundaries_rejected(bad):
    with pytest.raises(ValueError):validate_case(bad)

def test_replayed_or_forged_receiver_feedback_rejected():
    box=MailboxV2f();p=FeedbackV2f('B','A','A.e1','B.d1',1,2,3)
    issued={'A.e1':('A','B')}
    assert box._deliver(p,issued=issued)=='DELIVERED'
    with pytest.raises(ValueError,match='duplicate'):
        box._deliver(p,issued=issued)
    with pytest.raises(ValueError,match='causal'):
        MailboxV2f()._deliver(replace(p,issuer='C'),issued=issued)
    with pytest.raises(ValueError,match='shape'):
        MailboxV2f()._deliver(replace(p,response=0),issued=issued)

@pytest.mark.parametrize('mutation', (
   lambda d:d.__setitem__('new_frozen_scheduler_executions',44),
   lambda d:d.__setitem__('native_source_template_variants_distinguishable',True),
   lambda d:d.__setitem__('native_B_control_messages',1),
   lambda d:d.__setitem__('native_CMP_semantics_or_scheduler_coalescence_identified',True),
   lambda d:d['native_matrix'][2]['runs']['off']['metrics'].__setitem__('forward_emissions',5),
   lambda d:d['native_matrix'][3]['runs']['off']['metrics'].__setitem__('processed_events',3),
   lambda d:d['native_matrix'][2].__setitem__('label','forged'),
   lambda d:d['native_matrix'][2].__setitem__('native_mechanism_identified',True),
   lambda d:d['native_matrix'][2].__setitem__('observed_total_emissions_per_control',[0,0,0]),
   lambda d:d.__setitem__('status','NATIVE_FEEDBACK_PROVEN'),
   lambda d:d.__setitem__('full_native_v0w_anchor_replay_count',0),
   lambda d:d['native_matrix'][0].__setitem__('external_input_ticks',[100]),
))
def test_false_native_promotions_and_manipulations_fail_closed(mutation):
    d=fake_native_evidence();mutation(d)
    with pytest.raises(ValueError):validate_evidence(d,canon(d))

def test_immutability_and_correct_reproduction_of_supplied_15_pattern_report():
    d=fake_native_evidence();raw=canon(d);original=copy.deepcopy(d)
    r=run_integrated(d,raw,v2d_data=b'v2d-test')
    assert d==original
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['native_runs_new']==0
    assert r['source_owned_research_micro_executions']==65
    assert r['native_projection_cells_checked']==45
    assert r['research_control_messages_delivered_in_new_executor']==52
    assert r['native_receiver_B_control_messages']==0
    assert r['native_learning_proven'] is False
    assert r['native_integration_gate'].startswith('BLOCKED_')
    assert canon(r)==canon(run_integrated(d,raw,v2d_data=b'v2d-test'))

def test_predecessor_bytes_and_source_hash_must_match():
    d=fake_native_evidence();raw=canon(d)
    with pytest.raises(ValueError):validate_evidence(d,raw+b'\n')
    with pytest.raises(ValueError):validate_evidence(d,raw,v2d_data=b'other')

def test_monitor_faults_and_overflow_never_change_forward():
    c=case()
    def raiser(_):raise RuntimeError('sink fails')
    broken=ObserverV2a(sink=raiser)
    observed=execute_batch_v2f(c,observe=broken)
    assert broken.sink_fault
    assert forward_projection(observed)==forward_projection(execute_batch_v2f(c))
    full=ObserverV2a(capacity=1)
    short=execute_batch_v2f(c,observe=full)
    assert full.overflow and len(full.events)==1
    assert forward_projection(short)==forward_projection(execute_batch_v2f(c))

def test_null_controls_and_same_mailbox_cannot_be_interpreted_as_observer():
    with pytest.raises(ValueError):execute_batch_v2f(case(),feedback=True)
    with pytest.raises(ValueError):execute_batch_v2f(case(),mailbox=MailboxV2f())
    with pytest.raises(ValueError):execute_batch_v2f(case(),feedback=1)
    with pytest.raises(ValueError):execute_batch_v2f(case(),observe=object())

def test_research_actor_is_not_frozen_native_actor_even_with_positive_credit():
    b=MailboxV2f();r=execute_batch_v2f(case(),feedback=True,mailbox=b)
    assert r['research_score_by_sender']=={'A':2,'B':2,'C':0}
    assert r['native_B_control_packets']==0
    assert r['native_operator_updates']==0
    assert r['native_learning_proven'] is False
    assert r['research_receiver_local_judgments']==4
