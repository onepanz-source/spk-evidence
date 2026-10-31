"""T16 prospective macro report: staged PE-generated feedback and P-custody parity.

A successful scientific gate only demonstrates the bounded T15 thermal task
in a new *research* tick scheduler. It does not adopt legacy BV or A1d grants.
"""
from __future__ import annotations
import argparse,hashlib,json,random,tempfile
from pathlib import Path
from .staged_runtime_v1 import StagedCell,ensure,sha
from research.spk_v5_t15_macro_causal_learning.prospective_gate import (
   TRAIN_TEMPS,TEST_TEMPS,EQUILIBRIA,SEEDS,CONTROLS,experiment as t15_experiment,one_cell as t15_one_cell)

SCHEMA='spk-v5-t16-owned-staged-causal-learning/research-v0'
PARENT_SHA='83da0277ebf6ec36e0ab8fb8aab4cbd55d7eb926e64b94aef81f94e6cd353a77'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'


def scenario(folder,setpoint,seed,condition,reverse=False):
 path=Path(folder)/f'{setpoint}-{seed}-{condition}-{int(reverse)}.sqlite'
 cell=StagedCell(path,setpoint=setpoint,reverse_actuator=reverse)
 try:
  train=[t for t in TRAIN_TEMPS if t!=setpoint]
  random.Random(seed).shuffle(train)
  tests=[t for t in TEST_TEMPS if t!=setpoint]
  training=[]
  for t in train:
   if condition=='adaptive':learning,feedback=True,'genuine'
   elif condition=='frozen':learning,feedback=False,'genuine'
   else:learning,feedback=True, 'missing' if condition=='no_feedback' else condition
   ep=cell.submit(t,learning=learning,feedback=feedback)
   # Real separate transactions and at least one restart mid-episode.
   if t==train[0]:
    cell.dispatch();cell.dispatch();cell.reopen()
   cell.drain();training.append(cell.result(ep))
  theta_before=cell.state();before=cell.audit()
  if condition=='adaptive':cell.reopen()
  test_rows=[]
  for t in tests:
   ep=cell.submit(t,learning=False)
   cell.drain();test_rows.append(cell.result(ep))
  after=cell.audit();theta_after=cell.state()
  ensure(theta_before==theta_after and after['P_grants']==before['P_grants'],
         'T16_HELDOUT_P_MUTATION')
  return {'condition':condition,'setpoint':setpoint,'seed':seed,'reverse':reverse,
   'eval_cases':len(test_rows),'eval_hits':sum(x['improved'] for x in test_rows),
   'eval_loss':sum(abs(x['after']-setpoint) for x in test_rows),
   'train_grants':sum(x['credit'] for x in training),
   'theta':theta_after['theta'],'P_version':theta_after['version'],
   'eval_choices':[x['choice'] for x in test_rows],
   'eval_scores':[int(x['improved']) for x in test_rows],
   'training_temperatures':train,'heldout_temperatures':tests,
   'staged_events':after['events'],'dispatch_slots':after['dispatcher_slots'],
   'rows_sha256':after['rows_sha256'],'audit_credits':after['P_grants'],
   'fully_settled':after['settled']==after['episodes'],
   'heldout_P_frozen':True}
 finally:cell.close()


def staged_experiment():
 with tempfile.TemporaryDirectory(prefix='spk-t16-staged-') as td:
  runs=[scenario(td,eq,seed,mode) for mode in ('adaptive','frozen',*CONTROLS[1:])
        for seed in SEEDS for eq in EQUILIBRIA]
  # CONTROLS contains frozen; the explicit sequence above avoids duplicate.
  reverse=[scenario(td,eq,SEEDS[0],mode,True) for mode in ('adaptive','frozen') for eq in EQUILIBRIA]
 return runs,reverse


def report(root='.',*,compare_t15=True):
 root=Path(root)
 ensure(hashlib.sha256((root/'spk_architecture_v1/pe_execution_v1b.py').read_bytes()).hexdigest()==PE_SHA,
        'T16_FROZEN_PE_DRIFT')
 runs,reverse=staged_experiment()
 totals={}
 for mode in ('adaptive','frozen','no_feedback','altered','wrong_lineage'):
  records=[x for x in runs if x['condition']==mode]
  n=sum(x['eval_cases'] for x in records)
  totals[mode]={'heldout_cases':n,'heldout_improved':sum(x['eval_hits'] for x in records),
   'heldout_physical_loss':sum(x['eval_loss'] for x in records),
   'training_P_commits':sum(x['train_grants'] for x in records),
   'per_seed':{str(s):{'cases':sum(x['eval_cases'] for x in records if x['seed']==s),
                      'hits':sum(x['eval_hits'] for x in records if x['seed']==s),
                      'commits':sum(x['train_grants'] for x in records if x['seed']==s)} for s in SEEDS}}
 reverse_totals={mode:{'cases':sum(x['eval_cases'] for x in reverse if x['condition']==mode),
                       'hits':sum(x['eval_hits'] for x in reverse if x['condition']==mode),
                       'commits':sum(x['train_grants'] for x in reverse if x['condition']==mode)}
                       for mode in ('adaptive','frozen')}
 parities={}
 if compare_t15:
  original=t15_experiment()
  for mode in totals:
   expected=original['totals'][mode]
   ensure(all(totals[mode][k]==expected[k] for k in
       ('heldout_cases','heldout_improved','heldout_physical_loss','training_P_commits','per_seed')),
       'T16_T15_REFERENCE_OUTCOME_DRIFT:'+mode)
  ensure(reverse_totals==original['reversed_actuator_counterfactual'],
         'T16_REVERSED_PHYSICS_DRIFT')
  # Compare actual per-episode C choices and held-out results for all 30
  # adaptive and 30 fixed-control cells. Aggregate equality alone is weak.
  paired=[]
  with tempfile.TemporaryDirectory(prefix='spk-t16-independent-T15-parity-') as checkdir:
   for x in runs:
    if x['condition'] not in ('adaptive','frozen'):continue
    old=t15_one_cell(checkdir,x['setpoint'],x['seed'],x['condition'])
    ensure(x['eval_choices']==old['heldout_choices'] and
           x['eval_scores']==old['heldout_score'] and
           x['P_version']==old['P_version'] and x['theta']==old['theta_final'] and
           x['train_grants']==old['credits'],
           'T16_INDIVIDUAL_CELL_CHOICE_DRIFT')
    paired.append({'world':x['setpoint'],'seed':x['seed'],'mode':x['condition'],
                   'choices':x['eval_choices'],'scores':x['eval_scores']})
  ensure(len(paired)==60,'T16_PARITY_CELL_COUNT')
  parities={'t15_experiment_reexecuted':True,'all_five_modes':True,
            'reversed_actuator':True,'paired_case_count':len(paired),
            'paired_choices_sha256':sha(paired),
            'T15_cell_rows_sha256':original['cell_rows_sha256']}
 learned=totals['adaptive'];fixed=totals['frozen']
 positive_margin=(learned['heldout_improved']-fixed['heldout_improved'])/learned['heldout_cases']
 supported=(positive_margin>=0.10 and learned['training_P_commits']>0 and
     learned['heldout_physical_loss']<fixed['heldout_physical_loss'] and
     all(totals[x]['training_P_commits']==0 for x in ('frozen','no_feedback','altered','wrong_lineage')) and
     all(x['fully_settled'] and x['heldout_P_frozen'] for x in runs))
 return {'schema':SCHEMA,'source_T15_SHA256':PARENT_SHA,
  'world':'T15 deterministic bounded thermal cell','original_PE_compute_used':True,
  'stages':['C_PE','WORLD','A_PE','B_RELAY','C_CREDIT'],
  'transaction_scope':'ONE_DURABLE_TRANSACTION_PER_STAGE',
  'actor_ownership':{'C':'frozen PE decision + owned research P threshold',
                     'A':'sensor feature preprocessing + frozen PE comparator',
                     'B':'PE local relay; cannot authorize learning',
                     'WORLD':'deterministic host-authored thermal dynamics'},
  'independent_T15_parity':parities,'totals':totals,
  'reversed_actuator_counterfactual':reverse_totals,
  'heldout_P_frozen':all(x['heldout_P_frozen'] for x in runs),
  'research_P_grants':learned['training_P_commits'],
  'staged_dispatch_slots':sum(x['dispatch_slots'] for x in runs),
  'staged_event_rows':sum(x['staged_events'] for x in runs),
  'staged_rows_sha256':sha(runs),'restricted_gain_absolute':positive_margin,
  'hypothesis_supported_under_restricted_dynamics':supported,
  'status':'STAGED_CAUSAL_LEARNING_LIMITED_SUPPORTED' if supported else 'STAGED_CAUSAL_LEARNING_NOT_SUPPORTED',
  'T13_A1d_original_memory_permission_per_thermal_credit':False,
  'T14_signed_sensor_attestation':False,
  'native_frozen_BV_semantic_credit':False,'original_SPK_native_P_grants':0,
  'native_SPK_learning':False,'promotion_allowed':False,
  'known_limits':['Versioned T16 reference scheduler, NOT original SPK BV scheduler',
    'Host still defines thermal setpoint, world dynamics and sensor readings',
    'A computes a comparison with frozen SPK PE; Python prepares absolute distances',
    'The signed T14 source and T13 A1d memory access are NOT integrated with thermal policy updates',
    'T13 original goals 11/12 and T15 setpoints 3..12 are distinct contracts; never equate them by renaming',
    'Five distinct event transactions model staging, not independent processes or physical clock',
    'This experiment tests within-dynamics odd/even split, not broad generalization or source provenance']}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',default='.')
 parser.add_argument('--out',required=True);a=parser.parse_args();out=Path(a.out)
 ensure(not out.exists() and not out.is_symlink(),'T16_REPORT_EXISTS')
 d=report(a.root);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n')
 print('T16:',d['status'],'heldout',d['totals']['frozen']['heldout_improved'],'->',
       d['totals']['adaptive']['heldout_improved'],'original native learning 0')
 print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=='__main__':main()
