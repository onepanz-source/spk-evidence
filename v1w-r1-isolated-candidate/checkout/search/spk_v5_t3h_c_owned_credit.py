#!/usr/bin/env python3
"""Create-only report of finite C-authored A1b research verdict/credit cases."""
from __future__ import annotations
import hashlib,json,sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import safe_output,emit
from spk_v5_research.island_c_owned_credit_v5t3h import compact_audit

def pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3h-manifest.json').read_text())
    for rel,sha in manifest['pins_sha256'].items():
        f=ROOT/rel
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:
            raise ValueError('T3h inherited/new source pin drift: '+rel)

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    pins_ok()
    out=safe_output(a.out)
    r=compact_audit()
    emit(r,out)
    print('V5-T3h report created:',out)
    print('report_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
    print('T3H A1B C-COMPUTED AND REVERSE-DELIVERED RESEARCH CREDIT PASS; NO NATIVE BV/RL OR BLIND SENSOR CUSTODY')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,OSError,KeyError) as e:
        print('V5-T3h REJECTED:',e,file=sys.stderr);raise SystemExit(2)
