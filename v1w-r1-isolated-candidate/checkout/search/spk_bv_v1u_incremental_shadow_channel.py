#!/usr/bin/env python3
"""BV v1u: full v1t replay custody then bounded incrementally delivered SHADOW messages.

Native scheduler is NOT instrumented; laboratory ticks are synthetic and the
source traces are post-hoc. Never interpret this as a live native BV channel.
"""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.incremental_shadow_channel_v1u import analyze
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1t_native_trace_mailbox_adapter import main as tmain,NAMES as TNAMES

NAMES=('v1t',)+TNAMES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=[getattr(a,n) for n in NAMES]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),
                'aliased predecessor inputs')
        out=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        raw={n:entries[i][0] for i,n in enumerate(NAMES)}
        t=json.loads(raw['v1t'])
        report=analyze(t,raw['v1t'])
        # There is no new native event hook. This replay verifies the inherited
        # source provenance all the way down to the frozen v0e scheduler.
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1u-replay-v1t-') as td:
            rebuilt=Path(td)/'v1t.json'
            args=['--root',str(root)]
            for n in TNAMES:args.extend(('--'+n,str(getattr(a,n))))
            args.extend(('--out',str(rebuilt)))
            with contextlib.redirect_stdout(io.StringIO()):rc=tmain(args)
            require(rc==0 and rebuilt.is_file() and rebuilt.read_bytes()==raw['v1t'],
                    'native-bound v1t recomputation byte mismatch')
        require(all(path.read_bytes()==raw[n] for path,n in zip(paths,NAMES)),
                'predecessor mutated during verification')
        report['inherited_native_v1t_recomputation_verified_in_this_run']=True
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'shadow_incremental_sessions':report['lab_incremental_session_count'],
                          'native_callback_connected':False,
                          'native_scored_receiver_judgments':0,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1u REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
