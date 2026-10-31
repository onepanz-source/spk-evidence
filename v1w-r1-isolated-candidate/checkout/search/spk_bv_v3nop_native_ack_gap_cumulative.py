#!/usr/bin/env python3
"""BV v3n-v3p exact source-ready ACK wait-gap cumulative research.

python -m search.spk_bv_v3nop_native_ack_gap_cumulative \
  --v3klm /tmp/spk-bv-v3klm-native-ack-opportunity.json \
  --out /tmp/spk-bv-v3nop-native-ack-gap.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3klm_native_ack_opportunity_cumulative import (
    CODE_SHA as INHERITED_SHA,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_gap_integration_v3nop import (
    PREDECESSOR_SHA, build_report, experiment, validate_v3klm,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3klm_native_ack_opportunity_cumulative.py':
        '505ca3a28dabdea3695a36e3e8b6be5246cd88d0ce99a1f953ce6566d3d4f427',
    'spk_backvalidation_v2/derived_ack_wait_gap_v3n.py':
        '321c0fe0b8792c30bd604cd7bd43b573754f18ea958b4527d561e5d8687fa8f4',
    'spk_bv_research/native_ack_gap_integration_v3nop.py':
        'b82c80ee53eaab3957ba92082977758a0951d5dbb14d15722d61d8c590c7b55b',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3klm', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for relative, expected in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v3n-v3p source unsafe or unavailable: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v3n-v3p inherited/new SHA source drift: '+relative)
            pinned.append((path, raw))
        predecessor = args.v3klm.resolve(strict=True)
        if args.v3klm.is_symlink() or not predecessor.is_file():
            raise ValueError('v3n-v3p signed predecessor path unsafe')
        raw = predecessor.read_bytes()
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3n-v3p signed predecessor SHA mismatch')
        prev = json.loads(raw)
        validate_v3klm(prev, raw)
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
            raise ValueError('v3n-v3p signed precursor or source changed during replay')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'original_native_runs': report['new_original_native_runs'],
            'derived_ready_gap_runs': report['new_derived_gap_runs'],
            'causal_null_runs': report['new_causal_null_runs'],
            'native_ready_miss_thresholds':
                report['missed_ready_tick_threshold_contexts'],
            'new_quota_inversions': len(report['nonmonotone_new_quota_witnesses'] or []),
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3n-v3p REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
