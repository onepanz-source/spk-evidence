#!/usr/bin/env python3
"""SPK V5-T3l/m/n create-only bundled goal-identifiability audit."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from search.spk_v5_t3a_external_uci import safe_output,emit
from spk_v5_research.island_goal_nonpromotion_v5t3n import report

def pins_ok():
    manifest=json.loads((ROOT/'docs/spk-v5-t3lmn-manifest.json').read_text())
    for rel,hexhash in manifest['pins_sha256'].items():
        f=ROOT/rel
        if f.is_symlink() or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=hexhash:
            raise ValueError('pinned T3l/m/n source/reference drift: '+rel)
    return len(manifest['pins_sha256'])

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--uci-dir',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    pins_ok()
    output=safe_output(args.out)
    emit(report(args.uci_dir,120,1200),output)
    print('V5-T3l/m/n report created:',output)
    print('report_sha256',hashlib.sha256(output.read_bytes()).hexdigest())
    print('T3LMN A1B C-CREDIT GOAL-NONIDENTIFIABILITY PASS; PUBLIC PROXY DISCORDANCE; NO BLIND NATIVE BV OR RL')

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,TypeError,KeyError,AssertionError) as exc:
        print('T3LMN REJECTED:',exc,file=sys.stderr)
        raise SystemExit(2)
