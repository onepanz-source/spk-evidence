#!/usr/bin/env python3
"""Read-only native A1 computation replay, with SHA-bound v1a/v0w evidence."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_operator_replay_v1b import generate

MAX_JSON=2_000_000


def safe_input(p,root):
    p=p.absolute()
    if p.is_symlink() or any(q.is_symlink() for q in p.parents) or not p.is_file():
        raise InterventionError('unsafe or missing input')
    r=p.resolve(strict=True)
    if r==root or root in r.parents or r.stat().st_size>MAX_JSON:
        raise InterventionError('input in repository or oversized')
    return p.read_bytes(),(r.stat().st_dev,r.stat().st_ino)


def safe_output(p,root,inputs):
    p=p.absolute()
    if p.exists() or p.is_symlink() or not p.parent.is_dir() or \
            any(q.is_symlink() for q in p.parents) or root==p or root in p.parents or \
            any((p==q) for q in inputs):
        raise InterventionError('unsafe or existing output')
    return p


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v1a',type=Path,required=True)
    parser.add_argument('--v0w',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        v1ab,ident1=safe_input(a.v1a,root)
        wb,ident2=safe_input(a.v0w,root)
        if ident1==ident2:raise InterventionError('aliased reference inputs')
        out=safe_output(a.out,root,(a.v1a.absolute(),a.v0w.absolute()))
        v1a=json.loads(v1ab);w=json.loads(wb)
        # Import native execution entrypoints only AFTER validating reference files.
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        doc=generate(v1a,w,wb,fixture,execute_live_v0e,LiveBVPlanV0e,_admit,
                     _compute_local,root=root)
        if a.v1a.read_bytes()!=v1ab or a.v0w.read_bytes()!=wb:
            raise InterventionError('reference input changed during replay')
        with out.open('x',encoding='utf8') as handle:
            json.dump(doc,handle,sort_keys=True,indent=2,ensure_ascii=True)
            handle.write('\n')
        print(json.dumps({'status':doc['status'],'verified_forward_batches':doc['verified_forward_batches'],
            'real_neuron_operator_updates':0,'native_learning_proven':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1b REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
