#!/usr/bin/env python3
"""BV v4j-v4l source-pinned, non-admitted, shadow PE ACK slot arbitration."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v4ghi_native_coverage_frontier import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_ack_shadow_arbiter_v4jkl import evaluate, EnvelopeRejected
from spk_bv_research.native_allocation_boundary_v1r import canon

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v4ghi_native_coverage_frontier.py':
        '29e72502b3494bc730ba5385429c95fe36b83709ba925c79799993689a9bb3ca',
    'spk_bv_research/native_ack_shadow_arbiter_v4jkl.py':
        '64d84026fed3bbc0350a001fab66b41212987a10c4ad64ac92f543b86a1c02a1',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3tuv', type=Path, required=True)
    parser.add_argument('--v4abc', type=Path, required=True)
    parser.add_argument('--v4def', type=Path, required=True)
    parser.add_argument('--v4ghi', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        root = a.root.resolve(strict=True)
        pinned = []
        for relative, digest in CODE_SHA.items():
            path = root/relative
            if (not path.is_file() or path.is_symlink() or
                    path.resolve(strict=True) != path):
                raise EnvelopeRejected('v4j-v4l unsafe/missing source: '+relative)
            b = path.read_bytes()
            if sha256(b).hexdigest() != digest:
                raise EnvelopeRejected('v4j-v4l source SHA drift: '+relative)
            pinned.append((path, b))
        signed = []
        for src in (a.v3tuv, a.v4abc, a.v4def, a.v4ghi):
            path = src.resolve(strict=True)
            if src.is_symlink() or not path.is_file():
                raise EnvelopeRejected('v4j-v4l unsafe signed source')
            signed.append((path, path.read_bytes()))
        out = safe_output(a.out, root, tuple(p for p, _ in signed))
        decoded = [json.loads(b) for _, b in signed]
        result = evaluate(decoded[0], signed[0][1], decoded[1], signed[1][1],
                          decoded[2], signed[2][1], decoded[3], signed[3][1])
        if any(path.read_bytes() != raw for path, raw in pinned+signed):
            raise EnvelopeRejected('v4j-v4l pinned source changed during audit')
        with out.open('xb') as stream:
            stream.write(canon(result))
        w4 = result['shadow_variants'][
            'W4/deadline-only/PE_REASSIGN_CONDITIONAL_MEMORY_GUARD/protect-forward']
        print(json.dumps({
            'status': result['status'],
            'source_original_native_replays': result['source_original_native_replays'],
            'source_derived_ACK_contexts': result['source_derived_ACK_contexts'],
            'W4_shadow_complete_coverage_contexts': w4['contexts_with_complete_coverage'],
            'W4_native_PE_services_would_be_displaced':
                w4['native_service_units_would_be_displaced'],
            'displaced_services_reexecuted': False,
            'native_scheduler_changed': result['native_v0e_modified'],
            'output': str(out),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, EnvelopeRejected) as exc:
        print('SPK BV v4j-v4l SHADOW ARBITER REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
