#!/usr/bin/env python3
"""BV v1o: native-bound T4 hypothetical decision disclosures (no native receiver channel)."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.decision_disclosure_boundary_v1o import analyze,canon
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1n_knowledge_disclosure import main as nmain,NAMES as NNAMES

NAMES=('v1n',)+NNAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=[getattr(a,name) for name in NAMES]
        entries=[safe_input(x,root) for x in paths]
        require(len({i for _,i in entries})==len(entries),'aliased report inputs')
        out=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        blobs={name:entries[i][0] for i,name in enumerate(NAMES)}
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1o-v1n-') as td:
            target=Path(td)/'v1n.json'
            params=['--root',str(root)]
            for name in NNAMES:params.extend(('--'+name,str(getattr(a,name))))
            params.extend(('--out',str(target)))
            with contextlib.redirect_stdout(io.StringIO()):rc=nmain(params)
            require(rc==0 and target.is_file() and target.read_bytes()==blobs['v1n'],
                    'native-bound v1n recomputation byte mismatch')
        n=json.loads(blobs['v1n']);m=json.loads(blobs['v1m'])
        report=analyze(n,blobs['v1n'],m,blobs['v1m'])
        report['native_v1n_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==blobs[name] for path,name in zip(paths,NAMES)),
                'input reference changed during replay')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],'native_v1n_recomputed':True,
                          'shadow_cases':report['shadow_case_count'],
                          'native_authenticated_decision_records':0,
                          'native_learning_proven':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1o REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
