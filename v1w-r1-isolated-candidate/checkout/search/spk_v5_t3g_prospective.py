#!/usr/bin/env python3
"""V5-T3g create-only two-phase prospective screen, labels only in evaluate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import safe_output,emit
from search.spk_v5_t3f_day_stratification import t3f_pins_ok
from spk_v5_research.island_external_task_v5t3a import canonical
from spk_v5_research.island_prospective_validation_v5t3g import (
    read_features,read_labels,precommit,evaluate,COMMIT_SCHEMA,
)

def pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3g-manifest.json').read_text())
    for rel,expected in manifest['pins_sha256'].items():
        f=ROOT/rel
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:
            raise ValueError('T3g source SHA pin drift: '+rel)

def read_commit(path,expected_sha):
    if len(expected_sha)!=64 or any(c not in '0123456789abcdef' for c in expected_sha):
        raise ValueError('missing precommitted sha256')
    if path.is_symlink() or not path.is_file():
        raise ValueError('unsafe or missing precommit')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('precommit byte hash does not match declared precommit')
    result=json.loads(raw)
    if raw!=canonical(result) or result.get('schema')!=COMMIT_SCHEMA:
        raise ValueError('noncanonical or unrecognized precommit')
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description='T3g prospective protocol, NOT a blind custody service')
    sub=p.add_subparsers(dest='mode',required=True)
    pre=sub.add_parser('precommit',help='read feature-only CSV; never open label file')
    pre.add_argument('--features',required=True,type=Path)
    pre.add_argument('--source-id',required=True)
    pre.add_argument('--out',required=True,type=Path)
    ev=sub.add_parser('evaluate',help='read later-provided labels after matching feature precommit')
    ev.add_argument('--features',required=True,type=Path)
    ev.add_argument('--labels',required=True,type=Path)
    ev.add_argument('--precommit',required=True,type=Path)
    ev.add_argument('--precommit-sha256',required=True)
    ev.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    # Historical pins AND prospective pins enforce past decisions & code custody.
    t3f_pins_ok();pins_ok()
    output=safe_output(a.out)
    proto=ROOT/'docs/spk-v5-t3g-protocol.json'
    proto_sha=hashlib.sha256(proto.read_bytes()).hexdigest()
    rows,features_sha=read_features(a.features)
    if a.mode=='precommit':
        report=precommit(rows,features_sha,a.source_id,proto_sha)
    else:
        if a.labels.resolve()==a.features.resolve():
            raise ValueError('labels must be a separate source')
        commit=read_commit(a.precommit,a.precommit_sha256)
        labels,labels_sha=read_labels(a.labels)
        report=evaluate(rows,features_sha,labels,labels_sha,commit,proto_sha)
    emit(report,output)
    print('V5-T3g',a.mode,'created:',output)
    print('report_sha256',hashlib.sha256(output.read_bytes()).hexdigest())
    print('T3G PROSPECTIVE SCREEN RESEARCH ONLY; INDEPENDENT BLIND CUSTODY AND NATIVE RL NOT ESTABLISHED')

if __name__=='__main__':
    try: main()
    except (ValueError,TypeError,OSError,KeyError,json.JSONDecodeError) as e:
        print('V5-T3g REJECTED:',e,file=sys.stderr)
        raise SystemExit(2)
