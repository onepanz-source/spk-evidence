#!/usr/bin/env python3
"""BV v2g derived native callsite seam; strict exact-output/source custody."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from hashlib import sha256
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_fork_differential_v2g import build_report, experiment
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError

EXPECTED_V2F='1d5999b8ac1727110a9b58f3c854d1bf524f61e016d13ae25ef07a78b4d0aa65'
EXPECTED_V2E='219cce4eadd862bc09d0f4d8f385057fa8e3db3084a59c5f1b2274a485aaa916'
# Generated source digests are stamped into the release after tests.
CODE_SHA={
 'spk_backvalidation_v2/derived_native_fork_v2g.py': '8942cf17a9b4c96ce06cf34e093146e7e706532610475a20309473de380d0116',
 'spk_bv_research/native_fork_differential_v2g.py': 'fd9a105c3194608be0892a7dcbca0e70abf864ea063ffbcbcda9124552a32b7e',
}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--v2f',type=Path,required=True)
    p.add_argument('--v2e',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        pinned_code=[]
        for rel,expected in CODE_SHA.items():
            fp=root/rel
            if not fp.is_file() or fp.is_symlink() or fp.resolve(strict=True)!=fp:
                raise ValueError('unsafe v2g module path: '+rel)
            raw=fp.read_bytes()
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('v2g source digest mismatch: '+rel)
            pinned_code.append(raw)
        pathlist=(args.v2f,args.v2e)
        docs=[safe_input(p,root) for p in pathlist]
        if docs[0][1]==docs[1][1]:raise ValueError('predecessor alias')
        output=safe_output(args.out,root,tuple(p.absolute() for p in pathlist))
        raws=[x for x,_ in docs]
        for raw,expected in zip(raws,(EXPECTED_V2F,EXPECTED_V2E)):
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('predecessor digest mismatch')
        v2f,v2e=map(json.loads,raws)
        results=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
            results=experiment(v2f,raws[0],v2e,raws[1],root=root,
                               fixture_fn=fixture,native_executor=execute_live_v0e,
                               plan_type=LiveBVPlanV0e)
        report=build_report(v2f,raws[0],v2e,raws[1],results)
        if any(p.read_bytes()!=raw for p,raw in zip(pathlist,raws)):
            raise ValueError('predecessor modified during experiment')
        if any((root/rel).read_bytes()!=raw for rel,raw in zip(CODE_SHA,pinned_code)):
            raise ValueError('v2g source changed during experiment')
        with output.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'original_runs':report['new_frozen_original_runs'],
                          'derived_runs':report['new_in_memory_derived_executor_runs'],
                          'verified_callsite_events':report['callsite_counts'],
                          'output':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError) as e:
        print('SPK BV v2g REJECTED: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
