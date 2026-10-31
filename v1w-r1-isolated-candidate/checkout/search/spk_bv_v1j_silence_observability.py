#!/usr/bin/env python3
"""v1j native source-bound observability. Reexecute v1i before attestation."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_silence_observability_v1j import audit
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1i_native_feedback_silence import main as imain, NAMES as INAMES

NAMES=('v1i',)+INAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=tuple(getattr(a,n) for n in NAMES)
        raw=[safe_input(x,root) for x in paths]
        require(len({id_ for _,id_ in raw})==len(raw), 'aliased reference inputs')
        out=safe_output(a.out,root,tuple(x.absolute() for x in paths))
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1j-recompute-') as td:
            fresh=Path(td)/'v1i.json'
            cmd=['--root',str(root)]
            for n,path in zip(INAMES,paths[1:]):cmd.extend(('--'+n,str(path)))
            cmd.extend(('--out',str(fresh)))
            with contextlib.redirect_stdout(io.StringIO()):
                rc=imain(cmd)
            require(rc==0 and fresh.is_file() and fresh.read_bytes()==raw[0][0],
                    'v1i independent native reexecution byte mismatch')
        def by(n):return raw[NAMES.index(n)][0]
        result=audit(json.loads(by('v1i')),by('v1i'),
                    v1h=json.loads(by('v1h')),v1h_bytes=by('v1h'),
                    v1g1=json.loads(by('v1g1')),v1g1_bytes=by('v1g1'),
                    v1d_bytes=by('v1d'))
        result['native_v1i_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==buf for path,(buf,_) in zip(paths,raw)),
                'source reference changed during audit')
        with out.open('x',encoding='utf8') as f:
            json.dump(result,f,sort_keys=True,indent=2,ensure_ascii=True);f.write('\n')
        print(json.dumps({'status':result['status'],
             'source_bound_receiver_observations':len(result['source_bound_observers']),
             'native_absence_witnesses':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as e:
        print('SPK BV v1j REJECTED: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
