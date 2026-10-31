#!/usr/bin/env python3
"""BV v1r native-source-bound posthoc factorial allocation ambiguity report."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import analyze,canon,validate_q
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1q_native_factorial_interactions import main as qmain,NAMES as QNAMES

NAMES=('v1q',)+QNAMES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,name) for name in NAMES]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),'aliased source reports')
        out=safe_output(args.out,root,tuple(path.absolute() for path in paths))
        raw={name:entries[i][0] for i,name in enumerate(NAMES)}
        q=json.loads(raw['v1q']);validate_q(q,raw['v1q'])
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1r-recompute-v1q-') as tmp:
            rebuilt=Path(tmp)/'v1q.json'
            call=['--root',str(root)]
            for name in QNAMES:call+=['--'+name,str(getattr(args,name))]
            call+=['--out',str(rebuilt)]
            with contextlib.redirect_stdout(io.StringIO()):rc=qmain(call)
            require(rc==0 and rebuilt.is_file() and rebuilt.read_bytes()==raw['v1q'],
                    'source-bound native v1q recomputation byte mismatch')
        report=analyze(q,raw['v1q'])
        report['native_v1q_recomputation_verified_in_this_run']=True
        require(all(p.read_bytes()==raw[n] for p,n in zip(paths,NAMES)),
                'source report changed during analysis')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
            'terminal_intervention_allocation':report['posthoc_rational_allocation']['off']['terminal']['suppress_activity']['equal_permutation_average'],
            'terminal_overcount_correction':report['nonadditivity_diagnostics']['off']['terminal']['nonadditive_correction'],
            'endogenous_credit':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1r REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
