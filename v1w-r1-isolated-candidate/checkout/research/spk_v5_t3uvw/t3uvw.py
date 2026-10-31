#!/usr/bin/env python3
"""SPK v5 T3UVW: source-pinned repeated T3OPQ research execution audit.

Does NOT implement native single-pass C judgments or authenticate sensor/goal.
The original producer is invoked unchanged, twice, in the user's checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REF_SCHEMA = 'spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0'
REF_STATUS = 'SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING'
PINS = {
    'search/spk_bv_v0e_live_evidence.py': '1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py': '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'tests/test_spk_bv_live_dual_scheduler_v0e.py': '6de34cd1ff6c85c96faad3dc047066406cf49d9675ac87fc77b260814f18dfa8',
}
ADDITIONAL_PATHS = (
    'search/spk_v5_t3opq_source_bridge_gate.sh',
    'search/spk_v5_t3rst_cumulative_gate.sh',
    'research/spk_v5_t3rst/src/spk_t3rst.py',
    'research/spk_v5_t3uvw/t3uvw.py',
)

class GateError(Exception):
    pass


def fail(condition: bool, reason: str) -> None:
    if not condition:
        raise GateError(reason)


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_sha(value: Any) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def snapshot(root: Path) -> dict[str, str]:
    ret: dict[str,str] = {}
    for name in (*PINS, *ADDITIONAL_PATHS):
        p = root / name
        fail(p.is_file(), f'REQUIRED_SOURCE_ABSENT: {name}')
        ret[name] = sha_file(p)
    return ret


def verify_pins(hashes: dict[str,str]) -> None:
    for name, expected in PINS.items():
        fail(hashes.get(name) == expected,
             f'FROZEN_PIN_MISMATCH: {name} expected={expected} actual={hashes.get(name)}')


def validate_report(data: dict[str, Any], root: Path) -> dict[str, Any]:
    """Reuse prior T3RST validator, no redefinition or weaker alternative."""
    src = root / 'research/spk_v5_t3rst/src/spk_t3rst.py'
    spec = importlib.util.spec_from_file_location('_spk_t3rst_boundary', src)
    fail(spec is not None and spec.loader is not None, 'T3RST_VALIDATOR_UNAVAILABLE')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.audit_reference(data)
    fail(data.get('schema') == REF_SCHEMA and data.get('status') == REF_STATUS, 'REPORT_SCHEMA_OR_STATUS_INVALID')
    fail(summary['source_sha_verified'] is False, 'T3RST_CANNOT_ATTEST_SOURCE')
    return summary


def run_original_gate(root: Path, out: Path, log: Path) -> None:
    # No shell interpolation, no modification of frozen sources.
    gate = root / 'search/spk_v5_t3opq_source_bridge_gate.sh'
    with log.open('w', encoding='utf-8') as stream:
        completed = subprocess.run(['bash', str(gate), str(out)], cwd=root,
                                   stdout=stream, stderr=subprocess.STDOUT, check=False)
    fail(completed.returncode == 0, f'NATIVE_GATE_EXIT_{completed.returncode}: {log}')
    fail(out.is_file() and out.stat().st_size > 0, f'ORIGINAL_GATE_REPORT_MISSING: {out}')


def compare_runs(a: dict[str, Any], b: dict[str, Any], sha_a: str, sha_b: str) -> dict[str, Any]:
    fail(a == b, 'T3OPQ_NONDETERMINISTIC_REPORT_CONTENT')
    return {'exact_json_equal': True, 'byte_identical': sha_a == sha_b,
            'canonical_sha256': canonical_sha(a), 'rerun_1_sha256': sha_a,
            'rerun_2_sha256': sha_b,
            'assessment': 'DUAL_REPLAY_REPORT_DETERMINISTIC_NOT_SINGLE_PASS_CAUSAL'}


def build_result(root: Path, before: dict[str,str], after: dict[str,str],
                 run_a: dict, run_b: dict, hash_a: str, hash_b: str, outputs: list[Path]) -> dict:
    verify_pins(before)
    fail(before == after, 'SOURCE_CHANGED_DURING_REEXECUTION')
    source_summary = validate_report(run_a, root)
    validate_report(run_b, root)
    compare = compare_runs(run_a, run_b, hash_a, hash_b)
    limitations = run_a.get('claims_excluded', [])
    fail(any('dual BV-v0e source invocations' in x for x in limitations), 'DUAL_REPLAY_DISCLOSURE_MISSING')
    fail(any('host selects terminal observer' in x for x in limitations), 'HOST_SELECTION_DISCLOSURE_MISSING')
    fail(any('not authenticated' in x for x in limitations), 'SENSOR_NONAUTHENTICATION_DISCLOSURE_MISSING')
    return {
        'schema': 'spk-v5-t3uvw-reexecuted-source-custody/research-v0',
        'status': 'ORIGINAL_T3OPQ_REEXECUTED_TWICE_PINNED_DUAL_REPLAY_ONLY',
        'U_frozen_source': {'verified_legacy_pins': True, 'source_sha256': before,
                            'unchanged_during_reexecution': True,
                            'scope': 'three pinned legacy files plus four additive scripts; NOT complete transitive imports'},
        'V_original_gate': {'gate_path': 'search/spk_v5_t3opq_source_bridge_gate.sh',
                            'invocations': 2, 'same_checkout_not_independent_clones': True,
                            'reference_consistency': source_summary,
                            'comparison': compare,
                            'report_paths': [str(x) for x in outputs]},
        'W_causal_boundary': {
            'dual_replay_confirmed': True,
            'host_posthoc_terminal_selection': True,
            'native_single_pass_C_verdict_evidence': False,
            'independent_C_sensor_authentication': False,
            'native_semantic_BV_proven': False,
            'native_learning_proven': False,
            'blind_goal_generalization_proven': False,
            'next_required': 'instrument frozen producer read-only for true single-pass C-origin event receipt; do not infer it from dual replay',
        },
        'promotion_allowed': False,
        'not_a_native_semantic_BV_gate': True,
        'not_an_independent_blind_result': True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.repo.resolve()
    out = args.output.resolve()
    fail(root.is_dir() and out.parent.is_dir(), 'INVALID_REPOSITORY_OR_OUTPUT_DIRECTORY')
    paths = [out.with_name(out.stem + f'-original-{i}.json') for i in (1, 2)]
    logs = [out.with_name(out.stem + f'-original-{i}.log') for i in (1, 2)]
    fail(len({str(out), *(str(p) for p in paths), *(str(p) for p in logs)}) == 5, 'OUTPUT_COLLISION')
    before = snapshot(root)
    verify_pins(before)  # fail closed before executing producer
    for i in range(2):
        # Reject stale producer output on rerun.
        paths[i].unlink(missing_ok=True)
        run_original_gate(root, paths[i], logs[i])
        interim = snapshot(root)
        fail(interim == before, f'SOURCE_MUTATED_DURING_RUN_{i+1}')
    raw = [p.read_bytes() for p in paths]
    docs = [json.loads(b) for b in raw]
    result = build_result(root, before, snapshot(root), docs[0], docs[1],
                          sha_bytes(raw[0]), sha_bytes(raw[1]), paths)
    out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + '\n', encoding='utf-8')
    print('T3UVW SOURCE-CUSTODY REEXECUTION PASS: TWO ORIGINAL T3OPQ RUNS; DUAL REPLAY ONLY; NO NATIVE PROMOTION')
    print('source hash', result['V_original_gate']['comparison']['canonical_sha256'])
    print('report', out)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (GateError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'T3UVW FAIL CLOSED: {exc}', file=sys.stderr)
        sys.exit(3)
