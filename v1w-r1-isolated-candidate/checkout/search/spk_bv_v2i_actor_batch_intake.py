#!/usr/bin/env python3
"""BV v2i derived actor-batch intake, pinned v2h predecessor, fail-closed gate.

Usage: python -m search.spk_bv_v2i_actor_batch_intake \
  --v2h /tmp/spk-bv-v2h-derived-actor-feedback.json \
  --out /tmp/spk-bv-v2i-actor-batch-intake.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_intake_integration_v2i import (
    V2H_SHA, build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError

CODE_SHA = {
    'spk_backvalidation_v2/derived_receiver_port_v2h.py':
        '04f03c9977afc770d7c82c5a11f5474a40319cc0bcee06594171cc4db1f0a7a8',
    'spk_bv_research/receiver_port_integration_v2h.py':
        '1f4690ca76c591fe1e20819805cd5c11bebad56bd0affa3a50095af05c8ba030',
    'spk_backvalidation_v2/derived_actor_intake_v2i.py':
        '578ac2344d6dcd8452192e3f2bdb1b6257d2414c5cbdd02ab36524c216aaa8c0',
    'spk_bv_research/actor_intake_integration_v2i.py':
        '1fdc38a1e30e8af2681e9ca3ab9f87fc4488ba3730f36d9ed6eab82ee95f5f8f',
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2h',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        files=[]
        for rel, expected in CODE_SHA.items():
            path=root/rel
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('unsafe or missing v2i code: '+rel)
            raw=path.read_bytes()
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('v2i code SHA mismatch: '+rel)
            files.append((path,raw))
        predecessor,_=safe_input(args.v2h,root)
        if sha256(predecessor).hexdigest()!=V2H_SHA:
            raise ValueError('v2h signed-off report SHA mismatch')
        out=safe_output(args.out,root,(args.v2h.absolute(),))
        v2h=json.loads(predecessor)
        results=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e, LiveBVPlanV0e,
            )
            results=experiment(v2h,predecessor,root=root,
                fixture_fn=fixture,native_executor=execute_live_v0e,
                plan_type=LiveBVPlanV0e)
        report=build_report(v2h,predecessor,results)
        if args.v2h.read_bytes()!=predecessor or any(
                path.read_bytes()!=raw for path,raw in files):
            raise ValueError('source/evidence changed during v2i execution')
        with out.open('xb') as f:
            f.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'original_native_runs':report['new_original_native_runs'],
            'derived_normal_runs':report['new_derived_normal_runs'],
            'derived_loss_runs':report['new_derived_loss_runs'],
            'derived_pressure_runs':report['new_derived_receipt_pressure_runs'],
            'native_parity_cells':report['full_native_result_parity_cells'],
            'actor_intake_totals':report['actor_intake_totals'],
            'negative_fixture':report['negative_native_fixture'],
            'output':str(out),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError) as exc:
        print('SPK BV v2i REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
