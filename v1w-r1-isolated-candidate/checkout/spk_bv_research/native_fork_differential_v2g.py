"""90 paired native/fork executions over predeclared 15x3 v2e matrix.

This checks observational parity of the *existing frozen computation path*
under new, separately versioned call-site metadata instrumentation. It is not
an event/feedback delivery to recipient B, no new native learner is introduced.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    derive_executor, CallsiteObserver, read_pinned_source, EXPECTED_CALLS)
from spk_bv_research.off_on_v0t import require, snapshot, source_pins, runtime_modules_bound
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-derived-frozen-native-scheduler-callsite-parity/v2g'
STATUS='DERIVED_NATIVE_CALLSITE_PARITY_NO_NATIVE_RECEIVER_PORT'
OFFLINE='V2G_CONTRACT_VALID_NATIVE_FORK_EXECUTION_PENDING'
EXCLUSIONS=(
 'in-memory-derived-scheduler-is-not-frozen-source-changed',
 'callsite-metadata-is-not-a-semantic-spike-identity-or-native-sender-authority',
 'offer_feedback-invocation-is-not-actor-local-judgment-or-B-receipt',
 'forward-result-parity-is-bounded-not-universal-real-time-noninterference',
 'callback-to-research-logger-is-not-native-control-delivery',
 'no-independent-coverage-or-cryptographic-provenance-or-absence-proof',
 'no-native-operator-update-rollback-causal-credit-or-learning',
 'no-source-modification-or-architecture-contract-promotion',
)


def validate_v2f(v2f,raw,v2e_raw):
    require(type(v2f) is dict and raw==canon(v2f) and
            v2f.get('schema')=='spk-bv-batched-source-owned-feedback-vertical-slice/v2f' and
            v2f.get('status')=='RESEARCH_TICK_BATCH_AND_ACTOR_LOCAL_FEEDBACK_NATIVE_INTEGRATION_BLOCKED' and
            v2f.get('reference_v2e_sha256')==sha256(v2e_raw).hexdigest() and
            v2f.get('native_projection_cells_checked')==45 and
            v2f.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            v2f.get('source_owned_research_micro_executions')==65 and
            v2f.get('research_control_messages_delivered_in_new_executor')==52 and
            v2f.get('native_receiver_B_control_messages')==0 and
            v2f.get('native_learning_proven') is False,
            'invalid v2f provenance and research-native boundary')
    return True


def validate_v2e(v2e,raw):
    require(type(v2e) is dict and raw==canon(v2e) and
            v2e.get('schema')=='spk-bv-frozen-native-coincident-admission-discrimination/v2e' and
            v2e.get('status')=='SOURCE_BOUND_NATIVE_ADMISSION_MATRIX_MEASURED_CAUSE_UNRESOLVED' and
            v2e.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            v2e.get('new_frozen_scheduler_executions')==45 and
            v2e.get('full_native_v0w_anchor_replay_count')==12 and
            len(v2e.get('native_matrix',[]))==15 and
            [x['label'] for x in v2e['native_matrix']]==[x for x,_ in RECIPES],
            'invalid native v2e ancestor')
    for (label,recipe),row in zip(RECIPES,v2e['native_matrix']):
        require(row.get('recipe_template_index_and_tick')==[list(x) for x in recipe] and
                set(row.get('runs',{}))=={'off','on_forward_first','on_feedback_first'},
                'v2e native workload tamper')
    return True


def experiment(v2f,v2f_raw,v2e,v2e_raw, *,root:Path, fixture_fn,
               native_executor, plan_type):
    validate_v2f(v2f,v2f_raw,v2e_raw)
    validate_v2e(v2e,v2e_raw)
    root=root.resolve(strict=True)
    pins_before=source_pins(root)
    architecture_custody=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    frozen_bytes=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    require(type(plans) is tuple and len(plans)==4,
            'unexpected frozen fixture plans')
    baseline=snapshot(original)
    rows=[]
    total_calls=Counter()
    stress_runs=0
    for (label,recipe),prior in zip(RECIPES,v2e['native_matrix']):
        changed=build_workload(case,recipe)
        data=(changed,fabric,tuple(plans))
        data_sha=snapshot(data)
        require(data_sha==prior['shared_cell_input_sha256'],
                'native fixture differs from pinned v2e matrix')
        cell=[]
        for mode,enabled,priority in ARMS:
            native=_arm(native_executor,plan_type,changed,fabric,plans,
                        f'v2g-frozen/{label}/{mode}',enabled,priority,data_sha,data)
            require(native==prior['runs'][mode],
                    'frozen baseline differs from v2e historical full result')
            monitor=CallsiteObserver()
            derived,calls=derive_executor(frozen_bytes,native_executor,monitor)
            forked=_arm(derived,plan_type,changed,fabric,plans,
                        f'v2g-derived/{label}/{mode}',enabled,priority,data_sha,data)
            require(forked==native,'in-memory derived scheduler altered the native result')
            require(not monitor.overflow and not monitor.sink_failed and
                    monitor.offered==len(monitor.records) and
                    all(x.returned for x in monitor.records),
                    'call-site observation incomplete or failed')
            measured=monitor.counts()
            require(measured['_admit']>=1 and measured['_admit_plan']>=1,
                    'native derived function never visited expected admission boundary')
            total_calls.update(measured)
            # Fault isolation on the SAME derived frozen computation. These
            # incomplete observers must never become evidence of complete
            # coverage, even though the native forward/BV result still agrees.
            def broken_sink(_):
                raise RuntimeError('independent research sink unavailable')
            bad_sink=CallsiteObserver(sink=broken_sink)
            faulted,_=derive_executor(frozen_bytes,native_executor,bad_sink)
            faulted_report=_arm(faulted,plan_type,changed,fabric,plans,
                        f'v2g-sink-fault/{label}/{mode}',enabled,priority,data_sha,data)
            require(faulted_report==native and bad_sink.sink_failed,
                    'observer sink fault interfered with native outcome or not detected')
            saturated=CallsiteObserver(capacity=1)
            overflowed,_=derive_executor(frozen_bytes,native_executor,saturated)
            overflow_report=_arm(overflowed,plan_type,changed,fabric,plans,
                        f'v2g-overflow/{label}/{mode}',enabled,priority,data_sha,data)
            require(overflow_report==native and saturated.overflow and
                    len(saturated.records)==1 and saturated.offered>1,
                    'observer overflow interfered with native outcome or not detected')
            stress_runs+=2
            cell.append({'mode':mode,'same_full_native_report':True,
                        'whole_result_sha256':native['whole_result_sha256'],
                        'callsite_counts':measured,'observed_calls':monitor.offered,
                        'callsite_failure':False,'source_owned_receiver_feedback':False,
                        'sink_fault_native_result_equal':True,
                        'overflow_native_result_equal':True,
                        'sink_fault_evidence_complete':False,
                        'overflow_evidence_complete':False})
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'controls':cell})
        require(snapshot(original)==baseline,'native fixture mutated')
    require(len(rows)==15 and sum(len(x['controls']) for x in rows)==45,
            'not all frozen/derived native cells executed')
    require(source_pins(root)==pins_before and
            read_pinned_sources(root)==architecture_custody and
            read_pinned_source(root)==frozen_bytes,
            'frozen source changed during native fork experiment')
    return {'rows':rows,'total_calls':dict(sorted(total_calls.items())),
            'source_custody':True,'native_original_runs':45,'derived_runs':45,
            'derived_stress_runs':stress_runs,
            'source_audited_callsites':[{'callee':c,'line':line} for c,line in EXPECTED_CALLS]}


def build_report(v2f,v2f_raw,v2e,v2e_raw, results=None):
    validate_v2f(v2f,v2f_raw,v2e_raw)
    validate_v2e(v2e,v2e_raw)
    require(results is None or (results['source_custody'] and
            results['native_original_runs']==45 and results['derived_runs']==45 and
            results['derived_stress_runs']==90),
            'v2g native execution result unverified')
    return {
        'schema':SCHEMA,'status':STATUS if results else OFFLINE,
        'source_kind':'DERIVED_EXECUTABLE_PINNED_NATIVE_CALLSITES' if results else 'PREDECESSOR_ONLY_CONTRACT',
        'reference_v2f_sha256':sha256(v2f_raw).hexdigest(),
        'reference_v2e_sha256':sha256(v2e_raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(results),
        'new_frozen_original_runs':results['native_original_runs'] if results else 0,
        'new_in_memory_derived_executor_runs':results['derived_runs'] if results else 0,
        'new_derived_fault_and_overflow_runs':results['derived_stress_runs'] if results else 0,
        'full_native_report_parity_cells':45 if results else 0,
        'callsite_counts':results['total_calls'] if results else None,
        'verified_callsite_inventory':results['source_audited_callsites'] if results else None,
        'paired_native_matrix':results['rows'] if results else None,
        'derived_executor_has_runtime_invoked_metadata_port':bool(results),
        'derived_scheduler_is_frozen_scheduler':False,
        'native_B_receiver_control_messages':0,
        'native_producer_authenticated_semantic_spikes':0,
        'native_receiver_endogenous_judgments':0,
        'native_learner_updates':0,'native_learning_proven':False,
        'native_receiver_port_and_causal_credit_GATE':'BLOCKED_NO_ACTOR_DELIVERY_OR_SEMANTIC_SOURCE_PROOF',
        'claims_excluded':list(EXCLUSIONS),
    }
