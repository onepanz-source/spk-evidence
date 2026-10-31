"""V5-T3f PUBLIC, post-hoc, day-stratified falsification of T3e.

The source-A1b truth table is inherited unchanged from T3e. This code audits
when the two candidates disagree, using actual consecutive UCI observations.
No confidence interval or per-row independence claim. No new learner.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from spk_v5_research.island_external_task_v5t3a import DatasetRow
from spk_v5_research.island_real_transition_v5t3d import (
    validated_pairs, ALLOWED_GAPS_SECONDS, LIGHT_THRESHOLD_LUX,
)
from spk_v5_research.island_successor_competition_v5t3e import (
    native_boolean_truth_table,
)

SCHEMA = 'spk-v5-t3f-day-stratified-discordance/research-v0'
NAMES = ('datatraining.txt', 'datatest.txt', 'datatest2.txt')


def _sum_metrics(rows: list[dict]) -> dict:
    """Sum disjoint daily/episode bins; do not assume iid observations."""
    n=sum(x['n'] for x in rows)
    positives=sum(x['positive'] for x in rows)
    cw=sum(x['current_wrong'] for x in rows)
    pw=sum(x['persist_wrong'] for x in rows)
    pwins=sum(x['persist_correct_current_wrong'] for x in rows)
    cwins=sum(x['current_correct_persist_wrong'] for x in rows)
    if cw-pw != pwins-cwins:
        raise AssertionError('paired disagreement arithmetic violated')
    return {'n':n,'occupied_current':positives,
            'current_errors':cw,'persist_errors':pw,
            'net_errors_avoided_by_persist':cw-pw,
            'persist_fixes':pwins,'persist_regressions':cwins}


def audit_partition(rows: tuple[DatasetRow,...], name:str, truth:dict) -> dict:
    if name not in NAMES or len(rows)<3:
        raise ValueError('unknown or too-short source')
    if type(truth) is not dict or set(truth)!={'00','01','10','11'}:
        raise ValueError('bounded native truth table required')
    # Do not silently trust a caller-supplied truth table.
    if truth != native_boolean_truth_table():
        raise ValueError('forged source-A1b truth table')
    day=defaultdict(lambda:{'n':0,'positive':0,'current_wrong':0,'persist_wrong':0,
                             'persist_correct_current_wrong':0,
                             'current_correct_persist_wrong':0,
                             'rise_total':0,'rise_occupied':0})
    state={k: {'n':0,'positive':0,'current_wrong':0,'persist_wrong':0,
               'persist_correct_current_wrong':0,'current_correct_persist_wrong':0}
           for k in ('zero_photo_occupancy_day','positive_photo_occupancy_day')}
    unpaired=0; pairs=[]; last_day=None
    for _,before,after,delta in validated_pairs(rows):
        if delta not in ALLOWED_GAPS_SECONDS:
            unpaired+=1
            continue
        name_day=after.stamp[:10]
        previous=before.light>=LIGHT_THRESHOLD_LUX
        current=after.light>=LIGHT_THRESHOLD_LUX
        decision=truth[f'{int(previous)}{int(current)}']
        c,p=decision['current'],decision['persist']
        # Photo label accessible ONLY AFTER input-only A1b decisions.
        label=after.occupied
        if type(c) is not bool or type(p) is not bool or type(label) is not bool:
            raise AssertionError('nonbinary external evidence')
        pairs.append((name_day,label,c,p, bool(current and not previous)))
        d=day[name_day]
        d['n']+=1;d['positive']+=int(label)
        d['current_wrong']+=int(c!=label);d['persist_wrong']+=int(p!=label)
        d['persist_correct_current_wrong']+=int(p==label and c!=label)
        d['current_correct_persist_wrong']+=int(c==label and p!=label)
        d['rise_total']+=int(current and not previous)
        d['rise_occupied']+=int(current and not previous and label)
        # Current and persist are identical EXCEPT on physical dark->bright.
        if (c!=p)!=(current and not previous):
            raise AssertionError('disagreements do not match source A1b rise context')
    if not pairs:
        raise ValueError('no admitted physically adjacent pairs')
    days=[]
    for key,item in sorted(day.items()):
        datum=dict(item)
        datum.update({'day':key,'weekend':datetime.strptime(key,'%Y-%m-%d').weekday()>=5,
                      'all_labels_zero':item['positive']==0,
                      'net_errors_avoided_by_persist':item['current_wrong']-item['persist_wrong']})
        if item['current_wrong']-item['persist_wrong']!=item['persist_correct_current_wrong']-item['current_correct_persist_wrong']:
            raise AssertionError('day disagreement identity')
        days.append(datum)
    grouped={}
    for kind in state:
        keys={x['day'] for x in days if x['all_labels_zero']==(kind=='zero_photo_occupancy_day')}
        for d,label,c,p,_ in pairs:
            if d not in keys:continue
            x=state[kind]
            x['n']+=1;x['positive']+=int(label)
            x['current_wrong']+=int(c!=label);x['persist_wrong']+=int(p!=label)
            x['persist_correct_current_wrong']+=int(p==label and c!=label)
            x['current_correct_persist_wrong']+=int(c==label and p!=label)
        grouped[kind]=_sum_metrics([state[kind]])
        grouped[kind]['days']=len(keys)
    total=_sum_metrics(days)
    if total['n']!=len(pairs) or total['n']!=sum(x['n'] for x in grouped.values()):
        raise AssertionError('partition total mismatch')
    if (total['net_errors_avoided_by_persist'] !=
       sum(x['net_errors_avoided_by_persist'] for x in grouped.values())):
        raise AssertionError('stratified total mismatch')
    # Each dark->bright transition is one source-grounded decision opportunity.
    # Correlation between opportunities and physical episodes is NOT assumed away.
    rise=sum(x['rise_total'] for x in days)
    rise_occupied=sum(x['rise_occupied'] for x in days)
    if rise!=total['persist_fixes']+total['persist_regressions']:
        raise AssertionError('physical bright onsets do not equal paired disagreement')
    if rise_occupied!=total['persist_regressions']:
        raise AssertionError('all persistence regressions must be occupied bright onsets')
    leave_one_out=[{'held_out_day':d['day'],
                    'other_days_net_errors_avoided':total['net_errors_avoided_by_persist']-d['net_errors_avoided_by_persist'],
                    'other_days_row_count':total['n']-d['n']}
                   for d in days]
    return {'source':name,'days':days,'day_count':len(days),
            'total':total,'stratified_by_posthoc_photo_label_presence':grouped,
            'actual_dark_to_bright_opportunities':rise,
            'bright_onsets_with_current_photo_occupied':rise_occupied,
            'leave_one_day_out_DIAGNOSTIC_ONLY':leave_one_out,
            'days_persist_better':sum(x['net_errors_avoided_by_persist']>0 for x in days),
            'days_current_better':sum(x['net_errors_avoided_by_persist']<0 for x in days),
            'days_tied':sum(x['net_errors_avoided_by_persist']==0 for x in days),
            'rejected_irregular_intervals':unpaired,
            'warning':'same-building public time series; days and bright-onset opportunities NOT iid'}


def aggregate(train:tuple[DatasetRow,...],early:tuple[DatasetRow,...],
              late:tuple[DatasetRow,...],sources:dict, predecessor:dict,
              predecessor_sha:str) -> dict:
    if (type(predecessor) is not dict or
        predecessor.get('schema')!='spk-v5-t3e-real-successor-competitor/research-v0' or
        predecessor.get('status')!='REAL_SUCCESSOR_A1B_PERSISTENCE_COMPARISON_PUBLIC_NOT_BLIND_NO_RL' or
        predecessor.get('raw_original_file_sha256')!=sources or
        predecessor.get('candidate_selection',{}).get('chosen')!='persist' or
        predecessor.get('scientific_boundary',{}).get('native_learning') is not False or
        predecessor.get('scientific_boundary',{}).get('independent_blind_holdout') is not False):
        raise ValueError('T3e predecessor custody or no-RL boundary violated')
    truth=native_boolean_truth_table()
    result={key:audit_partition(rows,name,truth) for key,rows,name in (
        ('train',train,'datatraining.txt'),
        ('early',early,'datatest.txt'),
        ('late',late,'datatest2.txt'))}
    for key,original in (('train','train'),('early','early_public_prior_to_training'),
                         ('late','later_public_after_training')):
        older=predecessor['cohorts'][original]
        found=result[key]
        if found['total']['n']!=older['admitted_successor_pairs'] or \
           found['total']['current_errors']!=older['candidate_metrics']['current']['errors'] or \
           found['total']['persist_errors']!=older['candidate_metrics']['persist']['errors'] or \
           found['total']['persist_fixes']!=older['paired_persistence_correct_current_wrong'] or \
           found['total']['persist_regressions']!=older['paired_current_correct_persistence_wrong']:
            raise ValueError('T3e aggregate report disagrees with original source-driven audit')
    late_summary=result['late']['stratified_by_posthoc_photo_label_presence']
    empty=late_summary['zero_photo_occupancy_day']['net_errors_avoided_by_persist']
    active=late_summary['positive_photo_occupancy_day']['net_errors_avoided_by_persist']
    verdict=('PUBLIC_GAIN_CONCENTRATED_ON_ZERO_OCCUPANCY_DAYS' if
             empty>0 and active<=0 and empty+active==result['late']['total']['net_errors_avoided_by_persist']
             else 'PUBLIC_GAIN_CONTEXT_DEPENDENT_UNRESOLVED')
    return {'schema':SCHEMA,'status':'POSTHOC_CALENDAR_STRATIFICATION_NO_BLIND_NO_RL',
        'predecessor_T3e_report_sha256':predecessor_sha,
        'source_original_bytes_sha256':sources,
        'original_source_A1b_truth_table_replayed':True,
        'selection_from_train_frozen':'persist',
        'cohorts':result,'interpretation':{
            'late_public_verdict':verdict,
            'late_gain_zero_occupancy_days':empty,
            'late_gain_days_with_any_occupancy':active,
            'photo_labels_not_sent_to_A':True,
            'posthoc_photo_label_day_stratification':True,
            'classification_of_day_uses_ground_truth_ONLY_FOR_AUDIT':True,
            'calendar_and_episode_groups_not_independent_trials':True,
            'public_data_already_explored':True,
            'no_native_learning':True,
            'no_endogenous_island_reward':True,
            'no_valid_p_value_or_generalization_confidence_interval':True,
            'no_frozen_contract_edits':True},
        'limits':['Day group membership is derived from photo labels and is unavailable at inference',
                  'No runtime weekend gating or new candidate selected',
                  'Light onset opportunities are not independent physical experiments',
                  'No p-value from correlated row counts or post hoc inspection',
                  'A1b successor programming is a two-reading Boolean filter, not demonstrated RL']}
