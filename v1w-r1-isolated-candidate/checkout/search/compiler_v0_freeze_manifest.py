#!/usr/bin/env python3
"""C4 release inventory. Only the already committed Compiler v0 is frozen.

No timestamps, host paths, Python interpreter details, or git working tree state
are embedded. The manifest is not a signature and does not amend Core/Network v0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

SCHEMA = "spk-compiler-freeze/v0"
BASELINE_TAG = "spk-core-network-v0"
MANIFEST = "docs/spk-compiler-v0-freeze-manifest.json"
REQUIRED = (
    "spk_compiler/network_ir_v0.py",
    "spk_compiler/resource_admission_v0.py",
    "spk_compiler/pe_admission_v0.py",
    "spk_compiler/compile_pipeline_v0.py",
    "spk_compiler/compilation_manifest_v0.py",
    "spk_architecture/profile_v0.py",
    "docs/spk-compiler-pipeline-v0.md",
    "docs/spk-compilation-manifest-v0.md",
    "docs/spk-compiler-conformance-gate-v0.md",
    "tests/test_compile_pipeline_v0.py",
    "tests/test_compilation_manifest_v0.py",
    "tests/test_compiler_conformance_v0.py",
)
HEX = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class FreezeManifestError(ValueError):
    pass


def canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(payload: dict) -> str:
    return hashlib.sha256((SCHEMA + "\n" + canonical(payload)).encode("utf-8")).hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise FreezeManifestError("Invalid file path")
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != relative:
        raise FreezeManifestError("Unsafe or noncanonical file path")
    target = root / relative
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise FreezeManifestError("Symlink or out-of-root inventory path")
    if not target.is_file():
        raise FreezeManifestError(f"Missing frozen file: {relative}")
    return target


def make_document(root: Path, paths: tuple[str, ...],
                  baseline_commit: str, source_commit: str) -> dict:
    if not COMMIT.fullmatch(baseline_commit) or not COMMIT.fullmatch(source_commit):
        raise FreezeManifestError("Invalid Git commit identifiers")
    if not paths or len(paths) != len(set(paths)):
        raise FreezeManifestError("Missing or duplicate paths")
    files = [{"path": path, "sha256": hashlib.sha256(
        _safe_file(root, path).read_bytes()).hexdigest()} for path in sorted(paths)]
    payload = {
        "baseline_tag": BASELINE_TAG,
        "baseline_commit": baseline_commit,
        "compiler_source_commit": source_commit,
        "files": files,
    }
    return {"schema": SCHEMA, "version": "0", "payload": payload,
            "payload_sha256": digest(payload)}


def validate_document(doc: object, root: Path, expected_paths: tuple[str, ...]) -> None:
    if not isinstance(doc, dict) or set(doc) != {
            "schema", "version", "payload", "payload_sha256"}:
        raise FreezeManifestError("Invalid release manifest envelope")
    if doc["schema"] != SCHEMA or doc["version"] != "0":
        raise FreezeManifestError("Unsupported release manifest version")
    payload = doc["payload"]
    if not isinstance(payload, dict) or set(payload) != {
            "baseline_tag", "baseline_commit", "compiler_source_commit", "files"}:
        raise FreezeManifestError("Invalid payload schema")
    if payload["baseline_tag"] != BASELINE_TAG:
        raise FreezeManifestError("Unexpected Core/Network baseline")
    if not all(isinstance(payload[k], str) and COMMIT.fullmatch(payload[k])
               for k in ("baseline_commit", "compiler_source_commit")):
        raise FreezeManifestError("Invalid commit identifier")
    if not isinstance(doc["payload_sha256"], str) or not HEX.fullmatch(doc["payload_sha256"]):
        raise FreezeManifestError("Invalid payload digest")
    if digest(payload) != doc["payload_sha256"]:
        raise FreezeManifestError("Payload digest mismatch")
    entries = payload["files"]
    if not isinstance(entries, list) or not entries:
        raise FreezeManifestError("Missing frozen file inventory")
    paths = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise FreezeManifestError("Invalid file record")
        path, sha = entry["path"], entry["sha256"]
        if not isinstance(sha, str) or not HEX.fullmatch(sha):
            raise FreezeManifestError("Invalid file digest")
        data = _safe_file(root, path).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise FreezeManifestError(f"Frozen file changed: {path}")
        paths.append(path)
    if paths != sorted(set(paths)) or tuple(paths) != tuple(sorted(expected_paths)):
        raise FreezeManifestError("Incomplete, duplicate, or unsorted file inventory")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise FreezeManifestError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def inventory(root: Path) -> tuple[str, ...]:
    tracked = set(git(root, "ls-files", "--", "spk_compiler", "spk_architecture").splitlines())
    compiler = {p for p in tracked if p.startswith("spk_compiler/") and p.endswith(".py")}
    paths = compiler | set(REQUIRED)
    all_tracked = set(git(root, "ls-files").splitlines())
    for path in paths:
        if path not in all_tracked:
            raise FreezeManifestError(f"File must be committed before freeze: {path}")
    return tuple(sorted(paths))


def verify_baseline(root: Path, doc: dict) -> None:
    tag_commit = git(root, "rev-parse", f"{BASELINE_TAG}^{{commit}}")
    if tag_commit != doc["payload"]["baseline_commit"]:
        raise FreezeManifestError("Core/Network baseline tag moved")
    source_commit = doc["payload"]["compiler_source_commit"]
    git(root, "merge-base", "--is-ancestor", source_commit, "HEAD")
    if git(root, "diff", "--name-only", BASELINE_TAG, "HEAD", "--",
           "spk_core", "spk_network"):
        raise FreezeManifestError("Frozen Core/Network changed since baseline")


def main() -> None:
    parser = argparse.ArgumentParser()
    flags = parser.add_mutually_exclusive_group(required=True)
    flags.add_argument("--write", action="store_true")
    flags.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    target = root / MANIFEST
    paths = inventory(root)
    if args.write:
        # Prevent recording uncommitted source as if it were the source commit.
        dirty = git(root, "diff", "HEAD", "--", *paths)
        if dirty:
            raise FreezeManifestError("Frozen source has uncommitted modifications")
        baseline = git(root, "rev-parse", f"{BASELINE_TAG}^{{commit}}")
        doc = make_document(root, paths, baseline, git(root, "rev-parse", "HEAD"))
        verify_baseline(root, doc)
        text = canonical(doc) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != text:
            raise FreezeManifestError("Existing freeze manifest differs; refusing overwrite")
        target.write_text(text, encoding="utf-8")
        print(f"Generated {MANIFEST}: {len(paths)} frozen files")
    else:
        text = target.read_text(encoding="utf-8")
        doc = json.loads(text)
        if text != canonical(doc) + "\n":
            raise FreezeManifestError("Release manifest JSON is not canonical")
        validate_document(doc, root, paths)
        verify_baseline(root, doc)
        print(f"Compiler v0 freeze manifest verified: {len(paths)} files")


if __name__ == "__main__":
    try:
        main()
    except (FreezeManifestError, OSError, ValueError) as error:
        raise SystemExit(f"FAIL compiler freeze: {error}")
