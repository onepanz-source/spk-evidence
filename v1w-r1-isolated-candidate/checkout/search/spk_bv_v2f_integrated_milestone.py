#!/usr/bin/env python3
"""Full batch-aware micro forwarding and research receiver feedback milestone.

Runs no frozen scheduler. Verifies previously attested native v2e (45-run)
report, executes versioned micro-runtime, and optionally rechecks frozen files.
The resulting research feedback is NOT delivered to frozen native SPK B.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from hashlib import sha256
from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.observation_seam_contract_v1w import read_pinned_sources
from spk_bv_research.vertical_slice_integration_v2f import run_integrated

EXPECTED_V2E_BYTES_SHA256='219cce4eadd862bc09d0f4d8f385057fa8e3db3084a59c5f1b2274a485aaa916'
EXPECTED_MICRO_SHA256='d94608c954b0af42caeaeb4df65fa1e4e59ef6d672978c2b42916e85000f1a5d'
EXPECTED_AUDIT_SHA256='3290a55d0368d5a8db9faf09c7abbe46ff637e461d5331eb3411a48d5b9734a1'

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--v2e',type=Path,required=True)
    p.add_argument('--v2d',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--contract-only',action='store_true',help='omit source custody when frozen files are unavailable')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        relpaths=('spk_backvalidation_v2/batched_feedback_executor_v2f.py',
                  'spk_bv_research/vertical_slice_integration_v2f.py')
        src=[]
        for rel,expected in zip(relpaths,(EXPECTED_MICRO_SHA256,EXPECTED_AUDIT_SHA256)):
            file=root/rel
            if not file.is_file() or file.is_symlink() or file.resolve(strict=True)!=file:
                raise ValueError('research source path unsafe or absent')
            contents=file.read_bytes()
            if sha256(contents).hexdigest()!=expected:
                raise ValueError('research module source changed: '+rel)
            src.append(contents)
        args_paths=(args.v2e,args.v2d)
        sources=[safe_input(p,root) for p in args_paths]
        if sources[0][1]==sources[1][1]:
            raise ValueError('predecessor file alias')
        out=safe_output(args.out,root,tuple(p.absolute() for p in args_paths))
        v2eb,v2db=(v for v,_ in sources)
        if sha256(v2eb).hexdigest()!=EXPECTED_V2E_BYTES_SHA256:
            raise ValueError('native v2e report differs from supplied attestation')
        evidence=json.loads(v2eb)
        frozen_before=None
        if not args.contract_only:
            frozen_before=read_pinned_sources(root)
        report=run_integrated(evidence,v2eb,v2d_data=v2db,
                              custody=frozen_before is not None)
        if frozen_before is not None and frozen_before!=read_pinned_sources(root):
            raise ValueError('frozen source changed during research micro execution')
        if any((root/rel).read_bytes()!=raw for rel,raw in zip(relpaths,src)):
            raise ValueError('research source changed during audit')
        if any(p.read_bytes()!=raw for p,raw in zip(args_paths,(v2eb,v2db))):
            raise ValueError('input changed during audit')
        with out.open('xb') as f:f.write(canon(report))
        print(json.dumps({'status':report['status'],
                          'finite_native_projection_cells':report['native_projection_cells_checked'],
                          'new_research_micro_executions':report['source_owned_research_micro_executions'],
                          'research_control_delivered':report['research_control_messages_delivered_in_new_executor'],
                          'native_receiver_control_messages':0,'native_learning_proven':False,
                          'out':str(out)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError) as ex:
        print('SPK BV v2f REJECTED: '+str(ex),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
