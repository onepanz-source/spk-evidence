#!/usr/bin/env python3
"""V1p: source-bound native exogenous A/B/C CMP interventions (no learning)."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require,snapshot
from spk_bv_research.native_operator_replay_v1b import source_snapshot
from spk_bv_research.native_causal_locus_v1p import analyze,copy_intervention,PLAN,canon
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1o_decision_disclosure import main as omain,NAMES as ONAMES

NAMES=('v1o',)+ONAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,n) for n in NAMES]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),
                'aliased source bound reports')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        raw={n:entries[i][0] for i,n in enumerate(NAMES)}
        docs={n:json.loads(blob) for n,blob in raw.items()}
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1p-v1o-') as td:
            target=Path(td)/'v1o.json'
            pargs=['--root',str(root)]
            for name in ONAMES:pargs.extend(('--'+name,str(getattr(args,name))))
            pargs.extend(('--out',str(target)))
            with contextlib.redirect_stdout(io.StringIO()):rc=omain(pargs)
            require(rc==0 and target.is_file() and target.read_bytes()==raw['v1o'],
                    'native-bound v1o recomputation byte mismatch')
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        sources=source_snapshot(root,_admit,_compute_local)
        original=fixture(); original_sha=snapshot(original)
        _,owners=_admit(original[0],original[1])
        require(snapshot(original)==original_sha,'admission mutated original fixture')
        programs={n.node_id:snapshot(n.instructions) for n in original[0].nodes}
        arms={}
        for arm,_,_,_ in PLAN:
            variant,_=copy_intervention(original,arm,programs)
            variant_sha=snapshot(variant)
            arms[arm]={}
            for mode in ('off','on'):
                policy=LiveBVPlanV0e(enabled=mode=='on',priority='forward-first')
                result=execute_live_v0e(variant[0],variant[1],*variant[2],policy)
                require(snapshot(original)==original_sha and snapshot(variant)==variant_sha,
                        'native fixture mutated during matrix')
                duplicate=execute_live_v0e(variant[0],variant[1],*variant[2],policy)
                require(result==duplicate and snapshot(original)==original_sha and
                        snapshot(variant)==variant_sha,'nondeterministic native matrix arm')
                arms[arm][mode]=result
        report=analyze(docs['v1o'],raw['v1o'],docs['v1h'],raw['v1h'],
            docs['v1m'],raw['v1m'],docs['v1d'],raw['v1d'],
            original,owners,sources,arms)
        report['native_v1o_recomputation_verified_in_this_run']=True
        report['native_matrix_repeatability_attested_in_this_run']=True
        require(sources==source_snapshot(root,_admit,_compute_local) and
                snapshot(original)==original_sha and
                all(path.read_bytes()==raw[name] for path,name in zip(paths,NAMES)),
                'source or reference changed during native matrix')
        with out.open('xb') as stream:stream.write(canon(report))
        print(json.dumps({'status':report['status'],
            'paired_contrasts':len(report['paired_contrasts_off']),
            'native_scheduler_runs':report['native_scheduler_executions_in_this_matrix'],
            'receiver_judgments':0,'learning':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1p REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
