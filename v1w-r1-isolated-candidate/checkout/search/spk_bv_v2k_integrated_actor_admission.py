#!/usr/bin/env python3
"""BV v2k: pinned derived actor resource commits and exact native projection.

Usage: python -m search.spk_bv_v2k_integrated_actor_admission \
  --v2j /tmp/spk-bv-v2j-shadow-actor-control-service.json \
  --out /tmp/spk-bv-v2k-integrated-actor-resource-admission.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_resource_admission_integration_v2k import (
    PREDECESSOR_SHA,build_report,experiment,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError

CODE_SHA={
    'spk_backvalidation_v2/derived_receiver_port_v2h.py':
        '04f03c9977afc770d7c82c5a11f5474a40319cc0bcee06594171cc4db1f0a7a8',
    'spk_bv_research/receiver_port_integration_v2h.py':
        '1f4690ca76c591fe1e20819805cd5c11bebad56bd0affa3a50095af05c8ba030',
    'spk_backvalidation_v2/derived_actor_intake_v2i.py':
        '578ac2344d6dcd8452192e3f2bdb1b6257d2414c5cbdd02ab36524c216aaa8c0',
    'spk_bv_research/actor_intake_integration_v2i.py':
        '1fdc38a1e30e8af2681e9ca3ab9f87fc4488ba3730f36d9ed6eab82ee95f5f8f',
    'spk_backvalidation_v2/derived_actor_control_service_v2j.py':
        'ff32bbf02e041e1b194d415ae7052936110dc12e95bb9871937b9d1b48f6089c',
    'spk_bv_research/actor_control_service_integration_v2j.py':
        '9122de4dbef12e7dede2500fce962ebbc3e38522b96ba88a276aec396f293113',
    'spk_backvalidation_v2/derived_actor_admission_v2k.py':
        'fbcce0d368a7200d06d96fc4517e71fc30743bd9965721cb7f3e83abb8134d93',
    'spk_bv_research/actor_resource_admission_integration_v2k.py':
        '69a1252d669df6fc12be4ddd8a22d4eb7e80a90429580e3ef3d1c0eab3592438',
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2j',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnessed=[]
        for rel,expected in CODE_SHA.items():
            path=root/rel
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('unsafe or missing v2k code: '+rel)
            raw=path.read_bytes()
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('v2k inherited or current code SHA mismatch: '+rel)
            witnessed.append((path,raw))
        raw,_=safe_input(args.v2j,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2j signed-off report SHA mismatch')
        output=safe_output(args.out,root,(args.v2j.absolute(),))
        previous=json.loads(raw)
        result=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e,LiveBVPlanV0e,
            )
            result=experiment(previous,raw,root=root,fixture_fn=fixture,
                              native_executor=execute_live_v0e,
                              plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        if args.v2j.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnessed):
            raise ValueError('v2k source/evidence changed during native replay')
        with output.open('xb') as file:
            file.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'native_original_runs':report['new_native_original_runs'],
            'derived_normal_runs':report['new_derived_integrated_normal_runs'],
            'derived_intervention_runs':report['new_derived_integrated_intervention_runs'],
            'full_native_projection_parity_cells':report['full_native_projection_parity_cells'],
            'derived_resource_timeline_changed_cells':report['derived_resource_timeline_changed_cells'],
            'integrated_admission_totals':report['integrated_admission_totals'],
            'negative_native_fixture':report['negative_native_fixture'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError) as exc:
        print('SPK BV v2k REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
