"""BV v2j native-parity and bounded shadow control-service experiment."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver, read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_control_service_v2j import (
    ActorControlServiceV2j, ShadowServicePlanV2j,
    derive_shadow_service_executor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import (
    require, snapshot, source_pins, runtime_modules_bound,
)
from spk_bv_research.coincident_admission_discrimination_v2e import (
    RECIPES, build_workload,
)
from spk_bv_research.link_pressure_v0u import ARMS, _arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA = 'spk-bv-derived-bounded-actor-control-service/v2j'
STATUS = 'DERIVED_SHADOW_RESOURCE_CHARGED_CONTROL_SERVICE_NO_NATIVE_GRANT'
CONTRACT_STATUS = 'V2J_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
PREDECESSOR_SHA = 'b09c0ceb778070f8dafa8913945ba952c497411b5cf9063ff6d8f9f0a7ff3010'
POLICIES = ('loss','overflow','tail_off','tight')

EXCLUSIONS = (
    'shadow-services-are-in-process-derived-executions-not-native-PE-intake',
    'residual-resource-accounting-is-shadow-ledger-not-frozen-grant-commit',
    'post-native-tail-is-separately-clocked-research-control-not-native-time',
    'one-PE-service-two-local-memory-units-per-receipt-is-chosen-cost-proxy',
    'unprocessed-or-lost-messages-never-imply-negative-judgments-or-absence',
    'source-ownership-is-pinned-native-in-process-not-cryptographic-authentication',
    'finite-parity-does-not-prove-timing-independence-N-node-or-hardware',
    'no-frozen-actor-state-or-learning-update-no-contract-promotion',
)


def validate_v2i(previous, raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw == canon(previous) and sha256(raw).hexdigest() == PREDECESSOR_SHA,
            'v2j predecessor must be exact signed-off canonical v2i')
    require(previous.get('schema') ==
            'spk-bv-derived-native-actor-batch-control-intake/v2i' and
            previous.get('status') ==
            'DERIVED_COMMITTED_ACTOR_BATCH_INTAKE_NO_FROZEN_ACTOR_CONTRACT' and
            previous.get('full_native_result_parity_cells') == 45 and
            previous.get('actor_intake_totals',{}).get('derived_actor_batch_receipts') == 52 and
            previous.get('actor_intake_totals',{}).get('unconsumed_delivered_controls') == 104 and
            previous.get('actor_intake_totals',{}).get('delivered_controls') == 156 and
            previous.get('frozen_native_actor_intake_observed') is False and
            previous.get('native_actor_service_resources_accounted') is False and
            previous.get('native_learning_proven') is False and
            previous.get('next_gate') ==
            'BLOCKED_FROZEN_ACTOR_INTAKE_CONTRACT_AND_RESOURCE_SERVICE',
            'v2i predecessor false-native or missing evidence')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2i matrix predecessor missing')
    for (label,recipe),entry in zip(RECIPES,rows):
        require(entry.get('label')==label and
                entry.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in entry.get('modes',[])]==[x[0] for x in ARMS] and
                all(m.get('native_result_parity') is True and
                    type(m.get('whole_result_sha256')) is str and
                    len(m['whole_result_sha256'])==64
                    for m in entry['modes']),
                'v2i predecessor paired native matrix drift')
    return True


def _derived_arm(source, original, plan_type, changed, fabric, plans,
                 enabled, priority, digest, data, *, policy='normal'):
    require(policy=='normal' or policy in POLICIES,
            'v2j unknown actor service fault policy')
    if policy=='loss':
        port=ReceiverPortV2h(accept=lambda _record:False)
    elif policy=='overflow':
        port=ReceiverPortV2h(capacity=1)
    else:
        port=ReceiverPortV2h()
    if policy=='tail_off':
        service=ActorControlServiceV2j(port,ShadowServicePlanV2j(
            max_per_tick=1,per_actor_per_tick=1,max_tail_ticks=0))
    elif policy=='tight':
        service=ActorControlServiceV2j(port,ShadowServicePlanV2j(
            max_per_tick=1,per_actor_per_tick=1,max_tail_ticks=32))
    else:
        service=ActorControlServiceV2j(port)
    monitor=CallsiteObserver()
    derived,_,anchors,shadow_anchor=derive_shadow_service_executor(
        source,original,port,service,monitor)
    captured={}

    def capture_native_output(*args,**kwargs):
        outcome=derived(*args,**kwargs)
        require('resources' in outcome and
                type(outcome['resources'].get('timeline')) is list and
                bool(outcome['resources']['timeline']),
                'v2j derived native result lacks completed resource timeline')
        captured['timeline']=outcome['resources']['timeline']
        return outcome

    run=_arm(capture_native_output,plan_type,changed,fabric,plans,
             'v2j-derived-'+policy,enabled,priority,digest,data)
    service.close_after_native(captured['timeline'][-1]['tick'])
    require(service.audit_native_timeline(captured['timeline']),
            'v2j after-tick resource hook not anchored to native report')
    s=service.summary()
    port_summary=port.summary()
    require(shadow_anchor==296 and
            anchors == (('batch',194),('clock',125),
                        ('emission',217),('ingress',136)) and
            not monitor.overflow and not monitor.sink_failed and
            s['delivered_controls']==port_summary['control_delivered'] and
            s['shadow_control_service_grants']+
            s['unconsumed_delivered_controls']==s['delivered_controls'] and
            s['all_shadow_grants_within_native_plan_envelope'] and
            s['shadow_memory_units']==2*s['shadow_pe_service_units'] and
            s['native_tick_resource_rows']==len(captured['timeline']) and
            not s['frozen_native_resource_counters_mutated'] and
            not s['frozen_actor_intake_observed'] and
            s['native_operator_updates']==0 and
            s['absence_certificates']==0,
            'v2j invalid shadow actor service accounting/provenance')
    if policy=='normal':
        require(s['admitted_actors']==['A','B','C'] and
                port_summary['source_owned_emissions']==
                port_summary['native_ingress_events']==
                port_summary['receiver_local_judgments']==
                port_summary['control_delivered']==
                run['metrics']['forward_occurrences'],
                'v2j normal pinned actor feedback event drift')
    if policy=='loss':
        require(port_summary['lost']==port_summary['receiver_local_judgments'] and
                s['shadow_control_service_grants']==0 and
                s['delivered_controls']==0,
                'v2j loss fabricated control service or credit')
    if policy=='overflow':
        require(port_summary['queue_overflow'] or
                port_summary['mailbox_overflow'],
                'v2j overflow scenario did not exercise bounded transport')
    if policy=='tail_off':
        require(s['post_native_shadow_tail_grants']==0 and s['tail_ticks']==0,
                'v2j no-tail intervention continued after native scheduler')
    return run,s,port_summary,monitor.counts(),service.resource_timeline()


def experiment(previous,raw, *,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2i(previous,raw)
    root=root.resolve(strict=True)
    source_before=source_pins(root)
    arch_before=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    unchanged=snapshot(original)
    totals={key:0 for key in (
        'shadow_control_service_grants','native_slack_actor_service_grants',
        'post_native_shadow_tail_grants','unconsumed_delivered_controls',
        'delivered_controls','shadow_pe_service_units','shadow_memory_units',
        'tail_ticks')}
    cells=[]
    for (label,recipe),prior in zip(RECIPES,previous['paired_native_matrix']):
        changed=build_workload(case,recipe)
        data=(changed,fabric,tuple(plans))
        digest=snapshot(data)
        modes=[]
        for (mode,enabled,priority),historical in zip(ARMS,prior['modes']):
            native=_arm(native_executor,plan_type,changed,fabric,plans,
                        f'v2j-native/{label}/{mode}',enabled,priority,digest,data)
            require(native['whole_result_sha256']==historical['whole_result_sha256'],
                    'v2j native historical v2i result mismatch')
            derived,s,transport,counts,timeline=_derived_arm(
                source,native_executor,plan_type,changed,fabric,plans,
                enabled,priority,digest,data)
            require(derived==native and
                    counts.get('_admit')==1 and
                    counts.get('_admit_plan')==1 and
                    set(counts).issubset({'_admit','_admit_plan','offer_feedback'}),
                'v2j derived shadow hook altered native full report')
            for key in totals:
                totals[key]+=s[key]
            stress={}
            for policy in POLICIES:
                other,t,feedback,other_counts,_= _derived_arm(
                    source,native_executor,plan_type,changed,fabric,plans,
                    enabled,priority,digest,data,policy=policy)
                require(other==native and other_counts==counts,
                        'v2j loss/overflow/tail restriction changed native result')
                stress[policy]={
                    'shadow_grants':t['shadow_control_service_grants'],
                    'tail_grants':t['post_native_shadow_tail_grants'],
                    'unconsumed':t['unconsumed_delivered_controls'],
                    'lost':feedback['lost'],
                    'queue_overflow':feedback['queue_overflow'],
                    'mailbox_overflow':feedback['mailbox_overflow'],
                    'shadow_pressure':t['shadow_pressure'],
                }
            modes.append({
                'mode':mode,'full_native_result_parity':True,
                'whole_result_sha256':native['whole_result_sha256'],
                'shadow_service':s,'shadow_tick_audit':timeline,
                'callsite_counts':counts,'interventions':stress,
            })
        cells.append({'label':label,'recipe':[list(x) for x in recipe],
                      'modes':modes})
        require(snapshot(original)==unchanged,'v2j mutated original native fixture')
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    negative=replace(case,nodes=tuple(
        replace(node,instructions=block) if node.node_id=='B' else node
        for node in case.nodes))
    negative_data=(negative,fabric,tuple(plans))
    negative_digest=snapshot(negative_data)
    native_negative=_arm(native_executor,plan_type,negative,fabric,plans,
                         'v2j-negative-native-B',True,'forward-first',
                         negative_digest,negative_data)
    derived_negative,negative_service,negative_port,_,_= _derived_arm(
        source,native_executor,plan_type,negative,fabric,plans,
        True,'forward-first',negative_digest,negative_data)
    require(native_negative==derived_negative and
            negative_port['negative_judgments']==2 and
            negative_port['credit_by_sender']=={'A':-2} and
            negative_service['delivered_controls']==2 and
            negative_service['credit_by_actor']['A']<=0 and
            negative_service['absence_certificates']==0,
            'v2j native receiver negative credit claim unsupported')
    require(source_pins(root)==source_before and
            read_pinned_sources(root)==arch_before and
            read_pinned_source(root)==source and
            snapshot(original)==unchanged,
            'v2j changed frozen source, contract pins or fixture')
    return {
        'paired_native_matrix':cells,'service_totals':totals,
        'negative_fixture':{
            'delivered_negative_judgments':2,
            'shadow_service_grants':negative_service['shadow_control_service_grants'],
            'actor_credit':negative_service['credit_by_actor'],
            'unconsumed':negative_service['unconsumed_delivered_controls'],
        },
        'new_original_native_runs':46,
        'new_derived_normal_runs':46,
        'new_derived_intervention_runs':45*len(POLICIES),
        'native_full_result_parity_cells':45,
        'native_source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2i(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['native_full_result_parity_cells']==45 and
             result['new_original_native_runs']==46 and
             result['new_derived_normal_runs']==46 and
             result['new_derived_intervention_runs']==180),
            'v2j resource-charge native replay not admissible')
    totals=result['service_totals'] if result else None
    return {
        'schema':SCHEMA,
        'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('PINNED_DERIVED_SHADOW_ACTOR_CONTROL_SERVICE'
                       if result else 'PREDECESSOR_ONLY_CONTRACT'),
        'reference_v2i_sha256':sha256(raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(result),
        'new_original_native_runs':result['new_original_native_runs'] if result else 0,
        'new_derived_normal_runs':result['new_derived_normal_runs'] if result else 0,
        'new_derived_intervention_runs':result['new_derived_intervention_runs'] if result else 0,
        'full_native_result_parity_cells':result['native_full_result_parity_cells'] if result else 0,
        'shadow_service_totals':totals,
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'negative_native_fixture':result['negative_fixture'] if result else None,
        'shadow_cost_per_control':{'pe_service_units':1,
                                   'local_memory_units':2,
                                   'memory_domains':{'O':1,'E':1}},
        'derived_actor_independent_control_service_observed':bool(result and
            totals['shadow_control_service_grants']>0),
        'all_shadow_reservations_within_native_plan_envelope':bool(result),
        'frozen_native_actor_control_intake_observed':False,
        'frozen_native_resource_ledger_modified':False,
        'native_actor_service_resource_grants_proven':False,
        'native_learner_updates':0,
        'native_learning_proven':False,
        'next_gate':'BLOCKED_NATIVE_ACTOR_CONTROL_SERVICE_ADMISSION_AND_CREDIT_CONTRACT',
        'claims_excluded':list(EXCLUSIONS),
    }
