"""SPK S3.7d/3b2b2k/5: serialize version-dependent neuron service.

Pure graph transform. It inserts genuine state-commit causal dependencies before
later same-node STATE_LOADs, but neither executes nor confirms a commit.
No Core/Network/Compiler v0 source is modified.
"""
from dataclasses import dataclass
from heapq import heappop, heappush

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0, AccessDependencyV0


@dataclass(frozen=True, slots=True)
class SerializedNeuronBatchV0:
    node_id: str
    epoch_id: str
    target_pe_id: str
    event_time: int
    consume_request_id: int
    program_request_id: int
    state_load_request_id: int
    state_commit_request_id: int
    previous_commit_request_id: int | None


@dataclass(frozen=True, slots=True)
class SerializedInternalGraphV0:
    graph: AccessDependencyGraphV0
    batches: tuple[SerializedNeuronBatchV0, ...]
    added_edges: tuple[tuple[int, int], ...]  # (predecessor_id, successor_id)


def _predecessors(item):
    if hasattr(item, 'predecessor_ids'):
        value = item.predecessor_ids
    elif hasattr(item, 'predecessors'):
        value = item.predecessors
    else:
        raise ValueError('unsupported dependency predecessor interface')
    if (type(value) is not tuple or any(type(x) is not int or x < 0 for x in value)
            or value != tuple(sorted(set(value)))):
        raise ValueError('noncanonical predecessor IDs')
    return value


def _check_acyclic(by_id):
    # Iterative Kahn check: large finite causal DAGs must not hit Python's
    # recursion limit solely because they contain a long valid dependency path.
    degree = {rid: len(pred) for rid, pred in by_id.items()}
    successors = {rid: [] for rid in by_id}
    for rid, predecessors in by_id.items():
        for previous in predecessors:
            successors[previous].append(rid)
    ready = []
    for rid in sorted(degree):
        if degree[rid] == 0:
            heappush(ready, rid)
    visited = 0
    while ready:
        rid = heappop(ready)
        visited += 1
        for child in successors[rid]:
            degree[child] -= 1
            if degree[child] == 0:
                heappush(ready, child)
    if visited != len(by_id):
        raise ValueError('cyclic internal service dependency graph')


def serialize_internal_access_graph_v0(
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
) -> SerializedInternalGraphV0:
    """Add state-version causality to ordinary batches without dropping prior DAG edges.

    For each neuron, STATE_COMMIT requires successful P/S reads and the actual
    BATCH_CONSUME. The *next* STATE_LOAD requires the prior STATE_COMMIT.
    PROGRAM_REFERENCE may prefetch from immutable P; EVENT consumption may
    proceed independently. A separate owner must witness and apply the commit.
    """
    if type(requests) is not tuple or any(type(x) is not MemoryServiceRequestV0 for x in requests):
        raise TypeError('invalid service requests')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid access dependency graph')
    if type(graph.dependencies) is not tuple or any(type(x) is not AccessDependencyV0 for x in graph.dependencies):
        raise TypeError('invalid dependency entries')
    reqs = {x.request_id: x for x in requests}
    if (len(reqs) != len(requests) or any(type(k) is not int or k < 0 for k in reqs)):
        raise ValueError('duplicate or invalid service request identities')
    graph_ids = tuple(x.request_id for x in graph.dependencies)
    if graph_ids != tuple(sorted(reqs)):
        raise ValueError('noncanonical or incomplete dependency IDs')
    old = {x.request_id: _predecessors(x) for x in graph.dependencies}
    if any(set(pred) - reqs.keys() or rid in pred for rid, pred in old.items()):
        raise ValueError('unknown or self-dependent request')
    _check_acyclic(old)
    consumes = {}
    for r in requests:
        if r.kind is not Kind.BATCH_CONSUME:
            continue
        if (type(r.event_time) is not int or r.event_time < 0 or r.quantity < 1
                or r.domain is not Domain.EVENT or not r.target_id.startswith('events:')):
            raise ValueError('invalid neuronal BATCH_CONSUME binding')
        node = r.target_id[len('events:'):]
        if not node:
            raise ValueError('empty neuronal target')
        key = (r.epoch_id, node, r.target_pe_id, r.event_time)
        if key in consumes:
            raise ValueError('multiple batches for one neuron and EVENT_TIME')
        consumes[key] = r
    relevant = (Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD, Kind.STATE_COMMIT)
    bound = set()
    batches = []
    by_node = {}
    for key, consume in consumes.items():
        epoch, node, pe, timestamp = key
        matches = {}
        for kind, prefix, domain in (
            (Kind.PROGRAM_REFERENCE, 'program', Domain.PROGRAM),
            (Kind.STATE_LOAD, 'state', Domain.STATE),
            (Kind.STATE_COMMIT, 'state', Domain.STATE),
        ):
            selected = [r for r in requests if r.kind is kind and r.epoch_id == epoch
                        and r.target_id == f'{prefix}:{node}' and r.event_time == timestamp]
            if len(selected) != 1:
                raise ValueError('missing or duplicated internal operation per batch')
            r = selected[0]
            if (r.target_pe_id != pe or r.domain is not domain or r.quantity != 1):
                raise ValueError('incompatible P/S request target, domain or PE')
            if r.request_id in bound:
                raise ValueError('reused internal request')
            matches[kind] = r
            bound.add(r.request_id)
        by_node.setdefault((epoch, node), []).append((timestamp, consume, matches))
    internal_ids = {r.request_id for r in requests if r.kind in relevant}
    if bound != internal_ids:
        raise ValueError('orphan internal service operation')
    after = {rid: set(pred) for rid, pred in old.items()}
    previous = {}
    for (epoch, node), entries in sorted(by_node.items()):
        entries.sort(key=lambda x: x[0])
        if len({consume.target_pe_id for _, consume, _ in entries}) != 1:
            raise ValueError('one neuron cannot migrate PE within one epoch')
        last_t = None
        last_commit = None
        for timestamp, consume, matches in entries:
            if last_t is not None and timestamp <= last_t:
                raise ValueError('nonmonotone EVENT_TIME for neuron')
            p = matches[Kind.PROGRAM_REFERENCE].request_id
            s = matches[Kind.STATE_LOAD].request_id
            c = matches[Kind.STATE_COMMIT].request_id
            after[c].update((p, s, consume.request_id))
            if last_commit is not None:
                after[s].add(last_commit)
            batches.append(SerializedNeuronBatchV0(
                node, epoch, consume.target_pe_id, timestamp,
                consume.request_id, p, s, c, last_commit,
            ))
            last_commit = c
            last_t = timestamp
    canonical = {rid: tuple(sorted(pred)) for rid, pred in after.items()}
    _check_acyclic(canonical)
    emitted = AccessDependencyGraphV0(tuple(
        AccessDependencyV0(rid, canonical[rid]) for rid in sorted(canonical)
    ))
    edges = tuple(sorted((p, rid) for rid in canonical
                         for p in canonical[rid] if p not in old[rid]))
    return SerializedInternalGraphV0(
        emitted,
        tuple(sorted(batches, key=lambda x: (x.epoch_id, x.node_id, x.event_time))),
        edges,
    )
