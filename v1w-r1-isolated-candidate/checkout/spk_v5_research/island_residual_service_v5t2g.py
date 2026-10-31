"""V5-T2g: bounded *shadow* resource arbiter grounded in original BV-v0e traces.

A decision witness, even for silence, is minted by the shadow host (T2f).
Only capacity left after a fully executed, unchanged BV-v0e source trace may
serve the semantic control route. This is a counterfactual residual-capacity
replay, NOT integration into v0e, and NOT a native service grant.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from spk_v5_research.island_objective_v5t1 import CANDIDATES, digest
from spk_v5_research.island_endogenous_demand_v5t2c import DemandEpisode
from spk_v5_research.island_decision_reward_v5t2f import (
    STAGES, STAGE_OFFSET, MEM_CHARGE, TRANSIT, AdmissionError,
    witnessed_decision, verify_witness,
)
from spk_v5_research.island_bv_resource_bridge_v5t2e import source_plan
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e

SCHEMA = 'spk-v5-t2g-source-grounded-residual-island-service/research-v0'
STAGE_PE = ('PE0','PE0','PE1','PE2','PE2','PE1','PE0')
STAGE_DOMAIN = ('P','E','E','O','E','E','S')


@dataclass(frozen=True)
class ResidualPlan:
    source_mode: str = 'forward_first'
    global_pe_cap: int = 4
    per_pe_cap: int = 3
    link_cap: int = 1
    memory_domain_cap: int = 256
    memory_pe_cap: int = 256
    memory_global_cap: int = 768
    max_ticks_after_start: int = 20
    shadow_pe_quota: int = 7
    shadow_mem_quota: int = 12
    shadow_link_quota: int = 4
    drop_stage: str | None = None
    enabled: bool = True

    def __post_init__(self):
        if (self.source_mode not in ('disabled','forward_first') or
                type(self.enabled) is not bool or
                any(type(getattr(self,k)) is not int or getattr(self,k)<0
                    for k in ('global_pe_cap','per_pe_cap','link_cap',
                              'memory_domain_cap','memory_pe_cap','memory_global_cap',
                              'max_ticks_after_start','shadow_pe_quota',
                              'shadow_mem_quota','shadow_link_quota')) or
                self.max_ticks_after_start > 256 or
                self.drop_stage not in (None,*TRANSIT)):
            raise AdmissionError('bad resource profile or unbounded horizon')


def _occupancy(result: dict) -> tuple[dict,dict,dict]:
    """Read source engine counters; keep a conservative persistent memory floor."""
    rows = result['resources']['timeline']
    if not rows or len({r['tick'] for r in rows})!=len(rows):
        raise AdmissionError('source timeline absent or duplicated')
    by_tick={r['tick']:r for r in rows}
    peak_domain={d:max(r['memory_by_domain'].get(d,0) for r in rows)
                 for d in ('P','S','E','O')}
    peak_by_pe={p:max(r['memory_by_pe'].get(p,0) for r in rows)
                for p in ('PE0','PE1','PE2')}
    return by_tick,peak_domain,peak_by_pe


def residual_execution(record: DemandEpisode, action: str,
                       plan: ResidualPlan=ResidualPlan()) -> dict:
    """Execute actual BV-v0e FIRST, then reserve shadow services ex-post.

    No scheduling feedback enters v0e. Late reward is not a source-native grant.
    A blocked, lost or unobserved message never becomes negative reinforcement.
    """
    if type(plan) is not ResidualPlan or type(record) is not DemandEpisode or action not in CANDIDATES:
        raise AdmissionError('invalid source episode, action or resource plan')
    if type(record.demand) not in (bool,type(None)):
        raise AdmissionError('invalid typed sensor observation')
    witness,receipt=witnessed_decision(record,action)
    verify_witness(record,action,witness,receipt)
    # Closure and output are taken from the native v0e replay, not fabricated.
    case,fabric,source_plans=source_plan(record,action)
    source=execute_live_v0e(case,fabric,*source_plans,LiveBVPlanV0e(
        enabled=plan.source_mode!='disabled',priority='forward-first',
        assessor='C',terminal_channel=7,max_ticks=256))
    if source['schema']!='spk-bv-live-dual-event-scheduler/v0e':
        raise AdmissionError('not an original BV v0e timeline')
    source_rows,peak_domain,peak_pe=_occupancy(source)
    # Assert feasibility of the WHOLE frozen trace, not merely the ticks
    # at which the shadow worker happened to request a slot.
    if any(
        row['pe_service_total']>plan.global_pe_cap or
        row['link_total']>plan.link_cap or
        row['memory_total']>plan.memory_global_cap or
        any(value>plan.per_pe_cap for value in row['pe_service_by_pe'].values()) or
        any(value>plan.memory_pe_cap for value in row['memory_by_pe'].values()) or
        any(value>plan.memory_domain_cap for value in row['memory_by_domain'].values())
        for row in source_rows.values()
    ):
        raise AdmissionError('claimed profile cannot admit original frozen source trace')
    source_closure=[e['timestamp'] for e in source['forward']['terminal']
                    if e['node_id']=='C' and e['channel']==9]
    if len(source_closure)!=1:
        raise AdmissionError('source C closure missing or duplicated')
    # Never use an A1b reward if the source BV-v0e trace tells a different
    # story. Native timings, delivered signal and C closure are independently
    # reexecuted; disagreement is an abstention, not a negative judgment.
    native_C=tuple(e['timestamp'] for e in source['forward']['terminal']
                   if e['node_id']=='C' and e['channel']==7)
    native_demand=tuple(e['channel'] for e in source['forward']['terminal']
                        if e['node_id']=='C' and e['channel'] in (8,10))
    expected_demand=() if record.demand is None else (8 if record.demand else 10,)
    semantic_source_match=(native_C==receipt.c_forward_ticks and
                           native_demand==expected_demand and
                           source_closure[0]==receipt.closure_tick)
    source_digest=digest(source)
    trace=[]; deferred=Counter(); used=Counter(); previous=-1
    start=witness.start_tick
    status='pending_deadline'
    if not plan.enabled:
        status='shadow_disabled'
    else:
        for i,(stage,offset,mem,pe,domain) in enumerate(zip(
                STAGES,STAGE_OFFSET,MEM_CHARGE,STAGE_PE,STAGE_DOMAIN)):
            link=int(stage in TRANSIT)
            earliest=max(start+offset,previous+1,
                         source_closure[0] if stage=='C_observe_close' else 0)
            admitted=False
            for tick in range(earliest,start+plan.max_ticks_after_start+1):
                # All slots are from the original engine's *reported* load.
                # Beyond the source trace, keep its peak memory reservation.
                baseline=source_rows.get(tick)
                base_pe=baseline['pe_service_total'] if baseline else 0
                base_node=baseline['pe_service_by_pe'].get(pe,0) if baseline else 0
                base_link=baseline['link_total'] if baseline else 0
                base_mem=baseline['memory_total'] if baseline else sum(peak_domain.values())
                base_dom=(baseline['memory_by_domain'].get(domain,0) if baseline
                          else peak_domain[domain])
                base_pe_mem=(baseline['memory_by_pe'].get(pe,0) if baseline
                             else peak_pe[pe])
                # The native source must itself fit the claimed capacity.
                if (base_pe>plan.global_pe_cap or base_node>plan.per_pe_cap or
                    base_link>plan.link_cap or base_mem>plan.memory_global_cap or
                    base_dom>plan.memory_domain_cap or base_pe_mem>plan.memory_pe_cap):
                    raise AdmissionError('source load incompatible with claimed capacities')
                reasons=[]
                if base_pe+1>plan.global_pe_cap or base_node+1>plan.per_pe_cap:
                    reasons.append('PE_busy')
                if base_link+link>plan.link_cap:
                    reasons.append('link_busy')
                if (base_mem+mem>plan.memory_global_cap or
                    base_dom+mem>plan.memory_domain_cap or
                    base_pe_mem+mem>plan.memory_pe_cap):
                    reasons.append('memory_busy')
                if (used['PE']+1>plan.shadow_pe_quota or
                    used['memory']+mem>plan.shadow_mem_quota or
                    used['link']+link>plan.shadow_link_quota):
                    reasons.append('shadow_quota')
                if reasons:
                    for reason in reasons:deferred[reason]+=1
                    continue
                delivered=stage!=plan.drop_stage
                trace.append({'stage':stage,'tick':tick,'PE':1,'memory':mem,
                              'link':link,'PE_owner':pe,'memory_domain':domain,
                              'source_PE_at_grant':base_pe,'source_link_at_grant':base_link,
                              'source_memory_at_grant':base_mem,'delivered':delivered})
                used['PE']+=1;used['memory']+=mem;used['link']+=link
                previous=tick
                admitted=True
                if not delivered:
                    status='transport_loss'
                break
            if not admitted or status=='transport_loss':
                break
        else:
            if receipt.c_demand is None or not semantic_source_match:
                status='abstain_delivered'
            else:status='reward_delivered'
    completed=bool(trace and trace[-1]['stage']=='A_consume' and status in
                   ('reward_delivered','abstain_delivered'))
    reward=receipt.local_reward if status=='reward_delivered' else None
    verdict=(receipt.verdict if semantic_source_match else 'abstain') if completed else None
    if status=='reward_delivered' and reward not in (-1,1):
        raise AssertionError('invalid task reward')
    return {
        'schema':SCHEMA,'episode':witness.episode_id,'action':action,
        'decision_token':witness.token,'silent':not witness.has_A_spike,
        'status':status,'reward':reward,'verdict':verdict,
        'source_mode':plan.source_mode,'source_bv_v0e_sha256':source_digest,
        'source_closure_tick':source_closure[0],
        'source_semantic_parity':semantic_source_match,
        'shadow_last_grant_tick':previous if trace else None,
        'shadow_trace':trace,'deferred':dict(sorted(deferred.items())),
        'shadow_charged':{k:used[k] for k in ('PE','memory','link')},
        'unserved_stage':STAGES[len(trace)] if status=='pending_deadline' else None,
        'full_semantic_delivery':completed,
        'source_execution_unmodified':True,
        'source_BV_engine_admitted_shadow_control':False,
        'independent_task_truth':False,'native_learner_updates':0,
    }


def verify_residual_execution(record: DemandEpisode, action: str, plan: ResidualPlan,
                              purported: dict) -> None:
    """Reexecute source, decision witness and the exact bounded arbiter."""
    if type(purported) is not dict or purported!=residual_execution(record,action,plan):
        raise AdmissionError('forged, replayed or noncanonical source-grounded shadow report')


def run_t2g() -> dict:
    from spk_v5_research.island_endogenous_demand_v5t2c import generate_corpus
    source=generate_corpus(blocks=1,seed=37217,regime='aligned',train=False)
    cases=[(replace(r,demand=(False,True,None)[i%3]), CANDIDATES[i%3])
           for i,r in enumerate(source)]
    profiles={
        'normal':ResidualPlan(),
        'tight_PE':ResidualPlan(global_pe_cap=2,per_pe_cap=2),
        'deadline':ResidualPlan(max_ticks_after_start=9),
        'link_unavailable':ResidualPlan(link_cap=0,source_mode='disabled'),
        'lost_reverse':ResidualPlan(drop_stage='B_to_A'),
    }
    totals={};cells=[]
    for name,plan in profiles.items():
        counts=Counter();cost=Counter(); defers=Counter()
        for record,action in cases:
            # Some profiles (e.g. total link=0) cannot even admit source traffic.
            try: result=residual_execution(record,action,plan)
            except AdmissionError as ex:
                counts['source_profile_refused']+=1
                cells.append({'profile':name,'episode':record.episode.identity,
                              'action':action,'source_refusal':str(ex)})
                continue
            counts[result['status']]+=1
            counts['silent_cells']+=int(result['silent'])
            counts['silent_negative_deliveries']+=int(result['silent'] and result['reward']==-1)
            cost.update(result['shadow_charged']);defers.update(result['deferred'])
            cells.append({'profile':name,'episode':record.episode.identity,'action':action,
                          'source_digest':result['source_bv_v0e_sha256'],
                          'status':result['status'],'reward':result['reward'],
                          'service_ticks':[x['tick'] for x in result['shadow_trace']]})
        totals[name]={'counts':dict(sorted(counts.items())),
                      'shadow_cost':dict(sorted(cost.items())),
                      'deferrals':dict(sorted(defers.items()))}
    return {
        'schema':SCHEMA,
        'status':'SOURCE_GROUNDED_SHADOW_RESIDUAL_ADMISSION_ONLY_NO_NATIVE_ACTOR_ROUTE',
        'profiles':totals,'cells':len(cells),'evidence_sha256':digest(cells),
        'frozen_native_modified':False,'native_shadow_control_admission':False,
        'source_timeline_native':True,'shadow_grants_native':False,
        'blind_validation':False,'native_learner_updates':0,
        'limits':[
            'v0e is executed before the separate shadow arbitration; this is NOT interleaved native scheduler execution',
            'resource occupancy uses source v0e counters and conservative post-source memory peak, not production reservations',
            'shadow control packets are host-origin, not source-native authenticated messages',
            'absence of delivery, deadline exhaustion and signal loss are not negative reward',
            'the task and sensor remain synthetic; no independent truth, no native learning or operator adoption',
        ],
    }
