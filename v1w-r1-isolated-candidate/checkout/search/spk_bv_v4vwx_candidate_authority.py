"""Create-only source-pinned v4v-v4x research candidate authority report."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_actor_candidate_audit_v4vwx import evaluate

CODE_SHA = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':
        '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'spk_bv_research/native_ack_causal_replay_v4mno.py':
        'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261',
    'spk_bv_research/native_ack_actor_loop_v4pqr.py':
        'e489ceca0730d2404face2c79c2da36ffbfdeb82e63dd04dd9a07210a3586f85',
    'spk_bv_research/native_ack_paid_consumer_v4stu.py':
        '4ee3c1704aee638b6271277c18735e345783e9e4eeca5c65958613abb37fa046',
    'spk_bv_research/native_ack_paid_consumer_audit_v4stu.py':
        '7cdcd65f1cc4ea5373d19a1e1c0e43057b94ac850429147941a2105118d55eda',
    'spk_bv_research/native_actor_candidate_boundary_v4vwx.py':
        'c8a6aa32f615a73a0779a5ee095d2b04652544394e14be0889a08f6a1b3173b0',
    'spk_bv_research/native_actor_candidate_audit_v4vwx.py':
        'd0d602076e8d17058cb1705189bb1ebf2cfbf78d333813b47f6372b5e7aa7188',
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--v3tuv',required=True,type=Path)
    parser.add_argument('--v4stu',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        pinned=[]
        for name,expected in CODE_SHA.items():
            source=root/name
            if (not source.is_file() or source.is_symlink() or
                    source.resolve(strict=True)!=source):
                raise ValueError('v4vwx unsafe pinned module: '+name)
            raw=source.read_bytes()
            if sha256(raw).hexdigest()!=expected:
                raise ValueError('v4vwx pinned source SHA drift: '+name)
            pinned.append((source,raw))
        signed=[]
        for source in (args.v3tuv,args.v4stu):
            path=source.resolve(strict=True)
            if source.is_symlink() or not path.is_file():
                raise ValueError('v4vwx unsafe signed predecessor')
            signed.append((path,path.read_bytes()))
        destination=safe_output(args.out,root,tuple(p for p,_ in signed))
        report=evaluate(json.loads(signed[0][1]),signed[0][1],
                        json.loads(signed[1][1]),signed[1][1])
        if any(path.read_bytes()!=raw for path,raw in pinned+signed):
            raise ValueError('v4vwx source changed during execution')
        with destination.open('xb') as out:
            out.write(canon(report))
        print(json.dumps({
            'status':report['status'],'output':str(destination),
            'native_source_replays':report['totals']['native_source_replays'],
            'paid_source_actor_reexecutions':report['totals']['paid_source_actor_reexecutions'],
            'candidate_shadow_episodes':report['totals']['candidate_shadow_episodes'],
            'vetoed_candidates':report['totals']['candidate_shadow_episodes'],
            'learning_adoptions':report['applied_native_learning_updates'],
        },sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print('SPK BV v4v-v4x CANDIDATE AUTHORITY REJECTED: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
