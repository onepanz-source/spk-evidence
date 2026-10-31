#!/usr/bin/env python3
"""SPK BV v2s-v2u cumulative true derived pre-forward paid consumer gate.

python -m search.spk_bv_v2stu_concurrent_cumulative \
  --v2r /tmp/spk-bv-v2r-three-way-causal-priority.json \
  --out /tmp/spk-bv-v2stu-concurrent-cumulative.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2r_three_way_causal_priority import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.concurrent_consumer_cumulative_v2stu import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v2r_three_way_causal_priority.py':
        '3fd094a22b92c112947d616fdc6a998dce962a6fb3f8df644c29bd1aa40ab438',
    'spk_backvalidation_v2/derived_concurrent_consumer_v2s.py':
        '67d6e3dcd40beeaa8991102799ebc345a2ded2dbd0adb342a26ed88de6223f79',
    'spk_bv_research/concurrent_consumer_cumulative_v2stu.py':
        'e52acccef2e348e1d9bffbd4e78cba82269316ab3eed96fba4e5a452d49b0bdb',
}


def read_signed_v2r(path: Path, root: Path):
    path = path.absolute()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or not path.is_file():
        raise ValueError('v2s-v2u missing or unsafe signed v2r predecessor')
    resolved = path.resolve(strict=True)
    if resolved == root or root in resolved.parents or not 0 < resolved.stat().st_size <= 8_000_000:
        raise ValueError('v2s-v2u repository-owned or oversized predecessor')
    return path.read_bytes()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v2r', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        before = []
        for relative, expected in CODE_SHA.items():
            path = root / relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v2s-v2u missing/unsafe source ' + relative)
            data = path.read_bytes()
            if sha256(data).hexdigest() != expected:
                raise ValueError('v2s-v2u source or predecessor SHA drift ' + relative)
            before.append((path, data))
        signed = read_signed_v2r(args.v2r, root)
        if sha256(signed).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v2s-v2u signed v2r report SHA drift')
        output = safe_output(args.out, root, (args.v2r.absolute(),))
        previous = json.loads(signed)
        result = None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            result = experiment(previous, signed, root=root, fixture_fn=fixture,
                                native_executor=execute_live_v0e,
                                plan_type=LiveBVPlanV0e)
        report = build_report(previous, signed, result)
        if args.v2r.read_bytes() != signed or any(p.read_bytes() != old for p, old in before):
            raise ValueError('v2s-v2u predecessor or derived source mutated during gate')
        with output.open('xb') as handle:
            handle.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'native_original_runs': report['new_native_runs'],
            'derived_guard_runs': report['new_derived_three_way_guard_runs'],
            'derived_intervention_runs': report['new_derived_causal_intervention_runs'],
            'causal_consumer_forward_witness_cells': report['causal_consumer_forward_witness_cells'],
            'negative_fixture': report['negative_fixture'],
            'bounded_horizon': report['bounded_horizon_witness'],
            'concurrent_totals': report['three_way_paid_resource_totals'],
            'intervention_totals': report['intervention_totals'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, AssertionError,
            SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v2s-v2u REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
