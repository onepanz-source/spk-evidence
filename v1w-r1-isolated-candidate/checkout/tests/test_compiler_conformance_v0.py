"""C3: independent observable conformance of the SPK v0 compiler.

Separate fixtures, canonical JSON oracle, hash oracle and subprocess seeds.
No imports from C1/C2 test modules or from C2 private helpers.
"""

from dataclasses import asdict, FrozenInstanceError, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import (
    dumps_compilation_manifest_v0, loads_compilation_manifest_v0,
)
from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0, admit_pe_mapping_v0
from spk_compiler.resource_admission_v0 import ResourceProfileV0, admit_network_v0
from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkEdgeV0, NetworkNodeV0, NetworkV0
from spk_network.runtime_v0 import run_network_v0

SCHEMA = "spk-compilation-manifest/v0"


def canonical(value):
    """A stdlib oracle independent of the production serializer."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def manual_digest(payload):
    return sha256((SCHEMA + "\n" + canonical(payload)).encode("utf-8")).hexdigest()


@pytest.fixture
def scenario():
    config = CoreConfig(state_bits=8, fractional_bits=0)
    program = CoreProgram((
        CoreAcc(weight=1, channel=0), CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7), CoreReset(value_raw=0),
    ))
    network = NetworkV0(
        nodes=(NetworkNodeV0("A", config, program),
               NetworkNodeV0("B", config, program)),
        edges=(NetworkEdgeV0("A", 7, "B", 0, 2),
               NetworkEdgeV0("A", 7, "B", 0, 2)),
    )
    initial = (NetworkEventV0(2, "A", 0), NetworkEventV0(2, "A", 0))
    pe0 = ProcessingElementV0(
        pe_id="PE0", program_slots=8, state_slots=2, event_slots=8,
        output_slots=8, observation_slots=8, accesses_per_service_tick=2,
    )
    architecture = ArchitectureProfileV0(
        "compiler-c3-conformance", (pe0, replace(pe0, pe_id="PE1")),
    )
    placements = (NodePlacementV0("B", "PE1"), NodePlacementV0("A", "PE0"))
    return network, initial, ResourceProfileV0(), architecture, placements


def compile_case(scenario, **overrides):
    network, events, resources, architecture, placements = scenario
    arguments = {
        "network_ir_json": dumps_network_ir_v0(network),
        "initial_events": events,
        "resource_profile": resources,
        "architecture": architecture,
        "placements": placements,
    }
    arguments.update(overrides)
    return compile_network_ir_v0(**arguments)


def document(scenario):
    return dumps_compilation_manifest_v0(compile_case(scenario))


def rehash_json(original, edit):
    parsed = json.loads(original)
    edit(parsed)
    # Adversarial checksum recomputation with no call to the implementation.
    parsed["payload_sha256"] = manual_digest(parsed["payload"])
    return canonical(parsed)


def reject(doc, exc=ValueError):
    with pytest.raises(exc):
        loads_compilation_manifest_v0(doc)


def test_independent_canonical_json_oracle(scenario):
    output = document(scenario)
    assert output == canonical(json.loads(output))


def test_independent_digest_oracle(scenario):
    parsed = json.loads(document(scenario))
    assert parsed["payload_sha256"] == manual_digest(parsed["payload"])
    assert len(parsed["payload_sha256"]) == 64


def test_exact_envelope_and_payload_fields(scenario):
    parsed = json.loads(document(scenario))
    assert set(parsed) == {"schema", "version", "payload", "payload_sha256"}
    assert parsed["schema"] == SCHEMA
    assert parsed["version"] == "0"
    assert set(parsed["payload"]) == {
        "network_ir", "initial_events", "resource_profile", "architecture",
        "placements", "resource_admission", "pe_admission",
    }


def test_direct_admission_oracle_matches_embedded_claims(scenario):
    network, events, resources, architecture, placements = scenario
    payload = json.loads(document(scenario))["payload"]
    assert payload["resource_admission"] == json.loads(canonical(asdict(
        admit_network_v0(network, events, resources))))
    assert payload["pe_admission"] == json.loads(canonical(asdict(
        admit_pe_mapping_v0(network, architecture, placements))))


def test_network_ir_oracle(scenario):
    network = scenario[0]
    assert json.loads(dumps_network_ir_v0(network)) == json.loads(
        document(scenario))["payload"]["network_ir"]


def test_roundtrip_is_exact(scenario):
    assert loads_compilation_manifest_v0(document(scenario)) == compile_case(scenario)


def test_duplicate_initial_spikes_and_parallel_edges_survive(scenario):
    compiled = loads_compilation_manifest_v0(document(scenario))
    assert len(compiled.initial_events) == 2
    assert compiled.initial_events[0] == compiled.initial_events[1]
    assert len(compiled.network.edges) == 2
    assert compiled.network.edges[0] == compiled.network.edges[1]


def test_functional_behavior_is_unchanged(scenario):
    network, events, *_ = scenario
    reconstructed = loads_compilation_manifest_v0(document(scenario))
    assert run_network_v0(network, events) == run_network_v0(
        reconstructed.network, reconstructed.initial_events)


def test_compiled_result_is_frozen(scenario):
    result = loads_compilation_manifest_v0(document(scenario))
    with pytest.raises(FrozenInstanceError):
        result.initial_events = ()


def test_manifest_stability_under_input_ir_formatting(scenario):
    network = scenario[0]
    formatted = json.dumps(json.loads(dumps_network_ir_v0(network)), indent=3)
    variant = compile_case(scenario, network_ir_json=formatted)
    assert dumps_compilation_manifest_v0(variant) == document(scenario)


def test_manifest_stability_under_placement_order(scenario):
    variant = compile_case(scenario, placements=scenario[4][::-1])
    assert dumps_compilation_manifest_v0(variant) == document(scenario)


def test_empty_initial_events_are_preserved(scenario):
    compiled = compile_case(scenario, initial_events=())
    assert loads_compilation_manifest_v0(
        dumps_compilation_manifest_v0(compiled)).initial_events == ()


def test_checksum_detects_unrehashed_tamper(scenario):
    parsed = json.loads(document(scenario))
    parsed["payload"]["initial_events"] = []
    reject(canonical(parsed))


def test_rehash_cannot_forge_resource_admission(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"].update(resource_admission={})))


def test_rehash_cannot_forge_pe_admission(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"].update(pe_admission={})))


def test_rehash_cannot_bypass_logical_capacity(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["resource_profile"].update(max_nodes=1)))


def test_rehash_cannot_bypass_pe_program_capacity(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["architecture"]["pes"][0].update(program_slots=1)))


def test_rehash_cannot_use_unknown_pe(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["placements"][0].update(pe_id="missing")))


def test_rehash_cannot_remove_node_placement(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["placements"].pop()))


def test_rehash_cannot_reorder_canonical_placements(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["placements"].reverse()))


def test_rehash_cannot_insert_unrecognized_payload_field(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"].update(unexpected=True)))


def test_rehash_cannot_bypass_network_ir_schema(scenario):
    reject(rehash_json(document(scenario),
        lambda d: d["payload"]["network_ir"].update(schema="invalid-network")))


def test_wrong_outer_schema_rejected(scenario):
    parsed = json.loads(document(scenario))
    parsed["schema"] = "spk-compilation-manifest/v1"
    reject(canonical(parsed))


def test_wrong_version_rejected(scenario):
    parsed = json.loads(document(scenario))
    parsed["version"] = "1"
    reject(canonical(parsed))


def test_unrecognized_outer_field_rejected(scenario):
    parsed = json.loads(document(scenario))
    parsed["unexpected"] = 1
    reject(canonical(parsed))


def test_duplicate_outer_json_key_rejected(scenario):
    doc = document(scenario)
    assert '"schema":"spk-compilation-manifest/v0"' in doc
    reject(doc.replace('"schema":"spk-compilation-manifest/v0"',
        '"schema":"spk-compilation-manifest/v0","schema":"other"', 1))


def test_nonfinite_json_token_rejected(scenario):
    doc = document(scenario)
    reject(doc[:-1] + ',"bad":NaN}')


def test_invalid_checksum_format_rejected(scenario):
    parsed = json.loads(document(scenario))
    parsed["payload_sha256"] = "00"
    reject(canonical(parsed))


def test_invalid_public_api_types_rejected():
    with pytest.raises(TypeError):
        loads_compilation_manifest_v0(None)
    with pytest.raises(TypeError):
        dumps_compilation_manifest_v0(None)


def test_content_changes_change_digest(scenario):
    original = document(scenario)
    alternate = dumps_compilation_manifest_v0(compile_case(
        scenario, initial_events=(),
    ))
    assert original != alternate
    assert json.loads(original)["payload_sha256"] != json.loads(alternate)["payload_sha256"]


def test_identically_recompiled_content_is_byte_identical(scenario):
    first = document(scenario)
    for _ in range(3):
        assert document(scenario) == first


def test_process_hash_seed_does_not_affect_bytes():
    """Fresh interpreters ensure process-local hash randomization is exercised."""
    code = '''
from dataclasses import replace
from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import dumps_compilation_manifest_v0
from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.resource_admission_v0 import ResourceProfileV0
from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkEdgeV0, NetworkNodeV0, NetworkV0
c=CoreConfig(state_bits=8,fractional_bits=0)
p=CoreProgram((CoreAcc(weight=1,channel=0),CoreCmp(threshold_raw=1),CoreEmit(channel_out=7),CoreReset(value_raw=0)))
n=NetworkV0((NetworkNodeV0('A',c,p),NetworkNodeV0('B',c,p)),(NetworkEdgeV0('A',7,'B',0,2),NetworkEdgeV0('A',7,'B',0,2)))
e=(NetworkEventV0(2,'A',0),NetworkEventV0(2,'A',0))
pe=ProcessingElementV0('PE0',8,2,8,8,8,2)
a=ArchitectureProfileV0('compiler-c3-conformance',(pe,replace(pe,pe_id='PE1')))
result=compile_network_ir_v0(dumps_network_ir_v0(n),e,ResourceProfileV0(),a,(NodePlacementV0('B','PE1'),NodePlacementV0('A','PE0')))
print(dumps_compilation_manifest_v0(result))
'''
    results = []
    for seed in ("0", "1", "91"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1], env=env,
            text=True, capture_output=True, check=True, timeout=20,
        )
        results.append(completed.stdout.strip())
    assert results[0] == results[1] == results[2]
    assert results[0] == canonical(json.loads(results[0]))
