"""SPK Architecture A1b: real per-PE state, local event queues and ideal transport.

Independently executes the *declared finite* A1 corpus instruction fragment.
No frozen Network, Core, Compiler, oracle or observer is called by this engine.
Global chronological arbitration is intentionally retained: A1b is not a
parallel clock, distributed scheduler, contention or hardware timing model.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import heapq

from spk_architecture_v1.pe_fabric_v1a import FabricV1a


class PEAdmissionErrorV1b(ValueError):
    pass


class PELimitV1b(RuntimeError):
    pass


@dataclass
class PEContextV1b:
    pe_id: str
    states: dict[str, list[int]] = field(default_factory=dict)
    pending: dict[tuple[int, str], list[int]] = field(default_factory=dict)
    ready: list[tuple[int, str]] = field(default_factory=list)

    def enqueue(self, timestamp: int, node: str, channel: int):
        key = (timestamp, node)
        if key not in self.pending:
            self.pending[key] = []
            heapq.heappush(self.ready, key)
        self.pending[key].append(channel)

    def head(self):
        return self.ready[0] if self.ready else None

    def next_batch(self):
        key = heapq.heappop(self.ready)
        return key, tuple(sorted(self.pending.pop(key)))


def _natural(value):
    return type(value) is int and value >= 0


def _admit(case, fabric):
    if not isinstance(fabric, FabricV1a) or len(case.nodes) != 3:
        raise PEAdmissionErrorV1b('requires A1a three-neuron fabric')
    nodes = {n.node_id: n for n in case.nodes}
    if len(nodes) != len(case.nodes) or set(nodes) != {'A', 'B', 'C'}:
        raise PEAdmissionErrorV1b('requires three unique neurons A/B/C')
    if (len(set(fabric.pe_ids)) != len(fabric.pe_ids)
            or not fabric.pe_ids or len(fabric.placement) != len(nodes)):
        raise PEAdmissionErrorV1b('invalid PE population')
    owners = {}
    for p in fabric.placement:
        if p.node_id in owners or p.node_id not in nodes or p.pe_id not in fabric.pe_ids:
            raise PEAdmissionErrorV1b('invalid PE ownership')
        owners[p.node_id] = p.pe_id
    if set(owners) != set(nodes):
        raise PEAdmissionErrorV1b('incomplete PE ownership')

    for edge in case.edges:
        if (edge.source_node not in nodes or edge.target_node not in nodes
                or not _natural(edge.source_channel)
                or not _natural(edge.target_channel)
                or type(edge.delay_ticks) is not int or edge.delay_ticks <= 0):
            raise PEAdmissionErrorV1b('invalid source edge')
    source_edges = Counter((e.source_node, e.source_channel, e.target_node,
                            e.target_channel, e.delay_ticks) for e in case.edges)
    mapped_edges = Counter((r.source_node, r.source_channel, r.target_node,
                            r.target_channel, r.delay_ticks) for r in fabric.static_routes)
    if source_edges != mapped_edges:
        raise PEAdmissionErrorV1b('static PE routing differs from source edge occurrences')
    for route in fabric.static_routes:
        if (route.source_pe != owners.get(route.source_node)
                or route.target_pe != owners.get(route.target_node)):
            raise PEAdmissionErrorV1b('PE route custody mismatch')
        if not (_natural(route.source_channel) and _natural(route.target_channel)
                and type(route.delay_ticks) is int and route.delay_ticks > 0):
            raise PEAdmissionErrorV1b('invalid PE route timing')

    for n in case.nodes:
        if (type(n.state_bits) is not int or not 1 <= n.state_bits <= 32
                or type(n.fractional_bits) is not int
                or not 0 <= n.fractional_bits < n.state_bits
                or not _natural(n.initial_raw)
                or n.initial_raw >= (1 << n.state_bits)):
            raise PEAdmissionErrorV1b('invalid PE neuron config')
        for ins in n.instructions:
            if not isinstance(ins, tuple) or len(ins) != 2:
                raise PEAdmissionErrorV1b('invalid instruction')
            op, arg = ins
            if op == 'ACC':
                if (type(arg) is not tuple or len(arg) != 2
                        or not all(_natural(x) for x in arg)):
                    raise PEAdmissionErrorV1b('invalid ACC')
            elif op in ('CMP', 'EMIT', 'RESET', 'SHIFT'):
                if not _natural(arg) or (op == 'RESET' and arg >= 1 << n.state_bits):
                    raise PEAdmissionErrorV1b('invalid operand')
            else:
                raise PEAdmissionErrorV1b('instruction outside A1b fragment')
    for event in case.events:
        if (event.node_id not in nodes or not _natural(event.timestamp)
                or not _natural(event.channel)):
            raise PEAdmissionErrorV1b('invalid input event')
    return nodes, owners


def _compute_local(node, state, timestamp, channels):
    """Local PE neuron semantics, implemented without using frozen or oracle engines."""
    raw, previous = state
    if timestamp < previous:
        raise PEAdmissionErrorV1b('backward neuron timestamp')
    dt = timestamp - previous
    counts = Counter(channels)
    guard = False
    outputs = []
    for opcode, argument in node.instructions:
        if opcode == 'ACC':
            weight, channel = argument
            raw += weight * (1 << node.fractional_bits) * counts[channel]
            if raw >= (1 << node.state_bits):
                raise PEAdmissionErrorV1b('Core state overflow outside A1b domain')
        elif opcode == 'CMP':
            guard = raw >= argument
        elif opcode == 'EMIT':
            if guard:
                outputs.append(argument)
        elif opcode == 'RESET':
            if guard:
                raw = argument
        else:  # SHIFT
            raw >>= argument * dt
    return raw, guard, tuple(outputs)


def execute_on_pes_v1b(case, fabric, *, max_batches=128, max_events=4096):
    """Execute on PE-owned queues and memories under an ideal global clock.

    The global arbiter selects the lexicographically earliest (tick, neuron)
    from local PE queue heads. Routing creates a distinct delivery occurrence
    for each edge, including duplicates; inter-PE transfer adds *no extra*
    latency beyond declared edge.delay_ticks.
    """
    nodes, owner = _admit(case, fabric)
    if not (type(max_batches) is int and max_batches > 0
            and type(max_events) is int and max_events > 0):
        raise PEAdmissionErrorV1b('invalid positive execution bounds')
    pes = {pid: PEContextV1b(pid) for pid in fabric.pe_ids}
    for nid, node in nodes.items():
        pes[owner[nid]].states[nid] = [node.initial_raw, 0]
    for event in case.events:
        pes[owner[event.node_id]].enqueue(event.timestamp, event.node_id, event.channel)
    outgoing = {}
    for edge in fabric.static_routes:
        outgoing.setdefault((edge.source_node, edge.source_channel), []).append(edge)

    emissions, terminal, batch_log, route_log, transfers = [], [], [], [], []
    event_count = batch_count = 0
    while True:
        heads = [(head[0], head[1], pid) for pid, pe in pes.items()
                 if (head := pe.head()) is not None]
        if not heads:
            break
        timestamp, nid, pid = min(heads)
        pe = pes[pid]
        key, channels = pe.next_batch()
        assert key == (timestamp, nid)
        if batch_count >= max_batches:
            raise PELimitV1b('max_batches')
        if event_count + len(channels) > max_events:
            raise PELimitV1b('max_events')
        batch_count += 1
        event_count += len(channels)
        final_raw, guard, outputs = _compute_local(
            nodes[nid], pe.states[nid], timestamp, channels)
        pe.states[nid] = [final_raw, timestamp]
        for ch in outputs:
            emission = {'timestamp': timestamp, 'node_id': nid, 'channel': ch}
            emissions.append(emission)
            recipients = outgoing.get((nid, ch), ())
            if not recipients:
                terminal.append(emission)
            for route in recipients:
                delivery_tick = timestamp + route.delay_ticks
                pes[route.target_pe].enqueue(delivery_tick, route.target_node,
                                              route.target_channel)
                logical_route = {
                    'emission_timestamp': timestamp, 'source_node': nid,
                    'source_channel': ch, 'delivery_timestamp': delivery_tick,
                    'target_node': route.target_node,
                    'target_channel': route.target_channel,
                    'delay_ticks': route.delay_ticks,
                }
                route_log.append(logical_route)
                transfers.append({**logical_route, 'source_pe': pid,
                                  'target_pe': route.target_pe,
                                  'cross_pe': pid != route.target_pe})
        batch_log.append({'timestamp': timestamp, 'node_id': nid,
                          'channels': list(channels), 'final_raw': final_raw,
                          'final_guard': guard, 'output_channels': list(outputs)})
    result = {
        'emissions': emissions,
        'terminal_outputs': terminal,
        'states': [{'node_id': n.node_id,
                    'raw': pes[owner[n.node_id]].states[n.node_id][0],
                    'last_timestamp': pes[owner[n.node_id]].states[n.node_id][1]}
                   for n in case.nodes],
        'processed_batches': batch_count,
        'processed_events': event_count,
        'observations': {'batches': batch_log, 'routes': route_log},
    }
    return {'result': result,
            'transport': {'local_occurrences': sum(not x['cross_pe'] for x in transfers),
                          'cross_pe_occurrences': sum(x['cross_pe'] for x in transfers),
                          'transfers': transfers},
            'pe_snapshots': {pid: {'node_count': len(pe.states),
                                    'nodes': sorted(pe.states)}
                             for pid, pe in pes.items()}}
