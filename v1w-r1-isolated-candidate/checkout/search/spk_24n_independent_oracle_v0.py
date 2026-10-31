"""SPK 24n independent, bounded operational oracle for a declared Core fragment.

No import of spk_core, spk_network, spk_compiler or SPK runtime is permitted.
Inputs are primitive dataclasses. The frozen system is used only by the
separate differential adapter to construct a case and obtain its *actual*
result; it is NEVER used to derive the expected execution.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import heapq


class OracleDomainErrorV0(ValueError):
    pass


class OracleLimitV0(RuntimeError):
    pass


@dataclass(frozen=True)
class NodeV0:
    node_id: str
    state_bits: int
    fractional_bits: int
    initial_raw: int
    instructions: tuple[tuple, ...]


@dataclass(frozen=True)
class EdgeV0:
    source_node: str
    source_channel: int
    target_node: str
    target_channel: int
    delay_ticks: int


@dataclass(frozen=True)
class EventV0:
    timestamp: int
    node_id: str
    channel: int


@dataclass(frozen=True)
class CaseV0:
    nodes: tuple[NodeV0, ...]
    edges: tuple[EdgeV0, ...]
    events: tuple[EventV0, ...]


def _uint(value, where):
    if type(value) is not int or value < 0:
        raise OracleDomainErrorV0(f"{where}: expected nonnegative integer")
    return value


def _check(case):
    if type(case) is not CaseV0 or not case.nodes:
        raise OracleDomainErrorV0("nonempty CaseV0 required")
    ids = []
    for n in case.nodes:
        if type(n) is not NodeV0 or type(n.node_id) is not str or not n.node_id:
            raise OracleDomainErrorV0("invalid node")
        ids.append(n.node_id)
        if (type(n.state_bits) is not int or not 1 <= n.state_bits <= 32
                or type(n.fractional_bits) is not int
                or not 0 <= n.fractional_bits < n.state_bits):
            raise OracleDomainErrorV0("unsupported Core config")
        max_raw = (1 << n.state_bits) - 1
        if _uint(n.initial_raw, "initial_raw") > max_raw:
            raise OracleDomainErrorV0("initial state outside width")
        if type(n.instructions) is not tuple:
            raise OracleDomainErrorV0("instructions must be tuple")
        for ins in n.instructions:
            if type(ins) is not tuple or len(ins) != 2 or type(ins[0]) is not str:
                raise OracleDomainErrorV0("invalid instruction encoding")
            op, arg = ins
            if op == "ACC":
                if type(arg) is not tuple or len(arg) != 2:
                    raise OracleDomainErrorV0("invalid ACC")
                _uint(arg[0], "weight")
                _uint(arg[1], "channel")
            elif op in ("CMP", "EMIT", "RESET", "SHIFT"):
                _uint(arg, op)
                if op == "RESET" and arg > max_raw:
                    raise OracleDomainErrorV0("RESET outside width")
            else:
                raise OracleDomainErrorV0("out-of-domain instruction: " + op)
    if len(set(ids)) != len(ids):
        raise OracleDomainErrorV0("duplicate node")
    known = set(ids)
    for e in case.edges:
        if type(e) is not EdgeV0 or e.source_node not in known or e.target_node not in known:
            raise OracleDomainErrorV0("invalid edge")
        _uint(e.source_channel, "source_channel")
        _uint(e.target_channel, "target_channel")
        if _uint(e.delay_ticks, "delay_ticks") == 0:
            raise OracleDomainErrorV0("edge delay must be strictly positive")
    for event in case.events:
        if type(event) is not EventV0 or event.node_id not in known:
            raise OracleDomainErrorV0("invalid external event")
        _uint(event.timestamp, "timestamp")
        _uint(event.channel, "channel")


def _event(t, node, ch):
    return {"timestamp": t, "node_id": node, "channel": ch}


def execute_v0(case: CaseV0, *, max_batches=128, max_events=4096):
    """Execute primitive IR with a separate event queue and Core interpreter.

    Canonical observable projection: emissions, terminal outputs, state values,
    batch/route observations and event/batch counts. No hidden runtime calls.
    """
    _check(case)
    if (type(max_batches) is not int or max_batches < 1
            or type(max_events) is not int or max_events < 1):
        raise OracleDomainErrorV0("positive limits required")
    nodes = {n.node_id: n for n in case.nodes}
    memory = {n.node_id: [n.initial_raw, 0] for n in case.nodes}
    # Batch by (time, node) using independent pending storage.
    pending = defaultdict(list)
    times = []

    def offer(t, nid, ch):
        key = (t, nid)
        if key not in pending:
            heapq.heappush(times, key)
        pending[key].append(ch)

    for e in case.events:
        offer(e.timestamp, e.node_id, e.channel)
    routes_by_source = defaultdict(list)
    for edge in case.edges:
        routes_by_source[(edge.source_node, edge.source_channel)].append(edge)

    emitted = []
    terminal = []
    batches = []
    routes = []
    processed_events = 0
    processed_batches = 0
    while times:
        timestamp, nid = heapq.heappop(times)
        key = (timestamp, nid)
        if key not in pending:
            continue
        channels = tuple(sorted(pending.pop(key)))
        # Limits apply to successfully processed logical work, not offered work.
        if processed_batches >= max_batches:
            raise OracleLimitV0("max_batches")
        if processed_events + len(channels) > max_events:
            raise OracleLimitV0("max_events")
        processed_batches += 1
        processed_events += len(channels)
        n = nodes[nid]
        raw, previous = memory[nid]
        if timestamp < previous:
            raise OracleDomainErrorV0("nonmonotonic neuron time")
        dt = timestamp - previous
        counts = Counter(channels)
        guard = False
        output_channels = []
        for op, arg in n.instructions:
            if op == "ACC":
                weight, ch = arg
                raw += weight * (1 << n.fractional_bits) * counts[ch]
                if raw > (1 << n.state_bits) - 1:
                    raise OracleDomainErrorV0("Core overflow outside successful domain")
            elif op == "SHIFT":
                raw >>= arg * dt
            elif op == "CMP":
                guard = raw >= arg
            elif op == "EMIT":
                if guard:
                    output_channels.append(arg)
            else:  # RESET
                if guard:
                    raw = arg
        memory[nid] = [raw, timestamp]
        for ch in output_channels:
            occurrence = _event(timestamp, nid, ch)
            emitted.append(occurrence)
            recipients = routes_by_source[(nid, ch)]
            if not recipients:
                terminal.append(occurrence)
            for edge in recipients:
                arrived = timestamp + edge.delay_ticks
                offer(arrived, edge.target_node, edge.target_channel)
                routes.append({
                    "emission_timestamp": timestamp,
                    "source_node": nid,
                    "source_channel": ch,
                    "delivery_timestamp": arrived,
                    "target_node": edge.target_node,
                    "target_channel": edge.target_channel,
                    "delay_ticks": edge.delay_ticks,
                })
        batches.append({
            "timestamp": timestamp, "node_id": nid,
            "channels": list(channels), "final_raw": raw,
            "final_guard": guard, "output_channels": list(output_channels),
        })
    return {
        "emissions": emitted,
        "terminal_outputs": terminal,
        "states": [{"node_id": n.node_id,
                    "raw": memory[n.node_id][0],
                    "last_timestamp": memory[n.node_id][1]}
                   for n in case.nodes],
        "processed_batches": processed_batches,
        "processed_events": processed_events,
        "observations": {"batches": batches, "routes": routes},
    }


def relay_path_support_v0(case: CaseV0):
    """Separate algebraic DAG path-support oracle, not event simulation.

    Domain: pure channel-0 to channel-7 relays with CMP(1), RESET(0),
    zero initial states, and acyclic directed edges. Supports duplicate edges
    and multiplicity in the input. Returns per-node emission *timestamp sets*.
    """
    _check(case)
    relay = (("ACC", (1, 0)), ("CMP", 1), ("EMIT", 7), ("RESET", 0))
    for n in case.nodes:
        if n.initial_raw != 0 or n.instructions != relay:
            raise OracleDomainErrorV0("not a relay path-support case")
    for e in case.edges:
        if e.source_channel != 7 or e.target_channel != 0:
            raise OracleDomainErrorV0("not a relay path-support edge")
    for e in case.events:
        if e.channel != 0:
            raise OracleDomainErrorV0("not a relay path-support input")
    successor = defaultdict(list)
    indegree = {n.node_id: 0 for n in case.nodes}
    for e in case.edges:
        successor[e.source_node].append((e.target_node, e.delay_ticks))
        indegree[e.target_node] += 1
    ready = sorted(node for node, degree in indegree.items() if degree == 0)
    supports = {n.node_id: set() for n in case.nodes}
    for e in case.events:
        supports[e.node_id].add(e.timestamp)
    visited = 0
    while ready:
        nid = ready.pop(0)
        visited += 1
        for target, delay in successor[nid]:
            supports[target].update(t + delay for t in supports[nid])
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if visited != len(case.nodes):
        raise OracleDomainErrorV0("relay path-support requires DAG")
    return {node: tuple(sorted(values)) for node, values in supports.items()}
