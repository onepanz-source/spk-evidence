#!/usr/bin/env python3
"""Read-only-on-repository BV v0u native link capacity scan; output outside repo."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from spk_bv_research.off_on_v0t import InterventionError, source_pins
from spk_bv_research.link_pressure_v0u import scan, verify_v0t_baseline
from spk_bv_research.paired_runs_v0o import load_json, publish_new


def main(argv=None):
    p=argparse.ArgumentParser(description='BV v0u source-bound native link capacity sensitivity scan')
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--reference-v0t',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        out=a.out.absolute()
        if out.exists() or out.is_symlink() or out==root or root in out.parents:
            raise InterventionError('output exists or is inside source repository')
        if not a.reference_v0t.is_file() or a.reference_v0t.is_symlink():
            raise InterventionError('reference v0t must be existing regular file')
        source_pins(root)  # BEFORE importing the native scheduler or fixture
        reference=load_json(a.reference_v0t)
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
        from search.spk_bv_v0e_live_evidence import fixture
        result=scan(fixture,execute_live_v0e,LiveBVPlanV0e,root=root)
        result['v0t_baseline_check']=verify_v0t_baseline(result,reference)
        publish_new(out,result,forbidden=(root,))
        summary={
            'status':result['status'],
            'v0t_baseline_check':result['v0t_baseline_check']['status'],
            'original_fixture_sha256':result['original_fixture_sha256'],
            'cells':[{
                'capacity':cell['link_capacity'],
                'off_terminal_tick':cell['runs']['off']['last_forward_terminal_tick'],
                'on_forward_terminal_tick':cell['runs']['on_forward_first']['last_forward_terminal_tick'],
                'on_feedback_terminal_tick':cell['runs']['on_feedback_first']['last_forward_terminal_tick'],
                'nondominated':cell['local_proxy_frontier']['nondominated'],
            } for cell in result['cells']],
            'report':str(out),
        }
        print(json.dumps(summary,sort_keys=True))
        return 0
    except Exception as ex:
        print('SPK BV v0u REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
