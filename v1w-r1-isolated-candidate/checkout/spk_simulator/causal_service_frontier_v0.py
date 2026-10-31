"""SPK S3.7d/3b2b2c: causal start-eligibility frontier, not an active scheduler.

Classifies service requests at an explicit SERVICE_TIME boundary, requiring
completed predecessors, released external inputs, and caller-authenticated
OUTPUT/EVENT memory grants. Does not spend PE service units or invent a grant.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0


def _ids(label: str, values: tuple[int, ...]):
    if (type(values) is not tuple or any(type(x) is not int or x < 0 for x in values)
            or len(set(values)) != len(values)):
        raise ValueError(f'invalid {label}')


def _predecessors(dependency):
    # Both spellings appear in historical revisions of the dependency API.
    # Prefer the named public property; never reinterpret EVENT_TIME.
    for field in ('predecessor_request_ids', 'predecessor_ids', 'predecessors'):
        value = getattr(dependency, field, None)
        if value is not None:
            _ids('dependency predecessors', value)
            return value
    raise ValueError('unsupported AccessDependencyV0 predecessor interface')


@dataclass(frozen=True, slots=True)
class CausalServiceCandidateV0:
    request_id: int
    pe_id: str
    kind: Kind
    classification: str  # READY, DEPENDENCY, RELEASE, MEMORY, IN_FLIGHT, COMPLETED
    missing_predecessors: tuple[int, ...] = ()
    release_boundary: int = 0


@dataclass(frozen=True, slots=True)
class CausalServiceFrontierV0:
    service_boundary: int
    candidates: tuple[CausalServiceCandidateV0, ...]
    ready_request_ids: tuple[int, ...]
    waiting_dependency_ids: tuple[int, ...]
    waiting_release_ids: tuple[int, ...]
    waiting_memory_ids: tuple[int, ...]
    in_flight_request_ids: tuple[int, ...]
    completed_request_ids: tuple[int, ...]


def classify_causal_service_frontier_v0(
    architecture: ArchitectureProfileV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    *,
    service_boundary: int,
    completed_request_ids: tuple[int, ...] = (),
    in_flight_request_ids: tuple[int, ...] = (),
    granted_memory_request_ids: tuple[int, ...] = (),
    ingress: ExternalIngressBindingV0 | None = None,
) -> CausalServiceFrontierV0:
    """Classify request start eligibility; all external claims are caller evidence.

    This is not a grant allocator and does not validate historical service-unit
    completions. The upcoming owner-scheduler must authenticate all inputs.
    No request is marked READY with an unsatisfied predecessor, external
    release, or ungranted ROUTE_ENQUEUE/EMISSION_RECORD storage operation.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid service requests')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid dependency graph')
    if ingress is not None and type(ingress) is not ExternalIngressBindingV0:
        raise TypeError('invalid ingress')
    if type(service_boundary) is not int or service_boundary < 0:
        raise ValueError('invalid SERVICE_TIME boundary')
    for name, value in (
        ('completed', completed_request_ids), ('in_flight', in_flight_request_ids),
        ('granted_memory', granted_memory_request_ids),
    ):
        _ids(name, value)
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate service request ID')
    pes = {p.pe_id for p in architecture.pes}
    for req in requests:
        if (type(req.request_id) is not int or req.request_id < 0
                or req.target_pe_id not in pes
                or type(req.service_units) is not int or req.service_units < 1):
            raise ValueError('invalid request identity, PE or service units')
    deps = {d.request_id: _predecessors(d) for d in graph.dependencies}
    if len(deps) != len(graph.dependencies) or set(deps) != set(by_id):
        raise ValueError('dependency graph/request coverage mismatch')
    for rid, predecessors in deps.items():
        if rid in predecessors or set(predecessors) - set(by_id):
            raise ValueError('invalid predecessor identity')
    # Validate DAG independently: an impossible cyclic graph is not a WAIT state.
    colors = {}
    def visit(rid):
        if colors.get(rid) == 1:
            raise ValueError('cyclic service dependency graph')
        if colors.get(rid) == 2:
            return
        colors[rid] = 1
        for prev in deps[rid]:
            visit(prev)
        colors[rid] = 2
    for rid in deps:
        visit(rid)
    completed = set(completed_request_ids)
    running = set(in_flight_request_ids)
    grants = set(granted_memory_request_ids)
    if (completed | running | grants) - set(by_id):
        raise ValueError('unknown request in frontier snapshot')
    if completed & running or (grants & (completed | running)):
        raise ValueError('conflicting service states')
    for rid in completed | running:
        if not set(deps[rid]) <= completed:
            raise ValueError('completed/running service has unfinished predecessors')
    for rid in grants:
        if by_id[rid].kind not in (Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE):
            raise ValueError('memory grant for non-memory-gated request')

    releases = {}
    if ingress is not None:
        arrivals = {a.input_index: a for a in ingress.arrivals}
        if len(arrivals) != len(ingress.arrivals):
            raise ValueError('duplicate external arrival')
        if set(arrivals) != set(range(len(arrivals))):
            raise ValueError('noncontiguous external arrivals')
        for release in ingress.batch_releases:
            rid = release.consume_request_id
            if rid in releases or rid not in by_id or by_id[rid].kind is not Kind.BATCH_CONSUME:
                raise ValueError('invalid batch release identity')
            bound = tuple(a.input_index for a in ingress.arrivals if a.consume_request_id == rid)
            if (release.input_indices != bound or release.ready_boundary !=
                    max((arrivals[i].arrival_boundary for i in bound), default=0)):
                raise ValueError('invalid external release accounting')
            releases[rid] = release.ready_boundary
        consumes = {r.request_id for r in requests if r.kind is Kind.BATCH_CONSUME}
        if set(releases) != consumes:
            raise ValueError('incomplete ingress release coverage')
        for a in ingress.arrivals:
            req = by_id.get(a.consume_request_id)
            if (req is None or req.kind is not Kind.BATCH_CONSUME or
                    a.target_pe_id != req.target_pe_id or a.event_time != req.event_time):
                raise ValueError('external arrival/request mismatch')

    candidates = []
    partitions = {name: [] for name in ('READY', 'DEPENDENCY', 'RELEASE', 'MEMORY', 'IN_FLIGHT', 'COMPLETED')}
    for rid in sorted(by_id):
        req = by_id[rid]
        missing = tuple(sorted(set(deps[rid]) - completed))
        release = releases.get(rid, 0)
        if rid in completed:
            label = 'COMPLETED'
        elif rid in running:
            label = 'IN_FLIGHT'
        elif missing:
            label = 'DEPENDENCY'
        elif release > service_boundary:
            label = 'RELEASE'
        elif req.kind in (Kind.EMISSION_RECORD, Kind.ROUTE_ENQUEUE) and rid not in grants:
            label = 'MEMORY'
        else:
            label = 'READY'
        partitions[label].append(rid)
        candidates.append(CausalServiceCandidateV0(rid, req.target_pe_id, req.kind,
                                                    label, missing, release))
    return CausalServiceFrontierV0(
        service_boundary, tuple(candidates),
        *(tuple(partitions[key]) for key in ('READY','DEPENDENCY','RELEASE','MEMORY','IN_FLIGHT','COMPLETED'))
    )
