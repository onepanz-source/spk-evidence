#!/usr/bin/env python3
"""SPK BV v1t: source-replayed native posthoc A->B trace to isolated B mailbox."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_trace_mailbox_adapter_v1t import analyze,validate_inputs
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1s_receiver_disclosure_channel import main as smain,NAMES as SNAMES

NAMES=('v1s',)+SNAMES

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=[getattr(args,n) for n in NAMES]
        entries=[safe_input(p,root) for p in paths]
        require(len({identity for _,identity in entries})==len(entries),'aliased source inputs')
        output=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        blobs={name:entries[i][0] for i,name in enumerate(NAMES)}
        s=json.loads(blobs['v1s']);m=json.loads(blobs['v1m'])
        validate_inputs(s,blobs['v1s'],m,blobs['v1m'])
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1t-native-replay-') as td:
            rebuilt=Path(td)/'v1s.json'
            chain=['--root',str(root)]
            for name in SNAMES:chain+=['--'+name,str(getattr(args,name))]
            chain+=['--out',str(rebuilt)]
            with contextlib.redirect_stdout(io.StringIO()):rc=smain(chain)
            require(rc==0 and rebuilt.is_file() and rebuilt.read_bytes()==blobs['v1s'],
                    'full native-source-bound v1s recomputation byte mismatch')
        report=analyze(s,blobs['v1s'],m,blobs['v1m'])
        report['inherited_native_v1s_recomputation_verified_in_this_run']=True
        require(all(p.read_bytes()==blobs[name] for name,p in zip(NAMES,paths)),
                'source files mutated during replay')
        with output.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
            'lab_sessions':report['shadow_lab_session_count'],
            'native_channel':False,'native_receiver_judgments':0,
            'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1t REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
