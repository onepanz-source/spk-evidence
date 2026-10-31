#!/usr/bin/env python3
"""Create-only, source-pinned cumulative V5-T3i/j/k offline research evidence."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import safe_output,emit
from spk_v5_research.island_closed_loop_audit_v5t3k import report


def pins_ok():
    m=json.loads((ROOT/'docs/spk-v5-t3ijk-manifest.json').read_text())
    for rel,expected in m['pins_sha256'].items():
        f=ROOT/rel
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:
            raise ValueError('T3i/j/k pinned source/reference drift: '+rel)
    return len(m['pins_sha256'])


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--uci-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    pins_ok()
    path=safe_output(args.out)
    result=report(args.uci_dir)
    emit(result,path)
    print('T3IJK research report created:',path)
    print('report_sha256',hashlib.sha256(path.read_bytes()).hexdigest())
    print('T3IJK C-AUTHORED ONLINE RESEARCH LOOP PASS; SYNTHETIC-SHIFT BENEFIT ONLY; PUBLIC UCI PHOTO UTILITY NOT SHOWN; NO NATIVE RL')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError,AssertionError) as e:
        print('T3IJK REJECTED:',e,file=sys.stderr);raise SystemExit(2)
