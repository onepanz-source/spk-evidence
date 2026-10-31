#!/usr/bin/env python3
"""SPK BV v0n observational cost/occupancy CLI; no source or runtime mutations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.native_occupancy_v0n import (
    read_pairing, observe, observe_native, OccupancyError,
)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--pairing', type=Path, required=True)
    p.add_argument('--capture', type=Path)
    p.add_argument('--dossier', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--expected-fixture-sha', required=True)
    a=p.parse_args(argv)
    try:
        if (a.capture is None) != (a.dossier is None):
            raise OccupancyError('capture and dossier must be supplied together')
        if a.out.exists() or a.out.is_symlink():
            raise OccupancyError('output exists: no overwrite')
        sources=(a.pairing, a.capture, a.dossier)
        if a.out.resolve() in tuple(s.resolve() for s in sources if s is not None):
            raise OccupancyError('output conflicts with source file')
        report=read_pairing(a.pairing)
        if report['native_fixture_sha256'] != a.expected_fixture_sha:
            raise OccupancyError('expected fixture SHA256 mismatch')
        verified=a.capture is not None
        result=observe_native(report, a.capture, a.dossier) if verified else observe(report)
        raw=(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)+'\n').encode('ascii')
        if len(raw)>2_000_000:
            raise OccupancyError('output report exceeds byte budget')
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('xb') as fd: fd.write(raw)
        summary={k:result[k] for k in (
            'status','delivery_grant_pairs','end_of_tick_undelivered_grants_peak',
            'bounded_grant_delivery_tick_area','within_tick_grant_first_peak_upper_bound',
            'grant_and_delivery_coactive_tick_count','native_reported_wait_sum',
            'source_verified_by_recomputation')}
        print(json.dumps(summary,sort_keys=True))
        print('REPORT_FILE='+str(a.out))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('SPK v0n occupancy REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
