"""SPK 24h: reproducible *static* application-host adoption inventory.

Does not import/execute any repository module. An import/call in source is NOT
proof of runtime reachability or exclusivity. This tool never returns PASS for
host-wide enforcement; its acceptance is the reproducibility of its inventory.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None


DISPATCH = 'spk_simulator.owned_root_execution_dispatch_v0'
DISPATCHER = DISPATCH + '.OwnedRootExecutionDispatcherV0'
RAW_OWNER_MODULES = (
    'spk_simulator.owned_root_single_clock_v0',
    'spk_simulator.owned_root_terminal_commit_v0',
    'spk_simulator.owned_root_authority_custody_v0',
    'spk_simulator.owned_root_custody_execution_v0',
)
NON_APPLICATION_REPO_TOOLS = frozenset({
    # Manual inspection (2026-10-15): source/archive collector; it never
    # constructs or dispatches an SPK execution epoch. Match exact root path.
    'spk_24d_collect.py',
})
IGNORED_DIRS = frozenset({
    '.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox', 'node_modules', '.idea', '.vscode', 'build',
    'dist', '.eggs',
})


def _kind(rel: str) -> str:
    if rel in NON_APPLICATION_REPO_TOOLS:
        return 'repository_tool'
    prefix = rel.split('/', 1)[0]
    if prefix in ('tests', 'test') or rel.startswith('test_'):
        return 'test'
    if prefix in ('search', 'benchmarks', 'examples'):
        return 'research'
    if prefix == 'spk_simulator':
        return 'simulator_library'
    return 'unclassified_source'


def _is_known_non_application_tool(row: dict) -> bool:
    # A manually inspected tool is exempt only while its imports and direct
    # calls show no dispatcher/owner use or dynamic execution. A later change
    # to an executable SPK client must re-enter the candidate inventory.
    return (row['classification'] == 'repository_tool'
            and not row['dispatcher_reference']
            and not row['raw_owner_modules']
            and not row['dynamic_call_syntax'])


def _resolve_import(module: str | None, level: int, rel: str) -> str:
    if not level:
        return module or ''
    parts = Path(rel).with_suffix('').parts
    package = list(parts[:-1]) if parts[-1] != '__init__' else list(parts[:-1])
    if level > len(package):
        return ''
    target = package[:len(package) - level + 1]
    if module:
        target += module.split('.')
    return '.'.join(target)


def _name(expr: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Name):
        return aliases.get(expr.id, expr.id)
    if isinstance(expr, ast.Attribute):
        base = _name(expr.value, aliases)
        return f'{base}.{expr.attr}' if base else None
    return None


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq) or len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]
    return ((isinstance(left, ast.Name) and left.id == '__name__'
             and isinstance(right, ast.Constant) and right.value == '__main__')
            or (isinstance(right, ast.Name) and right.id == '__name__'
                and isinstance(left, ast.Constant) and left.value == '__main__'))


def inspect_source(rel: str, source: bytes) -> dict:
    """Parse literal import edges, direct call targets, and entrypoint syntax."""
    tree = ast.parse(source, filename=rel)
    aliases: dict[str, str] = {}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    aliases[alias.name.split('.')[0]] = alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_import(node.module, node.level, rel)
            if base:
                imported.add(base)
            for alias in node.names:
                if alias.name == '*':
                    imported.add(f'{base}.*')
                else:
                    aliases[alias.asname or alias.name] = f'{base}.{alias.name}'
                    # If `from spk_simulator import owned_root_execution_dispatch_v0`
                    # is used, the module import becomes a source reference.
                    imported.add(f'{base}.{alias.name}')

    calls = set()
    dynamic_calls = set()
    assignments: dict[str, str] = {}
    # A syntactic hint only: no control-flow or interprocedural inference.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = _name(node.func, aliases)
            if target:
                calls.add(target)
                if target in ('importlib.import_module', '__import__', 'builtins.__import__', 'eval', 'exec', 'builtins.eval', 'builtins.exec'):
                    dynamic_calls.add(target)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            val = node.value
            if isinstance(val, ast.Call) and _name(val.func, aliases) == DISPATCHER:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        assignments[t.id] = DISPATCHER
    has_construct = DISPATCHER in calls
    has_install = any(f'{name}.install' in calls for name in assignments)
    has_dispatch = any(f'{name}.dispatch' in calls for name in assignments)
    reference = (any(x == DISPATCH or x.startswith(DISPATCH + '.') for x in imported)
                 or any(x.startswith(DISPATCH + '.') for x in calls))
    raw_refs = sorted(m for m in RAW_OWNER_MODULES if any(
        imp == m or imp.startswith(m + '.') for imp in imported)
        or any(c.startswith(m + '.') for c in calls))
    return {
        'path': rel,
        'classification': _kind(rel),
        'main_guard': any(isinstance(n, ast.If) and _is_main_guard(n) for n in ast.walk(tree)),
        'dispatcher_reference': reference,
        'dispatcher_construction_call': has_construct,
        'same_binding_install_call': has_install,
        'same_binding_dispatch_call': has_dispatch,
        'raw_owner_modules': raw_refs,
        'dynamic_call_syntax': sorted(dynamic_calls),
        'star_imports': sorted(x for x in imported if x.endswith('.*')),
    }


def _script_entrypoints(root: Path) -> tuple[list[dict], list[str]]:
    result = []
    limitations = []
    path = root / 'pyproject.toml'
    if path.is_file():
        if tomllib is None:
            limitations.append('pyproject.toml present but tomllib unavailable')
        else:
            try:
                data = tomllib.loads(path.read_text(encoding='utf-8'))
                for section in ('scripts', 'gui-scripts'):
                    for name, target in sorted(data.get('project', {}).get(section, {}).items()):
                        result.append({'source': 'pyproject.toml', 'script': str(name), 'target': str(target)})
                for name, val in sorted(data.get('tool', {}).get('poetry', {}).get('scripts', {}).items()):
                    result.append({'source': 'pyproject.toml:poetry', 'script': str(name), 'target': str(val)})
            except (OSError, UnicodeError, ValueError, TypeError) as e:
                limitations.append(f'pyproject.toml could not be parsed: {type(e).__name__}')
    if (root / 'setup.cfg').is_file():
        limitations.append('setup.cfg entry_points require manual inspection')
    if (root / 'setup.py').is_file():
        limitations.append('setup.py entry_points require manual inspection; setup.py was not executed')
    return result, limitations


def audit_repository(root: Path) -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    files = []
    parse_errors = []
    fingerprint = hashlib.sha256()
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not (Path(folder) / d).is_symlink())
        for file in sorted(names):
            p = Path(folder) / file
            if p.suffix != '.py' or p.is_symlink():
                continue
            rel = p.relative_to(root).as_posix()
            try:
                source = p.read_bytes()
                fingerprint.update(rel.encode('utf-8') + b'\0' + len(source).to_bytes(8, 'big') + source)
                files.append(inspect_source(rel, source))
            except (OSError, SyntaxError, UnicodeError, ValueError) as e:
                parse_errors.append({'path': rel, 'error_kind': type(e).__name__, 'detail': str(e)[:200]})
    files.sort(key=lambda x: x['path'])
    scripts, limitations = _script_entrypoints(root)
    host = sorted({f['path'] for f in files if f['classification'] not in ('test', 'research', 'simulator_library')
                   and not _is_known_non_application_tool(f)
                   and (f['main_guard'] or f['dispatcher_reference'])})
    for entry in scripts:
        # An entrypoint may reference a module outside the scanned tree; it is
        # still an explicit candidate, never considered verified adoption.
        host.append(f"entrypoint:{entry['script']}={entry['target']}")
    host = sorted(set(host))
    dispatcher_consumers = [f for f in files if f['dispatcher_reference']]
    non_test_consumers = [f for f in dispatcher_consumers if f['classification'] not in ('test', 'research', 'simulator_library')
                          and not _is_known_non_application_tool(f)]
    # Internal SDK definition imports do not constitute host adoption.
    evidence = any(f['dispatcher_reference'] for f in non_test_consumers)
    if parse_errors or any('could not be parsed' in x or 'unavailable' in x for x in limitations):
        status = 'INCOMPLETE_STATIC_INVENTORY'
    elif evidence:
        status = 'ADOPTION_CANDIDATE_UNVERIFIED'
    else:
        status = 'NO_APPLICATION_ADOPTION_EVIDENCE'
    return {
        'schema': 'spk-application-host-integration-audit/v0',
        'status': status,
        'python_files_scanned': len(files),
        'python_source_sha256': fingerprint.hexdigest(),
        'host_candidates': host,
        'packaging_entrypoints': scripts,
        'dispatcher_references': dispatcher_consumers,
        'application_dispatcher_candidates': non_test_consumers,
        'raw_owner_importers': [f for f in files if f['raw_owner_modules'] and f['classification'] != 'test'],
        'dynamic_import_or_execution_syntax': [
            {'path': f['path'], 'forms': f['dynamic_call_syntax']}
            for f in files if f['dynamic_call_syntax'] and f['classification'] != 'test'
        ],
        'non_application_repository_tools': sorted(f['path'] for f in files if _is_known_non_application_tool(f)),
        'star_import_sites': [
            {'path': f['path'], 'imports': f['star_imports']}
            for f in files if f['star_imports'] and f['classification'] != 'test'
        ],
        'parse_errors': parse_errors,
        'limitations': limitations + [
            'AST references are not evidence of runtime adoption, exclusive routing, or unforgeability.',
            'Dynamic calls, runtime plugins, native extensions, shell launchers, and external repositories are not exhaustively resolved.',
            'No cross-instance/process fencing, crash durability, or host-wide enforcement is established.',
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='.', type=Path, help='repository root (read only)')
    p.add_argument('--json-out', type=Path, help='optional JSON report destination')
    p.add_argument('--require-adoption-evidence', action='store_true',
                   help='return 2 unless a non-test dispatcher consumer is found (NOT proof of enforcement)')
    a = p.parse_args(argv)
    report = audit_repository(a.repo)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    if a.json_out:
        a.json_out.write_text(rendered, encoding='utf-8')
    print('SPK 24h STATIC HOST AUDIT:', report['status'])
    print('python files:', report['python_files_scanned'])
    print('source fingerprint:', report['python_source_sha256'])
    print('host candidates:', len(report['host_candidates']))
    print('application dispatcher consumers:', len(report['application_dispatcher_candidates']))
    print('raw-owner importing modules outside tests:', len(report['raw_owner_importers']))
    print('parse errors:', len(report['parse_errors']))
    if not a.json_out:
        print(rendered)
    if report['status'] == 'INCOMPLETE_STATIC_INVENTORY':
        return 3
    if a.require_adoption_evidence and report['status'] != 'ADOPTION_CANDIDATE_UNVERIFIED':
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
