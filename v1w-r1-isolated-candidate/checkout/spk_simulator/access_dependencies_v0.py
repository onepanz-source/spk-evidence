"""SPK causal memory-access dependencies v0.

Builds a deterministic dependency DAG from an
observed execution and reconciled event provenance.

No scheduling, memory mutation or service time.
"""

from collections import Counter
from dataclasses import dataclass
from heapq import heappop, heappush

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
)
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.functional_trace_v0 import ObservedExecutionV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.event_provenance_v0 import (
    EventProvenanceV0,
    reconcile_event_provenance_v0,
)


@dataclass(frozen=True, slots=True)
class AccessDependencyV0:
    request_id: int
    predecessor_ids: tuple[int, ...]

    def __post_init__(self):
        if type(self.request_id) is not int or self.request_id < 0:
            raise ValueError("invalid request_id")

        if type(self.predecessor_ids) is not tuple:
            raise TypeError("predecessor_ids must be a tuple")

        for predecessor in self.predecessor_ids:
            if type(predecessor) is not int or predecessor < 0:
                raise ValueError("invalid predecessor ID")

        if (
            self.request_id in self.predecessor_ids
            or tuple(sorted(set(self.predecessor_ids)))
                != self.predecessor_ids
        ):
            raise ValueError("invalid predecessor set")


def _topological_ids(dependencies):
    predecessor_map = {
        item.request_id: item.predecessor_ids
        for item in dependencies
    }

    successors = {key: [] for key in predecessor_map}
    indegree = {}

    for request_id, predecessors in predecessor_map.items():
        indegree[request_id] = len(predecessors)

        for predecessor in predecessors:
            if predecessor not in successors:
                raise ValueError("unknown predecessor")
            successors[predecessor].append(request_id)

    ready = []

    for request_id, degree in indegree.items():
        if degree == 0:
            heappush(ready, request_id)

    result = []

    while ready:
        request_id = heappop(ready)
        result.append(request_id)

        for successor in successors[request_id]:
            indegree[successor] -= 1

            if indegree[successor] == 0:
                heappush(ready, successor)

    if len(result) != len(dependencies):
        raise ValueError("cyclic access dependencies")

    return tuple(result)


@dataclass(frozen=True, slots=True)
class AccessDependencyGraphV0:
    dependencies: tuple[AccessDependencyV0, ...]

    def __post_init__(self):
        if type(self.dependencies) is not tuple:
            raise TypeError("dependencies must be a tuple")

        if any(
            type(item) is not AccessDependencyV0
            for item in self.dependencies
        ):
            raise TypeError("invalid dependency")

        ids = tuple(
            item.request_id for item in self.dependencies
        )

        if ids != tuple(sorted(set(ids))):
            raise ValueError("noncanonical request IDs")

        _topological_ids(self.dependencies)


def topological_request_ids_v0(
    graph: AccessDependencyGraphV0,
) -> tuple[int, ...]:
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError("invalid dependency graph")

    return _topological_ids(graph.dependencies)


def build_access_dependencies_v0(
    network: NetworkV0,
    observed: ObservedExecutionV0,
    placement: PEAdmissionManifestV0,
    plan: LogicalAccessPlanV0,
    provenance: EventProvenanceV0,
    initial_events: tuple[NetworkEventV0, ...],
) -> AccessDependencyGraphV0:
    """Derive access precedence, not simulated execution time."""

    if type(provenance) is not EventProvenanceV0:
        raise TypeError("invalid provenance")

    expected = reconcile_event_provenance_v0(
        network,
        observed,
        placement,
        plan,
        initial_events,
    )

    if provenance != expected:
        raise ValueError("provenance mismatch")

    route_counts = Counter(
        (route.emission_timestamp, route.source_node)
        for route in observed.routes
    )

    references = plan.references
    dependencies = []
    previous_state_commit = {}
    cursor = 0

    def take(kind, node_id, timestamp, activity, predecessors):
        nonlocal cursor

        if cursor >= len(references):
            raise ValueError("missing logical access")

        reference = references[cursor]
        intent = reference.intent

        if not (
            intent.request_id == cursor
            and intent.kind is kind
            and intent.activity is activity
            and intent.event_time == timestamp
        ):
            raise ValueError("logical access order mismatch")

        if node_id is not None and intent.node_id != node_id:
            raise ValueError("logical access node mismatch")

        dependency = AccessDependencyV0(
            request_id=intent.request_id,
            predecessor_ids=tuple(sorted(set(predecessors))),
        )

        dependencies.append(dependency)
        cursor += 1

        return dependency.request_id

    for index, batch in enumerate(observed.batches):
        info = provenance.batches[index]
        node_id = batch.node_id
        timestamp = batch.timestamp

        if not (
            info.batch_index == index
            and info.timestamp == timestamp
            and info.node_id == node_id
            and info.channels == batch.channels
        ):
            raise ValueError("batch provenance mismatch")

        program_id = take(
            Kind.PROGRAM_REFERENCE,
            node_id,
            timestamp,
            Activity.EXECUTE,
            (),
        )

        previous_commit = previous_state_commit.get(node_id)

        state_id = take(
            Kind.STATE_LOAD,
            node_id,
            timestamp,
            Activity.EXECUTE,
            () if previous_commit is None
            else (previous_commit,),
        )

        consume_id = take(
            Kind.BATCH_CONSUME,
            node_id,
            timestamp,
            Activity.EXECUTE,
            info.routed_request_ids,
        )

        ready_ids = (program_id, state_id, consume_id)

        commit_id = take(
            Kind.STATE_COMMIT,
            node_id,
            timestamp,
            Activity.EXECUTE,
            ready_ids,
        )

        previous_state_commit[node_id] = commit_id

        emission_id = None

        if batch.output_channels:
            emission_id = take(
                Kind.EMISSION_RECORD,
                node_id,
                timestamp,
                Activity.EXECUTE,
                ready_ids,
            )

        route_count = route_counts[(timestamp, node_id)]

        if route_count and emission_id is None:
            raise ValueError("routing without emission")

        for _ in range(route_count):
            take(
                Kind.ROUTE_ENQUEUE,
                None,
                timestamp,
                Activity.ROUTER,
                (emission_id,),
            )

    if cursor != len(references):
        raise ValueError("unaccounted logical accesses")

    return AccessDependencyGraphV0(
        dependencies=tuple(dependencies)
    )
