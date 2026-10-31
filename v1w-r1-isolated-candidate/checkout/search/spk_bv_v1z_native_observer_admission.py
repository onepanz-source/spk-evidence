#!/usr/bin/env python3
"""BV v1z: source-bound versioned native observer ADMISSION CONTRACT, not native v2.

Pass native v1y and v1x reports; verify full canonical result hashes, trace
scopes, zero-authority boundaries and produce a BLOCKED native-v2 gate result.
The reference emitter belongs only to the research laboratory.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_observer_v2_boundary_v1z import analyze
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--v1y', type=Path, required=True)
    p.add_argument('--v1x', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        raw_y, y_inode = safe_input(args.v1y, root)
        raw_x, x_inode = safe_input(args.v1x, root)
        if y_inode == x_inode: raise ValueError('predecessor aliases forbidden')
        out = safe_output(args.out, root, (args.v1y.absolute(), args.v1x.absolute()))
        report = analyze(json.loads(raw_y), raw_y, json.loads(raw_x), raw_x)
        if args.v1y.read_bytes() != raw_y or args.v1x.read_bytes() != raw_x:
            raise ValueError('predecessor changed during audit')
        with out.open('xb') as fh: fh.write(canon(report))
        print(json.dumps({'status': report['status'], 'native_gate_status':report['native_gate_status'],
                          'new_native_runs':0, 'out':str(out)}, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AssertionError) as e:
        print('SPK BV v1z REJECTED: '+str(e), file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
