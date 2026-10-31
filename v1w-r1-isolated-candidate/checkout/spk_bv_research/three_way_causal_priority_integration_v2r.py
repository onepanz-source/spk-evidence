"""BV v2r: differential causal priority under separately charged consumer work.

The three parties are source-native forward/feedback, resource-serviced actor
ACKs, and independently paid actor applications. v2r is explicitly a causal
guard *discrimination*, NOT a native three-way concurrent arbiter contract.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected
from spk_backvalidation_v2.derived_native_fork_v2g import CallsiteObserver,read_pinned_source
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import ActorCreditPlanV2l
from spk_backvalidation_v2.derived_causal_admission_v2o import CausalAdmissionPlanV2o
from spk_backvalidation_v2.derived_actor_resource_consumer_v2q import (
    ConsumerResourcePlanV2q,DerivedActorResourceConsumerV2q,
    derive_resource_consumer_executor,
)
from spk_bv_research.actor_priority_contention_integration_v2m import (
    REGIMES,_payload,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import require,snapshot,source_pins,runtime_modules_bound
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES,build_workload
from spk_bv_research.link_pressure_v0u import ARMS,_arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-pinned-three-way-causal-priority-discrimination/v2r'
STATUS='DERIVED_THREE_WAY_CAUSAL_GUARD_CONTENTION_DISCRIMINATED_NATIVE_ARBITER_BLOCKED'
CONTRACT_STATUS='V2R_SIGNED_V2Q_PREDECESSOR_ONLY_NATIVE_ARBITER_UNPROVEN'
PREDECESSOR_SHA='f214cbe1c75df7535171d14400c2cf37965fa5868aa55d02bc8a56f0891aa926'
MODES=(('strict_native_ready',True,True),
       ('forward_only',True,False),
       ('feedback_only',False,True),
       ('actor_first_null_guard',False,False))
INTERVENTIONS=('consumer_charge_zero','consumer_tail_off',
               'causal_transport_loss','ACK_credit_zero')
EXCLUSIONS=(
    'forward-vs-ACK-priority-is-only-varied-in-separately-compiled-derived-source',
    'consumer-PE-charge-is-post-forward-and-does-not-itself-preempt-native-forward',
    'this-experiment-is-not-a-genuine-native-concurrent-three-way-arbiter',
    'ACK-priority-ablation-is-not-proof-that-frozen-native-priority-may-change',
    'strict-native-full-equality-only-applies-to-source-pinned-15-by-3-by-2-cells',
    'consumer-backlog-and-loss-never-imply-negative-credit-or-silence-certificate',
    'three-actor-finite-horizon-witness-is-not-general-termination-theorem',
    'resource-units-remain-abstract-not-hardware-calibrated',
    'no-native-learning-operator-update-or-cold-node-promotion',
    'ACK-credit-and-consumer-hash-chains-are-not-cryptographic-authentication',
)


def validate_v2q(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            canon(previous)==raw and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2r signed canonical v2q predecessor SHA/content drift')
    require(previous.get('schema')==
            'spk-bv-pinned-independent-actor-consumer-resource-charging/v2q' and
            previous.get('status')==
            'DERIVED_ACTOR_CONSUMER_INDEPENDENT_PE_MEMORY_CHARGED_NATIVE_PROJECTION' and
            previous.get('reference_v2p_sha256')==
                '1c3f2b0010f6a0470ac2b5be021838b8e1992e85760e367a532d5e5dfe8f9ef3' and
            previous.get('new_native_runs')==90 and
            previous.get('new_resource_charged_normal_runs')==90 and
            previous.get('new_resource_backpressure_intervention_runs')==180 and
            previous.get('new_negative_fixture_runs')==2 and
            previous.get('frozen_native_actor_resource_consumption_proven') is False and
            previous.get('frozen_native_actor_learning_proven') is False and
            previous.get('native_operator_updates')==0 and
            previous.get('next_gate')==
                'BLOCKED_FROZEN_NATIVE_ACTOR_INTAKE_AND_CONCURRENT_CONSUMER_FORWARD_ARBITRATION',
            'v2r signed v2q scientific exclusion/source predecessor drift')
    totals=previous.get('independently_charged_consumer_totals') or {}
    require(all(totals.get(regime,{}).get('cells')==45 and
                totals[regime]['native_projection']==45 and
                totals[regime]['ACKs']==156 and
                totals[regime]['charged_consumptions']==156 and
                totals[regime]['independent_PE_units']==156 and
                totals[regime]['independent_memory_units']==312
                for regime,_ in REGIMES) and
            totals.get('contended_capacity',{}).get('native_tick_paid')==0 and
            totals.get('contended_capacity',{}).get('consumer_tail_paid')==156 and
            all((previous.get('resource_backpressure_intervention_totals') or {}).get(
                    mode,{}).get('native_projection')==45
                for mode in ('charge_zero','memory_zero','tail_off','total_one')),
            'v2r signed v2q independent consumer resource discrimination drift')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2r signed v2q complete 15-recipe matrix missing')
    for (label,recipe),row in zip(RECIPES,rows):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in row.get('modes',[])]==
                    [arm[0] for arm in ARMS],
                'v2r signed v2q recipe/BV mode ordering drift')
        for mode in row['modes']:
            for regime,capacity in REGIMES:
                cell=mode.get('capacities',{}).get(regime,{})
                s=cell.get('summary') or {}
                require(cell.get('capacity')==capacity and
                        len(cell.get('signed_v2p_native_sha256',''))==64 and
                        cell.get('exact_full_native_projection') is True and
                        cell.get('v2p_ACK_journal_equal') is True and
                        s.get('derived_independent_consumer_resource_charges')==
                            len(cell.get('independent_PE_memory_charge_journal',[])) and
                        s.get('derived_actor_credit_ack_count')==
                            len(cell.get('ACK_journal',[])) and
                        s.get('pregrants_during_native_causal_veto')==0,
                        'v2r signed v2q native/ACK/consumer cell drift')
    return True


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,name,forward,bv,
                 intervention='normal'):
    opts={}
    credit=ActorCreditPlanV2l()
    resources=ConsumerResourcePlanV2q()
    if intervention=='consumer_charge_zero':
        resources=replace(resources,max_total_consumer_charges=0)
    elif intervention=='consumer_tail_off':
        resources=replace(resources,max_resource_tail_ticks=0)
    elif intervention=='causal_transport_loss':
        opts['accept']=lambda _:False
    elif intervention=='ACK_credit_zero':
        credit=ActorCreditPlanV2l(max_abs_credit=0)
    else:
        require(intervention=='normal','v2r invalid three-way contention intervention')
    port=ReceiverPortV2h(**opts)
    service=DerivedActorResourceConsumerV2q(
        port,resource_plan=resources,
        admission_plan=CausalAdmissionPlanV2o(forward,bv),credit_plan=credit)
    observer=CallsiteObserver()
    compiled,_,semantic,resource_hooks=derive_resource_consumer_executor(
        source,native_executor,port,service,observer)
    captured={}

    def run(*args,**kwargs):
        captured['derived']=compiled(*args,**kwargs)
        captured['projected']=service.project_original_native_result(
            captured['derived'])
        return captured['projected']

    projected=_arm(run,plan_type,changed,fabric,plans,
                   f'v2r-{name}-{intervention}',enabled,priority,digest,data)
    summary=service.summary()
    ACKs=service.credit_journal()
    consumer=service.consumer_journal()
    charges=service.resource_charge_journal()
    probes=service.admission_probes()
    feedback=port.summary()
    require(semantic==(('batch',194),('clock',125),
                       ('emission',217),('ingress',136)) and
            resource_hooks==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts().get('_admit')==1 and
            observer.counts().get('_admit_plan')==1 and
            summary['protect_ready_forward'] is forward and
            summary['protect_ready_native_feedback'] is bv and
            summary['pregrants_during_native_causal_veto']==0 and
            summary['derived_actor_credit_ack_count']==len(ACKs) and
            summary['delivered_controls']==len(ACKs)+
                summary['unconsumed_delivered_controls'] and
            summary['actor_consumer_applications']==len(consumer)==len(charges) and
            summary['derived_independent_consumer_PE_units']==len(charges) and
            summary['derived_independent_consumer_memory_units']==2*len(charges) and
            summary['actor_consumer_pending_ack_backlog']==len(ACKs)-len(charges) and
            summary['independent_consumer_source_budget_verified'] is True and
            summary['native_operator_updates']==0 and
            summary['absence_certificates']==0 and
            summary['frozen_actor_state_changed'] is False and
            len(probes)==summary['native_original_timeline_rows'],
            'v2r three-way native/ACK/consumer causal custody drift')
    if intervention=='normal':
        require(len(ACKs)==len(charges),
                'v2r default three-way resource tail left ACKs unpaid')
    if intervention in ('causal_transport_loss','ACK_credit_zero'):
        require(not ACKs and not charges and not consumer,
                'v2r causal null manufactured resource ACKs or consumer credit')
    if intervention=='consumer_charge_zero':
        require(not charges and len(ACKs)==summary[
                    'actor_consumer_pending_ack_backlog'],
                'v2r zero consumer grant fabricated applied credits')
    if intervention=='consumer_tail_off':
        require(summary['new_consumer_only_resource_timeline_rows']==0,
                'v2r explicit consumer tail-off synthesized service rows')
    return (projected,summary,ACKs,consumer,charges,probes,feedback,
            captured,observer.counts())


def _bounded_horizon(source,case,fabric,plans,native_executor,plan_type):
    reduced=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
             plans[2],plans[3])
    ctrl=plan_type(max_ticks=11)
    native=native_executor(case,fabric,*reduced,ctrl)
    require(len(native['resources']['timeline'])==11,
            'v2r bounded independent frozen native case no longer takes 11 ticks')
    outcomes={}
    for name,forward,bv in MODES:
        port=ReceiverPortV2h()
        service=DerivedActorResourceConsumerV2q(port,
            admission_plan=CausalAdmissionPlanV2o(forward,bv))
        compiled,_,_,_=derive_resource_consumer_executor(
            source,native_executor,port,service,CallsiteObserver())
        try:
            result=compiled(case,fabric,*reduced,ctrl)
        except LiveBVRejected as exc:
            require(name!='strict_native_ready' and
                    str(exc)=='bounded live logical horizon exceeded',
                    'v2r strict native-ready protected mode rejected finite horizon')
            outcomes[name]='BOUNDED_HORIZON_REJECTED_NO_CERTIFICATE'
        else:
            projection=service.project_original_native_result(result)
            require(name=='strict_native_ready' and projection==native and
                    service.summary()['derived_independent_consumer_resource_charges']>0,
                    'v2r one-sided guard ablation unexpectedly satisfied strict horizon')
            outcomes[name]='EXACT_FULL_NATIVE_PROJECTION_AND_PAID_CONSUMER'
    return {'max_ticks':11,'native_horizon_equality':True,
            'guard_modes':outcomes,
            'execution_attempts':5,
            'rejection_is_not_negative_actor_evidence':True}


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2q(previous,raw)
    root=root.resolve(strict=True)
    before_sources=source_pins(root)
    before_arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    case,fabric,plans=fixture_fn()
    input_hash=snapshot((case,fabric,plans))
    totals={regime:{name:{
        'cells':0,'full_native_projection':0,'forward_trace_equal':0,
        'feedback_trace_equal':0,'forward_functional_payload_equal':0,
        'ACKs':0,'consumer_paid':0,'consumer_pending':0,
        'independent_PE_units':0,'independent_memory_units':0,
        'native_timeline_ticks':0,'pre_forward_ACK_grants':0,
        'consumer_native_inline_paid':0,'consumer_tail_paid':0,
        'consumer_resource_capacity_rejections':0,
    } for name,_,_ in MODES} for regime,_ in REGIMES}
    interventions={p:{'cells':0,'native_restored':0,'ACKs':0,
                       'paid':0,'pending':0,'forward_equal_baseline':0,
                       'feedback_equal_baseline':0,'ACK_journal_equal_baseline':0}
                   for p in INTERVENTIONS}
    rows=[]
    for i,(label,recipe) in enumerate(RECIPES):
        changed=build_workload(case,recipe)
        modes=[]
        for j,(mode,enabled,priority) in enumerate(ARMS):
            capacities={}
            for regime,capacity in REGIMES:
                prev=previous['paired_native_matrix'][i]['modes'][j][
                    'capacities'][regime]
                amended=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
                         plans[2],plans[3])
                data=(changed,fabric,amended)
                digest=snapshot(data)
                original={}

                def capture_native(*args,**kwargs):
                    original['native']=native_executor(*args,**kwargs)
                    return original['native']

                native=_arm(capture_native,plan_type,changed,fabric,amended,
                    'v2r-original-'+regime,enabled,priority,digest,data)
                require(native['whole_result_sha256']==prev[
                            'signed_v2p_native_sha256'],
                        'v2r source original-native SHA differs from signed v2q')
                guard_cells={}
                for name,forward,bv in MODES:
                    p,s,acks,consumed,charges,probes,feedback,raw_result,counts=_derived_arm(
                        source,native_executor,plan_type,changed,fabric,amended,
                        enabled,priority,digest,data,name=name,forward=forward,bv=bv)
                    projected=raw_result['projected']
                    original_native=original['native']
                    whole=p==native and projected==original_native
                    same_forward=projected['forward']==original_native['forward']
                    same_feedback=projected['feedback']==original_native['feedback']
                    functional=_payload(projected['forward'])==_payload(
                        original_native['forward'])
                    require(functional and len(acks)==len(consumed)==len(charges) and
                            (name!='strict_native_ready' or
                             (whole and same_forward and same_feedback and
                              acks==prev['ACK_journal'] and
                              charges==prev['independent_PE_memory_charge_journal'] and
                              consumed==prev['charged_actor_consumptions'] and
                              s['native_causal_priority_veto_ticks']==
                                prev['summary']['native_causal_priority_veto_ticks'])),
                            'v2r three-way causal guard source/ACK/resource parity drift')
                    agg=totals[regime][name]
                    agg['cells']+=1
                    agg['full_native_projection']+=int(whole)
                    agg['forward_trace_equal']+=int(same_forward)
                    agg['feedback_trace_equal']+=int(same_feedback)
                    agg['forward_functional_payload_equal']+=int(functional)
                    agg['ACKs']+=len(acks)
                    agg['consumer_paid']+=len(charges)
                    agg['consumer_pending']+=s['actor_consumer_pending_ack_backlog']
                    agg['independent_PE_units']+=len(charges)
                    agg['independent_memory_units']+=2*len(charges)
                    agg['native_timeline_ticks']+=s['native_original_timeline_rows']
                    agg['pre_forward_ACK_grants']+=s['pre_forward_actor_grants']
                    agg['consumer_native_inline_paid']+=s[
                        'consumer_independent_inline_charges']
                    agg['consumer_tail_paid']+=s['consumer_independent_tail_charges']
                    agg['consumer_resource_capacity_rejections']+=s[
                        'consumer_resource_capacity_rejections']
                    summary_cell={
                        'full_native_projection':whole,
                        'forward_trace_equal':same_forward,
                        'feedback_trace_equal':same_feedback,
                        'functional_forward_equal':functional,
                        'forward_terminal_ticks':[x['timestamp']
                            for x in projected['forward']['terminal']],
                        'original_terminal_ticks':[x['timestamp']
                            for x in original_native['forward']['terminal']],
                        'ACKs':len(acks),'consumer_paid':len(charges),
                        'consumer_pending':s['actor_consumer_pending_ack_backlog'],
                        'native_timeline_ticks':s['native_original_timeline_rows'],
                        'pre_forward_ACK_grants':s['pre_forward_actor_grants'],
                        'consumer_native_inline_paid':s[
                            'consumer_independent_inline_charges'],
                        'consumer_tail_paid':s['consumer_independent_tail_charges'],
                        'consumer_resource_capacity_rejections':s[
                            'consumer_resource_capacity_rejections'],
                        'ACK_journal_sha256':sha256(canon(acks)).hexdigest(),
                        'charged_receipts_sha256':sha256(canon(charges)).hexdigest(),
                        'native_causal_veto_ticks':s['native_causal_priority_veto_ticks'],
                    }
                    if regime=='contended_capacity':
                        ablations={}
                        for intervention in INTERVENTIONS:
                            alt,alt_s,alt_acks,alt_cons,alt_charges,_,alt_feedback,alt_raw,_=_derived_arm(
                                source,native_executor,plan_type,changed,fabric,amended,
                                enabled,priority,digest,data,name=name,forward=forward,
                                bv=bv,intervention=intervention)
                            candidate=alt_raw['projected']
                            same_as_mode_forward=candidate['forward']==projected['forward']
                            same_as_mode_feedback=candidate['feedback']==projected['feedback']
                            same_acks=alt_acks==acks
                            null=intervention in ('causal_transport_loss','ACK_credit_zero')
                            require((null and alt==native and
                                     candidate==original_native and
                                     not alt_acks and not alt_charges) or
                                    (not null and candidate==projected and
                                     same_acks and same_as_mode_forward and
                                     same_as_mode_feedback),
                                    'v2r consumer/transport causal ablation changed unrelated native projection')
                            counter=interventions[intervention]
                            counter['cells']+=1
                            counter['native_restored']+=int(candidate==original_native)
                            counter['ACKs']+=len(alt_acks)
                            counter['paid']+=len(alt_charges)
                            counter['pending']+=alt_s['actor_consumer_pending_ack_backlog']
                            counter['forward_equal_baseline']+=int(same_as_mode_forward)
                            counter['feedback_equal_baseline']+=int(same_as_mode_feedback)
                            counter['ACK_journal_equal_baseline']+=int(same_acks)
                            ablations[intervention]={
                                'native_restored':candidate==original_native,
                                'ACK_count':len(alt_acks),
                                'consumer_paid':len(alt_charges),
                                'pending_backlog':alt_s['actor_consumer_pending_ack_backlog'],
                                'same_forward_as_mode':same_as_mode_forward,
                                'same_feedback_as_mode':same_as_mode_feedback,
                            }
                        summary_cell['causal_resource_interventions']=ablations
                    guard_cells[name]=summary_cell
                capacities[regime]={
                    'capacity':capacity,
                    'signed_v2q_native_sha256':prev['signed_v2p_native_sha256'],
                    'guard_modes':guard_cells,
                }
            modes.append({'mode':mode,'capacities':capacities})
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot((case,fabric,plans))==input_hash,
                'v2r pinned original-native fixture modified across arbitration modes')
    horizon=_bounded_horizon(source,case,fabric,plans,native_executor,plan_type)
    strict=totals['contended_capacity']['strict_native_ready']
    require(all(v['cells']==45 and v['forward_functional_payload_equal']==45
                for per_regime in totals.values() for v in per_regime.values()) and
            all(totals[regime]['strict_native_ready'][key]==45
                for regime,_ in REGIMES
                for key in ('full_native_projection','forward_trace_equal',
                            'feedback_trace_equal')) and
            all(totals[regime]['strict_native_ready']['ACKs']==156 and
                totals[regime]['strict_native_ready']['consumer_paid']==156
                for regime,_ in REGIMES) and
            strict['consumer_native_inline_paid']==0 and
            strict['consumer_tail_paid']==156 and
            totals['contended_capacity']['actor_first_null_guard'][
                'full_native_projection']==0 and
            totals['contended_capacity']['forward_only'][
                'feedback_trace_equal']<45 and
            totals['contended_capacity']['feedback_only'][
                'forward_trace_equal']<45 and
            all(v['cells']==180 for v in interventions.values()) and
            interventions['causal_transport_loss']['native_restored']==180 and
            interventions['ACK_credit_zero']['native_restored']==180 and
            interventions['consumer_charge_zero']['paid']==0 and
            interventions['consumer_charge_zero']['ACK_journal_equal_baseline']==180 and
            horizon['guard_modes']['strict_native_ready']==
                'EXACT_FULL_NATIVE_PROJECTION_AND_PAID_CONSUMER' and
            source_pins(root)==before_sources and
            read_pinned_sources(root)==before_arch and
            read_pinned_source(root)==source and
            snapshot((case,fabric,plans))==input_hash,
            'v2r three-way causal guard discrimination or source pins incomplete')
    return {
        'paired_native_matrix':rows,
        'causal_priority_resource_totals':totals,
        'causal_resource_intervention_totals':interventions,
        'bounded_horizon_discrimination':horizon,
        'independent_native_runs':90,
        'derived_four_guard_runs':360,
        'derived_causal_intervention_runs':720,
        'bounded_horizon_execution_attempts':5,
        'source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2q(previous,raw)
    require(result is None or
            (result['source_custody'] and
             result['independent_native_runs']==90 and
             result['derived_four_guard_runs']==360 and
             result['derived_causal_intervention_runs']==720 and
             result['bounded_horizon_execution_attempts']==5 and
             all(v['cells']==180 for v in
                 result['causal_resource_intervention_totals'].values())),
            'v2r independent three-way causal arbitration research gate incomplete')
    return {
        'schema':SCHEMA,
        'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('SOURCE_PINNED_THREE_WAY_CAUSAL_GUARD_DISCRIMINATION'
                       if result else 'SIGNED_V2Q_PREDECESSOR_ONLY'),
        'reference_v2q_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked':bool(result),
        'new_native_runs':result['independent_native_runs'] if result else 0,
        'new_derived_four_guard_runs':result['derived_four_guard_runs'] if result else 0,
        'new_derived_causal_intervention_runs':(
            result['derived_causal_intervention_runs'] if result else 0),
        'new_bounded_horizon_execution_attempts':(
            result['bounded_horizon_execution_attempts'] if result else 0),
        'causal_priority_resource_totals':(
            result['causal_priority_resource_totals'] if result else None),
        'causal_resource_intervention_totals':(
            result['causal_resource_intervention_totals'] if result else None),
        'bounded_horizon_discrimination':(
            result['bounded_horizon_discrimination'] if result else None),
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'native_concurrent_three_way_event_arbitration_proven':False,
        'native_forward_credit_learning_contract_proven':False,
        'arbitrary_workload_bounded_forward_liveness_proven':False,
        'native_operator_updates':0,
        'next_gate':
            'BLOCKED_FROZEN_NATIVE_CONCURRENT_ACTOR_CONSUMER_FORWARD_ARBITRATION',
        'claims_excluded':list(EXCLUSIONS),
    }
