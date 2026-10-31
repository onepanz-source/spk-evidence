#!/usr/bin/env python3
"""BV v2d: source-bound v0w historical native holdout vs explicit micro inputs.

Default mode checks unchanged frozen sources on fwork. --contract-only is
an explicitly un-attested offline analysis. No frozen scheduler is invoked.
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
from spk_bv_research.native_holdout_differential_v2d import analyze

SOURCES=('spk_backvalidation_v2/observed_scheduler_v2a.py',
         'spk_backvalidation_v2/time_order_executor_v2c.py',
         'spk_backvalidation_v2/explicit_input_executor_v2d.py')
EXPECTED_V2D_SHA256='ed14f790d4a2182ee40eff04844a23cb4f6f89c34bf8f07c5cd5a3093d232b0c'
PARENTS=('v2c','v0w','v2b','v2a','v1q','v1m','v1z','v1y','v1x')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in PARENTS:
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--contract-only',action='store_true',
                   help='no native frozen SHA recheck, explicitly un-attested')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,n) for n in PARENTS]
        data=[safe_input(path,root) for path in paths]
        if len({identity for _,identity in data})!=len(data):
            raise ValueError('aliased predecessor reports')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        source_raw=[]
        for name in SOURCES:
            f=root/name
            if f.is_symlink() or not f.is_file() or f.resolve(strict=True)!=f:
                raise ValueError('unsafe research executor source')
            raw=f.read_bytes()
            if not 1<=len(raw)<=100_000:
                raise ValueError('unbounded research executor source')
            source_raw.append(raw)
        if sha256(source_raw[2]).hexdigest()!=EXPECTED_V2D_SHA256:
            raise ValueError('v2d executor source changed from reviewed version')
        native_before=None if args.contract_only else read_pinned_sources(root)
        raws=[raw for raw,_ in data]
        objs=[json.loads(raw) for raw in raws]
        report=analyze(*[v for o,raw in zip(objs,raws) for v in (o,raw)],
                       *(sha256(r).hexdigest() for r in source_raw),
                       frozen_custody=native_before is not None)
        if native_before is not None and read_pinned_sources(root)!=native_before:
            raise ValueError('frozen native source drift during comparison')
        if any((root/name).read_bytes()!=raw for name,raw in zip(SOURCES,source_raw)):
            raise ValueError('micro source changed during comparison')
        if any(f.read_bytes()!=raw for f,raw in zip(paths,raws)):
            raise ValueError('predecessor report changed during comparison')
        with out.open('xb') as f:
            f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'native_v0w_historical_count_equal':24,
                          'native_v0w_historical_count_mismatch':6,
                          'new_frozen_scheduler_runs':0,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as e:
        print('SPK BV v2d REJECTED: '+str(e),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
