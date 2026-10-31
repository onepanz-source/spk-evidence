#!/usr/bin/env python3
"""Read-only native BV v0w temporal workload scan; no repository writes."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from spk_bv_research.workload_sensitivity_v0w import scan, verify_v0v_anchors
from spk_bv_research.off_on_v0t import InterventionError, source_pins
from spk_bv_research.paired_runs_v0o import load_json, publish_new


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--reference-v0v',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        out=args.out.absolute()
        if out.exists() or out.is_symlink() or out==root or root in out.parents:
            raise InterventionError('refuse existing or repository-contained report path')
        ref=args.reference_v0v
        if not ref.is_file() or ref.is_symlink() or ref.resolve()==out:
            raise InterventionError('unsafe or missing reference v0v report')
        source_pins(root)  # source bytes BEFORE import of native modules
        reference=load_json(ref)
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
        from search.spk_bv_v0e_live_evidence import fixture
        result=scan(fixture,execute_live_v0e,LiveBVPlanV0e,root=root)
        result['v0v_reference_check']=verify_v0v_anchors(result,reference)
        publish_new(out,result,forbidden=(root,))
        print(json.dumps({
            'status':result['status'],
            'reference_check':result['v0v_reference_check']['status'],
            'cells':len(result['cells']),
            'summary':[{
                'workload':c['workload'],'fabric':c['fabric_slots_per_tick'],
                'external_events':c['stimulus_count'],
                'off_terminal':c['runs']['off']['last_forward_terminal_tick'],
                'forward_first_terminal':c['runs']['on_forward_first']['last_forward_terminal_tick'],
                'feedback_first_terminal':c['runs']['on_feedback_first']['last_forward_terminal_tick'],
                'feedback_deliveries':c['runs']['on_forward_first']['metrics']['feedback_deliveries'],
            } for c in result['cells']],
            'report':str(out)
        },sort_keys=True))
        return 0
    except Exception as exc:
        print('SPK BV v0w REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
