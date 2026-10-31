#!/usr/bin/env python3
"""Source-bound conditional recipient impact, not actual network feedback."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_criterion_v1d import build as v1d_build
from spk_bv_research.native_operator_replay_v1b import generate,source_snapshot
from spk_bv_research.receiver_impact_v1e import build
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for item in ('v1d','v1c','v1b1','v1a','v0w'):
        p.add_argument('--'+item,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        inputs=(a.v1d,a.v1c,a.v1b1,a.v1a,a.v0w)
        entries=[safe_input(x,root) for x in inputs]
        if len({ident for _,ident in entries})!=len(entries):
            raise InterventionError('aliased native reference inputs')
        output=safe_output(a.out,root,inputs)
        dbytes,cbytes,bbytes,abytes,wbytes=[x[0] for x in entries]
        d,c,b,aa,w=[json.loads(data) for data in (dbytes,cbytes,bbytes,abytes,wbytes)]
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        before_sources=source_snapshot(root,_admit,_compute_local)
        base=generate(aa,w,wbytes,fixture,execute_live_v0e,LiveBVPlanV0e,
                      _admit,_compute_local,root=root)
        original=fixture()
        reconstructed=v1d_build(c,cbytes,b,bbytes,aa,w,wbytes,base,original,
                                _admit,_compute_local)
        doc=build(d,dbytes,reconstructed,original,_admit,_compute_local)
        if [x.read_bytes() for x in inputs]!=[dbytes,cbytes,bbytes,abytes,wbytes]:
            raise InterventionError('reference input changed during experiment')
        if before_sources!=source_snapshot(root,_admit,_compute_local) or \
           doc['frozen_native_sources']!=before_sources:
            raise InterventionError('frozen native sources changed during experiment')
        with output.open('x',encoding='utf8') as stream:
            json.dump(doc,stream,indent=2,sort_keys=True,ensure_ascii=True)
            stream.write('\n')
        print(json.dumps({'status':doc['status'],
            'receiver_pairs':doc['receiver_probe']['receiver_pairs'],
            'different_pairs':doc['receiver_probe']['different_pairs'],
            'route_attested':False,'native_judgments_observed':0,
            'native_learning_proven':False,'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1e REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
