#!/usr/bin/env python3
"""Read signed BV v3t-v3v and issue an UNADMITTED native service draft.

python -m search.spk_bv_v4abc_native_actor_contract_candidate \
  --v3tuv /tmp/spk-bv-v3tuv-grant-rank.json \
  --out /tmp/spk-bv-v4abc-native-contract-candidate.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v3tuv_grant_rank_cumulative import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_actor_service_contract_candidate_v4abc import (
    PREDECESSOR_SHA, CandidateRejected, analyze_predecessor,
)

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v3tuv_grant_rank_cumulative.py':
        'cb1c077c4b3fe6100ca8993bf1313c83e1968a391db2650f3c602a2c14a95614',
    'spk_bv_research/native_actor_service_contract_candidate_v4abc.py':
        '013cf9de199c9364339d9b3da808f1fd0b8d6719368f4d4f63137b93bdd5f7c2',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3tuv', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for relative, digest in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise CandidateRejected('v4 source unsafe/missing: '+relative)
            before = path.read_bytes()
            if sha256(before).hexdigest() != digest:
                raise CandidateRejected('v4 inherited/new source SHA drift: '+relative)
            pinned.append((path, before))
        predecessor = args.v3tuv.resolve(strict=True)
        if args.v3tuv.is_symlink() or not predecessor.is_file():
            raise CandidateRejected('v4 signed source report path unsafe')
        raw = predecessor.read_bytes()
        if sha256(raw).hexdigest() != PREDECESSOR_SHA:
            raise CandidateRejected('v4 signed source report SHA mismatch')
        output = safe_output(args.out, root, (predecessor,))
        report = analyze_predecessor(json.loads(raw), raw)
        if predecessor.read_bytes() != raw or any(
                path.read_bytes() != before for path, before in pinned):
            raise CandidateRejected('v4 signed source/predecessor changed in review')
        with output.open('xb') as stream:
            stream.write(canon(report))
        counts = report['source_exposure']
        print(json.dumps({
            'status': report['status'],
            'source_derived_contexts': counts['contexts'],
            'observed_global_ACK_grants': counts['real_global_ACK_grants'],
            'four_tick_no_grant_contexts': counts[
                'contexts_with_zero_grant_window']['4'],
            'eight_tick_no_grant_contexts': counts[
                'contexts_with_zero_grant_window']['8'],
            'native_contract_implemented': report[
                'native_actor_service_policy_implemented'],
            'output': str(output),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, CandidateRejected) as exc:
        print('SPK BV v4a-v4c CANDIDATE REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
