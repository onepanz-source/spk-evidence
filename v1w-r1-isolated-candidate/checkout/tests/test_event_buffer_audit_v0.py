from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    AccessIntentKindV0 as Kind, ActivityV0 as Activity,
    MemoryAccessIntentV0, MemoryDomainV0 as Domain,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0 as Space, MemoryTargetV0,
    MemoryTargetCatalogV0, MemoryTargetReferenceV0,
)
from spk_architecture.profile_v0 import ProcessingElementV0, ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_architecture.arbitration_v0 import default_arbitration_policy_v0
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.event_provenance_v0 import (
    BatchInputProvenanceV0, EventProvenanceV0,
)
from spk_simulator.access_dependencies_v0 import (
    AccessDependencyV0, AccessDependencyGraphV0,
)
from spk_simulator.causal_scheduler_v0 import schedule_causal_services_v0
from spk_simulator.event_buffer_audit_v0 import (
    EventBufferOverflowV0, audit_event_buffers_v0,
)


def scenario(*, event_slots=2, service_capacity=2,
             external_at_b=False, two_at_a=False):
    pe = ProcessingElementV0(
        "PE0", 8, 4, event_slots, 8, 8, service_capacity,
    )
    machine = ArchitectureProfileV0(
        "test-machine", (pe, replace(pe, pe_id="PE1")),
    )
    targets = MemoryTargetCatalogV0((
        MemoryTargetV0("events:A", Space.ACTIVE, "E0", "PE0", Domain.EVENT, "A"),
        MemoryTargetV0("events:B", Space.ACTIVE, "E0", "PE1", Domain.EVENT, "B"),
    ))
    a_qty = 2 if two_at_a else 1
    b_qty = 2 + int(external_at_b)
    specs = (
        (0, Kind.BATCH_CONSUME, Activity.EXECUTE, "A", "PE0", "events:A", 2, a_qty),
        (1, Kind.ROUTE_ENQUEUE, Activity.ROUTER, "B", "PE0", "events:B", 2, 1),
        (2, Kind.ROUTE_ENQUEUE, Activity.ROUTER, "B", "PE0", "events:B", 2, 1),
        (3, Kind.BATCH_CONSUME, Activity.EXECUTE, "B", "PE1", "events:B", 4, b_qty),
    )
    references = []
    requests = []
    for req_id, kind, activity, node, pe_id, target_id, event_time, quantity in specs:
        intent = MemoryAccessIntentV0(
            request_id=req_id, epoch_id="E0", pe_id=pe_id,
            activity=activity, kind=kind, node_id=node,
            event_time=event_time, quantity=quantity,
        )
        references.append(MemoryTargetReferenceV0(intent, target_id))
        requests.append(MemoryServiceRequestV0(
            request_id=req_id, principal_id=f"principal-{req_id}",
            activity=activity, profile_id="units-v0", epoch_id="E0",
            requester_pe_id=pe_id,
            target_pe_id="PE0" if node == "A" else "PE1",
            target_id=target_id, domain=Domain.EVENT, kind=kind,
            quantity=quantity, service_units=1, event_time=event_time,
        ))
    plan = LogicalAccessPlanV0("E0", targets, tuple(references))
    initial = (NetworkEventV0(2, "A", 0),) * a_qty
    if external_at_b:
        initial += (NetworkEventV0(4, "B", 0),)
    provenance = EventProvenanceV0(
        batches=(
            BatchInputProvenanceV0(0, 2, "A", (0,) * a_qty, a_qty, ()),
            BatchInputProvenanceV0(1, 4, "B", (0,) * b_qty, int(external_at_b), (1, 2)),
        ),
        initial_count=len(initial), routed_count=2,
        processed_count=a_qty + b_qty,
    )
    graph = AccessDependencyGraphV0((
        AccessDependencyV0(0, ()),
        AccessDependencyV0(1, (0,)),
        AccessDependencyV0(2, (0,)),
        AccessDependencyV0(3, (1, 2)),
    ))
    schedule = schedule_causal_services_v0(
        machine, tuple(requests), graph, default_arbitration_policy_v0(),
    )
    return machine, plan, provenance, tuple(requests), schedule, initial


def audit(data):
    return audit_event_buffers_v0(*data)


def test_baseline_peak_and_conservation():
    result = audit(scenario())
    usage = {p.pe_id: p for p in result.pe_usage}
    assert (result.initial_count, result.routed_count, result.consumed_count) == (1, 2, 3)
    assert usage["PE0"].peak_occupied == 1
    assert usage["PE1"].peak_occupied == 2
    assert all(p.final_occupied == 0 for p in result.pe_usage)


def test_routes_enter_only_after_service_completion():
    data = scenario()
    result = audit(data)
    completed = {c.request_id: c.completion_tick for c in data[4].completions}
    for boundary in result.boundaries:
        if boundary.routed_enqueued:
            assert boundary.service_tick in {completed[1], completed[2]}


def test_routing_overflow_explicit():
    with pytest.raises(EventBufferOverflowV0) as exc:
        audit(scenario(event_slots=1))
    assert exc.value.pe_id == "PE1"
    assert exc.value.required == 2
    assert exc.value.capacity == 1


def test_initial_preload_overflow_explicit():
    with pytest.raises(EventBufferOverflowV0) as exc:
        audit(scenario(event_slots=1, two_at_a=True))
    assert exc.value.pe_id == "PE0"
    assert exc.value.service_tick == 0


def test_initial_and_routed_same_node_capacity():
    result = audit(scenario(event_slots=3, external_at_b=True))
    assert next(u for u in result.pe_usage if u.pe_id == "PE1").peak_occupied == 3


def test_initial_and_routed_together_overflow():
    with pytest.raises(EventBufferOverflowV0) as exc:
        audit(scenario(event_slots=2, external_at_b=True))
    assert exc.value.pe_id == "PE1"


def test_service_bandwidth_affects_buffer_boundaries():
    fast = audit(scenario(service_capacity=2))
    slow = audit(scenario(service_capacity=1))
    assert fast.initial_count == slow.initial_count
    assert fast.routed_count == slow.routed_count
    assert fast.consumed_count == slow.consumed_count
    assert fast.boundaries != slow.boundaries


def test_wrong_initials_rejected():
    data = scenario()
    with pytest.raises(ValueError):
        audit(data[:-1] + ((),))


def test_missing_service_completion_rejected():
    data = scenario()
    bad = replace(data[4], completions=data[4].completions[:-1])
    with pytest.raises(ValueError):
        audit(data[:4] + (bad,) + data[5:])


def test_route_not_ready_rejected():
    data = scenario()
    completions = tuple(
        replace(c, completion_tick=4) if c.request_id == 1 else c
        for c in data[4].completions
    )
    bad = replace(data[4], completions=completions, total_service_ticks=4)
    with pytest.raises(ValueError, match="not ready"):
        audit(data[:4] + (bad,) + data[5:])


def test_duplicate_route_provenance_rejected():
    data = scenario()
    batches = (data[2].batches[0], replace(data[2].batches[1], routed_request_ids=(1,1)))
    bad = replace(data[2], batches=batches)
    with pytest.raises(ValueError):
        audit(data[:2] + (bad,) + data[3:])


def test_empty_workload():
    data = scenario()
    plan = replace(data[1], references=())
    provenance = EventProvenanceV0((), 0, 0, 0)
    graph = AccessDependencyGraphV0(())
    empty_schedule = schedule_causal_services_v0(
        data[0], (), graph, default_arbitration_policy_v0(),
    )
    result = audit_event_buffers_v0(data[0], plan, provenance, (), empty_schedule, ())
    assert result.boundaries == ()
    assert all(u.peak_occupied == 0 for u in result.pe_usage)


def test_deterministic_replay():
    data = scenario()
    assert audit(data) == audit(data)
