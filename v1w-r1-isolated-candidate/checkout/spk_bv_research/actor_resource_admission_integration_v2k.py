"""BV v2k: commit to derived resource counters, project exact native result."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ShadowServicePlanV2j,
)
from spk_backvalidation_v2.derived_actor_admission_v2k import (
    DerivedActorAdmissionV2k,derive_resource_admission_executor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require,snapshot,source_pins,runtime_modules_bound,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES,build_workload,
)
from spk_bv_research.link_pressure_v0u import ARMS,_arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-pinned-derived-integrated-control-resource-admission/v2k'
STATUS='DERIVED_ACTOR_CONTROL_RESOURCE_COMMITTED_NATIVE_PROJECTION_EQUAL'
CONTRACT_STATUS='V2K_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
PREDECESSOR_SHA='8fd1919c0bf197e83064828f074daa533038a1f798ea6398f8e0b88b0e6ae396'
POLICIES=('loss','fault','overflow','tail_off','tight')

EXCLUSIONS=(
    'counter-commit-happens-in-pinned-derived-executor-not-frozen-native-scheduler',
    'post-forward-admission-cannot-yet-serve-as-a-priority-contention-policy',
    'derived-resource-timeline-is-intentionally-not-whole-native-report-parity',
    'projection-restores-native-report-exactly-but-does-not-prove-preemptive-policy',
    'post-native-control-only-ticks-are-new-research-time-not-frozen-runtime',
    'one-PE-and-two-memory-units-are-chosen-proxy-costs-not-hardware-theorems',
    'recipient-identity-is-from-pinned-in-process-admission-not-cryptographic',
    'no-actor-learning-state-or-operator-updates-or-semantic-weight-adaptation',
    'no-frozen-contract-edit-N-node-hardware-timing-or-cold-promotion-claim',
)


def validate_v2j(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw==canon(previous) and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2k predecessor must be exact signed-off canonical v2j')
    totals=previous.get('shadow_service_totals') or {}
    require(previous.get('schema')=='spk-bv-derived-bounded-actor-control-service/v2j' and
            previous.get('status')==
                'DERIVED_SHADOW_RESOURCE_CHARGED_CONTROL_SERVICE_NO_NATIVE_GRANT' and
            previous.get('full_native_result_parity_cells')==45 and
            totals.get('delivered_controls')==156 and
            totals.get('shadow_control_service_grants')==156 and
            totals.get('native_slack_actor_service_grants')==140 and
            totals.get('post_native_shadow_tail_grants')==16 and
            previous.get('frozen_native_actor_control_intake_observed') is False and
            previous.get('native_actor_service_resource_grants_proven') is False and
            previous.get('native_learning_proven') is False and
            previous.get('next_gate')==
                'BLOCKED_NATIVE_ACTOR_CONTROL_SERVICE_ADMISSION_AND_CREDIT_CONTRACT',
            'v2j predecessor makes false native or missing-resource claims')
    cells=previous.get('paired_native_matrix')
    require(type(cells) is list and len(cells)==len(RECIPES),
            'v2k v2j matrix predecessor missing')
    for (label,recipe),entry in zip(RECIPES,cells):
        require(entry.get('label')==label and
                entry.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in entry.get('modes',[])]==
                    [x[0] for x in ARMS] and
                all(m.get('full_native_result_parity') is True and
                    type(m.get('whole_result_sha256')) is str and
                    len(m['whole_result_sha256'])==64
                    for m in entry['modes']),
                'v2j paired historical native result drift')
    return True


def _policy(port,policy):
    if policy=='tail_off':
        return ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=0)
    if policy=='tight':
        return ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=32)
    return ShadowServicePlanV2j()


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data, *,policy='normal'):
    require(policy=='normal' or policy in POLICIES,
            'v2k unsupported integrated admission pressure/fault policy')
    if policy=='loss':
        port=ReceiverPortV2h(accept=lambda _r:False)
    elif policy=='fault':
        def fail(_r):
            raise RuntimeError('control-service transport fault')
        port=ReceiverPortV2h(accept=fail)
    elif policy=='overflow':
        port=ReceiverPortV2h(capacity=1)
    else:
        port=ReceiverPortV2h()
    admission=DerivedActorAdmissionV2k(port,_policy(port,policy))
    observer=CallsiteObserver()
    derived,_,anchors,resource_anchors=derive_resource_admission_executor(
        source,native_executor,port,admission,observer)
    raw={}

    def native_projection_executor(*args,**kwargs):
        changed_result=derived(*args,**kwargs)
        native_projection=admission.project_original_native_result(changed_result)
        raw['integrated']=changed_result
        raw['projection']=native_projection
        return native_projection

    projected=_arm(native_projection_executor,plan_type,changed,fabric,plans,
                   'v2k-integrated-'+policy,enabled,priority,digest,data)
    s=admission.summary()
    port_summary=port.summary()
    require(resource_anchors==(296,307) and
            anchors==(('batch',194),('clock',125),
                      ('emission',217),('ingress',136)) and
            not observer.overflow and not observer.sink_failed and
            s['delivered_controls']==port_summary['control_delivered'] and
            s['derived_resource_grants_committed']+
            s['unconsumed_delivered_controls']==s['delivered_controls'] and
            s['within_original_native_plan_capacity'] and
            s['derived_committed_memory_units']==2*s['derived_committed_pe_service_units'] and
            s['derived_scheduler_resource_counters_intentionally_changed'] and
            not s['frozen_original_resource_counters_changed'] and
            not s['frozen_native_actor_intake_observed'] and
            s['native_operator_updates']==0 and
            s['absence_certificates']==0,
            'v2k missing derived counter or native-projection custody')
    before=raw['projection']
    after=raw['integrated']
    resource_diff=(after['resources']['timeline']!=
                   before['resources']['timeline'])
    require(after['forward']==before['forward'] and
            after['feedback']==before['feedback'] and
            resource_diff == (s['derived_resource_grants_committed']>0),
            'v2k integrated derived grant did not change only resource accounting')
    if policy=='normal':
        require(port_summary['source_owned_emissions']==
                port_summary['native_ingress_events']==
                port_summary['receiver_local_judgments']==
                port_summary['control_delivered']==
                projected['metrics']['forward_occurrences'],
                'v2k actor-local causal source/receiver proof drift')
    if policy=='loss':
        require(port_summary['lost']==port_summary['receiver_local_judgments'] and
                s['derived_resource_grants_committed']==0,
                'v2k loss created synthetic resource or credit grant')
    if policy=='fault':
        require(port_summary['fault_lost']==port_summary['receiver_local_judgments'] and
                s['derived_resource_grants_committed']==0,
                'v2k feedback callback fault fabricated credit')
    if policy=='overflow':
        require(port_summary['queue_overflow'] or
                port_summary['mailbox_overflow'],
                'v2k overflow intervention not exercised')
    if policy=='tail_off':
        require(s['new_derived_control_only_timeline_rows']==0 and
                s['derived_control_tail_grants']==0,
                'v2k no-tail intervention illegally served post-native')
    return projected,s,port_summary,observer.counts(),admission.resource_timeline(),raw


def experiment(previous,raw, *,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2j(previous,raw)
    root=root.resolve(strict=True)
    source_before=source_pins(root)
    arch_before=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    unchanged=snapshot(original)
    totals={key:0 for key in (
        'derived_resource_grants_committed','derived_inline_actor_grants',
        'derived_control_tail_grants','unconsumed_delivered_controls',
        'delivered_controls','derived_committed_pe_service_units',
        'derived_committed_memory_units','new_derived_control_only_timeline_rows')}
    rows=[]
    resource_changed_cells=0
    for (label,recipe),prior in zip(RECIPES,previous['paired_native_matrix']):
        changed=build_workload(case,recipe)
        data=(changed,fabric,tuple(plans))
        digest=snapshot(data)
        modes=[]
        for (mode,enabled,priority),historic in zip(ARMS,prior['modes']):
            captured={}

            def original_and_capture(*args,**kwargs):
                outcome=native_executor(*args,**kwargs)
                captured['native']=outcome
                return outcome

            native=_arm(original_and_capture,plan_type,changed,fabric,plans,
                        f'v2k-native/{label}/{mode}',enabled,priority,digest,data)
            require(native['whole_result_sha256']==historic['whole_result_sha256'],
                    'v2k historical frozen whole result differs from v2j')
            projected,s,transport,counts,timeline,outputs=_derived_arm(
                source,native_executor,plan_type,changed,fabric,plans,
                enabled,priority,digest,data)
            require(projected==native and
                    outputs['projection']==captured['native'] and
                    counts==historic['callsite_counts'] and
                    outputs['integrated']['forward']==captured['native']['forward'] and
                    outputs['integrated']['feedback']==captured['native']['feedback'],
                    'v2k original native full projection or forward/BV parity failed')
            resource_changed_cells+=int(
                outputs['integrated']['resources']['timeline']!=
                captured['native']['resources']['timeline'])
            for key in totals:
                totals[key]+=s[key]
            variants={}
            for policy in POLICIES:
                p,t,feedback,other_counts,_,raw_variant=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,plans,
                    enabled,priority,digest,data,policy=policy)
                require(p==native and other_counts==counts and
                        raw_variant['projection']==captured['native'],
                        'v2k pressure/loss/overflow failed native projection')
                variants[policy]={
                    'committed':t['derived_resource_grants_committed'],
                    'tail_grants':t['derived_control_tail_grants'],
                    'unconsumed':t['unconsumed_delivered_controls'],
                    'lost':feedback['lost'],
                    'fault_lost':feedback['fault_lost'],
                    'overflow':feedback['queue_overflow'] or feedback['mailbox_overflow'],
                    'pressure':t['resource_pressure'],
                }
            modes.append({
                'mode':mode,'exact_native_projection':True,
                'forward_and_feedback_original_equal':True,
                'derived_resource_counter_modified':
                    s['derived_resource_grants_committed']>0,
                'whole_original_native_sha256':native['whole_result_sha256'],
                'integrated_actor_resource':s,'resource_commit_audit':timeline,
                'callsite_counts':counts,'interventions':variants,
            })
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot(original)==unchanged,
                'v2k changed original immutable native fixture')
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    blocked=replace(case,nodes=tuple(
        replace(node,instructions=block) if node.node_id=='B' else node
        for node in case.nodes))
    negative_data=(blocked,fabric,tuple(plans))
    negative_digest=snapshot(negative_data)
    orig_negative=_arm(native_executor,plan_type,blocked,fabric,plans,
                       'v2k-negative-original',True,'forward-first',
                       negative_digest,negative_data)
    proj_negative,neg,port_negative,_,_,_= _derived_arm(
        source,native_executor,plan_type,blocked,fabric,plans,
        True,'forward-first',negative_digest,negative_data)
    require(proj_negative==orig_negative and
            port_negative['negative_judgments']==2 and
            neg['derived_resource_grants_committed']==2 and
            neg['credit_by_actor']['A']==-2 and
            neg['unconsumed_delivered_controls']==0,
            'v2k native-backed negative receiver credit projection failed')
    require(source_pins(root)==source_before and
            read_pinned_sources(root)==arch_before and
            read_pinned_source(root)==source and
            snapshot(original)==unchanged,
            'v2k altered frozen source pins or fixture')
    return {
        'paired_native_matrix':rows,'integrated_admission_totals':totals,
        'integrated_resource_timeline_changed_cells':resource_changed_cells,
        'negative_fixture':{
            'real_negative_judgments':2,
            'derived_integrated_actor_credit':neg['credit_by_actor'],
            'derived_resource_grants':neg['derived_resource_grants_committed'],
        },
        'native_original_runs':46,
        'derived_normal_runs':46,
        'derived_intervention_runs':45*len(POLICIES),
        'original_native_full_projection_cells':45,
        'native_source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2j(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['native_original_runs']==46 and
             result['derived_normal_runs']==46 and
             result['derived_intervention_runs']==225 and
             result['original_native_full_projection_cells']==45),
            'v2k native projected/derived-integrated result not admissible')
    totals=result['integrated_admission_totals'] if result else None
    return {
        'schema':SCHEMA,
        'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('PINNED_DERIVED_COUNTER_COMMIT_WITH_EXACT_NATIVE_PROJECTION'
                       if result else 'PREDECESSOR_ONLY_CONTRACT'),
        'reference_v2j_sha256':sha256(raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(result),
        'new_native_original_runs':result['native_original_runs'] if result else 0,
        'new_derived_integrated_normal_runs':result['derived_normal_runs'] if result else 0,
        'new_derived_integrated_intervention_runs':result['derived_intervention_runs'] if result else 0,
        'full_native_projection_parity_cells':result['original_native_full_projection_cells'] if result else 0,
        'derived_resource_timeline_changed_cells':
            result['integrated_resource_timeline_changed_cells'] if result else 0,
        'integrated_admission_totals':totals,
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'negative_native_fixture':result['negative_fixture'] if result else None,
        'actual_derived_counter_commits_observed':bool(result and
            totals['derived_resource_grants_committed']>0),
        'frozen_native_actor_resource_grant_commits_observed':False,
        'native_resource_result_full_parity_claimed':False,
        'original_forward_and_feedback_exact_parity':bool(result),
        'frozen_native_operator_updates':0,
        'native_learning_proven':False,
        'next_gate':'BLOCKED_REAL_NATIVE_ACTOR_EVENT_ADMISSION_AND_SEMANTIC_CREDIT_POLICY',
        'claims_excluded':list(EXCLUSIONS),
    }
