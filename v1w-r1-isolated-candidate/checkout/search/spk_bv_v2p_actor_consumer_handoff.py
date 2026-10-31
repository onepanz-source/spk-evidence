#!/usr/bin/env python3
"""BV v2p source-pinned actor consumer handoff research gate.

python -m search.spk_bv_v2p_actor_consumer_handoff \
  --v2o /tmp/spk-bv-v2o-native-causal-admission.json \
  --out /tmp/spk-bv-v2p-actor-consumer-handoff.json
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v2o_native_causal_admission import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.actor_consumer_handoff_integration_v2p import (
    PREDECESSOR_SHA,experiment,build_report,
)
from spk_backvalidation_v2.derived_native_fork_v2g import NativeForkError
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVRejected

CODE_SHA={
    **INHERITED_SHA,
    'search/spk_bv_v2o_native_causal_admission.py':
        '6eb4afd86f3b6c36ee37854e27aab88e7a6b345672acc82e0730b9b9d1d5a1eb',
    'spk_backvalidation_v2/derived_actor_consumer_v2p.py':
        'caaf0fab9e6363ec38a1cafe336b13505a55af313561cd83978d0130212a3a05',
    'spk_bv_research/actor_consumer_handoff_integration_v2p.py':
        'f8a5b19097fe25f8a31d88f3837213cffa1891cf1516f9e6424179949096e6f3',
}


def read_signed_v2o_report(path:Path,root:Path):
    path=path.absolute()
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
            or not path.is_file()):
        raise ValueError('v2p unsafe or missing signed v2o predecessor')
    resolved=path.resolve(strict=True)
    if (resolved==root or root in resolved.parents or
            not 0<resolved.stat().st_size<=8_000_000):
        raise ValueError('v2p repository-owned or oversized signed v2o report')
    return path.read_bytes()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--v2o',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--contract-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        witnessed=[]
        for relative,expected in CODE_SHA.items():
            path=root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path:
                raise ValueError('v2p missing or unsafe source: '+relative)
            before=path.read_bytes()
            if sha256(before).hexdigest()!=expected:
                raise ValueError('v2p inherited or actor consumer code SHA drift: '+relative)
            witnessed.append((path,before))
        raw=read_signed_v2o_report(args.v2o,root)
        if sha256(raw).hexdigest()!=PREDECESSOR_SHA:
            raise ValueError('v2p signed v2o predecessor digest drift')
        output=safe_output(args.out,root,(args.v2o.absolute(),))
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
        if args.v2o.read_bytes()!=raw or any(
                path.read_bytes()!=before for path,before in witnessed):
            raise ValueError('v2p pinned predecessor or inherited source mutated')
        with output.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status':report['status'],
            'native_runs':report['new_native_runs'],
            'derived_normal_runs':report['new_normal_consumer_runs'],
            'derived_intervention_runs':report['new_bounded_consumer_intervention_runs'],
            'negative_fixture_runs':report['new_negative_fixture_native_derived_runs'],
            'consumer_handoff_totals':report['consumer_handoff_totals'],
            'bounded_consumer_intervention_totals':
                report['bounded_consumer_intervention_totals'],
            'real_negative_fixture':report['real_negative_B_actor_consumer_fixture'],
            'output':str(output),
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,AssertionError,
            SyntaxError,NativeForkError,LiveBVRejected) as exc:
        print('SPK BV v2p REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
