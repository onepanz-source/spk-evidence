"""BV v2l: pinned actor credit transaction journals over v2k resource grants."""
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
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,DerivedActorCreditProtocolV2l,
    derive_actor_credit_executor,PROTOCOL_SCHEMA,
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

SCHEMA='spk-bv-pinned-derived-actor-credit-ack-protocol/v2l'
STATUS='DERIVED_ACTOR_CREDIT_EXACTLY_ONCE_RESOURCE_CAUSAL_NATIVE_PROJECTION'
CONTRACT_STATUS='V2L_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
PREDECESSOR_SHA='774758196caeefd0d8ff629d8c4aca2d543b6e3dee8c2f2fda51eb236afe6ad4'
POLICIES=('loss','fault','overflow','cap_zero','cap_one','quota_one','tail_off')
BASELINE_KEYS=(
    'derived_resource_grants_committed','derived_inline_actor_grants',
    'derived_control_tail_grants','unconsumed_delivered_controls',
    'delivered_controls','native_original_timeline_rows',
    'new_derived_control_only_timeline_rows',
    'derived_committed_pe_service_units','derived_committed_memory_units',
    'credit_by_actor','resource_pressure',
    'within_original_native_plan_capacity','absence_certificates',
    'derived_scheduler_resource_counters_intentionally_changed',
    'frozen_original_resource_counters_changed',
    'frozen_native_actor_intake_observed','native_learning_proven',
    'native_operator_updates',
)
EXCLUSIONS=(
    'actor-credit-register-is-separate-derived-research-state-not-frozen-actor-state',
    'hash-chain-is-deterministic-audit-integrity-not-cryptographic-authentication',
    'fifo-head-of-line-policy-may-starve-a-recipient-under-credit-saturation',
    'semantic-positive-means-receiver-batch-emitted-not-universal-goodness',
    'delivery-loss-policy-refusal-and-resource-pressure-are-not-negative-evidence',
    'v2k-resources-are-derived-proxy-costs-not-frozen-native-actor-grants',
    'no-preemptive-priority-competition-with-forward-computation',
    'no-frozen-native-actor-intake-learner-weight-update-or-adaptive-source-weight',
    'no-physical-hardware-N-node-distributed-trust-or-freeze-promotion',
)


def validate_v2k(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw==canon(previous) and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2l v2k predecessor not exact signed-off canonical evidence')
    s=previous.get('integrated_admission_totals') or {}
    require(previous.get('schema')==
                'spk-bv-pinned-derived-integrated-control-resource-admission/v2k' and
            previous.get('status')==
                'DERIVED_ACTOR_CONTROL_RESOURCE_COMMITTED_NATIVE_PROJECTION_EQUAL' and
            previous.get('reference_v2j_sha256')==
                '8fd1919c0bf197e83064828f074daa533038a1f798ea6398f8e0b88b0e6ae396' and
            previous.get('full_native_projection_parity_cells')==45 and
            previous.get('derived_resource_timeline_changed_cells')==45 and
            s.get('delivered_controls')==156 and
            s.get('derived_resource_grants_committed')==156 and
            s.get('derived_inline_actor_grants')==140 and
            s.get('derived_control_tail_grants')==16 and
            s.get('unconsumed_delivered_controls')==0 and
            s.get('derived_committed_memory_units')==312 and
            previous.get('actual_derived_counter_commits_observed') is True and
            previous.get('frozen_native_actor_resource_grant_commits_observed') is False and
            previous.get('native_resource_result_full_parity_claimed') is False and
            previous.get('native_learning_proven') is False and
            previous.get('next_gate')==
                'BLOCKED_REAL_NATIVE_ACTOR_EVENT_ADMISSION_AND_SEMANTIC_CREDIT_POLICY',
            'v2l v2k predecessor drifts in source/admission/exclusion evidence')
    cells=previous.get('paired_native_matrix')
    require(type(cells) is list and len(cells)==len(RECIPES),
            'v2l requires all 15 source-backed predecessor recipes')
    for (label,recipe),row in zip(RECIPES,cells):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [mode.get('mode') for mode in row.get('modes',[])]==
                    [x[0] for x in ARMS] and
                all(mode.get('exact_native_projection') is True and
                    mode.get('forward_and_feedback_original_equal') is True and
                    len(mode.get('whole_original_native_sha256',''))==64 and
                    mode.get('integrated_actor_resource',{}).get(
                        'derived_scheduler_resource_counters_intentionally_changed')
                        is True
                    for mode in row['modes']),
                'v2l historical v2k per-cell projection contract drift')
    return True


def _controls(policy):
    credit_plan=ActorCreditPlanV2l()
    service_plan=ShadowServicePlanV2j()
    port_kw={}
    if policy=='loss':
        port_kw['accept']=lambda _record:False
    elif policy=='fault':
        def fault(_record):
            raise RuntimeError('causal actor credit transport failure')
        port_kw['accept']=fault
    elif policy=='overflow':
        port_kw['capacity']=1
    elif policy=='cap_zero':
        credit_plan=ActorCreditPlanV2l(max_abs_credit=0)
    elif policy=='cap_one':
        credit_plan=ActorCreditPlanV2l(max_abs_credit=1)
    elif policy=='quota_one':
        credit_plan=ActorCreditPlanV2l(max_actor_acks_total=1)
    elif policy=='tail_off':
        service_plan=ShadowServicePlanV2j(max_per_tick=1,max_tail_ticks=0)
    else:
        require(policy=='normal','v2l unknown bounded credit intervention')
    return ReceiverPortV2h(**port_kw),credit_plan,service_plan


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,policy='normal'):
    port,credit_plan,service_plan=_controls(policy)
    credit=DerivedActorCreditProtocolV2l(port,credit_plan,service_plan)
    observer=CallsiteObserver()
    derived,_,anchors,resource_anchors=derive_actor_credit_executor(
        source,native_executor,port,credit,observer)
    raw={}

    def projected_executor(*args,**kwargs):
        integrated=derived(*args,**kwargs)
        projection=credit.project_original_native_result(integrated)
        raw['integrated']=integrated
        raw['projection']=projection
        return projection

    projected=_arm(projected_executor,plan_type,changed,fabric,plans,
                   f'v2l-credit-{policy}',enabled,priority,digest,data)
    summary=credit.summary()
    feedback=port.summary()
    journal=credit.credit_journal()
    require(anchors==(('batch',194),('clock',125),
                      ('emission',217),('ingress',136)) and
            resource_anchors==(296,307) and
            not observer.overflow and not observer.sink_failed and
            summary['derived_actor_credit_ack_count']==
                summary['derived_resource_grants_committed']==len(journal) and
            summary['derived_resource_grants_committed']+
                summary['unconsumed_delivered_controls']==
                    summary['delivered_controls'] and
            summary['delivered_controls']==feedback['control_delivered'] and
            summary['within_original_native_plan_capacity'] and
            summary['exactly_once_derived_credit_journal'] and
            summary['strict_actor_fifo_enforced'] and
            summary['credit_bounds_held'] and
            summary['absence_certificates']==0 and
            summary['native_operator_updates']==0 and
            summary['frozen_actor_state_changed'] is False and
            summary['frozen_actor_credit_contract_proven'] is False and
            raw['integrated']['forward']==raw['projection']['forward'] and
            raw['integrated']['feedback']==raw['projection']['feedback'],
            'v2l per-actor credit transaction broke causal native projection')
    if policy=='loss':
        require(feedback['lost']==feedback['receiver_local_judgments'] and
                len(journal)==0,'v2l transported loss invented actor acknowledgment')
    if policy=='fault':
        require(feedback['fault_lost']==feedback['receiver_local_judgments'] and
                len(journal)==0,'v2l callback fault invented actor credit')
    if policy=='overflow':
        require(feedback['queue_overflow'] or feedback['mailbox_overflow'],
                'v2l bounded mailbox overflow not actually exercised')
    if policy=='cap_zero':
        require(not journal and summary['delivered_policy_blocked_pending']==
                    summary['delivered_controls'] and
                summary['new_derived_control_only_timeline_rows']==0 and
                summary['actor_credit_register']=={'A':0,'B':0,'C':0},
                'v2l zero credit cap created fake service, tail or negative credit')
    if policy=='cap_one':
        require(all(abs(v)<=1 for v in summary['actor_credit_register'].values()),
                'v2l actor credit bound leaked across actor scope')
    if policy=='quota_one':
        require(len(journal)<=1,'v2l global acknowledgment quota overspent')
    if policy=='tail_off':
        require(summary['derived_control_tail_grants']==0 and
                summary['new_derived_control_only_timeline_rows']==0,
                'v2l no-tail policy fabricated post-native service')
    return projected,summary,feedback,observer.counts(),credit.resource_timeline(),journal,raw


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2k(previous,raw)
    root=root.resolve(strict=True)
    pins=source_pins(root)
    arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    original_snapshot=snapshot(original)
    rows=[]
    totals={key:0 for key in (
        'delivered_controls','derived_resource_grants_committed',
        'derived_inline_actor_grants','derived_control_tail_grants',
        'derived_actor_credit_ack_count','unconsumed_delivered_controls',
        'derived_committed_pe_service_units',
        'derived_committed_memory_units',
        'new_derived_control_only_timeline_rows',
        'delivered_policy_blocked_pending',
        'delivered_other_unconsumed_pending')}
    caps={policy:{'ack_count':0,'delivered':0,'policy_blocked':0,
                  'unconsumed':0,'tail_rows':0} for policy in POLICIES}
    for (label,recipe),prior in zip(RECIPES,previous['paired_native_matrix']):
        changed=build_workload(case,recipe)
        data=(changed,fabric,tuple(plans))
        digest=snapshot(data)
        modes=[]
        for (mode,enabled,priority),historic in zip(ARMS,prior['modes']):
            native_box={}

            def capture_original(*args,**kwargs):
                result=native_executor(*args,**kwargs)
                native_box['result']=result
                return result

            native=_arm(capture_original,plan_type,changed,fabric,plans,
                        f'v2l-original/{label}/{mode}',enabled,priority,digest,data)
            require(native['whole_result_sha256']==
                    historic['whole_original_native_sha256'],
                    'v2l native executable diverged from signed v2k matrix')
            projected,s,port,counts,timeline,journal,outputs=_derived_arm(
                source,native_executor,plan_type,changed,fabric,plans,
                enabled,priority,digest,data)
            require(projected==native and
                    outputs['projection']==native_box['result'] and
                    counts==historic['callsite_counts'] and
                    timeline==historic['resource_commit_audit'] and
                    all(s[key]==historic['integrated_actor_resource'][key]
                        for key in BASELINE_KEYS) and
                    s['derived_actor_credit_ack_count']==
                        s['derived_resource_grants_committed'] and
                    port['source_owned_emissions']==
                        port['native_ingress_events']==
                        port['receiver_local_judgments']==
                        port['control_delivered']==
                        native['metrics']['forward_occurrences'],
                    'v2l default mode changed v2k counters/native semantics')
            for key in totals:
                totals[key]+=s[key]
            variants={}
            for policy in POLICIES:
                p,t,feedback,variant_counts,_,acks,variant_outputs=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,plans,
                    enabled,priority,digest,data,policy=policy)
                require(p==native and
                        variant_outputs['projection']==native_box['result'] and
                        variant_counts==counts and
                        feedback['absence_certificates']==0,
                        'v2l credit policy intervention changed original native result')
                caps[policy]['ack_count']+=len(acks)
                caps[policy]['delivered']+=t['delivered_controls']
                caps[policy]['policy_blocked']+=t['delivered_policy_blocked_pending']
                caps[policy]['unconsumed']+=t['unconsumed_delivered_controls']
                caps[policy]['tail_rows']+=t['new_derived_control_only_timeline_rows']
                variants[policy]={
                    'ack_count':len(acks),
                    'delivered':t['delivered_controls'],
                    'policy_blocked':t['delivered_policy_blocked_pending'],
                    'unconsumed':t['unconsumed_delivered_controls'],
                    'tail_rows':t['new_derived_control_only_timeline_rows'],
                    'credit_by_actor':t['actor_credit_register'],
                    'loss':feedback['lost'],'fault':feedback['fault_lost'],
                    'queue_overflow':feedback['queue_overflow'],
                    'mailbox_overflow':feedback['mailbox_overflow'],
                }
            modes.append({
                'mode':mode,'whole_original_native_sha256':native['whole_result_sha256'],
                'exact_native_full_projection':True,
                'v2k_derived_resource_ledger_equal':True,
                'actor_credit_summary':s,
                'actor_credit_journal':journal,
                'callsite_counts':counts,
                'credit_policy_interventions':variants,
            })
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot(original)==original_snapshot,
                'v2l changed native fixture between recipe variants')
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    rejected=replace(case,nodes=tuple(
        replace(node,instructions=block) if node.node_id=='B' else node
        for node in case.nodes))
    negative_data=(rejected,fabric,tuple(plans))
    negative_digest=snapshot(negative_data)
    native_negative=_arm(native_executor,plan_type,rejected,fabric,plans,
        'v2l-negative-original',True,'forward-first',negative_digest,negative_data)
    projected,summary,port,_,_,journal,outputs=_derived_arm(
        source,native_executor,plan_type,rejected,fabric,plans,
        True,'forward-first',negative_digest,negative_data)
    require(projected==native_negative and
            port['negative_judgments']==2 and
            len(journal)==summary['derived_actor_credit_ack_count']==2 and
            [ack['response'] for ack in journal]==[-1,-1] and
            summary['actor_credit_register']['A']==-2 and
            not summary['native_learning_proven'] and
            outputs['integrated']['forward']==outputs['projection']['forward'],
            'v2l negative native causal evidence or actor credit journal drift')
    # A one-point credit bound must withhold the second genuine negative
    # without silently transforming it into an absence judgment.
    capped,cap,_,_,_,ack_cap,_=_derived_arm(
        source,native_executor,plan_type,rejected,fabric,plans,
        True,'forward-first',negative_digest,negative_data,policy='cap_one')
    require(capped==native_negative and
            len(ack_cap)==1 and cap['actor_credit_register']['A']==-1 and
            cap['delivered_policy_blocked_pending']==1 and
            cap['absence_certificates']==0,
            'v2l negative-B credit cap did not preserve withheld evidence')
    require(source_pins(root)==pins and
            read_pinned_sources(root)==arch and
            read_pinned_source(root)==source and
            snapshot(original)==original_snapshot,
            'v2l source/corpus changed during native replay')
    require(totals['delivered_controls']==156 and
            totals['derived_resource_grants_committed']==156 and
            totals['derived_actor_credit_ack_count']==156 and
            totals['derived_inline_actor_grants']==140 and
            totals['derived_control_tail_grants']==16 and
            totals['delivered_policy_blocked_pending']==0 and
            caps['cap_zero']['ack_count']==0 and
            caps['cap_zero']['policy_blocked']==156 and
            caps['cap_zero']['tail_rows']==0 and
            caps['quota_one']['ack_count']==45 and
            caps['cap_one']['ack_count']<156 and
            caps['tail_off']['ack_count']<156,
            'v2l normal or bounded negative policy-discrimination totals drift')
    return {
        'paired_native_matrix':rows,'actor_credit_totals':totals,
        'intervention_totals':caps,
        'negative_fixture':{
            'real_negative_judgments':2,
            'normal_actor_A_credit':summary['actor_credit_register']['A'],
            'normal_acked_negative_receipts':len(journal),
            'cap_one_actor_A_credit':cap['actor_credit_register']['A'],
            'cap_one_delivered_unapplied_judgments':
                cap['delivered_policy_blocked_pending'],
        },
        'native_original_runs':46,'derived_normal_runs':46,
        'derived_intervention_runs':45*len(POLICIES)+1,
        'full_native_projection_cells':45,
        'prior_v2k_derived_resource_parity_cells':45,
        'source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2k(previous,raw)
    require(result is None or
            (result['source_custody'] and
             result['native_original_runs']==46 and
             result['derived_normal_runs']==46 and
             result['derived_intervention_runs']==316 and
             result['full_native_projection_cells']==45 and
             result['prior_v2k_derived_resource_parity_cells']==45),
            'v2l actor credit protocol matrix not fully admitted')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('PINNED_DERIVED_ACTOR_CREDIT_JOURNAL_WITH_NATIVE_PROJECTION'
                       if result else 'V2K_PREDECESSOR_ONLY_CONTRACT'),
        'reference_v2k_sha256':sha256(raw).hexdigest(),
        'frozen_native_source_pins_rechecked_in_this_run':bool(result),
        'new_native_original_runs':result['native_original_runs'] if result else 0,
        'new_derived_credit_normal_runs':result['derived_normal_runs'] if result else 0,
        'new_derived_credit_intervention_runs':
            result['derived_intervention_runs'] if result else 0,
        'full_native_projection_parity_cells':
            result['full_native_projection_cells'] if result else 0,
        'v2k_integrated_derived_resource_parity_cells':
            result['prior_v2k_derived_resource_parity_cells'] if result else 0,
        'actor_credit_totals':result['actor_credit_totals'] if result else None,
        'intervention_totals':result['intervention_totals'] if result else None,
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'negative_native_fixture':result['negative_fixture'] if result else None,
        'real_frozen_native_actor_acknowledgments_proven':False,
        'real_frozen_native_actor_credit_contract_proven':False,
        'derived_actor_credit_journal_not_native_learning':True,
        'frozen_native_operator_updates':0,
        'native_learning_proven':False,
        'next_gate':'BLOCKED_NATIVE_ACTOR_EVENT_PRIORITY_AND_CREDIT_CONSUMPTION_CONTRACT',
        'claims_excluded':list(EXCLUSIONS),
    }
