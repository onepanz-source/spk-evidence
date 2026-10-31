#!/usr/bin/env python3
"""Recompute native v1f then attest original static/realized forward and reverse lineage.

Never implies that the hypothetical v1e variant ran through a native network.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.off_on_v0t import InterventionError,snapshot,require
from spk_bv_research.native_operator_replay_v1b import generate,source_snapshot
from spk_bv_research.native_criterion_v1d import build as v1d_build
from spk_bv_research.receiver_impact_v1e import build as v1e_build
from spk_bv_research.receiver_preference_v1f import build as v1f_build
from spk_bv_research.native_route_lineage_v1g import build as v1g_build
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output

NAMES=('v1f','v1e','v1d','v1c','v1b1','v1a','v0w')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    a=parser.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=tuple(getattr(a,n) for n in NAMES)
        entries=[safe_input(p,root) for p in paths]
        require(len({ident for _,ident in entries})==len(entries),'aliased reference inputs')
        out=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        fb,eb,db,cb,bb,ab,wb=(x[0] for x in entries)
        f,e,d,c,b,aa,w=[json.loads(x) for x in (fb,eb,db,cb,bb,ab,wb)]
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        before=source_snapshot(root,_admit,_compute_local)
        base=generate(aa,w,wb,fixture,execute_live_v0e,LiveBVPlanV0e,
                      _admit,_compute_local,root=root)
        native=fixture(); native_hash=snapshot(native)
        recomputed_d=v1d_build(c,cb,b,bb,aa,w,wb,base,native,_admit,_compute_local)
        recomputed_e=v1e_build(d,db,recomputed_d,native,_admit,_compute_local)
        recomputed_f=v1f_build(e,eb,recomputed_e)
        require(native_hash==snapshot(native),"frozen fixture mutated by upstream replay")
        nodes,owners=_admit(native[0],native[1])
        require(snapshot(native)==native_hash,"_admit mutated native fixture")
        off=execute_live_v0e(native[0],native[1],*native[2],LiveBVPlanV0e(enabled=False,priority='forward-first'))
        on=execute_live_v0e(native[0],native[1],*native[2],LiveBVPlanV0e(enabled=True,priority='forward-first'))
        report=v1g_build(f,fb,recomputed_f,native,off,on,owners,before)
        require(snapshot(native)==native_hash and before==source_snapshot(root,_admit,_compute_local),
                'frozen input or source drifted')
        require(all(p.read_bytes()==raw for p,raw in zip(paths,(fb,eb,db,cb,bb,ab,wb))),
                'reference files changed')
        with out.open('x',encoding='utf8') as fp:
            json.dump(report,fp,sort_keys=True,indent=2,ensure_ascii=True);fp.write('\n')
        print(json.dumps({'status':report['status'],
                          'static_routes':report['static_route_count'],
                          'forward_occurrences':report['original_off_occurrences'],
                          'reverse_deliveries':report['native_reverse_delivery_count'],
                          'receivers':report['conditional_receiver_route_audit'],
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1g REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
