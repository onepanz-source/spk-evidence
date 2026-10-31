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

from spk_architecture_v1.pe_execution_v1b import _admit
from research.spk_v5_t5ghi.pe_challenge_issuer_v0 import compute_and_issue, PEEmission
from spk_architecture_v1.temporal_transport_v1a import _admit_plan
from spk_architecture_v1.temporal_service_v1b import _valid_plan
from spk_architecture_v1.causal_memory_v1c import _valid_memory, _reservation
from spk_architecture_v1.causal_transport_v1d import _valid_links
from spk_backvalidation_v0.contract_v0 import digest

SCHEMA = 'spk-bv-live-dual-event-scheduler/v0e'

class LiveBVRejected(ValueError):
    """No CLOSED witness or rollback guarantee after quota/custody failure."""

@dataclass(frozen=True)
class LiveBVPlanV0e:
    enabled: bool = True
    priority: str = 'forward-first'  # or feedback-first
    assessor: str = 'C'
    terminal_channel: int = 7
    hop_latency: int = 1
    max_hops: int = 8
    max_packets: int = 128
    max_occurrences: int = 256
    max_ticks: int = 256
    max_batches: int = 128
    max_events: int = 512


def execute_live_v0e(case, fabric, tplan, pplan, mplan, lplan, bv=LiveBVPlanV0e(), receiver_challenge=None):
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
    # T5ABC additive fork only: runtime-context semantic messages, NOT native authority.
    semantic_issuances = []
    semantic_by_assessment = {}
    semantic_hops = []
    contention = Counter()
    occupancy_peak = 0
    reserved_memory = 0
    batch_count = 0
    event_count = 0
    first_tick = now = min((e.timestamp for e in case.events), default=0)

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

    def offer_feedback(aid, ids, sender, hop, ready, inherited_semantic=None):
        nonlocal feedback_serial
        if not bv.enabled or not ids:
            return
        if hop > bv.max_hops:
            raise LiveBVRejected('feedback ancestry exceeds max_hops')
        # C owns first issuance in this simulated scheduler execution; B passes
        # the packet's payload, not a host reconstruction from the final output.
        if hop == 1:
            semantic = semantic_by_assessment.get(aid)
        else:
            semantic = inherited_semantic
        if semantic is not None:
            if (semantic.get('assessment_id') != aid or
                    semantic.get('C_source') != 'C' or
                    semantic.get('sign') not in (-1, 1) or
                    semantic.get('source_channel') not in (11, 12) or
                    (semantic['source_channel'] == 11) != (semantic['sign'] == 1) or
                    (receiver_challenge is not None and
                     (type(semantic.get('challenge_digest')) is not str or len(semantic['challenge_digest'])!=64))):
                raise LiveBVRejected('experimental semantic payload custody violation')
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
                 'hop':hop,'ready':ready,
                 'semantic':dict(semantic) if semantic is not None else None})

    while pending or inflight or any(outboxes.values()) or ready_feedback:
        if now-first_tick >= min(bv.max_ticks,pplan.max_service_span_ticks,
                                 mplan.max_service_span_ticks,lplan.max_link_span_ticks):
            raise LiveBVRejected('bounded live logical horizon exceeded')
        # Deliver both event classes BEFORE executing neuron batches at this tick.
        while inflight and inflight[0][0] <= now:
            due, _, kind, item, cross = heapq.heappop(inflight)
            if due != now:
                raise LiveBVRejected('late event delivery')
            if cross:inflight_count -= 1
            if kind=='spike':
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
                experimental_semantic = item.get('semantic')
                if experimental_semantic is not None:
                    semantic_hops.append({'tick':now, 'assessment_id':item['assessment_id'],
                        'packet_id':item['packet_id'], 'sender':item['sender'],
                        'receiver':item['receiver'], 'hop':item['hop'],
                        'C_emission_id':experimental_semantic['C_emission_id'],
                        'source_channel':experimental_semantic['source_channel'],
                        'sign':experimental_semantic['sign'],
                        'receiver_authenticates_C':False,
                        **({'challenge_digest':experimental_semantic['challenge_digest']}
                           if 'challenge_digest' in experimental_semantic else {})})
                ancestors=set()
                for oid in item['evidence_ids']:
                    ancestors.update(occurrences[oid]['parents'])
                offer_feedback(item['assessment_id'],ancestors,item['receiver'],item['hop']+1,now,
                               experimental_semantic)

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
                parents=tuple(sorted({oid for _ch,oid in items if oid is not None}))
                raw,guard,outs,pe_emission=compute_and_issue(
                    nodes[nid],states[nid],now,channels,parents,batch_count+1,receiver_challenge)
                remote=sum(1 for ch in outs for edge in out.get((nid,ch),()) if edge.target_pe!=pid)
                if remote>lplan.max_outbox_per_pe:
                    raise LiveBVRejected('sender outbox overflow, no truncated emission')
                del pending[(ready,nid)]
                states[nid]=[raw,now]
                batch_count+=1;event_count+=len(items);pe_total+=1;service_used[pid]+=1
                reserved_memory+=needed;mem_total+=needed
                for p,q in pe_mem.items():mem_pe_used[p]+=q
                for d,q in dom_mem.items():mem_dom_used[d]+=q
                # The PE-scope reference adapter computes and authors its semantic
                # descriptor BEFORE the scheduler receives this result. The fork
                # only transports it. Neither this Python adapter nor the host
                # is an independently authenticated neuronal authority.
                if pe_emission is not None and type(pe_emission) is not PEEmission:
                    raise LiveBVRejected('PE issuance type mismatch')
                semantic_for_batch = pe_emission.to_packet() if pe_emission is not None else None
                if semantic_for_batch is not None:
                    semantic_issuances.append(dict(semantic_for_batch))
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
                            if nid == 'C' and semantic_for_batch is not None:
                                semantic_by_assessment[aid] = {
                                    **semantic_for_batch, 'assessment_id':aid}
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
        # Unified live arbitration. Feedback and spike *requests* compete now.
        while True:
            forward=[]
            for pe in fabric.pe_ids:
                if outboxes[pe]: forward.append(outboxes[pe][0])
            reverse=sorted((x for x in ready_feedback if x['ready']<=now),
                           key=lambda x:(x['ready'],x['packet_id']))
            if bv.priority=='forward-first':
                offers=[('spike',x) for x in forward]+[('bv',x) for x in reverse]
            else:
                offers=[('bv',x) for x in reverse]+[('spike',x) for x in forward]
            if not offers or link_fabric_used>=lplan.fabric_slots_per_tick:
                if offers:contention['fabric_link']+=len(offers)
                break
            selected=False
            for kind,x in offers:
                src=x['source_pe'] if kind=='spike' else owners[x['sender']]
                dst=x['target_pe'] if kind=='spike' else owners[x['receiver']]
                if src==dst:
                    if kind=='bv':raise LiveBVRejected('same-PE BV unsupported by v0e')
                    raise LiveBVRejected('local spike entered cross-PE outbox')
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
                link_used[(src,dst)]+=1
                link_fabric_used+=1
                selected=True
                break
            if not selected: break
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
               'cross_inflight_end_tick':inflight_count})
        now+=1

    if any(o['delivered_at'] is None for o in occurrences.values()):
        raise LiveBVRejected('unacknowledged forward occurrence')
    return {'schema':SCHEMA,'policy':bv.priority,'enabled':bv.enabled,
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
                           'nonphysical-cost-proxy','not-N-node'],
            # Additive field only. This is NOT cryptographic/native C authority.
            'experimental_semantic_port':{
                'status':'IN_SCHEDULER_PE_OUTPUT_BOUND_RECEIVER_VISIBLE_RESEARCH',
                'issuances':semantic_issuances, 'feedback_hops':semantic_hops,
                'receiver_A_sign_receipts':[x for x in semantic_hops if x['receiver']=='A'],
                'host_can_forge':True,'native_origin_authenticated':False,
                'native_receiver_semantic_credit':False,'native_learning':False}}
