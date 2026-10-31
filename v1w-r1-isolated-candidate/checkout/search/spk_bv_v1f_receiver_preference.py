#!/usr/bin/env python3
"""Recompute source-bound v1e then report declared receiver preference polarity.

Requires the frozen Architecture v1 runtime and prior research modules on fwork.
No receiver originated judgment, native operator update or learning.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_operator_replay_v1b import generate,source_snapshot
from spk_bv_research.native_criterion_v1d import build as v1d_build
from spk_bv_research.receiver_impact_v1e import build as v1e_build
from spk_bv_research.receiver_preference_v1f import build as v1f_build
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    for n in ('v1e','v1d','v1c','v1b1','v1a','v0w'):
        parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=tuple(getattr(a,n) for n in ('v1e','v1d','v1c','v1b1','v1a','v0w'))
        entries=[safe_input(p,root) for p in paths]
        if len({ident for _,ident in entries})!=len(entries):
            raise InterventionError('aliased reference inputs')
        output=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        eb,db,cb,bb,ab,wb=[r[0] for r in entries]
        e,d,c,b,aa,w=[json.loads(blob) for blob in (eb,db,cb,bb,ab,wb)]
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        sources_before=source_snapshot(root,_admit,_compute_local)
        base=generate(aa,w,wb,fixture,execute_live_v0e,LiveBVPlanV0e,
                      _admit,_compute_local,root=root)
        original=fixture()
        reconstructed_d=v1d_build(c,cb,b,bb,aa,w,wb,base,original,_admit,_compute_local)
        reconstructed_e=v1e_build(d,db,reconstructed_d,original,_admit,_compute_local)
        report=v1f_build(e,eb,reconstructed_e)
        if [p.read_bytes() for p in paths]!=[eb,db,cb,bb,ab,wb]:
            raise InterventionError('reference input changed during experiment')
        if sources_before!=source_snapshot(root,_admit,_compute_local) or \
           report['frozen_native_sources']!=sources_before:
            raise InterventionError('frozen sources changed during experiment')
        with output.open('x',encoding='utf8') as file:
            json.dump(report,file,sort_keys=True,indent=2,ensure_ascii=True)
            file.write('\n')
        print(json.dumps({'status':report['status'],
                          'receiver_pairs':report['native_conditional_pairs'],
                          'polarity_reversed':report['preference_polarity_reversed_on_different_pairs'],
                          'native_judgments_observed':0,'native_learning_proven':False,
                          'out':str(output)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1f REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
