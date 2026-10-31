from dataclasses import replace

import pytest

from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig,
    CoreEmit, CoreProgram, CoreReset,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import (
    NetworkEdgeV0, NetworkNodeV0, NetworkV0,
)
from spk_network.runtime_v0 import run_network_v0

from spk_architecture.profile_v0 import (
    ProcessingElementV0,
    ArchitectureProfileV0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0,
    PEAdmissionRejectedV0,
    admit_pe_mapping_v0,
)


def make_network():
    config = CoreConfig(
        state_bits=8,
        fractional_bits=0,
    )
    program = CoreProgram((
        CoreAcc(weight=1, channel=0),
        CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7),
        CoreReset(value_raw=0),
    ))

    return NetworkV0(
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


def make_architecture(
    program_slots=4,
    state_slots=1,
):
    pe0 = ProcessingElementV0(
        pe_id="PE0",
        program_slots=program_slots,
        state_slots=state_slots,
        event_slots=8,
        output_slots=8,
        observation_slots=4,
        accesses_per_service_tick=2,
    )

    return ArchitectureProfileV0(
        profile_id="spk-test-machine",
        pes=(
            pe0,
            replace(pe0, pe_id="PE1"),
        ),
    )


PLACEMENTS = (
    NodePlacementV0("A", "PE0"),
    NodePlacementV0("B", "PE1"),
)


def test_successful_mapping():
    manifest = admit_pe_mapping_v0(
        make_network(),
        make_architecture(),
        PLACEMENTS,
    )

    assert manifest.node_count == 2
    assert manifest.pe_count == 2
    assert manifest.total_program_slots == 8
    assert manifest.total_state_slots == 2
    assert manifest.cross_pe_edges == 3

    assert manifest.pe_usage[0].program_used == 4
    assert manifest.pe_usage[1].state_used == 1


def test_same_network_rejected_on_smaller_machine():
    network = make_network()

    accepted = admit_pe_mapping_v0(
        network,
        make_architecture(program_slots=4),
        PLACEMENTS,
    )
    assert accepted.node_count == 2

    with pytest.raises(PEAdmissionRejectedV0) as error:
        admit_pe_mapping_v0(
            network,
            make_architecture(program_slots=3),
            PLACEMENTS,
        )

    assert error.value.code == "ADMISSION_REJECTED"
    assert error.value.metric == "program_slots"


def test_state_capacity_rejected():
    with pytest.raises(PEAdmissionRejectedV0) as error:
        admit_pe_mapping_v0(
            make_network(),
            make_architecture(state_slots=0),
            PLACEMENTS,
        )

    assert error.value.metric == "state_slots"


def test_programs_not_implicitly_shared():
    # Both neurons are placed on PE0.
    placement = (
        NodePlacementV0("A", "PE0"),
        NodePlacementV0("B", "PE0"),
    )

    with pytest.raises(PEAdmissionRejectedV0) as error:
        admit_pe_mapping_v0(
            make_network(),
            make_architecture(
                program_slots=4,
                state_slots=2,
            ),
            placement,
        )

    # Two identical 4-instruction programs need
    # eight slots under the current conservative rule.
    assert error.value.required == 8


def test_parallel_cross_pe_edges_preserved():
    manifest = admit_pe_mapping_v0(
        make_network(),
        make_architecture(),
        PLACEMENTS,
    )

    assert manifest.cross_pe_edges == 3


def test_placement_order_is_irrelevant():
    network = make_network()
    architecture = make_architecture()

    first = admit_pe_mapping_v0(
        network, architecture, PLACEMENTS
    )

    second = admit_pe_mapping_v0(
        network, architecture, PLACEMENTS[::-1]
    )

    assert first == second


@pytest.mark.parametrize("placements", [
    (NodePlacementV0("A", "PE0"),),

    (
        NodePlacementV0("A", "PE0"),
        NodePlacementV0("A", "PE1"),
    ),

    (
        NodePlacementV0("A", "PE0"),
        NodePlacementV0("B", "UNKNOWN"),
    ),

    (
        NodePlacementV0("A", "PE0"),
        NodePlacementV0("MISSING", "PE1"),
    ),
])
def test_invalid_placements_rejected(placements):
    with pytest.raises(ValueError):
        admit_pe_mapping_v0(
            make_network(),
            make_architecture(),
            placements,
        )


@pytest.mark.parametrize("node_id,pe_id", [
    ("", "PE0"),
    ("A", ""),
])
def test_invalid_placement_ids(node_id, pe_id):
    with pytest.raises(ValueError):
        NodePlacementV0(node_id, pe_id)


def test_mapping_does_not_change_execution():
    network = make_network()
    events = (NetworkEventV0(2, "A", 0),)

    before = run_network_v0(network, events)

    admit_pe_mapping_v0(
        network,
        make_architecture(),
        PLACEMENTS,
    )

    after = run_network_v0(network, events)

    assert before == after
