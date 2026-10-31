"""Fail-closed contracts for SPK native learning runtime v1, no fake BV verdicts."""
import dataclasses, pathlib
import pytest
from spk_native_learning_v1.conformance_v1 import (
    run, prove, observed, setup, compare_frozen_when_learning_off, pin_sources)
from spk_native_learning_v1.live_learning_scheduler_v1 import (
    execute_native_learning_v1,LearningPlanV1,LiveBVPlanV0e,
    LiveBVRejected,_credit_decision,_c_program)

@pytest.mark.parametrize('choice,goal,expected',[(12,11,11),(11,12,12)])
def test_genuine_native_bv_changes_following_PE_program(choice,goal,expected):
 r=run(choice,goal)
 o=observed(r)
 assert len(o)==2
 assert o[0]==(10,0,choice,[choice])
 assert o[1]==(30,1,expected,[expected])
 assert len(r['learning']['grants'])==1
 assert r['learning']['grants'][0]['tick']<30
 assert r['resources']['P_learning_service_units']==1
 assert r['resources']['P_learning_memory_units']==1

@pytest.mark.parametrize('tick,expected',[(13,[(10,0,12),(13,0,12)]),(14,[(10,0,12),(14,1,11)]),(30,[(10,0,12),(30,1,11)])])
def test_temporal_strictness(tick,expected):
 r=run(12,11,second_tick=tick)
 assert [(x[0],x[1],x[2]) for x in observed(r)]==expected

@pytest.mark.parametrize('case',[
 ('bv_off',dict(bv_on=False)),('learning_off',dict(learning=False)),
 ('verify',dict(mode='verify')),('zero_budget',dict(budget=0)),
 ('no_causal_edges',dict(drop_forward=True))])
def test_fail_closed_without_admitted_credit(case):
 _,kw=case
 r=run(12,11,**kw)
 assert not r['learning']['grants']
 assert r['learning']['final']['version']==0
 assert [x[2] for x in observed(r)]==[12,12]
 assert r['resources']['P_learning_service_units']==0

@pytest.mark.parametrize('verdict', ['POSITIVE','SPURIOUS','',None])
def test_no_negative_verdict_no_credit(verdict):
 p=LearningPlanV1()
 assert _credit_decision(verdict=verdict,original_version=0,current_version=0,
    assessment_id='a1',consumed=set(),learn=p)!='GRANT'

def test_duplicated_packet_not_credit():
 assert _credit_decision(verdict='NEGATIVE',original_version=0,current_version=0,
    assessment_id='a1',consumed={'a1'},learn=LearningPlanV1())=='DUPLICATE_ASSESSMENT'

def test_overlap_stale_negative_denied():
 r=run(12,11,second_tick=13)
 assert len(r['learning']['grants'])==1
 assert any(x['reason']=='STALE_P_VERSION' for x in r['learning']['denials'])

def test_old_P_version_not_credit():
 assert _credit_decision(verdict='NEGATIVE',original_version=0,current_version=1,
    assessment_id='a1',consumed=set(),learn=LearningPlanV1())=='STALE_P_VERSION'

def test_positive_PE_verdict_never_changes_P():
 r=run(11,11)
 assert not r['learning']['grants']
 assert [x['verdict'] for x in r['feedback']['assessments']]==['POSITIVE','POSITIVE']

def test_A_negative_then_positive_follows_real_PE_outputs():
 r=run(12,11)
 assert [(x['A_PE_output'],x['verdict']) for x in r['feedback']['assessments']]==[(22,'NEGATIVE'),(21,'POSITIVE')]
 assert [(x['sender'],x['receiver']) for x in r['feedback']['deliveries']]==[('A','B'),('B','C'),('A','B'),('B','C')]

def test_original_BV_parity_when_learning_disabled():
 assert compare_frozen_when_learning_off()['frozen_PE_forward_and_BV_resource_parity']

def test_A_ambiguous_judgment_denied():
 args=list(setup(12,11))
 case=args[0]
 altered=[]
 for n in case.nodes:
  if n.node_id=='A':
   prog=(('ACC',(1,3)),('CMP',1),('EMIT',21),('EMIT',22),('EMIT',7),('RESET',0),
         ('ACC',(1,4)),('CMP',1),('EMIT',21),('EMIT',22),('EMIT',7),('RESET',0))
   n=dataclasses.replace(n,instructions=prog)
  altered.append(n)
 args[0]=dataclasses.replace(case,nodes=tuple(altered))
 with pytest.raises(LiveBVRejected,match='A_PE_JUDGMENT_NOT_UNIQUE'):
  execute_native_learning_v1(*args,bv=LiveBVPlanV0e(assessor='A',terminal_channel=7),learn=LearningPlanV1())

def test_incompatible_C_template_denied():
 args=list(setup(12,11))
 case=args[0]
 bad=tuple(dataclasses.replace(n,instructions=(('EMIT',12),)) if n.node_id=='C' else n for n in case.nodes)
 args[0]=dataclasses.replace(case,nodes=bad)
 with pytest.raises(LiveBVRejected,match='INADMISSIBLE_C_PROGRAM_TEMPLATE'):
  execute_native_learning_v1(*args)

@pytest.mark.parametrize('learn',[
 LearningPlanV1(max_grants=-1),LearningPlanV1(mode='train'),LearningPlanV1(enabled=1)])
def test_invalid_learning_plan_denied(learn):
 with pytest.raises(LiveBVRejected,match='INVALID_LEARNING_PLAN'):
  execute_native_learning_v1(*setup(12,11),learn=learn)

def test_wrong_assessor_denied():
 with pytest.raises(LiveBVRejected,match='SEMANTIC_ASSESSOR_MUST_BE_A'):
  execute_native_learning_v1(*setup(12,11),bv=LiveBVPlanV0e(assessor='C'))

def test_c_program_is_real_pe_fragment():
 assert _c_program(11)==(('ACC',(1,1)),('CMP',1),('EMIT',11),('RESET',0))
 with pytest.raises(LiveBVRejected):_c_program(13)

def test_independent_experiments_are_deterministic():
 assert prove()==prove()

def test_frozen_source_bytes_pin():
 # Test independent SHA guard rather than trusting a report or a lock file.
 root=pathlib.Path(__file__).resolve().parents[1]
 # On release fwork, root contains actual frozen SPK modules. In local
 # isolated fixture tests they are intentionally not inside this tree.
 if (root/'spk_backvalidation_v0'/'live_dual_scheduler_v0e.py').exists():
  assert len(pin_sources(root))==3
