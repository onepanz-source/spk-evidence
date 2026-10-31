"""BV v1d: predeclared *synthetic* guard criterion on genuine, isolated A1 local kernel.

Train and evaluation inputs are disjoint. There is no independent external truth,
receiver-produced judgment, network scheduler counterfactual or committed update.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import replace, is_dataclass
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import InterventionError, require, snapshot
from spk_bv_research.native_sensitivity_v1c import (CANDIDATES, DOMAIN, TIMESTAMP,
    PREVIOUS_TICK, validate_reference, sensitivity, build as v1c_build)

SCHEMA='spk-bv-native-declared-guard-objective/v1d'
STATUS='NATIVE_LOCAL_GUARD_CRITERION_DECLARED_SYNTHETIC_ONLY'
OBJECTIVE='declared.synthetic.guard_true_iff_two_zero_channels/v1d'
# Completely fixed BEFORE computing kernel outputs. Evaluation inputs are disjoint
# from the selection inputs, but NOT independent draws from an external distribution.
TRAIN_INDEX=(0,1,2)
EVAL_INDEX=(3,4,5)
EVAL_TIMESTAMP=11
EVAL_PREVIOUS_TICK=10
EXCLUSIONS=[
 'declared-input-derived-targets-not-independent-external-truth',
 'evaluation-subset-not-random-or-independent-heldout-distribution',
 'training-selects-variant-with-fixed-candidate-set-not-feedback-recommendation',
 'local-guard-readout-not-observed-downstream-network-utility',
 'operand-perturbations-not-certified-algebra-rewrites',
 'native-feedback-judgments-zero-no-causal-credit-or-neuron-update',
 'no-network-scheduler-variant-replay-no-hardware-or-architecture-promotion',
]

def target(channels):
    """Explicit human-authored toy goal; no feedback or measured label source."""
    require(type(channels) is tuple and all(type(v) is int for v in channels), 'bad target input')
    return sum(v==0 for v in channels)>=2


def observe(compute,node,raw,channels,*,timestamp,prior_tick):
    """Observe exactly typed native (raw, bool guard, channels), twice, fail closed."""
    require(type(raw) is int and type(channels) is tuple and type(timestamp) is int and
            type(prior_tick) is int and timestamp>prior_tick,'bad kernel observation input')
    node_before=snapshot(node)
    outputs=[]
    for _ in range(2):
        state=[raw,prior_tick]; ch=list(channels)
        result=compute(node,state,timestamp,ch)
        require(state==[raw,prior_tick] and ch==list(channels) and snapshot(node)==node_before,
                'native kernel mutated observation arguments')
        require(type(result) in (tuple,list) and len(result)==3 and
                type(result[0]) is int and type(result[1]) is bool and
                type(result[2]) in (list,tuple) and
                all(type(v) is int for v in result[2]),'bad native kernel observation result')
        outputs.append((snapshot(result),result[0],result[1],tuple(result[2])))
    require(outputs[0]==outputs[1],'nondeterministic native kernel observation')
    h,raw_out,guard,emitted=outputs[0]
    return {'result_sha256':h,'post_raw':raw_out,'guard':guard,'emitted_channels':list(emitted)}


def score_pair(compute,original,variant,indices,*,timestamp,prior_tick,reference=None):
    """Only paired/local readouts, with exact baseline hashes when anchored to v1c."""
    require(type(indices) is tuple and indices and all(type(i) is int and 0<=i<len(DOMAIN) for i in indices)
            and len(set(indices))==len(indices), 'invalid predeclared subset')
    rows=[]
    for i in indices:
        raw,channels=DOMAIN[i]
        before=observe(compute,original,raw,channels,timestamp=timestamp,prior_tick=prior_tick)
        after=observe(compute,variant,raw,channels,timestamp=timestamp,prior_tick=prior_tick)
        if reference is not None:
            ref=reference[i]
            require(before['result_sha256']==ref['baseline_result_sha256'] and
                    after['result_sha256']==ref['counterfactual_result_sha256'] and
                    ref['outcome'] in ('SAME','DIFFERENT') and
                    (before['result_sha256']!=after['result_sha256'])==(ref['outcome']=='DIFFERENT'),
                    'v1c paired kernel digest drift')
        expected=target(channels)
        rows.append({'domain_index':i,'raw':raw,'channels':list(channels),
            'expected_guard':expected,'baseline':before,'candidate':after,
            'baseline_correct':before['guard'] is expected,
            'candidate_correct':after['guard'] is expected})
    bc=sum(x['baseline_correct'] for x in rows)
    cc=sum(x['candidate_correct'] for x in rows)
    return {'rows':rows,'cases':len(rows),'baseline_correct':bc,'candidate_correct':cc,
            'correct_count_delta':cc-bc}


def analyze(nodes,compute,source_v1c,*,expected_programs):
    require(type(nodes) is dict and set(nodes)=={'A','B','C'},'bad admitted neuron set')
    require(type(source_v1c) is dict and source_v1c.get('schema')=='spk-bv-native-isolated-operand-sensitivity/v1c'
            and source_v1c.get('status')=='BOUNDED_NATIVE_KERNEL_COUNTERFACTUAL_NO_UTILITY_OR_LEARNING',
            'wrong native v1c reference')
    require(source_v1c.get('probe_pairs')==30 and source_v1c.get('rejected_pairs')==0 and
            source_v1c.get('original_nodes_immutable') is True,'native v1c not complete/immutable')
    c=source_v1c['candidates']
    require(type(c) is list and len(c)==len(CANDIDATES), 'v1c candidate inventory drift')
    before={n:snapshot(node) for n,node in nodes.items()}
    train=[]
    # Only training values are computed before selecting a candidate.
    for position,(nid,index,replacement) in enumerate(CANDIDATES):
        original=nodes[nid]
        require(is_dataclass(original) and not isinstance(original,type),'nonreplaceable neuron')
        program=original.instructions
        require(type(program) is tuple and program==expected_programs[nid] and
                program[index][0]==replacement[0] and program[index]!=replacement,
                'frozen program or candidate mismatch')
        ref=c[position]
        require(ref['neuron_id']==nid and ref['instruction_index']==index and
                ref['original_program_sha256']==snapshot(program) and
                ref['original_instruction']==json.loads(json.dumps(list(program[index]))) and
                ref['candidate_instruction']==json.loads(json.dumps(list(replacement))), 'v1c candidate identity mismatch')
        variant=replace(original,instructions=program[:index]+(replacement,)+program[index+1:])
        require(snapshot(variant)!=snapshot(original),'not an isolated variant')
        scores=score_pair(compute,original,variant,TRAIN_INDEX,timestamp=TIMESTAMP,
                          prior_tick=PREVIOUS_TICK,reference=ref['domain_outcomes'])
        train.append({'candidate_position':position,'neuron_id':nid,'instruction_index':index,
                      'original_program_sha256':snapshot(program),
                      'candidate_program_sha256':snapshot(variant.instructions),**scores})
    # Tie-breaking is fixed by CANDIDATES order. Selection accesses only train scores.
    selected=max(range(len(train)),key=lambda i:train[i]['correct_count_delta'])
    nid,index,replacement=CANDIDATES[selected]
    original=nodes[nid]
    program=original.instructions
    variant=replace(original,instructions=program[:index]+(replacement,)+program[index+1:])
    evaluation=score_pair(compute,original,variant,EVAL_INDEX,timestamp=EVAL_TIMESTAMP,
                          prior_tick=EVAL_PREVIOUS_TICK)
    require(all(snapshot(nodes[n])==before[n] for n in nodes),'mutated original neuron')
    delta=evaluation['correct_count_delta']
    return {'criterion':{'objective_id':OBJECTIVE,
        'target_rule':'guard is True exactly when channels contain at least two zeros',
        'criterion_origin':'synthetic-declared-from-inputs-not-independent-oracle',
        'training_domain_indices':list(TRAIN_INDEX),'evaluation_domain_indices':list(EVAL_INDEX),
        'training_timestamp':TIMESTAMP,'training_prior_tick':PREVIOUS_TICK,
        'evaluation_timestamp':EVAL_TIMESTAMP,'evaluation_prior_tick':EVAL_PREVIOUS_TICK,
        'immutable_predeclared_design_sha256':snapshot((OBJECTIVE,DOMAIN,TRAIN_INDEX,EVAL_INDEX,
                                           TIMESTAMP,PREVIOUS_TICK,EVAL_TIMESTAMP,EVAL_PREVIOUS_TICK))},
        'training':train,'selected_candidate_position':selected,
        'selection_rule':'largest training correct_count_delta, fixed candidate order ties',
        'selected_was_training_improvement':train[selected]['correct_count_delta']>0,
        'evaluation':evaluation,
        'evaluation_classification':('IMPROVES_DECLARED_GUARD_OBJECTIVE' if delta>0 else
                                     'DEGRADES_DECLARED_GUARD_OBJECTIVE' if delta<0 else
                                     'TIES_DECLARED_GUARD_OBJECTIVE'),
        'original_nodes_immutable':True,'independent_truth_attested':False,
        'native_judgments_observed':0,'native_updates_applied':0,
        'native_learning_proven':False,'causal_credit_identified':False}


def build(v1c,v1c_bytes,v1b1,v1b1_bytes,v1a,v0w,v0w_bytes,native_baseline,native_fixture,
          admit,compute):
    anchors=validate_reference(v1b1,v1b1_bytes,v1a,v0w,v0w_bytes)
    require(native_baseline==v1b1,'v1b.1 read-only replay mismatch')
    require(v1c.get('reference_v1b1_sha256')==sha256(v1b1_bytes).hexdigest() and
            v1c.get('reference_v0w_sha256')==sha256(v0w_bytes).hexdigest() and
            v1c.get('frozen_native_sources')==v1b1.get('frozen_native_sources') and
            v1c.get('native_fixture_sha256')==v1b1.get('native_fixture_sha256'),
            'v1c custody drift')
    fixture_before=snapshot(native_fixture)
    require(fixture_before==v1b1['native_fixture_sha256'],'frozen native fixture drift')
    nodes,_=admit(native_fixture[0],native_fixture[1])
    require(snapshot(native_fixture)==fixture_before,'native admission changed fixture')
    actual=v1c_build(v1b1,v1b1_bytes,v1a,v0w,v0w_bytes,native_baseline,native_fixture,admit,compute)
    require(json.loads(json.dumps(actual,sort_keys=True))==v1c,'full native v1c recomputation mismatch')
    result=analyze(nodes,compute,v1c,expected_programs=anchors['expected_programs'])
    require(snapshot(native_fixture)==fixture_before,'native v1d altered fixture')
    return {'schema':SCHEMA,'status':STATUS,
            'reference_v1c_file_sha256':sha256(v1c_bytes).hexdigest(),
            'reference_v1b1_file_sha256':sha256(v1b1_bytes).hexdigest(),
            'reference_v0w_file_sha256':sha256(v0w_bytes).hexdigest(),
            'native_fixture_sha256':fixture_before,
            'frozen_native_sources':v1b1['frozen_native_sources'],
            'recomputed_v1c_probe_pairs':actual['probe_pairs'],
            **result,'claims_excluded':EXCLUSIONS}
