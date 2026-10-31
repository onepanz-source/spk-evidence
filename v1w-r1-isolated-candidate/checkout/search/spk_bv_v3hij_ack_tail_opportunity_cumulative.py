#!/usr/bin/env python3
"""BV v3h–v3j source-paid finite ACK tail/cutover capacity gate.

python -m search.spk_bv_v3hij_ack_tail_opportunity_cumulative \
  --v3efg /tmp/spk-bv-v3efg-native-veto-attribution.json \
  --out /tmp/spk-bv-v3hij-ack-tail-opportunity.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3efg_native_veto_attribution_cumulative import (
    CODE_SHA as INHERITED_SHA, read_predecessor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.ack_tail_opportunity_integration_v3hij import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3efg_native_veto_attribution_cumulative.py':
        'deec4815c3e65e7e0b89aba4937b0f50f211bed0c7b76d1c32aca8c9e9b22ccb',
    'spk_backvalidation_v2/derived_ack_tail_envelope_v3h.py':
        '8214df58919bc7efab1d695cbd7d15e114e04b1058ccec02d4657f9221d2d723',
    'spk_bv_research/ack_tail_opportunity_integration_v3hij.py':
        '92e9d40225506b8e5c359b5c60022046a96a4efbab0035d3e3cb87071f056fc8',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3efg', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for relative, expected in CODE_SHA.items():
            path = root / relative
            if (not path.is_file() or path.is_symlink() or
                    path.resolve(strict=True) != path):
                raise ValueError('v3h-v3j source unsafe or unavailable: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v3h-v3j inherited/new SHA source drift: '+relative)
            pinned.append((path, raw))
        raw = read_predecessor(args.v3efg, root)
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3h-v3j signed v3efg predecessor SHA mismatch')
        output = safe_output(args.out, root, (args.v3efg.absolute(),))
        prev = json.loads(raw)
        result = None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            result = experiment(prev, raw, root=root, fixture_fn=fixture,
                native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(prev, raw, result)
        if args.v3efg.read_bytes() != raw or any(
                path.read_bytes() != old for path, old in pinned):
            raise ValueError('v3h-v3j source or predecessor changed during gate')
        with output.open('xb') as f:
            f.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'native_runs': report['new_native_runs'],
            'derived_tail_budget_runs': report['new_derived_budget_runs'],
            'causal_null_runs': report['new_causal_null_runs'],
            'source_ACK_prefix_comparisons':
                report['total_source_tail_prefix_comparisons'],
            'capacity_monotonicity_comparisons':
                report['total_source_capacity_monotonicity_comparisons'],
            'exact_finite_tail_cutovers': report['exact_finite_cutovers'],
            'quota_one': report['per_global_ACK_tick_quota_totals']['1']
                if result else None,
            'quota_two': report['per_global_ACK_tick_quota_totals']['2']
                if result else None,
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3h-v3j REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
