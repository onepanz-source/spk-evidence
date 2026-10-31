#!/usr/bin/env python3
"""BV v0v: no repository writes, report native link x in-flight limits."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from spk_bv_research.inflight_pressure_v0v import scan, verify_v0u_reference
from spk_bv_research.off_on_v0t import InterventionError, source_pins
from spk_bv_research.paired_runs_v0o import load_json, publish_new


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--reference-v0u',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        out=args.out.absolute()
        if out.exists() or out.is_symlink() or out==root or root in out.parents:
            raise InterventionError('refuse existing output or path inside repository')
        if not args.reference_v0u.is_file() or args.reference_v0u.is_symlink():
            raise InterventionError('unsafe or absent v0u reference')
        source_pins(root)  # validate bytes BEFORE native imports
        reference=load_json(args.reference_v0u)
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from search.spk_bv_v0e_live_evidence import fixture
        report=scan(fixture,execute_live_v0e,LiveBVPlanV0e,root=root)
        report['v0u_reference_check']=verify_v0u_reference(report,reference)
        publish_new(out,report,forbidden=(root,))
        print(json.dumps({
            'status':report['status'],
            'anchor':report['v0u_reference_check']['status'],
            'source_sha256':report['source_sha256'],
            'capacity_cells':len(report['cells']),
            'cells':[{'capacity':c['capacity'],
                      'off':c['runs']['off']['last_forward_terminal_tick'],
                      'forward_first':c['runs']['on_forward_first']['last_forward_terminal_tick'],
                      'feedback_first':c['runs']['on_feedback_first']['last_forward_terminal_tick'],
                      'peak_cross_inflight':max(x['metrics']['peak_cross_inflight']
                                               for x in c['runs'].values())}
                     for c in report['cells']],
            'report':str(out),
        },sort_keys=True))
        return 0
    except Exception as exc:
        print('SPK BV v0v REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
