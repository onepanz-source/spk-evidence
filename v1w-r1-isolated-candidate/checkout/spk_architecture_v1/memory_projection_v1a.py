"""A2a logical P/S/E/O PE memory reservation and execution-ledger projection.

This is *not* a bank scheduler, access authorization engine or physical memory.
It consumes real A1d committed batches, queues and route occurrences.  Resource
limits are abstract quantities declared by this profile, not byte counts.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from spk_architecture_v1.pe_execution_v1b import _admit
from spk_architecture_v1.pe_service_v1c import _validate_service_plan

SCHEMA = 'spk-architecture-memory-projection/v1a'
DOMAINS = ('P', 'S', 'E', 'O')


class MemoryAdmissionV1a(ValueError):
    pass


class MemoryInvariantV1a(AssertionError):
    pass


@dataclass(frozen=True)
class MemoryCapV1a:
    pe_id: str
    program_units: int
    state_units: int
    event_units: int
    observation_units: int


@dataclass(frozen=True)
class MemoryPlanV1a:
    epoch_id: str
    capacities: tuple[MemoryCapV1a, ...]


def _nat(x):
    return type(x) is int and x >= 0


def uniform_memory_plan_v1a(fabric, *, program_units=256, state_units=16,
                            event_units=4096, observation_units=4096,
                            epoch_id='E0'):
    return MemoryPlanV1a(epoch_id, tuple(MemoryCapV1a(
        pid, program_units, state_units, event_units, observation_units)
        for pid in fabric.pe_ids))


def admit_memory_v1a(case, fabric, service_plan, memory_plan,
                     *, max_batches=128):
    nodes, owners = _admit(case, fabric)
    _validate_service_plan(fabric, service_plan)
    if (type(memory_plan) is not MemoryPlanV1a
            or type(memory_plan.epoch_id) is not str
            or not memory_plan.epoch_id or memory_plan.epoch_id.strip() != memory_plan.epoch_id
            or type(memory_plan.capacities) is not tuple
            or len(memory_plan.capacities) != len(fabric.pe_ids)
            or not _nat(max_batches) or max_batches == 0):
        raise MemoryAdmissionV1a('invalid memory plan or epoch')
    capacities = {}
    for c in memory_plan.capacities:
        if (type(c) is not MemoryCapV1a or type(c.pe_id) is not str
                or c.pe_id not in fabric.pe_ids or c.pe_id in capacities
                or not all(_nat(x) for x in (c.program_units, c.state_units,
                                              c.event_units, c.observation_units))):
            raise MemoryAdmissionV1a('invalid per-PE domain capacity')
        capacities[c.pe_id] = c
    if set(capacities) != set(fabric.pe_ids):
        raise MemoryAdmissionV1a('incomplete PE memory capacity ownership')

    program = Counter()
    state = Counter()
    initial_events = Counter()
    static_max_observation = Counter()
    for n in case.nodes:
        program[owners[n.node_id]] += len(n.instructions)
        state[owners[n.node_id]] += 1
    for e in case.events:
        initial_events[owners[e.node_id]] += 1

    # Conservative per-batch route-observation upper bound from admitted
    # immutable programs and topology; never estimate it from the actual run.
    for pe_id in fabric.pe_ids:
        local_nodes = [n for n in case.nodes if owners[n.node_id] == pe_id]
        if local_nodes:
            per_batch = max(1 + sum(
                sum(1 for r in fabric.static_routes
                    if r.source_node == n.node_id and r.source_channel == operand)
                for op, operand in n.instructions if op == 'EMIT')
                for n in local_nodes)
            static_max_observation[pe_id] = max_batches * per_batch
    reservations = {}
    for pe_id in fabric.pe_ids:
        c = capacities[pe_id]
        need = {'P': program[pe_id], 'S': state[pe_id],
                'E': max(initial_events[pe_id], service_plan.queue_event_capacity_per_pe),
                'O': static_max_observation[pe_id]}
        cap = {'P': c.program_units, 'S': c.state_units,
               'E': c.event_units, 'O': c.observation_units}
        for domain in DOMAINS:
            if need[domain] > cap[domain]:
                raise MemoryAdmissionV1a(f'{pe_id}/{domain}: reserved demand exceeds capacity')
        reservations[pe_id] = {'capacity': cap, 'reservation': need}
    return {'schema': SCHEMA, 'epoch_id': memory_plan.epoch_id,
            'pe_ids': list(fabric.pe_ids), 'domains': list(DOMAINS),
            'node_owners': {nid: owners[nid] for nid in sorted(nodes)},
            'reservations': reservations, 'max_batches': max_batches,
            'limitations': ['abstract resource units not bytes',
                            'no transaction scheduling or access authorization',
                            'conservative per-PE observation budget']}


def project_execution_memory_v1a(case, fabric, admission, execution):
    """Independently replay A1d event/batch/route occurrence trace.

    Every recorded batch must consume existing occurrences and every routed
    occurrence must be placed on its owner's queue.  Committed fault-prefix
    pending counts must agree with the independently reconstructed queues.
    """
    if execution.get('status') not in ('CLOSED', 'PE_FAULT'):
        raise MemoryInvariantV1a('unrecognized A1d outcome')
    if admission.get('schema') != SCHEMA:
        raise MemoryInvariantV1a('invalid admission')
    owner = admission['node_owners']
    if set(owner) != {n.node_id for n in case.nodes}:
        raise MemoryInvariantV1a('admission/source ownership mismatch')
    payload = execution['result'] if execution['status'] == 'CLOSED' else execution['committed_prefix']
    observation = payload['observations']
    batches = observation['batches']
    routes = observation['routes']
    pending = Counter((e.timestamp, e.node_id, e.channel) for e in case.events)
    occupancy = Counter()
    peaks = Counter()
    records = Counter()
    accesses = Counter()
    for e in case.events:
        occupancy[owner[e.node_id]] += 1
    for pe in admission['pe_ids']:
        peaks[pe] = occupancy[pe]
    admitted_edges = {(r.source_node, r.source_channel, r.target_node,
                       r.target_channel, r.delay_ticks)
                      for r in fabric.static_routes}
    route_cursor = 0
    total_consumed = 0
    for batch in batches:
        timestamp, nid = batch['timestamp'], batch['node_id']
        pe = owner[nid]
        channels = batch['channels']
        if channels != sorted(channels) or not channels:
            raise MemoryInvariantV1a('invalid canonical batch')
        accesses[(pe, 'P', 'PROGRAM_REFERENCE')] += 1
        accesses[(pe, 'S', 'STATE_LOAD')] += 1
        accesses[(pe, 'E', 'BATCH_CONSUME')] += len(channels)
        for channel in channels:
            k = (timestamp, nid, channel)
            if pending[k] < 1:
                raise MemoryInvariantV1a('batch consumed nonexistent event occurrence')
            pending[k] -= 1
            occupancy[pe] -= 1
            total_consumed += 1
        accesses[(pe, 'S', 'STATE_COMMIT')] += 1
        accesses[(pe, 'E', 'EMISSION_RECORD')] += len(batch['output_channels'])
        records[pe] += 1
        accesses[(pe, 'O', 'OBSERVATION_RECORD')] += 1
        # Route sequence is monotonic in batch order; route multiplicity is
        # represented by individual occurrences and never deduplicated.
        while route_cursor < len(routes):
            route = routes[route_cursor]
            if (route['source_node'], route['emission_timestamp']) != (nid, timestamp):
                break
            if (route['delivery_timestamp'] != timestamp + route['delay_ticks']
                    or route['delay_ticks'] <= 0 or route['target_node'] not in owner
                    or (nid, route['source_channel'], route['target_node'],
                        route['target_channel'], route['delay_ticks']) not in admitted_edges):
                raise MemoryInvariantV1a('invalid route occurrence')
            dest = owner[route['target_node']]
            pending[(route['delivery_timestamp'], route['target_node'],
                     route['target_channel'])] += 1
            occupancy[dest] += 1
            peaks[dest] = max(peaks[dest], occupancy[dest])
            accesses[(dest, 'E', 'ROUTE_ENQUEUE')] += 1
            records[pe] += 1
            accesses[(pe, 'O', 'OBSERVATION_RECORD')] += 1
            route_cursor += 1
    if route_cursor != len(routes):
        raise MemoryInvariantV1a('unattributed route occurrences')
    if total_consumed != payload['processed_events'] or len(batches) != payload['processed_batches']:
        raise MemoryInvariantV1a('committed event/batch counter drift')
    remaining = {pe: occupancy[pe] for pe in admission['pe_ids']}
    if (len(case.events) + len(routes) != total_consumed + sum(remaining.values())):
        raise MemoryInvariantV1a('event occurrence conservation failed')
    if execution['status'] == 'CLOSED':
        if any(pending.values()):
            raise MemoryInvariantV1a('closed execution retains pending events')
    elif remaining != payload['pending_event_occurrences_per_pe']:
        raise MemoryInvariantV1a('fault-prefix pending event count mismatch')
    for pe in admission['pe_ids']:
        reserved = admission['reservations'][pe]['reservation']
        if peaks[pe] > reserved['E'] or records[pe] > reserved['O']:
            raise MemoryInvariantV1a('projection exceeded admitted event/observer reservation')
    return {
        'schema': SCHEMA, 'status': execution['status'], 'epoch_id': admission['epoch_id'],
        'pe_usage': {pe: {'P': admission['reservations'][pe]['reservation']['P'],
                          'S': admission['reservations'][pe]['reservation']['S'],
                          'E_peak': peaks[pe], 'E_pending': remaining[pe],
                          'O_records': records[pe]}
                     for pe in admission['pe_ids']},
        'logical_accesses': [
            {'pe_id': pe, 'domain': domain, 'intent': intent, 'quantity': quantity}
            for (pe, domain, intent), quantity in sorted(accesses.items())],
        'conservation': {'initial_events': len(case.events),
                         'routed_occurrences': len(routes),
                         'consumed_occurrences': total_consumed,
                         'pending_occurrences': sum(remaining.values())},
        'limitations': ['derived ledger; no physical transactions',
                        'no contention or permission enforcement',
                        'no rollback or durable PE fault recovery']}
