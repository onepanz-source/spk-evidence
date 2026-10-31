"""BV v0e RESEARCH: one live logical clock, two event classes, shared grants.

Unlike v0d, forward spikes and reverse BV packets are arbitrated while the
neuron program is executing, before either class has finished. This is a NEW
bounded reference executor, NOT the frozen A3d engine, nor distributed silicon.
No global credit, program adaptation, cold promotion or physical cost claim.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import heapq

from spk_architecture_v1.pe_execution_v1b import _admit, _compute_local
from spk_architecture_v1.temporal_transport_v1a import _admit_plan
from spk_architecture_v1.temporal_service_v1b import _valid_plan
from spk_architecture_v1.causal_memory_v1c import _valid_memory, _reservation
from spk_architecture_v1.causal_transport_v1d import _valid_links
from spk_backvalidation_v0.contract_v0 import digest

"""V5-T2h research-only *interleaved fork* of BV-v0e for semantic decision control.

The frozen v0e is copied as an immutable reference and NEVER edited. This
separate research executor admits host-origin decision stages in the SAME live
tick loop, PE/memory ledger, link queue and in-flight heap as source spikes and
source BV. This does not confer source-native origin or task independence.
"""
from dataclasses import replace
from spk_v5_research.island_objective_v5t1 import CANDIDATES
from spk_v5_research.island_endogenous_demand_v5t2c import DemandEpisode, generate_corpus
from spk_v5_research.island_decision_reward_v5t2f import (
    STAGES, STAGE_OFFSET, MEM_CHARGE, TRANSIT, AdmissionError, witnessed_decision,
    verify_witness,
)
from spk_v5_research.island_residual_service_v5t2g import STAGE_PE, STAGE_DOMAIN
from spk_v5_research.island_bv_resource_bridge_v5t2e import source_plan
from spk_backvalidation_v0.live_dual_scheduler_v0e import (
    execute_live_v0e as FROZEN_EXECUTE, LiveBVPlanV0e, LiveBVRejected,
)

T2H_SCHEMA = 'spk-v5-t2h-interleaved-research-scheduler/v0'

@dataclass(frozen=True)
class InterleavedPlan:
    enabled: bool = True
    priority: str = 'source-first'
    deadline_after_start: int = 36
    drop_stage: str | None = None
    source_bv_enabled: bool = True

    def __post_init__(self):
        if (type(self.enabled) is not bool or type(self.source_bv_enabled) is not bool or
                self.priority not in ('source-first','control-first') or
                type(self.deadline_after_start) is not int or
                not (0 <= self.deadline_after_start <= 120) or
                self.drop_stage not in (None,*TRANSIT)):
            raise AdmissionError('invalid interleaved shadow control configuration')


SCHEMA = 'spk-bv-live-dual-event-scheduler/v0e'

def _interleave(record, action, control, witness, receipt,
                case, fabric, tplan, pplan, mplan, lplan, bv):
    """Bounded live scheduler, with per-tick atomic reservation, deterministic order.

    Limitations: frozen A1 three-neuron domain, no progressive memory permits,
    no read/write BV authority transfer, one abstract service unit and two
    abstract (O,E) memory units per BV grant. Feedback can delay the *forward*
    LINK grant, never directly change neuron programs or state.
    """
    nodes, owners = _admit(case, fabric)
    _admit_plan(tplan)
    pe_caps = _valid_plan(fabric, pplan)
    mem_pe_caps, mem_domain_caps = _valid_memory(fabric, mplan)
    _valid_links(lplan)
    if (type(bv) is not LiveBVPlanV0e or type(bv.enabled) is not bool
            or bv.priority not in ('forward-first', 'feedback-first')):
        raise LiveBVRejected('invalid BV scheduling policy')
    if bv.assessor not in nodes or any(type(x) is not int or x <= 0 for x in
            (bv.hop_latency,bv.max_hops,bv.max_packets,bv.max_occurrences,
             bv.max_ticks,bv.max_batches,bv.max_events)) or type(bv.terminal_channel) is not int or bv.terminal_channel < 0:
        raise LiveBVRejected('invalid research bounds/assessor')
    out = defaultdict(list)
    for edge in fabric.static_routes:
        out[(edge.source_node,edge.source_channel)].append(edge)
    states = {nid:[node.initial_raw,0] for nid,node in nodes.items()}
    pending = defaultdict(list)  # (source timestamp, node) -> (channel, incoming route occurrence ID)
    for e in case.events:
        pending[(e.timestamp,e.node_id)].append((e.channel,None))
    ready_feedback = []
    outboxes = {p:[] for p in fabric.pe_ids}
    inflight = []  # heap of (tick, ordinal, class, payload, cross_pe)
    inflight_count = 0
    serial = 0
    occurrence_serial = 0
    assessment_serial = 0
    feedback_serial = 0
    arrived_receivers = set()  # (assessment, receiver), not a count of paths
    occurrences = {}
    assessments = []
    f_grants = []
    b_grants = []
    batches = []
    resource_timeline = []
    terminal = []
    emissions = []
    bv_deliveries = []
    contention = Counter()
    occupancy_peak = 0
    reserved_memory = 0
    batch_count = 0
    event_count = 0
    first_tick = now = min((e.timestamp for e in case.events), default=0)

    control_i = 0
    control_inflight = False
    control_ready_at = witness.decision_tick
    control_status = 'pending_deadline' if control.enabled else 'disabled'
    control_trace = []
    control_arrivals = []
    control_deferred = Counter()
    control_cost = Counter()

    def enqueue_inflight(due, kind, payload, cross):
        nonlocal serial,inflight_count,occupancy_peak
        if due <= now:
            raise LiveBVRejected('nonpositive causal delay')
        if cross:
            if inflight_count >= tplan.max_inflight_occurrences:
                return False
            inflight_count += 1
            occupancy_peak = max(occupancy_peak,inflight_count)
        heapq.heappush(inflight,(due,serial,kind,payload,cross))
        serial += 1
        return True

    def offer_feedback(aid, ids, sender, hop, ready):
        nonlocal feedback_serial
        if not bv.enabled or not ids:
            return
        if hop > bv.max_hops:
            raise LiveBVRejected('feedback ancestry exceeds max_hops')
        by_receiver=defaultdict(set)
        for oid in ids:
            if oid not in occurrences or occurrences[oid]['target'] != sender:
                raise LiveBVRejected('feedback forged nonexistent causal parent')
            by_receiver[occurrences[oid]['source']].add(oid)
        for dest in sorted(by_receiver):
            if feedback_serial >= bv.max_packets:
                raise LiveBVRejected('feedback max_packets budget exhausted')
            feedback_serial += 1
            ready_feedback.append({'packet_id':f'bv{feedback_serial}', 'assessment_id':aid,
                 'sender':sender,'receiver':dest, 'evidence_ids':tuple(sorted(by_receiver[dest])),
                 'hop':hop,'ready':ready})

    while pending or inflight or any(outboxes.values()) or ready_feedback or control_status == 'pending_deadline':
        if now-first_tick >= min(bv.max_ticks,pplan.max_service_span_ticks,
                                 mplan.max_service_span_ticks,lplan.max_link_span_ticks):
            raise LiveBVRejected('bounded live logical horizon exceeded')
        if (control_status == 'pending_deadline' and
                now > witness.start_tick + control.deadline_after_start):
            control_status = 'pending_deadline_expired'
        # Deliver all three event classes BEFORE executing neuron batches at this tick.
        while inflight and inflight[0][0] <= now:
            due, _, kind, item, cross = heapq.heappop(inflight)
            if due != now:
                raise LiveBVRejected('late event delivery')
            if cross:inflight_count -= 1
            if kind=='control':
                if not control_inflight or item['stage'] not in STAGES:
                    raise LiveBVRejected('forged or unexpected semantic control arrival')
                control_inflight = False
                control_ready_at = now
                control_arrivals.append({'stage':item['stage'],'tick':now})
            elif kind=='spike':
                pending[(now,item['target'])].append((item['channel'],item['id']))
                occurrences[item['id']]['delivered_at']=now
            else:
                key=(item['assessment_id'], item['receiver'])
                # Deduplicate judgment per assessment/receiver; preserve paths.
                independent=key not in arrived_receivers
                arrived_receivers.add(key)
                bv_deliveries.append({'tick':now,'assessment_id':item['assessment_id'],
                    'receiver':item['receiver'],'sender':item['sender'],
                    'packet_id':item['packet_id'],'independent_receiver':independent,
                    'evidence_ids':list(item['evidence_ids'])})
                ancestors=set()
                for oid in item['evidence_ids']:
                    ancestors.update(occurrences[oid]['parents'])
                offer_feedback(item['assessment_id'],ancestors,item['receiver'],item['hop']+1,now)

        service_used = Counter()
        mem_pe_used = Counter()
        mem_dom_used = Counter()
        mem_total = 0
        pe_total = 0
        # Atomic conservative grants; lack of room defers the whole batch.
        while True:
            candidates=sorted((ready,nid) for (ready,nid) in pending if ready<=now
                and not outboxes[owners[nid]] and service_used[owners[nid]]<pe_caps[owners[nid]])
            if not candidates or pe_total >= pplan.fabric_slots_per_tick:
                break
            accepted=False
            for ready,nid in candidates:
                pid=owners[nid]
                items=pending[(ready,nid)]
                envelope=_reservation(nodes[nid],[ch for ch,_ in items],pid,out)
                pe_mem=Counter()
                dom_mem=Counter()
                for target,dom,_intent,q in envelope:
                    pe_mem[target]+=q
                    dom_mem[dom]+=q
                needed=sum(pe_mem.values())
                if (mem_total+needed>mplan.fabric_slots_per_tick or
                    any(mem_pe_used[p]+q>mem_pe_caps[p] for p,q in pe_mem.items()) or
                    any(mem_dom_used[d]+q>mem_domain_caps[d] for d,q in dom_mem.items())):
                    contention['forward_memory']+=1
                    continue
                if batch_count>=bv.max_batches or event_count+len(items)>bv.max_events:
                    raise LiveBVRejected('forward batch/event bound exhausted')
                channels=[ch for ch,_ in items]
                if now<states[nid][1]:raise LiveBVRejected('backward state timestamp')
                raw,guard,outs=_compute_local(nodes[nid],states[nid],now,channels)
                remote=sum(1 for ch in outs for edge in out.get((nid,ch),()) if edge.target_pe!=pid)
                if remote>lplan.max_outbox_per_pe:
                    raise LiveBVRejected('sender outbox overflow, no truncated emission')
                del pending[(ready,nid)]
                states[nid]=[raw,now]
                batch_count+=1;event_count+=len(items);pe_total+=1;service_used[pid]+=1
                reserved_memory+=needed;mem_total+=needed
                for p,q in pe_mem.items():mem_pe_used[p]+=q
                for d,q in dom_mem.items():mem_dom_used[d]+=q
                parents=tuple(sorted({oid for _ch,oid in items if oid is not None}))
                batches.append({'tick':now,'ready':ready,'node':nid,'channels':sorted(channels),
                                'parents':list(parents),'raw':raw,'outputs':list(outs)})
                for ch in outs:
                    emissions.append({'timestamp':now,'node_id':nid,'channel':ch})
                    edges=out.get((nid,ch),())
                    if not edges:
                        terminal.append({'timestamp':now,'node_id':nid,'channel':ch})
                        if nid==bv.assessor and ch==bv.terminal_channel and bv.enabled:
                            assessment_serial+=1
                            aid=f'a{assessment_serial}'
                            assessments.append({'id':aid,'observer':nid,'tick':now,
                                                'input_occurrences':list(parents)})
                            offer_feedback(aid,parents,nid,1,now)
                    for edge in edges:
                        if occurrence_serial >= bv.max_occurrences:
                            raise LiveBVRejected('occurrence quota exhausted')
                        occurrence_serial+=1
                        oid=f'r{occurrence_serial}'
                        occ={'id':oid,'source':nid,'target':edge.target_node,
                             'source_pe':pid,'target_pe':edge.target_pe,
                             'channel':edge.target_channel,'emitted_at':now,
                             'delivered_at':None,'parents':parents,
                             'delay':edge.delay_ticks}
                        occurrences[oid]=occ
                        if pid==edge.target_pe:
                            due=now+edge.delay_ticks
                            if not enqueue_inflight(due,'spike',occ,False):
                                raise LiveBVRejected('unexpected local in-flight denial')
                            # Local transmissions do not consume link grants.
                        else:
                            outboxes[pid].append(occ)
                accepted=True
                break
            if not accepted:break

        link_used=Counter()
        link_fabric_used=0
        # The semantic route is admitted HERE, not after the native source run.
        # Both order policies share the same PE, memory, link and in-flight caps.
        while True:
            forward=[]
            for pe in fabric.pe_ids:
                if outboxes[pe]:forward.append(outboxes[pe][0])
            reverse=sorted((x for x in ready_feedback if x['ready']<=now),
                           key=lambda x:(x['ready'],x['packet_id']))
            source_offers = ([('spike',x) for x in forward]+[('bv',x) for x in reverse]
                if bv.priority=='forward-first' else
                [('bv',x) for x in reverse]+[('spike',x) for x in forward])
            control_can_offer=(control_status=='pending_deadline' and not control_inflight
                and control_i<len(STAGES) and now>=control_ready_at
                and now >= witness.start_tick+STAGE_OFFSET[control_i]
                and (STAGES[control_i]!='C_observe_close' or any(
                    x['node_id']=='C' and x['channel']==9 and x['timestamp']<=now
                    for x in terminal)))
            control_offers=[('control',STAGES[control_i])] if control_can_offer else []
            offers=(control_offers+source_offers if control.priority=='control-first'
                    else source_offers+control_offers)
            if not offers:break
            selected=False
            for kind,x in offers:
                if kind=='control':
                    stage=x; idx=control_i
                    src=STAGE_PE[idx]; domain=STAGE_DOMAIN[idx]
                    need_mem=MEM_CHARGE[idx]; needs_link=stage in TRANSIT
                    dst={'A_to_B':'PE1','B_to_C':'PE2','C_to_B':'PE1',
                         'B_to_A':'PE0'}.get(stage)
                    reasons=[]
                    if service_used[src]>=pe_caps[src] or pe_total>=pplan.fabric_slots_per_tick:
                        reasons.append('PE_busy')
                    if (mem_total+need_mem>mplan.fabric_slots_per_tick or
                            mem_pe_used[src]+need_mem>mem_pe_caps[src] or
                            mem_dom_used[domain]+need_mem>mem_domain_caps[domain]):
                        reasons.append('memory_busy')
                    if needs_link:
                        if (link_fabric_used>=lplan.fabric_slots_per_tick or
                                link_used[(src,dst)]>=lplan.link_slots_per_tick):
                            reasons.append('link_busy')
                        if inflight_count>=tplan.max_inflight_occurrences:
                            reasons.append('inflight_busy')
                    if reasons:
                        for reason in reasons:control_deferred[reason]+=1
                        continue
                    service_used[src]+=1;pe_total+=1
                    mem_pe_used[src]+=need_mem;mem_dom_used[domain]+=need_mem
                    mem_total+=need_mem
                    control_cost['PE']+=1;control_cost['memory']+=need_mem
                    if needs_link:
                        link_used[(src,dst)]+=1;link_fabric_used+=1
                        control_cost['link']+=1
                    delivered=stage!=control.drop_stage
                    control_trace.append({'stage':stage,'tick':now,'PE_owner':src,
                        'memory_domain':domain,'PE':1,'memory':need_mem,
                        'link':int(needs_link),'delivered':delivered,
                        'due_tick':now+1 if needs_link and delivered else None})
                    control_i+=1
                    if not delivered:
                        control_status='transport_loss'
                    elif needs_link:
                        if not enqueue_inflight(now+1,'control',{'stage':stage},True):
                            raise LiveBVRejected('unexpected derived control in-flight denial')
                        control_inflight=True
                    else:
                        control_ready_at=now+1
                    if stage=='A_consume' and delivered:
                        control_status='delivered_pending_semantic_audit'
                    selected=True
                    break
                src=x['source_pe'] if kind=='spike' else owners[x['sender']]
                dst=x['target_pe'] if kind=='spike' else owners[x['receiver']]
                if src==dst:
                    if kind=='bv':raise LiveBVRejected('same-PE BV unsupported by v0e')
                    raise LiveBVRejected('local spike entered cross-PE outbox')
                if link_fabric_used>=lplan.fabric_slots_per_tick:
                    contention['fabric_link']+=1
                    continue
                if link_used[(src,dst)]>=lplan.link_slots_per_tick:
                    contention['directional_link']+=1
                    continue
                if inflight_count>=tplan.max_inflight_occurrences:
                    contention['inflight']+=1
                    continue
                if kind=='bv':
                    if service_used[src]>=pe_caps[src] or pe_total>=pplan.fabric_slots_per_tick:
                        contention['bv_service']+=1
                        continue
                    if (mem_total+2>mplan.fabric_slots_per_tick or
                        mem_pe_used[src]+1>mem_pe_caps[src] or
                        mem_pe_used[dst]+1>mem_pe_caps[dst] or
                        mem_dom_used['O']+1>mem_domain_caps['O'] or
                        mem_dom_used['E']+1>mem_domain_caps['E']):
                        contention['bv_memory']+=1
                        continue
                    pe_total+=1;service_used[src]+=1
                    mem_total+=2;mem_pe_used[src]+=1;mem_pe_used[dst]+=1
                    mem_dom_used['O']+=1;mem_dom_used['E']+=1
                    ready_feedback.remove(x)
                    due=now+bv.hop_latency
                    b_grants.append({'tick':now,'delivered_at':due,'packet_id':x['packet_id'],
                                     'assessment_id':x['assessment_id'],
                                     'source_pe':src,'target_pe':dst,'sender':x['sender'],
                                     'receiver':x['receiver'],'wait':now-x['ready']})
                    if not enqueue_inflight(due,'bv',x,True):
                        raise LiveBVRejected('feedback credit accounting error')
                else:
                    outboxes[src].pop(0)
                    due=now+x['delay']+tplan.cross_pe_extra_ticks
                    if not enqueue_inflight(due,'spike',x,True):
                        raise LiveBVRejected('forward credit accounting error')
                    f_grants.append({'tick':now,'delivered_at':due,'id':x['id'],
                                     'source_pe':src,'target_pe':dst,'source':x['source'],
                                     'target':x['target'],'wait':now-x['emitted_at']})
                link_used[(src,dst)]+=1;link_fabric_used+=1
                selected=True
                break
            if not selected:break
        if (mem_total>mplan.fabric_slots_per_tick or pe_total>pplan.fabric_slots_per_tick or
            link_fabric_used>lplan.fabric_slots_per_tick or inflight_count>tplan.max_inflight_occurrences):
            raise AssertionError('shared resource oversubscription')
        resource_timeline.append({'tick':now,'forward_computations':sum(
               x['tick']==now for x in batches),
               'feedback_sends':sum(x['tick']==now for x in b_grants),
               'pe_service_total':pe_total,'pe_service_by_pe':dict(sorted(service_used.items())),
               'memory_total':mem_total,'memory_by_pe':dict(sorted(mem_pe_used.items())),
               'memory_by_domain':dict(sorted(mem_dom_used.items())),
               'link_total':link_fabric_used,'link_by_direction':[
                   [a,b,n] for (a,b),n in sorted(link_used.items())],
               'cross_inflight_end_tick':inflight_count,
               **({'semantic_control_PE':sum(x['tick']==now for x in control_trace),
                    'semantic_control_memory':sum(x['memory'] for x in control_trace if x['tick']==now),
                    'semantic_control_link':sum(x['link'] for x in control_trace if x['tick']==now)}
                   if control.enabled else {})})
        now+=1

    if any(o['delivered_at'] is None for o in occurrences.values()):
        raise LiveBVRejected('unacknowledged forward occurrence')
    native_view = {'schema':SCHEMA,'policy':bv.priority,'enabled':bv.enabled,
            'forward':{'states':{n:states[n][0] for n in sorted(nodes)},
                       'batches':batches,'emissions':emissions,'terminal':terminal,
                       'processed_events':event_count,'processed_batches':batch_count,
                       'link_grants':f_grants,'occurrences':list(occurrences.values())},
            'feedback':{'assessments':assessments,'link_grants':b_grants,
                        'deliveries':bv_deliveries,
                        'unique_receiver_votes':len(arrived_receivers)},
            'resources':{'timeline':resource_timeline,'peak_cross_inflight':occupancy_peak,
                         'forward_link_grants':len(f_grants),'bv_link_grants':len(b_grants),
                         'bv_service_units':len(b_grants),'bv_memory_units':2*len(b_grants),
                         'forward_reserved_memory_units':reserved_memory,
                         'contention':dict(sorted(contention.items()))},
            'constraints':['three-node-admission','global-logical-clock',
                           'atomic-conservative-memory','no-learning','no-promotion',
                           'no-verified-global-credit','no-A3d-bitwise-equivalence',
                           'nonphysical-cost-proxy','not-N-node']}

    closure=[x['timestamp'] for x in terminal if x['node_id']=='C' and x['channel']==9]
    outputs=tuple(x['timestamp'] for x in terminal if x['node_id']=='C' and x['channel']==7)
    observed=tuple(x['channel'] for x in terminal if x['node_id']=='C' and x['channel'] in (8,10))
    expected=() if record.demand is None else (8 if record.demand else 10,)
    parity=(len(closure)==1 and closure[0]==receipt.closure_tick and
            outputs==receipt.c_forward_ticks and observed==expected)
    if control_status=='delivered_pending_semantic_audit':
        control_status=('reward_delivered' if parity and receipt.c_demand is not None
                        else 'abstain_delivered')
    reward=receipt.local_reward if control_status=='reward_delivered' else None
    return {'schema':T2H_SCHEMA,'source_view':native_view,
        'control':{'status':control_status,'episode':witness.episode_id,
          'decision_token':witness.token,'silent':not witness.has_A_spike,
          'trace':control_trace,'arrivals':control_arrivals,
          'deferred':dict(sorted(control_deferred.items())),
          'cost':{key:control_cost[key] for key in ('PE','memory','link')},
          'source_semantic_parity':parity,
          'reward':reward,'verdict':receipt.verdict if reward is not None else
                    'abstain' if control_status=='abstain_delivered' else None,
          'host_origin_not_native':True,'native_learning':False},
        'frozen_modified':False,'learning_updates':0,
        'source_native_granted_semantic_control':False}


def integrated_execution(record: DemandEpisode, action: str,
                         plan: InterleavedPlan=InterleavedPlan()) -> dict:
    if type(record) is not DemandEpisode or action not in CANDIDATES or type(plan) is not InterleavedPlan:
        raise AdmissionError('invalid interleaved source record, action or plan')
    witness,receipt=witnessed_decision(record,action)
    verify_witness(record,action,witness,receipt)
    case,fabric,plans=source_plan(record,action)
    result=_interleave(record,action,plan,witness,receipt,case,fabric,*plans,
        LiveBVPlanV0e(enabled=plan.source_bv_enabled,priority='forward-first',
        assessor='C',terminal_channel=7,max_ticks=256))
    if not plan.enabled:
        original=FROZEN_EXECUTE(case,fabric,*plans,LiveBVPlanV0e(
            enabled=plan.source_bv_enabled,priority='forward-first',
            assessor='C',terminal_channel=7,max_ticks=256))
        if result['source_view']!=original:
            raise AssertionError('OFF MUST EXACTLY REPRODUCE frozen BV v0e')
    return result


def verify_integrated_execution(record: DemandEpisode, action: str,
                               plan: InterleavedPlan, claimed: dict) -> None:
    """Exact independent replay for typed shadow custody, not a remote signature."""
    if type(claimed) is not dict or claimed != integrated_execution(record,action,plan):
        raise AdmissionError('forged, reordered or noncanonical integrated research execution')


def run_t2h() -> dict:
    corpus=generate_corpus(blocks=1,seed=37217,regime='aligned',train=False)
    source=tuple((replace(rec,demand=(False,True,None)[idx%3]),CANDIDATES[idx%3])
                 for idx,rec in enumerate(corpus))
    profiles={
        'off':InterleavedPlan(enabled=False),
        'source_first':InterleavedPlan(),
        'control_first':InterleavedPlan(priority='control-first'),
        'deadline_short':InterleavedPlan(deadline_after_start=9),
        'return_loss':InterleavedPlan(drop_stage='B_to_A'),
    }
    matrix=[];summary={};executions={}
    for name,plan in profiles.items():
        count=Counter();charge=Counter();source_sha=[];deferrals=Counter()
        executions[name]=[]
        for rec,action in source:
            result=integrated_execution(rec,action,plan)
            control=result['control'];count[control['status']]+=1
            charge.update(control['cost'])
            source_sha.append(digest(result['source_view']))
            executions[name].append(result['source_view'])
            deferrals.update(control['deferred'])
            matrix.append({'profile':name,'episode':rec.episode.identity,
                'action':action,'status':control['status'],'reward':control['reward'],
                'source_sha256':source_sha[-1],
                'control_service_ticks':[x['tick'] for x in control['trace']]})
        summary[name]={'statuses':dict(sorted(count.items())),
                       'control_cost':dict(sorted(charge.items())),
                       'source_sha256':digest(source_sha),
                       'deferrals':dict(sorted(deferrals.items()))}
    for name in profiles:
        summary[name]['source_forward_batch_changes_vs_off']=sum(
            a['forward']['batches']!=b['forward']['batches']
            for a,b in zip(executions[name],executions['off']))
        summary[name]['source_terminal_changes_vs_off']=sum(
            a['forward']['terminal']!=b['forward']['terminal']
            for a,b in zip(executions[name],executions['off']))
    return {'schema':T2H_SCHEMA,'status':'INTERLEAVED_DERIVED_TICK_ARBITER_RESEARCH_ONLY',
        'episodes':len(source),'profiles':summary,'matrix_digest':digest(matrix),
        'native_engine_modified':False,'control_host_origin':True,
        'native_integration':False,'independent_task_truth':False,
        'blind_T3':False,'native_learning_updates':0,
        'limits':['This is an isolated copy/fork of BV v0e, NOT a native or frozen engine edit',
                  'Control commits are issued by the shadow host, not A native decision intake',
                  'Full native no-control replay is exact; on-control may alter timing and semantics',
                  'Reward requires after-the-fact A1b/v0e temporal parity, else abstention',
                  'Sensor and objective are synthetically defined, no blind independent task truth',
                  'No update or promotion to native neuron programs']}
