"""SPK S3.6b/2: explicit external-ingress release boundaries."""
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
    MemoryDomainV0 as Domain,
)
from spk_architecture.arbitration_v0 import default_arbitration_policy_v0
from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import (
    AccessDependencyGraphV0, AccessDependencyV0,
)
from spk_simulator.causal_scheduler_v0 import (
    CausalServiceLimitV0, schedule_causal_services_v0,
)
from spk_simulator.external_ingress_v0 import (
    BatchIngressReleaseV0, BoundExternalArrivalV0, ExternalIngressBindingV0,
)


def machine(capacity=1):
    return ArchitectureProfileV0(
        "machine-v0",
        tuple(
            ProcessingElementV0(
                pe_id=f"PE{i}",
                program_slots=8, state_slots=4, event_slots=8,
                output_slots=8, observation_slots=8,
                accesses_per_service_tick=capacity,
            )
            for i in range(2)
        ),
    )


def req(request_id, *, pe="PE0", kind=Kind.BATCH_CONSUME,
        event_time=2, units=1):
    return MemoryServiceRequestV0(
        request_id=request_id,
        principal_id=f"principal-{request_id}",
        activity=Activity.EXECUTE if kind is Kind.BATCH_CONSUME else Activity.ROUTER,
        profile_id="unit-v0",
        epoch_id="E0",
        requester_pe_id=pe,
        target_pe_id=pe,
        target_id=f"events:{'A' if pe == 'PE0' else 'B'}",
        domain=Domain.EVENT,
        kind=kind,
        quantity=1,
        service_units=units,
        event_time=event_time,
    )


def graph(*pairs):
    return AccessDependencyGraphV0(tuple(
        AccessDependencyV0(request_id, tuple(predecessors))
        for request_id, predecessors in pairs
    ))


def arrival(index, boundary, *, consume=0, pe="PE0", timestamp=2):
    return BoundExternalArrivalV0(
        input_index=index,
        event_time=timestamp,
        node_id="A" if pe == "PE0" else "B",
        channel=0,
        target_pe_id=pe,
        arrival_boundary=boundary,
        consume_request_id=consume,
    )


def ingress(arrivals, releases):
    return ExternalIngressBindingV0(tuple(arrivals), tuple(releases))


def release(consume, boundary, indices):
    return BatchIngressReleaseV0(consume, boundary, tuple(indices))


def schedule(requests, deps=None, binding=None, *, capacity=1,
             max_service_ticks=100):
    if deps is None:
        deps = graph(*(
            (r.request_id, ()) for r in sorted(requests, key=lambda r: r.request_id)
        ))
    return schedule_causal_services_v0(
        machine(capacity), tuple(requests), deps,
        default_arbitration_policy_v0(),
        ingress=binding, max_service_ticks=max_service_ticks,
    )


def first_tick(result, request_id):
    return min(s.service_tick for s in result.slices
               if s.request_id == request_id)


def complete_tick(result, request_id):
    return next(c.completion_tick for c in result.completions
                if c.request_id == request_id)


def test_duplicate_occurrences_wait_for_latest_boundary():
    result = schedule(
        (req(0),),
        binding=ingress(
            (arrival(0, 2), arrival(1, 7)),
            (release(0, 7, (0, 1)),),
        ),
    )
    assert first_tick(result, 0) == 7
    assert complete_tick(result, 0) == 8
    assert result.pe_usage[0].idle_ticks == 7
    assert result.total_service_units == 1


def test_early_external_arrival_starts_at_zero():
    result = schedule(
        (req(0),),
        binding=ingress((arrival(0, 0),), (release(0, 0, (0,)),)),
    )
    assert first_tick(result, 0) == 0
    assert complete_tick(result, 0) == 1


def test_absent_ingress_preserves_legacy_schedule():
    requests = (req(0, units=2), req(1, pe="PE1"))
    old = schedule(requests)
    explicit_zero = schedule(
        requests,
        binding=ingress(
            (arrival(0, 0), arrival(1, 0, consume=1, pe="PE1")),
            (release(0, 0, (0,)), release(1, 0, (1,))),
        ),
    )
    assert old == explicit_zero


def test_release_is_independent_of_event_time():
    result = schedule(
        (req(0, event_time=2),),
        binding=ingress((arrival(0, 12),), (release(0, 12, (0,)),)),
    )
    assert first_tick(result, 0) == 12
    assert all(s.event_time == 2 for s in result.slices)


def test_independent_pe_progresses_while_other_waits():
    result = schedule(
        (req(0), req(1, pe="PE1")),
        binding=ingress(
            (arrival(0, 9), arrival(1, 0, consume=1, pe="PE1")),
            (release(0, 9, (0,)), release(1, 0, (1,))),
        ),
    )
    assert complete_tick(result, 1) == 1
    assert complete_tick(result, 0) == 10


def test_join_requires_both_route_and_external_availability():
    routed = req(0, kind=Kind.ROUTE_ENQUEUE, pe="PE0", units=3)
    consumed = req(1, pe="PE1", event_time=4)
    deps = graph((0, ()), (1, (0,)))
    bound = ingress(
        (arrival(0, 5, consume=1, pe="PE1", timestamp=4),),
        (release(1, 5, (0,)),),
    )
    result = schedule((routed, consumed), deps, bound)
    assert complete_tick(result, 0) == 3
    assert first_tick(result, 1) == 5
    assert complete_tick(result, 1) == 6


def test_dependency_can_be_later_than_release():
    routed = req(0, kind=Kind.ROUTE_ENQUEUE, units=6)
    consumed = req(1, pe="PE1", event_time=4)
    deps = graph((0, ()), (1, (0,)))
    bound = ingress(
        (arrival(0, 1, consume=1, pe="PE1", timestamp=4),),
        (release(1, 1, (0,)),),
    )
    result = schedule((routed, consumed), deps, bound)
    assert complete_tick(result, 0) == 6
    assert first_tick(result, 1) == 6


def test_no_external_spikes_is_explicit_zero_release():
    result = schedule(
        (req(0),),
        binding=ingress((), (release(0, 0, ()),)),
    )
    assert first_tick(result, 0) == 0


def test_limit_counts_idle_cycles():
    bound = ingress((arrival(0, 8),), (release(0, 8, (0,)),))
    with pytest.raises(CausalServiceLimitV0):
        schedule((req(0),), binding=bound, max_service_ticks=8)
    assert schedule((req(0),), binding=bound,
                    max_service_ticks=9).total_service_ticks == 9


def test_missing_batch_release_is_rejected():
    with pytest.raises(ValueError, match="incomplete batch release"):
        schedule((req(0),), binding=ingress((), ()))


def test_release_unknown_request_is_rejected():
    with pytest.raises(ValueError, match="unknown batch consume"):
        schedule((req(0),), binding=ingress((), (release(9, 0, ()),)))


def test_release_for_wrong_operation_is_rejected():
    with pytest.raises(ValueError, match="unknown batch consume"):
        schedule((req(0, kind=Kind.ROUTE_ENQUEUE),),
                 binding=ingress((), (release(0, 0, ()),)))


def test_forged_release_boundary_is_rejected():
    with pytest.raises(ValueError, match="incorrect batch release"):
        schedule((req(0),), binding=ingress(
            (arrival(0, 5),), (release(0, 2, (0,)),),
        ))


def test_forged_release_membership_is_rejected():
    with pytest.raises(ValueError, match="release/input occurrence mismatch"):
        schedule((req(0),), binding=ingress(
            (arrival(0, 5),), (release(0, 5, (1,)),),
        ))


def test_duplicate_spike_occurrence_is_rejected():
    with pytest.raises(ValueError, match="duplicate initial input index"):
        schedule((req(0),), binding=ingress(
            (arrival(0, 2), arrival(0, 3)),
            (release(0, 3, (0, 0)),),
        ))


def test_bad_arrival_target_binding_is_rejected():
    with pytest.raises(ValueError, match="arrival/batch identity mismatch"):
        schedule((req(0),), binding=ingress(
            (arrival(0, 1, pe="PE1"),),
            (release(0, 1, (0,)),),
        ))


def test_arrival_for_unknown_consume_is_rejected():
    with pytest.raises(ValueError, match="unknown batch consume"):
        schedule((req(0),), binding=ingress(
            (arrival(0, 1, consume=91),),
            (release(0, 0, ()),),
        ))


def test_empty_workload_with_empty_binding():
    result = schedule((), binding=ingress((), ()))
    assert result.slices == ()
    assert result.total_service_ticks == 0


def test_input_order_is_deterministic_with_releases():
    requests = (req(0), req(1, pe="PE1"))
    bound = ingress(
        (arrival(0, 4), arrival(1, 1, consume=1, pe="PE1")),
        (release(0, 4, (0,)), release(1, 1, (1,))),
    )
    assert schedule(requests, binding=bound) == schedule(
        requests[::-1], binding=bound
    )


def test_legacy_dependency_barrier_preserved():
    requests = (req(0), req(1, pe="PE1"))
    bound = ingress(
        (arrival(0, 3), arrival(1, 0, consume=1, pe="PE1")),
        (release(0, 3, (0,)), release(1, 0, (1,))),
    )
    result = schedule(requests, graph((0, ()), (1, (0,))), bound)
    assert complete_tick(result, 0) == 4
    assert first_tick(result, 1) == 4
