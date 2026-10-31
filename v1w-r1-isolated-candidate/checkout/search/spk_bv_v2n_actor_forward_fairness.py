#!/usr/bin/env python3
"""BV v2n signed predecessor + derived fairness/native differential matrix.

Usage: python -m search.spk_bv_v2n_actor_forward_fairness \
  --v2m /tmp/spk-bv-v2m-actor-priority-contention.json \
  --out /tmp/spk-bv-v2n-actor-forward-fairness.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_input,safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_forward_fairness_integration_v2n import (
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
    'spk_backvalidation_v2/derived_actor_credit_protocol_v2l.py':
        '12d9aaa5692f0e2f7027a7f9c8b9d0a8773cb130ae30c66af52ed54c9cebbb76',
    'spk_bv_research/actor_credit_protocol_integration_v2l.py':
        '434c2299a47c5f14b35732af2a4893fdccc2858f9abdefcf9ac1dee22fb71c73',
    'spk_backvalidation_v2/derived_actor_priority_v2m.py':
        '5391c8bdc4cb02a1d30fbc7079e111fd55798af46f39522c04d7846c5ef1581f',
    'spk_bv_research/actor_priority_contention_integration_v2m.py':
        'ce3e42304a47762e961cae31e99ede8edb52475f74a3235c82e6b2b01f87b74a',
    'spk_backvalidation_v2/derived_actor_fairness_v2n.py':
        '19b66ee1f1f5b59c68f42ed3666f8a2dc30b1d7df72b52de1b139954f2aa1dc4',
    'spk_bv_research/actor_forward_fairness_integration_v2n.py':
        'da9887fd08ea23b468741336b4e698bce6dee46704fa189bbcbb80289e8a7213',
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2m',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnessed=[]
        for relative,expected in CODE_SHA.items():
            path=root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('missing or unsafe source pin v2n: '+relative)
            before=path.read_bytes()
            if sha256(before).hexdigest()!=expected:
                raise ValueError('v2n inherited source SHA drift: '+relative)
            witnessed.append((path,before))
        raw,_=safe_input(args.v2m,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2n canonical v2m predecessor SHA mismatch')
        output=safe_output(args.out,root,(args.v2m.absolute(),))
        previous=json.loads(raw)
        result=None
        if not args.contract_only:
            from search.spk_bv_v0e_live_evidence import fixture
            from spk_backvalidation_v0.live_dual_scheduler_v0e import (
                execute_live_v0e,LiveBVPlanV0e,
            )
            result=experiment(previous,raw,root=root,fixture_fn=fixture,
                native_executor=execute_live_v0e,plan_type=LiveBVPlanV0e)
        report=build_report(previous,raw,result)
        if args.v2m.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnessed):
            raise ValueError('v2n inherited source/predecessor changed during matrix')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'new_original_native_runs':report['new_original_native_runs'],
            'derived_fairness_window_runs':report['new_derived_fairness_window_runs'],
            'derived_causal_null_runs':report['new_derived_causal_null_runs'],
            'legacy_v2m_actor_first_reference_cells':report[
                'legacy_v2m_actor_first_reference_cells'],
            'fairness_window_totals':report['fairness_window_totals'],
            'causal_null_full_native_parity':report['causal_null_full_native_parity'],
            'bounded_horizon_witness':report['bounded_horizon_witness'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError) as exc:
        print('SPK BV v2n REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
