#!/usr/bin/env python3
"""BV v1m native post-hoc trace projection, with complete v1l predecessor replay."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require,snapshot
from spk_bv_research.native_network_counterfactual_v1h import variant_fixture
from spk_bv_research.native_operator_replay_v1b import source_snapshot
from spk_bv_research.native_passive_trace_projection_v1m import analyze
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1l_two_port_observer import main as lmain,NAMES as LNAMES

NAMES=('v1l',)+LNAMES


def native_execution(d,root):
    """Re-run four frozen native scheduler arms; NEVER patch production modules."""
    from search.spk_bv_v0e_live_evidence import fixture
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
    sources=source_snapshot(root,_admit,_compute_local)
    native=fixture(); initial=snapshot(native)
    _,owners=_admit(native[0],native[1])
    require(snapshot(native)==initial,'native fixture changed under admission')
    changed,details=variant_fixture(native,d)
    require(details.get('original_nodes_unchanged') is True,'not isolated intervention')
    changed_hash=snapshot(changed)
    runs={}
    for name,case in (('original',native),('variant',changed)):
        runs[name]={}
        for mode in ('off','on'):
            p=LiveBVPlanV0e(enabled=mode=='on',priority='forward-first')
            runs[name][mode]=execute_live_v0e(case[0],case[1],*case[2],p)
            require(snapshot(native)==initial and snapshot(changed)==changed_hash,
                    'native frozen case/variant changed during execution')
    require(sources==source_snapshot(root,_admit,_compute_local),
            'native module source changed during execution')
    return native,runs,owners,sources


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=[getattr(a,n) for n in NAMES]
        entries=[safe_input(p,root) for p in paths]
        require(len({i for _,i in entries})==len(entries),'aliased report input')
        output=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        blobs={name:entries[i][0] for i,name in enumerate(NAMES)}
        decoded={name:json.loads(blob) for name,blob in blobs.items()}
        require(decoded['v1l'].get('demo_lab_requested') is True and
                len(decoded['v1l'].get('lab_cases',()))==10,
                'v1m requires source-bound v1l --demo-lab predecessor')
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1m-v1l-') as td:
            reproduced=Path(td)/'v1l.json'
            largs=['--root',str(root)]
            for name in LNAMES:largs+=['--'+name,str(getattr(a,name))]
            largs+=['--demo-lab','--out',str(reproduced)]
            with contextlib.redirect_stdout(io.StringIO()):rc=lmain(largs)
            require(rc==0 and reproduced.is_file() and
                    reproduced.read_bytes()==blobs['v1l'],
                    'source-bound v1l native replay did not match byte-for-byte')
        native,runs,owners,sources=native_execution(decoded['v1d'],root)
        report=analyze(decoded['v1l'],blobs['v1l'],decoded['v1h'],blobs['v1h'],
                       decoded['v1g1'],blobs['v1g1'],decoded['v1d'],blobs['v1d'],
                       native,runs,owners,sources)
        require(all(p.read_bytes()==blobs[n] for p,n in zip(paths,NAMES)),
                'source reference changed during verification')
        with output.open('x',encoding='utf8') as f:
            json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=True)
            f.write('\n')
        print(json.dumps({'status':report['status'],
              'full_native_scheduler_runs_recomputed':4,
              'native_absence_certificates':0,'native_learning_proven':False,
              'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1m REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
