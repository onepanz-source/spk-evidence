#!/usr/bin/env python3
"""BV v3q-v3s actor-owned ACK progress and native-horizon censoring.

python -m search.spk_bv_v3qrs_actor_service_gap_cumulative \
  --v3nop /tmp/spk-bv-v3nop-native-ack-gap.json \
  --out /tmp/spk-bv-v3qrs-actor-service-gap.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3nop_native_ack_gap_cumulative import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_service_gap_integration_v3qrs import (
    PREDECESSOR_SHA, build_report, experiment, validate_v3nop,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3nop_native_ack_gap_cumulative.py':
        '66dc98a84829b912a218ee0dd207485e275dab11a8c07e17b26d4b0d81f3cc8e',
    'spk_backvalidation_v2/derived_actor_service_gap_v3q.py':
        'd30f32d200d4c8293fea191fe7e6cce77bd8b01175139397a09e9855743a883c',
    'spk_bv_research/actor_service_gap_integration_v3qrs.py':
        '5a90cf0663557141f308517f4a19c8d580b42be4327eccbba0791766146f1f3d',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3nop', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for relative, expected in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v3q-v3s source unsafe or unavailable: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v3q-v3s inherited/new SHA source drift: '+relative)
            pinned.append((path, raw))
        predecessor = args.v3nop.resolve(strict=True)
        if args.v3nop.is_symlink() or not predecessor.is_file():
            raise ValueError('v3q-v3s signed predecessor path unsafe')
        raw = predecessor.read_bytes()
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3q-v3s signed predecessor SHA mismatch')
        prev = json.loads(raw)
        validate_v3nop(prev, raw)
        output = safe_output(args.out, root, (predecessor,))
        result = None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            result = experiment(prev, raw, root=root, fixture_fn=fixture,
                native_executor=execute_live_v0e, plan_type=LiveBVPlanV0e)
        report = build_report(prev, raw, result)
        if predecessor.read_bytes() != raw or any(
                path.read_bytes() != old for path, old in pinned):
            raise ValueError('v3q-v3s signed predecessor/source changed during replay')
        with output.open('xb') as stream:
            stream.write(canon(report))
        totals = report['actor_progress_totals'] or {}
        print(json.dumps({
            'status': report['status'],
            'original_native_runs': report['new_original_native_runs'],
            'derived_actor_runs': report['new_derived_actor_runs'],
            'causal_null_runs': report['new_causal_null_runs'],
            'global_grants_with_waiting_peer_ticks':
                totals.get('global_grant_with_unserved_actor_ticks', 0),
            'contexts_with_waiting_peer':
                totals.get('contexts_with_global_progress_peer_miss', 0),
            'max_actor_ready_miss_streak':
                totals.get('maximum_actor_ready_miss_streak', 0),
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3q-v3s REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
