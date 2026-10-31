"""T17 causal-action-law falsification on held-out temperatures, normal and reversed.

Precommitted before running full experiment: same T15/T16 even-vs-odd split,
ten targets, three orders, +15pp forward and +25pp reversed gain thresholds,
zero grants for four manipulated/no-learning controls, all cells auditable.
Comparisons are within a simple one-dimensional test world, not broad RL.
"""
from __future__ import annotations
import argparse, hashlib, json, random, tempfile
from pathlib import Path
from .adaptive_runtime_v2 import StagedCell,ensure,sha
from research.spk_v5_t15_macro_causal_learning.prospective_gate import (
 TRAIN_TEMPS, TEST_TEMPS, EQUILIBRIA, SEEDS)

SCHEMA='spk-v5-t17-dual-P-unknown-actuator-causal-learning/research-v0'
PARENT_SHA='e768acd122f39c38dfb3c3dee8df2c1d3e74479beb53be1a5e746a957dd6d2ca'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
MODES=('adaptive','frozen','no_feedback','altered','wrong_lineage','effect_tamper')

def scenario(folder,setpoint,seed,condition,reverse):
 path=Path(folder)/f'{setpoint}-{seed}-{condition}-{int(reverse)}.sqlite'
 c=StagedCell(path,setpoint=setpoint,reverse_actuator=reverse,ceiling=16)
 try:
  train=[t for t in TRAIN_TEMPS if t!=setpoint]
  random.Random(seed).shuffle(train)
  evals=[t for t in TEST_TEMPS if t!=setpoint]
  rows=[]
  for t in train:
   ep=c.submit(t,learning=(condition!='frozen'),feedback={
       'adaptive':'genuine','frozen':'genuine','no_feedback':'missing',
       'altered':'altered','wrong_lineage':'wrong_lineage','effect_tamper':'effect_tamper'}[condition])
   if t==train[0]:
    c.dispatch();c.dispatch();c.reopen()
   c.drain();rows.append(c.result(ep))
  trained=c.state();audit_training=c.audit();c.reopen()
  evaluations=[]
  for t in evals:
   ep=c.submit(t,learning=False)
   c.drain();evaluations.append(c.result(ep))
  evaluated=c.state();audited=c.audit()
  ensure(trained==evaluated and audited['P_grants']==audit_training['P_grants'],
         'T17_HELDOUT_P_DRIFT')
  ensure(audited['settled']==audited['episodes'] and audited['pending']==0,
         'T17_UNFINISHED_CELL')
  return {'setpoint':setpoint,'seed':seed,'mode':condition,'reversed':reverse,
   'hits':sum(x['improved'] for x in evaluations),'eval_cases':len(evaluations),
   'loss':sum(abs(x['after']-setpoint) for x in evaluations),
   'train_grants':sum(x['credit'] for x in rows),'P_sign':evaluated['actuator_sign'],
   'P_theta':evaluated['theta'],'P_version':evaluated['version'],
   'heldout_actions':[x['choice'] for x in evaluations],
   'heldout_scores':[int(x['improved']) for x in evaluations],
   'training_order':train,'eval_temps':evals,'row_digest':audited['rows_sha256'],
   'event_digest':audited['events_sha256'],'event_count':audited['events'],
   'heldout_P_frozen':True,'all_stages_committed':True}
 finally:c.close()

def report(root='.'):
 root=Path(root)
 ensure(hashlib.sha256((root/'spk_architecture_v1/pe_execution_v1b.py').read_bytes()).hexdigest()==PE_SHA,
       'T17_FROZEN_PE_DRIFT')
 ensure(hashlib.sha256((root/'research/spk_v5_t17_macro_polarity/reference/t16-fwork.json').read_bytes()).hexdigest()==PARENT_SHA,
       'T17_T16_PARENT_DRIFT')
 with tempfile.TemporaryDirectory(prefix='spk-t17-dual-P-') as td:
  runs=[scenario(td,setpoint,seed,mode,reverse) for reverse in (False,True)
        for mode in MODES for seed in SEEDS for setpoint in EQUILIBRIA]
 totals={}
 for reverse in (False,True):
  name='reversed' if reverse else 'normal'; totals[name]={}
  for mode in MODES:
   selected=[r for r in runs if r['reversed']==reverse and r['mode']==mode]
   cases=sum(x['eval_cases'] for x in selected)
   totals[name][mode]={'cases':cases,'hits':sum(x['hits'] for x in selected),
       'physical_loss':sum(x['loss'] for x in selected),
       'P_grants':sum(x['train_grants'] for x in selected),
       'correct_sign':sum(x['P_sign']==(-1 if reverse else 1) for x in selected),
       'per_seed':{str(seed):{'hits':sum(x['hits'] for x in selected if x['seed']==seed),
           'cases':sum(x['eval_cases'] for x in selected if x['seed']==seed),
           'P_grants':sum(x['train_grants'] for x in selected if x['seed']==seed)}
           for seed in SEEDS}}
 improvements={name:(totals[name]['adaptive']['hits']-totals[name]['frozen']['hits'])/
                     totals[name]['adaptive']['cases'] for name in totals}
 supported=(improvements['normal']>=0.15 and improvements['reversed']>=0.25 and
      all(totals[name]['adaptive']['correct_sign']==len(SEEDS)*len(EQUILIBRIA) and
          all(totals[name][mode]['P_grants']==0 for mode in MODES if mode!='adaptive') and
          totals[name]['adaptive']['physical_loss']<totals[name]['frozen']['physical_loss']
          for name in totals) and all(x['heldout_P_frozen'] and x['all_stages_committed'] for x in runs))
 t16=json.loads((root/'research/spk_v5_t17_macro_polarity/reference/t16-fwork.json').read_text())
 ensure(totals['normal']['frozen']['hits']==t16['totals']['frozen']['heldout_improved']==165,
        'T17_T16_NORMAL_BASELINE_DRIFT')
 ensure(totals['reversed']['frozen']['per_seed']['17']['hits']==20,
        'T17_T16_REVERSE_BASELINE_DRIFT')
 # No valid claim of original native P grants/authority: this remains a forked research runtime.
 return {'schema':SCHEMA,'parent_T16_sha256':PARENT_SHA,
    'scientific_precommit':{'equilibria':list(EQUILIBRIA),'training_even':list(TRAIN_TEMPS),
     'heldout_odd':list(TEST_TEMPS),'seeds':list(SEEDS),
     'normal_margin_pp':15,'reversed_margin_pp':25,
     'initial_sign':0,'initial_theta':12,'actuator_law':'UNKNOWN_TO_C',
     'sign_discovery':'A computed post-minus-pre via frozen SPK PE; neutral clipping never identifies sign',
     'credit':'single versioned P CAS for polarity or threshold, B relay required'},
    'totals':totals,'gains_absolute':improvements,
    'independent_T16_baseline_reproduced':True,
    'correct_sign_by_world':{name:totals[name]['adaptive']['correct_sign'] for name in totals},
    'unmodified_frozen_PE_sha256':PE_SHA,
    'all_heldout_P_frozen':all(x['heldout_P_frozen'] for x in runs),
    'audited_cell_count':len(runs),
    'staged_events':sum(x['event_count'] for x in runs),
    'paired_cell_digest':sha(runs),
    'restricted_hypothesis_supported':supported,
    'status':'BOUNDED_UNKNOWN_ACTUATOR_LEARNING_SUPPORTED' if supported else
             'BOUNDED_UNKNOWN_ACTUATOR_LEARNING_NOT_SUPPORTED',
    'limitations':['T17 is an additive research scheduler, not frozen original BV',
      'A computes action-effect direction via original PE but Python preprocesses signed sensor difference',
      'Host defines world setpoint, actions, deterministic dynamics and input temperatures',
      'Only binary actuator polarity is learned, not arbitrary or stochastic transition laws',
      'One-dimensional thermal dynamics and odd/even heldout split; 3 seeds reuse the same 10 worlds',
      'No T13 A1d original memory authorization for these thermal goals; T14 detached signature not integrated',
      'No independent physically authenticated A sensor or host-resistant root of trust',
      'No original SPK BV native semantic P learning'],
    'original_T13_A1d_thermal_P_access':False,
    'original_T14_signed_thermal_source':False,
    'original_SPK_BV_native_P_grants':0,
    'original_SPK_native_learning':False,'promotion_allowed':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='.')
 p.add_argument('--out',required=True);args=p.parse_args()
 out=Path(args.out);ensure(not out.exists() and not out.is_symlink(),'T17_REPORT_ALREADY_EXISTS')
 r=report(args.root);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
 print('T17 scientific status',r['status'],
       'normal',r['totals']['normal']['frozen']['hits'],'->',r['totals']['normal']['adaptive']['hits'],
       'reversed',r['totals']['reversed']['frozen']['hits'],'->',r['totals']['reversed']['adaptive']['hits'])
 print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=='__main__':main()
