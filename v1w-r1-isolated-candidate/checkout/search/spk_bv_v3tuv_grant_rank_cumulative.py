#!/usr/bin/env python3
"""BV v3t-v3v finite FIFO grant-rank experiment; frozen native is unchanged.

python -m search.spk_bv_v3tuv_grant_rank_cumulative \
  --v3qrs /tmp/spk-bv-v3qrs-actor-service-gap.json \
  --out /tmp/spk-bv-v3tuv-grant-rank.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3qrs_actor_service_gap_cumulative import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.grant_rank_integration_v3tuv import (
    PREDECESSOR_SHA, build_report, experiment, validate_v3qrs,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected


CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3qrs_actor_service_gap_cumulative.py':
        '4c7fe064df512cde30bd58ba8b839b0d5b224542589d7c89c505a564d91e6cf6',
    'spk_backvalidation_v2/derived_grant_rank_certificate_v3t.py':
        '162fe4efc440a8f6a8a449d61c2c6e292a111d8c3c7449df6d73b25bd2122b44',
    'spk_bv_research/grant_rank_integration_v3tuv.py':
        '6120585368d245991537fbb3a626b67c272be3864ba525401c64d4451cc309c8',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3qrs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for relative, expected in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise ValueError('v3t-v3v pinned source unsafe or unavailable: '+relative)
            source = path.read_bytes()
            if sha256(source).hexdigest() != expected:
                raise ValueError('v3t-v3v inherited/new SHA source drift: '+relative)
            pinned.append((path, source))
        predecessor = args.v3qrs.resolve(strict=True)
        if args.v3qrs.is_symlink() or not predecessor.is_file():
            raise ValueError('v3t-v3v signed predecessor path unsafe')
        raw = predecessor.read_bytes()
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise ValueError('v3t-v3v signed predecessor SHA mismatch')
        prev = json.loads(raw)
        validate_v3qrs(prev, raw)
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
            raise ValueError('v3t-v3v source/predecessor changed during replay')
        with output.open('xb') as stream:
            stream.write(canon(report))
        totals = report['grant_rank_totals'] or {}
        print(json.dumps({
            'status': report['status'],
            'original_native_runs': report['new_original_native_runs'],
            'derived_rank_runs': report['new_derived_rank_runs'],
            'causal_null_runs': report['new_causal_null_runs'],
            'source_grant_ticks': totals.get('source_native_grant_ticks', 0),
            'exact_rank_ACKs': totals.get('served_exact_rank_certificates', 0),
            'censored_records': totals.get('censored_rank_below_threshold_certificates', 0),
            'contexts_with_waiting_peer': totals.get(
                'context_with_peer_waiting_and_global_grant', 0),
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, NativeForkError, LiveBVRejected) as exc:
        print('SPK BV v3t-v3v REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
