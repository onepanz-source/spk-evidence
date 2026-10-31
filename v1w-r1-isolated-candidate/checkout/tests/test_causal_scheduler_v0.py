from collections import defaultdict
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
    MemoryDomainV0 as Domain,
)
from spk_architecture.arbitration_v0 import (
    default_arbitration_policy_v0,
)
from spk_architecture.profile_v0 import (
    ArchitectureProfileV0,
    ProcessingElementV0,
)
from spk_architecture.transaction_mapping_v0 import (
    MemoryServiceRequestV0,
    TransactionCostProfileV0,
    TransactionCostRuleV0,
    map_memory_access_v0,
)
from spk_architecture.access_authorization_v0 import (
    AccessGrantV0,
    AuthorizationContextV0,
    AuthorizationPolicyV0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0,
    admit_pe_mapping_v0,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import (
    NetworkV0, NetworkNodeV0, NetworkEdgeV0,
)
from spk_core.isa import (
    CoreConfig, CoreAcc, CoreCmp,
    CoreEmit, CoreProgram, CoreReset,
)
from spk_simulator.functional_trace_v0 import (
    run_network_observed_v0,
)
from spk_simulator.logical_access_v0 import (
    generate_logical_accesses_v0,
)
from spk_simulator.event_provenance_v0 import (
    reconcile_event_provenance_v0,
)
from spk_simulator.access_dependencies_v0 import (
    AccessDependencyV0,
    AccessDependencyGraphV0,
    build_access_dependencies_v0,
)
from spk_simulator.causal_scheduler_v0 import (
    CausalServiceLimitV0,
    schedule_causal_services_v0,
)


def machine(capacity=1, pe_count=2):
    return ArchitectureProfileV0(
        "machine-v0",
        tuple(
            ProcessingElementV0(
                pe_id=f"PE{i}",
                program_slots=8,
                state_slots=4,
                event_slots=8,
                output_slots=8,
                observation_slots=8,
                accesses_per_service_tick=capacity,
            )
            for i in range(pe_count)
        ),
    )


def request(
    request_id,
    activity=Activity.EXECUTE,
    *,
    pe="PE0",
    requester=None,
    units=1,
    profile="cost-v0",
):
    kinds = {
        Activity.EXECUTE: (
            Kind.STATE_LOAD, Domain.STATE,
        ),
        Activity.ROUTER: (
            Kind.ROUTE_ENQUEUE, Domain.EVENT,
        ),
        Activity.LEARN: (
            Kind.OBSERVATION_READ, Domain.OBSERVATION,
        ),
        Activity.VERIFY: (
            Kind.SNAPSHOT_READ, Domain.STATE,
        ),
        Activity.REMODEL: (
            Kind.CANDIDATE_PROGRAM_WRITE, Domain.PROGRAM,
        ),
        Activity.OBSERVER: (
            Kind.OBSERVATION_RECORD, Domain.OBSERVATION,
        ),
    }

    kind, domain = kinds[activity]

    return MemoryServiceRequestV0(
        request_id=request_id,
        principal_id=f"principal-{request_id}",
        activity=activity,
        profile_id=profile,
        epoch_id="E0",
        requester_pe_id=(
            pe if requester is None else requester
        ),
        target_pe_id=pe,
        target_id=f"target-{request_id}",
        domain=domain,
        kind=kind,
        quantity=1,
        service_units=units,
        event_time=7,
    )


def graph(*items):
    return AccessDependencyGraphV0(
        tuple(
            AccessDependencyV0(
                request_id,
                tuple(preds),
            )
            for request_id, preds in items
        )
    )


def schedule(
    requests,
    dependencies=None,
    *,
    capacity=1,
    pe_count=2,
    max_service_ticks=100,
):
    if dependencies is None:
        dependencies = graph(
            *((item.request_id, ()) for item in requests)
        )

    return schedule_causal_services_v0(
        machine(capacity, pe_count),
        tuple(requests),
        dependencies,
        default_arbitration_policy_v0(),
        max_service_ticks=max_service_ticks,
    )


def tick_of(result, request_id):
    return next(
        completion.completion_tick
        for completion in result.completions
        if completion.request_id == request_id
    )


def test_priority_precedence():
    result = schedule((
        request(0, Activity.LEARN),
        request(1),
    ))

    assert [
        item.request_id for item in result.slices
    ] == [1, 0]


def test_capacity_per_tick():
    result = schedule(
        (request(0, units=5), request(1, units=2)),
        capacity=2,
    )

    used = defaultdict(int)

    for item in result.slices:
        used[
            (item.target_pe_id, item.service_tick)
        ] += item.granted_units

    assert max(used.values()) <= 2
    assert sum(
        item.granted_units for item in result.slices
    ) == 7
    assert result.total_service_units == 7


def test_independent_pes_overlap():
    result = schedule((
        request(0, pe="PE0"),
        request(1, pe="PE1"),
    ))

    assert result.total_service_ticks == 1
    assert {
        item.service_tick for item in result.slices
    } == {0}


def test_same_pe_successor_waits_next_tick():
    result = schedule(
        (request(0), request(1)),
        graph((0, ()), (1, (0,))),
        capacity=3,
    )

    assert tick_of(result, 0) == 1
    assert tick_of(result, 1) == 2


def test_remote_successor_waits_next_tick():
    result = schedule(
        (
            request(0, pe="PE0"),
            request(1, pe="PE1"),
        ),
        graph((0, ()), (1, (0,))),
    )

    assert tick_of(result, 0) == 1
    assert tick_of(result, 1) == 2
    assert result.pe_usage[1].idle_ticks == 1


def test_partial_service_multitick():
    result = schedule(
        (request(0, units=5),),
        capacity=2,
    )

    assert [
        (item.granted_units, item.remaining_units)
        for item in result.slices
    ] == [
        (2, 3),
        (2, 1),
        (1, 0),
    ]

    assert tick_of(result, 0) == 3


def test_preemption_at_tick_boundary():
    result = schedule(
        (
            request(0, Activity.REMODEL, units=3),
            request(1),
            request(2, pe="PE1"),
        ),
        graph(
            (0, ()),
            (1, (2,)),
            (2, ()),
        ),
    )

    assert [
        (item.request_id, item.service_tick)
        for item in result.slices
        if item.target_pe_id == "PE0"
    ] == [
        (0, 0),
        (1, 1),
        (0, 2),
        (0, 3),
    ]


def test_input_order_independent():
    requests = (
        request(2),
        request(0, pe="PE1"),
        request(1),
    )

    dependencies = graph(
        (0, ()),
        (1, (0,)),
        (2, ()),
    )

    assert schedule(
        requests, dependencies
    ) == schedule(
        requests[::-1], dependencies
    )


def test_event_time_unchanged():
    result = schedule(
        (request(0, units=3),)
    )

    assert all(
        item.event_time == 7
        for item in result.slices
    )


def test_duplicate_ids_rejected():
    with pytest.raises(
        ValueError, match="duplicate request_id"
    ):
        schedule(
            (request(0), request(0)),
            graph((0, ())),
        )


def test_missing_graph_request_rejected():
    with pytest.raises(
        ValueError, match="identity mismatch"
    ):
        schedule(
            (request(0), request(1)),
            graph((0, ())),
        )


def test_graph_extra_request_rejected():
    with pytest.raises(
        ValueError, match="identity mismatch"
    ):
        schedule(
            (request(0),),
            graph((0, ()), (1, ())),
        )


def test_unknown_target_pe_rejected():
    with pytest.raises(
        ValueError, match="unknown target PE"
    ):
        schedule((request(0, pe="PE99"),))


def test_unknown_requester_pe_rejected():
    with pytest.raises(
        ValueError, match="unknown requester PE"
    ):
        schedule((request(0, requester="PE99"),))


def test_invalid_demand_rejected():
    with pytest.raises(
        ValueError, match="invalid service_units"
    ):
        schedule((
            replace(request(0), service_units=0),
        ))


def test_mixed_cost_profiles_rejected():
    with pytest.raises(
        ValueError, match="mixed service-unit profiles"
    ):
        schedule((
            request(0),
            request(1, profile="other"),
        ))


def test_service_tick_limit():
    with pytest.raises(CausalServiceLimitV0):
        schedule(
            (request(0, units=3),),
            max_service_ticks=2,
        )


def test_empty_workload():
    result = schedule(())

    assert result.slices == ()
    assert result.completions == ()
    assert result.total_service_ticks == 0


def test_request_not_mutated():
    original = (
        request(0, units=2),
        request(1),
    )

    before = tuple(replace(item) for item in original)

    schedule(original)

    assert original == before


def test_actual_network_access_plan_integrates():
    config = CoreConfig(8, 0)

    program = CoreProgram((
        CoreAcc(weight=1, channel=0),
        CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7),
        CoreReset(value_raw=0),
    ))

    network = NetworkV0(
        nodes=(
            NetworkNodeV0("A", config, program),
            NetworkNodeV0("B", config, program),
        ),
        edges=(
            NetworkEdgeV0("A", 7, "B", 0, 2),
            NetworkEdgeV0("A", 7, "B", 0, 2),
            NetworkEdgeV0("A", 7, "B", 0, 3),
        ),
    )

    architecture = machine(capacity=2)

    placement = admit_pe_mapping_v0(
        network,
        architecture,
        (
            NodePlacementV0("A", "PE0"),
            NodePlacementV0("B", "PE1"),
        ),
    )

    initial = (NetworkEventV0(2, "A", 0),)

    observed = run_network_observed_v0(
        network, initial
    )

    plan = generate_logical_accesses_v0(
        network, observed, placement
    )

    provenance = reconcile_event_provenance_v0(
        network,
        observed,
        placement,
        plan,
        initial,
    )

    dependencies = build_access_dependencies_v0(
        network,
        observed,
        placement,
        plan,
        provenance,
        initial,
    )

    cost = TransactionCostProfileV0(
        "unit-cost-v0",
        tuple(
            TransactionCostRuleV0(kind, 1, 0)
            for kind in Kind
        ),
    )

    policy = AuthorizationPolicyV0("E0")
    requests = []

    for reference in plan.references:
        intent = reference.intent

        grant = AccessGrantV0(
            principal_id=(
                f"exec-{intent.node_id}"
                if intent.activity is Activity.EXECUTE
                else f"router-{intent.pe_id}"
            ),
            activity=intent.activity,
            pe_id=intent.pe_id,
            node_id=(
                intent.node_id
                if intent.activity is Activity.EXECUTE
                else None
            ),
        )

        context = AuthorizationContextV0(
            plan.catalog,
            placement,
            policy,
            grant,
        )

        requests.append(
            map_memory_access_v0(
                reference, context, cost
            )
        )

    result = schedule_causal_services_v0(
        architecture,
        tuple(requests),
        dependencies,
        default_arbitration_policy_v0(),
    )

    assert len(result.completions) == 18
    assert len(plan.references) == 18
    assert result.total_service_units == 18

    completion = {
        item.request_id: item.completion_tick
        for item in result.completions
    }

    batch = next(
        item
        for item in provenance.batches
        if item.timestamp == 4 and item.node_id == "B"
    )

    consume = next(
        reference.intent.request_id
        for reference in plan.references
        if (
            reference.intent.kind is Kind.BATCH_CONSUME
            and reference.intent.node_id == "B"
            and reference.intent.event_time == 4
        )
    )

    assert len(batch.routed_request_ids) == 2

    assert all(
        completion[route_id] < completion[consume]
        for route_id in batch.routed_request_ids
    )

    assert {
        item.event_time for item in result.slices
    } == {2, 4, 5}


@pytest.mark.parametrize(
    "capacity,specs",
    [
        (
            1,
            (
                (0, Activity.EXECUTE, "PE0", 1),
                (1, Activity.LEARN, "PE0", 2),
            ),
        ),
        (
            2,
            (
                (0, Activity.REMODEL, "PE0", 3),
                (1, Activity.EXECUTE, "PE0", 1),
            ),
        ),
        (
            3,
            (
                (0, Activity.EXECUTE, "PE0", 5),
                (1, Activity.OBSERVER, "PE1", 2),
                (2, Activity.ROUTER, "PE1", 3),
            ),
        ),
        (2, ()),
    ],
)
def test_matches_a4_without_dependencies(capacity, specs):
    from spk_architecture.arbitration_v0 import (
        arbitrate_memory_v0,
    )

    requests = tuple(
        request(
            request_id,
            activity,
            pe=pe_id,
            units=units,
        )
        for request_id, activity, pe_id, units in specs
    )

    architecture = machine(capacity)
    policy = default_arbitration_policy_v0()

    reference = arbitrate_memory_v0(
        architecture,
        requests,
        policy,
    )

    dependencies = graph(
        *(
            (item.request_id, ())
            for item in sorted(
                requests,
                key=lambda r: r.request_id,
            )
        )
    )

    causal = schedule_causal_services_v0(
        architecture,
        requests,
        dependencies,
        policy,
    )

    def chronological(slices):
        return tuple(sorted(
            slices,
            key=lambda item: (
                item.service_tick,
                item.target_pe_id,
                item.priority,
                item.principal_id,
                item.request_id,
            ),
        ))

    assert chronological(causal.slices) == chronological(
        reference.slices
    )

    assert set(causal.completions) == set(
        reference.completions
    )

    assert (
        causal.total_service_units
        == reference.total_service_units
    )
    assert (
        causal.total_service_ticks
        == reference.total_service_ticks
    )


def test_join_waits_for_all_predecessors():
    requests = (
        request(0, pe="PE0"),
        request(1, pe="PE1", units=3),
        request(2, pe="PE0"),
    )

    dependencies = graph(
        (0, ()),
        (1, ()),
        (2, (0, 1)),
    )

    result = schedule(requests, dependencies)

    assert tick_of(result, 0) == 1
    assert tick_of(result, 1) == 3
    assert tick_of(result, 2) == 4

    assert result.total_service_ticks == 4


def test_unrelated_pe_workload_does_not_delay_completion():
    single = schedule((
        request(0, pe="PE1"),
    ))

    contended = schedule((
        request(0, pe="PE1"),
        request(1, pe="PE0", units=7),
    ))

    assert tick_of(single, 0) == 1
    assert tick_of(contended, 0) == 1

    assert [
        (item.service_tick, item.granted_units)
        for item in single.slices
        if item.target_pe_id == "PE1"
    ] == [
        (item.service_tick, item.granted_units)
        for item in contended.slices
        if item.target_pe_id == "PE1"
    ]


def test_exact_service_tick_budget_is_accepted():
    requests = (request(0, units=3),)

    result = schedule(
        requests,
        capacity=2,
        max_service_ticks=2,
    )

    assert result.total_service_ticks == 2

    with pytest.raises(CausalServiceLimitV0):
        schedule(
            requests,
            capacity=2,
            max_service_ticks=1,
        )


@pytest.mark.parametrize(
    "capacity,specs",
    [
        (
            1,
            (
                (0, Activity.EXECUTE, "PE0", 1),
                (1, Activity.LEARN, "PE0", 2),
            ),
        ),
        (
            2,
            (
                (0, Activity.REMODEL, "PE0", 3),
                (1, Activity.EXECUTE, "PE0", 1),
            ),
        ),
        (
            3,
            (
                (0, Activity.EXECUTE, "PE0", 5),
                (1, Activity.OBSERVER, "PE1", 2),
                (2, Activity.ROUTER, "PE1", 3),
            ),
        ),
        (2, ()),
    ],
)
def test_matches_a4_without_dependencies(capacity, specs):
    from spk_architecture.arbitration_v0 import (
        arbitrate_memory_v0,
    )

    requests = tuple(
        request(
            request_id,
            activity,
            pe=pe_id,
            units=units,
        )
        for request_id, activity, pe_id, units in specs
    )

    architecture = machine(capacity)
    policy = default_arbitration_policy_v0()

    reference = arbitrate_memory_v0(
        architecture,
        requests,
        policy,
    )

    dependencies = graph(
        *(
            (item.request_id, ())
            for item in sorted(
                requests,
                key=lambda r: r.request_id,
            )
        )
    )

    causal = schedule_causal_services_v0(
        architecture,
        requests,
        dependencies,
        policy,
    )

    def chronological(slices):
        return tuple(sorted(
            slices,
            key=lambda item: (
                item.service_tick,
                item.target_pe_id,
                item.priority,
                item.principal_id,
                item.request_id,
            ),
        ))

    assert chronological(causal.slices) == chronological(
        reference.slices
    )

    assert set(causal.completions) == set(
        reference.completions
    )

    assert (
        causal.total_service_units
        == reference.total_service_units
    )
    assert (
        causal.total_service_ticks
        == reference.total_service_ticks
    )


def test_join_waits_for_all_predecessors():
    requests = (
        request(0, pe="PE0"),
        request(1, pe="PE1", units=3),
        request(2, pe="PE0"),
    )

    dependencies = graph(
        (0, ()),
        (1, ()),
        (2, (0, 1)),
    )

    result = schedule(requests, dependencies)

    assert tick_of(result, 0) == 1
    assert tick_of(result, 1) == 3
    assert tick_of(result, 2) == 4

    assert result.total_service_ticks == 4


def test_unrelated_pe_workload_does_not_delay_completion():
    single = schedule((
        request(0, pe="PE1"),
    ))

    contended = schedule((
        request(0, pe="PE1"),
        request(1, pe="PE0", units=7),
    ))

    assert tick_of(single, 0) == 1
    assert tick_of(contended, 0) == 1

    assert [
        (item.service_tick, item.granted_units)
        for item in single.slices
        if item.target_pe_id == "PE1"
    ] == [
        (item.service_tick, item.granted_units)
        for item in contended.slices
        if item.target_pe_id == "PE1"
    ]


def test_exact_service_tick_budget_is_accepted():
    requests = (request(0, units=3),)

    result = schedule(
        requests,
        capacity=2,
        max_service_ticks=2,
    )

    assert result.total_service_ticks == 2

    with pytest.raises(CausalServiceLimitV0):
        schedule(
            requests,
            capacity=2,
            max_service_ticks=1,
        )
