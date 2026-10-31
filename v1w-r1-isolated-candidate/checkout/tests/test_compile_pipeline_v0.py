"""C1 compiler integration tests: use the actual frozen SPK v0 modules."""

from dataclasses import FrozenInstanceError, replace
import json

import pytest

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0, admit_pe_mapping_v0
from spk_compiler.resource_admission_v0 import ResourceProfileV0, admit_network_v0
from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkEdgeV0, NetworkNodeV0, NetworkV0
from spk_network.runtime_v0 import run_network_v0


@pytest.fixture
def inputs():
    config = CoreConfig(state_bits=8, fractional_bits=0)
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
        ),
    )
    initial = (NetworkEventV0(2, "A", 0), NetworkEventV0(2, "A", 0))
    pe = ProcessingElementV0(
        pe_id="PE0", program_slots=8, state_slots=2, event_slots=8,
        output_slots=8, observation_slots=8, accesses_per_service_tick=2,
    )
    machine = ArchitectureProfileV0(
        "compiler-c1-test", (pe, replace(pe, pe_id="PE1")),
    )
    placements = (NodePlacementV0("B", "PE1"), NodePlacementV0("A", "PE0"))
    return (
        dumps_network_ir_v0(network),
        network, initial, ResourceProfileV0(), machine, placements,
    )


def compile_case(inputs, **changes):
    ir, _, events, resources, machine, placements = inputs
    args = dict(network_ir_json=ir, initial_events=events,
                resource_profile=resources, architecture=machine,
                placements=placements)
    args.update(changes)
    return compile_network_ir_v0(**args)


def test_pipeline_preserves_network_and_events(inputs):
    compiled = compile_case(inputs)
    assert compiled.network == inputs[1]
    assert compiled.initial_events == inputs[2]
    assert len(compiled.initial_events) == 2
    assert len(compiled.network.edges) == 2


def test_pipeline_matches_independent_admission(inputs):
    result = compile_case(inputs)
    _, network, initial, resources, machine, placements = inputs
    assert result.resource_admission == admit_network_v0(network, initial, resources)
    assert result.pe_admission == admit_pe_mapping_v0(network, machine, placements)


def test_pipeline_does_not_change_functional_execution(inputs):
    compiled = compile_case(inputs)
    assert run_network_v0(compiled.network, compiled.initial_events) == run_network_v0(
        inputs[1], inputs[2]
    )


def test_compilation_is_deterministic(inputs):
    assert compile_case(inputs) == compile_case(inputs)


def test_input_whitespace_is_not_compilation_state(inputs):
    formatted = json.dumps(json.loads(inputs[0]), indent=2, ensure_ascii=False)
    assert compile_case(inputs, network_ir_json=formatted) == compile_case(inputs)


def test_placement_order_is_canonical(inputs):
    reordered = compile_case(inputs, placements=inputs[5][::-1])
    canonical = compile_case(inputs)
    assert reordered == canonical
    assert tuple(p.node_id for p in canonical.placements) == ("A", "B")


def test_empty_initial_events_supported(inputs):
    compiled = compile_case(inputs, initial_events=())
    assert compiled.initial_events == ()


def test_invalid_json_rejected(inputs):
    with pytest.raises(ValueError):
        compile_case(inputs, network_ir_json="{not-json")


def test_incomplete_mapping_rejected(inputs):
    with pytest.raises(ValueError):
        compile_case(inputs, placements=(NodePlacementV0("A", "PE0"),))


def test_logical_resource_limit_rejected(inputs):
    restrictive = replace(inputs[3], max_nodes=1)
    with pytest.raises(ValueError):
        compile_case(inputs, resource_profile=restrictive)


def test_pe_resource_limit_rejected(inputs):
    pe = inputs[4].pes[0]
    constrained = ArchitectureProfileV0(
        "too-small", (replace(pe, program_slots=3), replace(pe, pe_id="PE1", program_slots=3)),
    )
    with pytest.raises(ValueError):
        compile_case(inputs, architecture=constrained)


@pytest.mark.parametrize("keyword,value", [
    ("network_ir_json", None),
    ("initial_events", []),
    ("initial_events", ("not-an-event",)),
    ("resource_profile", None),
    ("architecture", None),
    ("placements", [NodePlacementV0("A", "PE0")]),
])
def test_invalid_api_input_rejected(inputs, keyword, value):
    with pytest.raises(TypeError):
        compile_case(inputs, **{keyword: value})


def test_compiled_result_immutable(inputs):
    compiled = compile_case(inputs)
    with pytest.raises(FrozenInstanceError):
        compiled.network = None
