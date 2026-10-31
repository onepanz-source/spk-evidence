"""A3d: bounded link injection with sender-owned outboxes and backpressure.

Controller-approved conservative per-batch memory envelopes are granted over
finite per-PE, per-domain and shared capacity. A PE batch cannot execute until
all permits are acquired. These are logical access permits, not RAM accesses;
actual intent counts are checked against reserves after executing the batch.
The A3c conservative causal memory grants are preserved. A sender whose
remote occurrences cannot all enter the transport cannot execute a new batch.
No occurrence is silently dropped; injection delays causal delivery.
This is a finite logical link model, not a physical NoC.
"""
from __future__ import annotations
from dataclasses import dataclass
import heapq

from spk_architecture_v1.pe_execution_v1b import PEContextV1b, PELimitV1b, _admit, _compute_local
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a, TransportCapacityV1a, _admit_plan
from spk_architecture_v1.temporal_service_v1b import CausalServicePlanV1b, _valid_plan
from spk_architecture_v1.memory_access_v1b import INTENT_POLICY, issue_authority_v1b
from spk_architecture_v1.memory_projection_v1a import admit_memory_v1a, uniform_memory_plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.causal_memory_v1c import (
    CausalMemoryAdmissionV1c, CausalMemoryHorizonV1c,
    CausalMemoryPlanV1c, _valid_memory, _reservation,
)

SCHEMA = 'spk-architecture-causal-transport-backpressure/v1d'
DOMAINS = ('P', 'S', 'E', 'O')
DEFAULT_PRIORITY = ('E', 'S', 'P', 'O')

class CausalLinkAdmissionV1d(ValueError):
    pass


class CausalLinkHorizonV1d(RuntimeError):
    """Bound exceeded; no CLOSED result, retry or rollback claimed."""


class CausalOutboxCapacityV1d(RuntimeError):
    """One neuronal batch exceeds its sender's bounded outbox capacity."""


@dataclass(frozen=True)
class CausalLinkPlanV1d:
    link_slots_per_tick: int = 4096
    fabric_slots_per_tick: int = 4096
    max_outbox_per_pe: int = 128
    max_link_span_ticks: int = 4096


def _valid_links(link_plan):
    if type(link_plan) is not CausalLinkPlanV1d or any(
            type(x) is not int or x <= 0 for x in (
                link_plan.link_slots_per_tick,
                link_plan.fabric_slots_per_tick,
                link_plan.max_outbox_per_pe,
                link_plan.max_link_span_ticks)):
        raise CausalLinkAdmissionV1d('invalid logical link quota or horizon')


def execute_causal_transport_v1d(case, fabric, transport_plan: TransportPlanV1a,
                               pe_plan: CausalServicePlanV1b,
                               memory_plan: CausalMemoryPlanV1c,
                               link_plan: CausalLinkPlanV1d,
                               *, max_batches=128, max_events=4096):
    nodes, owners = _admit(case, fabric)
    _admit_plan(transport_plan)
    _valid_links(link_plan)
    pe_caps = _valid_plan(fabric, pe_plan)
    mem_pe_caps, mem_domains = _valid_memory(fabric, memory_plan)
    if not (type(max_batches) is int and max_batches > 0
            and type(max_events) is int and max_events > 0):
        raise CausalMemoryAdmissionV1c('invalid execution bounds')
    # Reuse pre-execution A2a PE domain admission; A2b policy is read from
    # controller-issued authority, not asserted by caller-side transactions.
    admission = admit_memory_v1a(case, fabric, uniform_service_plan_v1c(
        fabric, pe_slots=128, fabric_slots_per_tick=128,
        queue_event_capacity_per_pe=max_events),
        uniform_memory_plan_v1a(fabric, event_units=max_events,
                                observation_units=8192), max_batches=max_batches)
    authority = issue_authority_v1b(admission)
    allow = {(g.pe_id, g.domain, intent): g.activity
             for g in authority.grants for intent in g.allowed_intents}

    pes = {pid: PEContextV1b(pid) for pid in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owners[nid]].states[nid] = [node.initial_raw, 0]
    for e in case.events:
        pes[owners[e.node_id]].enqueue(e.timestamp, e.node_id, e.channel)
    outgoing = {}
    for edge in fabric.static_routes:
        outgoing.setdefault((edge.source_node, edge.source_channel), []).append(edge)
    inflight, ordinal, peak, delivered = [], 0, 0, 0
    outboxes = {pid: [] for pid in fabric.pe_ids}
    link_grants, outbox_timeline = [], []
    source_blocked_ticks = max_outbox_occupancy = link_wait = 0
    link_capacity_blocked = inflight_capacity_blocked = 0
    emissions, terminal, batches, routes, transfers, deliveries = [], [], [], [], [], []
    grants, service_timeline = [], []
    mem_ledger, actual_accesses, memory_timeline = [], [], []
    # Pending envelope holds PE custody while memory service spans ticks.
    memory_pending = {}  # batch key -> [[pe, domain, intent, remaining], ...]
    memory_completed_at = {}  # moment all memory permits were acquired
    memory_head_since = {}  # first tick at which this batch was PE queue head
    processed_batches = processed_events = 0
    batch_wait = weighted_wait = pe_stalls = fabric_stalls = 0
    memory_wait = 0

    heads = [h[0] for pe in pes.values() if (h := pe.head()) is not None]
    if not heads:
        first_tick = now = 0
    else:
        first_tick = now = min(heads)

    while True:
        heads = [(h[0], h[1], pid) for pid, pe in pes.items()
                 if (h := pe.head()) is not None]
        if not heads and not inflight and not any(outboxes.values()):
            break
        if now - first_tick >= min(memory_plan.max_service_span_ticks,
                                  pe_plan.max_service_span_ticks,
                                  link_plan.max_link_span_ticks):
            raise CausalLinkHorizonV1d('max_link_span_ticks: no closed result')
        while inflight and inflight[0][0] <= now:
            due, _, target_pe, target_node, channel = heapq.heappop(inflight)
            if due != now:
                raise AssertionError('late in-flight delivery')
            pes[target_pe].enqueue(now, target_node, channel)
            delivered += 1
            deliveries.append({'delivery_timestamp': now, 'target_node': target_node,
                               'target_pe': target_pe, 'target_channel': channel})

        # An outbox occurrence remains owned by the sender until a link grant.
        # Link credits and the in-flight capacity are renewed/rechecked per tick.
        link_used = {}
        link_fabric_used = 0

        def flush_outboxes():
            nonlocal ordinal, peak, link_fabric_used, link_wait
            # FIFO on each sender; no head-of-line bypass on that PE.
            for sender in fabric.pe_ids:
                queue = outboxes[sender]
                while queue:
                    item = queue[0]
                    edge = item['edge']
                    key = (sender, edge.target_pe)
                    if (link_used.get(key, 0) >= link_plan.link_slots_per_tick
                            or link_fabric_used >= link_plan.fabric_slots_per_tick
                            or len(inflight) >= transport_plan.max_inflight_occurrences):
                        break
                    queue.pop(0)
                    link_used[key] = link_used.get(key, 0) + 1
                    link_fabric_used += 1
                    due = now + edge.delay_ticks + transport_plan.cross_pe_extra_ticks
                    heapq.heappush(inflight, (due, ordinal, edge.target_pe,
                                              edge.target_node, edge.target_channel))
                    ordinal += 1
                    peak = max(peak, len(inflight))
                    link_wait += now - item['emission_timestamp']
                    link_grants.append({'tick': now, 'emission_timestamp': item['emission_timestamp'],
                                        'source_pe': sender, 'target_pe': edge.target_pe,
                                        'source_node': item['source_node'],
                                        'source_channel': item['source_channel'],
                                        'target_node': edge.target_node,
                                        'target_channel': edge.target_channel,
                                        'delivery_timestamp': due,
                                        'congestion_wait_ticks': now - item['emission_timestamp']})
                    record_route(item, due, True)

        def record_route(item, due, cross):
            edge = item['edge']
            emitted = item['emission_timestamp']
            extra = transport_plan.cross_pe_extra_ticks if cross else 0
            route = {'emission_timestamp': emitted, 'source_node': item['source_node'],
                     'source_channel': item['source_channel'], 'delivery_timestamp': due,
                     'target_node': edge.target_node,
                     'target_channel': edge.target_channel,
                     'delay_ticks': due - emitted}
            routes.append(route)
            transfers.append({**route, 'source_pe': item['source_pe'],
                              'target_pe': edge.target_pe, 'cross_pe': cross,
                              'declared_delay_ticks': edge.delay_ticks,
                              'extra_latency_ticks': extra})

        flush_outboxes()

        mem_pe_used = {pe: 0 for pe in fabric.pe_ids}
        mem_domain_used = {dom: 0 for dom in DOMAINS}
        mem_fabric_used = 0
        pe_used = {pe: 0 for pe in fabric.pe_ids}
        pe_fabric_used = 0

        def replenish():
            nonlocal mem_fabric_used
            keys = []
            for pid, pe in pes.items():
                head = pe.head()
                if head is None or head[0] > now or outboxes[pid]:
                    continue
                ready, nid = head
                k = (ready, nid, pid)
                keys.append(k)
                if k not in memory_pending:
                    memory_head_since[k] = now
                    envelope = _reservation(nodes[nid], pe.pending[(ready, nid)],
                                            pid, outgoing)
                    for target, dom, intent, qty in envelope:
                        if INTENT_POLICY[intent][0] != dom or (
                                target, dom, intent) not in allow:
                            raise CausalMemoryAdmissionV1c('controller denied live access intent')
                    memory_pending[k] = [[p, dom, intent, qty] for p, dom, intent, qty in envelope]
            for dom in memory_plan.priority_order:
                for k in sorted(keys):
                    for row in memory_pending[k]:
                        target, domain, intent, remain = row
                        if domain != dom or remain == 0:
                            continue
                        amount = min(remain, mem_pe_caps[target] - mem_pe_used[target],
                                     mem_domains[domain] - mem_domain_used[domain],
                                     memory_plan.fabric_slots_per_tick - mem_fabric_used)
                        if amount <= 0:
                            continue
                        row[3] -= amount
                        mem_pe_used[target] += amount
                        mem_domain_used[domain] += amount
                        mem_fabric_used += amount
                        mem_ledger.append({'tick': now, 'ready_timestamp': k[0],
                                           'node_id': k[1], 'source_pe': k[2],
                                           'pe_id': target, 'domain': domain,
                                           'intent': intent, 'units': amount})
            for k in keys:
                if k not in memory_completed_at and all(
                        row[3] == 0 for row in memory_pending[k]):
                    memory_completed_at[k] = now

        while pe_fabric_used < pe_plan.fabric_slots_per_tick:
            replenish()
            eligible = [(h[0], h[1], pid) for pid, pe in pes.items()
                        if pe_used[pid] < pe_caps[pid] and not outboxes[pid]
                        and (h := pe.head()) is not None and h[0] <= now
                        and all(row[3] == 0 for row in memory_pending[(h[0], h[1], pid)])]
            if not eligible:
                break
            ready, nid, pid = min(eligible)
            pe = pes[pid]
            queued = pe.pending[(ready, nid)]
            if processed_batches >= max_batches:
                raise PELimitV1b('max_batches')
            if processed_events + len(queued) > max_events:
                raise PELimitV1b('max_events')
            key, channels = pe.next_batch()
            if key != (ready, nid) or now < pe.states[nid][1]:
                raise AssertionError('invalid PE dequeue or backward time')
            envelope = memory_pending.pop((ready, nid, pid))
            memory_ready_tick = memory_completed_at.pop((ready, nid, pid))
            memory_head_tick = memory_head_since.pop((ready, nid, pid))
            credit = {(target, dom, intent): sum(
                entry['units'] for entry in mem_ledger
                if (entry['ready_timestamp'], entry['node_id'], entry['source_pe'])
                == (ready, nid, pid) and (entry['pe_id'], entry['domain'], entry['intent'])
                == (target, dom, intent)) for target, dom, intent, _ in envelope}
            # Fail closed before state mutation if one batch cannot fit the
            # bounded sender outbox even when completely empty. Never truncate.
            preview = _compute_local(nodes[nid], pe.states[nid], now, channels)
            remote_size = sum(1 for ch in preview[2]
                              for edge in outgoing.get((nid, ch), ())
                              if edge.target_pe != pid)
            if remote_size > link_plan.max_outbox_per_pe:
                raise CausalOutboxCapacityV1d('batch remote fanout exceeds outbox capacity')
            processed_events += len(channels)
            processed_batches += 1
            pe_used[pid] += 1
            pe_fabric_used += 1
            wait = now - ready
            batch_wait += wait
            weighted_wait += wait * len(channels)
            memory_wait += memory_ready_tick - memory_head_tick
            raw, guard, outputs = _compute_local(nodes[nid], pe.states[nid], now, channels)
            pe.states[nid] = [raw, now]
            actual = {(pid, 'P', 'PROGRAM_REFERENCE'): len(nodes[nid].instructions),
                      (pid, 'S', 'STATE_LOAD'): 1,
                      (pid, 'S', 'STATE_COMMIT'): 1,
                      (pid, 'E', 'BATCH_CONSUME'): len(channels),
                      (pid, 'O', 'OBSERVATION_RECORD'): 1,
                      (pid, 'E', 'EMISSION_RECORD'): len(outputs)}
            for ch in outputs:
                emission = {'timestamp': now, 'node_id': nid, 'channel': ch}
                emissions.append(emission)
                edges = outgoing.get((nid, ch), ())
                if not edges:
                    terminal.append(emission)
                for edge in edges:
                    target = (edge.target_pe, 'E', 'ROUTE_ENQUEUE')
                    actual[target] = actual.get(target, 0) + 1
                    obs = (pid, 'O', 'OBSERVATION_RECORD')
                    actual[obs] = actual.get(obs, 0) + 1
                    cross = pid != edge.target_pe
                    extra = transport_plan.cross_pe_extra_ticks if cross else 0
                    due = now + edge.delay_ticks + extra
                    if due <= now:
                        raise AssertionError('non-positive causal route delay')
                    item = {'emission_timestamp': now, 'source_node': nid,
                            'source_channel': ch, 'source_pe': pid, 'edge': edge}
                    if cross:
                        outboxes[pid].append(item)
                        max_outbox_occupancy = max(max_outbox_occupancy,
                                                   len(outboxes[pid]))
                        flush_outboxes()
                    else:
                        pes[edge.target_pe].enqueue(due, edge.target_node,
                                                    edge.target_channel)
                        record_route(item, due, False)
            for k, value in sorted(actual.items()):
                if value > credit.get(k, 0):
                    raise AssertionError('actual memory use exceeded controller reserve')
                if value:
                    actual_accesses.append({'tick': now, 'node_id': nid,
                                            'pe_id': k[0], 'domain': k[1],
                                            'intent': k[2], 'units': value})
            grants.append({'service_timestamp': now, 'ready_timestamp': ready,
                           'node_id': nid, 'pe_id': pid, 'channels': list(channels),
                           'wait_ticks': wait})
            batches.append({'timestamp': now, 'node_id': nid, 'channels': list(channels),
                            'final_raw': raw, 'final_guard': guard,
                            'output_channels': list(outputs)})
        remaining = [(h[0], h[1], pid) for pid, pe in pes.items()
                     if (h := pe.head()) is not None and h[0] <= now]
        # Sender link backpressure has its own metric. Do not relabel those
        # deferred heads as PE/fabric computational capacity stalls.
        computationally_waiting = [k for k in remaining if not outboxes[k[2]]]
        if computationally_waiting:
            if pe_fabric_used == pe_plan.fabric_slots_per_tick:
                fabric_stalls += len(computationally_waiting)
            elif any(pe_used[k[2]] >= pe_caps[k[2]] for k in computationally_waiting):
                pe_stalls += len(computationally_waiting)
        # Outbox stall is accounted separately from computation or memory wait.
        # Link congestion never discards or duplicates an occurrence.
        blocked = sum(bool(queue) for queue in outboxes.values())
        source_blocked_ticks += blocked
        if blocked:
            if link_fabric_used >= link_plan.fabric_slots_per_tick:
                link_capacity_blocked += blocked
            elif len(inflight) >= transport_plan.max_inflight_occurrences:
                inflight_capacity_blocked += blocked
            else:
                link_capacity_blocked += blocked
        outbox_timeline.append({'tick': now, 'outstanding': sum(map(len, outboxes.values())),
                                'blocked_sources': blocked, 'link_grants': link_fabric_used,
                                'inflight': len(inflight)})
        service_timeline.append({'tick': now, 'fabric_grants': pe_fabric_used,
                                 'pe_grants': [[pid, pe_used[pid]] for pid in fabric.pe_ids],
                                 'ready_heads_deferred': len(remaining)})
        memory_timeline.append({'tick': now, 'fabric_units': mem_fabric_used,
                                'pe_units': [[pid, mem_pe_used[pid]] for pid in fabric.pe_ids],
                                'domain_units': [[d, mem_domain_used[d]] for d in DOMAINS]})
        heads = [h[0] for pe in pes.values() if (h := pe.head()) is not None]
        if not heads and not inflight and not any(outboxes.values()):
            break
        if any(outboxes.values()):
            # With sender backpressure active, link credits recur next tick.
            now += 1
        else:
            due = min(heads + ([inflight[0][0]] if inflight else []))
            now = now + 1 if due <= now else due
    if (processed_events != len(case.events) + len(routes)
            or delivered != sum(x['cross_pe'] for x in transfers)
            or len(memory_pending) != 0 or any(outboxes.values())
            or len(link_grants) != delivered):
        raise AssertionError('causal event/memory custody conservation')
    result = {'emissions': emissions, 'terminal_outputs': terminal,
              'states': [{'node_id': n.node_id,
                          'raw': pes[owners[n.node_id]].states[n.node_id][0],
                          'last_timestamp': pes[owners[n.node_id]].states[n.node_id][1]}
                         for n in case.nodes],
              'processed_batches': processed_batches, 'processed_events': processed_events,
              'observations': {'batches': batches, 'routes': routes}}
    return {'schema': SCHEMA, 'result': result,
            'memory': {'reservation_ledger': mem_ledger,
                       'actual_accesses': actual_accesses,
                       'timeline': memory_timeline,
                       'batch_memory_wait_ticks': memory_wait,
                       'reserved_units': sum(x['units'] for x in mem_ledger),
                       'actual_units': sum(x['units'] for x in actual_accesses),
                       'epoch_id': admission['epoch_id']},
            'service': {'grants': grants, 'timeline': service_timeline,
                        'batch_wait_ticks': batch_wait,
                        'event_weighted_wait_ticks': weighted_wait,
                        'fabric_stall_incidents': fabric_stalls,
                        'pe_stall_incidents': pe_stalls},
            'transport': {'transfers': transfers, 'delivery_log': deliveries,
                          'cross_pe_occurrences': delivered,
                          'local_occurrences': len(transfers)-delivered,
                          'delivered_cross_pe_occurrences': delivered,
                          'peak_inflight_occurrences': peak,
                          'remaining_inflight_occurrences': len(inflight),
                          'link_grants': link_grants, 'outbox_timeline': outbox_timeline,
                          'outstanding_outbox_occurrences': sum(map(len, outboxes.values())),
                          'max_outbox_occupancy': max_outbox_occupancy,
                          'source_blocked_ticks': source_blocked_ticks,
                          'link_capacity_blocked': link_capacity_blocked,
                          'inflight_capacity_blocked': inflight_capacity_blocked,
                          'link_congestion_wait_ticks': link_wait},
            'pe_snapshots': {pid: {'node_count': len(pe.states), 'nodes': sorted(pe.states)}
                             for pid, pe in pes.items()}}
