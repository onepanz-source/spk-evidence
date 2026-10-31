#!/usr/bin/env python3
"""v2b native-micro count projection and temporal falsification, research only.

Native inputs are earlier, source-bound *reports*, not new runs in v2b.
Never overwrite output, follow symlinks or modify frozen SPK modules.
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
from spk_bv_research.native_micro_differential_v2b import compare

EXECUTOR='spk_backvalidation_v2/observed_scheduler_v2a.py'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in ('v2a','v1q','v1m','v1z','v1y','v1x'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true',
                        help='offline review: no fresh frozen-source custody')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,k) for k in ('v2a','v1q','v1m','v1z','v1y','v1x')]
        entries=[safe_input(p,root) for p in paths]
        if len({ident for raw,ident in entries})!=len(paths):
            raise ValueError('aliased input in v2b custody')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        source=root/EXECUTOR
        if (source.is_symlink() or not source.is_file() or
                source.resolve(strict=True)!=source):
            raise ValueError('unsafe or missing v2a source')
        source_bytes=source.read_bytes()
        if not 1<=len(source_bytes)<=100_000:
            raise ValueError('executor source not bounded')
        native_pins=None if args.contract_only else read_pinned_sources(root)
        documents=[json.loads(raw) for raw,ident in entries]
        raws=[raw for raw,ident in entries]
        report=compare(*[x for pair in zip(documents,raws) for x in pair],
                       sha256(source_bytes).hexdigest(),
                       frozen_custody=native_pins is not None)
        if native_pins is not None and read_pinned_sources(root)!=native_pins:
            raise ValueError('frozen source modified during v2b comparison')
        if source.read_bytes()!=source_bytes:
            raise ValueError('micro-executor mutated during v2b audit')
        if any(p.read_bytes()!=raw for p,raw in zip(paths,raws)):
            raise ValueError('input changed during v2b report generation')
        with out.open('xb') as f:
            f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'count_projection_cells_equal':16,
                          'native_original_emission_order_equal':False,
                          'new_native_scheduler_executions':0,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,AssertionError,IndexError) as e:
        print('SPK BV v2b REJECTED: '+str(e),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
