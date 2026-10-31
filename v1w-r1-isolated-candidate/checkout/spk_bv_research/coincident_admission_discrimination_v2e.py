"""BV v2e: predeclared read-only frozen-native admission experiment.

Observational discrimination, not an implementation or inference of native CMP,
not a semantic observer, and no receiver control/learning claim.
"""
from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass, replace
from hashlib import sha256
from pathlib import Path
import json

from spk_bv_research.off_on_v0t import PINNED, require, snapshot, source_pins, runtime_modules_bound
from spk_bv_research.inflight_pressure_v0v import validate_transport
from spk_bv_research.workload_sensitivity_v0w import _validate_events, WORKLOADS, CAPACITY_PROFILES
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_holdout_differential_v2d import SCHEMA as D_SCHEMA, STATUS as D_STATUS, compact_v0w

SCHEMA = 'spk-bv-frozen-native-coincident-admission-discrimination/v2e'
STATUS = 'SOURCE_BOUND_NATIVE_ADMISSION_MATRIX_MEASURED_CAUSE_UNRESOLVED'
OFFLINE_STATUS = 'PREDECLARED_ADMISSION_DISCRIMINATION_NO_NEW_NATIVE_RUN'
SOURCE = 'READONLY_FROZEN_V0E_NEW_PREDECLARED_NATIVE_ADMISSION_INTERVENTIONS'
# Case recipes use solely the two original event templates, timestamp and tuple order.
# (template id, timestamp); do not change CMP operands, fabric or frozen code.
RECIPES = (
 ('single_first', ((0,1),)),
 ('single_second', ((1,1),)),
 ('original_gap2', ((0,1),(1,3))),
 ('mixed_coincident', ((0,1),(1,1))),
 ('reverse_coincident', ((1,1),(0,1))),
 ('first_first_coincident', ((0,1),(0,1))),
 ('second_second_coincident', ((1,1),(1,1))),
 ('adjacent', ((0,1),(1,2))),
 ('delayed', ((0,1),(1,4))),
 ('triple_mixed_coincident', ((0,1),(1,1),(0,1))),
 ('triple_first_coincident', ((0,1),(0,1),(0,1))),
 ('triple_staggered', ((0,1),(1,2),(0,3))),
 ('two_coincident_clusters', ((0,1),(1,1),(0,3),(1,3))),
 ('triple_gap', ((0,1),(1,3),(0,5))),
 ('repeated_episode', ((0,1),(1,3),(0,9),(1,11))),
)
ANCHORS = {'original_gap2':'baseline','mixed_coincident':'coincident',
           'delayed':'second_plus_1','repeated_episode':'repeated_episode'}
EXCLUDED = (
 'native-aggregated-counts-do-not-identify-CMP-or-scheduler-coalescence-mechanism',
 'read-only-native-result-and-posthoc-summaries-not-online-recipient-knowledge',
 'source-template-comparison-is-not-proven-independent-source-identity',
 'identical-output-for-different-inputs-does-not-prove-identical-dynamic-work',
 'per-event-per-tick-per-template-predictions-are-research-heuristics-not-SPK-semantics',
 'frozen-native-scheduler-probed-without-hook-or-live-observation-delivery',
 'no-noninterference-under-all-timing-or-capacity-or-N-node-systems',
 'no-native-authentication-absence-witness-endogenous-judgment-or-learning',
 'no-frozen-source-or-architecture-modification',
)


def validate_predecessors(d,db,w,wb):
    require(type(d) is dict and type(db) is bytes and db==canon(d) and
            d.get('schema')==D_SCHEMA and d.get('status')==D_STATUS and
            d.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            d.get('historical_native_comparison_cells')==30 and
            d.get('historical_native_count_equal_cells')==24 and
            d.get('historical_native_count_mismatch_cells')==6 and
            d.get('new_frozen_scheduler_executions')==0 and
            d.get('coincident_stimulus_count_contrast')=={
                'native_total_emissions':3,'micro_total_emissions':6,
                'native_terminal':1,'micro_terminal':2,
                'same_external_input_timestamps':True,
                'native_aggregation_mechanism_inferred':False},
            'v2d attestation invalid')
    require(type(w) is dict and type(wb) is bytes and wb==compact_v0w(w) and
            sha256(wb).hexdigest()==d.get('reference_v0w_sha256') and
            w.get('schema')=='spk-bv-native-temporal-workload-three-arm/v0w' and
            w.get('status')=='SOURCE_BOUND_TEMPORAL_WORKLOAD_MODEL_SCAN_ONLY' and
            w.get('same_fixture_before_after_every_run') is True and
            w.get('source_sha256')==PINNED and
            w.get('workloads')==list(WORKLOADS) and
            w.get('capacity_profiles')==[
                {'fabric_slots_per_tick':a,'max_inflight_occurrences':b}
                for a,b in CAPACITY_PROFILES],
            'v0w historical native custody invalid')
    require(len(w.get('cells',()))==15, 'v0w expected 15 historical cells')
    for name,wi in ANCHORS.items():
        cell=w['cells'][WORKLOADS.index(wi)*3]
        require(cell.get('workload')==wi and
                (cell.get('fabric_slots_per_tick'),cell.get('max_inflight_occurrences'))==(1,4) and
                type(cell.get('runs')) is dict and set(cell['runs'])=={s for s,_,_ in ARMS},
                'inherited workload anchor missing: '+name)
    require(all(type(row) is dict and row.get('aggregate_counts_equal') is (row.get('workload')!='coincident')
                for row in d.get('native_micro_comparisons',[])) and
            len(d['native_micro_comparisons'])==30,
            'historical mismatch shape changed')
    return True


def build_workload(case, recipe):
    events=_validate_events(case)
    require(type(recipe) is tuple and 1<=len(recipe)<=4 and
            all(type(i) is tuple and len(i)==2 and type(i[0]) is int and
                i[0] in (0,1) and type(i[1]) is int and 1<=i[1]<=20
                for i in recipe), 'invalid native probe recipe')
    ticks=[t for _,t in recipe]
    require(ticks==sorted(ticks),'native probe input timestamps out of order')
    altered=replace(case,events=tuple(replace(events[i],timestamp=t) for i,t in recipe))
    require(snapshot(replace(altered,events=events))==snapshot(case),
            'non-event fixture fields changed')
    return altered


def predictions(recipe, *, templates_distinct):
    ticks=[t for _,t in recipe]
    return {
        'independent_three_emissions_per_input':3*len(recipe),
        'one_three_emission_chain_per_tick':3*len(set(ticks)),
        'one_three_emission_chain_per_template_tick':(
            3*len(set(recipe)) if templates_distinct else None),
    }


def source_template_distinguishable(case):
    e0,e1=_validate_events(case)
    return snapshot(replace(e0,timestamp=1))!=snapshot(replace(e1,timestamp=1))


def _check_anchor(label, run, w):
    row=w['cells'][WORKLOADS.index(ANCHORS[label])*3]
    for mode,_,_ in ARMS:
        actual=run[mode];reference=row['runs'][mode]
        for key in ('whole_result_sha256','metrics','forward_states_sha256',
                    'forward_emission_payload_multiset_sha256',
                    'forward_terminal_payload_multiset_sha256',
                    'last_forward_terminal_tick','last_feedback_delivery_tick'):
            require(actual.get(key)==reference.get(key),
                    f'frozen-native holdout anchor drift {label}/{mode}/{key}')


def native_experiment(fixture_fn, executor, plan_type, w, *, root:Path, pin_sources=True):
    root=root.resolve(strict=True)
    pins_before=source_pins(root) if pin_sources else None
    if pin_sources: runtime_modules_bound(root,executor,fixture_fn,plan_type)
    require(is_dataclass(plan_type) and {'enabled','priority'} <= {f.name for f in fields(plan_type)},
            'invalid frozen BV control plan')
    native=fixture_fn()
    case,fabric,plans=validate_transport(native)
    events=_validate_events(case)
    baseline=snapshot(native)
    require(baseline==w['original_fixture_sha256'], 'fixture changed from v0w source')
    distinguishable=source_template_distinguishable(case)
    cells=[]
    for label,recipe in RECIPES:
        changed=build_workload(case,recipe)
        data=(changed,fabric,plans)
        cell_digest=snapshot(data)
        require(snapshot(native)==baseline,'native fixture mutated before probe')
        runs={}
        for mode,enabled,priority in ARMS:
            runs[mode]=_arm(executor,plan_type,changed,fabric,plans,
                            f'v2e/{label}/{mode}',enabled,priority,cell_digest,data)
            require(snapshot(data)==cell_digest and snapshot(native)==baseline,
                    'frozen input mutated during native run')
        if label in ANCHORS: _check_anchor(label,runs,w)
        # Only describe empirical counts, never promote a hypothesis on one fit.
        forward=[runs[mode]['metrics']['forward_emissions'] for mode,_,_ in ARMS]
        p=predictions(recipe,templates_distinct=distinguishable)
        cells.append({
            'label':label,'recipe_template_index_and_tick':[list(v) for v in recipe],
            'external_input_ticks':[t for _,t in recipe],
            'event_count':len(recipe),'input_tuple_order_preserved':True,
            'rewritten_case_sha256':snapshot(changed),
            'shared_cell_input_sha256':cell_digest,
            'was_v0w_full_result_replay_anchor':label in ANCHORS,
            'runs':runs,
            'candidate_total_emission_predictions':p,
            'candidate_matches_per_control':{
                k:None if target is None else [n==target for n in forward]
                for k,target in p.items()},
            'observed_total_emissions_per_control':forward,
            'observed_terminal_per_control':[
                runs[mode]['metrics']['forward_terminal'] for mode,_,_ in ARMS],
            'native_mechanism_identified':False,
        })
    if pin_sources:
        require(source_pins(root)==pins_before, 'frozen producer source changed during v2e')
        runtime_modules_bound(root,executor,fixture_fn,plan_type)
    require(snapshot(native)==baseline, 'original fixture modified after native matrix')
    return {'cells':cells,'original_fixture_sha256':baseline,
            'source_template_variants_distinguishable_after_time_normalization':distinguishable,
            'native_runs':len(cells)*len(ARMS),
            'full_result_anchor_cells':len(ANCHORS)*len(ARMS),
            'pins':pins_before}


def analyze(d,db,w,wb, *, experimental=None, frozen_custody=False):
    validate_predecessors(d,db,w,wb)
    require(type(frozen_custody) is bool, 'invalid custody mode')
    if experimental is not None:
        require(type(experimental) is dict and experimental.get('native_runs')==45 and
                experimental.get('full_result_anchor_cells')==12 and
                len(experimental.get('cells',()))==len(RECIPES) and
                experimental.get('original_fixture_sha256')==w['original_fixture_sha256'] and
                experimental.get('pins')==PINNED and frozen_custody,
                'new native matrix requires source-bound full anchor custody')
    return {
        'schema':SCHEMA,
        'status':STATUS if experimental is not None else OFFLINE_STATUS,
        'source_kind':SOURCE if experimental is not None else 'PREDECLARED_DESIGN_AND_HISTORICAL_REPORTS_ONLY',
        'reference_v2d_sha256':sha256(db).hexdigest(),
        'reference_v0w_sha256':sha256(wb).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':frozen_custody,
        'native_semantic_probe_executed':experimental is not None,
        'native_executor_version':'spk-bv-live-dual-event-scheduler/v0e' if experimental is not None else None,
        'predeclared_workload_recipes':[
            {'label':name,'template_index_and_tick':[list(v) for v in recipe]}
            for name,recipe in RECIPES],
        'new_frozen_scheduler_executions':experimental['native_runs'] if experimental else 0,
        'full_native_v0w_anchor_replay_count':experimental['full_result_anchor_cells'] if experimental else 0,
        'native_source_template_variants_distinguishable':(
            experimental['source_template_variants_distinguishable_after_time_normalization']
            if experimental else None),
        'native_matrix':experimental['cells'] if experimental else None,
        'prior_native_coincident_total_emissions':3,
        'prior_separate_micro_coincident_total_emissions':6,
        'origin_of_hypotheses':'PREREGISTERED_DISCRIMINANTS_INSPIRED_BY_V2D_NOT_NATIVE_MECHANISM',
        'native_CMP_semantics_or_scheduler_coalescence_identified':False,
        'native_equivalence_to_v2a_v2c_v2d_proven':False,
        'native_B_control_messages':0,
        'native_independent_absence_certificates':0,
        'native_receiver_judgments':0,
        'native_operator_updates':0,
        'native_learning_proven':False,
        'claims_excluded':list(EXCLUDED),
    }
