#!/usr/bin/env python3
"""Produce native v0e shape inventory or strictly declared paired observational comparison."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.paired_runs_v0o import load_capture, load_json, inventory, compare, publish_new, PairError

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--compare-config',type=Path,default=None,help='omit for schema inventory')
    p.add_argument('--expected-fixture-sha',required=True)
    args=p.parse_args(argv)
    try:
        d=load_capture(args.capture)
        if d['native_fixture_sha256']!=args.expected_fixture_sha: raise PairError('expected fixture hash mismatch')
        report=compare(d,load_json(args.compare_config,bound=50_000)) if args.compare_config else inventory(d)
        publish_new(args.out,report,forbidden=(args.capture,args.compare_config) if args.compare_config else (args.capture,))
        print(json.dumps({'status':report['status'],'native_fixture_sha256':d['native_fixture_sha256'],
                          'entries':len(report.get('entries',[])),
                          'observed_metrics':report.get('observed_metrics',{}),
                          'file':str(args.out)},sort_keys=True))
    except Exception as ex:
        print('BV v0o analyze REJECTED: '+str(ex),file=sys.stderr);return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
