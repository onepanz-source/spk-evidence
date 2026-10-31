#!/usr/bin/env python3
"""BV v2o: source-pinned native causal work shield and actor ACK fairness.

Usage: python -m search.spk_bv_v2o_native_causal_admission \
  --v2n /tmp/spk-bv-v2n-actor-forward-fairness.json \
  --out /tmp/spk-bv-v2o-native-causal-admission.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2n_actor_forward_fairness import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_causal_admission_integration_v2o import (
    PREDECESSOR_SHA,experiment,build_report,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA={
    **INHERITED_SHA,
    'search/spk_bv_v2n_actor_forward_fairness.py':
        '2be1c0f495b4348d9e6479367503e21b72ad144a119404d1006d38be26d4ad1b',
    'spk_backvalidation_v2/derived_causal_admission_v2o.py':
        '4dd8bfab300508657afa4ab71c6dd751fe62889d9f72263f0e0ff9ac8160b080',
    'spk_bv_research/native_causal_admission_integration_v2o.py':
        '8a928ed5d31d34b28db72e80f346b42984afacb99d7c9f5d4be1aa687f71ab86',
}


def read_signed_v2n_report(path:Path,root:Path):
    """Large signed v2n matrix: preserve v1b path policy, raise byte cap only."""
    path=path.absolute()
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
            or not path.is_file()):
        raise ValueError('v2o unsafe or missing v2n predecessor')
    resolved=path.resolve(strict=True)
    if (resolved==root or root in resolved.parents or
            not 0<resolved.stat().st_size<=8_000_000):
        raise ValueError('v2o repository-owned or oversized signed v2n report')
    return path.read_bytes()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2n',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnessed=[]
        for relative,expected in CODE_SHA.items():
            path=root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('missing or unsafe v2o source: '+relative)
            before=path.read_bytes()
            if sha256(before).hexdigest()!=expected:
                raise ValueError('v2o inherited/current source SHA drift: '+relative)
            witnessed.append((path,before))
        raw=read_signed_v2n_report(args.v2n,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2o signed v2n report SHA drift')
        output=safe_output(args.out,root,(args.v2n.absolute(),))
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
        if args.v2n.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnessed):
            raise ValueError('v2o inherited code or signed report mutated in replay')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'original_native_runs':report['new_original_native_runs'],
            'derived_causal_admission_runs':report['new_derived_causal_admission_runs'],
            'derived_causal_null_runs':report['new_derived_causal_null_runs'],
            'bounded_horizon_discrimination':report['bounded_horizon_discrimination'],
            'causal_admission_totals':report['causal_admission_totals'],
            'causal_null_full_native_parity':report['causal_null_full_native_parity'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError,LiveBVRejected) as exc:
        print('SPK BV v2o REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
