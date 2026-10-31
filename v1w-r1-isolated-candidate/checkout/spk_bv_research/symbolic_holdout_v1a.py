"""SPK/* BV v1a RESEARCH: pure paired finite-symbolic holdout evaluation.

Synthetic, DECLARED truth labels. This module cannot demonstrate native SPK
learning, physical cost, independent external truth, or a committed update.
"""
from __future__ import annotations

import copy
import hashlib
import json
from spk_bv_research.judgment_contract_v0y import (
    JudgmentContractError, ident, tick, sha, ledger_template,
)
from spk_bv_research.shadow_update_v0z import (
    validate_hypotheses, template as hypothesis_template,
)

SCHEMA = 'spk-bv-paired-symbolic-holdout/v1a'
STATUS = 'SYNTHETIC_DECLARED_LABELS_SHADOW_NO_COMMIT'
LIBRARY = 'toy-four-boolean-ops/v1a'
OBJECTIVE = 'toy.binary_accuracy'
EVALUATOR = 'toy.declared_truth_table'
OPS = frozenset(('toy.and', 'toy.or', 'toy.xor', 'toy.nand'))
TRIAL_FIELDS = frozenset(('schema','status','hypothesis_id','operator_library',
    'objective_id','evaluator_id','future_episode_id','inputs','labels','budget',
    'label_origin','labels_sha256'))
INPUT_FIELDS = frozenset(('case_id','tick','a','b'))
BUDGET_FIELDS = frozenset(('max_evaluations','max_local_changes'))
LABEL_ORIGIN = 'declared-synthetic-truth-not-independent-external-oracle'


def require(ok, message):
    if not ok: raise JudgmentContractError(message)


def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',',':'),ensure_ascii=True).encode('ascii')).hexdigest()


def binary(v, name):
    require(type(v) is int and v in (0,1), name+' must be binary integer')
    return v


def apply(op,a,b):
    require(type(op) is str and op in OPS, 'non-toy or unknown operator')
    binary(a,'input a');binary(b,'input b')
    if op=='toy.and': return a & b
    if op=='toy.or': return a | b
    if op=='toy.xor': return a ^ b
    return 1-(a & b)


def evaluate(trial, ledger, plan):
    """Score a v0z-admitted hypothetical one-operator substitution, without actuation.

    The source truth labels are explicit assertions. No independent oracle or
    real held-out temporal separation is inferred from syntactic timestamps.
    """
    admitted=validate_hypotheses(plan,ledger)
    require(type(trial) is dict and set(trial)==TRIAL_FIELDS, 'invalid trial envelope fields')
    require(trial['schema']==SCHEMA and trial['status']==STATUS, 'invalid trial envelope')
    require(trial['operator_library']==LIBRARY, 'operator library mismatch')
    require(trial['objective_id']==OBJECTIVE and trial['evaluator_id']==EVALUATOR,
            'unregistered evaluator or objective')
    require(trial['label_origin']==LABEL_ORIGIN, 'truth source must be explicitly synthetic')
    hid=ident(trial['hypothesis_id'],'hypothesis_id')
    hs=[h for h in plan['hypotheses'] if h['hypothesis_id']==hid]
    require(len(hs)==1,'unknown hypothesis')
    h=hs[0]
    require(h['evaluation_objective_id']==OBJECTIVE and h['evaluation_evaluator_id']==EVALUATOR,
            'hypothesis is not predeclared for this toy scoring rule')
    require(h['baseline_operator'] in OPS and h['candidate_operator'] in OPS,
            'candidate/baseline outside finite toy operator library')
    require(trial['future_episode_id']==h['future_episode_id'], 'wrong future episode')
    inp=trial['inputs'];labels=trial['labels'];budget=trial['budget']
    require(type(inp) is list and len(inp)==4,'toy holdout must cover all four input pairs')
    require(type(labels) is list and len(labels)==len(inp),'label count mismatch')
    require(type(budget) is dict and set(budget)==BUDGET_FIELDS,'invalid budget fields')
    require(type(budget['max_evaluations']) is int and budget['max_evaluations']==4,
            'budget must allow exactly four paired comparisons')
    require(type(budget['max_local_changes']) is int and budget['max_local_changes']==1,
            'only one hypothetical local operator substitution allowed')
    seen_pairs=set();seen_ids=set(); ticks=[]
    for i,r in enumerate(inp):
        require(type(r) is dict and set(r)==INPUT_FIELDS,'invalid input record')
        cid=ident(r['case_id'],'case_id')
        require(cid not in seen_ids,'duplicate input case ID');seen_ids.add(cid)
        at=tick(r['tick'],'input.tick'); ticks.append(at)
        require(h['holdout_start_tick']<=at<=h['holdout_end_tick'], 'input outside prospective holdout')
        pair=(binary(r['a'],'a'),binary(r['b'],'b'))
        require(pair not in seen_pairs,'duplicate input pair');seen_pairs.add(pair)
        binary(labels[i],'truth label')
    require(seen_pairs=={(0,0),(0,1),(1,0),(1,1)},'incomplete binary domain')
    require(ticks==sorted(ticks),'non-monotonic holdout record time')
    require(digest(inp)==h['control_input_sha256']==h['candidate_input_sha256'],
            'declared paired input digest is not witnessed by trial inputs')
    require(digest(budget)==h['control_budget_sha256']==h['candidate_budget_sha256'],
            'declared paired budget digest is not witnessed by trial budget')
    sha(trial['labels_sha256'],'labels_sha256')
    require(trial['labels_sha256']==digest(labels),'declared label commitment mismatch')
    base,alternative=h['baseline_operator'],h['candidate_operator']
    bp=[apply(base,r['a'],r['b']) for r in inp]
    cp=[apply(alternative,r['a'],r['b']) for r in inp]
    bc=sum(a==b for a,b in zip(bp,labels));cc=sum(a==b for a,b in zip(cp,labels))
    delta=cc-bc
    verdict=('IMPROVES_AGAINST_DECLARED_SYNTHETIC_LABELS' if delta>0 else
             'DEGRADES_AGAINST_DECLARED_SYNTHETIC_LABELS' if delta<0 else
             'TIES_AGAINST_DECLARED_SYNTHETIC_LABELS')
    return {
        'hypothesis_id':hid,'future_episode_id':h['future_episode_id'],
        'baseline_operator':base,'candidate_operator':alternative,
        'paired_input_sha256':digest(inp),'paired_budget_sha256':digest(budget),
        'declared_labels_sha256':digest(labels),
        'number_of_paired_cases':4,'baseline_correct':bc,'candidate_correct':cc,
        'accuracy_denominator':4,'correct_count_delta':delta,'classification':verdict,
        'scores_computed_in_isolated_toy':True,
        'paired_inputs_and_budget_verified_for_toy':True,
        'external_truth_or_heldout_independence_proven':False,
        'real_neuron_operators_executed':False,'native_judgments_observed':0,
        'applied_updates':0,'causal_learning_proven':False,
    }


def demo_case(name, base, candidate, label_map):
    """Return explicit synthetic materials; DO NOT bind to native BV fixture."""
    require(name in ('positive','negative','tie'), 'unsupported demo case')
    from spk_bv_research.judgment_contract_v0y import ledger_template
    ledger=ledger_template()
    inputs=[{'case_id':f'x{i}','tick':7 if i<2 else 8,'a':a,'b':b}
           for i,(a,b) in enumerate(((0,0),(0,1),(1,0),(1,1)))]
    labels=[label_map[(r['a'],r['b'])] for r in inputs]
    budget={'max_evaluations':4,'max_local_changes':1}
    i_hash=digest(inputs);b_hash=digest(budget)
    ledger['criteria']=[dict(criterion_id='toycriterion',objective_id=OBJECTIVE,
                            evaluator_id=EVALUATOR,registered_tick=0,direction='maximize')]
    ledger['decisions']=[dict(decision_id='toydecision',neuron_id='ToyA',episode_id='past',
         decision_tick=1,predecision_state_sha256='a'*64,context_sha256='b'*64,
         admissible_operators=sorted([base,candidate]),chosen_operator=base)]
    ledger['judgments']=[dict(judgment_id='toyjudgment',decision_id='toydecision',
        observer_id='ToyB',receiver_id='ToyA',criterion_id='toycriterion',sign=-1,
        source_evidence=['toy_r1'],causal_origin_id='declared_origin',produced_tick=2,
        available_tick=3)]
    ledger['proposals']=[dict(proposal_id='toyproposal',target_decision_id='toydecision',
        judgment_ids=['toyjudgment'],proposed_operator=candidate,created_tick=4,
        eligibility_window=[3,6],verdict='noop')]
    plan=hypothesis_template()
    plan['hypotheses']=[dict(hypothesis_id='toy_hypothesis',proposal_id='toyproposal',
        criterion_id='toycriterion',planning_tick=4,future_episode_id='toyfuture',
        holdout_start_tick=7,holdout_end_tick=8,baseline_operator=base,
        candidate_operator=candidate,max_local_changes=1,
        control_input_sha256=i_hash,candidate_input_sha256=i_hash,
        control_budget_sha256=b_hash,candidate_budget_sha256=b_hash,
        evaluation_objective_id=OBJECTIVE,evaluation_evaluator_id=EVALUATOR,
        evaluation_mode='declared-paired-external-holdout')]
    trial={'schema':SCHEMA,'status':STATUS,'hypothesis_id':'toy_hypothesis',
        'operator_library':LIBRARY,'objective_id':OBJECTIVE,'evaluator_id':EVALUATOR,
        'future_episode_id':'toyfuture','inputs':inputs,'labels':labels,
        'budget':budget,'label_origin':LABEL_ORIGIN,'labels_sha256':digest(labels)}
    return ledger,plan,trial


def demonstrate():
    # Fully explicit symbolic truth tables. They are not independent ground truth.
    xor={(a,b): a^b for a in (0,1) for b in (0,1)}
    and_truth={(a,b): a&b for a in (0,1) for b in (0,1)}
    tie={(0,0):0,(0,1):1,(1,0):0,(1,1):1}
    cases=[('positive','toy.and','toy.xor',xor),
           ('negative','toy.and','toy.xor',and_truth),
           ('tie','toy.and','toy.or',tie)]
    result=[]
    for name,base,candidate,labels in cases:
        ledger,plan,trial=demo_case(name,base,candidate,labels)
        result.append({'demo':name,**evaluate(trial,ledger,plan)})
    require([r['classification'].split('_')[0] for r in result]==
            ['IMPROVES','DEGRADES','TIES'],'internal demo sanity case failed')
    return result
