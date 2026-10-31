"""V2d: native PREEXISTING v0w workload holdout vs new micro explicit input clock.

No new native runs, no native semantic equivalence or receiver authority.
Existing v0w reports were generated before v2c's fitted temporal policy.
"""
from __future__ import annotations
import json
from hashlib import sha256
from spk_bv_research.off_on_v0t import require, PINNED
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.temporal_differential_v2c import analyze as replay_c, SCHEMA as C_SCHEMA, STATUS as C_STATUS
from spk_bv_research.workload_sensitivity_v0w import (
    SCHEMA as W_SCHEMA, STATUS as W_STATUS, WORKLOADS, CAPACITY_PROFILES,
)
from spk_bv_research.native_factorial_interaction_v1q import SCHEMA as Q_SCHEMA
from spk_bv_research.native_capture_v0k import canonical_fixture, _json_bytes
from spk_backvalidation_v2.observed_scheduler_v2a import BoundedCaseV2a, ObserverV2a, ObservationV2a, PORT_VERSION
from spk_backvalidation_v2.explicit_input_executor_v2d import (
    EXECUTOR_VERSION, ExplicitInputsV2d, execute_explicit_v2d,
)

SCHEMA='spk-bv-preexisting-native-workload-holdout-differential/v2d'
STATUS='PRIOR_NATIVE_COINCIDENT_INPUT_COUNTEREXAMPLE_TO_MICRO_RELAY_COUNTS'
SOURCE='PRIOR_NATIVE_V0W_WORKLOAD_REPORT_VS_NEW_EXPLICIT_INPUT_MICRO_RESEARCH'
EXCLUDED=[
    'native-v0w-measurements-are-prior-source-bound-not-new-scheduler-runs',
    'micro-relay-is-not-native-CMP-even-when-counts-agree',
    'coincident-external-inputs-yield-different-total-emissions-in-this-fixture',
    'native-aggregate-emission-count-does-not-prove-a-specific-coalescence-mechanism',
    'native-v0w-forward-counts-do-not-disclose-native-AB-per-event-holdout-timestamps',
    'micro-ticks-are-not-independent-native-clock-or-receiver-knowledge',
    'no-spike-identity-join-or-endogenous-feedback-or-authentication-or-learning',
    'frozen-core-network-compiler-architecture-and-scheduler-remain-untouched',
]


def compact_v0w(w):
    return (json.dumps(w,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                       allow_nan=False)+'\n').encode('ascii')


def validate_sources(c,cb,w,wb,b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,
                     sha_a,sha_c):
    require(type(c) is dict and type(cb) is bytes and cb==canon(c) and
            c.get('schema')==C_SCHEMA and c.get('status')==C_STATUS and
            c.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            c.get('original_mode_order_and_AB_tick_projection_fit_count')==2 and
            c.get('native_CMP_semantics_equivalent') is False and
            c.get('reference_v2b_sha256')==sha256(bb).hexdigest(),
            'v2c original experiment report is not attested')
    rebuild=replay_c(b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a,sha_c,
                     frozen_custody=True)
    require(canon(rebuild)==cb,'v2c byte replay mismatch')
    require(type(w) is dict and type(wb) is bytes and 0<len(wb)<=300_000 and
            wb==compact_v0w(w) and w.get('schema')==W_SCHEMA and
            w.get('status')==W_STATUS and w.get('same_fixture_before_after_every_run') is True and
            w.get('variation_scope')=='external_event_timestamps_and_episode_repetition_only' and
            w.get('resource_scope')=='capacity_profiles_((1,4),(2,1),(2,4))_other_plans_unchanged' and
            w.get('source_sha256')==PINNED and
            w.get('original_fixture_sha256')==q.get('native_fixture_sha256') and
            q.get('schema')==Q_SCHEMA and
            w.get('workloads')==list(WORKLOADS) and
            w.get('capacity_profiles')==[{'fabric_slots_per_tick':u,'max_inflight_occurrences':v}
                                           for u,v in CAPACITY_PROFILES] and
            w.get('v0v_reference_check',{}).get('status')=='THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED' and
            w.get('v0v_reference_check',{}).get('v0v_v0u_v0t_v0o_chain') is True,
            'v0w source/fixture/capacity provenance mismatch')
    rows=w.get('cells')
    require(type(rows) is list and len(rows)==15,'unexpected native v0w workload rows')
    expected={'baseline':[1,3], 'coincident':[1,1],
              'second_plus_1':[1,4],'second_plus_3':[1,6],
              'repeated_episode':[1,3,9,11]}
    for i,row in enumerate(rows):
        workload=WORKLOADS[i//3]
        cap,inflight=CAPACITY_PROFILES[i%3]
        require(type(row) is dict and row.get('status')=='COMPLETE_THREE_ARM_WORKLOAD_CELL' and
                row.get('workload')==workload and
                row.get('stimulus_timestamps')==expected[workload] and
                row.get('stimulus_count')==len(expected[workload]) and
                (row.get('fabric_slots_per_tick'),row.get('max_inflight_occurrences'))==(cap,inflight) and
                type(row.get('runs')) is dict and
                set(row['runs'])=={'off','on_forward_first','on_feedback_first'},
                'v0w malformed native workload cell')
        for mode in ('off','on_forward_first'):
            n=row['runs'][mode]
            metrics=n.get('metrics',{})
            require(type(metrics.get('forward_emissions')) is int and
                    type(metrics.get('forward_terminal')) is int and
                    metrics['forward_emissions']>=metrics['forward_terminal']>=0 and
                    n.get('enabled') is (mode=='on_forward_first') and
                    n.get('priority')=='forward-first' and
                    type(n.get('whole_result_sha256')) is str and
                    len(n['whole_result_sha256'])==64,
                    'native v0w result shape/priority invalid')
    return expected


def paired_micro(workload,ticks,mode,*, capacity=512):
    case=BoundedCaseV2a('holdout.v2d.'+workload+'.'+mode,
                        tuple(1 for _ in ticks),('relay',)*3,mode=='on')
    schedule=ExplicitInputsV2d(tuple(ticks),1)
    off=execute_explicit_v2d(case,schedule)
    port=ObserverV2a(capacity=capacity)
    on=execute_explicit_v2d(case,schedule,observation_port=port)
    require(_json_bytes(canonical_fixture(off))==_json_bytes(canonical_fixture(on)),
            'micro observer changed forward result bytes')
    if not port.summary()['complete']:
        return on, port
    records=port.events
    require(len(records)==on['logical_event_count'] and
            len(records)>0 and records[-1].phase=='interval_coverage_close' and
            sum(e.phase=='interval_coverage_close' for e in records)==1 and
            all(type(e) is ObservationV2a and e.version==PORT_VERSION and
                e.episode==case.episode and e.ordinal==i and
                (i==0 or e.logical_tick>=records[i-1].logical_tick)
                for i,e in enumerate(records)),
            'micro observed event sequence/identity invalid')
    require(sum(e.phase=='sender_port_emission' for e in records)==
            sum(on['forward_emissions'].values()) and
            on['forward_terminal_count']==on['forward_emissions']['C'] and
            on['receiver_B_control_packets']==on['native_feedback_assessments']==
            on['operator_updates']==0,
            'micro source/receiver evidence overclaim')
    require([e.logical_tick for e in records if
             e.phase=='sender_port_emission' and e.actor=='A']==on['emission_ticks']['A'],
            'micro A emission timestamp diverged')
    return on,port


def analyze(c,cb,w,wb,b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,
            sha_a,sha_c,sha_d,*,frozen_custody=False):
    require(type(frozen_custody) is bool and all(type(h) is str and len(h)==64 and
            all(z in '0123456789abcdef' for z in h)
            for h in (sha_a,sha_c,sha_d)), 'bad micro source digest')
    ticks_by_workload=validate_sources(c,cb,w,wb,b,bb,a,ab,q,qb,m,mb,z,zb,y,yb,x,xb,sha_a,sha_c)
    comparisons=[];micro_runs=[]
    for workload in WORKLOADS:
        for mode in ('off','on'):
            ticks=ticks_by_workload[workload]
            out,port=paired_micro(workload,ticks,mode)
            micro_total=sum(out['forward_emissions'].values())
            micro_end=out['forward_terminal_count']
            micro_runs.append({'workload':workload,'mode':mode,
                               'input_ticks':ticks,'total_emissions':micro_total,
                               'terminal':micro_end,'A_emission_ticks':out['emission_ticks']['A'],
                               'B_emission_ticks':out['emission_ticks']['B'],
                               'C_emission_ticks':out['emission_ticks']['C'],
                               'observer_records':len(port.events),
                               'source_owned_micro_execution_events':True,
                               'observer_OFF_ON_result_bytes_equal':True})
            for cap_idx,(cap,inflight) in enumerate(CAPACITY_PROFILES):
                cell=w['cells'][list(WORKLOADS).index(workload)*3+cap_idx]
                native=cell['runs']['off' if mode=='off' else 'on_forward_first']
                native_total=native['metrics']['forward_emissions']
                native_terminal=native['metrics']['forward_terminal']
                comparisons.append({
                    'workload':workload,'mode':mode,
                    'stimulus_timestamps':ticks,
                    'fabric_slots_per_tick':cap,'max_inflight_occurrences':inflight,
                    'native_v0w_total_emissions':native_total,
                    'micro_v2d_total_emissions':micro_total,
                    'native_v0w_terminal':native_terminal,
                    'micro_v2d_terminal':micro_end,
                    'aggregate_counts_equal':native_total==micro_total and native_terminal==micro_end,
                    'native_v0w_result_sha256':native['whole_result_sha256'],
                    'native_AB_holdout_timestamps_available':False,
                    'native_spike_semantics_identical':None,
                })
    require(len(comparisons)==30 and len(micro_runs)==10,
            'incomplete workload differential')
    mismatched=[r for r in comparisons if not r['aggregate_counts_equal']]
    require(all(r['workload']=='coincident' and r['native_v0w_total_emissions']==3 and
                r['micro_v2d_total_emissions']==6 and r['native_v0w_terminal']==1 and
                r['micro_v2d_terminal']==2 for r in mismatched) and
            len(mismatched)==6 and
            sum(r['aggregate_counts_equal'] for r in comparisons)==24,
            'preexisting native holdout changed unexpectedly')
    baseline_v0w=w['cells'][0]['runs']['off']['whole_result_sha256']
    require(baseline_v0w==x['native_run_reference_matrix']['original']['off']['result_sha256'],
            'v0w baseline not tied to prior native v1x result')
    return {'schema':SCHEMA,'status':STATUS,'source_kind':SOURCE,
            'reference_v2c_sha256':sha256(cb).hexdigest(),
            'reference_v0w_sha256':sha256(wb).hexdigest(),
            'reference_v1q_sha256':sha256(qb).hexdigest(),
            'reference_v1x_sha256':sha256(xb).hexdigest(),
            'frozen_native_source_pins_rechecked_in_this_run':frozen_custody,
            'research_micro_v2a_sha256':sha_a,
            'research_micro_v2c_sha256':sha_c,
            'research_micro_v2d_sha256':sha_d,
            'historical_native_v0w_workload_cells':15,
            'historical_native_comparison_cells':30,
            'historical_native_count_equal_cells':24,
            'historical_native_count_mismatch_cells':6,
            'new_frozen_scheduler_executions':0,
            'new_research_micro_executions':20,
            'explicit_micro_input_workloads':micro_runs,
            'native_micro_comparisons':comparisons,
            'coincident_stimulus_count_contrast':{
                'native_total_emissions':3,'micro_total_emissions':6,
                'native_terminal':1,'micro_terminal':2,
                'same_external_input_timestamps':True,
                'native_aggregation_mechanism_inferred':False},
            'frozen_native_CMP_equivalence_proven':False,
            'native_scheduler_equivalence_proven':False,
            'native_BV_equivalence_proven':False,
            'native_independent_absence_certificates':0,
            'native_B_control_messages':0,'native_receiver_judgments':0,
            'operator_updates':0,'native_learning_proven':False,
            'claims_excluded':EXCLUDED}
