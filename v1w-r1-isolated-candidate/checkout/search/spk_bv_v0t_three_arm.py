#!/usr/bin/env python3
"""Execute native SPK BV v0e in OFF / ON-forward / ON-feedback modes.

Writes only an observational research report outside the source worktree.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.off_on_v0t import InterventionError, execute_three, source_pins, verify_reference_v0o
from spk_bv_research.paired_runs_v0o import publish_new


def main(argv=None):
    parser=argparse.ArgumentParser(description='SPK BV v0t source-bound 3-arm native v0e control')
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reference-v0o',type=Path,default=None)
    opts=parser.parse_args(argv)
    try:
        root=opts.root.resolve(strict=True)
        out=opts.out.absolute()
        if out.exists() or out.is_symlink() or root==out or root in out.parents:
            raise InterventionError('output must be absent and outside repository')
        # BEFORE importing native executor or fixture, require exact source bytes.
        source_pins(root)
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
        from search.spk_bv_v0e_live_evidence import fixture
        report=execute_three(fixture,execute_live_v0e,LiveBVPlanV0e,root=root)
        if opts.reference_v0o is not None:
            report['v0o_reference_check']=verify_reference_v0o(report,opts.reference_v0o)
        publish_new(out,report,forbidden=(root,))
        summary={
            'status':report['status'],
            'shared_fixture_input_sha256':report['shared_fixture_input_sha256'],
            'result_sha256':{k:v['whole_result_sha256'] for k,v in report['runs'].items()},
            'off_feedback_grants':report['runs']['off']['metrics']['feedback_link_grants'],
            'on_forward_first_feedback_grants':report['runs']['on_forward_first']['metrics']['feedback_link_grants'],
            'on_feedback_first_feedback_grants':report['runs']['on_feedback_first']['metrics']['feedback_link_grants'],
            'last_terminal_tick_deltas':{k:v['last_terminal_tick_delta'] for k,v in report['interventions'].items()},
            'file':str(out),
            'reference_v0o_status':report.get('v0o_reference_check',{}).get('status','NOT_VERIFIED'),
        }
        print(json.dumps(summary,sort_keys=True))
        return 0
    except Exception as ex:
        print('SPK BV v0t REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
