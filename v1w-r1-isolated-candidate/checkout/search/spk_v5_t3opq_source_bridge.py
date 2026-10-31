#!/usr/bin/env python3
"""Create-only T3o/p/q A1b C-terminal -> original BV-v0e audit (research)."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import safe_output,emit
from spk_v5_research.island_source_bridge_audit_v5t3q import report

def pins_ok():
    m=json.loads((ROOT/'docs/spk-v5-t3opq-manifest.json').read_text())
    for rel,sha in m['pins_sha256'].items():
        f=ROOT/rel
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:
            raise ValueError('T3o/p/q source SHA pin mismatch: '+rel)
    return len(m['pins_sha256'])

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    pins_ok()
    dst=safe_output(args.out)
    emit(report(),dst)
    print('V5-T3o/p/q source BV receipt report created:',dst)
    print('report_sha256',hashlib.sha256(dst.read_bytes()).hexdigest())
    print('T3OPQ BV-v0e C TERMINAL MIRROR DUAL SOURCE PASS; NO NATIVE SEMANTIC BV OR RL')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,TypeError,KeyError,AssertionError) as ex:
        print('T3OPQ REJECTED:',ex,file=sys.stderr)
        raise SystemExit(2)
