#!/usr/bin/env python3
"""Strict two-phase public UCI fixture ingress: no dataset fetched in cloud."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from spk_v5_research.island_external_task_v5t3a import (
    canonical, read_uci, pilot, evaluate, SCHEMA,
)


def pins_ok() -> None:
    manifest=json.loads((ROOT/'docs/spk-v5-t3a-manifest.json').read_text())
    for rel,hexdigest in manifest['pins_sha256'].items():
        src=ROOT/rel
        if (not src.is_file() or src.is_symlink() or
                hashlib.sha256(src.read_bytes()).hexdigest()!=hexdigest):
            raise ValueError('pinned source drift: '+rel)


def safe_output(destination: Path) -> Path:
    path=destination.expanduser().absolute()
    if path.exists() or path.is_symlink() or path==ROOT or ROOT in path.parents:
        raise ValueError('create-only report must be absent and outside repository')
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError('unsafe output parent')
    return path


def emit(data: dict, destination: Path) -> None:
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as handle:
        handle.write(canonical(data))


def synthetic_csv(where: Path, start: int, count: int) -> None:
    import csv
    from datetime import datetime, timedelta
    with where.open('w',newline='') as handle:
        w=csv.writer(handle)
        w.writerow(['date','Temperature','Humidity','Light','CO2','HumidityRatio','Occupancy'])
        for i in range(count):
            # Fixture-only, labels engineered from features; cannot be a test of external truth.
            bright=i%4 in (0,1)
            highco2=i%4 in (0,2)
            when=datetime(2020,1,1)+timedelta(minutes=start+i)
            w.writerow([when.strftime('%Y-%m-%d %H:%M:%S'),22,44,250 if bright else 20,
                        700 if highco2 else 480,0.006,int(bright and highco2)])


def main(args=None):
    parser=argparse.ArgumentParser(description='V5-T3a UCI external task protocol (research only)')
    sub=parser.add_subparsers(dest='mode',required=True)
    for mode in ('pilot','evaluate','selftest'):
        command=sub.add_parser(mode)
        command.add_argument('--out',required=True,type=Path)
        if mode!='selftest':command.add_argument('--data',required=True,type=Path)
        if mode=='evaluate':
            command.add_argument('--pilot',required=True,type=Path)
            command.add_argument('--pilot-sha256',required=True)
    parsed=parser.parse_args(args)
    pins_ok()
    out=safe_output(parsed.out)
    if parsed.mode=='selftest':
        with tempfile.TemporaryDirectory(prefix='spk-v5-t3a-') as base:
            train=Path(base)/'datatraining.txt'
            test=Path(base)/'datatest2.txt'
            synthetic_csv(train,0,180)
            synthetic_csv(test,300,60)
            tr,h1=read_uci(train,expected_filename='datatraining.txt')
            ev,h2=read_uci(test,expected_filename='datatest2.txt')
            cert=pilot(tr,h1)
            outcome=evaluate(ev,h2,cert)
            outcome['status']='ENGINEERED_SELFTEST_ONLY_NOT_PUBLIC_DATA'
            outcome['selftest_pilot_choice']=cert['learner']['selected']
            outcome['selftest_labels_engineered']=True
            outcome['selftest_no_external_data_executed']=True
            emit(outcome,out)
    elif parsed.mode=='pilot':
        rows,sha=read_uci(parsed.data,expected_filename='datatraining.txt')
        emit(pilot(rows,sha),out)
    else:
        if parsed.pilot.is_symlink() or not parsed.pilot.is_file():
            raise ValueError('unsafe/missing pilot certificate')
        original=parsed.pilot.read_bytes()
        if not (len(parsed.pilot_sha256)==64 and
                hashlib.sha256(original).hexdigest()==parsed.pilot_sha256):
            raise ValueError('pilot certificate differs from preregistered sha256')
        cert=json.loads(original)
        if canonical(cert)!=original:
            raise ValueError('noncanonical pilot certificate')
        rows,sha=read_uci(parsed.data,expected_filename='datatest2.txt')
        emit(evaluate(rows,sha,cert),out)
    print('V5-T3a',parsed.mode,'created:',out)
    print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())


if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,json.JSONDecodeError) as error:
        print('V5-T3a REJECTED:',error,file=sys.stderr)
        raise SystemExit(2)
