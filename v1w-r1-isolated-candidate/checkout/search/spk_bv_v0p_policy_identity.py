"""CLI for BV v0p identity-aware policy comparison, native data only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from spk_bv_research.paired_runs_v0o import load_capture, pins, PairError
from spk_bv_research.policy_identity_v0p import compute, EXPECTED_NATIVE_SHA


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--capture-13',type=Path,required=True)
    p.add_argument('--capture-811',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        repo=a.repo.resolve(strict=True)
        if (a.out.exists() or a.out.is_symlink() or
            a.out.absolute().is_relative_to(repo) or
            not a.out.absolute().is_relative_to(Path('/tmp'))):
            raise PairError('output must be new, outside worktree, under /tmp')
        first=load_capture(a.capture_13)
        second=load_capture(a.capture_811)
        if (first['native_fixture_sha256']!=EXPECTED_NATIVE_SHA or
            first['native_fixture']!=second['native_fixture'] or
            first['producer_pins']!=second['producer_pins'] or
            second['native_fixture_sha256']!=EXPECTED_NATIVE_SHA):
            raise PairError('independent fixtures differ or unexpected pinned native SHA')
        if pins(repo)!=first['producer_pins']:
            raise PairError('source pins differ from current repository')
        result=compute(first['native_fixture'],first['native_fixture_sha256'])
        result['source_pins_reverified']=True
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x',encoding='utf-8') as f:
            json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
            f.write('\n')
        print(json.dumps({'status':result['status'],'conserved_outcomes_all':result['conserved_outcomes_all'],
            'matched_feedback_deliveries':result['identity_joins']['feedback_delivery']['matched_immutable_payload_count'],
            'matched_forward_occurrences':result['identity_joins']['forward_occurrence']['matched_immutable_payload_count'],
            'output':str(a.out)},sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('BV v0p REJECTED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
