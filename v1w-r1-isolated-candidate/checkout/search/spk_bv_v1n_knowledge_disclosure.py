#!/usr/bin/env python3
"""BV v1n source-bound receiver disclosure lower-bound (no native monitor)."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_knowledge_disclosure_v1n import analyze
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1m_native_passive_projection import main as mmain,NAMES as MNAMES

NAMES=('v1m',)+MNAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=[getattr(a,n) for n in NAMES]
        entries=[safe_input(x,root) for x in paths]
        require(len({i for _,i in entries})==len(entries),'aliased report inputs')
        out=safe_output(a.out,root,tuple(x.absolute() for x in paths))
        blobs={n:entries[i][0] for i,n in enumerate(NAMES)}
        docs={n:json.loads(blobs[n]) for n in NAMES}
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1n-v1m-') as td:
            target=Path(td)/'v1m.json'
            args=['--root',str(root)]
            for n in MNAMES:args+=['--'+n,str(getattr(a,n))]
            args+=['--out',str(target)]
            with contextlib.redirect_stdout(io.StringIO()):rc=mmain(args)
            require(rc==0 and target.is_file() and target.read_bytes()==blobs['v1m'],
                    'source-bound v1m native replay byte mismatch')
        report=analyze(docs['v1m'],blobs['v1m'],docs['v1l'],blobs['v1l'],
                       docs['v1h'],blobs['v1h'],docs['v1g1'],blobs['v1g1'],
                       docs['v1d'],blobs['v1d'])
        report['native_v1m_recomputation_verified_in_this_run']=True
        require(all(p.read_bytes()==blobs[n] for p,n in zip(paths,NAMES)),
                'input reference changed during replay')
        with out.open('x',encoding='utf8') as f:
            json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=True); f.write('\n')
        print(json.dumps({'status':report['status'],'native_v1m_recomputed':True,
                          'shadow_worlds':len(report['shadow_worlds']),
                          'native_absence_witnesses':0,'native_learning_proven':False,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1n REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
