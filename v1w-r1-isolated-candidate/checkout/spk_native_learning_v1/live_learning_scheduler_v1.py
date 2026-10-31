"""SPK Native Learning Runtime v1: versioned fork of bounded BV v0e.

First intrinsic P update on receiver C after *actual* A PE emission and BV
delivery, before a subsequent C batch on the same live scheduler clock.
Frozen v0e source stays unmodified. Research domain deliberately bounded to
C choices 11/12 and A verdict channels 21/22. No generic learning claim.

Original foundation: BV v0e RESEARCH: one live logical clock, two event classes, shared grants.

Unlike v0d, forward spikes and reverse BV packets are arbitrated while the
neuron program is executing, before either class has finished. This is a NEW
bounded reference executor, NOT the frozen A3d engine, nor distributed silicon.
No global credit, program adaptation, cold promotion or physical cost claim.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
import heapq

from spk_architecture_v1.pe_execution_v1b import _admit, _compute_local
from spk_architecture_v1.temporal_transport_v1a import _admit_plan
from spk_architecture_v1.temporal_service_v1b import _valid_plan
from spk_architecture_v1.causal_memory_v1c import _valid_memory, _reservation
from spk_architecture_v1.causal_transport_v1d import _valid_links
from spk_backvalidation_v0.contract_v0 import digest

SCHEMA = 'spk-native-learning-live-bv/v1'
FROZEN_SOURCE_SHA256 = '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
FROZEN_PE_SHA256 = '8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'

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


@dataclass(frozen=True)
class LearningPlanV1:
    enabled: bool = True
    mode: str = 'execute'  # execute or verify; verify cannot change P
    max_grants: int = 8


def _c_program(choice):
    if choice not in (11, 12):
        raise LiveBVRejected('P_CHOICE_OUTSIDE_BOUND')
    return (('ACC',(1,1)),('CMP',1),('EMIT',choice),('RESET',0))


def _credit_decision(*, verdict, original_version, current_version,
                     assessment_id, consumed, learn):
    """Pure admission; same assessment never grants twice, stale never grants."""
    if assessment_id in consumed:
        return 'DUPLICATE_ASSESSMENT'
    if verdict != 'NEGATIVE':
        return 'POSITIVE_NO_CHANGE' if verdict == 'POSITIVE' else 'VERDICT_INVALID'
    if original_version != current_version:
        return 'STALE_P_VERSION'
    if not learn.enabled:
        return 'LEARNING_DISABLED'
    if learn.mode != 'execute':
        return 'VERIFY_MODE'
    return 'GRANT'


def execute_native_learning_v1(case, fabric, tplan, pplan, mplan, lplan,
                               bv=LiveBVPlanV0e(), learn=LearningPlanV1()):
    """Actual PE + BV scheduler loop with synchronous P program revision.

    Scoped to the admitted T7 A/B/C binary semantic corpus. The A judgment
    is computed by original _compute_local and attached to original BV packets.
    Credit only on actual C receiver delivery, before same-clock C batches.
    This v1 is NOT the frozen v0e and does NOT change the original code.
    """
    nodes, owners = _admit(case, fabric)
    if type(learn) is not LearningPlanV1 or type(learn.enabled) is not bool or type(learn.max_grants) is not int or learn.max_grants<0 or learn.mode not in ('execute','verify'):
        raise LiveBVRejected('INVALID_LEARNING_PLAN')
    initial_c=nodes['C']
    possible=[arg for op,arg in initial_c.instructions if op=='EMIT']
    if len(possible)!=1 or possible[0] not in (11,12) or initial_c.instructions!=_c_program(possible[0]):
        raise LiveBVRejected('INADMISSIBLE_C_PROGRAM_TEMPLATE')
    if bv.assessor!='A' or bv.terminal_channel!=7:
        raise LiveBVRejected('SEMANTIC_ASSESSOR_MUST_BE_A')
    p_state={'owner':'C','domain':'P','choice':possible[0],'version':0,'grants':0}
    p_grants=[]; p_denials=[]; p_reads=[]; consumed_assessments=set()
    p_resource_tick=Counter()  # one PE service + one P unit per native P write
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

    def offer_feedback(aid, ids, sender, hop, ready, verdict):
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
                 'hop':hop,'ready':ready,'verdict':verdict})

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
                    'evidence_ids':list(item['evidence_ids']),
                    'verdict':item['verdict']})
                # The *actual* native reverse delivery may update C's P here,
                # before any forward batch is selected for this tick.
                if item['receiver']=='C' and independent:
                    assessment=next((a for a in assessments if a['id']==item['assessment_id']),None)
                    if assessment is None or assessment['observer']!='A' or assessment['verdict']!=item['verdict']:
                        raise LiveBVRejected('ASSESSMENT_CUSTODY_MISMATCH')
                    parents=set()
                    for parent_id in assessment['input_occurrences']:
                        if parent_id not in occurrences or occurrences[parent_id]['target']!='A':
                            raise LiveBVRejected('ASSESSMENT_PARENT_INVALID')
                        parents.update(occurrences[parent_id]['parents'])
                    if not set(item['evidence_ids']) or not set(item['evidence_ids']).issubset(parents):
                        raise LiveBVRejected('REVERSE_PROVENANCE_INVALID')
                    originating=[]
                    for origin_id in item['evidence_ids']:
                        origin=occurrences[origin_id]
                        if origin['source']!='C' or origin['target']!='B' or origin['delivered_at'] is None:
                            raise LiveBVRejected('C_ORIGIN_NOT_DELIVERED')
                        matched=[b for b in batches if b['node']=='C' and b['tick']==origin['emitted_at'] and (11 if origin['channel']==1 else 12) in b['outputs']]
                        if len(matched)!=1: raise LiveBVRejected('ORIGINAL_C_BATCH_MISSING')
                        originating.append(matched[0])
                    if len({b['P_version'] for b in originating})!=1:
                        raise LiveBVRejected('AMBIGUOUS_P_LINEAGE')
                    read=originating[0]
                    decision=_credit_decision(verdict=item['verdict'], original_version=read['P_version'],
                        current_version=p_state['version'],assessment_id=item['assessment_id'],
                        consumed=consumed_assessments,learn=learn)
                    consumed_assessments.add(item['assessment_id'])
                    if decision=='GRANT' and p_state['grants']>=learn.max_grants:
                        decision='P_BUDGET_EXHAUSTED'
                    # Atomic P resource admission belongs to THIS scheduler.
                    # Reserve one PE service and P memory unit on C's owner PE;
                    # the ordinary batch arbiter sees these units at this tick.
                    if decision=='GRANT':
                        n=p_resource_tick[now]+1
                        if (n>pe_caps[owners['C']] or n>pplan.fabric_slots_per_tick
                              or n>mem_pe_caps[owners['C']]
                              or n>mem_domain_caps['P']
                              or n>mplan.fabric_slots_per_tick):
                            decision='P_RESOURCE_ADMISSION_DENIED'
                    if decision=='GRANT':
                        old=p_state.copy()
                        next_choice=11 if old['choice']==12 else 12
                        p_state.update(choice=next_choice,version=old['version']+1,grants=old['grants']+1)
                        p_resource_tick[now]+=1
                        nodes['C']=replace(nodes['C'], instructions=_c_program(next_choice))
                        p_grants.append({'tick':now,'assessment_id':item['assessment_id'],
                          'packet_id':item['packet_id'],'causal_occurrences':list(item['evidence_ids']),
                          'source_A_verdict':item['verdict'],'P_from':old['version'],
                          'P_to':p_state['version'],'choice_from':old['choice'],'choice_to':next_choice,
                          'A_PE_assessment_tick':assessment['tick']})
                    else:
                        p_denials.append({'tick':now,'assessment_id':item['assessment_id'],
                                          'reason':decision,'source_A_verdict':item['verdict']})
                ancestors=set()
                for oid in item['evidence_ids']:
                    ancestors.update(occurrences[oid]['parents'])
                offer_feedback(item['assessment_id'],ancestors,item['receiver'],item['hop']+1,now,item['verdict'])

        service_used = Counter({owners['C']:p_resource_tick[now]}) if p_resource_tick[now] else Counter()
        mem_pe_used = Counter({owners['C']:p_resource_tick[now]}) if p_resource_tick[now] else Counter()
        mem_dom_used = Counter({'P':p_resource_tick[now]}) if p_resource_tick[now] else Counter()
        mem_total = p_resource_tick[now]
        pe_total = p_resource_tick[now]
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
                if nid=='C':
                    p_reads.append({'tick':now,'P_version':p_state['version'], 'P_choice':p_state['choice']})
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
                                'parents':list(parents),'raw':raw,'outputs':list(outs),
                                **({'P_version':p_state['version'],'P_choice':p_state['choice']} if nid=='C' else {})})
                for ch in outs:
                    emissions.append({'timestamp':now,'node_id':nid,'channel':ch})
                    edges=out.get((nid,ch),())
                    if not edges:
                        terminal.append({'timestamp':now,'node_id':nid,'channel':ch})
                        if nid==bv.assessor and ch==bv.terminal_channel and bv.enabled:
                            assessment_serial+=1
                            aid=f'a{assessment_serial}'
                            actual=[v for v in outs if v in (21,22)]
                            if len(actual)!=1 or nid!='A':
                                raise LiveBVRejected('A_PE_JUDGMENT_NOT_UNIQUE')
                            verdict='POSITIVE' if actual[0]==21 else 'NEGATIVE'
                            assessments.append({'id':aid,'observer':nid,'tick':now,
                                    'input_occurrences':list(parents), 'verdict':verdict,
                                    'A_PE_output':actual[0]})
                            offer_feedback(aid,parents,nid,1,now,verdict)
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
               'cross_inflight_end_tick':inflight_count,
               'P_learning_units':p_resource_tick[now]})
        now+=1

    if any(o['delivered_at'] is None for o in occurrences.values()):
        raise LiveBVRejected('unacknowledged forward occurrence')
    # End-to-end witness: P revision must have changed the actual C node PE
    # program in this exact scheduler, not an external audit shadow.
    if nodes['C'].instructions != _c_program(p_state['choice']):
        raise LiveBVRejected('P_PROGRAM_BINDING_DRIFT')
    if p_state['version']!=len(p_grants):
        raise LiveBVRejected('P_GRANT_VERSION_DRIFT')
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
                         'P_learning_service_units':sum(p_resource_tick.values()),
                         'P_learning_memory_units':sum(p_resource_tick.values()),
                         'contention':dict(sorted(contention.items()))},
            'learning':{'schema':'spk-native-learning-owned-P/v1','initial_choice':possible[0],
                        'final':p_state,'grants':p_grants,'denials':p_denials,'reads':p_reads,
                        'actual_PE_program_updated':bool(p_grants),
                        'source_feedback':'A_PE_ACTUAL_EMISSION_VIA_BV'},
            'constraints':['three-node-admission','global-logical-clock',
                           'atomic-conservative-memory','bounded-binary-P-learning','no-frozen-original-promotion',
                           'no-verified-global-credit','no-A3d-bitwise-equivalence',
                           'nonphysical-cost-proxy','not-N-node']}
