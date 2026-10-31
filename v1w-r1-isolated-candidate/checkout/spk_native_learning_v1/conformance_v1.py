"""First falsifiable native same-scheduler P mutation gate; real originals only."""
from __future__ import annotations
from dataclasses import replace
import hashlib, json
from pathlib import Path
from spk_native_learning_v1.live_learning_scheduler_v1 import (execute_native_learning_v1,LearningPlanV1,LiveBVPlanV0e)

ORIGINAL = {
 'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
 'spk_architecture_v1/pe_execution_v1b.py':'8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c',
 'spk_architecture_v1/causal_memory_v1c.py':'175362406d3598331ec72c42084030248910e0033ea17d87d0810e221c8d7617',
}
SCHEMA='spk-native-learning-v1-first-same-scheduler-proof/v1'

def demand(cond, reason):
 if not cond: raise AssertionError(reason)

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def digest(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()

def pin_sources(root):
 root=Path(root).resolve()
 for rel,h in ORIGINAL.items():
  f=root/rel
  demand(f.is_file() and not f.is_symlink(), 'FROZEN_MISSING:'+rel)
  demand(hashlib.sha256(f.read_bytes()).hexdigest()==h,'FROZEN_DRIFT:'+rel)
 # Require the objects being invoked to be the pinned source modules,
 # not merely files with expected bytes that the interpreter never loaded.
 import spk_backvalidation_v0.live_dual_scheduler_v0e as orig_bv
 import spk_architecture_v1.pe_execution_v1b as orig_pe
 import spk_architecture_v1.causal_memory_v1c as orig_memory
 from spk_native_learning_v1 import live_learning_scheduler_v1 as live
 modules=(('spk_backvalidation_v0/live_dual_scheduler_v0e.py',orig_bv),
          ('spk_architecture_v1/pe_execution_v1b.py',orig_pe),
          ('spk_architecture_v1/causal_memory_v1c.py',orig_memory))
 for rel,module in modules:
  demand(Path(module.__file__).resolve()==(root/rel).resolve(),'FROZEN_LOADED_MODULE_MISMATCH:'+rel)
 demand(live._compute_local is orig_pe._compute_local and live._admit is orig_pe._admit,
        'FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH')
 demand(live._reservation is orig_memory._reservation and live._valid_memory is orig_memory._valid_memory,
        'FROZEN_MEMORY_ADMISSION_IDENTITY_MISMATCH')
 return dict(ORIGINAL)

def setup(choice,goal,*,later=True,drop_forward=False,second_tick=30):
 from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import case_for
 from spk_architecture_v1.pe_fabric_v1a import plan_v1a
 from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
 from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
 from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
 from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
 case=case_for(choice,goal,drop_forward=drop_forward)
 if later:
  second=replace(case.events[0],timestamp=second_tick)
  case=replace(case,events=case.events+(second,))
 fabric=plan_v1a(case,'spread')
 return (case,fabric,TransportPlanV1a(0,16),
  uniform_causal_service_plan_v1b(fabric,pe_slots=3,fabric_slots_per_tick=4),
  uniform_causal_memory_plan_v1c(fabric,pe_slots=256,domain_slots=256,fabric_slots_per_tick=768),
  CausalLinkPlanV1d(link_slots_per_tick=2,fabric_slots_per_tick=2,
   max_outbox_per_pe=128,max_link_span_ticks=256))

def run(choice,goal,*,later=True,bv_on=True,learning=True,mode='execute',budget=8,drop_forward=False,second_tick=30):
 args=setup(choice,goal,later=later,drop_forward=drop_forward,second_tick=second_tick)
 return execute_native_learning_v1(*args,
  bv=LiveBVPlanV0e(enabled=bv_on,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256),
  learn=LearningPlanV1(enabled=learning,mode=mode,max_grants=budget))

def observed(result):
 return [(b['tick'],b['P_version'],b['P_choice'],b['outputs']) for b in result['forward']['batches'] if b['node']=='C']

def compare_frozen_when_learning_off():
 from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e as FrozenBVPlan
 args=setup(12,11)
 bv=LiveBVPlanV0e(enabled=True,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256)
 actual=execute_native_learning_v1(*args,bv=bv,learn=LearningPlanV1(enabled=False))
 frozen=execute_live_v0e(*args,bv=FrozenBVPlan(enabled=True,priority='forward-first',assessor='A',terminal_channel=7,max_ticks=256))
 native_resources=actual['resources'].copy()
 native_resources.pop('P_learning_service_units',None);native_resources.pop('P_learning_memory_units',None)
 for t in native_resources['timeline']:
  demand(t.pop('P_learning_units',None)==0,'DISABLED_P_RESOURCE_GRANT')
 demand(frozen['resources']==native_resources,'FROZEN_RESOURCE_PARITY')
 demand(frozen['forward']['states']==actual['forward']['states'],'FROZEN_STATE_PARITY')
 for key in ('emissions','terminal','processed_events','processed_batches','link_grants','occurrences'):
  demand(frozen['forward'][key]==actual['forward'][key], 'FROZEN_FORWARD_PARITY_'+key)
 def drop_keys(rows,keys): return [{k:v for k,v in row.items() if k not in keys} for row in rows]
 demand(frozen['forward']['batches']==drop_keys(actual['forward']['batches'],('P_version','P_choice')),'FROZEN_BATCH_PARITY')
 for k in ('link_grants','unique_receiver_votes'):
  demand(frozen['feedback'][k]==actual['feedback'][k],'FROZEN_BV_PARITY_'+k)
 demand(frozen['feedback']['assessments']==drop_keys(actual['feedback']['assessments'],('verdict','A_PE_output')),'FROZEN_ASSESSMENT_PARITY')
 demand(frozen['feedback']['deliveries']==drop_keys(actual['feedback']['deliveries'],('verdict',)),'FROZEN_DELIVERY_PARITY')
 return {'frozen_PE_forward_and_BV_resource_parity':True,'old_batches':len(frozen['forward']['batches']),
         'old_BV_deliveries':len(frozen['feedback']['deliveries'])}

def prove():
 paired={}
 for choice,goal in ((12,11),(11,12)):
  res=run(choice,goal)
  c=observed(res)
  expected=11 if choice==12 else 12
  demand(len(c)==2,'TWO_C_BATCHES_REQUIRED')
  demand(c[0][2]==choice and c[0][3]==[choice],'FIRST_C_ORIGINAL_PE_OUTPUT')
  demand(c[1][2]==expected and c[1][3]==[expected],'SECOND_C_DID_NOT_READ_NEW_PROGRAM')
  demand(c[0][1]==0 and c[1][1]==1,'SECOND_C_P_VERSION_NOT_READ')
  grants=res['learning']['grants']; assessments=res['feedback']['assessments']; deliveries=res['feedback']['deliveries']
  demand(len(grants)==1 and grants[0]['choice_from']==choice and grants[0]['choice_to']==expected,
    'NO_CAUSAL_P_GRANT')
  demand(assessments[0]['A_PE_output']==22 and assessments[0]['verdict']=='NEGATIVE','A_DID_NOT_COMPUTE_NEGATIVE')
  demand(assessments[1]['A_PE_output']==21 and assessments[1]['verdict']=='POSITIVE','A_DID_NOT_COMPUTE_POSITIVE')
  demand([(x['sender'],x['receiver']) for x in deliveries]==[('A','B'),('B','C'),('A','B'),('B','C')], 'REVERSE_BV_ROUTE_MISSING')
  demand(grants[0]['tick']<c[1][0],'C_SECOND_BATCH_BEFORE_P_GRANT')
  demand(res['learning']['final']['version']==1 and res['learning']['final']['grants']==1,'P_REVISION_COUNT')
  demand(res['resources']['P_learning_service_units']==1 and res['resources']['P_learning_memory_units']==1,
    'P_RESOURCE_UNACCOUNTED')
  paired[f'{choice}->{goal}']={'C_PE_reads':c,'A_verdicts':[x['verdict'] for x in assessments],
   'P_grants':grants,'P_final':res['learning']['final'],'BV_deliveries':len(deliveries),
   'resource_digest':digest(res['resources'])}
 none=run(12,11,bv_on=False)
 demand([x[2] for x in observed(none)]==[12,12] and not none['learning']['grants'],'BV_DISABLED_MUST_NOT_LEARN')
 disabled=run(12,11,learning=False)
 demand([x[2] for x in observed(disabled)]==[12,12] and not disabled['learning']['grants'],'LEARNING_DISABLED_MUST_NOT_LEARN')
 verify=run(12,11,mode='verify')
 demand(not verify['learning']['grants'] and all(x['reason']!='GRANT' for x in verify['learning']['denials']),'VERIFY_MODE_GRANT')
 zero=run(12,11,budget=0)
 demand(not zero['learning']['grants'] and any(x['reason']=='P_BUDGET_EXHAUSTED' for x in zero['learning']['denials']),'ZERO_BUDGET_GRANT')
 positive=run(11,11)
 demand(not positive['learning']['grants'] and [x[2] for x in observed(positive)]==[11,11],'POSITIVE_FEEDBACK_CHANGED_P')
 dropout=run(12,11,drop_forward=True)
 demand(not dropout['learning']['grants'] and [x[2] for x in observed(dropout)]==[12,12],'ROUTE_DROPOUT_CHANGED_P')
 # Native feedback deliveries precede forward batch arbitration in the same tick.
 same_tick=run(12,11,second_tick=14)
 demand([(x[0],x[1],x[2]) for x in observed(same_tick)]==[(10,0,12),(14,1,11)],
        'BV_AND_C_SAME_TICK_DID_NOT_COMMIT_BEFORE_C')
 before_tick=run(12,11,second_tick=13)
 demand([(x[0],x[1],x[2]) for x in observed(before_tick)]==[(10,0,12),(13,0,12)],
        'P_GRANT_OCCURRED_BEFORE_BV_DELIVERY')
 demand(len(before_tick['learning']['grants'])==1 and any(x['reason']=='STALE_P_VERSION' for x in before_tick['learning']['denials']),
        'OVERLAPPING_NEGATIVE_FEEDBACK_NOT_FENCED')
 from spk_native_learning_v1.live_learning_scheduler_v1 import _credit_decision
 plan=LearningPlanV1()
 demand(_credit_decision(verdict='NEGATIVE',original_version=0,current_version=0,assessment_id='a1',consumed={'a1'},learn=plan)=='DUPLICATE_ASSESSMENT','REPLAY_GRANTED')
 demand(_credit_decision(verdict='NEGATIVE',original_version=0,current_version=1,assessment_id='a1',consumed=set(),learn=plan)=='STALE_P_VERSION','STALE_GRANTED')
 demand(_credit_decision(verdict='SPURIOUS',original_version=0,current_version=0,assessment_id='a1',consumed=set(),learn=plan)=='VERDICT_INVALID','FORGED_VERDICT_GRANTED')
 return {'positive_scenarios':paired,
  'negative_controls':{'BV_disabled':True,'learning_disabled':True,'verify_denied':True,
    'budget_exhausted_denied':True,'positive_no_P':True,'dropout_no_P':True,
    'replay_denied':True,'stale_denied':True,'forged_verdict_denied':True,'same_tick_bv_first':True,'earlier_C_not_rewritten':True},
  'frozen_parity':compare_frozen_when_learning_off()}

def report(root):
 pins=pin_sources(root)
 proof=prove()
 return {'schema':SCHEMA,'status':'NATIVE_V1_SAME_SCHEDULER_P_MUTATION_DEMONSTRATED',
   'original_frozen_components_unchanged':True,'original_frozen_BV_learning':False,
   'native_v1_research_learning':True,'scope':'BOUNDED_THREE_NEURON_BINARY_PROGRAM_SWAP',
   'A_PE_verdict_carried_on_actual_BV':True,'C_recomputes_on_updated_P_same_scheduler':True,
   'source_pins':pins,'proof':proof,
   'limits':['Versioned v1 fork, not frozen BV-v0e',
      'Only binary C decisions 11/12 and A verdict emissions 21/22 supported',
      'A corpus program encodes predeclared goal; host controls test cases',
      'No physical sensor, runtime durability, cryptographic root of trust, N-node topology or generalizable learning',
      'PE/_compute_local and resource validators execute from original frozen source on fwork',
      'No original learning P authority promotion']}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--root',default='.')
 a=p.parse_args();r=report(a.root)
 Path(a.output).parent.mkdir(parents=True,exist_ok=True)
 Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True,ensure_ascii=True)+'\n')
 print(r['status'],'P_GRANTS',sum(len(x['P_grants']) for x in r['proof']['positive_scenarios'].values()))
