"""Full-checkout only: bounded PE-sensed context native v1v conformance.

Nothing in this module waives source pins or simulates PE/admission.  It requires
previous v1u fwork report and reruns the real original PE/BV code on fwork.
"""
from __future__ import annotations
import argparse,hashlib,json,sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from spk_native_learning_v1 import sensed_context_v1v as s, contextual_durable_v1u as d
from spk_native_learning_v1.generalized_case_v1t import pin_sources
PARENT_SHA='7032bd088b6ed4b1488c61eee0502a64418d6228f3a7bf49bc4b9045c56c2620'
PARENT_STATUS='NATIVE_V1U_CONTEXTUAL_P_SAME_SCHEDULER_CAUSAL_PASS'
CASES=(((40,42),11,15),((41,43),11,12),((40,42,99),11,15),((41,43,99),11,12),((40,42),11,11))
SCHEMA='spk-native-learning-v1v-pe-sensed-context/v1'
def require(ok,message):
 if not ok:raise AssertionError(message)
def report(root,parent):
 parent=Path(parent)
 require(parent.is_file() and not parent.is_symlink(),'MISSING_V1U_PARENT')
 require(hashlib.sha256(parent.read_bytes()).hexdigest()==PARENT_SHA,'V1U_PARENT_SHA_DRIFT')
 prior=json.loads(parent.read_text());pins=pin_sources(root)
 require(prior['status']==PARENT_STATUS and prior['native_v1_research_learning']
    and not prior['frozen_original_BV_learning'] and prior['original_frozen_pins']==pins,
    'V1U_PARENT_STATUS_OR_SOURCE_DRIFT')
 # Real original _compute_local must generate both cues without passing a label.
 require(s._source_check(root)==pins,'ORIGINAL_PE_IMPORT_CUSTODY_DENIED')
 with TemporaryDirectory(prefix='spk-nlv1v-') as t:
  t=Path(t);path=t/'pe-sensed.db'
  first=s.run_sequence(path,CASES,root=root)
  repeated=s.run_sequence(path,CASES,root=root)
  require(first['new_tick_rows']==325 and repeated['new_tick_rows']==0,'PE_SENSED_REPLAY_DRIFT')
  require(first['audit']==repeated['audit']==s.audit(path,root=root),'PE_SENSED_AUDIT_DRIFT')
  episodes=first['episodes'];selection=first['audit']['selector'];chain=first['audit']['contextual']
  contexts=[x['derived_context'] for x in episodes]
  require(contexts==['ctx0','ctx1','ctx0','ctx1','ctx0'],'SENSOR_CONTEXT_RECALL_FAILED')
  require([x['PE_emissions'] for x in episodes]==[[71],[72],[71],[72],[71]],'NOT_REAL_PE_SENSED')
  require([x['episode']['final_P']['version'] for x in episodes]==[2,1,2,1,3],'PE_SENSED_P_VERSIONS')
  require([len(x['episode']['P_grants']) for x in episodes]==[2,1,0,0,1],'PE_SENSED_CREDIT_DRIFT')
  expected_C=[[10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],
              [10,1,12,[12]],[10,2,15,[15]]]
  require([x['episode']['C_PE_reads'][0] for x in episodes]==expected_C,'C_PE_NOT_REBOUND_TO_SENSED_P')
  require(selection['bindings']=={'s71':'ctx0','s72':'ctx1'},'PE_SENSED_BINDING_UNSTABLE')
  flipped=s.run_sequence(t/'reverse.db',(CASES[1],CASES[0]),root=root)
  require(flipped['audit']['selector']['bindings']=={'s72':'ctx0','s71':'ctx1'},
          'HOST_FIXED_LABEL_ROUTE_DETECTED')
  def choices_by_signal(r):
   return {signal:r['audit']['contextual']['bank'][ctx]['choice']
           for signal,ctx in r['audit']['selector']['bindings'].items()}
  first_two=s.run_sequence(t/'original-order.db',CASES[:2],root=root)
  require(choices_by_signal(first_two)==choices_by_signal(flipped),'PE_SIGNATURE_MEMORY_ASSIGNMENT_DRIFT')
  cuts=[]
  for cut in (1,9,13,14,15,27,60):
   p=t/f'cut{cut}.db'
   try:s.run_epoch(p,0,(40,42),11,15,pause_after=cut,root=root)
   except d.SimulatedPowerLoss:pass
   else:raise AssertionError('INTERRUPTION_NOT_TRIGGERED')
   recovered=s.run_epoch(p,0,(40,42),11,15,root=root)
   require(cut+recovered['episode']['new_tick_rows']==65,'POWER_LOSS_DUPLICATED_TICKS')
   cuts.append({'cut':cut,'journal_head_sha256':recovered['episode']['journal_head_sha256']})
  rejects=[]
  for name,bad in [('mixed',(40,43)),('ambiguous',(40,41,42,43)),('missing',(40,)),('duplicate',(40,40,42))]:
   before=s.audit(path,root=root)
   try:s.run_epoch(path,5,bad,11,12,root=root)
   except s.SensorReject:rejects.append(name)
   else:raise AssertionError('BAD_PE_SENSOR_ADMITTED:'+name)
   require(s.audit(path,root=root)==before,'SENSOR_DENIAL_MUTATED_P')
  tamper=t/'tamper.db';s.run_sequence(tamper,CASES[:2],root=root)
  with sqlite3.connect(tamper) as db:
   db.execute("UPDATE sensed_epoch SET raw_json='[40,42,99]' WHERE epoch=0")
  try:s.audit(tamper,root=root)
  except s.SensorReject:tamper_denied=True
  else:raise AssertionError('SENSOR_ORIGIN_DRIFT_ACCEPTED')
  return {'schema':SCHEMA,'status':'V1V_PE_SENSED_CONTEXT_P_RECALL_PASS',
   'parent_v1u_sha256':PARENT_SHA,'frozen_source_pins':pins,
   'real_original_PE_classifier':True,'host_passes_context_label':False,
   'PE_signatures':[x['PE_signature'] for x in episodes],
   'derived_contexts':contexts,'derived_context_versions':[x['episode']['final_P']['version'] for x in episodes],
   'original_PE_C_reads':expected_C,'P_grants_by_epoch':[len(x['episode']['P_grants']) for x in episodes],
   'episodes':len(episodes),'persistent_tick_rows':first['new_tick_rows'],
   'second_run_new_tick_rows':repeated['new_tick_rows'],
   'signature_to_internal_context':selection['bindings'],
   'noise_equivalent_classes':True,'reversed_observation_order_retains_association':True,
   'selector_chain_sha256':selection['head_sha256'],'causal_chain_sha256':chain['chain_sha256'],
   'restart_cuts':cuts,'negative_sensor_rejections':rejects,
   'tamper_denied':tamper_denied,
   'versioned_v1v_research_learning':True,'frozen_original_BV_learning':False,
   'promotion_allowed':False,'limitations':[
     'A bounded pre-episode PE cue classifier; not BV-transported context detection',
     'Two predeclared sensor cue pairs, 40+42 and 41+43, not open-ended context learning',
     'Host authors raw observation channels and task goal, no independent sensor or goal authority',
     'C uses same-scheduler BV-native-v1 learning only AFTER PE context selection',
     'The older v1u direct context API remains callable and bypasses this optional port',
     'SQLite hashes detect drift under honest reexecution, not forging by privileged host',
     'Only 3 PE candidates 11/12/15 and A/B/C; original frozen BV-v0e never learns',
     'Cooperative POSIX lock, deterministic genesis replay; no irreversible outside effects']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('output');ap.add_argument('--root',default='.')
 ap.add_argument('--parent',required=True);args=ap.parse_args()
 r=report(args.root,args.parent);path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
 print(r['status'],'EPOCHS',r['episodes'],'TICKS',r['persistent_tick_rows'])
if __name__=='__main__':main()
