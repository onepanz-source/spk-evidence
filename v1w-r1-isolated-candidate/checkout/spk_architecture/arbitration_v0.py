"""SPK deterministic architectural arbitration v0.

Finite, all-ready-at-zero service scheduling.
No memory mutation or neuronal execution.
"""

from dataclasses import dataclass
from math import ceil

from spk_architecture.access_v0 import (
    ActivityV0,
    MemoryDomainV0,
    AccessIntentKindV0,
)
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import (
    MemoryServiceRequestV0,
)


class ArbitrationLimitV0(RuntimeError):
    code = "EXECUTION_LIMIT"


@dataclass(frozen=True, slots=True)
class PriorityRuleV0:
    activity: ActivityV0
    priority: int

    def __post_init__(self):
        if type(self.activity) is not ActivityV0:
            raise TypeError("invalid activity")
        if type(self.priority) is not int:
            raise TypeError("invalid priority")
        if not 0 <= self.priority <= 5:
            raise ValueError("priority outside P0-P5")


@dataclass(frozen=True, slots=True)
class ArbitrationPolicyV0:
    policy_id: str
    rules: tuple[PriorityRuleV0, ...]

    def __post_init__(self):
        if (
            type(self.policy_id) is not str
            or not self.policy_id
            or self.policy_id.strip() != self.policy_id
        ):
            raise ValueError("invalid policy ID")

        if type(self.rules) is not tuple:
            raise TypeError("rules must be a tuple")

        if any(
            type(rule) is not PriorityRuleV0
            for rule in self.rules
        ):
            raise TypeError("invalid priority rule")

        activities = [r.activity for r in self.rules]

        if (
            len(set(activities)) != len(activities)
            or set(activities) != set(ActivityV0)
        ):
            raise ValueError("incomplete priority policy")

    def priority_for(self, activity):
        for rule in self.rules:
            if rule.activity is activity:
                return rule.priority
        raise ValueError("unknown activity")


def default_arbitration_policy_v0():
    return ArbitrationPolicyV0(
        policy_id="spk-fixed-priority-v0",
        rules=(
            PriorityRuleV0(ActivityV0.EXECUTE, 0),
            PriorityRuleV0(ActivityV0.ROUTER, 0),
            PriorityRuleV0(ActivityV0.LEARN, 2),
            PriorityRuleV0(ActivityV0.VERIFY, 3),
            PriorityRuleV0(ActivityV0.REMODEL, 4),
            PriorityRuleV0(ActivityV0.OBSERVER, 5),
        ),
    )


@dataclass(frozen=True, slots=True)
class ServiceSliceV0:
    principal_id: str
    request_id: int
    target_pe_id: str
    target_id: str
    domain: MemoryDomainV0
    activity: ActivityV0
    priority: int
    event_time: int | None
    service_tick: int
    granted_units: int
    remaining_units: int


@dataclass(frozen=True, slots=True)
class ServiceCompletionV0:
    principal_id: str
    request_id: int
    target_pe_id: str
    completion_tick: int


@dataclass(frozen=True, slots=True)
class PEArbitrationUsageV0:
    pe_id: str
    capacity_per_tick: int
    service_units: int
    service_ticks: int


@dataclass(frozen=True, slots=True)
class ArbitrationResultV0:
    policy_id: str
    slices: tuple[ServiceSliceV0, ...]
    completions: tuple[ServiceCompletionV0, ...]
    pe_usage: tuple[PEArbitrationUsageV0, ...]
    total_service_units: int
    total_service_ticks: int


def _validate_request(request):
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
            raise ValueError(f"invalid request {name}")

    for name in ("request_id", "quantity", "service_units"):
        value = getattr(request, name)
        minimum = 0 if name == "request_id" else 1
        if type(value) is not int or value < minimum:
            raise ValueError(f"invalid request {name}")

    if type(request.activity) is not ActivityV0:
        raise TypeError("invalid request activity")

    if type(request.domain) is not MemoryDomainV0:
        raise TypeError("invalid request domain")

    if type(request.kind) is not AccessIntentKindV0:
        raise TypeError("invalid request kind")

    if request.event_time is not None:
        if (
            type(request.event_time) is not int
            or request.event_time < 0
        ):
            raise ValueError("invalid event_time")


def arbitrate_memory_v0(
    architecture: ArchitectureProfileV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    policy: ArbitrationPolicyV0,
    *,
    max_service_ticks: int = 10000,
) -> ArbitrationResultV0:
    """Schedule finite service requests across target PEs."""

    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture")

    if type(requests) is not tuple:
        raise TypeError("requests must be a tuple")

    if type(policy) is not ArbitrationPolicyV0:
        raise TypeError("invalid arbitration policy")

    if (
        type(max_service_ticks) is not int
        or max_service_ticks <= 0
    ):
        raise ValueError("invalid max_service_ticks")

    pe_map = {pe.pe_id: pe for pe in architecture.pes}
    grouped = {pe.pe_id: [] for pe in architecture.pes}
    identities = set()

    for request in requests:
        _validate_request(request)

        identity = (request.principal_id, request.request_id)

        if identity in identities:
            raise ValueError("duplicate service request identity")

        identities.add(identity)

        if request.target_pe_id not in pe_map:
            raise ValueError("unknown target PE")

        grouped[request.target_pe_id].append(request)

    # Admission before any service.
    minimum_ticks = 0

    for pe in architecture.pes:
        demand = sum(
            req.service_units
            for req in grouped[pe.pe_id]
        )

        required_ticks = ceil(
            demand / pe.accesses_per_service_tick
        )

        minimum_ticks = max(minimum_ticks, required_ticks)

    if minimum_ticks > max_service_ticks:
        raise ArbitrationLimitV0(
            f"required service ticks={minimum_ticks}, "
            f"limit={max_service_ticks}"
        )

    slices = []
    completions = []
    usage = []

    for pe in architecture.pes:
        capacity = pe.accesses_per_service_tick

        ordered = sorted(
            grouped[pe.pe_id],
            key=lambda req: (
                policy.priority_for(req.activity),
                req.principal_id,
                req.request_id,
            ),
        )

        tick = 0
        available = capacity
        total_units = 0

        for request in ordered:
            remaining = request.service_units
            priority = policy.priority_for(request.activity)

            while remaining:
                granted = min(remaining, available)
                remaining -= granted
                total_units += granted

                serviced_tick = tick

                slices.append(
                    ServiceSliceV0(
                        principal_id=request.principal_id,
                        request_id=request.request_id,
                        target_pe_id=pe.pe_id,
                        target_id=request.target_id,
                        domain=request.domain,
                        activity=request.activity,
                        priority=priority,
                        event_time=request.event_time,
                        service_tick=serviced_tick,
                        granted_units=granted,
                        remaining_units=remaining,
                    )
                )

                available -= granted

                if available == 0:
                    tick += 1
                    available = capacity

                if remaining == 0:
                    completions.append(
                        ServiceCompletionV0(
                            principal_id=request.principal_id,
                            request_id=request.request_id,
                            target_pe_id=pe.pe_id,
                            completion_tick=serviced_tick + 1,
                        )
                    )

        usage.append(
            PEArbitrationUsageV0(
                pe_id=pe.pe_id,
                capacity_per_tick=capacity,
                service_units=total_units,
                service_ticks=ceil(total_units / capacity),
            )
        )

    return ArbitrationResultV0(
        policy_id=policy.policy_id,
        slices=tuple(slices),
        completions=tuple(completions),
        pe_usage=tuple(usage),
        total_service_units=sum(
            item.service_units for item in usage
        ),
        total_service_ticks=max(
            (item.service_ticks for item in usage),
            default=0,
        ),
    )
