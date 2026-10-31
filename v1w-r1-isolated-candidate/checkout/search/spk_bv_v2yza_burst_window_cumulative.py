#!/usr/bin/env python3
"""SPK BV v2y–v3a: source-backed two-turn queue pressure and ACK-window gate.

python -m search.spk_bv_v2yza_burst_window_cumulative \
  --v2vwx /tmp/spk-bv-v2vwx-queue-precedence-cumulative.json \
  --out /tmp/spk-bv-v2yza-burst-window-cumulative.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2vwx_queue_precedence_cumulative import (
    CODE_SHA as INHERITED_SHA, read_predecessor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.burst_window_cumulative_v2yza import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v2vwx_queue_precedence_cumulative.py':
        '8fe6c848206bf046bc8c0fd01ba5c5ec401ef581b2689aee09358dc4b4a15bb3',
    'spk_backvalidation_v2/derived_actor_burst_window_v2y.py':
        '532bb462f2a4d3f75fc58e6087fbfcd271773f9bb0a700eae989aea9eaa3c7e8',
    'spk_bv_research/burst_window_cumulative_v2yza.py':
        '22e06f36b160a36cf4eee8e0b2fdbf5466c1aa73abf72aec5e09f3de1eb1d7b1',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v2vwx', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        sources = []
        for relative, digest in CODE_SHA.items():
            path = root / relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v2y-v3a source unsafe or unavailable: ' + relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise ValueError('v2y-v3a source or inherited pin drift: ' + relative)
            sources.append((path, raw))
        previous_raw = read_predecessor(args.v2vwx, root)
        if sha256(previous_raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v2y-v3a signed v2vwx predecessor SHA drift')
        output = safe_output(args.out, root, (args.v2vwx.absolute(),))
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
        if args.v2vwx.read_bytes() != previous_raw or any(
                path.read_bytes() != raw for path, raw in sources):
            raise ValueError('v2y-v3a signed predecessor or executable changed during replay')
        with output.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'new_native_runs': report['new_native_runs'],
            'new_derived_policy_runs': report['new_derived_policy_runs'],
            'new_derived_ablation_runs': report['new_derived_ablation_runs'],
            'source_queue_collision_cells': report['source_queue_collision_cells'],
            'unbounded_two_turn_streak_cells': report['unbounded_two_turn_streak_cells'],
            'bounded_window_activated_cells': report['bounded_window_activated_cells'],
            'bounded_window_activated_ticks': report['bounded_window_activated_ticks'],
            'bounded_overrun_cells': report['bounded_overrun_cells'],
            'ACK_journal_bound_intervention_cells':
                report['ACK_journal_bound_intervention_cells'],
            'conditional_window_totals': report['conditional_window_totals'],
            'causal_pressure_ablations': report['causal_pressure_ablations'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v2y-v3a REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
