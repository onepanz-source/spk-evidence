"""BV v4m-v4o: separate, bounded native *counterfactual* execution branch.

Native v0e remains untouched. External synthetic ACK requests take PE, O/E
memory, directional/fabric link credit and in-flight custody BEFORE forward
service; all downstream forward/BV operations are executed anew, rather than
relabelled or moved in a static native ledger. No actor ACK provenance, owner
consumption, learning, admission to Architecture v1 or liveness is asserted.
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
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e

SCHEMA = 'spk-bv-derived-native-ACK-causal-replay/research-v4m-v4o'
STATUS = 'CAUSAL_NATIVE_REEXECUTION_WITH_EXOGENOUS_ACK_NO_ACTOR_CREDIT'


class CausalProbeRejected(ValueError):
    """Invalid experimental request or bounded execution cannot be completed."""


@dataclass(frozen=True)
class SyntheticACKRequest:
    identity: str
    tick: int
    source_pe: str = 'PE0'
    target_pe: str = 'PE1'


def _validate_requests(requests, fabric, start, bv):
    if type(requests) is not tuple:
        raise CausalProbeRejected('requests must be an immutable tuple')
    ids = set()
    prior = None
    for r in requests:
        if (type(r) is not SyntheticACKRequest or type(r.identity) is not str or
                not r.identity or r.identity in ids or type(r.tick) is not int or
                r.tick < start or (prior is not None and r.tick < prior) or
                type(r.source_pe) is not str or type(r.target_pe) is not str or
                r.source_pe not in fabric.pe_ids or
                r.target_pe not in fabric.pe_ids or
                r.source_pe == r.target_pe or r.source_pe != 'PE0' or
                r.target_pe != 'PE1'):
            raise CausalProbeRejected('forged, unordered or unsupported synthetic ACK')
        ids.add(r.identity)
        prior = r.tick
    if len(requests) > bv.max_packets:
        raise CausalProbeRejected('synthetic ACK quota exhausted')


def execute_causal_probe(case, fabric, tplan, pplan, mplan, lplan,
                         bv: LiveBVPlanV0e, requests: tuple):
    """Actually rerun local neuron computation and BV/forward link arbitration.

    External request arrival is intentionally NOT derived from the changed
    output of the run. Credit here means only simulated PE/link transport.
    An ACK arrival does not mutate a receiver, train a neuron or discharge a
    derived actor's FIFO entry.
    """
    nodes, owners = _admit(case, fabric)
    _admit_plan(tplan)
    pe_caps = _valid_plan(fabric, pplan)
    mem_pe_caps, mem_domain_caps = _valid_memory(fabric, mplan)
    _valid_links(lplan)
    if (type(bv) is not LiveBVPlanV0e or type(bv.enabled) is not bool or
            bv.priority not in ('forward-first', 'feedback-first') or
            bv.assessor not in nodes or
            any(type(x) is not int or x <= 0 for x in (
                bv.hop_latency, bv.max_hops, bv.max_packets,
                bv.max_occurrences, bv.max_ticks, bv.max_batches, bv.max_events)) or
            type(bv.terminal_channel) is not int or bv.terminal_channel < 0):
        raise CausalProbeRejected('invalid native causal probe plan')
    start = min((e.timestamp for e in case.events), default=0)
    _validate_requests(requests, fabric, start, bv)
    outgoing = defaultdict(list)
    for edge in fabric.static_routes:
        outgoing[(edge.source_node, edge.source_channel)].append(edge)
    states = {nid: [n.initial_raw, 0] for nid, n in nodes.items()}
    pending = defaultdict(list)
    for event in case.events:
        pending[(event.timestamp, event.node_id)].append((event.channel, None))
    ready_feedback = []
    outboxes = {pe: [] for pe in fabric.pe_ids}
    inflight = []
    inflight_count = serial = occurrence_serial = assessment_serial = 0
    feedback_serial = ack_cursor = 0
    ready_acks = []
    arrived_receivers = set()
    occurrences = {}
    assessments = []
    f_grants, b_grants, ack_grants, ack_deliveries = [], [], [], []
    batches, resource_timeline, terminal, emissions, bv_deliveries = [], [], [], [], []
    contention = Counter()
    occupancy_peak = reserved_memory = batch_count = event_count = 0
    now = start

    def enqueue_inflight(due, kind, payload, cross):
        nonlocal serial, inflight_count, occupancy_peak
        if due <= now:
            raise CausalProbeRejected('noncausal delivery')
        if cross:
            if inflight_count >= tplan.max_inflight_occurrences:
                return False
            inflight_count += 1
            occupancy_peak = max(occupancy_peak, inflight_count)
        heapq.heappush(inflight, (due, serial, kind, payload, cross))
        serial += 1
        return True

    def offer_feedback(aid, ids, sender, hop, ready):
        nonlocal feedback_serial
        if not bv.enabled or not ids:
            return
        if hop > bv.max_hops:
            raise CausalProbeRejected('feedback ancestry exceeds max_hops')
        destinations = defaultdict(set)
        for oid in ids:
            if oid not in occurrences or occurrences[oid]['target'] != sender:
                raise CausalProbeRejected('forged feedback causal parent')
            destinations[occurrences[oid]['source']].add(oid)
        for dest in sorted(destinations):
            if feedback_serial >= bv.max_packets:
                raise CausalProbeRejected('native BV packet bound exhausted')
            feedback_serial += 1
            ready_feedback.append({
                'packet_id': f'bv{feedback_serial}', 'assessment_id': aid,
                'sender': sender, 'receiver': dest,
                'evidence_ids': tuple(sorted(destinations[dest])),
                'hop': hop, 'ready': ready})

    while (pending or inflight or any(outboxes.values()) or ready_feedback or
           ready_acks or ack_cursor < len(requests)):
        if now - start >= min(bv.max_ticks, pplan.max_service_span_ticks,
                              mplan.max_service_span_ticks, lplan.max_link_span_ticks):
            raise CausalProbeRejected('causal probe finite execution horizon exceeded')
        while ack_cursor < len(requests) and requests[ack_cursor].tick <= now:
            ready_acks.append(requests[ack_cursor])
            ack_cursor += 1
        while inflight and inflight[0][0] <= now:
            due, _, kind, item, cross = heapq.heappop(inflight)
            if due != now:
                raise CausalProbeRejected('late causal delivery')
            if cross:
                inflight_count -= 1
            if kind == 'spike':
                pending[(now, item['target'])].append((item['channel'], item['id']))
                occurrences[item['id']]['delivered_at'] = now
            elif kind == 'bv':
                key = (item['assessment_id'], item['receiver'])
                independent = key not in arrived_receivers
                arrived_receivers.add(key)
                bv_deliveries.append({
                    'tick': now, 'assessment_id': item['assessment_id'],
                    'receiver': item['receiver'], 'sender': item['sender'],
                    'packet_id': item['packet_id'],
                    'independent_receiver': independent,
                    'evidence_ids': list(item['evidence_ids'])})
                ancestors = set()
                for oid in item['evidence_ids']:
                    ancestors.update(occurrences[oid]['parents'])
                offer_feedback(item['assessment_id'], ancestors,
                               item['receiver'], item['hop'] + 1, now)
            elif kind == 'synthetic-ack':
                ack_deliveries.append({'identity': item.identity,
                                       'tick': now, 'target_pe': item.target_pe,
                                       'actor_credit_applied': False})
            else:
                raise CausalProbeRejected('unexpected in-flight kind')
        service_used = Counter()
        mem_pe_used = Counter()
        mem_dom_used = Counter()
        mem_total = pe_total = 0
        link_used = Counter()
        link_fabric_used = 0

        # One oldest EXOGENOUS request takes an *actual* simulated PE, O/E,
        # direction/fabric-link and in-flight service grant atomically. It is
        # scheduled ahead of native forward/BV; this changes their causal run.
        if ready_acks:
            ack = ready_acks[0]
            src, dst = ack.source_pe, ack.target_pe
            if (pe_caps[src] > 0 and pplan.fabric_slots_per_tick > 0 and
                    mem_pe_caps[src] > 0 and mem_pe_caps[dst] > 0 and
                    mplan.fabric_slots_per_tick >= 2 and
                    mem_domain_caps['O'] > 0 and mem_domain_caps['E'] > 0 and
                    lplan.fabric_slots_per_tick > 0 and
                    lplan.link_slots_per_tick > 0 and
                    inflight_count < tplan.max_inflight_occurrences):
                ready_acks.pop(0)
                service_used[src] += 1
                pe_total += 1
                mem_pe_used[src] += 1
                mem_pe_used[dst] += 1
                mem_dom_used['O'] += 1
                mem_dom_used['E'] += 1
                mem_total += 2
                link_used[(src, dst)] += 1
                link_fabric_used += 1
                due = now + bv.hop_latency
                if not enqueue_inflight(due, 'synthetic-ack', ack, True):
                    raise CausalProbeRejected('synthetic ACK transport grant rollback')
                ack_grants.append({'identity': ack.identity, 'tick': now,
                                   'ready': ack.tick, 'wait': now - ack.tick,
                                   'delivered_at': due, 'source_pe': src,
                                   'target_pe': dst})
            else:
                contention['synthetic_ack_transport_blocked'] += 1

        while True:
            candidates = sorted((ready, nid) for ready, nid in pending
                if ready <= now and not outboxes[owners[nid]] and
                service_used[owners[nid]] < pe_caps[owners[nid]])
            if not candidates or pe_total >= pplan.fabric_slots_per_tick:
                break
            accepted = False
            for ready, nid in candidates:
                pid = owners[nid]
                items = pending[(ready, nid)]
                envelope = _reservation(nodes[nid], [ch for ch, _ in items],
                                        pid, outgoing)
                pe_mem = Counter()
                dom_mem = Counter()
                for target, domain, _, quantity in envelope:
                    pe_mem[target] += quantity
                    dom_mem[domain] += quantity
                needed = sum(pe_mem.values())
                if (mem_total + needed > mplan.fabric_slots_per_tick or
                        any(mem_pe_used[pe] + q > mem_pe_caps[pe]
                            for pe, q in pe_mem.items()) or
                        any(mem_dom_used[d] + q > mem_domain_caps[d]
                            for d, q in dom_mem.items())):
                    contention['forward_memory'] += 1
                    continue
                if batch_count >= bv.max_batches or event_count + len(items) > bv.max_events:
                    raise CausalProbeRejected('forward batch/event quota exhausted')
                channels = [ch for ch, _ in items]
                if now < states[nid][1]:
                    raise CausalProbeRejected('backward native neuron state timestamp')
                raw, guard, outs = _compute_local(nodes[nid], states[nid], now, channels)
                remote = sum(1 for ch in outs for edge in outgoing.get((nid, ch), ())
                             if edge.target_pe != pid)
                if remote > lplan.max_outbox_per_pe:
                    raise CausalProbeRejected('native output buffer overflow')
                del pending[(ready, nid)]
                states[nid] = [raw, now]
                batch_count += 1
                event_count += len(items)
                pe_total += 1
                service_used[pid] += 1
                reserved_memory += needed
                mem_total += needed
                for pe, q in pe_mem.items():
                    mem_pe_used[pe] += q
                for domain, q in dom_mem.items():
                    mem_dom_used[domain] += q
                parents = tuple(sorted({oid for _, oid in items if oid is not None}))
                batches.append({'tick': now, 'ready': ready, 'node': nid,
                                'channels': sorted(channels), 'parents': list(parents),
                                'raw': raw, 'outputs': list(outs)})
                for ch in outs:
                    emissions.append({'timestamp': now, 'node_id': nid, 'channel': ch})
                    edges = outgoing.get((nid, ch), ())
                    if not edges:
                        terminal.append({'timestamp': now, 'node_id': nid, 'channel': ch})
                        if nid == bv.assessor and ch == bv.terminal_channel and bv.enabled:
                            assessment_serial += 1
                            aid = f'a{assessment_serial}'
                            assessments.append({'id': aid, 'observer': nid, 'tick': now,
                                                'input_occurrences': list(parents)})
                            offer_feedback(aid, parents, nid, 1, now)
                    for edge in edges:
                        if occurrence_serial >= bv.max_occurrences:
                            raise CausalProbeRejected('native occurrence quota exhausted')
                        occurrence_serial += 1
                        oid = f'r{occurrence_serial}'
                        occ = {'id': oid, 'source': nid, 'target': edge.target_node,
                               'source_pe': pid, 'target_pe': edge.target_pe,
                               'channel': edge.target_channel, 'emitted_at': now,
                               'delivered_at': None, 'parents': parents,
                               'delay': edge.delay_ticks}
                        occurrences[oid] = occ
                        if pid == edge.target_pe:
                            if not enqueue_inflight(now + edge.delay_ticks,
                                                    'spike', occ, False):
                                raise CausalProbeRejected('local in-flight denial')
                        else:
                            outboxes[pid].append(occ)
                accepted = True
                break
            if not accepted:
                break

        # Shared native and synthetic link credits: the synthetic grant has
        # already consumed the first slot. Native traffic can spill to future
        # ticks and all dependent neuron events are recomputed.
        while True:
            forward = [outboxes[pe][0] for pe in fabric.pe_ids if outboxes[pe]]
            reverse = sorted((x for x in ready_feedback if x['ready'] <= now),
                             key=lambda x: (x['ready'], x['packet_id']))
            offers = ([('spike', x) for x in forward] + [('bv', x) for x in reverse]
                      if bv.priority == 'forward-first' else
                      [('bv', x) for x in reverse] + [('spike', x) for x in forward])
            if not offers or link_fabric_used >= lplan.fabric_slots_per_tick:
                if offers:
                    contention['fabric_link'] += len(offers)
                break
            selected = False
            for kind, item in offers:
                src = item['source_pe'] if kind == 'spike' else owners[item['sender']]
                dst = item['target_pe'] if kind == 'spike' else owners[item['receiver']]
                if src == dst:
                    raise CausalProbeRejected('native cross-PE link required')
                if link_used[(src, dst)] >= lplan.link_slots_per_tick:
                    contention['directional_link'] += 1
                    continue
                if inflight_count >= tplan.max_inflight_occurrences:
                    contention['inflight'] += 1
                    continue
                if kind == 'bv':
                    if service_used[src] >= pe_caps[src] or pe_total >= pplan.fabric_slots_per_tick:
                        contention['bv_service'] += 1
                        continue
                    if (mem_total + 2 > mplan.fabric_slots_per_tick or
                            mem_pe_used[src] + 1 > mem_pe_caps[src] or
                            mem_pe_used[dst] + 1 > mem_pe_caps[dst] or
                            mem_dom_used['O'] + 1 > mem_domain_caps['O'] or
                            mem_dom_used['E'] + 1 > mem_domain_caps['E']):
                        contention['bv_memory'] += 1
                        continue
                    pe_total += 1
                    service_used[src] += 1
                    mem_total += 2
                    mem_pe_used[src] += 1
                    mem_pe_used[dst] += 1
                    mem_dom_used['O'] += 1
                    mem_dom_used['E'] += 1
                    ready_feedback.remove(item)
                    due = now + bv.hop_latency
                    b_grants.append({'tick': now, 'delivered_at': due,
                                     'packet_id': item['packet_id'],
                                     'assessment_id': item['assessment_id'],
                                     'source_pe': src, 'target_pe': dst,
                                     'sender': item['sender'], 'receiver': item['receiver'],
                                     'wait': now - item['ready']})
                    if not enqueue_inflight(due, 'bv', item, True):
                        raise CausalProbeRejected('BV inflight accounting failure')
                else:
                    outboxes[src].pop(0)
                    due = now + item['delay'] + tplan.cross_pe_extra_ticks
                    if not enqueue_inflight(due, 'spike', item, True):
                        raise CausalProbeRejected('forward inflight accounting failure')
                    f_grants.append({'tick': now, 'delivered_at': due,
                                     'id': item['id'], 'source_pe': src,
                                     'target_pe': dst, 'source': item['source'],
                                     'target': item['target'],
                                     'wait': now - item['emitted_at']})
                link_used[(src, dst)] += 1
                link_fabric_used += 1
                selected = True
                break
            if not selected:
                break
        if (pe_total > pplan.fabric_slots_per_tick or
                any(service_used[pe] > pe_caps[pe] for pe in fabric.pe_ids) or
                mem_total > mplan.fabric_slots_per_tick or
                any(mem_pe_used[pe] > mem_pe_caps[pe] for pe in fabric.pe_ids) or
                any(mem_dom_used[d] > mem_domain_caps[d] for d in mem_domain_caps) or
                link_fabric_used > lplan.fabric_slots_per_tick or
                any(link_used[direction] > lplan.link_slots_per_tick
                    for direction in link_used) or
                inflight_count > tplan.max_inflight_occurrences):
            raise CausalProbeRejected('PE, memory, link or inflight oversubscription')
        resource_timeline.append({
            'tick': now,
            'forward_computations': sum(b['tick'] == now for b in batches),
            'feedback_sends': sum(b['tick'] == now for b in b_grants),
            'synthetic_ack_sends': sum(a['tick'] == now for a in ack_grants),
            'pe_service_total': pe_total,
            'pe_service_by_pe': dict(sorted(service_used.items())),
            'memory_total': mem_total,
            'memory_by_pe': dict(sorted(mem_pe_used.items())),
            'memory_by_domain': dict(sorted(mem_dom_used.items())),
            'link_total': link_fabric_used,
            'link_by_direction': [[a, b, n] for (a, b), n in sorted(link_used.items())],
            'cross_inflight_end_tick': inflight_count})
        now += 1
    if (len(ack_deliveries) != len(requests) or
            any(o['delivered_at'] is None for o in occurrences.values())):
        raise CausalProbeRejected('unresolved ACK or forward occurrence at termination')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'native': {
            'policy': bv.priority, 'enabled': bv.enabled,
            'forward': {'states': {n: states[n][0] for n in sorted(nodes)},
                        'batches': batches, 'emissions': emissions,
                        'terminal': terminal, 'processed_events': event_count,
                        'processed_batches': batch_count,
                        'link_grants': f_grants,
                        'occurrences': list(occurrences.values())},
            'feedback': {'assessments': assessments, 'link_grants': b_grants,
                         'deliveries': bv_deliveries,
                         'unique_receiver_votes': len(arrived_receivers)},
            'resources': {'timeline': resource_timeline,
                          'peak_cross_inflight': occupancy_peak,
                          'forward_link_grants': len(f_grants),
                          'bv_link_grants': len(b_grants),
                          'bv_service_units': len(b_grants),
                          'bv_memory_units': 2 * len(b_grants),
                          'forward_reserved_memory_units': reserved_memory,
                          'contention': dict(sorted(contention.items()))},
        },
        'synthetic_ack': {'requests': len(requests),
                          'transport_grants': ack_grants,
                          'transport_deliveries': ack_deliveries,
                          'applied_actor_credits': 0,
                          'owner_ACK_FIFOs_decremented': 0},
        'native_source_timeline_frozen': False,
        'native_forward_BV_causally_reexecuted': True,
        'real_actor_ACK_evidence': False,
        'native_v0e_modified': False,
    }
