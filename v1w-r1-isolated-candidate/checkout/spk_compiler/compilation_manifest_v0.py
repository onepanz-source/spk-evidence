"""SPK Compiler C2: canonical, self-contained compilation manifest v0.

The digest detects accidental or unkeyed modifications. It is NOT a
signature, an authentication token, or a proof of dynamic feasibility.
"""

from dataclasses import asdict, fields
from hashlib import sha256
import json
import re

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_compiler.compile_pipeline_v0 import CompiledNetworkV0, compile_network_ir_v0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.resource_admission_v0 import ResourceProfileV0
from spk_network.events_v0 import NetworkEventV0

SCHEMA_V0 = "spk-compilation-manifest/v0"
VERSION_V0 = "0"
_PAYLOAD_FIELDS = frozenset({
    "network_ir", "initial_events", "resource_profile", "architecture",
    "placements", "resource_admission", "pe_admission",
})


def _canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )


def _digest(payload):
    # Domain separation prevents this checksum being mistaken for one
    # computed for another document type.
    raw = (SCHEMA_V0 + "\n" + _canonical_json(payload)).encode("utf-8")
    return sha256(raw).hexdigest()


def _object_pairs_strict(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _record(value, expected_keys, label):
    if type(value) is not dict or set(value) != set(expected_keys):
        raise ValueError(f"invalid {label} fields")
    return value


def _instance(value, cls, label):
    data = _record(value, (f.name for f in fields(cls)), label)
    return cls(**data)


def _as_payload(compiled):
    # Verify consistency even if a caller constructs CompiledNetworkV0 by
    # hand; frozen dataclasses are not a trust boundary.
    checked = compile_network_ir_v0(
        compiled.canonical_network_ir,
        compiled.initial_events,
        compiled.resource_profile,
        compiled.architecture,
        compiled.placements,
    )
    if checked != compiled:
        raise ValueError("compiled input differs from fresh admission")

    payload = {
        "network_ir": json.loads(compiled.canonical_network_ir),
        "initial_events": [asdict(e) for e in compiled.initial_events],
        "resource_profile": asdict(compiled.resource_profile),
        "architecture": asdict(compiled.architecture),
        "placements": [asdict(p) for p in compiled.placements],
        "resource_admission": asdict(compiled.resource_admission),
        "pe_admission": asdict(compiled.pe_admission),
    }
    # dataclasses.asdict preserves tuples, while JSON represents them as
    # arrays. Normalize before hashing or comparing with parsed JSON.
    return json.loads(_canonical_json(payload))


def dumps_compilation_manifest_v0(compiled: CompiledNetworkV0) -> str:
    """Produce a canonical JSON document from an admitted C1 result."""
    if type(compiled) is not CompiledNetworkV0:
        raise TypeError("expected CompiledNetworkV0")
    payload = _as_payload(compiled)
    return _canonical_json({
        "schema": SCHEMA_V0,
        "version": VERSION_V0,
        "payload_sha256": _digest(payload),
        "payload": payload,
    })


def loads_compilation_manifest_v0(text: str) -> CompiledNetworkV0:
    """Strictly check checksum and independently redo BOTH admission gates."""
    if type(text) is not str:
        raise TypeError("manifest must be JSON text")

    document = json.loads(
        text, object_pairs_hook=_object_pairs_strict,
        parse_constant=_reject_constant,
    )
    _record(document, ("schema", "version", "payload_sha256", "payload"),
            "manifest")
    if document["schema"] != SCHEMA_V0 or document["version"] != VERSION_V0:
        raise ValueError("unsupported compilation manifest schema/version")

    payload = _record(document["payload"], _PAYLOAD_FIELDS, "payload")
    claimed = document["payload_sha256"]
    if type(claimed) is not str or re.fullmatch(r"[0-9a-f]{64}", claimed) is None:
        raise ValueError("invalid manifest checksum")
    if claimed != _digest(payload):
        raise ValueError("manifest checksum mismatch")

    if type(payload["network_ir"]) is not dict:
        raise ValueError("network_ir must be a JSON object")
    if type(payload["initial_events"]) is not list:
        raise ValueError("invalid initial_events")
    if type(payload["placements"]) is not list:
        raise ValueError("invalid placements")

    events = tuple(
        _instance(entry, NetworkEventV0, "initial event")
        for entry in payload["initial_events"]
    )
    resource_profile = _instance(
        payload["resource_profile"], ResourceProfileV0, "resource profile",
    )

    architecture_data = _record(
        payload["architecture"], (f.name for f in fields(ArchitectureProfileV0)),
        "architecture",
    )
    if type(architecture_data["pes"]) is not list:
        raise ValueError("architecture pes must be a list")
    pes = tuple(
        _instance(item, ProcessingElementV0, "PE")
        for item in architecture_data["pes"]
    )
    architecture = ArchitectureProfileV0(
        profile_id=architecture_data["profile_id"], pes=pes,
    )
    placements = tuple(
        _instance(item, NodePlacementV0, "placement")
        for item in payload["placements"]
    )

    # The frozen Network IR codec validates its own schema and version.
    compiled = compile_network_ir_v0(
        network_ir_json=_canonical_json(payload["network_ir"]),
        initial_events=events,
        resource_profile=resource_profile,
        architecture=architecture,
        placements=placements,
    )

    # Check derived admission proofs against independent recomputation and
    # reject noncanonical placement order / alternate structural encodings.
    if _as_payload(compiled) != payload:
        raise ValueError("manifest conflicts with independently compiled result")
    return compiled
