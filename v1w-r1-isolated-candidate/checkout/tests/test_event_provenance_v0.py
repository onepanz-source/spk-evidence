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
from spk_architecture.access_v0 import AccessIntentKindV0
from spk_architecture.profile_v0 import (
    ProcessingElementV0, ArchitectureProfileV0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0, admit_pe_mapping_v0,
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


@pytest.fixture
def setup():
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

    return network, placement


def run(setup, initial_events):
    network, placement = setup

    observed = run_network_observed_v0(
        network, initial_events
    )

    plan = generate_logical_accesses_v0(
        network, observed, placement
    )

    return observed, plan


def reconcile(setup, initial_events):
    network, placement = setup
    observed, plan = run(setup, initial_events)

    return reconcile_event_provenance_v0(
        network, observed, placement,
        plan, initial_events,
    )


def test_event_conservation(setup):
    initial = (NetworkEventV0(2, "A", 0),)
    result = reconcile(setup, initial)

    assert result.initial_count == 1
    assert result.routed_count == 3
    assert result.processed_count == 4

    assert [
        (b.timestamp, b.node_id,
         b.initial_count, b.routed_count)
        for b in result.batches
    ] == [
        (2, "A", 1, 0),
        (4, "B", 0, 2),
        (5, "B", 0, 1),
    ]


def test_routed_dependencies_preserve_multiplicity(setup):
    initial = (NetworkEventV0(2, "A", 0),)

    observed, plan = run(setup, initial)
    network, placement = setup

    result = reconcile_event_provenance_v0(
        network, observed, placement,
        plan, initial,
    )

    route_ids = {
        ref.intent.request_id
        for ref in plan.references
        if ref.intent.kind
        is AccessIntentKindV0.ROUTE_ENQUEUE
    }

    consumed_route_ids = [
        request_id
        for batch in result.batches
        for request_id in batch.routed_request_ids
    ]

    assert len(consumed_route_ids) == 3
    assert len(set(consumed_route_ids)) == 3
    assert set(consumed_route_ids) == route_ids


def test_missing_initial_event_rejected(setup):
    initial = (NetworkEventV0(2, "A", 0),)
    observed, plan = run(setup, initial)
    network, placement = setup

    with pytest.raises(ValueError):
        reconcile_event_provenance_v0(
            network, observed, placement, plan, ()
        )


def test_extra_initial_event_rejected(setup):
    initial = (NetworkEventV0(2, "A", 0),)
    observed, plan = run(setup, initial)
    network, placement = setup

    with pytest.raises(ValueError):
        reconcile_event_provenance_v0(
            network, observed, placement, plan,
            initial + initial,
        )


def test_tampered_access_plan_rejected(setup):
    initial = (NetworkEventV0(2, "A", 0),)
    observed, plan = run(setup, initial)
    network, placement = setup

    tampered = replace(
        plan,
        references=plan.references[:-1],
    )

    with pytest.raises(ValueError):
        reconcile_event_provenance_v0(
            network, observed, placement,
            tampered, initial,
        )


def test_empty_execution(setup):
    result = reconcile(setup, ())

    assert result.batches == ()
    assert result.initial_count == 0
    assert result.routed_count == 0
    assert result.processed_count == 0


def test_initial_and_routed_event_same_batch(setup):
    initial = (
        NetworkEventV0(2, "A", 0),
        NetworkEventV0(4, "B", 0),
    )

    result = reconcile(setup, initial)

    batch = next(
        item for item in result.batches
        if item.timestamp == 4 and item.node_id == "B"
    )

    assert len(batch.channels) == 3
    assert batch.initial_count == 1
    assert batch.routed_count == 2
    assert result.processed_count == 5


def test_invalid_initial_collection_rejected(setup):
    network, placement = setup
    observed, plan = run(setup, ())

    with pytest.raises(TypeError):
        reconcile_event_provenance_v0(
            network, observed, placement, plan, []
        )


def test_reconciliation_is_deterministic(setup):
    initial = (NetworkEventV0(2, "A", 0),)

    assert reconcile(
        setup, initial
    ) == reconcile(setup, initial)
