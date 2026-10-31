"""S3.7b: routed event identities bound to Network v0 observations."""
from dataclasses import replace

import pytest

from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset,
)
from spk_network.model_v0 import NetworkV0, NetworkNodeV0, NetworkEdgeV0
from spk_network.events_v0 import NetworkEventV0
from spk_architecture.profile_v0 import (
    ArchitectureProfileV0, ProcessingElementV0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0, admit_pe_mapping_v0,
)
from spk_simulator.functional_trace_v0 import run_network_observed_v0
from spk_simulator.logical_access_v0 import generate_logical_accesses_v0
from spk_simulator.event_provenance_v0 import reconcile_event_provenance_v0
from spk_simulator.event_storage_v0 import (
    RoutedStorageStateV0, RoutedStorageBlockedV0,
)
from spk_simulator.routing_binding_v0 import (
    BoundRouteV0, RoutedBindingManifestV0, bind_network_routes_v0,
    offer_bound_routed_event_v0, admit_bound_routed_event_v0,
    consume_bound_routed_event_v0,
)


def setup_case(*, output=3, events=3, same_pe=False, initial=None):
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
        pe_id="PE0", program_slots=8, state_slots=2,
        event_slots=events, output_slots=output,
        observation_slots=4, accesses_per_service_tick=2,
    )
    architecture = ArchitectureProfileV0(
        "binding-lab", (pe, replace(pe, pe_id="PE1")),
    )
    placement = admit_pe_mapping_v0(
        network, architecture,
        (NodePlacementV0("A", "PE0"),
         NodePlacementV0("B", "PE0" if same_pe else "PE1")),
    )
    observed = run_network_observed_v0(network, initial)
    plan = generate_logical_accesses_v0(network, observed, placement)
    provenance = reconcile_event_provenance_v0(
        network, observed, placement, plan, initial,
    )
    args = (network, observed, placement, plan, provenance, initial, architecture)
    binding = bind_network_routes_v0(*args)
    state = RoutedStorageStateV0("binding-lab", "E0")
    return args, binding, state


def test_three_routes_bound_to_request_ids():
    _, binding, _ = setup_case()
    assert len(binding.routes) == 3
    assert len({item.route_request_id for item in binding.routes}) == 3
    assert all(item.occurrence.event_id == item.route_request_id
               for item in binding.routes)


def test_parallel_edges_have_distinct_owners():
    _, binding, _ = setup_case()
    a, b, c = binding.routes
    assert a.occurrence == replace(b.occurrence, event_id=a.route_request_id)
    assert a.occurrence.delivery_event_time == 4
    assert c.occurrence.delivery_event_time == 5


def test_route_consumer_binding():
    args, binding, _ = setup_case()
    provenance = args[4]
    consumed = {
        item.route_request_id: (item.target_batch_index, item.consume_request_id)
        for item in binding.routes
    }
    for batch in provenance.batches:
        for route_id in batch.routed_request_ids:
            assert consumed[route_id][0] == batch.batch_index
    a, b, c = binding.routes
    assert a.consume_request_id == b.consume_request_id
    assert c.consume_request_id != a.consume_request_id


def test_source_target_and_logical_delay():
    _, binding, _ = setup_case()
    for item in binding.routes:
        event = item.occurrence
        assert (event.source_node_id, event.source_pe_id, event.source_channel) == (
            "A", "PE0", 7,
        )
        assert (event.target_node_id, event.target_pe_id, event.target_channel) == (
            "B", "PE1", 0,
        )
        assert event.delivery_event_time - event.emission_event_time in (2, 3)
        assert event.epoch_id == "E0"


def test_bound_offer_admit_consume():
    args, binding, state = setup_case()
    architecture = args[-1]
    route = binding.routes[0]
    state = offer_bound_routed_event_v0(architecture, state, binding, route.route_request_id)
    assert state.pending_output == (route.occurrence,)
    state = admit_bound_routed_event_v0(architecture, state, binding, route.route_request_id)
    assert state.admitted_events == (route.occurrence,)
    state = consume_bound_routed_event_v0(
        architecture, state, binding, route.route_request_id,
        consume_request_id=route.consume_request_id,
    )
    assert state.pending_output == () and state.admitted_events == ()
    assert state.consumed_ids == (route.route_request_id,)


def test_output_full_fails_closed():
    args, binding, state = setup_case(output=1)
    arch = args[-1]
    state = offer_bound_routed_event_v0(arch, state, binding, binding.routes[0].route_request_id)
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        offer_bound_routed_event_v0(arch, state, binding, binding.routes[1].route_request_id)
    assert exc.value.domain == "OUTPUT"
    assert len(state.pending_output) == 1


def test_destination_full_preserves_pending():
    args, binding, state = setup_case(events=1)
    arch = args[-1]
    first, second = binding.routes[:2]
    state = offer_bound_routed_event_v0(arch, state, binding, first.route_request_id)
    state = admit_bound_routed_event_v0(arch, state, binding, first.route_request_id)
    state = offer_bound_routed_event_v0(arch, state, binding, second.route_request_id)
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        admit_bound_routed_event_v0(arch, state, binding, second.route_request_id)
    assert exc.value.domain == "EVENT"
    assert state.pending_output == (second.occurrence,)
    assert state.admitted_events == (first.occurrence,)


def test_duplicate_offer_rejected():
    args, binding, state = setup_case()
    arch = args[-1]
    route_id = binding.routes[0].route_request_id
    state = offer_bound_routed_event_v0(arch, state, binding, route_id)
    with pytest.raises(ValueError, match="reused event identity"):
        offer_bound_routed_event_v0(arch, state, binding, route_id)


def test_unknown_route_id_rejected():
    args, binding, state = setup_case()
    with pytest.raises(KeyError):
        offer_bound_routed_event_v0(args[-1], state, binding, 99999)


def test_wrong_consume_request_rejected():
    args, binding, state = setup_case()
    arch = args[-1]
    route = binding.routes[0]
    state = offer_bound_routed_event_v0(arch, state, binding, route.route_request_id)
    state = admit_bound_routed_event_v0(arch, state, binding, route.route_request_id)
    with pytest.raises(ValueError, match="wrong consuming batch request"):
        consume_bound_routed_event_v0(
            arch, state, binding, route.route_request_id,
            consume_request_id=route.consume_request_id + 1,
        )
    assert len(state.admitted_events) == 1


def test_epoch_mismatch_rejected():
    args, binding, state = setup_case()
    with pytest.raises(ValueError, match="architecture/epoch mismatch"):
        offer_bound_routed_event_v0(
            args[-1], replace(state, epoch_id="Ewrong"), binding,
            binding.routes[0].route_request_id,
        )


def test_profile_mismatch_rejected():
    args, binding, state = setup_case()
    with pytest.raises(ValueError, match="architecture/epoch mismatch"):
        offer_bound_routed_event_v0(
            args[-1], replace(state, profile_id="other"), binding,
            binding.routes[0].route_request_id,
        )


def test_tampered_route_observation_rejected():
    args, _, _ = setup_case()
    network, observed, placement, plan, provenance, initial, arch = args
    bad_route = replace(observed.routes[0], target_channel=4)
    bad_observed = replace(observed, routes=(bad_route,) + observed.routes[1:])
    with pytest.raises(ValueError):
        bind_network_routes_v0(
            network, bad_observed, placement, plan, provenance, initial, arch,
        )


def test_tampered_logical_access_plan_rejected():
    args, _, _ = setup_case()
    network, observed, placement, plan, provenance, initial, arch = args
    with pytest.raises(ValueError):
        bind_network_routes_v0(
            network, observed, placement,
            replace(plan, references=plan.references[:-1]),
            provenance, initial, arch,
        )


def test_tampered_provenance_rejected():
    args, _, _ = setup_case()
    network, observed, placement, plan, provenance, initial, arch = args
    with pytest.raises(ValueError, match="provenance mismatch"):
        bind_network_routes_v0(
            network, observed, placement, plan,
            replace(provenance, routed_count=99), initial, arch,
        )


def test_wrong_external_stimuli_rejected():
    args, _, _ = setup_case()
    network, observed, placement, plan, provenance, _, arch = args
    with pytest.raises(ValueError):
        bind_network_routes_v0(
            network, observed, placement, plan, provenance, (), arch,
        )


def test_wrong_machine_profile_rejected():
    args, _, _ = setup_case()
    network, observed, placement, plan, provenance, initial, arch = args
    with pytest.raises(ValueError, match="architecture/placement profile mismatch"):
        bind_network_routes_v0(
            network, observed, placement, plan, provenance, initial,
            replace(arch, profile_id="other"),
        )


def test_forged_pending_occurrence_rejected():
    args, binding, state = setup_case()
    arch = args[-1]
    route = binding.routes[0]
    bad = replace(route.occurrence, target_channel=5)
    state = replace(state, pending_output=(bad,))
    with pytest.raises(ValueError, match="differs from binding"):
        admit_bound_routed_event_v0(arch, state, binding, route.route_request_id)


def test_forged_admitted_occurrence_rejected():
    args, binding, state = setup_case()
    arch = args[-1]
    route = binding.routes[0]
    bad = replace(route.occurrence, target_channel=5)
    state = replace(state, admitted_events=(bad,))
    with pytest.raises(ValueError, match="differs from binding"):
        consume_bound_routed_event_v0(
            arch, state, binding, route.route_request_id,
            consume_request_id=route.consume_request_id,
        )


def test_route_dataclass_rejects_mismatched_event_id():
    _, manifest, _ = setup_case()
    first = manifest.routes[0]
    with pytest.raises(ValueError, match="route/event ID mismatch"):
        replace(first, occurrence=replace(first.occurrence, event_id=1000))


def test_manifest_rejects_duplicate_routes():
    _, manifest, _ = setup_case()
    with pytest.raises(ValueError, match="noncanonical"):
        replace(manifest, routes=(manifest.routes[0], manifest.routes[0]))


def test_empty_execution_has_no_routed_occurrences():
    args, manifest, state = setup_case(initial=())
    assert manifest.routes == ()
    assert state.pending_output == ()
    assert state.admitted_events == ()


def test_same_pe_routing_is_not_omitted():
    _, manifest, _ = setup_case(same_pe=True)
    assert len(manifest.routes) == 3
    assert all(route.occurrence.source_pe_id == route.occurrence.target_pe_id == "PE0"
               for route in manifest.routes)


def test_replay_is_deterministic():
    args, manifest, _ = setup_case()
    assert bind_network_routes_v0(*args) == manifest


def test_id_reuse_after_consumption_fails():
    args, manifest, state = setup_case()
    arch = args[-1]
    route = manifest.routes[0]
    rid = route.route_request_id
    state = offer_bound_routed_event_v0(arch, state, manifest, rid)
    state = admit_bound_routed_event_v0(arch, state, manifest, rid)
    state = consume_bound_routed_event_v0(
        arch, state, manifest, rid,
        consume_request_id=route.consume_request_id,
    )
    with pytest.raises(ValueError, match="reused event identity"):
        offer_bound_routed_event_v0(arch, state, manifest, rid)


def test_unbound_stored_occupant_rejected():
    args, binding, state = setup_case()
    arch = args[-1]
    forged = replace(binding.routes[0].occurrence, event_id=555)
    state = replace(state, admitted_events=(forged,))
    with pytest.raises(ValueError, match="unbound stored occurrence"):
        offer_bound_routed_event_v0(
            arch, state, binding, binding.routes[1].route_request_id,
        )


def test_unbound_consumed_identity_rejected():
    args, binding, state = setup_case()
    state = replace(state, consumed_ids=(555,))
    with pytest.raises(ValueError, match="unbound consumed identity"):
        offer_bound_routed_event_v0(
            args[-1], state, binding, binding.routes[0].route_request_id,
        )
