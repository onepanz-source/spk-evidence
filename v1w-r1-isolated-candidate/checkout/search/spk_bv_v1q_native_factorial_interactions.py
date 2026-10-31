#!/usr/bin/env python3
"""BV v1q native full-factorial experiment, zero endogenous judgment claims."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require,snapshot
from spk_bv_research.native_operator_replay_v1b import source_snapshot
from spk_bv_research.native_factorial_interaction_v1q import ARMS,analyze,canon,clone
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1p_native_causal_locus import main as pmain,NAMES as PNAMES

NAMES=('v1p',)+PNAMES


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,name) for name in NAMES]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),'aliased source reports')
        out=safe_output(args.out,root,tuple(path.absolute() for path in paths))
        raw={name:entries[i][0] for i,name in enumerate(NAMES)}
        from spk_bv_research.native_factorial_interaction_v1q import validate_predecessor
        prev=json.loads(raw['v1p']);validate_predecessor(prev,raw['v1p'])
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1q-replay-v1p-') as tmp:
            target=Path(tmp)/'v1p.json'
            prev_args=['--root',str(root)]
            for name in PNAMES:prev_args+=['--'+name,str(getattr(args,name))]
            prev_args+=['--out',str(target)]
            with contextlib.redirect_stdout(io.StringIO()):rc=pmain(prev_args)
            require(rc==0 and target.is_file() and target.read_bytes()==raw['v1p'],
                    'native v1p recomputation byte mismatch')
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        sources=source_snapshot(root,_admit,_compute_local)
        native=fixture();initial=snapshot(native)
        _,owners=_admit(native[0],native[1])
        require(snapshot(native)==initial,'native fixture mutated during admission')
        pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
        runs={}
        for arm in ARMS:
            variant,_=clone(native,arm,pins)
            variant_hash=snapshot(variant)
            runs[arm]={}
            for mode in ('off','on'):
                plan=LiveBVPlanV0e(enabled=mode=='on',priority='forward-first')
                result=execute_live_v0e(variant[0],variant[1],*variant[2],plan)
                duplicate=execute_live_v0e(variant[0],variant[1],*variant[2],plan)
                require(result==duplicate and snapshot(native)==initial and
                        snapshot(variant)==variant_hash,
                        'nondeterministic factorial arm or native mutation')
                runs[arm][mode]=result
        report=analyze(prev,raw['v1p'],native,owners,sources,runs)
        report['native_v1p_recomputation_verified_in_this_run']=True
        report['native_factorial_repeatability_attested_in_this_run']=True
        require(snapshot(native)==initial and
                sources==source_snapshot(root,_admit,_compute_local) and
                all(path.read_bytes()==raw[name] for path,name in zip(paths,NAMES)),
                'source inputs or architecture changed during factorial replay')
        with out.open('xb') as fh:fh.write(canon(report))
        print(json.dumps({'status':report['status'],
            'native_scheduler_runs':report['native_scheduler_executions_in_matrix'],
            'terminal_pair_interactions':{k:report['factorial_mobius_count_coefficients']['off']['terminal'][k]
                for k in ('AB','AC','BC','ABC')},
            'native_receiver_judgments':0,'learning':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1q REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
