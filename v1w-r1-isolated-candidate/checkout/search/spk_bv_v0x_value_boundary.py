#!/usr/bin/env python3
"""Recompute BV v0w native source and produce a cautious cost/value boundary."""
import argparse
import json
import sys
from pathlib import Path
from spk_bv_research.value_boundary_v0x import BoundaryError, summarize
from spk_bv_research.off_on_v0t import source_pins
from spk_bv_research.paired_runs_v0o import load_json, publish_new


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--v0w-13', type=Path, required=True)
    p.add_argument('--v0w-811', type=Path)
    p.add_argument('--recompute-native', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        out = args.out.absolute()
        if out.exists() or out.is_symlink() or out == root or root in out.parents:
            raise BoundaryError('refuse overwrite or repository-contained output')
        paths = (args.v0w_13, args.v0w_811)
        for q in paths:
            if q is not None and (not q.is_file() or q.is_symlink() or q.resolve() == out):
                raise BoundaryError('missing/unsafe or aliased reference input')
        pins = source_pins(root)
        x = load_json(args.v0w_13)
        if x.get('source_sha256') != pins:
            raise BoundaryError('native v0e source SHA differs from v0w report')
        summary = summarize(x)
        cross_process = False
        if args.v0w_811 is not None:
            y = load_json(args.v0w_811)
            if x != y:
                raise BoundaryError('v0w process captures differ')
            cross_process = True
        recomputed = False
        if args.recompute_native:
            from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_bv_research.workload_sensitivity_v0w import scan
            native = scan(fixture, execute_live_v0e, LiveBVPlanV0e, root=root)
            a, b = dict(x), dict(native)
            a.pop('v0v_reference_check', None)
            if a != b:
                raise BoundaryError('recomputed native workloads differ from report')
            recomputed = True
        if pins != source_pins(root):
            raise BoundaryError('native sources changed during boundary audit')
        summary['source_sha256_reverified'] = True
        summary['cross_process_payload_equality_verified'] = cross_process
        summary['native_workloads_reexecuted_and_equal'] = recomputed
        if recomputed:
            summary['status'] = 'SOURCE_RECOMPUTED_COST_ONLY_NO_INFORMATIONAL_BENEFIT_IDENTIFICATION'
        publish_new(out, summary, forbidden=(root,))
        print(json.dumps({
            'status': summary['status'], 'cells': summary['native_cells'],
            'forward_conserved': summary['forward_outcome_conservation_cells'],
            'feedback_first_delay_cells': summary['feedback_first_positive_delay_cells'],
            'native_recomputed': recomputed, 'cross_process_equal': cross_process,
            'report_file': str(out),
        }, sort_keys=True))
        return 0
    except Exception as e:
        print('SPK BV v0x REJECTED: ' + str(e), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
