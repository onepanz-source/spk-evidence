"""A3b: causal, finite PE service grants over A3a in-flight transport.

This deliberately reuses A1b local neuron semantics, with grant timestamps
feeding both the neuron and its emitted spike timestamps. Service contention
thus has *causal* effects, unlike separate A1c/A2c aggregate accounting.
The globally deterministic arbiter is NOT a physical distributed clock.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq

from spk_architecture_v1.pe_fabric_v1a import FabricV1a
from spk_architecture_v1.pe_execution_v1b import (
    PEContextV1b, PELimitV1b, _admit, _compute_local,
)
from spk_architecture_v1.temporal_transport_v1a import (
    TransportPlanV1a, TransportCapacityV1a, _admit_plan,
)

SCHEMA = 'spk-architecture-causal-pe-service/v1b'


class CausalServiceAdmissionV1b(ValueError):
    pass


class CausalServiceHorizonV1b(RuntimeError):
    """Service budget exhausted: no completed result or rollback is claimed."""


@dataclass(frozen=True)
class CausalServicePlanV1b:
    pe_slots: tuple[tuple[str, int], ...]
    fabric_slots_per_tick: int
    max_service_span_ticks: int = 4096


def uniform_causal_service_plan_v1b(fabric, *, pe_slots, fabric_slots_per_tick,
                                    max_service_span_ticks=4096):
    if not isinstance(fabric, FabricV1a):
        raise CausalServiceAdmissionV1b('invalid PE fabric')
    return CausalServicePlanV1b(
        tuple((pid, pe_slots) for pid in fabric.pe_ids),
        fabric_slots_per_tick, max_service_span_ticks)


def _valid_plan(fabric, plan):
    if (type(plan) is not CausalServicePlanV1b
            or type(plan.pe_slots) is not tuple
            or type(plan.fabric_slots_per_tick) is not int
            or plan.fabric_slots_per_tick <= 0
            or type(plan.max_service_span_ticks) is not int
            or plan.max_service_span_ticks <= 0):
        raise CausalServiceAdmissionV1b('invalid causal service plan')
    slots = {}
    for row in plan.pe_slots:
        if (type(row) is not tuple or len(row) != 2
                or type(row[0]) is not str or not row[0]
                or type(row[1]) is not int or row[1] <= 0
                or row[0] in slots):
            raise CausalServiceAdmissionV1b('invalid PE service slots')
        slots[row[0]] = row[1]
    if set(slots) != set(fabric.pe_ids):
        raise CausalServiceAdmissionV1b('PE grant population mismatch')
    return slots


def execute_causal_service_v1b(case, fabric: FabricV1a,
                               transport_plan: TransportPlanV1a,
                               service_plan: CausalServicePlanV1b,
                               *, max_batches=128, max_events=4096):
    """Compute at actual service tick; wait may change decay, routes and batching.

    All arrivals for the same (ready tick, neuron) coalesce before that tick's
    grants. Once deferred, distinct ready-tick groups remain distinct even if
    serviced at the same tick; this is an explicit A3b scheduling policy.
    Every route has strictly positive declared delay, so a grant cannot create
    a new ready batch at its own tick. A single arbiter orders by
    (ready_tick, node_id, PE id), skipping PEs without remaining grants.
    """
    nodes, owners = _admit(case, fabric)
    _admit_plan(transport_plan)
    pe_limits = _valid_plan(fabric, service_plan)
    if not (type(max_batches) is int and max_batches > 0
            and type(max_events) is int and max_events > 0):
        raise CausalServiceAdmissionV1b('invalid execution bounds')

    pes = {pid: PEContextV1b(pid) for pid in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owners[nid]].states[nid] = [node.initial_raw, 0]
    for event in case.events:
        pes[owners[event.node_id]].enqueue(event.timestamp, event.node_id,
                                          event.channel)
    outgoing = {}
    for edge in fabric.static_routes:
        outgoing.setdefault((edge.source_node, edge.source_channel), []).append(edge)

    inflight = []  # (delivery_tick, occurrence_id, PE, node, channel)
    ordinal = peak = delivered = 0
    emissions, terminal, batches, routes, transfers, deliveries = [], [], [], [], [], []
    grants, service_ticks = [], []
    processed_events = processed_batches = 0
    weighted_wait = grant_wait = fabric_stalls = pe_stalls = 0

    def frontier():
        return [(head[0], head[1], pid) for pid, pe in pes.items()
                if (head := pe.head()) is not None]

    heads = frontier()
    candidates = [x[0] for x in heads]
    if inflight:
        candidates.append(inflight[0][0])
    if not candidates:
        # No input events: accepted empty execution, matching A3a.
        first_tick = now = 0
    else:
        first_tick = now = min(candidates)

    while True:
        heads = frontier()
        if not heads and not inflight:
            break
        if now - first_tick >= service_plan.max_service_span_ticks:
            raise CausalServiceHorizonV1b('max_service_span_ticks')
        while inflight and inflight[0][0] <= now:
            delivery_tick, _, target_pe, target_node, target_channel = heapq.heappop(inflight)
            if delivery_tick != now:
                raise AssertionError('noncausal late in-flight delivery')
            pes[target_pe].enqueue(now, target_node, target_channel)
            delivered += 1
            deliveries.append({'delivery_timestamp': now, 'target_node': target_node,
                               'target_pe': target_pe, 'target_channel': target_channel})

        used = {pid: 0 for pid in fabric.pe_ids}
        fabric_used = 0
        while fabric_used < service_plan.fabric_slots_per_tick:
            eligible = [(head[0], head[1], pid) for pid, pe in pes.items()
                        if used[pid] < pe_limits[pid]
                        and (head := pe.head()) is not None
                        and head[0] <= now]
            if not eligible:
                break
            ready_tick, nid, pid = min(eligible)
            pe = pes[pid]
            pending = pe.pending[(ready_tick, nid)]
            if processed_batches >= max_batches:
                raise PELimitV1b('max_batches')
            if processed_events + len(pending) > max_events:
                raise PELimitV1b('max_events')
            key, channels = pe.next_batch()
            if key != (ready_tick, nid):
                raise AssertionError('PE-owned event queue head mismatch')
            if now < pe.states[nid][1]:
                raise AssertionError('backward PE causal grant')
            processed_events += len(channels)
            processed_batches += 1
            used[pid] += 1
            fabric_used += 1
            wait = now - ready_tick
            grant_wait += wait
            weighted_wait += wait * len(channels)
            raw, guard, outputs = _compute_local(nodes[nid], pe.states[nid],
                                                 now, channels)
            pe.states[nid] = [raw, now]
            grants.append({'service_timestamp': now, 'ready_timestamp': ready_tick,
                           'node_id': nid, 'pe_id': pid, 'channels': list(channels),
                           'wait_ticks': wait})
            for channel in outputs:
                emission = {'timestamp': now, 'node_id': nid, 'channel': channel}
                emissions.append(emission)
                edges = outgoing.get((nid, channel), ())
                if not edges:
                    terminal.append(emission)
                for edge in edges:
                    cross = pid != edge.target_pe
                    extra = transport_plan.cross_pe_extra_ticks if cross else 0
                    due = now + edge.delay_ticks + extra
                    if due <= now:
                        raise AssertionError('route must be causally future')
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
                             'source_channel': channel, 'delivery_timestamp': due,
                             'target_node': edge.target_node,
                             'target_channel': edge.target_channel,
                             'delay_ticks': edge.delay_ticks + extra}
                    routes.append(route)
                    transfers.append({**route, 'source_pe': pid,
                                      'target_pe': edge.target_pe,
                                      'cross_pe': cross,
                                      'declared_delay_ticks': edge.delay_ticks,
                                      'extra_latency_ticks': extra})
            batches.append({'timestamp': now, 'node_id': nid,
                            'channels': list(channels), 'final_raw': raw,
                            'final_guard': guard, 'output_channels': list(outputs)})
        # Number of stalled PE queue heads, not number of ungranted events.
        remaining = [(head[0], head[1], pid) for pid, pe in pes.items()
                     if (head := pe.head()) is not None and head[0] <= now]
        if remaining:
            if fabric_used == service_plan.fabric_slots_per_tick:
                fabric_stalls += len(remaining)
            else:
                pe_stalls += len(remaining)
        service_ticks.append({'tick': now, 'fabric_grants': fabric_used,
                              'pe_grants': [[pid, used[pid]] for pid in fabric.pe_ids],
                              'ready_heads_deferred': len(remaining)})
        heads = frontier()
        if not heads and not inflight:
            break
        # Never jump over a pending ready batch. Skip otherwise-idle ticks.
        next_due = [h[0] for h in heads]
        if inflight:
            next_due.append(inflight[0][0])
        soonest = min(next_due)
        now = now + 1 if soonest <= now else soonest

    if delivered != sum(t['cross_pe'] for t in transfers):
        raise AssertionError('remote event occurrence conservation')
    if processed_events != len(case.events) + len(routes):
        raise AssertionError('event occurrence conservation')
    result = {
        'emissions': emissions, 'terminal_outputs': terminal,
        'states': [{'node_id': n.node_id,
                    'raw': pes[owners[n.node_id]].states[n.node_id][0],
                    'last_timestamp': pes[owners[n.node_id]].states[n.node_id][1]}
                   for n in case.nodes],
        'processed_batches': processed_batches, 'processed_events': processed_events,
        'observations': {'batches': batches, 'routes': routes},
    }
    return {
        'schema': SCHEMA,
        'result': result,
        'service': {'grants': grants, 'timeline': service_ticks,
                    'batch_wait_ticks': grant_wait,
                    'event_weighted_wait_ticks': weighted_wait,
                    'fabric_stall_incidents': fabric_stalls,
                    'pe_stall_incidents': pe_stalls,
                    'max_service_span_ticks': service_plan.max_service_span_ticks},
        'transport': {'transfers': transfers, 'delivery_log': deliveries,
                      'cross_pe_occurrences': delivered,
                      'local_occurrences': len(transfers) - delivered,
                      'delivered_cross_pe_occurrences': delivered,
                      'peak_inflight_occurrences': peak,
                      'remaining_inflight_occurrences': len(inflight),
                      'cross_pe_extra_ticks': transport_plan.cross_pe_extra_ticks},
        'pe_snapshots': {pid: {'node_count': len(pe.states), 'nodes': sorted(pe.states)}
                         for pid, pe in pes.items()},
    }
