"""V5-T3c post-selection public UCI falsification audit (research only).

Frozen A1b executes EACH candidate for EACH source record. All candidate scores
are AUDITOR-ONLY, never supplied to the pilot learner; no adaptive refitting.
Contemporaneous sensors are encoded as an artificial two-tick event sequence,
so 'temporal' is *not evidence of physical temporal pattern learning*.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from spk_v5_research.island_external_task_v5t3a import (
    DatasetRow, CANDIDATES, to_demand_episode,
    EVALUATION_ROWS,
)
from spk_v5_research.island_endogenous_demand_v5t2c import evaluate_candidate

SCHEMA='spk-v5-t3c-full-public-coverage-audit/research-v0'
COHORTS=8
COHORT_SIZE=60


def confusion(rows, predicted):
    if len(rows)!=len(predicted):
        raise ValueError('prediction/observation mismatch')
    tp=tn=fp=fn=0
    for row, prediction in zip(rows, predicted):
        if type(row) is not DatasetRow or type(prediction) is not bool:
            raise ValueError('unauthorized evaluation row or prediction')
        if prediction and row.occupied: tp+=1
        elif prediction: fp+=1
        elif row.occupied: fn+=1
        else: tn+=1
    n=len(rows)
    if n==0:
        raise ValueError('empty test partition')
    return {'observations':n,'positive':tp+fn,'negative':tn+fp,
            'tp':tp,'tn':tn,'fp':fp,'fn':fn,'errors':fp+fn,
            'error_rate':round((fp+fn)/n,8),
            'balanced_accuracy':_balanced(tp,tn,fp,fn)}


def _balanced(tp,tn,fp,fn):
    if not (tp+fn) or not (tn+fp): return None
    return round((tp/(tp+fn) + tn/(tn+fp))/2,8)


def audit_partition(rows, *, original_name):
    """Native per-row replay + static-rule parity + full and disjoint-cohort audits."""
    if original_name not in ('datatraining.txt','datatest.txt','datatest2.txt') or len(rows)<COHORTS*COHORT_SIZE:
        raise ValueError('unsupported source or insufficient full coverage')
    programs={c:[] for c in CANDIDATES}
    thresholds={'light_and_co2':[], 'co2_only':[], 'never':[], 'light_only':[]}
    for i,row in enumerate(rows):
        ep=to_demand_episode(row,index=i)
        for c in CANDIDATES:
            metrics=evaluate_candidate((ep,),c)
            if metrics['forward_spikes'] not in (0,1):
                raise ValueError('expected no more than one output per evaluation episode')
            programs[c].append(bool(metrics['forward_spikes']))
        thresholds['light_and_co2'].append(row.light>=200 and row.co2>=600)
        thresholds['co2_only'].append(row.co2>=600)
        thresholds['never'].append(False)
        thresholds['light_only'].append(row.light>=200)
    if (programs['temporal']!=thresholds['light_and_co2'] or
        programs['overemit']!=thresholds['co2_only'] or
        programs['silent']!=thresholds['never']):
        raise ValueError('A1b behavior differs from simultaneous static sensor rule')
    full={c:confusion(rows,v) for c,v in programs.items()}
    # Paired errors share the same original row; never interpret rows as independent trials.
    paired={}
    for challenger in ('overemit','silent'):
        p=programs['temporal']; q=programs[challenger]
        paired[challenger]={
            'temporal_correct_challenger_wrong':sum((a==r.occupied) and (b!=r.occupied) for a,b,r in zip(p,q,rows)),
            'temporal_wrong_challenger_correct':sum((a!=r.occupied) and (b==r.occupied) for a,b,r in zip(p,q,rows)),
        }
    comparison={'light_only':confusion(rows,thresholds['light_only']),
                'light_and_co2':confusion(rows,thresholds['light_and_co2'])}
    by_date=defaultdict(list)
    for i,row in enumerate(rows):
        by_date[row.stamp[:10]].append(i)
    daily=[]
    for day,indices in sorted(by_date.items()):
        dr=tuple(rows[i] for i in indices)
        dm={c:confusion(dr,tuple(programs[c][i] for i in indices)) for c in CANDIDATES}
        daily.append({'day':day,'sample_count':len(indices),'metrics':dm})
    total=COHORTS*COHORT_SIZE
    indices=[(i*len(rows))//total for i in range(total)]
    if len(set(indices))!=total: raise ValueError('sampling indexes collide')
    cohorts=[]
    for j in range(COHORTS):
        selected=indices[j::COHORTS]
        chunk=tuple(rows[i] for i in selected)
        cm={c:confusion(chunk,tuple(programs[c][i] for i in selected)) for c in CANDIDATES}
        cohorts.append({'id':j,'n':len(chunk),'metrics':cm})
    # Recompute the exact already-published T3b 60-point selection without refitting.
    t3b_indices=[(i*len(rows))//EVALUATION_ROWS for i in range(EVALUATION_ROWS)]
    sampled=tuple(rows[i] for i in t3b_indices)
    published_60={c:confusion(sampled,tuple(programs[c][i] for i in t3b_indices)) for c in CANDIDATES}
    return {'source_filename':original_name,'source_rows':len(rows),
            'first_stamp':rows[0].stamp,'last_stamp':rows[-1].stamp,
            'full_native_A1b_candidate_audit':full,
            'paired_error_disagreement':paired,
            'static_sensors_auditor_only':comparison,
            'exact_static_equivalence_all_rows':True,
            'per_calendar_day':daily,
            'disjoint_8x60_stratification':cohorts,
            'replicated_original_T3b_60_sampling':published_60,
            'cohorts_nonindependent_time_series':True}


def validate_temporal_order(early,train,late):
    if not early or not train or not late:
        raise ValueError('empty source')
    date=lambda x:datetime.strptime(x.stamp,'%Y-%m-%d %H:%M:%S')
    if not (date(early[-1]) < date(train[0]) <= date(train[-1]) < date(late[0])):
        raise ValueError('temporal order or disjointness violation')


def aggregate_report(early,early_sha,late,late_sha,train,train_sha,pilot_cert,pilot_sha,public_eval,eval_sha):
    from spk_v5_research.island_external_task_v5t3a import pilot, evaluate
    reconstructed=pilot(train,train_sha)
    reconstructed.update({
        'source_encoding':'original UCI seven-column header, eight-column indexed rows',
        'source_id_sent_to_neuron':False,
        'source_sha_basis':'raw original file bytes, no transformations',
        'authentic_uci_ingress_schema':'spk-v5-t3b-authentic-uci-row-index/research-v0',
    })
    reconstructed['claims_excluded'].append('UCI photo labels are external oracle supervision, not endogenous RL credit')
    if reconstructed!=pilot_cert:
        raise ValueError('pilot certificate does not match original training run')
    if pilot_cert['learner']['selected']!='temporal':
        raise ValueError('this historical observation must preserve pilot choice')
    published=evaluate(late,late_sha,pilot_cert)
    published.update({
        'source_encoding':'original UCI seven-column header, eight-column indexed rows',
        'source_id_sent_to_neuron':False,
        'source_sha_basis':'raw original file bytes, no transformations',
        'authentic_uci_ingress_schema':'spk-v5-t3b-authentic-uci-row-index/research-v0',
    })
    published['claims_excluded'].append('UCI photo labels are external oracle supervision, not endogenous RL credit')
    if published!=public_eval:
        raise ValueError('published T3b evaluation differs from original-source replay')
    validate_temporal_order(early,train,late)
    t=audit_partition(train,original_name='datatraining.txt')
    e=audit_partition(early,original_name='datatest.txt')
    l=audit_partition(late,original_name='datatest2.txt')
    p=l['replicated_original_T3b_60_sampling']
    for c in CANDIDATES:
        a=public_eval['post_selection_counterfactual_audit_ONLY'][c]
        b=p[c]
        if (a['error']!=b['errors'] or a['false_positive']!=b['fp'] or
                a['false_negative']!=b['fn'] or a['correct']!=b['observations']-b['errors']):
            raise ValueError('T3b public sixty-point replay mismatch')
    return {
        'schema':SCHEMA,'phase':'POST_SELECTION_PUBLIC_AUDIT',
        'status':'PUBLIC_A1B_FULL_COVERAGE_STATIC_EQUIVALENCE_NO_BLIND_NO_RL',
        'source_sha256_original_bytes':{
            'datatraining.txt':train_sha,'datatest.txt':early_sha,'datatest2.txt':late_sha},
        'pilot_sha256':pilot_sha,'published_T3b_evaluation_sha256':eval_sha,
        'selected_policy_frozen_from_pilot':'temporal',
        'datasets':{'training_full_posthoc_DIAGNOSTIC_ONLY':t,
                    'earlier_than_training_NOT_FORWARD_HOLDOUT':e,
                    'later_than_training_PUBLIC_HOLDOUT':l},
        'key_interpretation':{
            'full_coverage_native_program_error_early':e['full_native_A1b_candidate_audit']['temporal']['errors'],
            'full_coverage_native_program_error_late':l['full_native_A1b_candidate_audit']['temporal']['errors'],
            'temporal_is_exactly_static_light_ge_200_AND_co2_ge_600':True,
            'physical_temporal_pattern_learning_demonstrated':False,
            'selection_is_existing_arm_choice_not_weight_learning':True,
            'later_public_data_used_post_selection_only':True,
            'external_photo_labels_used_as_supervised_reward':True,
            'native_BV_semantic_reward_and_native_learning':False},
        'scope_exclusions':['public, previously accessible labels: not independent blind holdout',
          'post-hoc expanded audit: no preregistered full-coverage statistical claim',
          'one correlated chronological time series, no independent row-level trials',
          'static two-sensor conjunction encoded by a synthetic one-tick offset',
          'no native neuron program updates, real temporal learning, or endogenous reinforcement',
          'per-day and interleaved 60-point cohorts are diagnostics, not valid confidence samples'],
    }
