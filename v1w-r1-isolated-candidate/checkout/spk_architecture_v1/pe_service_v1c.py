"""A1c: finite PE and shared arbiter service slots over A1b logical execution.

Service ticks are a separate accounting plane. They do NOT change logical
spike timestamps, edge delays, or Core semantics. One deterministic central
arbiter still chooses (logical timestamp, node ID). The model has no parallel
workers, physical latency, network congestion control, or backpressure.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_architecture_v1.pe_fabric_v1a import FabricV1a
from spk_architecture_v1.pe_execution_v1b import (
    PEAdmissionErrorV1b, PELimitV1b, PEContextV1b, _admit, _compute_local,
)

SCHEMA = 'spk-architecture-pe-service/v1c'


class PEServiceAdmissionV1c(ValueError):
    pass


class PEQueueOverflowV1c(RuntimeError):
    """Queue exceeded capacity. No rollback or recovery is claimed."""


@dataclass(frozen=True)
class ServicePlanV1c:
    pe_slots: tuple[tuple[str, int], ...]
    fabric_slots_per_tick: int
    queue_event_capacity_per_pe: int


def uniform_service_plan_v1c(fabric: FabricV1a, *, pe_slots: int,
                             fabric_slots_per_tick: int,
                             queue_event_capacity_per_pe: int = 4096):
    if not isinstance(fabric, FabricV1a):
        raise PEServiceAdmissionV1c('invalid PE fabric')
    return ServicePlanV1c(tuple((pe, pe_slots) for pe in fabric.pe_ids),
                          fabric_slots_per_tick, queue_event_capacity_per_pe)


def _positive(n):
    return type(n) is int and n > 0


def _validate_service_plan(fabric, plan):
    if (type(plan) is not ServicePlanV1c
            or not _positive(plan.fabric_slots_per_tick)
            or not _positive(plan.queue_event_capacity_per_pe)
            or type(plan.pe_slots) is not tuple
            or len(plan.pe_slots) != len(fabric.pe_ids)):
        raise PEServiceAdmissionV1c('invalid service plan')
    seen = set()
    for item in plan.pe_slots:
        if (type(item) is not tuple or len(item) != 2
                or type(item[0]) is not str or item[0] in seen
                or item[0] not in fabric.pe_ids or not _positive(item[1])):
            raise PEServiceAdmissionV1c('invalid per-PE service capacity')
        seen.add(item[0])
    if seen != set(fabric.pe_ids):
        raise PEServiceAdmissionV1c('service plan PE ownership mismatch')
    return dict(plan.pe_slots)


def _enqueue_bounded(pe, timestamp, nid, channel, cap):
    if sum(len(channels) for channels in pe.pending.values()) >= cap:
        raise PEQueueOverflowV1c('queue_event_capacity_per_pe')
    pe.enqueue(timestamp, nid, channel)


def execute_with_service_v1c(case, fabric, plan, *, max_batches=128,
                             max_events=4096):
    """Compute on actual PE-owned queues; grant finite virtual service credits.

    Logical computation never depends on the service ledger. Limited slots
    can delay *service* of the next batch but cannot silently alter spike
    timestamps or the frozen Core result. This is an observational resource
    accounting model and deliberately not a physical execution simulator.
    """
    nodes, owner = _admit(case, fabric)
    slots = _validate_service_plan(fabric, plan)
    if not (_positive(max_batches) and _positive(max_events)):
        raise PEServiceAdmissionV1c('invalid execution budget')

    pes = {pe_id: PEContextV1b(pe_id) for pe_id in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owner[nid]].states[nid] = [node.initial_raw, 0]
    outgoing = {}
    for route in fabric.static_routes:
        outgoing.setdefault((route.source_node, route.source_channel), []).append(route)
    for e in case.events:
        _enqueue_bounded(pes[owner[e.node_id]], e.timestamp, e.node_id, e.channel,
                         plan.queue_event_capacity_per_pe)

    service_tick = 0
    tick_fabric_used = 0
    tick_pe_used = {pid: 0 for pid in fabric.pe_ids}
    stalls_fabric = stalls_pe = 0
    service_ledger = []
    emissions, terminal, batches, routes, transfers = [], [], [], [], []
    event_count = batch_count = 0

    while True:
        heads = [(head[0], head[1], pid) for pid, pe in pes.items()
                 if (head := pe.head()) is not None]
        if not heads:
            break
        timestamp, nid, pid = min(heads)
        pe = pes[pid]
        channels = pe.pending[(timestamp, nid)]
        # Budget checks happen before any batch dequeue or compute.
        if batch_count >= max_batches:
            raise PELimitV1b('max_batches')
        if event_count + len(channels) > max_events:
            raise PELimitV1b('max_events')

        if service_tick < timestamp:
            service_tick = timestamp
            tick_fabric_used = 0
            tick_pe_used = {pe_id: 0 for pe_id in fabric.pe_ids}
        while (tick_fabric_used >= plan.fabric_slots_per_tick
               or tick_pe_used[pid] >= slots[pid]):
            if tick_fabric_used >= plan.fabric_slots_per_tick:
                stalls_fabric += 1
            if tick_pe_used[pid] >= slots[pid]:
                stalls_pe += 1
            service_tick += 1
            tick_fabric_used = 0
            tick_pe_used = {pe_id: 0 for pe_id in fabric.pe_ids}

        key, channels = pe.next_batch()
        if key != (timestamp, nid):
            raise AssertionError('global arbiter/local queue disagreement')
        tick_fabric_used += 1
        tick_pe_used[pid] += 1
        batch_count += 1
        event_count += len(channels)
        raw, guard, output_channels = _compute_local(
            nodes[nid], pe.states[nid], timestamp, channels)
        pe.states[nid] = [raw, timestamp]
        service_ledger.append({'logical_timestamp': timestamp,
                               'service_tick': service_tick,
                               'service_wait_ticks': service_tick - timestamp,
                               'node_id': nid, 'pe_id': pid,
                               'input_occurrences': len(channels)})
        for ch in output_channels:
            emission = {'timestamp': timestamp, 'node_id': nid, 'channel': ch}
            emissions.append(emission)
            recipients = outgoing.get((nid, ch), ())
            if not recipients:
                terminal.append(emission)
            for route in recipients:
                delivery_tick = timestamp + route.delay_ticks
                _enqueue_bounded(pes[route.target_pe], delivery_tick,
                                 route.target_node, route.target_channel,
                                 plan.queue_event_capacity_per_pe)
                detail = {'emission_timestamp': timestamp,
                          'source_node': nid, 'source_channel': ch,
                          'delivery_timestamp': delivery_tick,
                          'target_node': route.target_node,
                          'target_channel': route.target_channel,
                          'delay_ticks': route.delay_ticks}
                routes.append(detail)
                transfers.append({**detail, 'source_pe': pid,
                                  'target_pe': route.target_pe,
                                  'cross_pe': pid != route.target_pe})
        batches.append({'timestamp': timestamp, 'node_id': nid,
                        'channels': list(channels), 'final_raw': raw,
                        'final_guard': guard,
                        'output_channels': list(output_channels)})

    result = {'emissions': emissions, 'terminal_outputs': terminal,
              'states': [{'node_id': n.node_id,
                          'raw': pes[owner[n.node_id]].states[n.node_id][0],
                          'last_timestamp': pes[owner[n.node_id]].states[n.node_id][1]}
                         for n in case.nodes],
              'processed_batches': batch_count, 'processed_events': event_count,
              'observations': {'batches': batches, 'routes': routes}}
    return {
        'result': result,
        'transport': {'transfers': transfers,
                      'cross_pe_occurrences': sum(t['cross_pe'] for t in transfers),
                      'local_occurrences': sum(not t['cross_pe'] for t in transfers)},
        'pe_snapshots': {pid: {'node_count': len(pe.states),
                               'nodes': sorted(pe.states)} for pid, pe in pes.items()},
        'service': {'schema': SCHEMA, 'plan': {
            'pe_slots': [[pid, slots[pid]] for pid in fabric.pe_ids],
            'fabric_slots_per_tick': plan.fabric_slots_per_tick,
            'queue_event_capacity_per_pe': plan.queue_event_capacity_per_pe},
            'batches': batch_count, 'fabric_stall_ticks': stalls_fabric,
            'pe_stall_ticks': stalls_pe,
            'max_service_tick': max((row['service_tick'] for row in service_ledger),
                                    default=0),
            'ledger': service_ledger},
    }
