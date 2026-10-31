#!/usr/bin/env python3
"""v2c source-bound research-only time-order differential, no frozen edits.

Use --contract-only for offline report review without native custody.
Both native v1m and v1q are prior postreturn reports, never live events.
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
from spk_bv_research.temporal_differential_v2c import analyze

EXECUTORS = ('spk_backvalidation_v2/observed_scheduler_v2a.py',
             'spk_backvalidation_v2/time_order_executor_v2c.py')
EXPECTED_V2C_SHA256 = '737bdf3400c33e0639a5cae65339397d34a8d359d228becd417e44601e2724de'
PARENTS = ('v2b','v2a','v1q','v1m','v1z','v1y','v1x')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in PARENTS:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true',
                        help='no new audit of frozen sources; report marks false')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,k) for k in PARENTS]
        data=[safe_input(p,root) for p in paths]
        if len({identity for _,identity in data})!=len(data):
            raise ValueError('aliased predecessor reports')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        source_bytes=[]
        for name in EXECUTORS:
            p=root/name
            if p.is_symlink() or not p.is_file() or p.resolve(strict=True)!=p:
                raise ValueError('unsafe or missing micro-executor')
            raw=p.read_bytes()
            if not 1<=len(raw)<=100_000:
                raise ValueError('micro source not bounded')
            source_bytes.append(raw)
        if sha256(source_bytes[1]).hexdigest() != EXPECTED_V2C_SHA256:
            raise ValueError('v2c scheduler changed from reviewed source')
        native_before=None if args.contract_only else read_pinned_sources(root)
        raws=[raw for raw,_ in data]
        reports=[json.loads(raw) for raw in raws]
        report=analyze(*[v for o,b in zip(reports,raws) for v in (o,b)],
                       *(sha256(raw).hexdigest() for raw in source_bytes),
                       frozen_custody=native_before is not None)
        if native_before is not None and read_pinned_sources(root)!=native_before:
            raise ValueError('frozen source custody drift')
        if any((root/p).read_bytes()!=raw for p,raw in zip(EXECUTORS,source_bytes)):
            raise ValueError('micro source modified during research audit')
        if any(p.read_bytes()!=raw for p,raw in zip(paths,raws)):
            raise ValueError('predecessor changed during research audit')
        with out.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'finite_count_cells':16,
                          'original_AB_timestamp_pairs_fit':2,
                          'native_scheduler_executions':0,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v2c REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
