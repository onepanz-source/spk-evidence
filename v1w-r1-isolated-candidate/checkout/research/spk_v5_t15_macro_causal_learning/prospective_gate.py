"""T15 preregistered prospective experiments: no per-trial goal/label injection.

Training: even temperatures. Evaluation: odd temperatures never provided to C
for that cell. Distinct static thermal equilibria 3..12, three training orders.
No hidden task tokens or learned rule are prepared by the host.
"""
from __future__ import annotations
import argparse,hashlib,json,random,tempfile
from pathlib import Path
from .causal_cell_v1 import LearningCell,ThermalWorld,encode,sha,ensure

PARENT_T14_SHA='2f204181d43c3ce3835daeb31f19d29d84409b93e34644b4b47248a264a69e4b'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
SCHEMA='spk-v5-t15-prospective-A-computed-feedback-falsification/research-v0'
TRAIN_TEMPS=(0,2,4,6,8,10,12,14)
TEST_TEMPS=(1,3,5,7,9,11,13,15)
EQUILIBRIA=tuple(range(3,13))
SEEDS=(17,29,43)
CONTROLS=('frozen','no_feedback','altered','wrong_lineage')

def one_cell(td,target,seed,condition,*,reverse_actuator=False):
    if condition not in ('adaptive',*CONTROLS):raise ValueError('CONDITION_UNKNOWN')
    cell=LearningCell(Path(td)/f'{condition}-{target}-{seed}-{int(reverse_actuator)}.sqlite',
                      setpoint=target,reverse_actuator=reverse_actuator)
    try:
        train=[t for t in TRAIN_TEMPS if t!=target]
        # Order is determined by published seed and feature; no access to
        # evaluation labels, and no per-episode correct action from the host.
        random.Random(seed).shuffle(train)
        test=[t for t in TEST_TEMPS if t!=target]
        train_rows=[]
        for x in train:
            if condition=='adaptive': mode='genuine';learning=True
            elif condition=='frozen':mode='genuine';learning=False
            else:mode=condition if condition!='no_feedback' else 'missing';learning=True
            train_rows.append(cell.trial(x,learning=learning,feedback=mode))
        theta=cell.state()['theta'];version=cell.state()['version']
        cell.reopen()
        before=cell.audit()
        test_rows=[cell.trial(x,learning=False,feedback='genuine') for x in test]
        after=cell.audit()
        ensure(after['P_version']==before['P_version']==version and after['theta']==theta,
               'HELDOUT_P_MUTATED')
        correct=sum(t['improved'] for t in test_rows)
        # Environment-only utility, not adapted from any A verdict.
        physical_loss=sum(abs(t['after']-target) for t in test_rows)
        return {'condition':condition,'setpoint':target,'seed':seed,
                'train_temps':train,'eval_temps':test,'train_actions':len(train_rows),
                'test_actions':len(test_rows),'train_negative':sum(t['verdict']=='WORSENED' for t in train_rows),
                'credits':sum(t['credit'] for t in train_rows),
                'theta_final':theta,'P_version':version,'heldout_improved':correct,
                'heldout_loss':physical_loss,
                'heldout_choices':[t['choice'] for t in test_rows],
                'heldout_score':[int(t['improved']) for t in test_rows],
                'audit':{'credits':after['credits'],'events':after['events'],
                         'source_rows_sha256':after['source_rows_sha256']},
                'heldout_P_frozen':True,'reverse_actuator':reverse_actuator}
    finally:cell.close()

def experiment():
    # No T14 lab receipt: the falsification harness tests *causal source
    # computation* separately, not an extension of original T14 custody.
    with tempfile.TemporaryDirectory(prefix='spk-t15-falsification-') as td:
        cells=[one_cell(td,target,seed,condition) for condition in ('adaptive',*CONTROLS)
                 for seed in SEEDS for target in EQUILIBRIA]
        reversed_cells=[one_cell(td,target,SEEDS[0],condition,reverse_actuator=True)
                        for condition in ('adaptive','frozen') for target in EQUILIBRIA]
    totals={}
    for condition in ('adaptive',*CONTROLS):
        data=[x for x in cells if x['condition']==condition]
        n=sum(x['test_actions'] for x in data)
        hit=sum(x['heldout_improved'] for x in data)
        totals[condition]={'heldout_cases':n,'heldout_improved':hit,
                          'heldout_accuracy':hit/n,'heldout_physical_loss':sum(x['heldout_loss'] for x in data),
                          'training_P_commits':sum(x['credits'] for x in data),
                          'per_seed':{str(seed):{
                             'cases':sum(x['test_actions'] for x in data if x['seed']==seed),
                             'hits':sum(x['heldout_improved'] for x in data if x['seed']==seed),
                             'commits':sum(x['credits'] for x in data if x['seed']==seed)}
                             for seed in SEEDS}}
    adaptive={(x['setpoint'],x['seed']):x for x in cells if x['condition']=='adaptive'}
    frozen={(x['setpoint'],x['seed']):x for x in cells if x['condition']=='frozen'}
    gain_by_world=[]
    for target in EQUILIBRIA:
        a=sum(adaptive[(target,seed)]['heldout_improved'] for seed in SEEDS)
        f=sum(frozen[(target,seed)]['heldout_improved'] for seed in SEEDS)
        gain_by_world.append({'setpoint':target,'adaptive_hits':a,'frozen_hits':f,'delta':a-f})
    baseline=totals['frozen'];learned=totals['adaptive']
    improvement=learned['heldout_accuracy']-baseline['heldout_accuracy']
    # Research claim is explicit and can fail. 10 percentage points is a
    # prospective minimum margin, not post-hoc tuning or a significance test.
    supported=(improvement>=0.10 and
               all(totals['adaptive']['per_seed'][str(s)]['hits']>
                   totals['frozen']['per_seed'][str(s)]['hits'] for s in SEEDS) and
               learned['training_P_commits']>0 and
               learned['heldout_physical_loss']<baseline['heldout_physical_loss'] and
               all(totals[c]['training_P_commits']==0 for c in CONTROLS))
    reversed_counterfactual={condition:{'cases':sum(x['test_actions'] for x in reversed_cells
                                                 if x['condition']==condition),
                                     'hits':sum(x['heldout_improved'] for x in reversed_cells
                                                if x['condition']==condition),
                                     'commits':sum(x['credits'] for x in reversed_cells
                                                  if x['condition']==condition)}
                             for condition in ('adaptive','frozen')}
    return {'schema':SCHEMA,
            'source_T14_report_sha256':PARENT_T14_SHA,
            'experiment_precommit':{'world':'deterministic clipped linear thermal cell',
              'plant':'heat +1, cool -1, bounded [0,15]',
              'equilibria':list(EQUILIBRIA),'seeds':list(SEEDS),
              'training_temperatures_even':list(TRAIN_TEMPS),
              'heldout_temperatures_odd':list(TEST_TEMPS),
              'exclude_equilibrium':True,'initial_theta':12,
              'positive_margin_absolute':0.10,
              'A_reward':'A-local error features and original _compute_local PE comparator',
              'C_program':'two complementary original _compute_local PE branches',
              'credit_rule':'monotone one-dimensional threshold versioned CAS on worsening',
              'physical_sensor':'simulated, NOT authenticated hardware'},
            'totals':totals,'gain_by_world':gain_by_world,
            'cell_rows_sha256':sha(cells),
            'reversed_actuator_counterfactual':reversed_counterfactual,
            'negative_controls_fail_closed':all(totals[c]['training_P_commits']==0 for c in CONTROLS),
            'evaluation_has_no_P_writes':all(x['heldout_P_frozen'] for x in cells),
            'adaptive_gain_absolute':improvement,
            'hypothesis_support_on_restricted_world':supported,
            'status':'RESTRICTED_CAUSAL_LEARNING_SUPPORTED' if supported else 'RESTRICTED_CAUSAL_LEARNING_NOT_SUPPORTED',
            'scientific_limits':[
              'A and C actors are Python-hosted research implementations; only the local PE primitive comes from original SPK',
              'A Python actor encodes absolute-distance sensor features before PE comparison',
              'C update assumes known monotone signed actuator model, not inferred world dynamics',
              'World equilibria and deterministic transition law are authored by the test harness; no external attestation',
              'Held-out temperatures are new within each world but drawn from the same one-dimensional thermal dynamics',
              'Repeated seeds share the same worlds and held-out temperatures; not independent physical samples',
              'The result does not test other topologies, real time, physical transport, native original BV, or native SPK learning',
              'Signed laboratory protocol T14 and original A1d access are not part of this falsification harness',
              'Reversing actuator sign invalidates the credit rule assumption and is an explicit model-misspecification counterfactual',
              'No broad claims about generalization or causal discovery are licensed'],
            'original_frozen_sPK_P_learning':False,'promotion_allowed':False}

def report(root):
    root=Path(root)
    ensure(hashlib.sha256((root/'spk_architecture_v1/pe_execution_v1b.py').read_bytes()).hexdigest()==PE_SHA,
           'T15_ORIGINAL_PE_SOURCE_DRIFT')
    return experiment()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='.')
    p.add_argument('--out',required=True)
    args=p.parse_args();out=Path(args.out)
    ensure(not out.exists() and not out.is_symlink(),'T15_REPORT_ALREADY_EXISTS')
    data=report(args.root);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('T15 PROSPECTIVE A-COMPUTED FEEDBACK EXPERIMENT:',data['status'])
    print('heldout',data['totals']['frozen']['heldout_improved'],'->',data['totals']['adaptive']['heldout_improved'],
          'of',data['totals']['adaptive']['heldout_cases'])
    print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=='__main__':main()
