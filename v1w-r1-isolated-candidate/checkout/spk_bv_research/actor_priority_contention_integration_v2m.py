"""BV v2m: source-pinned differential PE contention and actor-first causality."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from spk_backvalidation_v2.derived_native_fork_v2g import (
    CallsiteObserver,read_pinned_source,
)
from spk_backvalidation_v2.derived_receiver_port_v2h import ReceiverPortV2h
from spk_backvalidation_v2.derived_actor_credit_protocol_v2l import (
    ActorCreditPlanV2l,
)
from spk_backvalidation_v2.derived_actor_priority_v2m import (
    DerivedActorPriorityV2m,derive_priority_executor,
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

SCHEMA='spk-bv-pinned-derived-actor-forward-resource-priority/v2m'
STATUS='DERIVED_ACTOR_FIRST_CAUSAL_FORWARD_TIMING_CONTENTION_FUNCTIONAL_PARITY'
CONTRACT_STATUS='V2M_CONTRACT_ONLY_NATIVE_EXECUTION_PENDING'
PREDECESSOR_SHA='b77f257adc6cb6c888e6cef44e67d39e54bf328ed6e9ee4d434eb7eea3bdf3d7'
REGIMES=(('original_capacity',3),('contended_capacity',1))
NULLS=('loss','fault','cap_zero')
EXCLUSIONS=(
    'actor-first-is-a-derived-pre-forward-priority-policy-not-frozen-native',
    'forward-timing-difference-under-contention-is-intentional-not-whole-native-parity',
    'equal-final-states-and-terminal-payloads-are-observed-only-in-pinned-three-actor-corpus',
    'resource-only-projection-does-not-undo-forward-timing-caused-by-early-service',
    'pre-forward-control-cannot-interrupt-an-already-atomic-forward-batch',
    'service-priority-can-starve-forward-under-other-corpora-or-explicit-bounds',
    'semantic-credit-still-a-derived-journal-no-frozen-actor-intake-or-learning',
    'feedback-controls-not-authenticated-over-distributed-mesh-or-crypto',
    'no-physical-PE-energy-cost-theorem-hardware-N-node-or-cold-promotion',
)


def validate_v2l(previous,raw):
    require(type(previous) is dict and type(raw) is bytes and
            raw==canon(previous) and sha256(raw).hexdigest()==PREDECESSOR_SHA,
            'v2m v2l predecessor must be exact signed-off canonical report')
    totals=previous.get('actor_credit_totals') or {}
    variants=previous.get('intervention_totals') or {}
    require(previous.get('schema')=='spk-bv-pinned-derived-actor-credit-ack-protocol/v2l' and
            previous.get('status')==
                'DERIVED_ACTOR_CREDIT_EXACTLY_ONCE_RESOURCE_CAUSAL_NATIVE_PROJECTION' and
            previous.get('reference_v2k_sha256')==
                '774758196caeefd0d8ff629d8c4aca2d543b6e3dee8c2f2fda51eb236afe6ad4' and
            previous.get('full_native_projection_parity_cells')==45 and
            previous.get('v2k_integrated_derived_resource_parity_cells')==45 and
            totals.get('delivered_controls')==156 and
            totals.get('derived_actor_credit_ack_count')==156 and
            totals.get('derived_resource_grants_committed')==156 and
            totals.get('derived_inline_actor_grants')==140 and
            totals.get('derived_control_tail_grants')==16 and
            variants.get('cap_zero',{}).get('ack_count')==0 and
            variants.get('cap_zero',{}).get('policy_blocked')==156 and
            variants.get('cap_one',{}).get('ack_count')==90 and
            previous.get('real_frozen_native_actor_acknowledgments_proven') is False and
            previous.get('real_frozen_native_actor_credit_contract_proven') is False and
            previous.get('native_learning_proven') is False and
            previous.get('next_gate')==
                'BLOCKED_NATIVE_ACTOR_EVENT_PRIORITY_AND_CREDIT_CONSUMPTION_CONTRACT',
            'v2m inherited v2l evidence changed semantic/credit resource claims')
    cells=previous.get('paired_native_matrix')
    require(type(cells) is list and len(cells)==len(RECIPES),
            'v2m predecessor missing 15 stable original workloads')
    for (label,recipe),row in zip(RECIPES,cells):
        require(row.get('label')==label and
                row.get('recipe')==[list(x) for x in recipe] and
                [mode.get('mode') for mode in row.get('modes',[])]==
                    [arm[0] for arm in ARMS] and
                all(mode.get('exact_native_full_projection') is True and
                    mode.get('v2k_derived_resource_ledger_equal') is True and
                    len(mode.get('whole_original_native_sha256',''))==64
                    for mode in row['modes']),
                'v2m v2l historical native projection or recipe signature drift')
    return True


def _payload(forward):
    return {
        'state':forward['states'],
        'processed_events':forward['processed_events'],
        'processed_batches':forward['processed_batches'],
        'terminal_multiset':sorted(Counter(
            (x['node_id'],x['channel']) for x in forward['terminal']).items()),
        'emission_multiset':sorted(Counter(
            (x['node_id'],x['channel']) for x in forward['emissions']).items()),
    }


def _derived_arm(source,native_executor,plan_type,changed,fabric,plans,
                 enabled,priority,digest,data,*,actor_priority,policy='normal'):
    port_opts={}
    credit_plan=ActorCreditPlanV2l()
    if policy=='loss':
        port_opts['accept']=lambda _item:False
    elif policy=='fault':
        def failure(_item):
            raise RuntimeError('bounded receiver callback failure')
        port_opts['accept']=failure
    elif policy=='cap_zero':
        credit_plan=ActorCreditPlanV2l(max_abs_credit=0)
    else:
        require(policy=='normal','v2m unknown zero-control intervention')
    port=ReceiverPortV2h(**port_opts)
    service=DerivedActorPriorityV2m(
        port,priority=actor_priority,credit_plan=credit_plan)
    observer=CallsiteObserver()
    derived,_,anchors,resource=derive_priority_executor(
        source,native_executor,port,service,observer)
    results={}

    def run_and_project(*args,**kwargs):
        integrated=derived(*args,**kwargs)
        resource_only=service.project_original_native_result(integrated)
        results['integrated']=integrated
        results['cost_projection']=resource_only
        return resource_only

    projected=_arm(run_and_project,plan_type,changed,fabric,plans,
                   f'v2m-{actor_priority}-{policy}',enabled,priority,digest,data)
    summary=service.summary()
    probes=service.priority_probes()
    journal=service.credit_journal()
    feedback=port.summary()
    require(anchors==(('batch',194),('clock',125),
                      ('emission',217),('ingress',136)) and
            resource==(158,296,307) and
            not observer.overflow and not observer.sink_failed and
            summary['actor_event_priority']==actor_priority and
            summary['derived_resource_grants_committed']==len(journal)==
                summary['derived_actor_credit_ack_count'] and
            summary['derived_resource_grants_committed']+
                summary['unconsumed_delivered_controls']==
                    summary['delivered_controls'] and
            summary['delivered_controls']==feedback['control_delivered'] and
            summary['within_original_native_plan_capacity'] and
            summary['absence_certificates']==0 and
            summary['native_operator_updates']==0 and
            summary['frozen_native_event_priority_policy_modified'] is False and
            summary['frozen_actor_state_changed'] is False and
            summary['frozen_actor_credit_contract_proven'] is False and
            results['integrated']['forward']==results['cost_projection']['forward'] and
            results['integrated']['feedback']==results['cost_projection']['feedback'] and
            len(probes)==summary['native_original_timeline_rows'],
            'v2m priority causality or pre-forward resource custody drift')
    if actor_priority=='forward-first':
        require(summary['pre_forward_actor_grants']==0 and
                summary['ready_forward_batches_blocked_by_pre_grants']==0,
                'v2m forward-first applied pre-forward credit')
    if policy in ('loss','fault','cap_zero'):
        require(len(journal)==0 and
                summary['pre_forward_actor_grants']==0 and
                summary['derived_resource_grants_committed']==0 and
                summary['absence_certificates']==0,
                'v2m loss, callback fault or zero credit created actor grants')
    return projected,summary,feedback,observer.counts(),probes,journal,results


def experiment(previous,raw,*,root:Path,fixture_fn,native_executor,plan_type):
    validate_v2l(previous,raw)
    root=root.resolve(strict=True)
    before_pins=source_pins(root)
    before_arch=read_pinned_sources(root)
    runtime_modules_bound(root,native_executor,fixture_fn,plan_type)
    source=read_pinned_source(root)
    original=fixture_fn()
    case,fabric,plans=original
    original_snapshot=snapshot(original)
    rows=[]
    totals={regime:{
        'source_backed_cells':0,
        'forward_first_full_original_native_parity':0,
        'forward_first_v2l_journal_parity':0,
        'actor_first_full_original_native_parity':0,
        'actor_first_changed_forward_timing':0,
        'actor_first_terminal_payload_parity':0,
        'actor_first_final_state_parity':0,
        'actor_first_processed_event_and_batch_parity':0,
        'actor_first_pre_forward_grants':0,
        'actor_first_ready_forward_PE_blocked':0,
        'actor_first_acks':0,
        'loss_full_native_parity':0,
        'fault_full_native_parity':0,
        'cap_zero_full_native_parity':0,
    } for regime,_ in REGIMES}
    for label,recipe in RECIPES:
        changed=build_workload(case,recipe)
        modes=[]
        for (mode,enabled,priority),historic in zip(
                ARMS,previous['paired_native_matrix'][len(rows)]['modes']):
            paired={}
            for regime,capacity in REGIMES:
                regime_plans=(plans[0],replace(plans[1],
                    fabric_slots_per_tick=capacity),plans[2],plans[3])
                data=(changed,fabric,tuple(regime_plans))
                digest=snapshot(data)
                captured={}

                def original_and_capture(*args,**kwargs):
                    result=native_executor(*args,**kwargs)
                    captured['native']=result
                    return result

                native=_arm(original_and_capture,plan_type,changed,fabric,
                    regime_plans,f'v2m-native/{regime}',enabled,priority,digest,data)
                if regime=='original_capacity':
                    require(native['whole_result_sha256']==
                            historic['whole_original_native_sha256'],
                            'v2m original native base cell does not equal v2l')
                f,fs,fp,fc,_,fj,fr=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,regime_plans,
                    enabled,priority,digest,data,actor_priority='forward-first')
                require(f==native and
                        fr['cost_projection']==captured['native'] and
                        fc==historic['callsite_counts'] and
                        (regime!='original_capacity' or
                         (fj==historic['actor_credit_journal'] and
                          fs['actor_credit_chain_roots']==
                          historic['actor_credit_summary']['actor_credit_chain_roots'])),
                        'v2m forward-first failed original or v2l actor credit parity')
                a,actor,actor_port,ac,probes,acks,ar=_derived_arm(
                    source,native_executor,plan_type,changed,fabric,regime_plans,
                    enabled,priority,digest,data,actor_priority='actor-first')
                require(actor['derived_resource_grants_committed']==len(acks) and
                        actor['pre_forward_actor_grants']>0 and
                        actor['derived_inline_actor_grants']==
                            actor['pre_forward_actor_grants'] and
                        ac==historic['callsite_counts'] and
                        actor_port['absence_certificates']==0 and
                        not actor['frozen_native_actor_intake_observed'] and
                        actor['native_learning_proven'] is False,
                        'v2m actor-first grants do not respect prior native causal credit')
                original_forward=captured['native']['forward']
                changed_forward=ar['integrated']['forward']
                functional=_payload(original_forward)==_payload(changed_forward)
                changed_timing=changed_forward!=original_forward
                same_state=changed_forward['states']==original_forward['states']
                terminals=Counter((x['node_id'],x['channel'])
                                  for x in original_forward['terminal'])==Counter(
                                  (x['node_id'],x['channel'])
                                  for x in changed_forward['terminal'])
                events_equal=(changed_forward['processed_events']==
                              original_forward['processed_events'] and
                              changed_forward['processed_batches']==
                              original_forward['processed_batches'])
                blocked=actor['ready_forward_batches_blocked_by_pre_grants']
                require(functional and same_state and terminals and events_equal,
                        'v2m resource priority changed terminal payload/state in pinned corpus')
                if regime=='contended_capacity':
                    require(changed_timing and a!=native and blocked>0 and
                            actor['pre_forward_actor_grants']>0,
                            'v2m contended actor-first lacks causal forward timing witness')
                null={}
                if regime=='contended_capacity':
                    for policy in NULLS:
                        negative,neg_summary,neg_port,neg_counts,_,_,neg_raw=_derived_arm(
                            source,native_executor,plan_type,changed,fabric,regime_plans,
                            enabled,priority,digest,data,
                            actor_priority='actor-first',policy=policy)
                        require(negative==native and
                                neg_raw['cost_projection']==captured['native'] and
                                neg_counts==historic['callsite_counts'],
                                'v2m negative causal intervention did not restore native result')
                        totals[regime][policy+'_full_native_parity']+=1
                        null[policy]={
                            'exact_full_native_result':True,
                            'pre_actor_grants':neg_summary['pre_forward_actor_grants'],
                            'delivered':neg_summary['delivered_controls'],
                            'acks':neg_summary['derived_actor_credit_ack_count'],
                            'lost':neg_port['lost'],'fault_lost':neg_port['fault_lost'],
                        }
                agg=totals[regime]
                agg['source_backed_cells']+=1
                agg['forward_first_full_original_native_parity']+=1
                agg['forward_first_v2l_journal_parity']+=int(
                    regime=='original_capacity' and
                    fj==historic['actor_credit_journal'])
                agg['actor_first_full_original_native_parity']+=int(a==native)
                agg['actor_first_changed_forward_timing']+=int(changed_timing)
                agg['actor_first_terminal_payload_parity']+=int(terminals)
                agg['actor_first_final_state_parity']+=int(same_state)
                agg['actor_first_processed_event_and_batch_parity']+=int(events_equal)
                agg['actor_first_pre_forward_grants']+=actor['pre_forward_actor_grants']
                agg['actor_first_ready_forward_PE_blocked']+=blocked
                agg['actor_first_acks']+=len(acks)
                paired[regime]={
                    'capacity':capacity,
                    'original_native_sha256':native['whole_result_sha256'],
                    'forward_first_exact_native_projection':True,
                    'forward_first_actor_acks':len(fj),
                    'actor_first_original_native_full_projection_equal':a==native,
                    'actor_first_forward_timing_changed':changed_timing,
                    'actor_first_terminal_payload_same':terminals,
                    'actor_first_final_states_same':same_state,
                    'actor_first_forward_event_and_batch_counts_same':events_equal,
                    'actor_first_ready_forward_PE_blocks':blocked,
                    'actor_first_summary':actor,
                    'actor_first_priority_probes':probes,
                    'actor_first_credit_journal':acks,
                    'actor_first_terminal_ticks':[
                        x['timestamp'] for x in changed_forward['terminal']],
                    'frozen_native_terminal_ticks':[
                        x['timestamp'] for x in original_forward['terminal']],
                    'null_interventions':null,
                }
            modes.append({'mode':mode,'capacities':paired})
        rows.append({'label':label,'recipe':[list(x) for x in recipe],
                     'modes':modes})
        require(snapshot(original)==original_snapshot,
                'v2m source native fixture was modified during priority replay')
    # A separate genuine negative receiver-B cell is replayed under tight
    # PE contention: negative semantic credit must remain actor-addressed,
    # independent of whether it is applied before forward batches.
    block=(('ACC',(1,0)),('CMP',100),('EMIT',7),('RESET',0))
    negative=replace(case,nodes=tuple(
        replace(node,instructions=block) if node.node_id=='B' else node
        for node in case.nodes))
    low_plans=(plans[0],replace(plans[1],fabric_slots_per_tick=1),plans[2],plans[3])
    neg_data=(negative,fabric,tuple(low_plans))
    neg_hash=snapshot(neg_data)
    nneg=_arm(native_executor,plan_type,negative,fabric,low_plans,
              'v2m-real-negative-native',True,'forward-first',neg_hash,neg_data)
    fn,_,_,_,_,_,_= _derived_arm(
        source,native_executor,plan_type,negative,fabric,low_plans,
        True,'forward-first',neg_hash,neg_data,actor_priority='forward-first')
    an,ans,anp,_,_,anj,_=_derived_arm(
        source,native_executor,plan_type,negative,fabric,low_plans,
        True,'forward-first',neg_hash,neg_data,actor_priority='actor-first')
    require(fn==nneg and anp['negative_judgments']==2 and
            [ack['response'] for ack in anj]==[-1,-1] and
            ans['actor_credit_register']['A']==-2 and
            ans['derived_actor_credit_ack_count']==2 and
            an['metrics']['forward_occurrences']==nneg['metrics']['forward_occurrences'],
            'v2m pre-priority negative-B causal credit and forward count drift')
    tight=totals['contended_capacity']
    require(tight['source_backed_cells']==45 and
            tight['forward_first_full_original_native_parity']==45 and
            tight['actor_first_changed_forward_timing']==45 and
            tight['actor_first_ready_forward_PE_blocked']>0 and
            tight['actor_first_terminal_payload_parity']==45 and
            tight['actor_first_final_state_parity']==45 and
            all(tight[k]==45 for k in (
                'loss_full_native_parity','fault_full_native_parity',
                'cap_zero_full_native_parity')) and
            totals['original_capacity']['forward_first_v2l_journal_parity']==45,
            'v2m differential priority/functional and negative controls incomplete')
    require(source_pins(root)==before_pins and
            read_pinned_sources(root)==before_arch and
            read_pinned_source(root)==source and
            snapshot(original)==original_snapshot,
            'v2m runtime source binding changed across priority interventions')
    return {
        'paired_native_matrix':rows,'priority_contention_totals':totals,
        'negative_fixture':{
            'real_negative_B_judgments':2,
            'actor_first_actor_A_derived_credit':-2,
            'resource_granted_negative_actor_acks':2,
            'frozen_native_learning_observed':False,
        },
        'native_original_runs':91,
        'derived_forward_first_runs':91,
        'derived_actor_first_runs':91,
        'derived_null_intervention_runs':135,
        'native_source_custody':True,
    }


def build_report(previous,raw,result=None):
    validate_v2l(previous,raw)
    require(result is None or
            (result['native_source_custody'] and
             result['native_original_runs']==91 and
             result['derived_forward_first_runs']==91 and
             result['derived_actor_first_runs']==91 and
             result['derived_null_intervention_runs']==135 and
             all(x['source_backed_cells']==45
                 for x in result['priority_contention_totals'].values())),
            'v2m priority differential lacks full causal/pinned matrix')
    return {
        'schema':SCHEMA,'status':STATUS if result else CONTRACT_STATUS,
        'source_kind':('PINNED_DERIVED_PRE_FORWARD_ACTOR_PRIORITY_CONTENTION'
                       if result else 'V2L_PREDECESSOR_ONLY_CONTRACT'),
        'reference_v2l_sha256':sha256(raw).hexdigest(),
        'source_pins_rechecked_in_this_run':bool(result),
        'new_original_native_runs':result['native_original_runs'] if result else 0,
        'new_derived_forward_first_runs':
            result['derived_forward_first_runs'] if result else 0,
        'new_derived_actor_first_runs':
            result['derived_actor_first_runs'] if result else 0,
        'new_derived_causal_null_runs':
            result['derived_null_intervention_runs'] if result else 0,
        'priority_contention_totals':
            result['priority_contention_totals'] if result else None,
        'paired_native_matrix':result['paired_native_matrix'] if result else None,
        'negative_native_fixture':result['negative_fixture'] if result else None,
        'native_forward_timing_full_parity_under_actor_first_claimed':False,
        'derived_resource_counter_commit_real':bool(result),
        'frozen_native_actor_service_or_learning_proven':False,
        'native_operator_updates':0,
        'next_gate':'BLOCKED_FROZEN_NATIVE_ACTOR_PRIORITY_ADMISSION_FAIRNESS_AND_CREDIT_CONSUMPTION',
        'claims_excluded':list(EXCLUSIONS),
    }
