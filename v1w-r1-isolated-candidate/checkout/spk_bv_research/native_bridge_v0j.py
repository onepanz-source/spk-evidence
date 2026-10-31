"""Fail-closed offline bridge for explicitly inspected native BV packet NDJSON.

Never imports, executes, or assumes BV v0h internals. Every mapping must be
supplied explicitly after inspecting the native producer. Structural bijection
is NOT equivalence to BV v0h's independent replay witness.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
from typing import Mapping

from .evidence_cost_v0i import (
    EvidenceCostLedger, EvidenceCostContractError, Reception, BudgetProfile,
)

FIELDS = frozenset(Reception.__dataclass_fields__)
META = frozenset(("schema", "source_label", "field_paths", "cost_model", "assumptions"))
SCHEMA = "spk-bv-native-packet-mapping/v0j"
MAX_FILE_BYTES = 32_000_000
MAX_ROWS = 100_000
MAX_LINE_BYTES = 1_000_000


class NativeBridgeError(ValueError):
    pass


def _sha(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def _path_get(record, path):
    node = record
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise NativeBridgeError(f"path unavailable: {path!r}")
        node = node[key]
    return node


@dataclass(frozen=True)
class NativeMapping:
    source_label: str
    field_paths: Mapping[str, tuple[str, ...] | int]
    cost_model: str
    assumptions: tuple[str, ...]
    manifest_sha256: str

    @classmethod
    def from_dict(cls, doc):
        if not isinstance(doc, dict) or set(doc) != META or doc["schema"] != SCHEMA:
            raise NativeBridgeError("mapping manifest schema/fields invalid")
        label = doc["source_label"]
        if not isinstance(label, str) or not 1 <= len(label) <= 128 or not label.isascii():
            raise NativeBridgeError("source_label must be bounded ASCII")
        paths = doc["field_paths"]
        if not isinstance(paths, dict) or set(paths) != FIELDS:
            raise NativeBridgeError("all 12 explicit mappings are required")
        model = doc["cost_model"]
        if model not in ("native_positive_units", "uniform_abstract_unit"):
            raise NativeBridgeError("cost_model must declare the unit source")
        notes = doc["assumptions"]
        if not isinstance(notes, list) or not notes or not all(
            isinstance(x, str) and 1 <= len(x) <= 256 for x in notes
        ):
            raise NativeBridgeError("nonempty explicit assumptions required")
        normalized = {}
        seen_paths = set()
        for field, entry in paths.items():
            if (field == "transport_units" and model == "uniform_abstract_unit"
                    and type(entry) is int and entry == 1):
                normalized[field] = 1
                continue
            if not isinstance(entry, list) or not 1 <= len(entry) <= 8 or not all(
                isinstance(x, str) and 1 <= len(x) <= 128 for x in entry
            ):
                raise NativeBridgeError(f"{field}: expected nonempty explicit key path")
            # Prevent accidental alias of two distinct identity dimensions.
            pointer = tuple(entry)
            if pointer in seen_paths:
                raise NativeBridgeError("field mappings may not alias a source path")
            seen_paths.add(pointer)
            normalized[field] = pointer
        if model == "native_positive_units" and type(normalized["transport_units"]) is int:
            raise NativeBridgeError("native unit model cannot use constant")
        if model == "uniform_abstract_unit" and normalized["transport_units"] != 1:
            raise NativeBridgeError("uniform cost model requires unit literal 1")
        return cls(label, normalized, model, tuple(notes), _sha(doc))

    def convert(self, record):
        if not isinstance(record, dict):
            raise NativeBridgeError("native packet must be a JSON object")
        values = {field: (_path_get(record, source) if isinstance(source, tuple) else source)
                  for field, source in self.field_paths.items()}
        try:
            return Reception.from_dict(values)
        except EvidenceCostContractError as exc:
            raise NativeBridgeError(f"normalized receipt rejected: {exc}") from exc


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def read_manifest(path: Path) -> NativeMapping:
    if path.stat().st_size > MAX_LINE_BYTES:
        raise NativeBridgeError("manifest exceeds size bound")
    try:
        return NativeMapping.from_dict(json.loads(path.read_text(encoding="utf-8"),
                                                  object_pairs_hook=_reject_duplicate_keys,
                                                  parse_constant=_reject_json_constant))
    except (ValueError, UnicodeError) as exc:
        raise NativeBridgeError(f"invalid mapping manifest: {exc}") from exc


def bridge_packet_ndjson(path: Path, mapping: NativeMapping,
                         *, profile: BudgetProfile | None = None):
    """One native input packet row must produce exactly one unique Reception.

    Entire function emits no receipt output before completing all checks.
    Ingestion is read-only, and the native-source evidence digest is calculated
    from complete native records, not manufactured v0i identities.
    """
    if path.stat().st_size > MAX_FILE_BYTES:
        raise NativeBridgeError("native file exceeds byte bound")
    ledger = EvidenceCostLedger(profile)
    source_canonical = []
    unique_ids = set()
    rows = 0
    with path.open("rb") as file:
        for raw in file:
            if len(raw) > MAX_LINE_BYTES:
                raise NativeBridgeError("native line exceeds byte bound")
            if not raw.strip():
                raise NativeBridgeError("native packet file cannot contain blank records")
            rows += 1
            if rows > MAX_ROWS:
                raise NativeBridgeError("native packet file exceeds row bound")
            try:
                # Fail closed on duplicate JSON object keys, including nested keys.
                doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
                                 parse_constant=_reject_json_constant)
                receipt = mapping.convert(doc)
                tx_key = (receipt.epoch, receipt.transmission_id)
                if tx_key in unique_ids:
                    raise NativeBridgeError("native packet to reception not injective (duplicate transmission ID)")
                # Error if both packets differ but collapse into one normalized record.
                if not ledger.ingest(receipt):
                    raise NativeBridgeError("duplicate normalized transmission")
            except (UnicodeError, ValueError, TypeError, EvidenceCostContractError) as exc:
                raise NativeBridgeError(f"native row {rows}: {exc}") from exc
            unique_ids.add(tx_key)
            source_canonical.append(doc)
    if rows == 0:
        raise NativeBridgeError("empty native physical packet trace is not evidence")
    snapshot = ledger.snapshot()
    if snapshot["physical_transmissions"] != rows:
        raise NativeBridgeError("raw packet to normalized reception cardinality mismatch")
    snapshot["native_bridge"] = {
        "schema": "spk-bv-native-packet-bridge-receipt/v0j",
        "source_label": mapping.source_label,
        "source_packet_rows": rows,
        "bijective_packet_mapping": True,
        "source_ordered_sha256": _sha(source_canonical),
        "source_multiset_sha256": _sha(sorted((_sha(x) for x in source_canonical))),
        "mapping_manifest_sha256": mapping.manifest_sha256,
        "cost_model": mapping.cost_model,
        "assumptions": list(mapping.assumptions),
        "claims_excluded": ["native-v0h-source-authenticity", "v0h-independent-witness-equivalence",
                            "causal-credit", "packet-independence", "runtime-link-capacity"],
    }
    return snapshot
