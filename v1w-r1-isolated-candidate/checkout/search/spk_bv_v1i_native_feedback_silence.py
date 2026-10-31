#!/usr/bin/env python3
"""Reexecute v1h in a new temporary output and audit feedback silence and polarity."""
from __future__ import annotations
import argparse, contextlib, io, json, sys, tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_feedback_silence_v1i import audit
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from search.spk_bv_v1h_network_counterfactual import main as hmain, NAMES as HNAMES

NAMES=('v1h',)+HNAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=tuple(getattr(a,n) for n in NAMES)
        inputs=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in inputs})==len(inputs),
                'reference inputs alias one another')
        out=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1i-native-replay-') as temp:
            dest=Path(temp)/'v1h-recomputed.json'
            native_args=['--root',str(root)]
            for name,path in zip(HNAMES,paths[1:]):
                native_args+=['--'+name,str(path)]
            native_args+=['--out',str(dest)]
            with contextlib.redirect_stdout(io.StringIO()):
                rc=hmain(native_args)
            require(rc==0 and dest.is_file(),
                    'source-bound v1h native reconstruction rejected')
            reconstructed=dest.read_bytes()
            require(reconstructed==inputs[0][0],
                    'v1h input not equal to independently reexecuted native network')
        report=json.loads(inputs[0][0])
        gbytes=inputs[1+HNAMES.index('v1g1')][0]
        dbytes=inputs[1+HNAMES.index('v1d')][0]
        result=audit(report,inputs[0][0],g_bytes=gbytes,d_bytes=dbytes)
        result['native_v1h_recomputation_verified_in_this_run']=True
        require(all(p.read_bytes()==data for p,(data,_) in zip(paths,inputs)),
                'native source references changed during audit')
        with out.open('x',encoding='utf8') as fp:
            json.dump(result,fp,indent=2,sort_keys=True,ensure_ascii=True)
            fp.write('\n')
        print(json.dumps({'status':result['status'],
              'native_recomputation':True,
              'variant_feedback_sign':result['variant_receiver_judgment_sign'],
              'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1i REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
