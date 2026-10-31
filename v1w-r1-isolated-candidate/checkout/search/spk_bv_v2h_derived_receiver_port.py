#!/usr/bin/env python3
"""BV v2h: pinned native/derived actor-local judgment and mailbox gate.

Run from the SPK repository root. The v2g predecessor input and the output
must be OUTSIDE the repository. Fails closed on source or evidence drift.
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.receiver_port_integration_v2h import (
    build_report, experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError

EXPECTED_V2G='eb108df313fb705f6a6b54a08edfa10abc0df170bf98f45249f1068243d703f0'
CODE_SHA={
    'spk_backvalidation_v2/derived_receiver_port_v2h.py':
        '04f03c9977afc770d7c82c5a11f5474a40319cc0bcee06594171cc4db1f0a7a8',
    'spk_bv_research/receiver_port_integration_v2h.py':
        '1f4690ca76c591fe1e20819805cd5c11bebad56bd0affa3a50095af05c8ba030',
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2g',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        files=[]
        for rel,expected in CODE_SHA.items():
            path=root/rel
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('unsafe or missing v2h code: '+rel)
            raw=path.read_bytes()
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('v2h code SHA mismatch: '+rel)
            files.append((path,raw))
        predecessor,identity=safe_input(args.v2g,root)
        if sha256(predecessor).hexdigest()!=EXPECTED_V2G:
            raise ValueError('v2g signed-off report SHA mismatch')
        out=safe_output(args.out,root,(args.v2g.absolute(),))
        v2g=json.loads(predecessor)
        results=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e,LiveBVPlanV0e,
            )
            results=experiment(v2g,predecessor,root=root,
                               fixture_fn=fixture,native_executor=execute_live_v0e,
                               plan_type=LiveBVPlanV0e)
        report=build_report(v2g,predecessor,results)
        if args.v2g.read_bytes()!=predecessor:
            raise ValueError('v2g report changed during native gate')
        if any(path.read_bytes()!=raw for path,raw in files):
            raise ValueError('v2h source changed during native gate')
        with out.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'native_runs':report['new_native_original_runs'],
            'derived_normal_runs':report['new_derived_normal_runs'],
            'derived_fault_runs':report['new_derived_fault_runs'],
            'negative_judgments':report['negative_real_actor_judgments'],
            'actor_semantic_totals':report['actor_semantic_totals'],
            'output':str(out),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError) as exc:
        print('SPK BV v2h REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
