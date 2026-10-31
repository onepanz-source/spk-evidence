#!/usr/bin/env python3
"""BV v2q: independent PE and memory charging per derived actor application.

python -m search.spk_bv_v2q_independent_consumer_resource \
  --v2p /tmp/spk-bv-v2p-actor-consumer-handoff.json \
  --out /tmp/spk-bv-v2q-independent-consumer-resource.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2p_actor_consumer_handoff import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_resource_consumer_integration_v2q import (
    PREDECESSOR_SHA,experiment,build_report,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA={
    **INHERITED_SHA,
    'search/spk_bv_v2p_actor_consumer_handoff.py':
        'a50ecf57125ce3ded74d8a944a69278204e2354a9ff7d8da15475a51d1e6bd48',
    'spk_backvalidation_v2/derived_actor_resource_consumer_v2q.py':
        '1ba82f4876a716eb4bd8d26ce7259a8e69afc0ce6dae803dbff6af56dbc1b619',
    'spk_bv_research/actor_resource_consumer_integration_v2q.py':
        'e15941d42672b27bc74ece82173d16a9f147841f3e050c8c2064ef4d29e790e7',
}


def read_signed_v2p_report(path:Path,root:Path):
    path=path.absolute()
    if (path.is_symlink() or any(p.is_symlink() for p in path.parents)
            or not path.is_file()):
        raise ValueError('v2q unsafe or missing canonical v2p predecessor')
    resolved=path.resolve(strict=True)
    if (resolved==root or root in resolved.parents or
            not 0<resolved.stat().st_size<=8_000_000):
        raise ValueError('v2q repository-owned or oversized signed v2p report')
    return path.read_bytes()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2p',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnesses=[]
        for relative,expected in CODE_SHA.items():
            path=root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('v2q unsafe or missing inherited source: '+relative)
            before=path.read_bytes()
            if sha256(before).hexdigest()!=expected:
                raise ValueError('v2q inherited or independent resource code SHA drift: '+relative)
            witnesses.append((path,before))
        raw=read_signed_v2p_report(args.v2p,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2q signed v2p predecessor SHA changed')
        output=safe_output(args.out,root,(args.v2p.absolute(),))
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
        if args.v2p.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnesses):
            raise ValueError('v2q signed v2p report or source changed during replay')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'native_runs':report['new_native_runs'],
            'resource_charged_runs':report['new_resource_charged_normal_runs'],
            'resource_intervention_runs':
                report['new_resource_backpressure_intervention_runs'],
            'negative_fixture_runs':report['new_negative_fixture_runs'],
            'independently_charged_consumer_totals':
                report['independently_charged_consumer_totals'],
            'resource_backpressure_intervention_totals':
                report['resource_backpressure_intervention_totals'],
            'real_negative_fixture':report['real_negative_B_resource_fixture'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError,LiveBVRejected) as exc:
        print('SPK BV v2q REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
