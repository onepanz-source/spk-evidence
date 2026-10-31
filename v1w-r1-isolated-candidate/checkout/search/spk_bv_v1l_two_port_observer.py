#!/usr/bin/env python3
"""BV v1l: source-bound native-v1k replay, then an isolated lab observer demo."""
from __future__ import annotations
import argparse,contextlib,io,json,sys,tempfile
from pathlib import Path
from spk_bv_research.off_on_v0t import require
from spk_bv_research.observer_closed_world_v1l import audit
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from search.spk_bv_v1k_witness_authority import main as kmain,NAMES as KNAMES

NAMES=('v1k',)+KNAMES

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--demo-lab',action='store_true')
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=[getattr(a,n) for n in NAMES]
        items=[safe_input(x,root) for x in paths]
        require(len({i for _,i in items})==len(items),'aliased inputs')
        out=safe_output(a.out,root,tuple(x.absolute() for x in paths))
        with tempfile.TemporaryDirectory(prefix='spk-bv-v1l-replay-') as td:
            tempout=Path(td)/'v1k.json'
            args=['--root',str(root)]
            for n,path in zip(KNAMES,paths[1:]):args+=['--'+n,str(path)]
            # Match an attested v1k demo reference, if it used demo-shadow.
            k=json.loads(items[0][0])
            if k.get('shadow_plan_supplied'):
                # Only exact built-in v1k demo scenarios are supported for
                # recreation. Other shadow plans require externally supplied
                # original protocol, not a guessed equivalent.
                from spk_bv_research.receiver_witness_boundary_v1k import example_protocol
                from hashlib import sha256
                shadows=[example_protocol(expectation_id='shadow.missing'),
                    example_protocol(expectation_id='shadow.pending',deadline_tick=9),
                    example_protocol(expectation_id='shadow.gap',coverage_end_tick=7),
                    example_protocol(expectation_id='shadow.seen',observed_ids=['shadow.future.event.1'])]
                hashes=[sha256(json.dumps(z,sort_keys=True,separators=(',',':')).encode()).hexdigest() for z in shadows]
                require([z.get('shadow_protocol_sha256') for z in k.get('shadow_scenarios',[])]==hashes,
                        'v1k non-demo shadow protocol requires explicit replay support')
                args+=['--demo-shadow']
            args+=['--out',str(tempout)]
            with contextlib.redirect_stdout(io.StringIO()):rc=kmain(args)
            require(rc==0 and tempout.is_file() and tempout.read_bytes()==items[0][0],
                    'native v1k recomputation byte mismatch')
        raw={n:items[i][0] for i,n in enumerate(NAMES)}
        r=audit(json.loads(raw['v1k']),raw['v1k'],jbytes=raw['v1j'],
                ibytes=raw['v1i'],hbytes=raw['v1h'],gbytes=raw['v1g1'],demo=a.demo_lab)
        r['native_v1k_recomputation_verified_in_this_run']=True
        require(all(path.read_bytes()==b for path,(b,_) in zip(paths,items)),
                'source files changed during replay')
        with out.open('x',encoding='utf8') as f:
            json.dump(r,f,sort_keys=True,indent=2,ensure_ascii=True);f.write('\n')
        print(json.dumps({'status':r['status'],'lab_cases':len(r['lab_cases']),
                          'native_absence_witnesses':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v1l REJECTED: '+str(ex),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
