#!/usr/bin/env python3
"""BV v1y: frozen native OFF/ON EXTERNAL interpreter probe, not BV receiver."""
from __future__ import annotations
import argparse, contextlib, io, json, sys, tempfile
from pathlib import Path
from hashlib import sha256

from spk_bv_research.off_on_v0t import require, snapshot
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_external_probe_v1y import analyze, observed_pair
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from search.spk_bv_v1b_native_operator_replay import safe_input, safe_output
from search.spk_bv_v1x_reference_observation_port import main as xmain, NAMES as XNAMES

NAMES=('v1x',)+XNAMES


def verify_source_digest_map(source_bytes, report_digests):
    """Read-pinned source API returns BYTES, while v1w JSON stores HEX hashes."""
    require(type(source_bytes) is dict and type(report_digests) is dict and
            {k:sha256(v).hexdigest() for k,v in source_bytes.items()}==report_digests,
            'source bytes do not match pinned v1w SHA map')
    return True


def replay_with_probe(x,w,root):
    from search.spk_bv_v0e_live_evidence import fixture
    from spk_backvalidation_v0.live_dual_scheduler_v0e import execute_live_v0e, LiveBVPlanV0e
    from spk_architecture_v1.pe_execution_v1b import _admit, _compute_local
    from spk_bv_research.native_operator_replay_v1b import source_snapshot
    from spk_bv_research.native_causal_locus_v1p import copy_intervention, native_arm
    from spk_bv_research.native_route_lineage_v1g import _edge

    expected_path=(root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py').resolve(strict=True)
    actual=Path(execute_live_v0e.__code__.co_filename).resolve(strict=True)
    require(actual==expected_path,'scheduler entrypoint module path mismatch')
    require(execute_live_v0e.__code__.co_name=='execute_live_v0e', 'frozen entrypoint changed')
    pins=read_pinned_sources(root)
    verify_source_digest_map(pins, w['source_pinned_static_candidate_inventory']['source_file_sha256'])
    original=fixture()
    original_sha=snapshot(original)
    _,owners=_admit(original[0],original[1])
    links=[_edge(e,owners) for e in original[1].static_routes]
    programs={n.node_id:snapshot(n.instructions) for n in original[0].nodes}
    sourcepins=source_snapshot(root,_admit,_compute_local)
    p=x['native_run_reference_matrix']
    lines=sorted({item['line'] for category in ('receiver_ingress','back_validation')
                  for item in w['source_pinned_static_candidate_inventory']['bounded_callsite_examples'][category]})
    require(all(type(k) is int and k>0 for k in lines),'bad trace source line')
    pairs={}
    for arm,alias in (('original','sham'),('variant','A_cmp2')):
        native,_=copy_intervention(original,alias,programs)
        state_sha=snapshot(native)
        pairs[arm]={}
        for mode in ('off','on'):
            plan=LiveBVPlanV0e(enabled=mode=='on',priority='forward-first')
            args=(native[0],native[1],*native[2],plan)
            pair=observed_pair(execute_live_v0e,args,execute_live_v0e,lines)
            require(pair['no_probe_result_sha256']==p[arm][mode]['result_sha256'],
                    'native probe comparison differs from v1x baseline')
            require(snapshot(native)==state_sha and snapshot(original)==original_sha,
                    'fixture drift while probing native runtime')
            pairs[arm][mode]=pair
    require(read_pinned_sources(root)==pins and
            source_snapshot(root,_admit,_compute_local)==sourcepins,
            'frozen source drift during external probe')
    return pairs


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    for name in NAMES:p.add_argument('--'+name,type=Path,required=(name=='v1x'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true',help='offline report: no new native scheduler runs')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        names=('v1x',) if args.contract_only else NAMES
        require(args.contract_only or all(getattr(args,n) is not None for n in NAMES),
                'missing complete native predecessor chain')
        paths=[getattr(args,name) for name in names]
        items=[safe_input(v,root) for v in paths]
        require(len({i for _,i in items})==len(items),'source alias')
        out=safe_output(args.out,root,tuple(p.absolute() for p in paths))
        raw=dict(zip(names,(content for content,_ in items)))
        x=json.loads(raw['v1x'])
        pairs=None
        sources=None
        if not args.contract_only:
            sources=read_pinned_sources(root)
            with tempfile.TemporaryDirectory(prefix='spk-bv-v1y-replay-') as td:
                rec=Path(td)/'v1x.json'
                replay_args=['--root',str(root)]
                for name in XNAMES: replay_args.extend(('--'+name,str(getattr(args,name))))
                replay_args.extend(('--out',str(rec)))
                with contextlib.redirect_stdout(io.StringIO()):rc=xmain(replay_args)
                require(rc==0 and rec.is_file() and rec.read_bytes()==raw['v1x'],
                        'inherited v1x byte mismatch')
            require(read_pinned_sources(root)==sources,'source changed during inherited replay')
            pairs=replay_with_probe(x,json.loads(raw['v1w']),root)
        report=analyze(x,raw['v1x'],native_pairs=pairs,source_rechecked=not args.contract_only)
        if pairs is not None:
            report['inherited_native_v1x_recomputation_verified_in_this_run']=True
            require(read_pinned_sources(root)==sources,'source changed during native probe')
        require(all(paths[i].read_bytes()==raw[name] for i,name in enumerate(names)),
                'predecessor input mutated during audit')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
            'native_probe_pairs':0 if pairs is None else 4,
            'native_receiver_packets':0,'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,SyntaxError) as exc:
        print('SPK BV v1y REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
