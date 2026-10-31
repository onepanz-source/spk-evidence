#!/usr/bin/env python3
"""V5-T3d create-only UCI real-successor posthoc audit (no learning)."""
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
from search.spk_v5_t3c_public_full_coverage import new_pins_ok,read_sealed
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_real_transition_v5t3d import aggregate,SCHEMA


def t3d_pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3d-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        file=ROOT/rel
        if not file.is_file() or file.is_symlink() or sha256(file.read_bytes()).hexdigest()!=expected:
            raise ValueError('T3d source pin drift: '+rel)


def audit_inputs(train:Path,early:Path,late:Path,t3c_report:Path,t3c_sha:str)->dict:
    evidence=read_sealed(t3c_report,t3c_sha)
    manifest=json.loads((ROOT/'docs/spk-v5-t3c-manifest.json').read_text())
    if t3c_sha!=manifest['external_public_uci_report_sha256']:
        raise ValueError('not the exact frozen UCI T3c report')
    t,ts=read_authentic_uci(train,expected_filename='datatraining.txt')
    e,es=read_authentic_uci(early,expected_filename='datatest.txt')
    l,ls=read_authentic_uci(late,expected_filename='datatest2.txt')
    return aggregate(t,ts,e,es,l,ls,evidence,t3c_sha)


def main(argv=None):
    ap=argparse.ArgumentParser(description='T3d real successor temporal falsification, public data only')
    for prop in ('train','early','late','t3c-report','t3c-sha256','out'):
        ap.add_argument('--'+prop,required=True,type=Path if prop!='t3c-sha256' else str)
    a=ap.parse_args(argv)
    pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok()
    out=safe_output(a.out)
    report=audit_inputs(a.train,a.early,a.late,a.t3c_report,a.t3c_sha256)
    if report['schema']!=SCHEMA:raise ValueError('unexpected output schema')
    emit(report,out)
    print('V5-T3d physically successive public UCI audit created:',out)
    print('report_sha256',sha256(out.read_bytes()).hexdigest())
    print('T3D REAL-SUCCESSOR INPUT PASS; RARE ONSET, NO BLIND AND NO NATIVE RL')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as e:
        print('V5-T3d REJECTED:',e,file=sys.stderr)
        raise SystemExit(2)
