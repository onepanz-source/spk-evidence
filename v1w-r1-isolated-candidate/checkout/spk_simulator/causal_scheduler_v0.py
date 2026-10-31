"""SPK causal architectural service scheduler v0.

Schedules an already mapped, finite service-request DAG.
No event creation, memory mutation, or Network execution.
"""

from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush

from spk_architecture.access_v0 import (
    ActivityV0, AccessIntentKindV0, MemoryDomainV0,
)
from spk_architecture.arbitration_v0 import (
    ArbitrationPolicyV0, ServiceCompletionV0, ServiceSliceV0,
)
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0,
    BatchIngressReleaseV0,
)


class CausalServiceLimitV0(RuntimeError):
    code = "EXECUTION_LIMIT"


@dataclass(frozen=True, slots=True)
class CausalPEUsageV0:
    pe_id: str
    capacity_per_tick: int
    granted_units: int
    busy_ticks: int
    idle_ticks: int


@dataclass(frozen=True, slots=True)
class CausalScheduleResultV0:
    policy_id: str
    slices: tuple[ServiceSliceV0, ...]
    completions: tuple[ServiceCompletionV0, ...]
    pe_usage: tuple[CausalPEUsageV0, ...]
    total_service_units: int
    total_service_ticks: int


def _check_request(request):
    if type(request) is not MemoryServiceRequestV0:
        raise TypeError("invalid memory service request")

    for name in (
        "principal_id", "profile_id", "epoch_id",
        "requester_pe_id", "target_pe_id", "target_id",
    ):
        value = getattr(request, name)
        if (
            type(value) is not str
            or not value
            or value.strip() != value
        ):
            raise ValueError(f"invalid {name}")

    for name in ("request_id", "quantity", "service_units"):
        value = getattr(request, name)
        minimum = 0 if name == "request_id" else 1
        if type(value) is not int or value < minimum:
            raise ValueError(f"invalid {name}")

    if type(request.activity) is not ActivityV0:
        raise TypeError("invalid activity")

    if type(request.kind) is not AccessIntentKindV0:
        raise TypeError("invalid kind")

    if type(request.domain) is not MemoryDomainV0:
        raise TypeError("invalid domain")

    if request.event_time is not None and (
        type(request.event_time) is not int
        or request.event_time < 0
    ):
        raise ValueError("invalid EVENT_TIME")


def _ingress_release_boundaries_v0(ingress, request_by_id):
    """Validate binding coverage and derive explicit release boundaries.

    Does not prove an external plan's authenticity; bind_external_ingress_v0
    remains the authoritative producer from the original event occurrences.
    """
    if ingress is None:
        return {}
    if type(ingress) is not ExternalIngressBindingV0:
        raise TypeError("invalid ingress binding")

    arrivals_by_consume = defaultdict(list)
    seen_inputs = set()

    for arrival in ingress.arrivals:
        if type(arrival) is not BoundExternalArrivalV0:
            raise TypeError("invalid bound arrival")
        for name in ("input_index", "arrival_boundary", "consume_request_id"):
            value = getattr(arrival, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid arrival {name}")
        if arrival.input_index in seen_inputs:
            raise ValueError("duplicate initial input index")
        seen_inputs.add(arrival.input_index)

        request = request_by_id.get(arrival.consume_request_id)
        if request is None or request.kind is not AccessIntentKindV0.BATCH_CONSUME:
            raise ValueError("arrival references unknown batch consume")
        if not (
            request.target_pe_id == arrival.target_pe_id
            and request.target_id == f"events:{arrival.node_id}"
            and request.event_time == arrival.event_time
            and type(arrival.node_id) is str
            and arrival.node_id
        ):
            raise ValueError("arrival/batch identity mismatch")
        arrivals_by_consume[arrival.consume_request_id].append(arrival)

    if seen_inputs != set(range(len(ingress.arrivals))):
        raise ValueError("initial input indices must be contiguous")

    release_by_consume = {}
    for release in ingress.batch_releases:
        if type(release) is not BatchIngressReleaseV0:
            raise TypeError("invalid batch release")
        if (
            type(release.consume_request_id) is not int
            or release.consume_request_id < 0
            or type(release.ready_boundary) is not int
            or release.ready_boundary < 0
            or type(release.input_indices) is not tuple
        ):
            raise ValueError("invalid batch release fields")
        request_id = release.consume_request_id
        if request_id in release_by_consume:
            raise ValueError("duplicate batch release")
        request = request_by_id.get(request_id)
        if request is None or request.kind is not AccessIntentKindV0.BATCH_CONSUME:
            raise ValueError("release references unknown batch consume")

        bound = arrivals_by_consume.get(request_id, [])
        indices = tuple(item.input_index for item in bound)
        if release.input_indices != indices:
            raise ValueError("release/input occurrence mismatch")
        if release.ready_boundary != max(
            (item.arrival_boundary for item in bound), default=0
        ):
            raise ValueError("incorrect batch release boundary")
        release_by_consume[request_id] = release.ready_boundary

    consume_ids = {
        request_id for request_id, request in request_by_id.items()
        if request.kind is AccessIntentKindV0.BATCH_CONSUME
    }
    if set(release_by_consume) != consume_ids:
        raise ValueError("incomplete batch release coverage")
    return release_by_consume


def schedule_causal_services_v0(
    architecture: ArchitectureProfileV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    policy: ArbitrationPolicyV0,
    *,
    max_service_ticks: int = 10_000,
    ingress: ExternalIngressBindingV0 | None = None,
) -> CausalScheduleResultV0:
    """Fixed-priority, cycle-boundary, dependency-aware arbitration.

    Completion in service tick s enables successors only
    in tick s+1.
    """

    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")

    if type(requests) is not tuple:
        raise TypeError("requests must be a tuple")

    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError("invalid dependency graph")

    if type(policy) is not ArbitrationPolicyV0:
        raise TypeError("invalid arbitration policy")

    if (
        type(max_service_ticks) is not int
        or max_service_ticks <= 0
    ):
        raise ValueError("invalid max_service_ticks")

    pe_map = {pe.pe_id: pe for pe in architecture.pes}
    request_by_id = {}
    profile_ids = set()

    for request in requests:
        _check_request(request)

        if request.request_id in request_by_id:
            raise ValueError("duplicate request_id")

        if request.target_pe_id not in pe_map:
            raise ValueError("unknown target PE")

        if request.requester_pe_id not in pe_map:
            raise ValueError("unknown requester PE")

        request_by_id[request.request_id] = request
        profile_ids.add(request.profile_id)

    if len(profile_ids) > 1:
        raise ValueError("mixed service-unit profiles")

    if set(request_by_id) != {
        dependency.request_id
        for dependency in graph.dependencies
    }:
        raise ValueError("request/dependency identity mismatch")

    release_boundaries = _ingress_release_boundaries_v0(
        ingress, request_by_id
    )

    successors = defaultdict(list)
    indegree = {}

    for dependency in graph.dependencies:
        indegree[dependency.request_id] = len(
            dependency.predecessor_ids
        )

        for predecessor in dependency.predecessor_ids:
            successors[predecessor].append(
                dependency.request_id
            )

    ready = {pe_id: [] for pe_id in pe_map}
    waiting_for_release = []
    service_tick = 0
    remaining = {
        request_id: request.service_units
        for request_id, request in request_by_id.items()
    }

    def queue(request_id):
        boundary = release_boundaries.get(request_id, 0)
        if boundary > service_tick:
            heappush(waiting_for_release, (boundary, request_id))
            return
        request = request_by_id[request_id]

        heappush(
            ready[request.target_pe_id],
            (
                policy.priority_for(request.activity),
                request.principal_id,
                request.request_id,
            ),
        )

    for request_id in sorted(indegree):
        if indegree[request_id] == 0:
            queue(request_id)

    slices = []
    completions = []
    completed = set()

    granted_by_pe = {pe_id: 0 for pe_id in pe_map}
    busy_by_pe = {pe_id: 0 for pe_id in pe_map}

    while len(completed) < len(request_by_id):

        if service_tick >= max_service_ticks:
            raise CausalServiceLimitV0(
                f"service ticks exceeded {max_service_ticks}"
            )

        while (
            waiting_for_release
            and waiting_for_release[0][0] <= service_tick
        ):
            _, released_id = heappop(waiting_for_release)
            queue(released_id)

        finished_this_tick = []
        any_service = False

        for pe_id in sorted(pe_map):
            available = (
                pe_map[pe_id].accesses_per_service_tick
            )

            busy = False

            while available and ready[pe_id]:
                (
                    priority,
                    principal_id,
                    request_id,
                ) = heappop(ready[pe_id])

                request = request_by_id[request_id]

                granted = min(
                    available,
                    remaining[request_id],
                )

                remaining[request_id] -= granted
                available -= granted
                granted_by_pe[pe_id] += granted

                busy = True
                any_service = True

                slices.append(
                    ServiceSliceV0(
                        principal_id=principal_id,
                        request_id=request_id,
                        target_pe_id=pe_id,
                        target_id=request.target_id,
                        domain=request.domain,
                        activity=request.activity,
                        priority=priority,
                        event_time=request.event_time,
                        service_tick=service_tick,
                        granted_units=granted,
                        remaining_units=remaining[request_id],
                    )
                )

                if remaining[request_id] == 0:
                    completions.append(
                        ServiceCompletionV0(
                            principal_id=principal_id,
                            request_id=request_id,
                            target_pe_id=pe_id,
                            completion_tick=service_tick + 1,
                        )
                    )

                    finished_this_tick.append(request_id)

                else:
                    heappush(
                        ready[pe_id],
                        (priority, principal_id, request_id),
                    )

            if busy:
                busy_by_pe[pe_id] += 1

        if not any_service:
            if waiting_for_release:
                # The PE is idle until the next explicit input boundary.
                service_tick = waiting_for_release[0][0]
                continue
            raise RuntimeError(
                "causal scheduler made no progress"
            )

        # Release successors only after every PE
        # has finished the current service tick.
        for predecessor in finished_this_tick:
            completed.add(predecessor)

            for successor in successors[predecessor]:
                indegree[successor] -= 1

                if indegree[successor] == 0:
                    queue(successor)

        service_tick += 1

    slices.sort(
        key=lambda item: (
            item.service_tick,
            item.target_pe_id,
            item.priority,
            item.principal_id,
            item.request_id,
        )
    )

    completions.sort(
        key=lambda item: (
            item.completion_tick,
            item.target_pe_id,
            item.principal_id,
            item.request_id,
        )
    )

    pe_usage = tuple(
        CausalPEUsageV0(
            pe_id=pe_id,
            capacity_per_tick=(
                pe_map[pe_id].accesses_per_service_tick
            ),
            granted_units=granted_by_pe[pe_id],
            busy_ticks=busy_by_pe[pe_id],
            idle_ticks=service_tick - busy_by_pe[pe_id],
        )
        for pe_id in sorted(pe_map)
    )

    total_units = sum(granted_by_pe.values())

    if total_units != sum(
        request.service_units for request in requests
    ):
        raise RuntimeError(
            "service accounting invariant violated"
        )

    return CausalScheduleResultV0(
        policy_id=policy.policy_id,
        slices=tuple(slices),
        completions=tuple(completions),
        pe_usage=pe_usage,
        total_service_units=total_units,
        total_service_ticks=service_tick,
    )
