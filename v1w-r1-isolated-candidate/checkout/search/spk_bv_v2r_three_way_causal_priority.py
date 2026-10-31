#!/usr/bin/env python3
"""BV v2r: causal native/ACK/paid-consumer counterfactual discrimination.

python -m search.spk_bv_v2r_three_way_causal_priority \
  --v2q /tmp/spk-bv-v2q-independent-consumer-resource.json \
  --out /tmp/spk-bv-v2r-three-way-causal-priority.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2q_independent_consumer_resource import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.three_way_causal_priority_integration_v2r import (
    PREDECESSOR_SHA,experiment,build_report,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA={
    **INHERITED_SHA,
    'search/spk_bv_v2q_independent_consumer_resource.py':
        '9bb2e494c253e0ed4cc5bebf097ef5c3e5de18ffb90eb6197f45acfe8c03907d',
    'spk_bv_research/three_way_causal_priority_integration_v2r.py':
        'ef856b9057e23a64046bdb5e0b842ad25d75dd6d97bac8329b40a5a8f7e19fb4',
}


def read_signed_v2q_report(path:Path,root:Path):
    path=path.absolute()
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
            or not path.is_file()):
        raise ValueError('v2r unsafe or missing signed v2q predecessor')
    resolved=path.resolve(strict=True)
    if (resolved==root or root in resolved.parents or
            not 0<resolved.stat().st_size<=8_000_000):
        raise ValueError('v2r repository-owned or oversized signed v2q matrix')
    return path.read_bytes()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2q',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnessed=[]
        for relative,expected in CODE_SHA.items():
            path=root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('v2r missing or unsafe pinned source: '+relative)
            before=path.read_bytes()
            if sha256(before).hexdigest()!=expected:
                raise ValueError('v2r inherited or current code SHA drift: '+relative)
            witnessed.append((path,before))
        raw=read_signed_v2q_report(args.v2q,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2r canonical v2q predecessor digest changed')
        output=safe_output(args.out,root,(args.v2q.absolute(),))
        previous=json.loads(raw)
        result=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e,LiveBVPlanV0e,
            )
            result=experiment(previous,raw,root=root,fixture_fn=fixture,
                              native_executor=execute_live_v0e,
                              plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        if args.v2q.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnessed):
            raise ValueError('v2r signed predecessor or inherited code mutated')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'native_original_runs':report['new_native_runs'],
            'derived_four_guard_runs':report['new_derived_four_guard_runs'],
            'derived_causal_intervention_runs':
                report['new_derived_causal_intervention_runs'],
            'bounded_horizon_discrimination':report['bounded_horizon_discrimination'],
            'causal_priority_resource_totals':report['causal_priority_resource_totals'],
            'causal_resource_intervention_totals':
                report['causal_resource_intervention_totals'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError,LiveBVRejected) as exc:
        print('SPK BV v2r REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
