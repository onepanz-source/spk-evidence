"""A1d: deterministic PE-local fail-stop before a service grant.

This is an actual stepwise execution on independently owned PE queues. A fault
quiesces the entire reference fabric at a pre-batch boundary; only the already
committed prefix is exported. No rollback, checkpoint restart, redistribution,
physical failure timing or distributed consensus is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass

from spk_architecture_v1.pe_execution_v1b import (
    PEContextV1b, PELimitV1b, _admit, _compute_local,
)
from spk_architecture_v1.pe_service_v1c import (
    _enqueue_bounded, _positive, _validate_service_plan,
    PEServiceAdmissionV1c,
)

SCHEMA = 'spk-architecture-pe-failstop/v1d'


class PEFaultAdmissionV1d(ValueError):
    pass


class PEFaultNotReachedV1d(RuntimeError):
    """A requested fault was not triggered. It cannot count as a closed run."""


@dataclass(frozen=True)
class PEFaultPlanV1d:
    pe_id: str
    after_local_batches: int


def _check_fault_plan(fabric, fault):
    if fault is None:
        return
    if (type(fault) is not PEFaultPlanV1d
            or type(fault.pe_id) is not str
            or fault.pe_id not in fabric.pe_ids
            or type(fault.after_local_batches) is not int
            or fault.after_local_batches < 0):
        raise PEFaultAdmissionV1d('invalid PE fail-stop plan')


def _pending_counts(pes):
    return {pid: sum(len(v) for v in pe.pending.values())
            for pid, pe in pes.items()}


def execute_failstop_v1d(case, fabric, service_plan, fault=None,
                         *, max_batches=128, max_events=4096):
    """Execute locally with one optional deterministic pre-grant PE failure.

    When a PE fails, every PE stops: the fault witness contains a committed
    prefix, never a successful result, even if healthy PEs still have work.
    This is fail-stop containment, NOT high availability or PE failover.
    """
    nodes, owner = _admit(case, fabric)
    slots = _validate_service_plan(fabric, service_plan)
    _check_fault_plan(fabric, fault)
    if not (_positive(max_batches) and _positive(max_events)):
        raise PEServiceAdmissionV1c('invalid execution budget')

    pes = {pid: PEContextV1b(pid) for pid in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owner[nid]].states[nid] = [node.initial_raw, 0]
    outgoing = {}
    for route in fabric.static_routes:
        outgoing.setdefault((route.source_node, route.source_channel), []).append(route)
    for event in case.events:
        _enqueue_bounded(pes[owner[event.node_id]], event.timestamp,
                         event.node_id, event.channel,
                         service_plan.queue_event_capacity_per_pe)

    service_tick = 0
    tick_fabric_used = 0
    tick_pe_used = {pid: 0 for pid in fabric.pe_ids}
    stalls_fabric = stalls_pe = 0
    local_batches = {pid: 0 for pid in fabric.pe_ids}
    service_ledger = []
    emissions, terminal, batches, routes, transfers = [], [], [], [], []
    event_count = batch_count = 0

    def snapshot():
        return [{'node_id': n.node_id,
                 'raw': pes[owner[n.node_id]].states[n.node_id][0],
                 'last_timestamp': pes[owner[n.node_id]].states[n.node_id][1]}
                for n in case.nodes]

    while True:
        heads = [(head[0], head[1], pid) for pid, pe in pes.items()
                 if (head := pe.head()) is not None]
        if not heads:
            break
        timestamp, nid, pid = min(heads)
        pe = pes[pid]
        pending_batch = pe.pending[(timestamp, nid)]
        # Check the same execution bounds as A1c before fault admission.
        if batch_count >= max_batches:
            raise PELimitV1b('max_batches')
        if event_count + len(pending_batch) > max_events:
            raise PELimitV1b('max_events')

        if fault is not None and pid == fault.pe_id and (
                local_batches[pid] == fault.after_local_batches):
            return {
                'schema': SCHEMA, 'status': 'PE_FAULT',
                'fault': {'pe_id': pid, 'after_local_batches': local_batches[pid],
                          'node_id': nid, 'logical_timestamp': timestamp,
                          'stage': 'before_service_grant'},
                'committed_prefix': {
                    'processed_batches': batch_count,
                    'processed_events': event_count,
                    'local_batches': dict(local_batches),
                    'states': snapshot(),
                    'emissions': list(emissions),
                    'terminal_outputs': list(terminal),
                    'observations': {'batches': list(batches),
                                     'routes': list(routes)},
                    'service_ledger': list(service_ledger),
                    'pending_event_occurrences_per_pe': _pending_counts(pes),
                    'fabric_stall_ticks': stalls_fabric,
                    'pe_stall_ticks': stalls_pe,
                },
                'limitations': ['global fail-stop and quiescence',
                                'no rollback or automatic PE reassignment',
                                'no physical fault timing or persistent recovery'],
            }

        if service_tick < timestamp:
            service_tick = timestamp
            tick_fabric_used = 0
            tick_pe_used = {pe_id: 0 for pe_id in fabric.pe_ids}
        while (tick_fabric_used >= service_plan.fabric_slots_per_tick
               or tick_pe_used[pid] >= slots[pid]):
            if tick_fabric_used >= service_plan.fabric_slots_per_tick:
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
        local_batches[pid] += 1
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
                                 service_plan.queue_event_capacity_per_pe)
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

    if fault is not None:
        raise PEFaultNotReachedV1d('requested PE fail-stop not reached')
    result = {'emissions': emissions, 'terminal_outputs': terminal,
              'states': snapshot(),
              'processed_batches': batch_count,
              'processed_events': event_count,
              'observations': {'batches': batches, 'routes': routes}}
    return {
        'schema': SCHEMA, 'status': 'CLOSED',
        'result': result,
        'transport': {'transfers': transfers,
                      'cross_pe_occurrences': sum(t['cross_pe'] for t in transfers),
                      'local_occurrences': sum(not t['cross_pe'] for t in transfers)},
        'pe_snapshots': {pid: {'node_count': len(pe.states),
                               'nodes': sorted(pe.states)} for pid, pe in pes.items()},
        'service': {'schema': 'spk-architecture-pe-service/v1c',
                    'plan': {'pe_slots': [[pid, slots[pid]] for pid in fabric.pe_ids],
                             'fabric_slots_per_tick': service_plan.fabric_slots_per_tick,
                             'queue_event_capacity_per_pe': service_plan.queue_event_capacity_per_pe},
                    'batches': batch_count, 'fabric_stall_ticks': stalls_fabric,
                    'pe_stall_ticks': stalls_pe,
                    'max_service_tick': max((x['service_tick'] for x in service_ledger),
                                            default=0),
                    'ledger': service_ledger},
    }
