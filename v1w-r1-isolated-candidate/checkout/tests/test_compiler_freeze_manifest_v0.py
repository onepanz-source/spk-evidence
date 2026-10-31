"""C4 freeze-manifest fail-closed checks, independent of compiler runtime."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "search"))
from compiler_v0_freeze_manifest import (  # noqa: E402
    FreezeManifestError, canonical, digest, make_document, validate_document,
)

BASE = "a" * 40
SOURCE = "b" * 40


@pytest.fixture
def inventory(tmp_path):
    paths = ("spk_compiler/a.py", "docs/spec.md")
    for name in paths:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("content:" + name, encoding="utf-8")
    return tmp_path, paths


def valid(inventory):
    root, paths = inventory
    return make_document(root, paths, BASE, SOURCE)


def check(inventory, doc):
    root, paths = inventory
    validate_document(doc, root, paths)


def rehash(doc):
    doc["payload_sha256"] = digest(doc["payload"])
    return doc


def test_manifest_passes_untampered(inventory):
    check(inventory, valid(inventory))


def test_json_canonical_is_stable(inventory):
    doc = valid(inventory)
    assert canonical(doc) == canonical(doc)
    assert len(doc["payload_sha256"]) == 64


def test_manifest_order_is_canonical(inventory):
    root, paths = inventory
    assert make_document(root, paths[::-1], BASE, SOURCE) == valid(inventory)


def test_source_file_modification_is_rejected(inventory):
    doc = valid(inventory)
    (inventory[0] / "spk_compiler/a.py").write_text("altered")
    with pytest.raises(FreezeManifestError, match="changed"):
        check(inventory, doc)


def test_manifest_checksum_tampering_is_rejected(inventory):
    doc = valid(inventory)
    doc["payload"]["compiler_source_commit"] = "c" * 40
    with pytest.raises(FreezeManifestError, match="digest"):
        check(inventory, doc)


def test_rehashed_digest_does_not_bypass_file_hash(inventory):
    doc = valid(inventory)
    doc["payload"]["files"][0]["sha256"] = "0" * 64
    with pytest.raises(FreezeManifestError, match="changed"):
        check(inventory, rehash(doc))


def test_missing_file_record_is_rejected_even_after_rehash(inventory):
    doc = valid(inventory)
    doc["payload"]["files"].pop()
    with pytest.raises(FreezeManifestError, match="inventory"):
        check(inventory, rehash(doc))


def test_duplicate_file_record_is_rejected(inventory):
    doc = valid(inventory)
    doc["payload"]["files"].append(copy.deepcopy(doc["payload"]["files"][0]))
    with pytest.raises(FreezeManifestError, match="inventory"):
        check(inventory, rehash(doc))


def test_invalid_baseline_is_rejected(inventory):
    doc = valid(inventory)
    doc["payload"]["baseline_tag"] = "unknown"
    with pytest.raises(FreezeManifestError, match="baseline"):
        check(inventory, rehash(doc))


def test_invalid_schema_is_rejected(inventory):
    doc = valid(inventory)
    doc["schema"] = "v2"
    with pytest.raises(FreezeManifestError, match="version"):
        check(inventory, doc)


def test_unsorted_file_record_is_rejected(inventory):
    doc = valid(inventory)
    doc["payload"]["files"].reverse()
    with pytest.raises(FreezeManifestError, match="inventory"):
        check(inventory, rehash(doc))


def test_path_traversal_is_rejected(inventory):
    root, _ = inventory
    with pytest.raises(FreezeManifestError, match="Unsafe"):
        make_document(root, ("../outside.py",), BASE, SOURCE)


def test_symlink_is_rejected(inventory):
    root, _ = inventory
    (root / "bad-link.py").symlink_to(root / "spk_compiler/a.py")
    with pytest.raises(FreezeManifestError, match="Symlink"):
        make_document(root, ("bad-link.py",), BASE, SOURCE)


def test_invalid_commit_rejected(inventory):
    root, paths = inventory
    with pytest.raises(FreezeManifestError, match="commit"):
        make_document(root, paths, "not-a-commit", SOURCE)
