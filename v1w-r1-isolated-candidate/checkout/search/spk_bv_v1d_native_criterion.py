#!/usr/bin/env python3
"""Source-bound v1d declared synthetic guard criterion on native A1 local kernel."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_criterion_v1d import build
from spk_bv_research.native_operator_replay_v1b import generate,source_snapshot
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--v1c',type=Path,required=True)
    p.add_argument('--v1b1',type=Path,required=True)
    p.add_argument('--v1a',type=Path,required=True)
    p.add_argument('--v0w',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        paths=(a.v1c,a.v1b1,a.v1a,a.v0w)
        entries=[safe_input(x,root) for x in paths]
        if len({x[1] for x in entries})!=len(paths):
            raise InterventionError('aliased references')
        out=safe_output(a.out,root,tuple(x.absolute() for x in paths))
        v1cb,v1b1b,v1ab,wbytes=[x[0] for x in entries]
        v1c,v1b1,v1a,w=[json.loads(x) for x in (v1cb,v1b1b,v1ab,wbytes)]
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        native_baseline=generate(v1a,w,wbytes,fixture,execute_live_v0e,
                                LiveBVPlanV0e,_admit,_compute_local,root=root)
        native=fixture()
        report=build(v1c,v1cb,v1b1,v1b1b,v1a,w,wbytes,native_baseline,native,_admit,_compute_local)
        if [p.read_bytes() for p in paths] != [v1cb,v1b1b,v1ab,wbytes]:
            raise InterventionError('reference changed during experiment')
        if report['frozen_native_sources'] != source_snapshot(root,_admit,_compute_local):
            raise InterventionError('frozen native source changed during experiment')
        with out.open('x',encoding='utf8') as f:
            json.dump(report,f,sort_keys=True,indent=2,ensure_ascii=True);f.write('\n')
        print(json.dumps({'status':report['status'],'selected_candidate_position':report['selected_candidate_position'],
            'evaluation_delta':report['evaluation']['correct_count_delta'],
            'native_learning_proven':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1d REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
