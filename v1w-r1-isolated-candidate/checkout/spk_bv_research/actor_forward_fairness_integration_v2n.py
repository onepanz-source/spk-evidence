"""BV v2n: signed v2m successor, bounded opportunity and liveness counterexamples."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_actor_fairness_v2n import (
    FairnessPlanV2n,DerivedActorFairnessV2n,derive_fair_executor,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import (
    DerivedActorPriorityV2m,derive_priority_executor,
)
from spk_bv_research.actor_priority_contention_integration_v2m import (
    _payload,REGIMES,
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

SCHEMA='spk-bv-pinned-derived-forward-actor-fairness-opportunity/v2n'
STATUS='DERIVED_FORWARD_PROTECTED_OPPORTUNITY_CAUSAL_ACTOR_CREDIT_BOUNDED'
CONTRACT_STATUS='V2N_SIGNED_PREDECESSOR_ONLY_NO_FAIRNESS_EXECUTION'
PREDECESSOR_SHA='97f023c54198e05fcf8dc63f3602ec955acad0ea83a34544be7ef6f5e2311177'
WINDOWS=(('always_protect',0),('one_actor_turn',1),('legacy_window_16',16))
NULLS=('loss','fault','cap_zero')
EXCLUSIONS=(
    'forward-protection-is-a-derived-budget-opportunity-not-guaranteed-batch-execution',
    'finite-forward-opportunity-window-is-not-universal-liveness-or-deadline-proof',
    'no-credit-feedback-admission-into-frozen-native-actor-state-or-learning',
    'derived-priority-reservation-can-alter-bv-link-and-causal-schedule',
    'resource-only-projection-cannot-remove-timing-effects-of-reordering',
    'unconsumed-or-not-yet-due-judgments-are-not-negative-credit-evidence',
    'observer-delivery-is-not-distributed-cryptographic-authentication',
    'synthetic-control-service-units-are-not-physical-hardware-energy-costs',
    'only-source-pinned-three-actor-corpus-no-universal-starvation-free-theorem',
    'frozen-native-event-policy-no-operator-update-and-no-cold-promotion',
)


def validate_v2m(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw==canon(previous) and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2n requires exact signed-off canonical v2m predecessor')
    require(previous.get('schema')==
            'spk-bv-pinned-derived-actor-forward-resource-priority/v2m' and
            previous.get('status')==
            'DERIVED_ACTOR_FIRST_CAUSAL_FORWARD_TIMING_CONTENTION_FUNCTIONAL_PARITY' and
            previous.get('reference_v2l_sha256')==
                'b77f257adc6cb6c888e6cef44e67d39e54bf328ed6e9ee4d434eb7eea3bdf3d7' and
            previous.get('new_original_native_runs')==91 and
            previous.get('new_derived_actor_first_runs')==91 and
            previous.get('new_derived_forward_first_runs')==91 and
            previous.get('new_derived_causal_null_runs')==135 and
            previous.get('source_pins_rechecked_in_this_run') is True and
            previous.get('frozen_native_actor_service_or_learning_proven') is False and
            previous.get('native_forward_timing_full_parity_under_actor_first_claimed') is False and
            previous.get('native_operator_updates')==0 and
            previous.get('next_gate')==
                'BLOCKED_FROZEN_NATIVE_ACTOR_PRIORITY_ADMISSION_FAIRNESS_AND_CREDIT_CONSUMPTION',
            'v2n v2m research claim/status or frozen-native exclusions changed')
    totals=previous.get('priority_contention_totals') or {}
    tight=totals.get('contended_capacity') or {}
    require(tight.get('source_backed_cells')==45 and
            tight.get('actor_first_changed_forward_timing')==45 and
            tight.get('actor_first_pre_forward_grants')==141 and
            tight.get('actor_first_ready_forward_PE_blocked')==162 and
            tight.get('actor_first_acks')==156 and
            tight.get('forward_first_full_original_native_parity')==45 and
            tight.get('actor_first_terminal_payload_parity')==45 and
            tight.get('actor_first_final_state_parity')==45 and
            totals.get('original_capacity',{}).get('source_backed_cells')==45,
            'v2n v2m recorded causal budget and forward benchmark changed')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2n missing signed-off v2m native corpus')
    for (label,recipe),row in zip(RECIPES,rows):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in row.get('modes',[])]==
                    [a[0] for a in ARMS],
                'v2n signed v2m workload/admission mode reorder')
        for mode in row['modes']:
            for regime,capacity in REGIMES:
                old=mode.get('capacities',{}).get(regime) or {}
                require(old.get('capacity')==capacity and
                        old.get('forward_first_exact_native_projection') is True and
                        old.get('actor_first_final_states_same') is True and
                        old.get('actor_first_terminal_payload_same') is True and
                        old.get('actor_first_forward_event_and_batch_counts_same') is True and
                        len(old.get('original_native_sha256',''))==64 and
                        len(old.get('actor_first_priority_probes',[]))>0,
                        'v2n v2m per-capacity source/functional custody drift')
    return True


def _fair_arm(source,native_executor,plan_type,changed,fabric,plans,enabled,
              priority,digest,data,*,window,policy='normal'):
    port_opts={}
    credit_plan=ActorCreditPlanV2l()
    if policy=='loss':
        port_opts['accept']=lambda _item:False
    elif policy=='fault':
        def fault(_item):
            raise RuntimeError('intentional bounded receiver callback fault')
        port_opts['accept']=fault
    elif policy=='cap_zero':
        credit_plan=ActorCreditPlanV2l(max_abs_credit=0)
    else:
        require(policy=='normal','v2n unsupported causal-null intervention')
    port=ReceiverPortV2h(**port_opts)
    service=DerivedActorFairnessV2n(port,
        fairness_plan=FairnessPlanV2n(window),credit_plan=credit_plan)
    observer=CallsiteObserver()
    derived,_,anchors,resource=derive_fair_executor(
        source,native_executor,port,service,observer)
    result={}

    def run(*args,**kwargs):
        result['integrated']=derived(*args,**kwargs)
        result['projected']=service.project_original_native_result(
            result['integrated'])
        return result['projected']

    projection=_arm(run,plan_type,changed,fabric,plans,
                    f'v2n-window-{window}-{policy}',enabled,priority,digest,data)
    summary=service.summary()
    probes=service.fairness_probes()
    result['priority_probes']=service.priority_probes()
    journal=service.credit_journal()
    feedback=port.summary()
    require(anchors==(('batch',194),('clock',125),
                      ('emission',217),('ingress',136)) and
            resource==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            summary['derived_actor_credit_ack_count']==len(journal)==
                summary['derived_resource_grants_committed'] and
            summary['derived_resource_grants_committed']+
                summary['unconsumed_delivered_controls']==
                    summary['delivered_controls']==feedback['control_delivered'] and
            summary['within_original_native_plan_capacity'] and
            summary['absence_certificates']==0 and
            summary['native_operator_updates']==0 and
            summary['frozen_native_event_priority_policy_modified'] is False and
            summary['frozen_actor_state_changed'] is False and
            summary['frozen_actor_credit_contract_proven'] is False and
            result['integrated']['forward']==result['projected']['forward'] and
            len(probes)==summary['native_original_timeline_rows'] and
            summary['max_observed_competing_actor_streak']<=window,
            'v2n source-backed causal resource/forward fairness custody drift')
    if policy!='normal':
        require(not journal and
                summary['pre_forward_actor_grants']==0 and
                summary['derived_resource_grants_committed']==0 and
                summary['absence_certificates']==0,
                'v2n causal-null fabricated actor credit or pre-forward service')
    return projection,summary,feedback,observer.counts(),probes,journal,result


def _horizon_counterexample(source,case,fabric,plans,native_executor,plan_type):
    from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected
    low=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
         plans[2],plans[3])
    bound=plan_type(max_ticks=11)
    native=native_executor(case,fabric,*low,bound)
    require(len(native['resources']['timeline'])==11,
            'v2n strict native horizon changed from signed-off fixture')
    ff_port=ReceiverPortV2h()
    ff_service=DerivedActorPriorityV2m(ff_port,priority='forward-first')
    forward_first,_,_,_=derive_priority_executor(
        source,native_executor,ff_port,ff_service,CallsiteObserver())
    ff_result=forward_first(case,fabric,*low,bound)
    require(ff_service.project_original_native_result(ff_result)==native,
            'v2n horizon control forward-first lost exact native projection')
    rejections={}
    for name,window in (('always_protect',0),('legacy_window_16',16)):
        port=ReceiverPortV2h()
        fair=DerivedActorFairnessV2n(port,fairness_plan=FairnessPlanV2n(window))
        derived,_,_,_=derive_fair_executor(
            source,native_executor,port,fair,CallsiteObserver())
        try:
            derived(case,fabric,*low,bound)
        except LiveBVRejected as exc:
            require(str(exc)=='bounded live logical horizon exceeded',
                    'v2n horizon rejected for unclassified causal bound')
            rejections[name]='BOUNDED_HORIZON_REJECTED_NO_CERTIFICATE'
        else:
            require(False,'v2n horizon counterexample unexpectedly completed')
    return {
        'global_PE_slots_per_tick':1,
        'native_horizon_max_ticks':11,
        'frozen_native_completed':True,
        'forward_first_derived_completed_and_exact_native_projection':True,
        'derived_fairness_results':rejections,
        'bound_rejection_is_not_silence_or_negative_judgment':True,
        'execution_attempts':4,
    }


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2m(previous,raw)
    root=root.resolve(strict=True)
    prior_source=source_pins(root)
    prior_arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    case_snapshot=snapshot(original)
    matrix=[]
    totals={regime:{name:{
        'cells':0,'full_original_native_projection_parity':0,
        'forward_terminal_timestamp_parity':0,
        'forward_functional_payload_parity':0,
        'forward_timing_changed':0,
        'protected_forward_opportunity_ticks':0,
        'protected_with_actual_forward_progress':0,
        'protected_without_forward_progress':0,
        'ready_forward_PE_blocked':0,
        'pre_forward_actor_grants':0,
        'actor_credit_acks':0,
        'ack_wait_total_ticks':0,
        'ack_wait_max_ticks':0,
        'forward_last_terminal_delay_sum':0,
        'forward_last_terminal_delay_max':0,
    } for name,_ in WINDOWS} for regime,_ in REGIMES}
    null_totals={key:0 for key in NULLS}
    old_reference_parity=0
    for index,(label,recipe) in enumerate(RECIPES):
        changed=build_workload(case,recipe)
        modes=[]
        for mode_index,(mode,enabled,priority) in enumerate(ARMS):
            cells={}
            for regime,capacity in REGIMES:
                existing=previous['paired_native_matrix'][index]['modes'][
                    mode_index]['capacities'][regime]
                changed_plans=(plans[0],replace(plans[1],
                    fabric_slots_per_tick=capacity),plans[2],plans[3])
                data=(changed,fabric,tuple(changed_plans))
                digest=snapshot(data)
                native_result={}

                def capture_native(*args,**kwargs):
                    native_result['raw']=native_executor(*args,**kwargs)
                    return native_result['raw']

                native=_arm(capture_native,plan_type,changed,fabric,
                    changed_plans,f'v2n-native-{regime}',enabled,priority,
                    digest,data)
                require(native['whole_result_sha256']==
                        existing['original_native_sha256'],
                        'v2n original scheduler differs from signed-off v2m native')
                frozen=native_result['raw']
                experiments={}
                for name,window in WINDOWS:
                    projected,s,port,c,probes,acks,raw_result=_fair_arm(
                        source,native_executor,plan_type,changed,fabric,
                        changed_plans,enabled,priority,digest,data,window=window)
                    forward=raw_result['integrated']['forward']
                    old_forward=frozen['forward']
                    functional=_payload(forward)==_payload(old_forward)
                    terminal_equal=sorted(x['timestamp'] for x in
                        forward['terminal'])==sorted(x['timestamp'] for x in
                        old_forward['terminal'])
                    require(functional and c.get('_admit')==1 and
                            c.get('_admit_plan')==1 and
                            s['max_consecutive_actor_ticks_with_ready_forward']==window and
                            s['protected_forward_pe_slots']==1 and
                            s['max_observed_competing_actor_streak']<=window and
                            all((not row['protected_forward_opportunity'] or
                                 row['actor_pregrants']<=capacity-1)
                                for row in probes) and
                            len(acks)==s['derived_actor_credit_ack_count'] and
                            not port['absence_certificates'],
                            'v2n functional, time-window or actor ack invariant broken')
                    if name=='legacy_window_16':
                        require(s['protected_forward_opportunity_ticks']==0 and
                                s['pre_forward_actor_grants']==existing[
                                    'actor_first_summary']['pre_forward_actor_grants'] and
                                [x['timestamp'] for x in forward['terminal']]==
                                    existing['actor_first_terminal_ticks'] and
                                acks==existing['actor_first_credit_journal'] and
                                raw_result['priority_probes']==
                                    existing['actor_first_priority_probes'] and
                                projected['whole_result_sha256']==
                                    snapshot(raw_result['projected']),
                                'v2n long window differs from signed-off v2m actor-first')
                        old_reference_parity+=1
                    agg=totals[regime][name]
                    agg['cells']+=1
                    agg['full_original_native_projection_parity']+=int(
                        raw_result['projected']==frozen)
                    agg['forward_terminal_timestamp_parity']+=int(terminal_equal)
                    agg['forward_functional_payload_parity']+=int(functional)
                    agg['forward_timing_changed']+=int(forward!=old_forward)
                    agg['protected_forward_opportunity_ticks']+=s[
                        'protected_forward_opportunity_ticks']
                    agg['protected_with_actual_forward_progress']+=s[
                        'protected_opportunities_with_actual_forward_progress']
                    agg['protected_without_forward_progress']+=s[
                        'protected_opportunities_without_forward_progress']
                    agg['ready_forward_PE_blocked']+=s[
                        'ready_forward_batches_blocked_by_pre_grants']
                    agg['pre_forward_actor_grants']+=s['pre_forward_actor_grants']
                    agg['actor_credit_acks']+=len(acks)
                    wait=[ack['serviced_tick']-ack['due_tick'] for ack in acks]
                    require(all(n>=0 for n in wait),
                            'v2n ack serviced before source-caused due time')
                    agg['ack_wait_total_ticks']+=sum(wait)
                    agg['ack_wait_max_ticks']=max(agg['ack_wait_max_ticks'],
                                                 max(wait,default=0))
                    base_last=max((x['timestamp'] for x in old_forward['terminal']),
                                  default=0)
                    last=max((x['timestamp'] for x in forward['terminal']),default=0)
                    delta=last-base_last
                    agg['forward_last_terminal_delay_sum']+=delta
                    agg['forward_last_terminal_delay_max']=max(
                        agg['forward_last_terminal_delay_max'],delta)
                    experiments[name]={
                        'window':window,
                        'exact_full_native_cost_projection':raw_result['projected']==frozen,
                        'forward_functional_payload_same':functional,
                        'terminal_timestamp_parity':terminal_equal,
                        'forward_timing_changed':forward!=old_forward,
                        'forward_terminal_ticks':[x['timestamp'] for x in
                                                  forward['terminal']],
                        'native_terminal_ticks':[x['timestamp'] for x in
                                                 old_forward['terminal']],
                        'forward_last_terminal_delay_ticks':delta,
                        'summary':s,
                        'fairness_probes':probes,
                        'actor_credit_journal':acks,
                        'actor_ack_wait_ticks':wait,
                        'callsite_counts':c,
                    }
                if regime=='contended_capacity':
                    null={}
                    for policy in NULLS:
                        proj,s,port,c,probes,acks,data_result=_fair_arm(
                            source,native_executor,plan_type,changed,fabric,
                            changed_plans,enabled,priority,digest,data,
                            window=1,policy=policy)
                        require(proj==native and
                                data_result['projected']==frozen and
                                not acks and
                                s['pre_forward_actor_grants']==0,
                                'v2n causal null fails exact independent native parity')
                        null_totals[policy]+=1
                        null[policy]={
                            'whole_native_result_equal':True,
                            'control_delivered':s['delivered_controls'],
                            'actor_acks':len(acks),
                            'transport_lost':port['lost'],
                            'callback_fault_lost':port['fault_lost'],
                        }
                    experiments['causal_nulls_window_one']=null
                cells[regime]={
                    'capacity':capacity,
                    'signed_v2m_native_sha256':existing['original_native_sha256'],
                    'fairness_windows':experiments,
                }
            modes.append({'mode':mode,'capacities':cells})
        matrix.append({'label':label,'recipe':[list(x) for x in recipe],
                       'modes':modes})
        require(snapshot(original)==case_snapshot,
                'v2n source native fixture mutated while evaluating fairness')
    require(old_reference_parity==90 and
            all(v==45 for v in null_totals.values()) and
            all(row['cells']==45 and
                row['forward_functional_payload_parity']==45
                for regime in totals.values() for row in regime.values()) and
            totals['contended_capacity']['legacy_window_16'][
                'ready_forward_PE_blocked']==162 and
            totals['contended_capacity']['legacy_window_16'][
                'forward_timing_changed']==45 and
            totals['contended_capacity']['legacy_window_16'][
                'pre_forward_actor_grants']==141,
            'v2n full fairness matrix or signed v2m unbounded benchmark missing')
    witness=_horizon_counterexample(
        source,case,fabric,plans,native_executor,plan_type)
    require(source_pins(root)==prior_source and
            read_pinned_sources(root)==prior_arch and
            read_pinned_source(root)==source and
            snapshot(original)==case_snapshot,
            'v2n source/fabric/pinned frozen scheduler changed across replay')
    return {
        'paired_native_matrix':matrix,
        'fairness_window_totals':totals,
        'causal_null_full_native_parity':null_totals,
        'legacy_v2m_actor_first_reference_cells':old_reference_parity,
        'bounded_horizon_witness':witness,
        'native_original_runs':90,
        'derived_fairness_window_runs':270,
        'derived_causal_null_runs':135,
        'source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2m(previous,raw)
    require(result is None or
            (result['source_custody'] and
             result['native_original_runs']==90 and
             result['derived_fairness_window_runs']==270 and
             result['derived_causal_null_runs']==135 and
             result['legacy_v2m_actor_first_reference_cells']==90 and
             result['bounded_horizon_witness']['execution_attempts']==4 and
             len(result['bounded_horizon_witness']['derived_fairness_results'])==2 and
             all(v==45 for v in result['causal_null_full_native_parity'].values())),
            'v2n incomplete source-backed native/fairness/null matrix')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('SOURCE_PINNED_DERIVED_FORWARD_OPPORTUNITY_FAIRNESS'
                       if result else 'SIGNED_V2M_PREDECESSOR_ONLY'),
        'reference_v2m_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked_in_this_run':bool(result),
        'new_original_native_runs':result['native_original_runs'] if result else 0,
        'new_derived_fairness_window_runs':result['derived_fairness_window_runs'] if result else 0,
        'new_derived_causal_null_runs':result['derived_causal_null_runs'] if result else 0,
        'legacy_v2m_actor_first_reference_cells':(
            result['legacy_v2m_actor_first_reference_cells'] if result else 0),
        'bounded_horizon_witness':result['bounded_horizon_witness'] if result else None,
        'new_bounded_horizon_execution_attempts':4 if result else 0,
        'fairness_window_totals':result['fairness_window_totals'] if result else None,
        'causal_null_full_native_parity':(
            result['causal_null_full_native_parity'] if result else None),
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'universal_forward_liveness_proven':False,
        'protected_forward_budget_opportunity_real':bool(result),
        'native_actor_credit_admission_proven':False,
        'frozen_native_actor_priority_changed':False,
        'native_operator_updates':0,
        'next_gate':
            'BLOCKED_FROZEN_NATIVE_ACTOR_FAIRNESS_LIVENESS_ADMISSION_AND_CREDIT_CONSUMPTION',
        'claims_excluded':list(EXCLUSIONS),
    }
