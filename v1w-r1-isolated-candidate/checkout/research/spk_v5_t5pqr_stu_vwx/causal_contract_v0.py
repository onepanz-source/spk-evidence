"""Three logically distinct SPK research gates: observational identifiability,
synthetic controlled intervention, and shadow feedback eligibility.

Everything is host-controlled Python. Zero native C authority, verified sensing,
causal inference about a real C action, feedback credit, or learning.
"""
from __future__ import annotations
from hashlib import sha256
import json

class CausalBoundary(ValueError):
    pass

def need(test,code):
    if not test: raise CausalBoundary(code)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(value):
    return sha256(canonical(value)).hexdigest()

def validate_source(rows):
    need(type(rows) is list and len(rows)==180,'180_CASES_REQUIRED')
    for i,row in enumerate(rows):
        need(type(row) is dict and row.get('index')==i,'CASE_INDEX_DRIFT')
        need(row.get('A_outcome') in ('IMPROVED','UNCHANGED','WORSENED'),'OUTCOME_DOMAIN')
        need(type(row.get('A_assessment')) is int and row['A_assessment']=={'IMPROVED':1,'UNCHANGED':0,'WORSENED':-1}[row['A_outcome']],'OUTCOME_ASSESSMENT_MISMATCH')
        for key in ('receipt_present','research_guard_candidate','source_forward_emission_chain'):
            need(type(row.get(key)) is bool,'SOURCE_BOOLEAN_'+key)
        need(type(row.get('source_sha256')) is str and len(row['source_sha256'])==64 and all(c in '0123456789abcdef' for c in row['source_sha256']),'SOURCE_SHA')
        need(row.get('A_independent_observation_authenticated') is False and row.get('A_causal_attribution_to_C') is False and row.get('A_to_C_credit') is False,'ILLICIT_PROMOTION')
        if row['research_guard_candidate']:
            need(row['receipt_present'] and row['source_forward_emission_chain'],'GUARD_WITHOUT_CHAIN')

def observational_twins(rows):
    """Both worlds fit all 180 observations yet disagree on treatment effects.

    Receipt bit is *only* a hypothetical treatment label for non-identification
    mathematics, NOT evidence that C actually intervened on an A goal.
    """
    validate_source(rows)
    worlds=[]
    for direction in (+1,-1):
        outputs=[]
        for r in rows:
            observed=r['A_assessment']
            pseudo_action=int(r['receipt_present'])
            untreated=observed-direction if pseudo_action else observed
            treated=observed if pseudo_action else observed+direction
            need((treated if pseudo_action else untreated)==observed,'OBSERVATIONAL_PARITY')
            outputs.append({'index':r['index'],'Y_without':untreated,'Y_with':treated,'Y_observed':observed,'pseudo_action':pseudo_action})
        worlds.append({'world':'PLUS' if direction==1 else 'MINUS','illustrative_effect':direction,
                       'observed_rows_sha256':digest([x['Y_observed'] for x in outputs]),
                       'unobserved_potential_outcome_sha256':digest(outputs),
                       'potential_outcomes':outputs})
    need(worlds[0]['observed_rows_sha256']==worlds[1]['observed_rows_sha256'],'WORLDS_NOT_OBSERVATIONALLY_EQUAL')
    return worlds

def intervention_pairs(rows):
    """Simulated, host-authored twin trials on 24 guard-candidate case IDs.

    Assignment is independently pseudorandom per pair and concealed from the
    synthetic outcome generator until execution. The plant effect is DEFINED by
    this simulator, so causal identification holds only inside that model.
    """
    validate_source(rows)
    candidates=[r for r in rows if r['research_guard_candidate']]
    need(len(candidates)==24,'GUARD_COUNT')
    trials=[]
    for case in candidates:
        i=case['index']
        # Pseudorandom arm order does not change the paired difference.
        arm0_is_treated=bool(int(digest({'experiment':'SPK-T5-STU','case':i})[:2],16)&1)
        baseline=5+(i%7)
        modeled_effect={0:2,1:-1,2:0}[i%3]
        arms=[]
        for j,treated in enumerate((arm0_is_treated,not arm0_is_treated)):
            arms.append({'arm':j,'simulated_action':int(treated),'A_synthetic_measurement':baseline+modeled_effect*int(treated)})
        treated_y=next(x['A_synthetic_measurement'] for x in arms if x['simulated_action'])
        control_y=next(x['A_synthetic_measurement'] for x in arms if not x['simulated_action'])
        need(treated_y-control_y==modeled_effect,'SYNTHETIC_PAIR_EFFECT_MISMATCH')
        trials.append({'case_index':i,'reference_source_sha256':case['source_sha256'],
                       'host_controlled_pseudorandom_assignment':True,
                       'synthetic_plant_effect':modeled_effect,'paired_difference':treated_y-control_y,
                       'arms':arms,'native_C_action_performed':False,'sensor_authenticated':False})
    counts={str(e):sum(t['paired_difference']==e for t in trials) for e in (-1,0,2)}
    need(counts=={'-1':8,'0':8,'2':8},'PLANT_CASE_BALANCE_DRIFT')
    return {'trials':trials,'synthetic_effect_counts':counts,
            'mean_synthetic_paired_effect_numerator':sum(t['paired_difference'] for t in trials),
            'mean_synthetic_paired_effect_denominator':24,
            'authentic_sensor_observations':0,'native_C_actions':0,'real_C_effect_identified':False}

def research_feedback(rows):
    validate_source(rows)
    candidates=[r for r in rows if r['research_guard_candidate']]
    need(len(candidates)==24,'GUARD_COUNT')
    return [{'sequence':j,'case_index':r['index'],'source_sha256':r['source_sha256'],
             'a_observation_sha256':r['A_observation_sha256'],'a_outcome':r['A_outcome'],
             'causally_attributed_to_C':False,'sensor_authenticated':False,
             'native_credit':False,'native_learning':False,'classification':'RESEARCH_ONLY_A_LOCAL_FEEDBACK'}
            for j,r in enumerate(candidates)]
