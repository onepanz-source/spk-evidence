#!/usr/bin/env python3
"""BV v3b–v3d source episodes: ACK wait, prefix and native veto differential.

python -m search.spk_bv_v3bcd_episode_wait_prefix_cumulative \
  --v2yza /tmp/spk-bv-v2yza-burst-window-cumulative.json \
  --out /tmp/spk-bv-v3bcd-episode-wait-prefix.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2yza_burst_window_cumulative import (
    CODE_SHA as INHERITED_SHA, read_predecessor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.episode_wait_prefix_integration_v3bcd import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v2yza_burst_window_cumulative.py':
        '9d034972be0b3698d5fcb96804c12a1f69ed9d596ab42c008b3b2ea883fa653a',
    'spk_backvalidation_v2/derived_ack_wait_audit_v3b.py':
        'a4c3e26b0e290a65a27abe95f46f9442bfd4b84eaeb29fa0b27ebc01f987e7d3',
    'spk_bv_research/episode_wait_prefix_integration_v3bcd.py':
        'e762299efd5b837a1f3568a4cfaf7122dc7456e7a6b8452a01054c897a90fbd3',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v2yza', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        sources = []
        for relative, digest in CODE_SHA.items():
            path = root / relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v3b-v3d source unsafe or unavailable: ' + relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise ValueError('v3b-v3d source or inherited SHA pin drift: ' + relative)
            sources.append((path, raw))
        previous_raw = read_predecessor(args.v2yza, root)
        if sha256(previous_raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3b-v3d v2yza predecessor SHA mismatch')
        output = safe_output(args.out, root, (args.v2yza.absolute(),))
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
        if args.v2yza.read_bytes() != previous_raw or any(
                path.read_bytes() != raw for path, raw in sources):
            raise ValueError('v3b-v3d source executable/predecessor changed during gate')
        with output.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'new_original_native_runs': report['new_original_native_runs'],
            'new_derived_queue_runs': report['new_derived_queue_runs'],
            'new_derived_null_runs': report['new_derived_null_runs'],
            'prefix_causal_nonanticipation': report['prefix_causal_nonanticipation'],
            'null_guard_unbounded_max_ACK_wait_ticks':
                report['null_guard_unbounded_max_ACK_wait_ticks'],
            'null_guard_bounded_max_ACK_wait_ticks':
                report['null_guard_bounded_max_ACK_wait_ticks'],
            'strict_native_veto_max_ACK_wait_ticks':
                report['strict_native_veto_max_ACK_wait_ticks'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3b-v3d REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
