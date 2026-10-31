from collections import defaultdict
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0,
    MemoryDomainV0,
)
from spk_architecture.profile_v0 import (
    ProcessingElementV0,
    ArchitectureProfileV0,
)
from spk_architecture.transaction_mapping_v0 import (
    MemoryServiceRequestV0,
)
from spk_architecture.arbitration_v0 import (
    PriorityRuleV0,
    ArbitrationPolicyV0,
    ArbitrationLimitV0,
    default_arbitration_policy_v0,
    arbitrate_memory_v0,
)


def machine(capacity=2, count=1):
    pes = tuple(
        ProcessingElementV0(
            pe_id=f"PE{i}",
            program_slots=8,
            state_slots=4,
            event_slots=8,
            output_slots=8,
            observation_slots=8,
            accesses_per_service_tick=capacity,
        )
        for i in range(count)
    )
    return ArchitectureProfileV0("machine-v0", pes)


def request(
    request_id,
    activity=ActivityV0.EXECUTE,
    *,
    pe="PE0",
    units=1,
    principal="principal",
    event_time=7,
):
    return MemoryServiceRequestV0(
        request_id=request_id,
        principal_id=principal,
        activity=activity,
        profile_id="cost-v0",
        epoch_id="E0",
        requester_pe_id=pe,
        target_pe_id=pe,
        target_id="memory",
        domain=MemoryDomainV0.STATE,
        kind=AccessIntentKindV0.STATE_LOAD,
        quantity=1,
        service_units=units,
        event_time=event_time,
    )


def schedule(requests, capacity=2, count=1, **kwargs):
    return arbitrate_memory_v0(
        machine(capacity, count),
        tuple(requests),
        default_arbitration_policy_v0(),
        **kwargs,
    )


def test_priority_precedence():
    result = schedule(
        (
            request(1, ActivityV0.REMODEL),
            request(2, ActivityV0.EXECUTE),
        ),
        capacity=1,
    )

    assert [s.request_id for s in result.slices] == [2, 1]
    assert result.total_service_ticks == 2


def test_pe_capacity_never_exceeded():
    result = schedule(
        (request(1, units=5), request(2, units=3)),
        capacity=2,
    )

    occupied = defaultdict(int)

    for item in result.slices:
        occupied[
            (item.target_pe_id, item.service_tick)
        ] += item.granted_units

    assert all(value <= 2 for value in occupied.values())
    assert result.total_service_units == 8
    assert result.total_service_ticks == 4


def test_multitick_request():
    result = schedule((request(1, units=5),), capacity=2)

    assert [s.granted_units for s in result.slices] == [2, 2, 1]
    assert [s.remaining_units for s in result.slices] == [3, 1, 0]
    assert result.completions[0].completion_tick == 3


def test_input_order_independent():
    requests = (
        request(3, ActivityV0.VERIFY),
        request(1, ActivityV0.EXECUTE),
        request(2, ActivityV0.LEARN),
    )

    assert schedule(requests) == schedule(requests[::-1])


def test_pes_serve_concurrently():
    result = schedule(
        (
            request(1, pe="PE0", units=2),
            request(2, pe="PE1", units=2),
        ),
        count=2,
    )

    assert result.total_service_ticks == 1
    assert len(result.completions) == 2
    assert all(
        item.completion_tick == 1
        for item in result.completions
    )


def test_event_time_unchanged():
    result = schedule(
        (request(1, units=5, event_time=11),)
    )
    assert all(
        item.event_time == 11
        for item in result.slices
    )


def test_duplicate_identity_rejected():
    with pytest.raises(ValueError):
        schedule((request(1), request(1)))


def test_same_id_different_principals_allowed():
    result = schedule((
        request(1, principal="A"),
        request(1, principal="B"),
    ))
    assert len(result.completions) == 2


def test_unknown_pe_rejected():
    with pytest.raises(ValueError):
        schedule((request(1, pe="UNKNOWN"),))


def test_invalid_service_units_rejected():
    with pytest.raises(ValueError):
        schedule((request(1, units=0),))


def test_budget_rejected_before_service():
    with pytest.raises(ArbitrationLimitV0):
        schedule(
            (request(1, units=5),),
            max_service_ticks=2,
        )


def test_service_demand_conserved():
    requests = (
        request(1, units=3),
        request(2, units=7),
        request(3, units=2),
    )

    result = schedule(requests)

    assert sum(
        s.granted_units for s in result.slices
    ) == sum(
        r.service_units for r in requests
    )


def test_empty_workload():
    result = schedule(())
    assert result.slices == ()
    assert result.completions == ()
    assert result.total_service_ticks == 0


def test_incomplete_priority_policy_rejected():
    policy = default_arbitration_policy_v0()
    with pytest.raises(ValueError):
        ArbitrationPolicyV0(
            policy_id="incomplete",
            rules=policy.rules[:-1],
        )


def test_invalid_priority_rejected():
    with pytest.raises(ValueError):
        PriorityRuleV0(ActivityV0.EXECUTE, 6)


def test_request_not_modified():
    original = request(1, units=3)
    before = replace(original)

    schedule((original,))

    assert original == before
