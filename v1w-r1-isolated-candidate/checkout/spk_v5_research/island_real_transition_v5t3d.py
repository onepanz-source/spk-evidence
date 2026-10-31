"""V5-T3d physical-successor UCI transition audit. Research only, NO learner.

Source row[i-1] supplies an actual earlier light observation; source row[i]
supplies a later light observation. Photographic labels are accessed ONLY after
A1b has produced its terminal output to score the external occupancy-onset task.
Ticks represent *one adjacent measured 59/60/61-second interval*, not a claim
that native simulator ticks are wall-clock minutes. No fabricated one-row P.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256

from spk_v5_research.island_external_task_v5t3a import DatasetRow, canonical
from spk_v5_research.island_objective_v5t1 import Episode, execute_episode

SCHEMA='spk-v5-t3d-physical-successor-occupancy-onset/research-v0'
LIGHT_THRESHOLD_LUX=200.0
ALLOWED_GAPS_SECONDS=(59,60,61)
PROGRAMS=('temporal','overemit','silent')


def validated_pairs(rows: tuple[DatasetRow,...]):
    if not isinstance(rows,tuple) or len(rows)<3 or any(type(r) is not DatasetRow for r in rows):
        raise ValueError('need validated immutable successive UCI records')
    previous=None
    for i,row in enumerate(rows):
        t=datetime.strptime(row.stamp,'%Y-%m-%d %H:%M:%S')
        if previous is not None:
            delta=(t-previous).total_seconds()
            if delta<=0:
                raise ValueError('nonmonotone or duplicated clock')
            # Never pretend gaps outside the declared physical one-minute window
            # were one tick. Caller must count and declare every excluded interval.
            yield i-1,rows[i-1],row,int(delta) if delta.is_integer() else delta
        previous=t


def to_transition_episode(earlier:DatasetRow,later:DatasetRow, *, identity:str, physical_delta:int) -> Episode:
    if (type(earlier) is not DatasetRow or type(later) is not DatasetRow or
            not isinstance(identity,str) or not identity or
            type(physical_delta) is not int or physical_delta not in ALLOWED_GAPS_SECONDS or
            (datetime.strptime(later.stamp,'%Y-%m-%d %H:%M:%S') -
             datetime.strptime(earlier.stamp,'%Y-%m-%d %H:%M:%S')).total_seconds()!=physical_delta):
        raise ValueError('episode requires two physically successive observed measurements')
    # PREVIOUS threshold is encoded at tick 10. CURRENT brighter-than-threshold
    # is represented by a *different real reading* at tick 11; no future input.
    first=0 if earlier.light < LIGHT_THRESHOLD_LUX else 1
    events=((10,first),)
    if later.light>=LIGHT_THRESHOLD_LUX:
        events+=((11,2),)
    return Episode(identity,events)


def confusion(outputs:list[bool],labels:list[bool]) -> dict:
    if len(outputs)!=len(labels) or not outputs or any(type(v) is not bool for v in outputs+labels):
        raise ValueError('invalid predicted/label vectors')
    tp=sum(p and y for p,y in zip(outputs,labels))
    fp=sum(p and not y for p,y in zip(outputs,labels))
    fn=sum(not p and y for p,y in zip(outputs,labels))
    tn=len(labels)-tp-fp-fn
    pos=tp+fn; neg=tn+fp
    return {'observations':len(labels),'positive_onsets':pos,'negative_nononsets':neg,
            'tp':tp,'tn':tn,'fp':fp,'fn':fn,'errors':fp+fn,
            'error_rate':round((fp+fn)/len(labels),8),
            'balanced_accuracy':round((tp/pos + tn/neg)/2,8) if pos and neg else None}


def audit_partition(rows: tuple[DatasetRow,...], name:str) -> dict:
    if name not in ('datatraining.txt','datatest.txt','datatest2.txt'):
        raise ValueError('unknown UCI source partition')
    decisions={key:[] for key in PROGRAMS}
    by_day=defaultdict(lambda: {key:[] for key in (*PROGRAMS,'target')})
    labels=[]; static_rise=[]; static_current=[]; gaps=defaultdict(int)
    paired=0; skipped=0; same_current_context_witnesses=0
    witnessed_after_dark=False; witnessed_after_bright=False
    current_bright_after_dark=0; current_bright_after_bright=0
    for index,before,after,delta in validated_pairs(rows):
        gaps[str(delta)]+=1
        if delta not in ALLOWED_GAPS_SECONDS:
            skipped+=1
            continue
        ep=to_transition_episode(before,after,identity=f'{name}:{index:05}',physical_delta=delta)
        # Strictly separate sensor-side execution from photo-derived reward.
        temporal=bool(execute_episode(ep,'temporal')['output'])
        overemit=bool(execute_episode(ep,'overemit')['output'])
        silence=bool(execute_episode(ep,'silent')['output'])
        current=after.light>=LIGHT_THRESHOLD_LUX
        previous=before.light<LIGHT_THRESHOLD_LUX
        rise=previous and current
        if (temporal!=rise or overemit!=current or silence):
            raise AssertionError('A1b mismatch: genuine physical successor temporal rule')
        # External photographic labels are not inspected until AFTER A1b execution.
        target=not before.occupied and after.occupied
        for key,pred in (('temporal',temporal),('overemit',overemit),('silent',silence)):
            decisions[key].append(pred)
            by_day[after.stamp[:10]][key].append(pred)
        labels.append(target)
        static_rise.append(rise); static_current.append(current)
        by_day[after.stamp[:10]]['target'].append(target)
        if current and previous: current_bright_after_dark+=1
        if current and not previous: current_bright_after_bright+=1
        paired+=1
    if paired<2:
        raise ValueError('no physical successor pairs')
    full={k:confusion(v,labels) for k,v in decisions.items()}
    if decisions['temporal']!=static_rise or decisions['overemit']!=static_current:
        raise AssertionError('missing static two-reading equivalence')
    byday=[{'day':d,'n':len(v['target']), 'positive_onsets':sum(v['target']),
            'metrics':{p:confusion(v[p],v['target']) for p in PROGRAMS}}
           for d,v in sorted(by_day.items())]
    # A faithful physical temporal computation is distinguishable from a
    # static *current-only* predicate, but not from a two-reading rise detector.
    found_both=bool(current_bright_after_dark and current_bright_after_bright)
    return {'filename':name,'source_rows':len(rows),'source_pair_count':len(rows)-1,
            'admitted_successor_pairs':paired,'rejected_gapped_pairs':skipped,
            'seconds_between_actual_measurements':dict(sorted(gaps.items())),
            'task':'photo-derived occupancy onset: previous absent AND current present',
            'native_A1b_full_successor_replay':full,
            'static_current_light_ge_200':confusion(static_current,labels),
            'static_two_reading_light_rise':confusion(static_rise,labels),
            'exact_temporal_equivalence_to_two_reading_rule':True,
            'current_bright_given_previous_dark':current_bright_after_dark,
            'current_bright_given_previous_bright':current_bright_after_bright,
            'counterexample_to_current_only_equivalence_exists':found_both,
            'per_calendar_day_NONINDEPENDENT':byday,
            'winning_vs_silence_by_number_of_errors':full['temporal']['errors']<full['silent']['errors'],
            'causal_input_assertions':{
              'each_episode_uses_two_distinct_real_rows':True,
              'photo_label_not_sent_to_A':True,
              'successor_gap_seconds_admitted':list(ALLOWED_GAPS_SECONDS),
              'mapping_one_physical_adjacent_reading_to_one_simulator_tick':True,
              'physical_latency_of_internal_SPk_tick_verified':False,
            }}


def aggregate(train,train_sha,early,early_sha,late,late_sha,t3c_report,t3c_sha) -> dict:
    if (type(t3c_report) is not dict or
            t3c_report.get('schema')!='spk-v5-t3c-full-public-coverage-audit/research-v0' or
            t3c_report.get('status')!='PUBLIC_A1B_FULL_COVERAGE_STATIC_EQUIVALENCE_NO_BLIND_NO_RL' or
            t3c_report.get('source_sha256_original_bytes')!={'datatraining.txt':train_sha,'datatest.txt':early_sha,'datatest2.txt':late_sha} or
            not t3c_report.get('key_interpretation',{}).get('temporal_is_exactly_static_light_ge_200_AND_co2_ge_600') or
            not t3c_report.get('key_interpretation',{}).get('physical_temporal_pattern_learning_demonstrated') is False):
        raise ValueError('T3c predecessor evidence invalid or drifted')
    ordered=lambda r: datetime.strptime(r.stamp,'%Y-%m-%d %H:%M:%S')
    if not (ordered(early[-1])<ordered(train[0]) and ordered(train[-1])<ordered(late[0])):
        raise ValueError('wrong public chronological split')
    sections={
        'train_DIAGNOSTIC_ONLY':audit_partition(train,'datatraining.txt'),
        'early_BEFORE_training':audit_partition(early,'datatest.txt'),
        'late_PUBLIC_TEST':audit_partition(late,'datatest2.txt'),
    }
    return {'schema':SCHEMA,'status':'REAL_SUCCESSOR_TEMPORAL_CAPABILITY_PASS_OCCUPANCY_ONSET_RL_NO_GO',
            'phase':'POST_HOC_PUBLIC_PHYSICAL_SUCCESSOR_FALSIFICATION',
            'source_sha256_original_bytes':{'datatraining.txt':train_sha,'datatest.txt':early_sha,'datatest2.txt':late_sha},
            't3c_predecessor_sha256':t3c_sha,
            'params_frozen_for_THIS_POSTHOC_AUDIT_only':{'light_threshold_lux':LIGHT_THRESHOLD_LUX,
                   'admitted_real_gap_seconds':list(ALLOWED_GAPS_SECONDS),
                   'time_mapping':'actual ~1-minute successive observations to abstract adjacent A1b ticks'},
            'splits':sections,
            'interpretation':{
                'actual_physically_successive_measurement_inputs':True,
                'genuine_input_order_sensitivity':True,
                'task_origin':'photo label transition generated by third-party data, selected post hoc',
                'model_temporal_rule_equals_simple_two_reading_static_program':True,
                'external_outcome_C_is_not_endogenous_reward':True,
                'new_shadow_learning_occurred':False,
                'native_program_updates':0,
                'independent_blind_holdout':False,
                'performance_comparison_post_hoc':True,
            },
            'limits':['positive cases are rare; all-minute observations are autocorrelated',
                      'earlier public test occurs BEFORE training period',
                      'public test evaluated after earlier public T3b/T3c inspection, NOT BLIND',
                      'training label pairs are task-supervision, not neuron-generated C judgment',
                      'real successor separation does not establish temporal RL or better-than-simple two-reading rule',
                      'one simulated tick denotes an admitted inter-sample interval, not physical wall clock execution',
                      'no frozen Core/Compiler/Architecture/BV source changed'],
           }
