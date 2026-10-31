from dataclasses import FrozenInstanceError, replace

import pytest

from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig,
    CoreEmit, CoreProgram, CoreReset,
)
from spk_network.model_v0 import (
    NetworkV0, NetworkNodeV0, NetworkEdgeV0,
)
from spk_network.events_v0 import NetworkEventV0
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
from spk_simulator.access_dependencies_v0 import (
    AccessDependencyV0,
    AccessDependencyGraphV0,
    build_access_dependencies_v0,
    topological_request_ids_v0,
)


def scenario(initial=None):
    if initial is None:
        initial = (NetworkEventV0(2, "A", 0),)

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
        network, initial
    )

    plan = generate_logical_accesses_v0(
        network, observed, placement
    )

    provenance = reconcile_event_provenance_v0(
        network, observed, placement,
        plan, initial,
    )

    return (
        network, observed, placement,
        plan, provenance, initial,
    )


def build(data):
    return build_access_dependencies_v0(*data)


def deps(data):
    return {
        item.request_id: item.predecessor_ids
        for item in build(data).dependencies
    }


def test_all_accesses_accounted():
    data = scenario()
    graph = build(data)
    assert len(graph.dependencies) == 18
    assert [d.request_id for d in graph.dependencies] == list(range(18))


def test_emission_depends_on_batch_inputs():
    d = deps(scenario())
    assert d[4] == (0, 1, 2)


def test_routes_depend_on_emission():
    d = deps(scenario())
    assert d[5] == (4,)
    assert d[6] == (4,)
    assert d[7] == (4,)


def test_parallel_routes_required_for_batch():
    d = deps(scenario())
    assert d[10] == (5, 6)


def test_later_batch_waits_for_remaining_route():
    d = deps(scenario())
    assert d[15] == (7,)


def test_state_load_waits_for_previous_commit():
    d = deps(scenario())
    assert d[14] == (11,)


def test_commit_waits_for_batch_requirements():
    d = deps(scenario())
    assert d[11] == (8, 9, 10)


def test_independent_prefetch_has_no_global_barrier():
    d = deps(scenario())
    assert d[8] == ()
    assert d[9] == ()


def test_initial_spike_has_no_route_dependency():
    d = deps(scenario())
    assert d[2] == ()


def test_initial_and_routed_same_batch():
    initial = (
        NetworkEventV0(2, "A", 0),
        NetworkEventV0(4, "B", 0),
    )
    data = scenario(initial)
    graph = build(data)
    _, _, _, plan, provenance, _ = data

    batch = next(
        item for item in provenance.batches
        if item.timestamp == 4 and item.node_id == "B"
    )
    consume = next(
        ref.intent.request_id
        for ref in plan.references
        if ref.intent.node_id == "B"
        and ref.intent.event_time == 4
        and ref.intent.kind.value == "BATCH_CONSUME"
    )

    assert batch.initial_count == 1
    assert batch.routed_count == 2
    assert dict(
        (d.request_id, d.predecessor_ids)
        for d in graph.dependencies
    )[consume] == tuple(sorted(batch.routed_request_ids))


def test_empty_execution():
    graph = build(scenario(()))
    assert graph.dependencies == ()
    assert topological_request_ids_v0(graph) == ()


def test_tampered_provenance_rejected():
    data = scenario()
    bad = replace(data[4], initial_count=99)

    with pytest.raises(ValueError):
        build(data[:4] + (bad,) + data[5:])


def test_tampered_plan_rejected():
    data = scenario()
    bad = replace(
        data[3],
        references=data[3].references[:-1],
    )

    with pytest.raises(ValueError):
        build(data[:3] + (bad,) + data[4:])


def test_missing_initial_event_rejected():
    data = scenario()

    with pytest.raises(ValueError):
        build(data[:-1] + ((),))


def test_unknown_predecessor_rejected():
    with pytest.raises(ValueError):
        AccessDependencyGraphV0((
            AccessDependencyV0(0, (99,)),
        ))


def test_cycle_rejected():
    with pytest.raises(ValueError):
        AccessDependencyGraphV0((
            AccessDependencyV0(0, (1,)),
            AccessDependencyV0(1, (0,)),
        ))


def test_duplicate_request_ids_rejected():
    with pytest.raises(ValueError):
        AccessDependencyGraphV0((
            AccessDependencyV0(0, ()),
            AccessDependencyV0(0, ()),
        ))


def test_duplicate_predecessors_rejected():
    with pytest.raises(ValueError):
        AccessDependencyV0(2, (0, 0))


def test_boolean_request_id_rejected():
    with pytest.raises(ValueError):
        AccessDependencyV0(True, ())


def test_deterministic_topological_order():
    graph = build(scenario())
    order = topological_request_ids_v0(graph)
    position = {
        request_id: index
        for index, request_id in enumerate(order)
    }

    assert len(order) == 18

    for item in graph.dependencies:
        for predecessor in item.predecessor_ids:
            assert position[predecessor] < position[item.request_id]

    assert order == topological_request_ids_v0(graph)


def test_graph_is_immutable():
    graph = build(scenario())

    with pytest.raises(FrozenInstanceError):
        graph.dependencies = ()
