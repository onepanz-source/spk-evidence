#!/usr/bin/env python3
"""Source-bound v2a bounded research executor, no frozen-SPK semantic promotion.

On fwork, frozen-source read-only pinning is mandatory. '--contract-only'
permits offline research testing but marks that verification absent.
Inputs/out must be separate, external to repository, and never overwrite.
"""
from __future__ import annotations
import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.versioned_executor_admission_v2a import analyze

NEW_EXECUTOR = 'spk_backvalidation_v2/observed_scheduler_v2a.py'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for key in ('v1z','v1y','v1x'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true',
                   help='offline audit; frozen source pins NOT rechecked')
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        inputs=[a.v1z,a.v1y,a.v1x]
        entries=[safe_input(path,root) for path in inputs]
        if len(set(ident for _,ident in entries))!=len(entries):
            raise ValueError('predecessor inode alias')
        out=safe_output(a.out,root,tuple(x.absolute() for x in inputs))
        module=root/NEW_EXECUTOR
        if not module.is_file() or module.is_symlink() or module.resolve(strict=True)!=module:
            raise ValueError('versioned executable source missing or unsafe')
        src=module.read_bytes()
        if not src or len(src)>100_000:
            raise ValueError('unexpected v2a source length')
        before=None if a.contract_only else read_pinned_sources(root)
        (zb,yb,xb)=(r for r,_ in entries)
        report=analyze(json.loads(zb),zb,json.loads(yb),yb,json.loads(xb),xb,
                       frozen_source_custody=before is not None,
                       executor_sha256=sha256(src).hexdigest())
        if before is not None and read_pinned_sources(root)!=before:
            raise ValueError('frozen source modified during execution')
        if module.read_bytes()!=src:
            raise ValueError('new executor modified during execution')
        if any(p.read_bytes()!=b for p,(b,_) in zip(inputs,entries)):
            raise ValueError('input changed during execution')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'], 'micro_pairs':8,
                          'frozen_source_custody':before is not None,
                          'native_B_delivery':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,AssertionError) as e:
        print('SPK BV v2a REJECTED: '+str(e),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
