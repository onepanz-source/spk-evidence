#!/usr/bin/env python3
"""Inspect real v0k capture. Never executes a native fixture or fabricates fields."""
import argparse
import json
from pathlib import Path
import sys

from spk_bv_research.native_dossier_v0l import (
    DossierError, load_capture, native_dossier,
)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True,help='fresh output, never overwrite')
    p.add_argument('--expected-fixture-sha')
    p.add_argument('--sample-values',type=int,default=0,choices=[0,1,2,3],
                   help='explicit opt-in: print up to three actual scalar rows per group')
    a=p.parse_args(argv)
    try:
        if a.out.exists() or a.out.is_symlink():
            raise DossierError('output already exists; refusing overwrite')
        if a.capture.resolve() == a.out.resolve():
            raise DossierError('output overlaps capture')
        doc=load_capture(a.capture)
        report=native_dossier(doc,sample_values=a.sample_values,expected_sha=a.expected_fixture_sha)
        data=json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')+b'\n'
        if len(data)>2_000_000:
            raise DossierError('report exceeds size bound')
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('xb') as f:
            f.write(data)
        print(json.dumps({'status':report['status'],
            'native_fixture_sha256':report['native_fixture_sha256'],
            'delivery_rows':report['groups']['feedback_deliveries']['native_rows'],
            'grant_rows':report['groups']['feedback_link_grants']['native_rows'],
            'assessment_rows':report['groups']['feedback_assessments']['native_rows'],
            'forward_batch_rows':report['groups']['forward_batches']['native_rows'],
            'native_v0h_verified':False,'report':str(a.out)},sort_keys=True))
        return 0
    except (DossierError, OSError,ValueError,KeyError,TypeError) as exc:
        print('BV v0l native dossier REJECTED: '+str(exc),file=sys.stderr)
        return 2
if __name__=='__main__':
    raise SystemExit(main())
