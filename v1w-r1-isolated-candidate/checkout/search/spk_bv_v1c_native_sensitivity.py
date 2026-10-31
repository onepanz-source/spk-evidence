#!/usr/bin/env python3
"""Run bounded read-only native A1 operand sensitivity, source-bound to v1b.1."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.native_sensitivity_v1c import build
from spk_bv_research.native_operator_replay_v1b import generate
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--v1b1',type=Path,required=True)
    p.add_argument('--v1a',type=Path,required=True)
    p.add_argument('--v0w',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        inputs=[safe_input(f,root) for f in (a.v1b1,a.v1a,a.v0w)]
        if len({i[1] for i in inputs})!=3:
            raise InterventionError('aliased input references')
        out=safe_output(a.out,root,(a.v1b1.absolute(),a.v1a.absolute(),a.v0w.absolute()))
        v1bb,v1ab,wb=(entry[0] for entry in inputs)
        v1b=json.loads(v1bb);v1a=json.loads(v1ab);w=json.loads(wb)
        # Native imports only after safe file validation.
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        native_baseline=generate(v1a,w,wb,fixture,execute_live_v0e,
                                 LiveBVPlanV0e,_admit,_compute_local,root=root)
        native=fixture()
        report=build(v1b,v1bb,v1a,w,wb,native_baseline,native,_admit,_compute_local)
        if [path.read_bytes() for path in (a.v1b1,a.v1a,a.v0w)]!=[v1bb,v1ab,wb]:
            raise InterventionError('reference input changed during probe')
        # verify source custody again, after the study, not just before it
        from spk_bv_research.native_operator_replay_v1b import source_snapshot
        assert report['frozen_native_sources']==source_snapshot(root,_admit,_compute_local)
        with out.open('x',encoding='utf8') as fd:
            json.dump(report,fd,sort_keys=True,indent=2,ensure_ascii=True);fd.write('\n')
        print(json.dumps({'status':report['status'],'probe_pairs':report['probe_pairs'],
             'different':report['different_pairs'],'rejected':report['rejected_pairs'],
             'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1c REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
