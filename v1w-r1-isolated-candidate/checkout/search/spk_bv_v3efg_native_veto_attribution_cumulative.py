#!/usr/bin/env python3
"""BV v3e-v3g source native veto guard factorial / ACK wait overlap.

python -m search.spk_bv_v3efg_native_veto_attribution_cumulative \
  --v3bcd /tmp/spk-bv-v3bcd-episode-wait-prefix.json \
  --out /tmp/spk-bv-v3efg-native-veto-attribution.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3bcd_episode_wait_prefix_cumulative import (
    CODE_SHA as INHERITED_SHA, read_predecessor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_veto_attribution_v3efg import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3bcd_episode_wait_prefix_cumulative.py':
        'b0b4b47c1f3e71892daebc3bc76308a445074aa589bfb55ee331205bad78b102',
    'spk_backvalidation_v2/derived_native_veto_wait_audit_v3e.py':
        'a3b0d36f7730bb39b5a555623a11bdbcf35f96b979cf408003aba63840cea3e1',
    'spk_bv_research/native_veto_attribution_v3efg.py':
        '376c16b6d011270a773d4f456b5e7106b28f842b859817f13aa703e23329513d',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3bcd', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        sources = []
        for relative, digest in CODE_SHA.items():
            path = root / relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v3e-v3g pinned source unavailable or unsafe: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise ValueError('v3e-v3g source or inherited SHA drift: '+relative)
            sources.append((path, raw))
        raw = read_predecessor(args.v3bcd, root)
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3e-v3g predecessor SHA mismatch')
        output = safe_output(args.out, root, (args.v3bcd.absolute(),))
        previous = json.loads(raw)
        result = None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            result = experiment(previous, raw, root=root,
                fixture_fn=fixture, native_executor=execute_live_v0e,
                plan_type=LiveBVPlanV0e)
        report = build_report(previous, raw, result)
        if args.v3bcd.read_bytes() != raw or any(
                path.read_bytes() != old for path, old in sources):
            raise ValueError('v3e-v3g signed source changed during matrix execution')
        with output.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'native_runs': report['new_native_runs'],
            'factorial_derived_runs': report['new_derived_policy_runs'],
            'causal_null_runs': report['new_null_runs'],
            'tail_off_runs': report['new_tail_off_runs'],
            'factorial_contrasts': report['factorial_contrasts'],
            'tail_disabled_observations': report['tail_disabled_observations'],
            'guard_max_ACK_wait_ticks': {
                name: policies['bounded-turns']['ACK_wait_max_ticks']
                for name, policies in (report['guard_factorial_totals'] or {}).items()},
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3e-v3g REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
