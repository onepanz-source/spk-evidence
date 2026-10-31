"""C2 tests use C1 and Network IR but do not import fixtures from other tests."""

from dataclasses import replace
import json

import pytest

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import (
    dumps_compilation_manifest_v0,
    loads_compilation_manifest_v0,
)
from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.resource_admission_v0 import ResourceProfileV0
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
        nodes=(NetworkNodeV0("A", config, program),
               NetworkNodeV0("B", config, program)),
        edges=(NetworkEdgeV0("A", 7, "B", 0, 2),
               NetworkEdgeV0("A", 7, "B", 0, 2)),
    )
    initial = (NetworkEventV0(2, "A", 0), NetworkEventV0(2, "A", 0))
    pe = ProcessingElementV0(
        pe_id="PE0", program_slots=8, state_slots=2, event_slots=8,
        output_slots=8, observation_slots=8, accesses_per_service_tick=2,
    )
    architecture = ArchitectureProfileV0(
        "compiler-c2-test", (pe, replace(pe, pe_id="PE1")),
    )
    placements = (NodePlacementV0("B", "PE1"), NodePlacementV0("A", "PE0"))
    return network, initial, ResourceProfileV0(), architecture, placements


def compile_case(inputs, **changes):
    network, initial, resources, architecture, placements = inputs
    kwargs = dict(
        network_ir_json=dumps_network_ir_v0(network),
        initial_events=initial,
        resource_profile=resources,
        architecture=architecture,
        placements=placements,
    )
    kwargs.update(changes)
    return compile_network_ir_v0(**kwargs)


def make_doc(inputs):
    return dumps_compilation_manifest_v0(compile_case(inputs))


def tamper_rehash(doc, fn):
    # TEST ONLY: simulates a malicious party who can recompute the checksum.
    import spk_compiler.compilation_manifest_v0 as module
    data = json.loads(doc)
    fn(data["payload"])
    data["payload_sha256"] = module._digest(data["payload"])
    return json.dumps(data)


def test_roundtrip_reconstructs_compilation(inputs):
    assert loads_compilation_manifest_v0(make_doc(inputs)) == compile_case(inputs)


def test_unchanged_network_functional_result(inputs):
    replayed = loads_compilation_manifest_v0(make_doc(inputs))
    original = compile_case(inputs)
    assert run_network_v0(replayed.network, replayed.initial_events) == run_network_v0(
        original.network, original.initial_events
    )


def test_canonical_serialization_repeated(inputs):
    assert make_doc(inputs) == make_doc(inputs)


def test_canonical_json_no_insignificant_space(inputs):
    doc = make_doc(inputs)
    assert doc == json.dumps(json.loads(doc), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def test_placement_order_independent(inputs):
    first = compile_case(inputs)
    second = compile_case(inputs, placements=inputs[4][::-1])
    assert dumps_compilation_manifest_v0(first) == dumps_compilation_manifest_v0(second)


def test_ir_whitespace_independent(inputs):
    ir = dumps_network_ir_v0(inputs[0])
    other = compile_case(inputs, network_ir_json=json.dumps(json.loads(ir), indent=2))
    assert dumps_compilation_manifest_v0(other) == make_doc(inputs)


def test_event_multiplicity_is_preserved(inputs):
    replayed = loads_compilation_manifest_v0(make_doc(inputs))
    assert replayed.initial_events == inputs[1]
    assert len(replayed.initial_events) == 2
    assert len(replayed.network.edges) == 2


def test_profiles_and_admissions_preserved(inputs):
    original = compile_case(inputs)
    replayed = loads_compilation_manifest_v0(make_doc(inputs))
    assert replayed.resource_profile == original.resource_profile
    assert replayed.architecture == original.architecture
    assert replayed.resource_admission == original.resource_admission
    assert replayed.pe_admission == original.pe_admission


def test_checksum_mismatch_rejected(inputs):
    doc = json.loads(make_doc(inputs))
    doc["payload"]["initial_events"] = []
    with pytest.raises(ValueError, match="checksum"):
        loads_compilation_manifest_v0(json.dumps(doc))


def test_recomputed_checksum_cannot_forge_admission(inputs):
    doc = tamper_rehash(
        make_doc(inputs),
        lambda payload: payload["resource_admission"].update(node_count=99),
    )
    with pytest.raises(ValueError, match="conflicts"):
        loads_compilation_manifest_v0(doc)


def test_recomputed_checksum_cannot_bypass_resource_limits(inputs):
    doc = tamper_rehash(
        make_doc(inputs),
        lambda payload: payload["resource_profile"].update(max_nodes=1),
    )
    with pytest.raises(ValueError):
        loads_compilation_manifest_v0(doc)


def test_unknown_payload_field_rejected(inputs):
    doc = tamper_rehash(make_doc(inputs), lambda payload: payload.update(extraneous=1))
    with pytest.raises(ValueError, match="payload fields"):
        loads_compilation_manifest_v0(doc)


def test_unknown_top_level_field_rejected(inputs):
    doc = json.loads(make_doc(inputs))
    doc["unknown"] = "invalid"
    with pytest.raises(ValueError, match="manifest fields"):
        loads_compilation_manifest_v0(json.dumps(doc))


def test_duplicate_json_keys_rejected(inputs):
    doc = make_doc(inputs)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        loads_compilation_manifest_v0(doc[:-1] + ',"schema":"other"}')


def test_wrong_version_rejected(inputs):
    doc = json.loads(make_doc(inputs))
    doc["version"] = "1"
    with pytest.raises(ValueError, match="schema/version"):
        loads_compilation_manifest_v0(json.dumps(doc))


def test_nonfinite_json_constant_rejected(inputs):
    doc = make_doc(inputs)
    with pytest.raises(ValueError, match="invalid JSON constant"):
        loads_compilation_manifest_v0(doc[:-1] + ',"extra":NaN}')


def test_unknown_pe_placement_rejected_even_with_new_hash(inputs):
    def mutate(payload):
        payload["placements"][0]["pe_id"] = "PE-does-not-exist"
    with pytest.raises(ValueError):
        loads_compilation_manifest_v0(tamper_rehash(make_doc(inputs), mutate))


def test_empty_input_events_roundtrip(inputs):
    compiled = compile_case(inputs, initial_events=())
    assert loads_compilation_manifest_v0(dumps_compilation_manifest_v0(compiled)) == compiled


def test_invalid_text_input_rejected():
    with pytest.raises(TypeError):
        loads_compilation_manifest_v0(None)


def test_invalid_compiled_input_rejected():
    with pytest.raises(TypeError):
        dumps_compilation_manifest_v0(None)


def test_manually_forged_compiled_result_rejected(inputs):
    original = compile_case(inputs)
    forged = replace(original, placements=(NodePlacementV0("A", "PE1"), NodePlacementV0("B", "PE0")))
    with pytest.raises(ValueError, match="differs"):
        dumps_compilation_manifest_v0(forged)


def test_manifest_accepts_pretty_json(inputs):
    doc = json.dumps(json.loads(make_doc(inputs)), indent=2)
    assert loads_compilation_manifest_v0(doc) == compile_case(inputs)
