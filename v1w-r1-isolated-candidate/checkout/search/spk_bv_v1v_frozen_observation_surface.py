#!/usr/bin/env python3
"""BV v1v: frozen native source API surface inventory; NO event hook installed."""
from __future__ import annotations
import argparse, contextlib, io, json, sys, tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.frozen_observation_surface_v1v import audit_surface,read_pinned_sources
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1u_incremental_shadow_channel import main as umain,NAMES as UNAMES

NAMES=('v1u',)+UNAMES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,type=Path,required=(n=='v1u'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true',
                   help='offline report WITHOUT native source inspection or inherited replay')
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        names=('v1u',) if a.contract_only else NAMES
        if not a.contract_only:
            require(all(getattr(a,n) is not None for n in NAMES),
                    'native mode requires ALL predecessor reports')
        paths=[getattr(a,n) for n in names]
        entries=[safe_input(path,root) for path in paths]
        require(len({i for _,i in entries})==len(entries),'predecessor file alias')
        output=safe_output(a.out,root,tuple(path.absolute() for path in paths))
        raw={n:entries[i][0] for i,n in enumerate(names)}
        u=json.loads(raw['v1u'])
        sources=None if a.contract_only else read_pinned_sources(root,u)
        report=audit_surface(u,raw['v1u'],sources)
        if not a.contract_only:
            with tempfile.TemporaryDirectory(prefix='spk-bv-v1v-replay-v1u-') as td:
                reproduced=Path(td)/'v1u.json'
                prev=['--root',str(root)]
                for n in UNAMES:prev.extend(('--'+n,str(getattr(a,n))))
                prev.extend(('--out',str(reproduced)))
                with contextlib.redirect_stdout(io.StringIO()):rc=umain(prev)
                require(rc==0 and reproduced.is_file() and
                        reproduced.read_bytes()==raw['v1u'],
                        'full native v1u predecessor replay byte mismatch')
            require(sources==read_pinned_sources(root,u),
                    'frozen source changed during predecessor replay')
            report['inherited_native_v1u_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==raw[n] for path,n in zip(paths,names)),
                'predecessor changed during v1v inspection')
        with output.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
             'static_frozen_source_audit':report['frozen_source_bytes_rechecked_in_this_run'],
             'inherited_native_replay':report['inherited_native_v1u_recomputation_verified_in_this_run'],
             'native_live_receiver_channel':False,'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,SyntaxError) as exc:
        print('SPK BV v1v REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
