"""BV v0f RESEARCH: parameterized neuron/PE population with two live event classes.

Unlike v0d, forward spikes and reverse BV packets are arbitrated while the
neuron program is executing, before either class has finished. This is a NEW
bounded reference executor, NOT the frozen A3d engine, nor distributed silicon.
No global credit, program adaptation, cold promotion or physical cost claim.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import heapq

from spk_architecture_v1.pe_execution_v1b import _compute_local, _natural
from spk_architecture_v1.pe_fabric_v1a import FabricV1a, PlacementV1a, StaticRouteV1a
from spk_architecture_v1.temporal_transport_v1a import _admit_plan
from spk_architecture_v1.temporal_service_v1b import _valid_plan
from spk_architecture_v1.causal_memory_v1c import _valid_memory, _reservation
from spk_architecture_v1.causal_transport_v1d import _valid_links
from spk_backvalidation_v0.contract_v0 import digest

SCHEMA = 'spk-bv-n-node-live-dual-event-scheduler/v0f'

class LiveBVRejected(ValueError):
    """No CLOSED witness or rollback guarantee after quota/custody failure."""

@dataclass(frozen=True)
class LiveBVPlanV0f:
    enabled: bool = True
    priority: str = 'forward-first'  # or feedback-first
    assessors: tuple[str, ...] = ()
    terminal_channel: int = 7
    hop_latency: int = 1
    max_hops: int = 8
    max_packets: int = 128
    max_occurrences: int = 256
    max_ticks: int = 256
    max_batches: int = 128
    max_events: int = 512



def plan_n_v0f(case, pe_count: int, *, mapping=None, max_nodes=1024, max_edges=8192):
    """Create an N-neuron FabricV1a container with general PE ownership.

    This is a *new research profile*; frozen A1a admission stays three-node.
    The numeric limits protect this prototype, not the abstract SPK semantics.
    """
    if (type(pe_count) is not int or not 1 <= pe_count <= 1024 or
        type(max_nodes) is not int or max_nodes <= 0 or
        type(max_edges) is not int or max_edges < 0):
        raise LiveBVRejected('invalid prototype fabric population or limits')
    if not hasattr(case, 'nodes') or not hasattr(case, 'edges'):
        raise LiveBVRejected('invalid case population')
    if not 1 <= len(case.nodes) <= max_nodes or len(case.edges) > max_edges:
        raise LiveBVRejected('N-node research admission bound exceeded')
    ids=[n.node_id for n in case.nodes]
    if any(type(i) is not str or not i for i in ids) or len(set(ids))!=len(ids):
        raise LiveBVRejected('invalid or duplicate neuron identity')
    pes=tuple(f'PE{i}' for i in range(pe_count))
    if mapping is None:
        owners={nid:pes[i%pe_count] for i,nid in enumerate(ids)}
    else:
        if type(mapping) is not dict or set(mapping)!=set(ids) or any(
               type(v) is not str or v not in pes for v in mapping.values()):
            raise LiveBVRejected('invalid explicit neuron PE mapping')
        owners=dict(mapping)
    routes=tuple(StaticRouteV1a(e.source_node,e.source_channel,e.target_node,
         e.target_channel,e.delay_ticks,owners.get(e.source_node),owners.get(e.target_node))
         for e in case.edges)
    f=FabricV1a('n-node-v0f',pes,
         tuple(PlacementV1a(nid,owners[nid]) for nid in sorted(ids)),routes)
    _admit_n_v0f(case,f)
    return f


def _admit_n_v0f(case, fabric):
    """Explicit admission copied in scope from A1b, WITHOUT modifying A1b.

    Covers the frozen instruction fragment, not arbitrary future SPK programs.
    """
    if type(fabric) is not FabricV1a or not hasattr(case,'nodes') or not case.nodes:
        raise LiveBVRejected('invalid N-node population')
    if any(type(n.node_id) is not str or not n.node_id for n in case.nodes):
        raise LiveBVRejected('invalid neuron IDs')
    if len(case.nodes)>1024 or len(case.edges)>8192:
        raise LiveBVRejected('N-node research admission bound exceeded')
    nodes={n.node_id:n for n in case.nodes}
    if len(nodes)!=len(case.nodes):
        raise LiveBVRejected('duplicate neuron IDs')
    if (not fabric.pe_ids or len(set(fabric.pe_ids))!=len(fabric.pe_ids)
         or len(fabric.placement)!=len(nodes)):
        raise LiveBVRejected('invalid PE population')
    owners={}
    for p in fabric.placement:
        if (p.node_id not in nodes or p.node_id in owners or
            p.pe_id not in fabric.pe_ids):
            raise LiveBVRejected('invalid PE custody')
        owners[p.node_id]=p.pe_id
    if set(owners)!=set(nodes):
        raise LiveBVRejected('incomplete PE custody')
    edges=Counter()
    for e in case.edges:
        if (e.source_node not in nodes or e.target_node not in nodes or
            not _natural(e.source_channel) or not _natural(e.target_channel) or
            type(e.delay_ticks) is not int or e.delay_ticks <= 0):
            raise LiveBVRejected('invalid edge occurrence')
        edges[(e.source_node,e.source_channel,e.target_node,e.target_channel,e.delay_ticks)]+=1
    routes=Counter()
    for r in fabric.static_routes:
        if (r.source_node not in nodes or r.target_node not in nodes or
            r.source_pe!=owners[r.source_node] or r.target_pe!=owners[r.target_node] or
            not _natural(r.source_channel) or not _natural(r.target_channel) or
            type(r.delay_ticks) is not int or r.delay_ticks <= 0):
            raise LiveBVRejected('forged static route')
        routes[(r.source_node,r.source_channel,r.target_node,r.target_channel,r.delay_ticks)]+=1
    if edges!=routes:
        raise LiveBVRejected('static route multiplicity/custody mismatch')
    for n in case.nodes:
        if (type(n.state_bits) is not int or not 1<=n.state_bits<=32 or
            type(n.fractional_bits) is not int or not 0<=n.fractional_bits<n.state_bits or
            not _natural(n.initial_raw) or n.initial_raw >= (1<<n.state_bits)):
            raise LiveBVRejected('invalid neuron state config')
        if type(n.instructions) is not tuple:
            raise LiveBVRejected('invalid instruction population')
        for ins in n.instructions:
            if type(ins) is not tuple or len(ins)!=2:
                raise LiveBVRejected('invalid instruction')
            op,arg=ins
            if op=='ACC':
                if (type(arg) is not tuple or len(arg)!=2 or not all(_natural(x) for x in arg)):
                    raise LiveBVRejected('invalid ACC')
            elif op in ('CMP','EMIT','RESET','SHIFT'):
                if not _natural(arg) or (op=='RESET' and arg >= (1<<n.state_bits)):
                    raise LiveBVRejected('invalid instruction operand')
            else:
                raise LiveBVRejected('instruction outside frozen fragment')
    for e in case.events:
        if e.node_id not in nodes or not _natural(e.timestamp) or not _natural(e.channel):
            raise LiveBVRejected('invalid external event')
    return nodes,owners


def layered_case_v0f(layer_sizes, *, events_at=(0,), recurrent=False):
    """Deterministic, fully connected adjacent layers; optionally a QUIET loop.

    Topology description is independent from mapping to processing elements.
    Quiet loop routes to channel 1 while relay neurons read only channel 0.
    """
    from search.spk_24n_independent_oracle_v0 import CaseV0,NodeV0,EdgeV0,EventV0
    if (type(layer_sizes) is not tuple or not layer_sizes or
        any(type(n) is not int or n<=0 for n in layer_sizes) or
        sum(layer_sizes)>1024 or type(recurrent) is not bool or
        type(events_at) is not tuple or
        any(type(t) is not int or t<0 for t in events_at)):
        raise LiveBVRejected('invalid layered research configuration')
    relay=(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0))
    layers=[];idx=0
    for count in layer_sizes:
        layers.append(tuple(f'N{i}' for i in range(idx,idx+count)))
        idx+=count
    nodes=tuple(NodeV0(n,16,0,0,relay) for layer in layers for n in layer)
    edges=tuple(EdgeV0(src,7,dst,0,1) for l0,l1 in zip(layers,layers[1:])
                for src in l0 for dst in l1)
    if recurrent and len(layers)>1:
        edges+=(EdgeV0(layers[-1][-1],7,layers[0][0],1,1),)
    events=tuple(EventV0(t,layers[0][0],0) for t in events_at)
    return CaseV0(nodes,edges,events),layers

def execute_n_v0f(case, fabric, tplan, pplan, mplan, lplan, bv=LiveBVPlanV0f()):
    """N-neuron bounded live scheduler with atomic per-tick reservation.

    Limitations: frozen A1 *instruction fragment*, no progressive memory permits,
    no read/write BV authority transfer, one abstract service unit and two
    abstract (O,E) memory units per BV grant. Feedback can delay the *forward*
    LINK grant, never directly change neuron programs or state.
    """
    nodes, owners = _admit_n_v0f(case, fabric)
    _admit_plan(tplan)
    pe_caps = _valid_plan(fabric, pplan)
    mem_pe_caps, mem_domain_caps = _valid_memory(fabric, mplan)
    _valid_links(lplan)
    if (type(bv) is not LiveBVPlanV0f or type(bv.enabled) is not bool
            or bv.priority not in ('forward-first', 'feedback-first')):
        raise LiveBVRejected('invalid BV scheduling policy')
    if (type(bv.assessors) is not tuple or
        any(type(x) is not str or x not in nodes for x in bv.assessors) or
        len(set(bv.assessors))!=len(bv.assessors) or
        any(type(x) is not int or x <= 0 for x in
            (bv.hop_latency,bv.max_hops,bv.max_packets,bv.max_occurrences,
             bv.max_ticks,bv.max_batches,bv.max_events)) or type(bv.terminal_channel) is not int or bv.terminal_channel < 0):
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
                and service_used[owners[nid]]<pe_caps[owners[nid]])
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
                    raise LiveBVRejected('single batch exceeds sender outbox capacity')
                if len(outboxes[pid])+remote>lplan.max_outbox_per_pe:
                    contention['forward_outbox']+=1
                    continue
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
                        if nid in bv.assessors and ch==bv.terminal_channel and bv.enabled:
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
            if not offers:
                break
            selected=False
            for kind,x in offers:
                src=x['source_pe'] if kind=='spike' else owners[x['sender']]
                dst=x['target_pe'] if kind=='spike' else owners[x['receiver']]
                is_local=src==dst
                if kind=='spike' and is_local:
                    raise LiveBVRejected('local spike incorrectly entered cross-PE outbox')
                if not is_local:
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
                    pe_need=Counter((src,dst))
                    if (mem_total+2>mplan.fabric_slots_per_tick or
                        any(mem_pe_used[p]+q>mem_pe_caps[p] for p,q in pe_need.items()) or
                        mem_dom_used['O']+1>mem_domain_caps['O'] or
                        mem_dom_used['E']+1>mem_domain_caps['E']):
                        contention['bv_memory']+=1
                        continue
                    pe_total+=1;service_used[src]+=1
                    mem_total+=2
                    for p,q in pe_need.items():mem_pe_used[p]+=q
                    mem_dom_used['O']+=1;mem_dom_used['E']+=1
                    ready_feedback.remove(x)
                    due=now+bv.hop_latency
                    b_grants.append({'tick':now,'delivered_at':due,'packet_id':x['packet_id'],
                                     'assessment_id':x['assessment_id'],
                                     'source_pe':src,'target_pe':dst,'sender':x['sender'],
                                     'receiver':x['receiver'],'cross_pe':not is_local,
                                     'wait':now-x['ready']})
                    if not enqueue_inflight(due,'bv',x,not is_local):
                        raise LiveBVRejected('feedback credit accounting error')
                else:
                    outboxes[src].pop(0)
                    due=now+x['delay']+tplan.cross_pe_extra_ticks
                    if not enqueue_inflight(due,'spike',x,True):
                        raise LiveBVRejected('forward credit accounting error')
                    f_grants.append({'tick':now,'delivered_at':due,'id':x['id'],
                                     'source_pe':src,'target_pe':dst,'source':x['source'],
                                     'target':x['target'],'wait':now-x['emitted_at']})
                if not is_local:
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
            'population':{'neurons':len(nodes),'pe_count':len(fabric.pe_ids),
                          'placements':[[n,owners[n]] for n in sorted(nodes)]},
            'forward':{'states':{n:states[n][0] for n in sorted(nodes)},
                       'batches':batches,'emissions':emissions,'terminal':terminal,
                       'processed_events':event_count,'processed_batches':batch_count,
                       'link_grants':f_grants,'occurrences':list(occurrences.values())},
            'feedback':{'assessments':assessments,'link_grants':b_grants,
                        'deliveries':bv_deliveries,
                        'unique_receiver_votes':len(arrived_receivers)},
            'resources':{'timeline':resource_timeline,'peak_cross_inflight':occupancy_peak,
                         'forward_link_grants':len(f_grants),'bv_link_grants':sum(g['cross_pe'] for g in b_grants),
                         'bv_local_sends':sum(not g['cross_pe'] for g in b_grants),
                         'bv_service_units':len(b_grants),'bv_memory_units':2*len(b_grants),
                         'forward_reserved_memory_units':reserved_memory,
                         'contention':dict(sorted(contention.items()))},
            'constraints':['parameterized-bounded-admission','global-logical-clock',
                           'atomic-conservative-memory','no-learning','no-promotion',
                           'no-verified-global-credit','no-A3d-bitwise-equivalence',
                           'nonphysical-cost-proxy','not-validated-for-all-network-programs']}
