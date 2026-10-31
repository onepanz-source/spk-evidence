"""BV v2q: signed v2p parity and independent derived actor consumer PE/RAM."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import CallsiteObserver,read_pinned_source
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_resource_consumer_v2q import (
    ConsumerResourcePlanV2q,DerivedActorResourceConsumerV2q,
    derive_resource_consumer_executor,
)
from spk_backvalidation_v2.derived_actor_consumer_v2p import ActorConsumerPlanV2p
from spk_bv_research.actor_priority_contention_integration_v2m import REGIMES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import require,snapshot,source_pins,runtime_modules_bound
from spk_bv_research.coincident_admission_discrimination_v2e import RECIPES,build_workload
from spk_bv_research.link_pressure_v0u import ARMS,_arm
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources

SCHEMA='spk-bv-pinned-independent-actor-consumer-resource-charging/v2q'
STATUS='DERIVED_ACTOR_CONSUMER_INDEPENDENT_PE_MEMORY_CHARGED_NATIVE_PROJECTION'
CONTRACT_STATUS='V2Q_SIGNED_V2P_PREDECESSOR_ONLY_NO_NATIVE_RESOURCE_CONTRACT'
PREDECESSOR_SHA='1c3f2b0010f6a0470ac2b5be021838b8e1992e85760e367a532d5e5dfe8f9ef3'
INTERVENTIONS=('total_one','charge_zero','tail_off','memory_zero')
EXCLUSIONS=(
    'resource-grants-are-in-a-separately-source-compiled-derived-scheduler-only',
    'one-PE-and-two-memory-units-is-an-abstract-testable-cost-not-calibrated-hardware',
    'frozen-native-event-admission-priority-and-actor-intake-never-changed',
    'positive-or-negative-applied-credit-is-derived-only-not-a-learning-update',
    'consumer-independent-PE-charge-happens-after-original-native-work-per-tick',
    'native-projection-is-proven-for-two-PE-capacities-and-pinned-15-by-3-cells',
    'ACK-backlog-from-resource-starvation-is-neither-negative-credit-nor-silence-proof',
    'hash-chains-are-in-process-integrity-checks-not-authentication',
    'arbitrary-deadline-general-liveness-and-forward-priority-contract-unproven',
    'bounded-three-node-research-no-N-node-or-cold-promotion',
)


def validate_v2p(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            canon(previous)==raw and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2q signed canonical v2p predecessor bytes SHA drift')
    require(previous.get('schema')==
            'spk-bv-pinned-derived-actor-ack-consumer-handoff/v2p' and
            previous.get('status')==
            'DERIVED_ACTOR_CONSUMER_ACK_HANDOFF_EXACTLY_ONCE_NATIVE_PARITY' and
            previous.get('reference_v2o_sha256')==
                '778a38f312d1e5403f0106015214cec924fe4f284e4cdbf107422f8b76c0716c' and
            previous.get('new_native_runs')==90 and
            previous.get('new_normal_consumer_runs')==90 and
            previous.get('new_bounded_consumer_intervention_runs')==180 and
            previous.get('new_negative_fixture_native_derived_runs')==2 and
            previous.get('frozen_native_actor_consumption_proven') is False and
            previous.get('frozen_native_learning_proven') is False and
            previous.get('separate_consumer_PE_or_memory_spend_proven') is False and
            previous.get('ACK_not_equivalent_to_actor_applied_credit') is True and
            previous.get('native_operator_updates')==0 and
            previous.get('next_gate')==
                'BLOCKED_FROZEN_NATIVE_ACTOR_INTAKE_AND_INDEPENDENT_CONSUMER_RESOURCE_POLICY',
            'v2q signed v2p consumer scientific boundary drift')
    totals=previous.get('consumer_handoff_totals') or {}
    require(all(totals.get(regime,{}).get('cells')==45 and
                totals[regime]['full_native_projection_equal']==45 and
                totals[regime]['acked']==156 and
                totals[regime]['consumer_applied']==156 and
                totals[regime]['consumer_pending']==0
                for regime,_ in REGIMES) and
            all((previous.get('bounded_consumer_intervention_totals') or {}).get(
                policy,{}).get('native_parity')==45
                for policy in ('total_one','tail_off')) and
            previous.get('real_negative_B_actor_consumer_fixture',{}).get(
                'derived_actor_A_applied_credit')==-2,
            'v2q signed v2p actor-consumer full parity or negative fixture drift')
    rows=previous.get('paired_native_matrix')
    require(type(rows) is list and len(rows)==len(RECIPES),
            'v2q signed v2p complete source matrix missing')
    for (label,recipe),row in zip(RECIPES,rows):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [m.get('mode') for m in row.get('modes',[])]==
                    [arm[0] for arm in ARMS],
                'v2q signed v2p workloads/mode ordering drift')
        for mode in row['modes']:
            for regime,capacity in REGIMES:
                cell=mode.get('capacities',{}).get(regime,{})
                summary=cell.get('summary') or {}
                require(cell.get('capacity')==capacity and
                        len(cell.get('signed_v2o_native_sha256',''))==64 and
                        cell.get('full_frozen_native_projection_equal') is True and
                        cell.get('strict_v2o_acks_exactly_equal') is True and
                        summary.get('actor_consumer_applications')==
                            len(cell.get('actor_consumer_receipts',[])) and
                        summary.get('derived_actor_credit_ack_count')==
                            len(cell.get('actor_credit_journal',[])) and
                        summary.get('consumer_extra_PE_or_memory_budget_charged') is False,
                        'v2q signed v2p source-backed actor/ACK cell drift')
    return True


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,name,policy='normal'):
    resource_plan=ConsumerResourcePlanV2q()
    if policy=='total_one':
        resource_plan=replace(resource_plan,max_total_consumer_charges=1)
    elif policy=='charge_zero':
        resource_plan=replace(resource_plan,max_total_consumer_charges=0)
    elif policy=='tail_off':
        resource_plan=replace(resource_plan,max_resource_tail_ticks=0)
    elif policy=='memory_zero':
        resource_plan=replace(resource_plan,max_consumer_memory_per_tick=0)
    else:
        require(policy=='normal','v2q invalid bounded resource intervention')
    port=ReceiverPortV2h()
    consumer=DerivedActorResourceConsumerV2q(port,resource_plan=resource_plan)
    observer=CallsiteObserver()
    derived,_,semantic,resource=derive_resource_consumer_executor(
        source,native_executor,port,consumer,observer)
    raw={}

    def run(*args,**kwargs):
        raw['result']=derived(*args,**kwargs)
        raw['projection']=consumer.project_original_native_result(raw['result'])
        return raw['projection']

    projected=_arm(run,plan_type,changed,fabric,plans,
                   f'v2q-{name}-{policy}',enabled,priority,digest,data)
    summary=consumer.summary()
    ACKs=consumer.credit_journal()
    applied=consumer.consumer_journal()
    charges=consumer.resource_charge_journal()
    trace=consumer.resource_charge_trace()
    require(semantic==(('batch',194),('clock',125),
                       ('emission',217),('ingress',136)) and
            resource==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            observer.counts().get('_admit')==1 and
            observer.counts().get('_admit_plan')==1 and
            summary['protect_ready_forward'] is True and
            summary['protect_ready_native_feedback'] is True and
            summary['pregrants_during_native_causal_veto']==0 and
            summary['derived_actor_credit_ack_count']==len(ACKs)==
                summary['derived_resource_grants_committed'] and
            summary['delivered_controls']==len(ACKs) and
            summary['actor_consumer_applications']==len(applied)==len(charges) and
            summary['derived_independent_consumer_resource_charges']==len(charges) and
            summary['derived_independent_consumer_PE_units']==len(charges) and
            summary['derived_independent_consumer_memory_units']==2*len(charges) and
            summary['actor_consumer_pending_ack_backlog']==len(ACKs)-len(charges) and
            summary['within_original_native_plan_capacity'] and
            summary['independent_consumer_source_budget_verified'] and
            summary['consumer_extra_PE_or_memory_budget_charged'] is True and
            summary['consumer_consumption_borrows_existing_ACK_charge'] is False and
            summary['native_operator_updates']==0 and
            summary['absence_certificates']==0 and
            summary['frozen_actor_state_changed'] is False and
            summary['native_learning_proven'] is False and
            len(trace)==summary['native_original_timeline_rows']+
                summary['new_consumer_only_resource_timeline_rows'] and
            len(raw['result']['resources']['timeline'])==
                summary['native_original_timeline_rows']+
                summary['new_derived_control_only_timeline_rows']+
                summary['new_consumer_only_resource_timeline_rows'],
            'v2q derived resource paid ACK consumption or native parity drift')
    require(policy!='normal' or len(applied)==len(ACKs),
            'v2q bounded default resource capacity cannot settle source ACKs')
    require(policy not in ('charge_zero','memory_zero') or
            (not applied and summary['new_consumer_only_resource_timeline_rows']==0),
            'v2q refused memory/PE consumer policy fabricated resources')
    return projected,summary,ACKs,applied,charges,trace,raw,observer.counts()


def _negative_fixture(source,case,fabric,plans,native_executor,plan_type):
    code=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    changed=replace(case,nodes=tuple(replace(node,instructions=code)
                if node.node_id=='B' else node for node in case.nodes))
    reduced=(plans[0],replace(plans[1],fabric_slots_per_tick=1),
             plans[2],plans[3])
    native=native_executor(changed,fabric,*reduced,plan_type())
    port=ReceiverPortV2h()
    consumer=DerivedActorResourceConsumerV2q(port)
    compiled,_,_,_=derive_resource_consumer_executor(
        source,native_executor,port,consumer,CallsiteObserver())
    result=compiled(changed,fabric,*reduced,plan_type())
    receipts=consumer.consumer_journal()
    s=consumer.summary()
    require(consumer.project_original_native_result(result)==native and
            port.summary()['negative_judgments']==2 and
            [receipt['response'] for receipt in receipts]==[-1,-1] and
            [receipt['actor'] for receipt in receipts]==['A','A'] and
            s['actor_consumer_applied_credit']['A']==-2 and
            s['actor_credit_register']['A']==-2 and
            s['derived_independent_consumer_resource_charges']==2 and
            s['derived_independent_consumer_memory_units']==4,
            'v2q source-negative B research actor credit/memory charge corrupted')
    return {'real_negative_B_judgments':2,'applied_to_actor':'A',
            'derived_actor_A_credit':-2,'independent_PE_charge_units':2,
            'independent_memory_charge_units':4,
            'frozen_native_actor_learning_observed':False}


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2p(previous,raw)
    root=root.resolve(strict=True)
    source_start=source_pins(root)
    arch_start=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    case,fabric,plans=fixture_fn()
    original_hash=snapshot((case,fabric,plans))
    totals={regime:{'cells':0,'native_projection':0,'forward_equal':0,
                    'feedback_equal':0,'ACKs':0,'charged_consumptions':0,
                    'applied_pending':0,'independent_PE_units':0,
                    'independent_memory_units':0,'native_tick_paid':0,
                    'consumer_tail_paid':0,'extra_consumer_timeline_rows':0,
                    'resource_capacity_rejections':0}
            for regime,_ in REGIMES}
    interventions={p:{'cells':0,'native_projection':0,'ACKs':0,
                       'paid_applications':0,'pending_backlog':0,
                       'consumer_extra_rows':0}
                   for p in INTERVENTIONS}
    cells=[]
    for i,(label,recipe) in enumerate(RECIPES):
        changed=build_workload(case,recipe)
        modes=[]
        for j,(mode,enabled,priority) in enumerate(ARMS):
            capacities={}
            for regime,capacity in REGIMES:
                previous_cell=previous['paired_native_matrix'][i]['modes'][j][
                    'capacities'][regime]
                amended=(plans[0],replace(plans[1],fabric_slots_per_tick=capacity),
                         plans[2],plans[3])
                data=(changed,fabric,amended)
                digest=snapshot(data)
                box={}

                def capture(*args,**kwargs):
                    box['original']=native_executor(*args,**kwargs)
                    return box['original']

                native=_arm(capture,plan_type,changed,fabric,amended,
                    'v2q-native-'+regime,enabled,priority,digest,data)
                require(native['whole_result_sha256']==previous_cell[
                    'signed_v2o_native_sha256'],
                    'v2q independent original native differs from signed v2p')
                projection,s,acks,applied,charges,trace,raw_result,counts=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,amended,
                    enabled,priority,digest,data,name=mode)
                whole=projection==native and raw_result['projection']==box['original']
                require(whole and raw_result['result']['forward']==
                        box['original']['forward'] and
                        raw_result['result']['feedback']==box['original']['feedback'] and
                        acks==previous_cell['actor_credit_journal'] and
                        s['derived_actor_credit_ack_count']==
                            previous_cell['summary']['derived_actor_credit_ack_count'] and
                        s['pre_forward_actor_grants']==
                            previous_cell['summary']['pre_forward_actor_grants'] and
                        s['actor_consumer_applied_credit']==
                            previous_cell['summary']['actor_consumer_applied_credit'] and
                        len(applied)==len(previous_cell['actor_consumer_receipts']) and
                        len(charges)==len(applied),
                        'v2q independently charged actor consumption lost v2p ACK/native parity')
                agg=totals[regime]
                agg['cells']+=1
                agg['native_projection']+=int(whole)
                agg['forward_equal']+=int(raw_result['result']['forward']==
                                          box['original']['forward'])
                agg['feedback_equal']+=int(raw_result['result']['feedback']==
                                           box['original']['feedback'])
                agg['ACKs']+=len(acks)
                agg['charged_consumptions']+=len(charges)
                agg['applied_pending']+=s['actor_consumer_pending_ack_backlog']
                agg['independent_PE_units']+=s['derived_independent_consumer_PE_units']
                agg['independent_memory_units']+=s[
                    'derived_independent_consumer_memory_units']
                agg['native_tick_paid']+=s['consumer_independent_inline_charges']
                agg['consumer_tail_paid']+=s['consumer_independent_tail_charges']
                agg['extra_consumer_timeline_rows']+=s[
                    'new_consumer_only_resource_timeline_rows']
                agg['resource_capacity_rejections']+=s[
                    'consumer_resource_capacity_rejections']
                cell={
                    'capacity':capacity,
                    'signed_v2p_native_sha256':previous_cell[
                        'signed_v2o_native_sha256'],
                    'exact_full_native_projection':True,
                    'v2p_ACK_journal_equal':True,
                    'summary':s,
                    'ACK_journal':acks,
                    'charged_actor_consumptions':applied,
                    'independent_PE_memory_charge_journal':charges,
                    'independent_resource_timeline':trace,
                }
                if regime=='contended_capacity':
                    interventions_cells={}
                    for policy in INTERVENTIONS:
                        p,inter,inter_acks,inter_applied,inter_charges,_,inter_raw,_=_derived_arm(
                            source,native_executor,plan_type,changed,fabric,amended,
                            enabled,priority,digest,data,name=mode,policy=policy)
                        require(p==native and inter_raw['projection']==box['original'] and
                                inter_acks==acks and
                                len(inter_charges)==len(inter_applied) and
                                len(inter_charges)+inter[
                                    'actor_consumer_pending_ack_backlog']==len(acks),
                                'v2q independent consumer intervention changed source ACK/native')
                        counter=interventions[policy]
                        counter['cells']+=1
                        counter['native_projection']+=1
                        counter['ACKs']+=len(inter_acks)
                        counter['paid_applications']+=len(inter_charges)
                        counter['pending_backlog']+=inter[
                            'actor_consumer_pending_ack_backlog']
                        counter['consumer_extra_rows']+=inter[
                            'new_consumer_only_resource_timeline_rows']
                        interventions_cells[policy]={
                            'charged':len(inter_charges),
                            'pending_backlog':inter[
                                'actor_consumer_pending_ack_backlog'],
                            'independent_resource_timeline_rows':inter[
                                'new_consumer_only_resource_timeline_rows'],
                            'native_parity':True,
                        }
                    cell['resource_interventions']=interventions_cells
                capacities[regime]=cell
            modes.append({'mode':mode,'capacities':capacities})
        cells.append({'label':label,'recipe':[list(x) for x in recipe],
                      'modes':modes})
        require(snapshot((case,fabric,plans))==original_hash,
                'v2q source-native input fixture mutated during resource replays')
    negative=_negative_fixture(source,case,fabric,plans,native_executor,plan_type)
    require(all(t['cells']==t['native_projection']==t['forward_equal']==
                t['feedback_equal']==45 and t['ACKs']==t['charged_consumptions']==
                t['independent_PE_units']==156 and
                t['independent_memory_units']==312 and t['applied_pending']==0
                for t in totals.values()) and
            totals['contended_capacity']['resource_capacity_rejections']>0 and
            all(t['cells']==t['native_projection']==45 and t['ACKs']==156
                for t in interventions.values()) and
            interventions['total_one']['paid_applications']==45 and
            interventions['charge_zero']['paid_applications']==0 and
            interventions['memory_zero']['paid_applications']==0 and
            interventions['tail_off']['pending_backlog']>0 and
            source_pins(root)==source_start and
            read_pinned_sources(root)==arch_start and
            read_pinned_source(root)==source and
            snapshot((case,fabric,plans))==original_hash,
            'v2q independent paid actor service parity/backpressure/source custody drift')
    return {
        'paired_native_matrix':cells,
        'independently_charged_consumer_totals':totals,
        'resource_backpressure_intervention_totals':interventions,
        'real_negative_B_resource_fixture':negative,
        'independent_native_runs':90,
        'resource_charged_normal_runs':90,
        'resource_backpressure_intervention_runs':180,
        'negative_fixture_runs':2,
        'native_source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2p(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['independent_native_runs']==90 and
             result['resource_charged_normal_runs']==90 and
             result['resource_backpressure_intervention_runs']==180 and
             result['negative_fixture_runs']==2 and
             all(v['cells']==45 for v in
                 result['resource_backpressure_intervention_totals'].values())),
            'v2q independent resource causal matrix incomplete')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('SOURCE_PINNED_DERIVED_INDEPENDENT_ACTOR_CONSUMER_RESOURCE'
                       if result else 'SIGNED_V2P_PREDECESSOR_ONLY'),
        'reference_v2p_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked':bool(result),
        'new_native_runs':result['independent_native_runs'] if result else 0,
        'new_resource_charged_normal_runs':(
            result['resource_charged_normal_runs'] if result else 0),
        'new_resource_backpressure_intervention_runs':(
            result['resource_backpressure_intervention_runs'] if result else 0),
        'new_negative_fixture_runs':result['negative_fixture_runs'] if result else 0,
        'independently_charged_consumer_totals':(
            result['independently_charged_consumer_totals'] if result else None),
        'resource_backpressure_intervention_totals':(
            result['resource_backpressure_intervention_totals'] if result else None),
        'real_negative_B_resource_fixture':(
            result['real_negative_B_resource_fixture'] if result else None),
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'frozen_native_actor_resource_consumption_proven':False,
        'frozen_native_actor_learning_proven':False,
        'physical_hardware_consumer_cost_calibrated':False,
        'native_operator_updates':0,
        'next_gate':
            'BLOCKED_FROZEN_NATIVE_ACTOR_INTAKE_AND_CONCURRENT_CONSUMER_FORWARD_ARBITRATION',
        'claims_excluded':list(EXCLUSIONS),
    }
