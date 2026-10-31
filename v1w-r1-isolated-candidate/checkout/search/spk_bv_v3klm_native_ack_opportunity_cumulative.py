#!/usr/bin/env python3
"""BV v3k-v3m source-native conditional ACK service opportunity research.

python -m search.spk_bv_v3klm_native_ack_opportunity_cumulative \
  --v3hij /tmp/spk-bv-v3hij-ack-tail-opportunity.json \
  --out /tmp/spk-bv-v3klm-native-ack-opportunity.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3hij_ack_tail_opportunity_cumulative import (
    CODE_SHA as INHERITED_SHA, read_predecessor,
)
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_opportunity_integration_v3klm import (
    PREDECESSOR_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3hij_ack_tail_opportunity_cumulative.py':
        '4786d2f202d968d0ad6e92ffbcde665af2e7308d7939452c92d97d281d19fe6e',
    'spk_backvalidation_v2/derived_native_opportunity_certificate_v3k.py':
        'b5747d46259d6f24f10657367fd9d469644d421f335850136e854ff53af19930',
    'spk_bv_research/native_ack_opportunity_integration_v3klm.py':
        'ef19c5e87d8b0bc175902f86c9588eab8a1bb25d04816bde12212411da3575c7',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3hij', type=Path, required=True)
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
                raise ValueError('v3k-v3m source unsafe or unavailable: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v3k-v3m inherited/new SHA source drift: '+relative)
            pinned.append((path, raw))
        raw = read_predecessor(args.v3hij, root)
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3k-v3m signed v3hij predecessor SHA mismatch')
        output = safe_output(args.out, root, (args.v3hij.absolute(),))
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
        if args.v3hij.read_bytes() != raw or any(
                path.read_bytes() != old for path, old in pinned):
            raise ValueError('v3k-v3m pinned source changed during execution')
        with output.open('xb') as f:
            f.write(canon(report))
        print(json.dumps({
            'status': report['status'],
            'native_runs': report['new_original_native_runs'],
            'derived_queue_capacity_runs': report['new_derived_policy_runs'],
            'causal_null_runs': report['new_causal_null_runs'],
            'conditionally_feasible_source_opportunities':
                report['sufficient_source_opportunities'],
            'weak_no_veto_opportunities_without_grant':
                report['unsafe_weak_no_veto_opportunities'],
            'policy_and_global_quota_contrasts':
                report['policy_and_global_resource_contrasts'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3k-v3m REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
