#!/usr/bin/env python3
"""Native A/B/C variant-network OFF/ON replay after a v1g.1 source-bound audit.

Full source-bound reconstruction first. Research-only copy intervention;
no feedback-derived choice, runtime modification, utility or learning.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from spk_bv_research.off_on_v0t import require,snapshot
from spk_bv_research.native_operator_replay_v1b import generate,source_snapshot
from spk_bv_research.native_criterion_v1d import build as v1d_build
from spk_bv_research.receiver_impact_v1e import build as v1e_build
from spk_bv_research.receiver_preference_v1f import build as v1f_build
from spk_bv_research.native_route_lineage_v1g import build as v1g_build
from spk_bv_research.native_network_counterfactual_v1h import variant_fixture,build
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output

NAMES=('v1g1','v1f','v1e','v1d','v1c','v1b1','v1a','v0w')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        paths=tuple(getattr(args,n) for n in NAMES)
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),
                'reference inputs alias one another')
        out=safe_output(args.out,root,tuple(path.absolute() for path in paths))
        blobs=[item[0] for item in entries]
        gblob,fblob,eblob,dblob,cblob,bblob,ablob,wblob=blobs
        g,f,e,d,c,b,a,w=[json.loads(blob) for blob in blobs]
        from search.spk_bv_v0e_live_evidence import fixture
        from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
        from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
        before_sources=source_snapshot(root,_admit,_compute_local)
        baseline=generate(a,w,wblob,fixture,execute_live_v0e,LiveBVPlanV0e,
                          _admit,_compute_local,root=root)
        native=fixture(); native_hash=snapshot(native)
        rd=v1d_build(c,cblob,b,bblob,a,w,wblob,baseline,native,_admit,_compute_local)
        re=v1e_build(d,dblob,rd,native,_admit,_compute_local)
        rf=v1f_build(e,eblob,re)
        nodes,owners=_admit(native[0],native[1])
        require(snapshot(native)==native_hash,'admission mutated native fixture')
        original_off=execute_live_v0e(native[0],native[1],*native[2],
                                       LiveBVPlanV0e(enabled=False,priority='forward-first'))
        original_on=execute_live_v0e(native[0],native[1],*native[2],
                                      LiveBVPlanV0e(enabled=True,priority='forward-first'))
        rg=v1g_build(f,fblob,rf,native,original_off,original_on,owners,before_sources)
        require(rg==g,'native v1g.1 source-bound reconstruction differs from reference')
        require(snapshot(native)==native_hash,'original fixture changed during audit')
        modified,_=variant_fixture(native,d)
        modified_hash=snapshot(modified)
        candidate_off=execute_live_v0e(modified[0],modified[1],*modified[2],
                                        LiveBVPlanV0e(enabled=False,priority='forward-first'))
        require(snapshot(modified)==modified_hash and snapshot(native)==native_hash,
                'variant execution mutated fixture')
        candidate_on=execute_live_v0e(modified[0],modified[1],*modified[2],
                                       LiveBVPlanV0e(enabled=True,priority='forward-first'))
        require(snapshot(modified)==modified_hash and snapshot(native)==native_hash,
                'variant ON execution mutated fixture')
        # Cross-run deterministic identity, not only a summary comparison.
        check_off=execute_live_v0e(modified[0],modified[1],*modified[2],
                                   LiveBVPlanV0e(enabled=False,priority='forward-first'))
        check_on=execute_live_v0e(modified[0],modified[1],*modified[2],
                                  LiveBVPlanV0e(enabled=True,priority='forward-first'))
        require(candidate_off==check_off and candidate_on==check_on,
                'native candidate replay nondeterministic')
        report=build(native,g,gblob,d,dblob,original_off,original_on,candidate_off,
                     candidate_on,owners,before_sources)
        require(snapshot(modified)==modified_hash and snapshot(native)==native_hash and
                before_sources==source_snapshot(root,_admit,_compute_local),
                'native sources or fixture changed during counterfactual')
        require(all(path.read_bytes()==blob for path,blob in zip(paths,blobs)),
                'reference input changed during counterfactual')
        with out.open('x',encoding='utf8') as stream:
            json.dump(report,stream,sort_keys=True,indent=2,ensure_ascii=True)
            stream.write('\n')
        print(json.dumps({'status':report['status'],
              'original_off_occurrences':report['original']['off']['occurrences'],
              'candidate_off_occurrences':report['variant']['off']['occurrences'],
              'candidate_on_feedback_assessments':report['native_feedback_assessments']['variant_on'],
              'learned':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as exc:
        print('SPK BV v1h REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
