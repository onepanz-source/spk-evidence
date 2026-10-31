#!/usr/bin/env python3
"""SPK BV v1w: additive observer-seam feasibility, not an installed live hook."""
from __future__ import annotations
import argparse, contextlib, io, json, sys, tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import analyze, read_pinned_sources
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from search.spk_bv_v1v_frozen_observation_surface import main as vmain, NAMES as VNAMES

NAMES = ('v1v',) + VNAMES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:
        p.add_argument('--'+n,type=Path,required=(n=='v1v'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true',
        help='offline design ONLY: no frozen native source or inherited replay verification')
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        names=('v1v',) if a.contract_only else NAMES
        require(a.contract_only or all(getattr(a,n) is not None for n in NAMES),
                'all predecessor reports required for source-bound mode')
        paths=[getattr(a,n) for n in names]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),
                'aliased predecessor reports')
        output=safe_output(a.out,root,tuple(path.absolute() for path in paths))
        raw={n:entries[i][0] for i,n in enumerate(names)}
        v=json.loads(raw['v1v'])
        blobs=None if a.contract_only else read_pinned_sources(root)
        report=analyze(v,raw['v1v'],blobs=blobs)
        if not a.contract_only:
            with tempfile.TemporaryDirectory(prefix='spk-bv-v1w-replay-v1v-') as td:
                reproduced=Path(td)/'v1v.json'
                prev=['--root',str(root)]
                for n in VNAMES:
                    prev.extend(('--'+n,str(getattr(a,n))))
                prev.extend(('--out',str(reproduced)))
                with contextlib.redirect_stdout(io.StringIO()):rc=vmain(prev)
                require(rc==0 and reproduced.is_file() and
                        reproduced.read_bytes()==raw['v1v'],
                        'v1v complete inherited replay byte mismatch')
            require(blobs==read_pinned_sources(root),
                    'frozen source changed during inherited replay')
            report['inherited_native_v1v_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==raw[n] for path,n in zip(paths,names)),
                'predecessor changed during read-only audit')
        with output.open('xb') as fp:fp.write(canon(report))
        print(json.dumps({'status':report['status'],
          'source_ast_audited':report['native_source_readonly_bytes_rechecked_in_this_run'],
          'v1v_replayed':report['inherited_native_v1v_recomputation_verified_in_this_run'],
          'live_receiver_messages':0,'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,SyntaxError) as exc:
        print('SPK BV v1w REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
