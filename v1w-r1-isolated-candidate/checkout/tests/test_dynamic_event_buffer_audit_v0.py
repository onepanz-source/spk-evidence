"""S3.6b/3: dynamic external arrivals in the completed event-buffer audit."""
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0 as Activity, AccessIntentKindV0 as Kind,
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
from spk_simulator.external_ingress_v0 import (
    ExternalArrivalV0, ExternalIngressPlanV0, bind_external_ingress_v0,
)
from spk_simulator.event_buffer_audit_v0 import (
    EventBufferOverflowV0, audit_event_buffers_v0,
)
from tests.test_event_buffer_audit_v0 import scenario


def causal_graph():
    return AccessDependencyGraphV0((
        AccessDependencyV0(0, ()),
        AccessDependencyV0(1, (0,)),
        AccessDependencyV0(2, (0,)),
        AccessDependencyV0(3, (1, 2)),
    ))


def arrival_bound(data, *boundaries):
    assert len(boundaries) == len(data[5])
    return bind_external_ingress_v0(
        data[1], data[2], data[5],
        ExternalIngressPlanV0(tuple(
            ExternalArrivalV0(i, boundary)
            for i, boundary in enumerate(boundaries)
        )),
    )


def reschedule(data, binding, graph=None):
    machine, plan, provenance, requests, _, initial = data
    schedule = schedule_causal_services_v0(
        machine, requests, causal_graph() if graph is None else graph,
        default_arbitration_policy_v0(), ingress=binding,
    )
    return (machine, plan, provenance, requests, schedule, initial)


def audit(data, binding):
    return audit_event_buffers_v0(*data, ingress=binding)


def test_zero_ingress_matches_legacy_exactly():
    data = scenario()
    bound = arrival_bound(data, 0)
    assert audit(data, bound) == audit_event_buffers_v0(*data)


def test_late_ingress_is_not_preloaded():
    data = scenario()
    bound = arrival_bound(data, 5)
    delayed = reschedule(data, bound)
    result = audit(delayed, bound)
    assert result.initial_count == 1
    assert result.consumed_count == 3
    assert min(b.service_tick for b in result.boundaries if b.external_enqueued) == 5
    assert all(b.external_enqueued == 0 for b in result.boundaries if b.service_tick < 5)
    assert result.pe_usage[0].peak_occupied == 1


def test_external_arrival_does_not_change_event_time():
    data = scenario()
    bound = arrival_bound(data, 12)
    delayed = reschedule(data, bound)
    result = audit(delayed, bound)
    assert bound.arrivals[0].event_time == 2
    assert bound.arrivals[0].arrival_boundary == 12
    assert all(r.event_time == old.event_time
               for r, old in zip(delayed[3], data[3]))
    assert result.initial_count == 1


def test_same_boundary_external_and_routed_overflow():
    data = scenario(event_slots=2, external_at_b=True)
    route_tick = next(c.completion_tick for c in data[4].completions
                      if c.request_id == 2)
    bound = arrival_bound(data, 0, route_tick)
    delayed = reschedule(data, bound)
    with pytest.raises(EventBufferOverflowV0) as exc:
        audit(delayed, bound)
    assert exc.value.pe_id == "PE1"
    assert exc.value.required == 3
    assert exc.value.capacity == 2


def test_staggered_batches_can_fit_one_slot():
    pe = ProcessingElementV0("PE0", 8, 4, 1, 8, 8, 1)
    machine = ArchitectureProfileV0("staggered", (pe,))
    catalog = MemoryTargetCatalogV0((
        MemoryTargetV0("events:A", Space.ACTIVE, "E0", "PE0", Domain.EVENT, "A"),
    ))
    refs, requests = [], []
    for index, timestamp in enumerate((2, 3)):
        intent = MemoryAccessIntentV0(
            request_id=index, epoch_id="E0", pe_id="PE0", activity=Activity.EXECUTE,
            kind=Kind.BATCH_CONSUME, node_id="A", event_time=timestamp, quantity=1,
        )
        refs.append(MemoryTargetReferenceV0(intent, "events:A"))
        requests.append(MemoryServiceRequestV0(
            request_id=index, principal_id=f"exec-{index}",
            activity=Activity.EXECUTE, profile_id="unit-v0", epoch_id="E0",
            requester_pe_id="PE0", target_pe_id="PE0", target_id="events:A",
            domain=Domain.EVENT, kind=Kind.BATCH_CONSUME,
            quantity=1, service_units=1, event_time=timestamp,
        ))
    plan = LogicalAccessPlanV0("E0", catalog, tuple(refs))
    initial = (NetworkEventV0(2, "A", 0), NetworkEventV0(3, "A", 0))
    provenance = EventProvenanceV0(
        (BatchInputProvenanceV0(0, 2, "A", (0,), 1, ()),
         BatchInputProvenanceV0(1, 3, "A", (0,), 1, ())),
        2, 0, 2,
    )
    deps = AccessDependencyGraphV0((
        AccessDependencyV0(0, ()), AccessDependencyV0(1, (0,)),
    ))
    bound = bind_external_ingress_v0(
        plan, provenance, initial,
        ExternalIngressPlanV0((ExternalArrivalV0(0, 0), ExternalArrivalV0(1, 5))),
    )
    schedule = schedule_causal_services_v0(
        machine, tuple(requests), deps, default_arbitration_policy_v0(),
        ingress=bound,
    )
    args = (machine, plan, provenance, tuple(requests), schedule, initial)
    result = audit(args, bound)
    assert result.consumed_count == 2
    assert result.pe_usage[0].peak_occupied == 1
    assert all(b.occupied_after <= 1 for b in result.boundaries)
    with pytest.raises(EventBufferOverflowV0):
        audit_event_buffers_v0(*args)


def test_duplicate_initial_occurrences_remain_distinct():
    data = scenario(two_at_a=True, event_slots=2)
    bound = arrival_bound(data, 1, 4)
    result = audit(reschedule(data, bound), bound)
    assert result.initial_count == 2
    assert [b.external_enqueued for b in result.boundaries if b.external_enqueued] == [1, 1]
    assert result.pe_usage[0].peak_occupied == 2


def test_mismatched_ingress_binding_rejected():
    data = scenario()
    bound = arrival_bound(data, 2)
    forged = replace(bound, arrivals=(replace(bound.arrivals[0], arrival_boundary=7),))
    with pytest.raises(ValueError, match="ingress/plan/provenance mismatch"):
        audit(data, forged)


def test_forged_channel_rejected():
    data = scenario()
    bound = arrival_bound(data, 0)
    forged = replace(bound, arrivals=(replace(bound.arrivals[0], channel=9),))
    with pytest.raises(ValueError, match="ingress/plan/provenance mismatch"):
        audit(data, forged)


def test_missing_external_occurrence_rejected():
    data = scenario()
    bound = arrival_bound(data, 0)
    with pytest.raises(ValueError, match="ingress must bind every"):
        audit(data, replace(bound, arrivals=()))


def test_legacy_schedule_cannot_consume_late_arrival():
    data = scenario()
    bound = arrival_bound(data, 15)
    with pytest.raises(ValueError, match="consumed before external arrival"):
        audit(data, bound)


def test_invalid_ingress_type_rejected():
    with pytest.raises(TypeError, match="invalid ingress binding"):
        audit(scenario(), "not an ingress binding")


def test_deterministic_dynamic_buffer_replay():
    data = scenario()
    bound = arrival_bound(data, 6)
    delayed = reschedule(data, bound)
    assert audit(delayed, bound) == audit(delayed, bound)


def test_empty_workload_has_no_occupancy():
    data = scenario()
    plan = replace(data[1], references=())
    provenance = EventProvenanceV0((), 0, 0, 0)
    empty = schedule_causal_services_v0(
        data[0], (), AccessDependencyGraphV0(()),
        default_arbitration_policy_v0(),
    )
    binding = bind_external_ingress_v0(
        plan, provenance, (), ExternalIngressPlanV0(())
    )
    result = audit_event_buffers_v0(data[0], plan, provenance, (), empty, (), ingress=binding)
    assert result.boundaries == ()
    assert all(u.peak_occupied == 0 for u in result.pe_usage)
