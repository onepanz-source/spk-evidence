#!/usr/bin/env python3
"""SPK BV v2v-v2x cumulative source-bound ACK/consumer queue discrimination.

python -m search.spk_bv_v2vwx_queue_precedence_cumulative \
  --v2stu /tmp/spk-bv-v2stu-concurrent-cumulative.json \
  --out /tmp/spk-bv-v2vwx-queue-precedence-cumulative.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2stu_concurrent_cumulative import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.queue_precedence_pressure_integration_v2vwx import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v2stu_concurrent_cumulative.py': '820a17496f1d7eea1095fabd75146b5cc5e0838419448374642e106bcc77bd1d',
    'spk_backvalidation_v2/derived_actor_queue_fairness_v2v.py': '322f1cb33304124cb3f7dc6d7dbd614f090e74b30978436405979764c49173ca',
    'spk_bv_research/queue_precedence_pressure_integration_v2vwx.py': 'f7c7b47fd20080141603835b82bdb7cc233b36b976895a944c8cb03238daebb4',
}


def read_predecessor(path: Path, root: Path):
    path = path.absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError('v2v-v2x unsafe or missing signed v2stu predecessor')
    resolved = path.resolve(strict=True)
    if resolved == root or root in resolved.parents or not 0 < resolved.stat().st_size <= 8_000_000:
        raise ValueError('v2v-v2x repository-owned or oversized predecessor')
    return path.read_bytes()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v2stu', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        sources = []
        for relative, digest in CODE_SHA.items():
            path = root / relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v2v-v2x source unavailable or unsafe: ' + relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise ValueError('v2v-v2x source or inherited code pin drift: ' + relative)
            sources.append((path, raw))
        previous_raw = read_predecessor(args.v2stu, root)
        if sha256(previous_raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v2v-v2x signed v2stu report SHA drift')
        output = safe_output(args.out, root, (args.v2stu.absolute(),))
        previous = json.loads(previous_raw)
        result = None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            result = experiment(previous, previous_raw, root=root,
                fixture_fn=fixture, native_executor=execute_live_v0e,
                plan_type=LiveBVPlanV0e)
        report = build_report(previous, previous_raw, result)
        if args.v2stu.read_bytes() != previous_raw or any(
                path.read_bytes() != raw for path, raw in sources):
            raise ValueError('v2v-v2x predecessor or derived executable changed during gate')
        with output.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'new_native_runs': report['new_native_runs'],
            'new_derived_policy_runs': report['new_derived_policy_runs'],
            'new_derived_causal_intervention_runs':
                report['new_derived_causal_intervention_runs'],
            'ready_queue_collision_cells': report['ready_queue_collision_cells'],
            'distinct_ACK_journal_policy_cells':
                report['distinct_ACK_journal_policy_cells'],
            'bounded_turn_limit_activated_cells':
                report['bounded_turn_limit_activated_cells'],
            'two_queue_policy_totals': report['two_queue_policy_totals'],
            'causal_intervention_totals': report['causal_intervention_totals'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, AssertionError,
            SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v2v-v2x REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
