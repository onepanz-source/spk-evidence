#!/usr/bin/env python3
"""Create-only public post-hoc calendar stratification of the sealed V5-T3e experiment."""
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
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
from spk_v5_research.island_uci_index_v5t3b import read_authentic_uci
from spk_v5_research.island_calendar_stratification_v5t3f import SCHEMA,aggregate


def t3f_pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3f-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        f=ROOT/rel
        if (not f.is_file() or f.is_symlink() or
            hashlib.sha256(f.read_bytes()).hexdigest()!=expected):
            raise ValueError('T3f source pin drift: '+rel)


def audit_inputs(train:Path,early:Path,late:Path,t3e_report:Path,t3e_sha:str)->dict:
    manifest=json.loads((ROOT/'docs/spk-v5-t3e-manifest.json').read_text())
    if t3e_sha!=manifest['new_reference_sha256']:
        raise ValueError('not the frozen T3e report sha')
    predecessor=read_sealed(t3e_report,t3e_sha)
    inputs={}
    source={}
    for name,path in (('datatraining.txt',train),('datatest.txt',early),('datatest2.txt',late)):
        inputs[name],source[name]=read_authentic_uci(path,expected_filename=name)
    if source!=manifest['original_UCI_SHA256']:
        raise ValueError('original UCI source SHA drift')
    result=aggregate(inputs['datatraining.txt'],inputs['datatest.txt'],
                     inputs['datatest2.txt'],source,predecessor,t3e_sha)
    if result.get('schema')!=SCHEMA:
        raise ValueError('output schema drift')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description='T3f public day-block discordance, NO blind or native RL')
    for prop in ('train','early','late','t3e-report','t3e-sha256','out'):
        ap.add_argument('--'+prop,required=True,type=str if prop=='t3e-sha256' else Path)
    a=ap.parse_args(argv)
    pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok();t3e_pins_ok();t3f_pins_ok()
    out=safe_output(a.out)
    report=audit_inputs(a.train,a.early,a.late,a.t3e_report,a.t3e_sha256)
    emit(report,out)
    print('V5-T3f UCI calendar-block auditor created:',out)
    print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
    print('T3F POSTHOC CALENDAR CONCENTRATION PASS; NO BLIND, NO ENDOGENOUS OR NATIVE RL')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,KeyError,json.JSONDecodeError) as err:
        print('V5-T3f REJECTED:',err,file=sys.stderr)
        raise SystemExit(2)
