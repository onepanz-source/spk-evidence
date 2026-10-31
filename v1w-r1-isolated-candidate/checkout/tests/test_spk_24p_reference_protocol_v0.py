"""Pure checks for stable evidence structures and declared host semantics."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'search/spk_24p_network_application_host_v0.py'


def test_source_has_no_direct_single_root_or_custody_imports():
    tree = ast.parse(MODULE.read_text(encoding='utf-8'))
    imports = []
    for entry in ast.walk(tree):
        if isinstance(entry, ast.ImportFrom) and entry.module:
            imports.append(entry.module)
        if isinstance(entry, ast.Import):
            imports.extend(alias.name for alias in entry.names)
    assert not any(name.startswith('spk_simulator.owned_root') or
                   name.startswith('spk_simulator.application_runtime_host')
                   for name in imports)


def test_no_dynamic_import_or_exec_in_reference_host():
    tree = ast.parse(MODULE.read_text(encoding='utf-8'))
    calls = [x.func.id for x in ast.walk(tree) if isinstance(x, ast.Call)
             and isinstance(x.func, ast.Name)]
    assert not any(x in ('exec', 'eval', '__import__') for x in calls)


def test_contract_only_uses_frozen_runtime_as_actual_engine():
    src = MODULE.read_text(encoding='utf-8')
    assert 'compare_actual_v0(network, events, watched_value' in src
    assert 'execute_v0(case, **budgets)' in src
    assert 'loads_compilation_manifest_v0(manifest_json)' in src
