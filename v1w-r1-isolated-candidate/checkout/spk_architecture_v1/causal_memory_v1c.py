"""A3c: causal batch memory reservations before PE computation.

Controller-approved conservative per-batch memory envelopes are granted over
finite per-PE, per-domain and shared capacity. A PE batch cannot execute until
all permits are acquired. These are logical access permits, not RAM accesses;
actual intent counts are checked against reserves after executing the batch.
The global arbiter and positive logical route delays remain A3b's.
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

SCHEMA = 'spk-architecture-causal-memory-permits/v1c'
DOMAINS = ('P', 'S', 'E', 'O')
DEFAULT_PRIORITY = ('E', 'S', 'P', 'O')

class CausalMemoryAdmissionV1c(ValueError):
    pass

class CausalMemoryHorizonV1c(RuntimeError):
    """No completed execution claim after a causal service horizon failure."""

@dataclass(frozen=True)
class CausalMemoryPlanV1c:
    pe_slots: tuple[tuple[str, int], ...]
    domain_slots: tuple[tuple[str, int], ...]
    fabric_slots_per_tick: int
    priority_order: tuple[str, ...] = DEFAULT_PRIORITY
    max_service_span_ticks: int = 4096


def uniform_causal_memory_plan_v1c(fabric, *, pe_slots=1024,
                                   domain_slots=1024, fabric_slots_per_tick=1024,
                                   max_service_span_ticks=4096):
    return CausalMemoryPlanV1c(
        tuple((pe, pe_slots) for pe in fabric.pe_ids),
        tuple((d, domain_slots) for d in DOMAINS),
        fabric_slots_per_tick, DEFAULT_PRIORITY, max_service_span_ticks)


def _valid_memory(fabric, plan):
    if (type(plan) is not CausalMemoryPlanV1c
            or type(plan.pe_slots) is not tuple
            or type(plan.domain_slots) is not tuple
            or type(plan.priority_order) is not tuple
            or type(plan.fabric_slots_per_tick) is not int
            or plan.fabric_slots_per_tick <= 0
            or type(plan.max_service_span_ticks) is not int
            or plan.max_service_span_ticks <= 0):
        raise CausalMemoryAdmissionV1c('invalid causal memory plan')
    pe, domains = {}, {}
    for rows, dest in ((plan.pe_slots, pe), (plan.domain_slots, domains)):
        for row in rows:
            if (type(row) is not tuple or len(row) != 2
                    or type(row[0]) is not str or type(row[1]) is not int
                    or row[1] <= 0 or row[0] in dest):
                raise CausalMemoryAdmissionV1c('invalid or duplicated memory quota')
            dest[row[0]] = row[1]
    if (set(pe) != set(fabric.pe_ids) or set(domains) != set(DOMAINS)
            or set(plan.priority_order) != set(DOMAINS)
            or len(plan.priority_order) != len(DOMAINS)):
        raise CausalMemoryAdmissionV1c('memory quota population/priority mismatch')
    return pe, domains


def _reservation(node, channels, pid, outgoing):
    """Worst-case (not actual) accesses, with target E charged to target PE."""
    rows = [(pid, 'P', 'PROGRAM_REFERENCE', len(node.instructions)),
            (pid, 'S', 'STATE_LOAD', 1), (pid, 'S', 'STATE_COMMIT', 1),
            (pid, 'E', 'BATCH_CONSUME', len(channels)),
            (pid, 'O', 'OBSERVATION_RECORD', 1)]
    for op, channel in node.instructions:
        if op == 'EMIT':
            rows.append((pid, 'E', 'EMISSION_RECORD', 1))
            for edge in outgoing.get((node.node_id, channel), ()):
                rows.append((edge.target_pe, 'E', 'ROUTE_ENQUEUE', 1))
                rows.append((pid, 'O', 'OBSERVATION_RECORD', 1))
    combined = {}
    for pe, domain, intent, amount in rows:
        combined[(pe, domain, intent)] = combined.get((pe, domain, intent), 0) + amount
    return tuple((pe, dom, intent, qty) for (pe, dom, intent), qty in sorted(combined.items())
                 if qty)


def execute_causal_memory_v1c(case, fabric, transport_plan: TransportPlanV1a,
                               pe_plan: CausalServicePlanV1b,
                               memory_plan: CausalMemoryPlanV1c,
                               *, max_batches=128, max_events=4096):
    nodes, owners = _admit(case, fabric)
    _admit_plan(transport_plan)
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
        if not heads and not inflight:
            break
        if now - first_tick >= min(memory_plan.max_service_span_ticks,
                                  pe_plan.max_service_span_ticks):
            raise CausalMemoryHorizonV1c('max_service_span_ticks: no closed result')
        while inflight and inflight[0][0] <= now:
            due, _, target_pe, target_node, channel = heapq.heappop(inflight)
            if due != now:
                raise AssertionError('late in-flight delivery')
            pes[target_pe].enqueue(now, target_node, channel)
            delivered += 1
            deliveries.append({'delivery_timestamp': now, 'target_node': target_node,
                               'target_pe': target_pe, 'target_channel': channel})

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
                if head is None or head[0] > now:
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
                        if pe_used[pid] < pe_caps[pid]
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
                    if cross:
                        if len(inflight) >= transport_plan.max_inflight_occurrences:
                            raise TransportCapacityV1a('max_inflight_occurrences')
                        heapq.heappush(inflight, (due, ordinal, edge.target_pe,
                                                  edge.target_node, edge.target_channel))
                        ordinal += 1
                        peak = max(peak, len(inflight))
                    else:
                        pes[edge.target_pe].enqueue(due, edge.target_node,
                                                    edge.target_channel)
                    route = {'emission_timestamp': now, 'source_node': nid,
                             'source_channel': ch, 'delivery_timestamp': due,
                             'target_node': edge.target_node,
                             'target_channel': edge.target_channel,
                             'delay_ticks': edge.delay_ticks + extra}
                    routes.append(route)
                    transfers.append({**route, 'source_pe': pid,
                                      'target_pe': edge.target_pe, 'cross_pe': cross,
                                      'declared_delay_ticks': edge.delay_ticks,
                                      'extra_latency_ticks': extra})
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
        if remaining:
            if pe_fabric_used == pe_plan.fabric_slots_per_tick:
                fabric_stalls += len(remaining)
            elif any(pe_used[k[2]] >= pe_caps[k[2]] for k in remaining):
                pe_stalls += len(remaining)
        service_timeline.append({'tick': now, 'fabric_grants': pe_fabric_used,
                                 'pe_grants': [[pid, pe_used[pid]] for pid in fabric.pe_ids],
                                 'ready_heads_deferred': len(remaining)})
        memory_timeline.append({'tick': now, 'fabric_units': mem_fabric_used,
                                'pe_units': [[pid, mem_pe_used[pid]] for pid in fabric.pe_ids],
                                'domain_units': [[d, mem_domain_used[d]] for d in DOMAINS]})
        heads = [h[0] for pe in pes.values() if (h := pe.head()) is not None]
        if not heads and not inflight:
            break
        due = min(heads + ([inflight[0][0]] if inflight else []))
        now = now + 1 if due <= now else due
    if (processed_events != len(case.events) + len(routes)
            or delivered != sum(x['cross_pe'] for x in transfers)
            or len(memory_pending) != 0):
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
                          'remaining_inflight_occurrences': len(inflight)},
            'pe_snapshots': {pid: {'node_count': len(pe.states), 'nodes': sorted(pe.states)}
                             for pid, pe in pes.items()}}
