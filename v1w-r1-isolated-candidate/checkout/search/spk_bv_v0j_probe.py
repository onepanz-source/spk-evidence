#!/usr/bin/env python3
"""Static, bounded, read-only probe: inspect BV native source without importing it."""
from __future__ import annotations
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import re

HINT = re.compile(r"(bv|back.validation|feedback|context|batch|recept|provenance|witness|trace)", re.I)
SYMBOL = re.compile(r"(feedback|packet|recept|context|batch|provenance|trace|witness|route|vote)", re.I)
ROOTS = ("spk_bv_research", "search", "tests")
MAX_FILES = 180
MAX_FILE_BYTES = 500_000


def _symbols(filename: Path):
    content = filename.read_bytes()
    if len(content) > MAX_FILE_BYTES:
        return {"warning": "file size exceeds scan bound"}
    if filename.suffix == ".sh":
        names = sorted(set(m.group(0) for m in re.finditer(
            rb"spk_bv_[A-Za-z0-9_]+(?:\.py|\.sh)?", content)))
        return {"script_references": [n.decode("ascii") for n in names[:30]]}
    try:
        tree = ast.parse(content, filename=str(filename))
    except (SyntaxError, ValueError, UnicodeError) as e:
        return {"warning": f"syntax: {type(e).__name__}"}
    classes, functions, keys = [], [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and SYMBOL.search(node.name):
            attrs = []
            for child in node.body:
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    attrs.append(child.target.id)
            classes.append({"name": node.name, "fields": attrs[:35], "line": node.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and SYMBOL.search(node.name):
            arguments = [x.arg for x in node.args.posonlyargs + node.args.args + node.args.kwonlyargs]
            functions.append({"name": node.name, "args": arguments[:24], "line": node.lineno})
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                and isinstance(node.slice.value, str) and SYMBOL.search(node.slice.value):
            keys.add(node.slice.value)
    return {"classes": classes[:30], "functions": functions[:45], "subscript_keys": sorted(keys)[:50]}


def inspect(root: Path):
    root = root.resolve()
    inspected = []
    candidates = []
    for base in ROOTS:
        target = root / base
        if target.is_symlink() or not target.is_dir():
            continue
        for f in target.glob("**/*"):
            if (not f.is_file() or f.is_symlink() or f.suffix not in (".py", ".sh")
                    or not HINT.search(f.name)):
                continue
            candidates.append(f)
    for path in sorted(candidates)[:MAX_FILES]:
        content = path.read_bytes()
        inspected.append({"path": path.relative_to(root).as_posix(),
                          "bytes": len(content), "source_sha256": sha256(content).hexdigest(),
                          **_symbols(path)})
    return {"schema": "spk-bv-native-source-probe/v0j",
            "status": "STATIC_DISCOVERY_ONLY", "files_scanned": len(inspected),
            "scan_truncated": len(candidates) > MAX_FILES,
            "files": inspected,
            "claims_excluded": ["trace-identity-validation", "native-source-replay",
                                "BV-v0h-equivalence", "causal-credit"]}


def main(argv=None):
    p = argparse.ArgumentParser(description="Static BV v0h/native producer discovery, read-only")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--compact", action="store_true")
    a = p.parse_args(argv)
    data = inspect(a.root)
    print(json.dumps(data, indent=None if a.compact else 2,
                     sort_keys=True, separators=(",", ":") if a.compact else None))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
