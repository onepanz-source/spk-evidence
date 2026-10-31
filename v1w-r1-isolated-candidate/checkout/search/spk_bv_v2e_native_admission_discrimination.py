#!/usr/bin/env python3
"""Run predeclared v2e native admission matrix, read-only on frozen scheduler.

--contract-only generates NO new native evidence and no source-custody claim.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from hashlib import sha256

from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.off_on_v0t import PINNED
from spk_bv_research.coincident_admission_discrimination_v2e import analyze,native_experiment

EXPECTED_V2E_RESEARCH_SHA256='14e78098b5eff792ce816b32acb04999b2b2c66ead1bdf4884466c33871fd71c'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--v2d',type=Path,required=True)
    p.add_argument('--v0w',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        research_path=root/'spk_bv_research/coincident_admission_discrimination_v2e.py'
        if (not research_path.is_file() or research_path.is_symlink() or
                research_path.resolve(strict=True)!=research_path or
                sha256(research_path.read_bytes()).hexdigest()!=EXPECTED_V2E_RESEARCH_SHA256):
            raise ValueError('v2e research source changed from reviewed release')
        source_copy=research_path.read_bytes()
        paths=(args.v2d,args.v0w)
        sources=[safe_input(x,root) for x in paths]
        if len({identity for _,identity in sources})!=2:
            raise ValueError('predecessor file alias')
        out=safe_output(args.out,root,tuple(x.absolute() for x in paths))
        raw_d,raw_w=(v for v,_ in sources)
        d,w=json.loads(raw_d),json.loads(raw_w)
        from spk_bv_research.coincident_admission_discrimination_v2e import validate_predecessors
        validate_predecessors(d,raw_d,w,raw_w)
        native=None; frozen=False
        if not args.contract_only:
            before=read_pinned_sources(root)
            from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
            from search.spk_bv_v0e_live_evidence import fixture
            native=native_experiment(fixture,execute_live_v0e,LiveBVPlanV0e,w,root=root)
            if before!=read_pinned_sources(root):
                raise ValueError('frozen source changed during native experimental scan')
            frozen=True
        report=analyze(d,raw_d,w,raw_w,experimental=native,frozen_custody=frozen)
        if research_path.read_bytes()!=source_copy:
            raise ValueError('v2e research code modified during native run')
        if any(path.read_bytes()!=raw for path,raw in zip(paths,(raw_d,raw_w))):
            raise ValueError('predecessor file changed during v2e scan')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'new_native_executions':report['new_frozen_scheduler_executions'],
                          'v0w_full_result_anchors':report['full_native_v0w_anchor_replay_count'],
                          'native_mechanism_identified':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as e:
        print('SPK BV v2e REJECTED: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
