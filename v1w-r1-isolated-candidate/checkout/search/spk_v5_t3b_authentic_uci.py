#!/usr/bin/env python3
"""V5-T3b additive runner: original UCI indexed CSV, original-byte SHA custody."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import pins_ok, safe_output, emit
from spk_v5_research.island_external_task_v5t3a import pilot, evaluate, canonical
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci


def check_new_pins() -> None:
    manifest=json.loads((ROOT/'docs/spk-v5-t3b-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        file=ROOT/rel
        if not file.is_file() or file.is_symlink() or sha256(file.read_bytes()).hexdigest()!=expected:
            raise ValueError('new-source pin drift: '+rel)


def main(argv=None) -> None:
    ap=argparse.ArgumentParser(description='V5-T3b authentic public UCI source format (research only)')
    subs=ap.add_subparsers(dest='mode', required=True)
    for mode in ('pilot','evaluate'):
        p=subs.add_parser(mode)
        p.add_argument('--data', required=True, type=Path)
        p.add_argument('--out', required=True, type=Path)
        if mode=='evaluate':
            p.add_argument('--pilot', required=True, type=Path)
            p.add_argument('--pilot-sha256', required=True)
    a=ap.parse_args(argv)
    pins_ok()
    check_new_pins()
    out=safe_output(a.out)
    if a.mode=='pilot':
        rows,source_sha=read_authentic_uci(a.data,expected_filename='datatraining.txt')
        result=pilot(rows,source_sha)
    else:
        if a.pilot.is_symlink() or not a.pilot.is_file():
            raise ValueError('missing or unsafe pilot certificate')
        data=a.pilot.read_bytes()
        if (len(a.pilot_sha256)!=64 or sha256(data).hexdigest()!=a.pilot_sha256):
            raise ValueError('pilot SHA mismatch')
        certificate=json.loads(data)
        if canonical(certificate)!=data:
            raise ValueError('pilot is not canonical')
        rows,source_sha=read_authentic_uci(a.data,expected_filename='datatest2.txt')
        result=evaluate(rows,source_sha,certificate)
    # Preserve T3a semantics and schema; explicitly distinguish this ingress mode.
    result['source_encoding']='original UCI seven-column header, eight-column indexed rows'
    result['source_id_sent_to_neuron']=False
    result['source_sha_basis']='raw original file bytes, no transformations'
    result['authentic_uci_ingress_schema']='spk-v5-t3b-authentic-uci-row-index/research-v0'
    result['claims_excluded'].append('UCI photo labels are external oracle supervision, not endogenous RL credit')
    emit(result,out)
    print('V5-T3b',a.mode,'created:',out)
    print('report_sha256',sha256(out.read_bytes()).hexdigest())

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as error:
        print('V5-T3b REJECTED:',error,file=sys.stderr)
        raise SystemExit(2)
