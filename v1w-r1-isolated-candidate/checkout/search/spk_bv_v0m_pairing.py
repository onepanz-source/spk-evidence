#!/usr/bin/env python3
"""SPK v0m: source-bound read-only native record pairing CLI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.native_dossier_v0l import load_capture, DossierError
from spk_bv_research.native_packet_pairing_v0m import (
    read_dossier, native_pairing, PairingError,
)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--dossier', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='must not already exist')
    p.add_argument('--expected-fixture-sha', required=True)
    a = p.parse_args(argv)
    try:
        if a.out.exists() or a.out.is_symlink():
            raise PairingError('output already exists: no overwrite')
        if a.out.resolve() in (a.capture.resolve(), a.dossier.resolve()):
            raise PairingError('output path conflicts with source')
        doc = load_capture(a.capture)
        if doc['native_fixture_sha256'] != a.expected_fixture_sha:
            raise PairingError('explicit native fixture sha mismatch')
        dossier = read_dossier(a.dossier)
        result = native_pairing(doc, dossier)
        result_bytes = (json.dumps(result, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=True, allow_nan=False)+'\n').encode('ascii')
        if len(result_bytes) > 2_000_000:
            raise PairingError('result exceeds output limit')
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open('xb') as f:
            f.write(result_bytes)
        print(json.dumps({k:result[k] for k in (
            'status', 'native_fixture_sha256', 'delivery_rows', 'grant_rows',
            'paired_unique_packet_ids', 'assessment_rows', 'cross_pe_grants',
            'local_pe_grants', 'sum_native_reported_wait',
            'joined_pair_multiset_sha256', 'native_v0h_verified')},sort_keys=True))
        print('REPORT_FILE='+str(a.out))
        return 0
    except (OSError, ValueError, KeyError, TypeError, DossierError, PairingError) as exc:
        print('BV v0m native pairing REJECTED: '+str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
