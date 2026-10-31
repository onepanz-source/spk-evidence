"""SPK 24m: frozen Compiler -> Network v0 reference execution and replay.

This is a *network* reference adapter, NOT an extension of the 24j
single-root, output-free ApplicationRuntimeHostV0 contract.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
from pathlib import Path

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import (
    dumps_compilation_manifest_v0, loads_compilation_manifest_v0,
)
from spk_compiler.network_ir_v0 import dumps_network_ir_v0, loads_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.resource_admission_v0 import ResourceProfileV0
from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkEdgeV0, NetworkNodeV0, NetworkV0
from spk_network.runtime_v0 import run_network_v0

SCHEMA = "spk-compiler-network-evidence/v0"
VERSION = "0"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _sha(data: str) -> str:
    return sha256(data.encode("utf-8")).hexdigest()


def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("invalid JSON constant: " + value)


def _parse(text):
    if type(text) is not str:
        raise TypeError("evidence must be UTF-8 JSON text")
    return json.loads(text, object_pairs_hook=_pairs_unique,
                      parse_constant=_reject_constant)


def _json_tree(value):
    """Project native runtime data onto the canonical JSON evidence domain.

    dataclasses.asdict() retains tuples recursively; canonical JSON encodes
    them as arrays, which json.loads() returns as lists. Compare the same
    wire representation during production and replay, without relaxing any
    values or fields in the evidence contract.
    """
    return _parse(_canonical(value))


def _budget(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(name + " must be a positive integer")
    return value


@dataclass
class _Recorder:
    batches: list = field(default_factory=list)
    routes: list = field(default_factory=list)

    def on_batch(self, observation):
        self.batches.append(observation)

    def on_route(self, observation):
        self.routes.append(observation)


def _execute(network, events, max_batches, max_events):
    options = dict(max_batches=max_batches, max_events=max_events)
    ordinary = run_network_v0(network, events, **options)
    observer = _Recorder()
    observed = run_network_v0(
        network, events, learning_observer=observer, **options,
    )
    if observed != ordinary:
        raise ValueError("observer changed complete network execution result")
    return _json_tree({
        "result": asdict(ordinary),
        "observations": {
            "batches": [asdict(entry) for entry in observer.batches],
            "routes": [asdict(entry) for entry in observer.routes],
        },
    })


def _payload(manifest_json, max_batches, max_events):
    compiled = loads_compilation_manifest_v0(manifest_json)
    trace = _execute(compiled.network, compiled.initial_events,
                     max_batches, max_events)
    return {
        "manifest_json": manifest_json,
        "manifest_sha256": _sha(manifest_json),
        "max_batches": max_batches,
        "max_events": max_events,
        **trace,
    }


def _seal(payload):
    envelope = {
        "schema": SCHEMA,
        "version": VERSION,
        "payload": payload,
        "payload_sha256": _sha(SCHEMA + "\n" + _canonical(payload)),
    }
    return _canonical(envelope)


def compile_and_run_v0(*, network_ir_json, initial_events,
                       resource_profile, architecture, placements,
                       max_batches=32, max_events=128):
    """Compile declarative source, reconstruct it and record full observations."""
    mb = _budget(max_batches, "max_batches")
    me = _budget(max_events, "max_events")
    compiled = compile_network_ir_v0(
        network_ir_json=network_ir_json,
        initial_events=initial_events,
        resource_profile=resource_profile,
        architecture=architecture,
        placements=placements,
    )
    manifest = dumps_compilation_manifest_v0(compiled)
    roundtrip = loads_compilation_manifest_v0(manifest)
    if roundtrip != compiled:
        raise ValueError("compiler manifest roundtrip mismatch")
    # Independent source path bypasses manifest reconstruction; both call the
    # same frozen Network v0 runtime, so this is *not* a two-engine oracle.
    source_network = loads_network_ir_v0(network_ir_json)
    source_result = run_network_v0(source_network, tuple(initial_events),
                                   max_batches=mb, max_events=me)
    payload = _payload(manifest, mb, me)
    if _json_tree(asdict(source_result)) != payload["result"]:
        raise ValueError("source and compiler-reconstructed execution diverged")
    return _seal(payload)


def verify_and_replay_v0(document):
    """Validate envelope and re-execute frozen runtime, not merely its hash.

    A matching checksum proves integrity relative to the supplied document,
    not authenticity: an attacker can alter and reseal the whole artifact.
    """
    envelope = _parse(document)
    if type(envelope) is not dict or set(envelope) != {
        "schema", "version", "payload", "payload_sha256"
    }:
        raise ValueError("invalid evidence envelope fields")
    if envelope["schema"] != SCHEMA or envelope["version"] != VERSION:
        raise ValueError("invalid evidence schema/version")
    p = envelope["payload"]
    if type(p) is not dict or set(p) != {
        "manifest_json", "manifest_sha256", "max_batches", "max_events",
        "result", "observations"
    }:
        raise ValueError("invalid evidence payload fields")
    if document != _canonical(envelope):
        raise ValueError("evidence must use canonical JSON encoding")
    if envelope["payload_sha256"] != _sha(SCHEMA + "\n" + _canonical(p)):
        raise ValueError("evidence checksum mismatch")
    if type(p["manifest_json"]) is not str or p["manifest_sha256"] != _sha(p["manifest_json"]):
        raise ValueError("manifest digest mismatch")
    mb = _budget(p["max_batches"], "max_batches")
    me = _budget(p["max_events"], "max_events")
    reconstructed = _payload(p["manifest_json"], mb, me)
    if reconstructed != p:
        raise ValueError("replay evidence mismatch")
    return p


def reference_scenario_v0():
    """Positive-delay 2-neuron routing with a duplicated edge (not an epoch host)."""
    cfg = CoreConfig(state_bits=8, fractional_bits=0)
    program = CoreProgram((
        CoreAcc(weight=1, channel=0), CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7), CoreReset(value_raw=0),
    ))
    network = NetworkV0(
        nodes=(NetworkNodeV0("A", cfg, program), NetworkNodeV0("B", cfg, program)),
        edges=(NetworkEdgeV0("A", 7, "B", 0, 3),
               NetworkEdgeV0("A", 7, "B", 0, 2),
               NetworkEdgeV0("A", 7, "B", 0, 2)),
    )
    pe = ProcessingElementV0(
        pe_id="PE0", program_slots=8, state_slots=2, event_slots=8,
        output_slots=8, observation_slots=8, accesses_per_service_tick=2,
    )
    return dict(
        network_ir_json=dumps_network_ir_v0(network),
        initial_events=(NetworkEventV0(2, "A", 0),),
        resource_profile=ResourceProfileV0(),
        architecture=ArchitectureProfileV0("spk-24m-evidence", (
            pe, replace(pe, pe_id="PE1"),
        )),
        placements=(NodePlacementV0("A", "PE0"), NodePlacementV0("B", "PE1")),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write", type=Path)
    choice.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        document = compile_and_run_v0(**reference_scenario_v0())
        args.write.write_text(document + "\n", encoding="utf-8")
    else:
        document = args.verify.read_text(encoding="utf-8").rstrip("\n")
    payload = verify_and_replay_v0(document)
    result = payload["result"]
    print(_canonical({
        "status": "PASS", "schema": SCHEMA,
        "evidence_sha256": _sha(document),
        "manifest_sha256": payload["manifest_sha256"],
        "processed_batches": result["processed_batches"],
        "processed_events": result["processed_events"],
        "route_observations": len(payload["observations"]["routes"]),
        "batch_observations": len(payload["observations"]["batches"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
