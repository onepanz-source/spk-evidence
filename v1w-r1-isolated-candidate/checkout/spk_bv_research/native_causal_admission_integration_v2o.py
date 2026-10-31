"""BV v2o: signed v2n succession, native-causal guard and paired ablations."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import CallsiteObserver,read_pinned_source
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import (
    CausalAdmissionPlanV2o,DerivedCausalAdmissionV2o,derive_causal_executor,
)
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected
from spk_bv_research.actor_priority_contention_integration_v2m import _payload,REGIMES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import require,snapshot,source_pins,runtime_modules_bound
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES,build_workload
from spk_bv_research.link_pressure_v0u import ARMS,_arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-pinned-native-causal-ready-actor-admission/v2o'
STATUS='DERIVED_NATIVE_CAUSAL_READY_VETO_EXACT_FULL_PARITY_AND_BOUND_WITNESS'
CONTRACT_STATUS='V2O_SIGNED_V2N_PREDECESSOR_ONLY_NO_NATIVE_CONTRACT'
PREDECESSOR_SHA='1fbb75ad2ff7f8a9f0124b94bd72e7dac1d4f559e23a07b4d65e95981e162459'
MODES=(('strict_native_causal',True,True),('forward_only',True,False),
       ('feedback_only',False,True),('actor_first_null_guard',False,False))
NULLS=('loss','fault','cap_zero')
EXCLUSIONS=(
    'native-priority-veto-executes-only-in-separate-derived-source-compiled-function',
    'exact-native-result-is-proven-only-for-pinned-15-recipes-three-modes-two-PE-capacities',
    'native-causal-ready-veto-is-conservative-not-maximum-opportunistic-throughput',
    'ready-feedback-at-hook-does-not-prove-all-future-generated-feedback-known',
    'finite-causal-horizon-witness-does-not-establish-arbitrary-workload-deadline-theorem',
    'derived-actor-credit-journal-does-not-modify-frozen-native-actor-state',
    'native-learning-operator-update-and-event-consumption-contract-unproven',
    'receiver-causal-hash-chains-are-not-distributed-cryptographic-authentication',
    'abstract-PE-and-memory-credits-do-not-prove-hardware-costs',
    'bounded-three-actor-case-no-N-node-or-cold-promotion',
)


def validate_v2n(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            canon(previous)==raw and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2o signed-off canonical v2n predecessor SHA/content changed')
    require(previous.get('schema')==
            'spk-bv-pinned-derived-forward-actor-fairness-opportunity/v2n' and
            previous.get('status')==
            'DERIVED_FORWARD_PROTECTED_OPPORTUNITY_CAUSAL_ACTOR_CREDIT_BOUNDED' and
            previous.get('reference_v2m_sha256')==
                '97f023c54198e05fcf8dc63f3602ec955acad0ea83a34544be7ef6f5e2311177' and
            previous.get('new_original_native_runs')==90 and
            previous.get('new_derived_fairness_window_runs')==270 and
            previous.get('new_derived_causal_null_runs')==135 and
            previous.get('legacy_v2m_actor_first_reference_cells')==90 and
            previous.get('universal_forward_liveness_proven') is False and
            previous.get('native_actor_credit_admission_proven') is False and
            previous.get('frozen_native_actor_priority_changed') is False and
            previous.get('native_operator_updates')==0 and
            previous.get('next_gate')==
                'BLOCKED_FROZEN_NATIVE_ACTOR_FAIRNESS_LIVENESS_ADMISSION_AND_CREDIT_CONSUMPTION',
            'v2o v2n scientific and frozen-contract exclusions drift')
    totals=previous.get('fairness_window_totals') or {}
    tight=totals.get('contended_capacity') or {}
    reserve=tight.get('always_protect') or {}
    require(reserve.get('cells')==45 and
            reserve.get('forward_timing_changed')==0 and
            reserve.get('actor_credit_acks')==156 and
            reserve.get('ack_wait_total_ticks')==537 and
            reserve.get('protected_forward_opportunity_ticks')==234 and
            tight.get('one_actor_turn',{}).get('forward_timing_changed')==45 and
            tight.get('legacy_window_16',{}).get('ready_forward_PE_blocked')==162 and
            totals.get('original_capacity',{}).get('always_protect',{}).get('cells')==45 and
            all(v==45 for v in (previous.get('causal_null_full_native_parity') or {}).values()) and
            (previous.get('bounded_horizon_witness') or {}).get('native_horizon_max_ticks')==11 and
            previous['bounded_horizon_witness']['derived_fairness_results'].get(
                'always_protect')=='BOUNDED_HORIZON_REJECTED_NO_CERTIFICATE',
            'v2o signed v2n fairness/timing/horizon evidence drift')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2o predecessor lacks pinned full workload matrix')
    for (label,recipe),row in zip(RECIPES,rows):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in row.get('modes',[])]==
                    [arm[0] for arm in ARMS],
                'v2o predecessor recipe or BV mode reordering')
        for mode in row['modes']:
            for regime,capacity in REGIMES:
                cell=mode.get('capacities',{}).get(regime) or {}
                windows=cell.get('fairness_windows') or {}
                require(cell.get('capacity')==capacity and
                        len(cell.get('signed_v2m_native_sha256',''))==64 and
                        windows.get('always_protect',{}).get('window')==0 and
                        windows.get('always_protect',{}).get(
                            'forward_functional_payload_same') is True and
                        windows.get('legacy_window_16',{}).get('window')==16,
                        'v2o signed v2n predecessor source-cell/signature drift')
    return True


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,name,forward,bv,policy='normal'):
    opts={}
    credit=ActorCreditPlanV2l()
    if policy=='loss':
        opts['accept']=lambda _x:False
    elif policy=='fault':
        def fault(_x):
            raise RuntimeError('v2o intentional callback loss')
        opts['accept']=fault
    elif policy=='cap_zero':
        credit=ActorCreditPlanV2l(max_abs_credit=0)
    else:
        require(policy=='normal','v2o unknown causal intervention')
    port=ReceiverPortV2h(**opts)
    service=DerivedCausalAdmissionV2o(port,
        admission_plan=CausalAdmissionPlanV2o(forward,bv),credit_plan=credit)
    observer=CallsiteObserver()
    derived,_,anchors,resource=derive_causal_executor(
        source,native_executor,port,service,observer)
    captured={}

    def run(*args,**kwargs):
        captured['integrated']=derived(*args,**kwargs)
        captured['projection']=service.project_original_native_result(
            captured['integrated'])
        return captured['projection']

    projected=_arm(run,plan_type,changed,fabric,plans,
                   f'v2o-{name}-{policy}',enabled,priority,digest,data)
    summary=service.summary()
    probes=service.admission_probes()
    journal=service.credit_journal()
    feedback=port.summary()
    require(anchors==(('batch',194),('clock',125),
                      ('emission',217),('ingress',136)) and
            resource==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts().get('_admit')==1 and
            observer.counts().get('_admit_plan')==1 and
            summary['protect_ready_forward'] is forward and
            summary['protect_ready_native_feedback'] is bv and
            summary['pregrants_during_native_causal_veto']==0 and
            summary['derived_actor_credit_ack_count']==len(journal)==
                summary['derived_resource_grants_committed'] and
            summary['derived_resource_grants_committed']+
                summary['unconsumed_delivered_controls']==
                    summary['delivered_controls']==feedback['control_delivered'] and
            summary['within_original_native_plan_capacity'] and
            summary['absence_certificates']==0 and
            summary['native_operator_updates']==0 and
            summary['native_event_arbitration_modified'] is False and
            summary['frozen_actor_state_changed'] is False and
            summary['native_learning_proven'] is False and
            len(probes)==summary['native_original_timeline_rows'],
            'v2o derived causal admission/native budget/journal custody drift')
    if policy!='normal':
        require(not journal and summary['pre_forward_actor_grants']==0 and
                summary['derived_resource_grants_committed']==0,
                'v2o causal null forged actor-control native PE admission')
    return projected,summary,feedback,observer.counts(),probes,journal,captured


def _bound_witness(source,case,fabric,plans,native_executor,plan_type):
    low=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
         plans[2],plans[3])
    ctrl=plan_type(max_ticks=11)
    native=native_executor(case,fabric,*low,ctrl)
    require(len(native['resources']['timeline'])==11,
            'v2o independently bounded native horizon changed')
    cells={}
    for name,forward,bv in MODES:
        port=ReceiverPortV2h()
        service=DerivedCausalAdmissionV2o(port,
            admission_plan=CausalAdmissionPlanV2o(forward,bv))
        derived,_,_,_=derive_causal_executor(
            source,native_executor,port,service,CallsiteObserver())
        try:
            result=derived(case,fabric,*low,ctrl)
        except LiveBVRejected as exc:
            require(name!='strict_native_causal' and
                    str(exc)=='bounded live logical horizon exceeded',
                    'v2o strict deadline guard failed or unrelated rejection')
            cells[name]={'status':'BOUNDED_HORIZON_REJECTED_NO_CERTIFICATE'}
        else:
            projected=service.project_original_native_result(result)
            require(name=='strict_native_causal' and projected==native and
                    service.summary()['pre_forward_actor_grants']>0,
                    'v2o one-sided deadline ablation unexpectedly completed')
            cells[name]={
                'status':'COMPLETED_EXACT_NATIVE_CAUSAL_PROJECTION',
                'source_native_resource_ticks':
                    service.summary()['native_original_timeline_rows'],
                'derived_pre_forward_actor_grants':
                    service.summary()['pre_forward_actor_grants'],
            }
    return {
        'max_ticks':11,'global_pe_slots_per_tick':1,
        'independent_frozen_native_completed':True,
        'admission_mode_outcomes':cells,
        'total_execution_attempts':5,
        'horizon_rejection_is_not_actor_negative_credit':True,
    }


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2n(previous,raw)
    root=root.resolve(strict=True)
    prior_sources=source_pins(root)
    prior_arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    original_hash=snapshot(original)
    totals={regime:{name:{
        'cells':0,'exact_full_native_projection':0,
        'exact_forward_timing':0,'exact_native_feedback':0,
        'exact_native_functional_payload':0,
        'actor_pre_forward_grants':0,'native_causal_veto_ticks':0,
        'native_forward_veto_ticks':0,'native_feedback_veto_ticks':0,
        'actor_credit_acks':0,'actor_ack_wait_total':0,
        'actor_ack_wait_max':0,
        'first_actor_grant_in_native_idle_tick_cells':0,
    } for name,_,_ in MODES} for regime,_ in REGIMES}
    null_totals={x:0 for x in NULLS}
    rows=[]
    for i,(label,recipe) in enumerate(RECIPES):
        changed=build_workload(case,recipe)
        modes=[]
        for j,(mode,enabled,priority) in enumerate(ARMS):
            regime_rows={}
            for regime,capacity in REGIMES:
                existing=previous['paired_native_matrix'][i]['modes'][j][
                    'capacities'][regime]
                changed_plans=(plans[0],replace(plans[1],
                    fabric_slots_per_tick=capacity),plans[2],plans[3])
                data=(changed,fabric,tuple(changed_plans))
                digest=snapshot(data)
                native_box={}

                def capture_native(*args,**kwargs):
                    native_box['result']=native_executor(*args,**kwargs)
                    return native_box['result']

                native=_arm(capture_native,plan_type,changed,fabric,
                    changed_plans,f'v2o-native-{regime}',enabled,priority,digest,data)
                require(native['whole_result_sha256']==existing[
                    'signed_v2m_native_sha256'],
                    'v2o source-native cell differs from signed v2n native digest')
                frozen=native_box['result']
                experiments={}
                for name,forward,bv in MODES:
                    projection,summary,feedback,counts,probes,acks,raw_result=_derived_arm(
                        source,native_executor,plan_type,changed,fabric,
                        changed_plans,enabled,priority,digest,data,
                        name=name,forward=forward,bv=bv)
                    result=raw_result['integrated']
                    same_forward=result['forward']==frozen['forward']
                    same_feedback=result['feedback']==frozen['feedback']
                    functional=_payload(result['forward'])==_payload(frozen['forward'])
                    whole=raw_result['projection']==frozen
                    require(functional and
                            summary['pregrants_during_native_causal_veto']==0 and
                            (not (forward and bv) or
                             (whole and same_forward and same_feedback)),
                            'v2o strict source-backed native causal parity lost')
                    if name=='strict_native_causal':
                        require(whole and
                                len(acks)==summary['delivered_controls'],
                                'v2o strict actor credit backlog not fully ACKed')
                    if name=='actor_first_null_guard':
                        ref=existing['fairness_windows']['legacy_window_16']
                        require(not summary['native_causal_priority_veto_ticks'] and
                                [x['timestamp'] for x in result['forward']['terminal']]==
                                    ref['forward_terminal_ticks'] and
                                acks==ref['actor_credit_journal'],
                                'v2o null guard does not recover signed v2n actor-first')
                    agg=totals[regime][name]
                    agg['cells']+=1
                    agg['exact_full_native_projection']+=int(whole)
                    agg['exact_forward_timing']+=int(same_forward)
                    agg['exact_native_feedback']+=int(same_feedback)
                    agg['exact_native_functional_payload']+=int(functional)
                    agg['actor_pre_forward_grants']+=summary['pre_forward_actor_grants']
                    agg['native_causal_veto_ticks']+=summary['native_causal_priority_veto_ticks']
                    agg['native_forward_veto_ticks']+=summary['native_forward_veto_ticks']
                    agg['native_feedback_veto_ticks']+=summary['native_feedback_veto_ticks']
                    agg['actor_credit_acks']+=len(acks)
                    agg['first_actor_grant_in_native_idle_tick_cells']+=int(
                        summary['pre_forward_actor_grants']>0)
                    waits=[a['serviced_tick']-a['due_tick'] for a in acks]
                    require(all(w>=0 for w in waits),
                            'v2o ACK serviced before due judgment')
                    agg['actor_ack_wait_total']+=sum(waits)
                    agg['actor_ack_wait_max']=max(agg['actor_ack_wait_max'],
                                                  max(waits,default=0))
                    experiments[name]={
                        'protect_ready_forward':forward,
                        'protect_ready_native_feedback':bv,
                        'full_independent_original_native_projection_equal':whole,
                        'exact_forward_trace_equal':same_forward,
                        'exact_native_feedback_equal':same_feedback,
                        'forward_functional_payload_equal':functional,
                        'summary':summary,
                        'native_causal_admission_probes':probes,
                        'actor_credit_journal':acks,
                        'actor_ack_wait_ticks':waits,
                        'callsite_counts':counts,
                    }
                if regime=='contended_capacity':
                    null={}
                    for policy in NULLS:
                        projection,summary,feedback,counts,probes,acks,raw_result=_derived_arm(
                            source,native_executor,plan_type,changed,fabric,
                            changed_plans,enabled,priority,digest,data,
                            name='strict_native_causal',forward=True,bv=True,
                            policy=policy)
                        require(projection==native and
                                raw_result['projection']==frozen and
                                not acks and summary['pre_forward_actor_grants']==0,
                                'v2o strict native causal-null whole projection drift')
                        null_totals[policy]+=1
                        null[policy]={
                            'full_native_equality':True,
                            'delivered':summary['delivered_controls'],
                            'actor_credit_ack_count':len(acks),
                            'transport_lost':feedback['lost'],
                            'callback_fault_lost':feedback['fault_lost'],
                        }
                    experiments['causal_nulls']=null
                regime_rows[regime]={
                    'capacity':capacity,
                    'signed_v2n_native_sha256':existing['signed_v2m_native_sha256'],
                    'admission_modes':experiments,
                }
            modes.append({'mode':mode,'capacities':regime_rows})
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot(original)==original_hash,
                'v2o source native fixture modified across interventions')
    bound=_bound_witness(source,case,fabric,plans,native_executor,plan_type)
    strict=totals['contended_capacity']['strict_native_causal']
    require(all(t['cells']==45 and t['exact_native_functional_payload']==45
                for regime in totals.values() for t in regime.values()) and
            all(totals[regime]['strict_native_causal'][k]==45
                for regime,_ in REGIMES
                for k in ('exact_full_native_projection','exact_forward_timing',
                          'exact_native_feedback')) and
            all(totals[regime]['strict_native_causal'][
                'first_actor_grant_in_native_idle_tick_cells']>0
                for regime,_ in REGIMES) and
            strict['actor_pre_forward_grants']>0 and
            all(n==45 for n in null_totals.values()) and
            totals['contended_capacity']['actor_first_null_guard'][
                'exact_full_native_projection']==0 and
            bound['admission_mode_outcomes']['strict_native_causal']['status']==
                'COMPLETED_EXACT_NATIVE_CAUSAL_PROJECTION',
            'v2o strict native causal admission parity or ablations incomplete')
    require(source_pins(root)==prior_sources and
            read_pinned_sources(root)==prior_arch and
            read_pinned_source(root)==source and snapshot(original)==original_hash,
            'v2o frozen source/pinned architecture changed across replays')
    return {
        'paired_native_matrix':rows,'causal_admission_totals':totals,
        'causal_null_full_native_parity':null_totals,
        'bounded_horizon_discrimination':bound,
        'native_original_runs':90,'derived_causal_admission_runs':360,
        'derived_causal_null_runs':135,'native_source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2n(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['native_original_runs']==90 and
             result['derived_causal_admission_runs']==360 and
             result['derived_causal_null_runs']==135 and
             result['bounded_horizon_discrimination']['total_execution_attempts']==5 and
             all(v==45 for v in result['causal_null_full_native_parity'].values())),
            'v2o source-backed native causal admission matrix incomplete')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('SOURCE_PINNED_DERIVED_NATIVE_CAUSAL_READY_ADMISSION'
                       if result else 'SIGNED_V2N_PREDECESSOR_ONLY'),
        'reference_v2n_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked_in_this_run':bool(result),
        'new_original_native_runs':result['native_original_runs'] if result else 0,
        'new_derived_causal_admission_runs':result['derived_causal_admission_runs'] if result else 0,
        'new_derived_causal_null_runs':result['derived_causal_null_runs'] if result else 0,
        'new_bounded_horizon_execution_attempts':5 if result else 0,
        'causal_admission_totals':result['causal_admission_totals'] if result else None,
        'causal_null_full_native_parity':result['causal_null_full_native_parity'] if result else None,
        'bounded_horizon_discrimination':(
            result['bounded_horizon_discrimination'] if result else None),
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'frozen_native_actor_event_admission_proven':False,
        'frozen_native_actor_learning_proven':False,
        'arbitrary_workload_native_deadline_equivalence_proven':False,
        'native_operator_updates':0,
        'next_gate':
            'BLOCKED_FROZEN_NATIVE_ACTOR_CONSUMER_HANDOFF_AND_GENERAL_CAUSAL_READY_PROOF',
        'claims_excluded':list(EXCLUSIONS),
    }
