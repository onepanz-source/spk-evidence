#!/usr/bin/env python3
"""BV v1x reference-owned event port + frozen native no-observer repeatability."""
from __future__ import annotations
import argparse, contextlib, io, json, sys, tempfile
from pathlib import Path
from hashlib import sha256

from spk_bv_research.off_on_v0t import require, snapshot
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.reference_observation_port_v1x import analyze
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from search.spk_bv_v1w_observation_seam import main as wmain, NAMES as WNAMES

NAMES=('v1w',)+WNAMES


def native_no_observer_baseline(v1p,root):
    """Actual frozen native runs, always WITHOUT an observer or injection."""
    from search.spk_bv_v0e_live_evidence import fixture
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e,LiveBVPlanV0e
    from spk_architecture_v1.pe_execution_v1b import _admit,_compute_local
    from spk_bv_research.native_operator_replay_v1b import source_snapshot
    from spk_bv_research.native_causal_locus_v1p import copy_intervention,native_arm
    from spk_bv_research.native_route_lineage_v1g import _edge
    original=fixture()
    original_sha=snapshot(original)
    _,owners=_admit(original[0],original[1])
    links=[_edge(e,owners) for e in original[1].static_routes]
    programs={n.node_id:snapshot(n.instructions) for n in original[0].nodes}
    pins=source_snapshot(root,_admit,_compute_local)
    require(type(v1p) is dict and v1p.get('frozen_native_sources')==pins and
            v1p.get('native_fixture_sha256')==original_sha and
            v1p.get('native_matrix_repeatability_attested_in_this_run') is True,
            'v1p native fixtures/sources not attested')
    matrix={}
    for arm,alias in (('original','sham'),('variant','A_cmp2')):
        native,_=copy_intervention(original,alias,programs)
        clone_sha=snapshot(native)
        matrix[arm]={}
        for mode in ('off','on'):
            policy=LiveBVPlanV0e(enabled=(mode=='on'),priority='forward-first')
            r1=execute_live_v0e(native[0],native[1],*native[2],policy)
            r2=execute_live_v0e(native[0],native[1],*native[2],policy)
            require(canon(r1)==canon(r2) and snapshot(native)==clone_sha and
                    snapshot(original)==original_sha,'native frozen run not repeatable')
            got=native_arm(r1,links)
            require(got==v1p['intervention_runs'][alias][mode],
                    'native baseline differs from attested v1p '+arm+'/'+mode)
            matrix[arm][mode]={'sender':got['emissions_by_neuron']['A'],
                               'ingress':got['edges']['A->B:7->0'],
                               'result_sha256':got['native_result_sha256'],
                               'repeatability_identical':True}
    require(snapshot(original)==original_sha and
            pins==source_snapshot(root,_admit,_compute_local),
            'source or fixture drift during comparison')
    return matrix


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for n in NAMES:
        p.add_argument('--'+n,type=Path,required=(n=='v1w'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reference-only',action='store_true',
        help='offline REFERENCE laboratory only; no native scheduler or replay')
    a=p.parse_args(argv)
    try:
        root=a.root.resolve(strict=True)
        names=('v1w',) if a.reference_only else NAMES
        require(a.reference_only or all(getattr(a,n) is not None for n in NAMES),
                'full native baseline needs complete predecessor chain')
        paths=[getattr(a,n) for n in names]
        entries=[safe_input(path,root) for path in paths]
        require(len({identity for _,identity in entries})==len(entries),
                'aliased inputs')
        out=safe_output(a.out,root,tuple(p.absolute() for p in paths))
        raw={n:entries[i][0] for i,n in enumerate(names)}
        w=json.loads(raw['v1w'])
        refs=None
        before_sources=None
        if not a.reference_only:
            before_sources=read_pinned_sources(root)
            with tempfile.TemporaryDirectory(prefix='spk-bv-v1x-v1w-') as td:
                reproduced=Path(td)/'v1w.json'
                pargs=['--root',str(root)]
                for name in WNAMES:pargs.extend(('--'+name,str(getattr(a,name))))
                pargs.extend(('--out',str(reproduced)))
                with contextlib.redirect_stdout(io.StringIO()):rc=wmain(pargs)
                require(rc==0 and reproduced.is_file() and
                        reproduced.read_bytes()==raw['v1w'],
                        'v1w inherited native recomputation byte mismatch')
            require(before_sources==read_pinned_sources(root),
                    'frozen source changed during inherited replay')
            refs=native_no_observer_baseline(json.loads(raw['v1p']),root)
        report=analyze(w,raw['v1w'],native_reference=refs,
                       source_rechecked=not a.reference_only)
        if not a.reference_only:
            report['inherited_native_v1w_recomputation_verified_in_this_run']=True
            require(before_sources==read_pinned_sources(root),
                    'frozen source changed during baseline runs')
        require(all(path.read_bytes()==raw[name] for name,path in zip(names,paths)),
                'predecessor file changed during audit')
        with out.open('xb') as stream:stream.write(canon(report))
        print(json.dumps({'status':report['status'],'reference_cases':len(report['reference_lab_sessions']),
                          'native_no_observer_runs':report['native_scheduler_executions_in_this_module'],
                          'native_listener_invoked':False,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,SyntaxError) as exc:
        print('SPK BV v1x REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
