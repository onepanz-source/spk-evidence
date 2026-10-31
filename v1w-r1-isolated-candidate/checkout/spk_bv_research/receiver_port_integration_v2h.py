"""BV v2h native-derived receiver judgments: 15x3 historical replay gate.

Each new report compares actual pinned native execution with an AST-derived
function that records real source emission, ingress and recipient computation.
It does NOT claim native actor-state feedback intake, causal learning or a
cryptographically authenticated producer.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, EXPECTED_CALLS, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import (
    ReceiverPortV2h, derive_receiver_executor, PORT_VERSION,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, snapshot, source_pins, runtime_modules_bound,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA = 'spk-bv-derived-native-actor-semantic-receiver-port/v2h'
STATUS = 'DERIVED_ACTOR_CAUSAL_FEEDBACK_DELIVERED_NO_FROZEN_ACTOR_INTAKE'
CONTRACT_STATUS = 'V2H_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
EXCLUSIONS = (
    'source-identity-is-derived-from-pinned-native-callsite-not-network-cryptographic-authentication',
    'receiver-judgment-is-research-selected-output-criterion-not-algebra-derived-quality',
    'actor-scoped-in-process-mailbox-is-not-frozen-neuron-state-or-operator-intake',
    'post-native-drain-may-deliver-after-last-native-tick',
    'lost-or-overflowed-feedback-is-not-a-negative-or-absence-certificate',
    'finite-full-native-result-parity-is-not-all-input-real-time-noninterference',
    'no-native-learning-credit-rollback-promotion-or-operator-update',
    'no-frozen-source-modification-no-N-node-or-hardware-claim',
)


def validate_v2g(report, raw):
    require(type(report) is dict and type(raw) is bytes and raw == canon(report),
            'v2g report must be canonical and byte identical')
    require(report.get('schema') == 'spk-bv-derived-frozen-native-scheduler-callsite-parity/v2g' and
            report.get('status') == 'DERIVED_NATIVE_CALLSITE_PARITY_NO_NATIVE_RECEIVER_PORT' and
            report.get('source_kind') == 'DERIVED_EXECUTABLE_PINNED_NATIVE_CALLSITES' and
            report.get('frozen_native_source_pins_rechecked_in_this_run') is True and
            report.get('full_native_report_parity_cells') == 45 and
            report.get('new_frozen_original_runs') == 45 and
            report.get('new_in_memory_derived_executor_runs') == 45 and
            report.get('new_derived_fault_and_overflow_runs') == 90 and
            report.get('derived_scheduler_is_frozen_scheduler') is False and
            report.get('native_receiver_endogenous_judgments') == 0 and
            report.get('native_B_receiver_control_messages') == 0 and
            report.get('native_learner_updates') == 0 and
            report.get('native_learning_proven') is False,
            'untrusted v2g provenance or false-native claims')
    expected = [{'callee':n,'line':line} for n,line in EXPECTED_CALLS]
    require(report.get('verified_callsite_inventory') == expected,
            'v2g native callsite roster changed')
    cells = report.get('paired_native_matrix')
    require(type(cells) is list and len(cells) == len(RECIPES),
            'v2g workload matrix missing')
    for (name,recipe), row in zip(RECIPES, cells):
        require(row.get('label') == name and
                row.get('recipe') == [list(x) for x in recipe] and
                type(row.get('controls')) is list and
                [x.get('mode') for x in row['controls']] == [x[0] for x in ARMS] and
                all(x.get('same_full_native_report') is True and
                    x.get('callsite_failure') is False and
                    x.get('source_owned_receiver_feedback') is False and
                    x.get('sink_fault_native_result_equal') is True and
                    x.get('overflow_native_result_equal') is True and
                    x.get('sink_fault_evidence_complete') is False and
                    x.get('overflow_evidence_complete') is False and
                    type(x.get('whole_result_sha256')) is str and
                    len(x['whole_result_sha256']) == 64
                    for x in row['controls']),
                'v2g matrix mismatch or incorrectly promoted control')
    return True


def _derived_arm(source, native_executor, plan_type, changed, fabric,
                 plans, enabled, priority, input_sha, data, *,
                 policy='normal'):
    if policy == 'loss':
        port = ReceiverPortV2h(accept=lambda _: False)
        observer = CallsiteObserver()
    elif policy == 'fault':
        def fails(_):
            raise RuntimeError('receiver research transport fault')
        def bad_sink(_):
            raise RuntimeError('research metadata observer unavailable')
        port = ReceiverPortV2h(accept=fails)
        observer = CallsiteObserver(sink=bad_sink)
    elif policy == 'overflow':
        port = ReceiverPortV2h(capacity=1)
        observer = CallsiteObserver(capacity=1)
    else:
        require(policy == 'normal', 'unknown receiver fault intervention')
        port = ReceiverPortV2h()
        observer = CallsiteObserver()
    derived,callsite_roster,anchor_roster = derive_receiver_executor(
        source, native_executor, port, observer)
    run = _arm(derived,plan_type,changed,fabric,plans,
               f'v2h-derived-{policy}',enabled,priority,input_sha,data)
    port.close()
    summary = port.summary()
    if policy == 'normal':
        require(summary['port_closed'] and
                not observer.overflow and not observer.sink_failed and
                observer.offered == len(observer.records) and
                all(x.returned for x in observer.records),
                'native callsite metadata not complete')
        require(summary['source_owned_emissions'] ==
                run['metrics']['forward_occurrences'] and
                summary['native_ingress_events'] ==
                run['metrics']['forward_occurrences'] and
                summary['receiver_local_judgments'] ==
                run['metrics']['forward_occurrences'] and
                summary['control_delivered'] == summary['receiver_local_judgments'] and
                not summary['queue_overflow'] and not summary['mailbox_overflow'] and
                summary['lost'] == 0 and summary['fault_lost'] == 0 and
                summary['negative_judgments'] == 0 and
                summary['absence_certificates'] == 0 and
                not summary['frozen_actor_state_receives_feedback'],
                'derived native actor-semantic feedback trace inconsistent')
        require(observer.counts()['_admit'] == 1 and
                observer.counts()['_admit_plan'] == 1,
                'derived native admission hooks not invoked')
    elif policy == 'loss':
        require(summary['lost'] == summary['receiver_local_judgments'] and
                summary['control_delivered'] == 0,
                'receiver feedback loss not isolated')
    elif policy == 'fault':
        require(summary['fault_lost'] == summary['receiver_local_judgments'] and
                summary['control_delivered'] == 0 and observer.sink_failed,
                'receiver port or observer fault not isolated')
    else:
        require(summary['queue_overflow'] or summary['mailbox_overflow'],
                'receiver control overflow not exercised')
        require(observer.overflow and observer.offered > 1,
                'observer overflow not exercised')
    return run, summary, observer.counts(), anchor_roster


def experiment(v2g,v2g_raw, *,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2g(v2g,v2g_raw)
    root=root.resolve(strict=True)
    pins_before=source_pins(root)
    architecture_custody=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    require(type(plans) is tuple and len(plans)==4,
            'bad historical native fixture shape')
    unchanged=snapshot(original)
    results=[]
    totals={'source_owned_emissions':0,'native_ingress_events':0,
            'receiver_local_judgments':0,'control_delivered':0,
            'positive_judgments':0,'negative_judgments':0,'post_native_deliveries':0}
    for (label,recipe),prior in zip(RECIPES,v2g['paired_native_matrix']):
        changed=build_workload(case,recipe)
        data=(changed,fabric,tuple(plans))
        digest=snapshot(data)
        modes=[]
        for (mode,enabled,priority),historical in zip(ARMS,prior['controls']):
            native=_arm(native_executor,plan_type,changed,fabric,plans,
                        f'v2h-native/{label}/{mode}',enabled,priority,digest,data)
            require(native['whole_result_sha256']==historical['whole_result_sha256'],
                    'native historical v2g result drift')
            derived,summary,counts,anchors=_derived_arm(
                source,native_executor,plan_type,changed,fabric,plans,
                enabled,priority,digest,data)
            require(derived==native and counts==historical['callsite_counts'],
                    'v2h semantic hooks altered native outcome or v2g callsites')
            for key in totals:
                totals[key]+=summary[key]
            faults={}
            for intervention in ('loss','fault','overflow'):
                stressed,s,_,_=_derived_arm(source,native_executor,plan_type,
                    changed,fabric,plans,enabled,priority,digest,data,policy=intervention)
                require(stressed==native,
                        'v2h receiver loss/fault/overflow interfered with frozen computation')
                faults[intervention]={
                    'delivered':s['control_delivered'],
                    'lost':s['lost'],'fault_lost':s['fault_lost'],
                    'queue_overflow':s['queue_overflow'],
                    'mailbox_overflow':s['mailbox_overflow'],
                }
            modes.append({'mode':mode,'full_native_parity':True,
                          'whole_result_sha256':native['whole_result_sha256'],
                          'callsite_counts':counts,
                          'actor_port':summary,'fault_controls':faults})
        results.append({'label':label,'recipe':[list(x) for x in recipe],
                        'modes':modes})
        require(snapshot(original)==unchanged, 'native fixture modified by v2h')
    require(source_pins(root)==pins_before and
            read_pinned_sources(root)==architecture_custody and
            read_pinned_source(root)==source,
            'frozen native source changed during derived actor port gate')
    # Predeclared negative actor-local judgment: B receives genuine A spikes,
    # computes a batch with no output, and issues negative controls. This is
    # NOT inferred from the absence of C events or from observer counts.
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    blocked_case=replace(case,nodes=tuple(
        replace(node,instructions=block) if node.node_id=='B' else node
        for node in case.nodes))
    blocked_data=(blocked_case,fabric,tuple(plans))
    blocked_sha=snapshot(blocked_data)
    negative_native=_arm(native_executor,plan_type,blocked_case,fabric,plans,
                         'v2h-negative-native-B',True,'forward-first',
                         blocked_sha,blocked_data)
    negative_derived,negative_port,_,_=_derived_arm_negative(
        source,native_executor,plan_type,blocked_case,fabric,plans,blocked_sha,
        blocked_data)
    require(negative_native==negative_derived and
            negative_port['negative_judgments']==2 and
            negative_port['positive_judgments']==0 and
            negative_port['control_delivered']==2 and
            negative_port['credit_by_sender']=={'A':-2} and
            negative_port['absence_certificates']==0,
            'endogenous receiver negative verdict or forward parity failed')
    require(snapshot(original)==unchanged and source_pins(root)==pins_before,
            'negative native experiment altered frozen fixture/source')
    return {'rows':results,'totals':totals,
            'new_native_original_runs':45,
            'new_derived_normal_runs':45,
            'new_derived_fault_runs':135,
            'negative_native_and_derived_runs':2,
            'negative_real_actor_judgments':negative_port['negative_judgments'],
            'source_custody':True}


def _derived_arm_negative(source,native_executor,plan_type,changed,fabric,
                          plans,input_sha,data):
    port=ReceiverPortV2h()
    monitor=CallsiteObserver()
    clone,_,_=derive_receiver_executor(source,native_executor,port,monitor)
    result=_arm(clone,plan_type,changed,fabric,plans,'v2h-negative-derived-B',
                True,'forward-first',input_sha,data)
    port.close()
    require(not monitor.overflow and not monitor.sink_failed and
            port.summary()['source_owned_emissions']==2 and
            port.summary()['native_ingress_events']==2,
            'negative B proof lacks observed source and ingress')
    return result,port.summary(),monitor.counts(),None


def build_report(v2g,v2g_raw,result=None):
    validate_v2g(v2g,v2g_raw)
    require(result is None or (
        result['source_custody'] and
        result['new_native_original_runs']==45 and
        result['new_derived_normal_runs']==45 and
        result['new_derived_fault_runs']==135 and
        result['negative_native_and_derived_runs']==2 and
        result['negative_real_actor_judgments']==2),
        'v2h native execution result not admissible')
    return {
        'schema':SCHEMA,
        'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('PINNED_DERIVED_RUNTIME_ACTOR_SEMANTIC_EVENTS'
                       if result else 'PREDECESSOR_ONLY_CONTRACT'),
        'reference_v2g_sha256':sha256(v2g_raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(result),
        'new_native_original_runs':result['new_native_original_runs'] if result else 0,
        'new_derived_normal_runs':result['new_derived_normal_runs'] if result else 0,
        'new_derived_fault_runs':result['new_derived_fault_runs'] if result else 0,
        'negative_native_and_derived_runs':result['negative_native_and_derived_runs'] if result else 0,
        'negative_real_actor_judgments':result['negative_real_actor_judgments'] if result else 0,
        'full_native_result_parity_cells':45 if result else 0,
        'actor_semantic_totals':result['totals'] if result else None,
        'paired_native_matrix':result['rows'] if result else None,
        'derived_actor_control_port_observed':bool(result),
        'research_receiver_local_judgment':bool(result),
        'research_sender_scoped_mailbox_delivery':bool(result),
        'frozen_native_actor_receives_research_control':False,
        'cryptographic_spike_origin_proven':False,
        'native_operator_updates':0,
        'native_learning_proven':False,
        'next_gate':'BLOCKED_FROZEN_ACTOR_INTAKE_AND_LEARNING_CONTRACT',
        'claims_excluded':list(EXCLUSIONS),
    }
