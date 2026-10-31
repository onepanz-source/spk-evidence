from collections import Counter
from dataclasses import replace

import pytest

from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig,
    CoreEmit, CoreProgram, CoreReset,
)
from spk_network.model_v0 import (
    NetworkV0, NetworkNodeV0, NetworkEdgeV0,
)
from spk_network.events_v0 import NetworkEventV0

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
)
from spk_architecture.profile_v0 import (
    ProcessingElementV0,
    ArchitectureProfileV0,
)
from spk_architecture.access_authorization_v0 import (
    AccessGrantV0,
    AuthorizationPolicyV0,
    AuthorizationContextV0,
    authorize_access_v0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0,
    admit_pe_mapping_v0,
)
from spk_simulator.functional_trace_v0 import (
    run_network_observed_v0,
)
from spk_simulator.logical_access_v0 import (
    generate_logical_accesses_v0,
)


@pytest.fixture
def scenario():
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

    pe = ProcessingElementV0(
        pe_id="PE0",
        program_slots=4,
        state_slots=1,
        event_slots=8,
        output_slots=8,
        observation_slots=4,
        accesses_per_service_tick=2,
    )

    architecture = ArchitectureProfileV0(
        "machine-v0",
        (pe, replace(pe, pe_id="PE1")),
    )

    placement = admit_pe_mapping_v0(
        network,
        architecture,
        (
            NodePlacementV0("A", "PE0"),
            NodePlacementV0("B", "PE1"),
        ),
    )

    observed = run_network_observed_v0(
        network,
        (NetworkEventV0(2, "A", 0),),
    )

    return network, placement, observed


def make_plan(scenario):
    network, placement, observed = scenario

    return generate_logical_accesses_v0(
        network=network,
        observed=observed,
        placement=placement,
    )


def test_access_counts(scenario):
    plan = make_plan(scenario)

    counts = Counter(
        ref.intent.kind for ref in plan.references
    )

    assert len(plan.references) == 18
    assert counts[Kind.PROGRAM_REFERENCE] == 3
    assert counts[Kind.STATE_LOAD] == 3
    assert counts[Kind.BATCH_CONSUME] == 3
    assert counts[Kind.STATE_COMMIT] == 3
    assert counts[Kind.EMISSION_RECORD] == 3
    assert counts[Kind.ROUTE_ENQUEUE] == 3


def test_batch_multiplicity(scenario):
    plan = make_plan(scenario)

    batches = [
        ref.intent
        for ref in plan.references
        if ref.intent.kind is Kind.BATCH_CONSUME
    ]

    assert [
        (item.event_time, item.node_id, item.quantity)
        for item in batches
    ] == [
        (2, "A", 1),
        (4, "B", 2),
        (5, "B", 1),
    ]


def test_routing_multiplicity(scenario):
    plan = make_plan(scenario)

    routes = [
        ref for ref in plan.references
        if ref.intent.kind is Kind.ROUTE_ENQUEUE
    ]

    assert len(routes) == 3
    assert all(
        ref.intent.activity is Activity.ROUTER
        for ref in routes
    )
    assert all(
        ref.intent.pe_id == "PE0"
        for ref in routes
    )
    assert all(
        ref.intent.event_time == 2
        for ref in routes
    )
    assert all(
        ref.target_id == "events:B"
        for ref in routes
    )


def test_catalog_preserves_placement(scenario):
    plan = make_plan(scenario)

    assert plan.catalog.get("state:A").pe_id == "PE0"
    assert plan.catalog.get("state:B").pe_id == "PE1"
    assert (
        plan.catalog.get("events:B").owner_node_id
        == "B"
    )


def test_authorization_integration(scenario):
    _, placement, _ = scenario
    plan = make_plan(scenario)
    policy = AuthorizationPolicyV0("E0")

    state_reference = next(
        ref for ref in plan.references
        if (
            ref.intent.kind is Kind.STATE_LOAD
            and ref.intent.node_id == "A"
        )
    )

    execute_context = AuthorizationContextV0(
        plan.catalog,
        placement,
        policy,
        AccessGrantV0(
            "executor-A",
            Activity.EXECUTE,
            "PE0",
            node_id="A",
        ),
    )

    assert authorize_access_v0(
        state_reference, execute_context
    ).allowed

    route_reference = next(
        ref for ref in plan.references
        if ref.intent.kind is Kind.ROUTE_ENQUEUE
    )

    router_context = AuthorizationContextV0(
        plan.catalog,
        placement,
        policy,
        AccessGrantV0(
            "router-PE0",
            Activity.ROUTER,
            "PE0",
        ),
    )

    assert authorize_access_v0(
        route_reference, router_context
    ).allowed


def test_generation_is_deterministic(scenario):
    assert make_plan(scenario) == make_plan(scenario)


def test_missing_route_rejected(scenario):
    network, placement, observed = scenario

    corrupted = replace(
        observed,
        routes=observed.routes[:-1],
    )

    with pytest.raises(ValueError):
        generate_logical_accesses_v0(
            network, corrupted, placement
        )


def test_missing_batch_rejected(scenario):
    network, placement, observed = scenario

    corrupted = replace(
        observed,
        batches=observed.batches[:-1],
    )

    with pytest.raises(ValueError):
        generate_logical_accesses_v0(
            network, corrupted, placement
        )


def test_empty_execution(scenario):
    network, placement, _ = scenario

    observed = run_network_observed_v0(network, ())
    plan = generate_logical_accesses_v0(
        network, observed, placement
    )

    assert plan.references == ()
    assert len(plan.catalog.targets) == 8


def test_incomplete_placement_rejected(scenario):
    network, placement, observed = scenario

    invalid = replace(
        placement,
        pe_usage=placement.pe_usage[:1],
    )

    with pytest.raises(ValueError):
        generate_logical_accesses_v0(
            network, observed, invalid
        )
