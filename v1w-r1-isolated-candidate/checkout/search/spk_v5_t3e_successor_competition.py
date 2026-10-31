#!/usr/bin/env python3
"""Create-only V5-T3e original-UCI physical-successor static-competitor audit."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import pins_ok,safe_output,emit
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok,read_sealed
from search.spk_v5_t3d_real_transition import t3d_pins_ok
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_successor_competition_v5t3e import aggregate,SCHEMA


def t3e_pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3e-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        file=ROOT/rel
        if not file.is_file() or file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            raise ValueError('T3e source custody drift: '+rel)


def audit_inputs(train:Path,early:Path,late:Path,t3d_report:Path,t3d_sha:str)->dict:
    manifest=json.loads((ROOT/'docs/spk-v5-t3d-manifest.json').read_text())
    if t3d_sha!=manifest['original_uci_report_sha256']:
        raise ValueError('must use exact canonical T3d predecessor hash')
    predecessor=read_sealed(t3d_report,t3d_sha)
    t,ts=read_authentic_uci(train,expected_filename='datatraining.txt')
    e,es=read_authentic_uci(early,expected_filename='datatest.txt')
    l,ls=read_authentic_uci(late,expected_filename='datatest2.txt')
    frozen=manifest['public_original_uci_SHA256']
    if {'datatraining.txt':ts,'datatest.txt':es,'datatest2.txt':ls}!=frozen:
        raise ValueError('not the original UCI raw bytes pinned at T3d')
    return aggregate(t,ts,e,es,l,ls,predecessor,t3d_sha)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Research V5 T3e time-order v static; PUBLIC not blind')
    for p in ('train','early','late','t3d-report','t3d-sha256','out'):
        parser.add_argument('--'+p,required=True,type=str if p=='t3d-sha256' else Path)
    a=parser.parse_args(argv)
    pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok();t3e_pins_ok()
    output=safe_output(a.out)
    result=audit_inputs(a.train,a.early,a.late,a.t3d_report,a.t3d_sha256)
    if result['schema']!=SCHEMA:
        raise ValueError('T3e output schema drift')
    emit(result,output)
    print('V5-T3e public physical-successor candidate audit:',output)
    print('report_sha256',hashlib.sha256(output.read_bytes()).hexdigest())
    print('T3E A1B PERSISTENCE COMPETITION PASS; PUBLIC TEST NOT BLIND; NATIVE RL NONE')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as err:
        print('V5-T3e REJECTED:',err,file=sys.stderr)
        raise SystemExit(2)
