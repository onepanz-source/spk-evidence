#!/usr/bin/env python3
"""SPK BV v1s sealed-lab separate-channel audit with full native v1r custody replay."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_disclosure_channel_v1s import analyze,validate_r,canon
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1r_allocation_boundary import main as rmain,NAMES as RNAMES

NAMES=('v1r',)+RNAMES


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,n) for n in NAMES]
        entries=[safe_input(p,root) for p in paths]
        require(len({identity for _,identity in entries})==len(entries),'aliased source inputs')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        raw=dict((name,entries[i][0]) for i,name in enumerate(NAMES))
        r=json.loads(raw['v1r']);validate_r(r,raw['v1r'])
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1s-verify-v1r-') as tmp:
            rebuilt=Path(tmp)/'v1r.json'
            chain=['--root',str(root)]
            for name in RNAMES:chain+=['--'+name,str(getattr(args,name))]
            chain+=['--out',str(rebuilt)]
            with contextlib.redirect_stdout(io.StringIO()):rc=rmain(chain)
            require(rc==0 and rebuilt.is_file() and rebuilt.read_bytes()==raw['v1r'],
                    'full native-source-bound v1r recomputation byte mismatch')
        report=analyze(r,raw['v1r'])
        report['inherited_native_v1r_recomputation_verified_in_this_run']=True
        require(all(p.read_bytes()==raw[n] for p,n in zip(paths,NAMES)),
                'upstream evidence mutated during report generation')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],'lab_cases':report['lab_case_count'],
                          'native_receiver_judgments':0,'native_learning':False,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1s REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
