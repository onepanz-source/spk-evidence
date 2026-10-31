#!/usr/bin/env python3
"""Create-only post-selection full original UCI audit; no learner retraining."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import pins_ok,safe_output,emit
from search.spk_v5_t3b_authentic_uci import check_new_pins
from spk_v5_research.island_external_task_v5t3a import canonical
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_public_audit_v5t3c import aggregate_report


def new_pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3c-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        item=ROOT/rel
        if item.is_symlink() or not item.is_file() or sha256(item.read_bytes()).hexdigest()!=expected:
            raise ValueError('T3c source pin drift: '+rel)


def read_sealed(path:Path,expected:str):
    if (not isinstance(path,Path) or path.is_symlink() or not path.is_file()
            or len(expected)!=64 or any(ch not in '0123456789abcdef' for ch in expected)):
        raise ValueError('unsafe or unsealed evidence file')
    raw=path.read_bytes()
    if len(raw)>1_000_000 or sha256(raw).hexdigest()!=expected:
        raise ValueError('evidence SHA mismatch')
    obj=json.loads(raw)
    if type(obj) is not dict or canonical(obj)!=raw:
        raise ValueError('evidence not canonical JSON')
    return obj


def main(argv=None):
    ap=argparse.ArgumentParser(description='V5-T3c source-grounded full public UCI falsification audit')
    for prop in ('train','early','late','pilot','public-evaluation','out'):
        ap.add_argument('--'+prop,required=True,type=Path)
    ap.add_argument('--pilot-sha256',required=True)
    ap.add_argument('--eval-sha256',required=True)
    a=ap.parse_args(argv)
    pins_ok();check_new_pins();new_pins_ok()
    output=safe_output(a.out)
    pilot=read_sealed(a.pilot,a.pilot_sha256)
    published=read_sealed(a.public_evaluation,a.eval_sha256)
    if published.get('status')!='PUBLIC_UCI_EVALUATION_NOT_BLIND' or published.get('phase')!='evaluation':
        raise ValueError('not a certified public evaluation')
    train,trainsha=read_authentic_uci(a.train,expected_filename='datatraining.txt')
    early,earlysha=read_authentic_uci(a.early,expected_filename='datatest.txt')
    late,latesha=read_authentic_uci(a.late,expected_filename='datatest2.txt')
    report=aggregate_report(early,earlysha,late,latesha,train,trainsha,
                            pilot,a.pilot_sha256,published,a.eval_sha256)
    emit(report,output)
    print('T3c full original UCI post-selection public audit:',output)
    print('report_sha256',sha256(output.read_bytes()).hexdigest())
    print('T3C FULL PUBLIC A1B AUDIT & STATIC-EQUIVALENCE PASS; PHYSICAL TEMPORAL LEARNING NOT SHOWN; T3 BLIND/NATIVE LEARNING BLOCKED')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as e:
        print('V5-T3c REJECTED:',e,file=sys.stderr)
        raise SystemExit(2)
