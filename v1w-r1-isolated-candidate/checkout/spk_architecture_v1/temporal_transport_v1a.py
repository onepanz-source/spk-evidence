"""A3a: explicit causal arrival of routed spikes between PE-owned event queues.

This is a *logical transport* model. A1b Core arithmetic is executed locally;
inter-PE route occurrences wait in an in-flight heap until their delivery tick.
No physical bus, service clock, memory arbiter, recovery or backpressure is modeled.
At zero additional latency the result must be exactly A1b's frozen-domain result.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import heapq

from spk_architecture_v1.pe_fabric_v1a import FabricV1a
from spk_architecture_v1.pe_execution_v1b import (
    PEContextV1b, PEAdmissionErrorV1b, PELimitV1b, _admit, _compute_local,
)

SCHEMA = 'spk-architecture-temporal-transport/v1a'


class TransportAdmissionV1a(ValueError):
    pass


class TransportCapacityV1a(RuntimeError):
    """The in-flight limit was exhausted; executed prefix is not rolled back."""


@dataclass(frozen=True)
class TransportPlanV1a:
    cross_pe_extra_ticks: int
    max_inflight_occurrences: int = 4096


def _admit_plan(plan):
    if (type(plan) is not TransportPlanV1a
            or type(plan.cross_pe_extra_ticks) is not int
            or plan.cross_pe_extra_ticks < 0
            or type(plan.max_inflight_occurrences) is not int
            or plan.max_inflight_occurrences <= 0):
        raise TransportAdmissionV1a('invalid transport latency or in-flight bound')


def execute_temporal_v1a(case, fabric: FabricV1a, plan: TransportPlanV1a,
                         *, max_batches=128, max_events=4096):
    """Route spikes with explicit in-flight custody and causal logical arrivals.

    At a given tick all arrived transfers are delivered *before* the recipient
    batch is dequeued; same-tick occurrences therefore retain A1b batching.
    Only inter-PE routes gain `cross_pe_extra_ticks`; local routes retain the
    declared edge delay. Computation is chronological with one global arbiter.
    No PE/memory service contention is modeled in this A3a experiment.
    """
    nodes, owner = _admit(case, fabric)
    _admit_plan(plan)
    if not (type(max_batches) is int and max_batches > 0
            and type(max_events) is int and max_events > 0):
        raise TransportAdmissionV1a('invalid execution bounds')
    pes = {pid: PEContextV1b(pid) for pid in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owner[nid]].states[nid] = [node.initial_raw, 0]
    for event in case.events:
        pes[owner[event.node_id]].enqueue(event.timestamp, event.node_id, event.channel)
    outgoing = {}
    for edge in fabric.static_routes:
        outgoing.setdefault((edge.source_node, edge.source_channel), []).append(edge)

    # (delivery_tick, unique_ordinal, target_pe, target_node, target_channel)
    inflight = []
    next_ordinal = 0
    peak_inflight = 0
    delivered_cross = 0
    delivery_log = []
    emissions, terminal, batches, routes, transfers = [], [], [], [], []
    event_count = batch_count = 0
    while True:
        heads = [(head[0], head[1], pid) for pid, pe in pes.items()
                 if (head := pe.head()) is not None]
        first_head = min(heads) if heads else None
        # When an arrival and a ready batch share a tick, deliver first. This
        # is necessary to conserve same-tick batch multiplicity.
        if inflight and (first_head is None or inflight[0][0] <= first_head[0]):
            tick = inflight[0][0]
            while inflight and inflight[0][0] == tick:
                _, _, pid, nid, channel = heapq.heappop(inflight)
                pes[pid].enqueue(tick, nid, channel)
                delivered_cross += 1
                delivery_log.append({'delivery_timestamp': tick, 'target_node': nid,
                                     'target_pe': pid, 'target_channel': channel})
            continue
        if first_head is None:
            break
        tick, nid, pid = first_head
        pe = pes[pid]
        channels = pe.pending[(tick, nid)]
        if batch_count >= max_batches:
            raise PELimitV1b('max_batches')
        if event_count + len(channels) > max_events:
            raise PELimitV1b('max_events')
        key, channels = pe.next_batch()
        if key != (tick, nid):
            raise AssertionError('PE queue head lost custody')
        event_count += len(channels)
        batch_count += 1
        raw, guard, outputs = _compute_local(nodes[nid], pe.states[nid],
                                             tick, channels)
        pe.states[nid] = [raw, tick]
        for ch in outputs:
            emission = {'timestamp': tick, 'node_id': nid, 'channel': ch}
            emissions.append(emission)
            recipients = outgoing.get((nid, ch), ())
            if not recipients:
                terminal.append(emission)
            for edge in recipients:
                cross = pid != edge.target_pe
                extra = plan.cross_pe_extra_ticks if cross else 0
                delivery_tick = tick + edge.delay_ticks + extra
                if cross:
                    if len(inflight) >= plan.max_inflight_occurrences:
                        raise TransportCapacityV1a('max_inflight_occurrences')
                    heapq.heappush(inflight, (delivery_tick, next_ordinal,
                                              edge.target_pe, edge.target_node,
                                              edge.target_channel))
                    next_ordinal += 1
                    peak_inflight = max(peak_inflight, len(inflight))
                else:
                    pes[edge.target_pe].enqueue(delivery_tick, edge.target_node,
                                                edge.target_channel)
                route = {'emission_timestamp': tick, 'source_node': nid,
                         'source_channel': ch, 'delivery_timestamp': delivery_tick,
                         'target_node': edge.target_node,
                         'target_channel': edge.target_channel,
                         'delay_ticks': edge.delay_ticks + extra}
                routes.append(route)
                transfers.append({**route, 'source_pe': pid,
                                  'target_pe': edge.target_pe, 'cross_pe': cross,
                                  'declared_delay_ticks': edge.delay_ticks,
                                  'extra_latency_ticks': extra})
        batches.append({'timestamp': tick, 'node_id': nid, 'channels': list(channels),
                        'final_raw': raw, 'final_guard': guard,
                        'output_channels': list(outputs)})

    result = {
        'emissions': emissions, 'terminal_outputs': terminal,
        'states': [{'node_id': n.node_id, 'raw': pes[owner[n.node_id]].states[n.node_id][0],
                    'last_timestamp': pes[owner[n.node_id]].states[n.node_id][1]}
                   for n in case.nodes],
        'processed_batches': batch_count, 'processed_events': event_count,
        'observations': {'batches': batches, 'routes': routes},
    }
    total_remote = sum(t['cross_pe'] for t in transfers)
    if delivered_cross != total_remote:
        raise AssertionError('in-flight transfer conservation failure')
    if event_count != len(case.events) + len(routes):
        raise AssertionError('total event occurrence conservation failure')
    return {
        'schema': SCHEMA, 'result': result,
        'transport': {'transfers': transfers, 'delivery_log': delivery_log,
                      'cross_pe_occurrences': total_remote,
                      'local_occurrences': len(transfers) - total_remote,
                      'delivered_cross_pe_occurrences': delivered_cross,
                      'peak_inflight_occurrences': peak_inflight,
                      'remaining_inflight_occurrences': len(inflight),
                      'cross_pe_extra_ticks': plan.cross_pe_extra_ticks},
        'pe_snapshots': {pid: {'node_count': len(pe.states), 'nodes': sorted(pe.states)}
                         for pid, pe in pes.items()},
    }
