#!/usr/bin/env python3
"""BV v1k: reexecute native v1j and audit receiver witness authority boundary."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.receiver_witness_boundary_v1k import audit,example_protocol
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1j_silence_observability import main as jmain,NAMES as JNAMES

NAMES=('v1j',)+JNAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--shadow-protocol',type=Path,help='optional experimenter-only list; never a native witness')
    p.add_argument('--demo-shadow',action='store_true',help='source-independent logical negative controls')
    a=p.parse_args(argv)
    try:
        require(not (a.shadow_protocol and a.demo_shadow),'choose supplied shadow protocol OR demo')
        root=a.root.resolve(strict=True)
        paths=tuple(getattr(a,n) for n in NAMES)+((a.shadow_protocol,) if a.shadow_protocol else ())
        data=[safe_input(x,root) for x in paths]
        require(len({ident for _,ident in data})==len(data),'aliased source files')
        out=safe_output(a.out,root,tuple(x.absolute() for x in paths))
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1k-native-replay-') as td:
            result=Path(td)/'v1j.json'
            cmd=['--root',str(root)]
            for n,path in zip(JNAMES,paths[1:]):cmd+=['--'+n,str(path)]
            cmd+=['--out',str(result)]
            with contextlib.redirect_stdout(io.StringIO()):rc=jmain(cmd)
            require(rc==0 and result.is_file() and result.read_bytes()==data[0][0],
                    'source-recomputed v1j mismatch')
        raw={n:data[i][0] for i,n in enumerate(NAMES)}
        shadows=None
        if a.shadow_protocol:
            shadows=json.loads(data[-1][0])
        elif a.demo_shadow:
            shadows=[example_protocol(expectation_id='shadow.missing'),
                     example_protocol(expectation_id='shadow.pending',deadline_tick=9),
                     example_protocol(expectation_id='shadow.gap',coverage_end_tick=7),
                     example_protocol(expectation_id='shadow.seen',observed_ids=['shadow.future.event.1'])]
        report=audit(json.loads(raw['v1j']),raw['v1j'],
                     v1i_bytes=raw['v1i'],v1h_bytes=raw['v1h'],
                     v1g1_bytes=raw['v1g1'],shadow=shadows)
        report['native_v1j_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==r for path,(r,_) in zip(paths,data)),
                'input changed during replay')
        with out.open('x',encoding='utf8') as f:
            json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=True);f.write('\n')
        print(json.dumps({'status':report['status'],'shadow_scenarios':len(report['shadow_scenarios']),
                          'native_absence_witnesses':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1k REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
