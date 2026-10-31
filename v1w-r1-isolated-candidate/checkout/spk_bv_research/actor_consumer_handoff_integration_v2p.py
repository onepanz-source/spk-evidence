"""BV v2p: signed v2o strict native parity and independent actor ACK consumer."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import CallsiteObserver,read_pinned_source
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_consumer_v2p import (
    ActorConsumerPlanV2p,DerivedActorConsumerV2p,derive_consumer_executor,
)
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected
from spk_bv_research.actor_priority_contention_integration_v2m import REGIMES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import require,snapshot,source_pins,runtime_modules_bound
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES,build_workload
from spk_bv_research.link_pressure_v0u import ARMS,_arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-pinned-derived-actor-ack-consumer-handoff/v2p'
STATUS='DERIVED_ACTOR_CONSUMER_ACK_HANDOFF_EXACTLY_ONCE_NATIVE_PARITY'
CONTRACT_STATUS='V2P_SIGNED_V2O_PREDECESSOR_ONLY_NO_NATIVE_CONSUMER_CONTRACT'
PREDECESSOR_SHA='778a38f312d1e5403f0106015214cec924fe4f284e4cdbf107422f8b76c0716c'
INTERVENTIONS=('total_one','total_zero','tail_off','throughput_zero')
EXCLUSIONS=(
    'actor-consumption-is-an-independent-derived-register-not-frozen-native-actor-intake',
    'consumer-reuses-the-resource-charged-ACK-entitlement-no-extra-PE-or-memory-cost-claimed',
    'source-pinned-45-cells-at-each-of-two-PE-capacities-are-not-arbitrary-workload-proof',
    'consumer-tick-after-native-or-derived-tail-is-not-a-frozen-native-scheduling-policy',
    'hash-chained-receipts-detect-replay-in-process-but-are-not-network-authentication',
    'ACK-pending-under-quota-or-truncated-tail-is-not-negative-or-silence-evidence',
    'native-learning-operator-weight-updates-and-actor-intake-remain-unproven',
    'abstract-reused-ACK-resource-budget-is-not-physical-actor-compute-measurement',
    'three-actor-bounded-case-no-cold-promotion-or-general-N-node-theorem',
)


def validate_v2o(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            canon(previous)==raw and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2p signed canonical v2o predecessor SHA changed')
    require(previous.get('schema')==
            'spk-bv-pinned-native-causal-ready-actor-admission/v2o' and
            previous.get('status')==
            'DERIVED_NATIVE_CAUSAL_READY_VETO_EXACT_FULL_PARITY_AND_BOUND_WITNESS' and
            previous.get('reference_v2n_sha256')==
                '1fbb75ad2ff7f8a9f0124b94bd72e7dac1d4f559e23a07b4d65e95981e162459' and
            previous.get('new_original_native_runs')==90 and
            previous.get('new_derived_causal_admission_runs')==360 and
            previous.get('new_derived_causal_null_runs')==135 and
            previous.get('new_bounded_horizon_execution_attempts')==5 and
            previous.get('native_operator_updates')==0 and
            previous.get('frozen_native_actor_event_admission_proven') is False and
            previous.get('frozen_native_actor_learning_proven') is False and
            previous.get('next_gate')==
                'BLOCKED_FROZEN_NATIVE_ACTOR_CONSUMER_HANDOFF_AND_GENERAL_CAUSAL_READY_PROOF',
            'v2p signed v2o causal guard scientific boundary drift')
    totals=previous.get('causal_admission_totals',{})
    require(all(totals.get(regime,{}).get('strict_native_causal',{}).get(
                'exact_full_native_projection')==45 for regime,_ in REGIMES) and
            all(totals.get(regime,{}).get('strict_native_causal',{}).get(
                'actor_credit_acks')==156 for regime,_ in REGIMES) and
            previous.get('bounded_horizon_discrimination',{}).get('max_ticks')==11 and
            previous['bounded_horizon_discrimination'][
                'admission_mode_outcomes']['strict_native_causal']['status']==
                    'COMPLETED_EXACT_NATIVE_CAUSAL_PROJECTION',
            'v2p predecessor strict native parity and finite horizon drift')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2p signed v2o native paired-matrix missing')
    for (label,recipe),row in zip(RECIPES,rows):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [mode.get('mode') for mode in row.get('modes',[])]==
                    [a[0] for a in ARMS],
                'v2p signed recipe ordering changed')
        for mode in row['modes']:
            for regime,capacity in REGIMES:
                cell=mode.get('capacities',{}).get(regime,{})
                strict=cell.get('admission_modes',{}).get('strict_native_causal',{})
                require(cell.get('capacity')==capacity and
                        len(cell.get('signed_v2n_native_sha256',''))==64 and
                        strict.get('full_independent_original_native_projection_equal') is True and
                        strict.get('exact_forward_trace_equal') is True and
                        strict.get('exact_native_feedback_equal') is True and
                        strict.get('summary',{}).get('protect_ready_forward') is True and
                        strict.get('summary',{}).get('protect_ready_native_feedback') is True and
                        strict.get('summary',{}).get('derived_actor_credit_ack_count')==
                            len(strict.get('actor_credit_journal',[])),
                        'v2p signed v2o strict source-native cell drift')
    return True


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,name,policy='normal'):
    if policy=='normal':
        plan=ActorConsumerPlanV2p()
    elif policy=='total_one':
        plan=ActorConsumerPlanV2p(max_total_consume=1)
    elif policy=='total_zero':
        plan=ActorConsumerPlanV2p(max_total_consume=0)
    elif policy=='tail_off':
        plan=ActorConsumerPlanV2p(max_tail_ticks=0)
    elif policy=='throughput_zero':
        plan=ActorConsumerPlanV2p(max_consume_per_tick=0)
    else:
        raise ValueError('v2p unrecognized bounded consumer intervention')
    port=ReceiverPortV2h()
    consumer=DerivedActorConsumerV2p(port,consumer_plan=plan)
    observer=CallsiteObserver()
    derived,_,semantic,resource=derive_consumer_executor(
        source,native_executor,port,consumer,observer)
    integrated={}

    def run(*args,**kwargs):
        integrated['result']=derived(*args,**kwargs)
        integrated['projection']=consumer.project_original_native_result(
            integrated['result'])
        return integrated['projection']

    projected=_arm(run,plan_type,changed,fabric,plans,
                   f'v2p-{name}-{policy}',enabled,priority,digest,data)
    summary=consumer.summary()
    acks=consumer.credit_journal()
    applied=consumer.consumer_journal()
    trace=consumer.consumer_trace()
    require(semantic==(('batch',194),('clock',125),
                       ('emission',217),('ingress',136)) and
            resource==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts().get('_admit')==1 and
            observer.counts().get('_admit_plan')==1 and
            summary['protect_ready_forward'] is True and
            summary['protect_ready_native_feedback'] is True and
            summary['pregrants_during_native_causal_veto']==0 and
            summary['derived_actor_credit_ack_count']==len(acks)==
                summary['derived_resource_grants_committed'] and
            summary['actor_consumer_applications']==len(applied) and
            summary['actor_consumer_pending_ack_backlog']==len(acks)-len(applied) and
            summary['delivered_controls']==len(acks) and
            summary['within_original_native_plan_capacity'] and
            summary['native_operator_updates']==0 and
            summary['absence_certificates']==0 and
            summary['frozen_actor_state_changed'] is False and
            summary['native_learning_proven'] is False and
            summary['consumer_consumption_borrows_existing_ACK_charge'] is True and
            summary['consumer_extra_PE_or_memory_budget_charged'] is False and
            len({receipt['ack_digest'] for receipt in applied})==len(applied) and
            len(trace)==summary['native_original_timeline_rows']+
                summary['consumer_extra_tail_ticks'],
            'v2p derived consumer/grant/resource/native causal contract drift')
    require(policy!='normal' or len(applied)==len(acks),
            'v2p normal consumer tail did not settle source ACK backlog')
    require(policy not in ('total_zero','throughput_zero') or
            (not applied and summary['consumer_extra_tail_ticks']==0),
            'v2p disabled consumer fabricated application or tail')
    return projected,summary,acks,applied,trace,integrated,observer.counts()


def _negative_fixture(source,case,fabric,plans,native_executor,plan_type):
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    altered=replace(case,nodes=tuple(replace(node,instructions=block)
                if node.node_id=='B' else node for node in case.nodes))
    capacity=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
              plans[2],plans[3])
    native=native_executor(altered,fabric,*capacity,plan_type())
    port=ReceiverPortV2h()
    consumer=DerivedActorConsumerV2p(port)
    derived,_,_,_=derive_consumer_executor(
        source,native_executor,port,consumer,CallsiteObserver())
    integrated=derived(altered,fabric,*capacity,plan_type())
    summary=consumer.summary()
    receipts=consumer.consumer_journal()
    require(consumer.project_original_native_result(integrated)==native and
            port.summary()['negative_judgments']==2 and
            len(receipts)==2 and
            [item['response'] for item in receipts]==[-1,-1] and
            [item['actor'] for item in receipts]==['A','A'] and
            summary['actor_consumer_applied_credit']['A']==-2 and
            summary['actor_credit_register']['A']==-2 and
            summary['native_operator_updates']==0,
            'v2p real negative B actor-consumer application incorrectly attributed')
    return {'real_negative_B_judgments':2,'source_actor':'B',
            'consumer_target_actor':'A','applied_negative_receipts':2,
            'derived_actor_A_applied_credit':-2,
            'frozen_native_learning_observed':False}


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2o(previous,raw)
    root=root.resolve(strict=True)
    before_sources=source_pins(root)
    before_arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    case,fabric,plans=fixture_fn()
    original_hash=snapshot((case,fabric,plans))
    totals={regime:{'cells':0,'full_native_projection_equal':0,
                    'native_forward_equal':0,'native_feedback_equal':0,
                    'acked':0,'consumer_applied':0,'consumer_pending':0,
                    'actor_grants_pre_forward':0,
                    'consumer_native_tick_applications':0,
                    'consumer_tail_applications':0,
                    'consumer_extra_tail_ticks':0}
            for regime,_ in REGIMES}
    interventions={key:{'cells':0,'ack_count':0,'applied':0,
                          'backlog':0,'native_parity':0,'tail_ticks':0}
                   for key in INTERVENTIONS}
    cells=[]
    for i,(label,recipe) in enumerate(RECIPES):
        changed=build_workload(case,recipe)
        modes=[]
        for j,(mode,enabled,priority) in enumerate(ARMS):
            capacities={}
            for regime,capacity in REGIMES:
                prev=previous['paired_native_matrix'][i]['modes'][j][
                    'capacities'][regime]
                signed=prev['admission_modes']['strict_native_causal']
                amended=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
                         plans[2],plans[3])
                data=(changed,fabric,amended)
                digest=snapshot(data)
                native_box={}

                def capture_native(*args,**kwargs):
                    native_box['result']=native_executor(*args,**kwargs)
                    return native_box['result']

                native=_arm(capture_native,plan_type,changed,fabric,amended,
                    'v2p-native-'+regime,enabled,priority,digest,data)
                require(native['whole_result_sha256']==
                        prev['signed_v2n_native_sha256'],
                        'v2p independent frozen-native result SHA differs from signed v2o')
                projection,s,acks,applied,trace,integrated,counts=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,amended,
                    enabled,priority,digest,data,name=mode)
                native_result=native_box['result']
                whole=projection==native and integrated['projection']==native_result
                require(whole and integrated['result']['forward']==
                        native_result['forward'] and
                        integrated['result']['feedback']==native_result['feedback'] and
                        acks==signed['actor_credit_journal'] and
                        counts==signed['callsite_counts'] and
                        s['pre_forward_actor_grants']==
                            signed['summary']['pre_forward_actor_grants'] and
                        all(s[key]==value for key,value in signed['summary'].items()
                            if key!='schema') and
                        len(applied)==len(acks),
                        'v2p changed v2o native/ACK evidence at '
                        f'{i}/{j}/{regime}; parity={whole}; '
                        f'forward={integrated["result"]["forward"]==native_result["forward"]}; '
                        f'feedback={integrated["result"]["feedback"]==native_result["feedback"]}; '
                        f'ACK={acks==signed["actor_credit_journal"]}; '
                        f'counts={counts==signed["callsite_counts"]}; '
                        f'summary-diff={[k for k,v in signed["summary"].items() if k!="schema" and s[k]!=v]}')
                agg=totals[regime]
                agg['cells']+=1
                agg['full_native_projection_equal']+=int(whole)
                agg['native_forward_equal']+=int(
                    integrated['result']['forward']==native_result['forward'])
                agg['native_feedback_equal']+=int(
                    integrated['result']['feedback']==native_result['feedback'])
                agg['acked']+=len(acks)
                agg['consumer_applied']+=len(applied)
                agg['consumer_pending']+=s['actor_consumer_pending_ack_backlog']
                agg['actor_grants_pre_forward']+=s['pre_forward_actor_grants']
                agg['consumer_native_tick_applications']+=s[
                    'consumer_native_tick_applications']
                agg['consumer_tail_applications']+=s['consumer_tail_applications']
                agg['consumer_extra_tail_ticks']+=s['consumer_extra_tail_ticks']
                row={
                    'capacity':capacity,
                    'signed_v2o_native_sha256':prev['signed_v2n_native_sha256'],
                    'full_frozen_native_projection_equal':whole,
                    'strict_v2o_acks_exactly_equal':True,
                    'summary':s,'actor_credit_journal':acks,
                    'actor_consumer_receipts':applied,
                    'actor_consumer_tick_trace':trace,
                }
                if regime=='contended_capacity':
                    runs={}
                    for policy in INTERVENTIONS:
                        p,p_summary,p_acks,p_applied,p_trace,p_raw,_=_derived_arm(
                            source,native_executor,plan_type,changed,fabric,amended,
                            enabled,priority,digest,data,name=mode,policy=policy)
                        require(p==native and
                                p_raw['projection']==native_result and
                                p_acks==acks and
                                len(p_applied)+p_summary[
                                    'actor_consumer_pending_ack_backlog']==len(acks),
                                'v2p consumer quota changed native output or ACK custody')
                        counters=interventions[policy]
                        counters['cells']+=1
                        counters['ack_count']+=len(p_acks)
                        counters['applied']+=len(p_applied)
                        counters['backlog']+=p_summary[
                            'actor_consumer_pending_ack_backlog']
                        counters['native_parity']+=1
                        counters['tail_ticks']+=p_summary['consumer_extra_tail_ticks']
                        runs[policy]={
                            'applied':len(p_applied),
                            'pending_ack_backlog':p_summary[
                                'actor_consumer_pending_ack_backlog'],
                            'actor_applied_credit':p_summary[
                                'actor_consumer_applied_credit'],
                            'native_projection_equal':True,
                            'consumer_extra_tail_ticks':p_summary[
                                'consumer_extra_tail_ticks'],
                        }
                    row['bounded_consumer_interventions']=runs
                capacities[regime]=row
            modes.append({'mode':mode,'capacities':capacities})
        cells.append({'label':label,'recipe':[list(x) for x in recipe],
                      'modes':modes})
        require(snapshot((case,fabric,plans))==original_hash,
                'v2p native fixture mutated during ACK consumption matrix')
    negative=_negative_fixture(source,case,fabric,plans,native_executor,plan_type)
    require(all(v['cells']==45 and v['full_native_projection_equal']==45 and
                v['native_forward_equal']==45 and v['native_feedback_equal']==45 and
                v['acked']==v['consumer_applied']==156 and v['consumer_pending']==0 and
                v['actor_grants_pre_forward']>0 for v in totals.values()) and
            all(v['cells']==v['native_parity']==45 and v['ack_count']==156 for
                v in interventions.values()) and
            interventions['total_one']['applied']==45 and
            interventions['total_zero']['applied']==0 and
            interventions['throughput_zero']['applied']==0 and
            interventions['tail_off']['backlog']>0 and
            source_pins(root)==before_sources and
            read_pinned_sources(root)==before_arch and
            read_pinned_source(root)==source and
            snapshot((case,fabric,plans))==original_hash,
            'v2p causal native equality, backlog interventions or source pins drift')
    return {'paired_native_matrix':cells,
            'consumer_handoff_totals':totals,
            'bounded_consumer_intervention_totals':interventions,
            'real_negative_B_actor_consumer_fixture':negative,
            'new_native_runs':90,
            'new_normal_consumer_runs':90,
            'new_bounded_consumer_intervention_runs':180,
            'new_negative_fixture_native_derived_runs':2,
            'native_source_custody':True}


def build_report(previous,raw,result=None):
    validate_v2o(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['new_native_runs']==90 and
             result['new_normal_consumer_runs']==90 and
             result['new_bounded_consumer_intervention_runs']==180 and
             result['new_negative_fixture_native_derived_runs']==2 and
             all(v['cells']==45 for v in
                 result['bounded_consumer_intervention_totals'].values())),
            'v2p actor ACK consumer experiment incomplete')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('SOURCE_PINNED_DERIVED_ACTOR_ACK_CONSUMER_HANDOFF'
                       if result else 'SIGNED_V2O_PREDECESSOR_ONLY'),
        'reference_v2o_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked_in_this_run':bool(result),
        'new_native_runs':result['new_native_runs'] if result else 0,
        'new_normal_consumer_runs':result['new_normal_consumer_runs'] if result else 0,
        'new_bounded_consumer_intervention_runs':(
            result['new_bounded_consumer_intervention_runs'] if result else 0),
        'new_negative_fixture_native_derived_runs':(
            result['new_negative_fixture_native_derived_runs'] if result else 0),
        'consumer_handoff_totals':result['consumer_handoff_totals'] if result else None,
        'bounded_consumer_intervention_totals':(
            result['bounded_consumer_intervention_totals'] if result else None),
        'real_negative_B_actor_consumer_fixture':(
            result['real_negative_B_actor_consumer_fixture'] if result else None),
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'frozen_native_actor_consumption_proven':False,
        'frozen_native_learning_proven':False,
        'separate_consumer_PE_or_memory_spend_proven':False,
        'ACK_not_equivalent_to_actor_applied_credit':True,
        'native_operator_updates':0,
        'next_gate':
            'BLOCKED_FROZEN_NATIVE_ACTOR_INTAKE_AND_INDEPENDENT_CONSUMER_RESOURCE_POLICY',
        'claims_excluded':list(EXCLUSIONS),
    }
