#!/usr/bin/env python3
"""BV v4g-v4i exact finite source-native ACK coverage frontier (no adoption)."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v4def_native_capacity_envelope import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_actor_coverage_frontier_v4ghi import evaluate, EnvelopeRejected
from spk_bv_research.native_allocation_boundary_v1r import canon

# New module pin populated after code freeze, including original native pins.
CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v4def_native_capacity_envelope.py':
        '94225ab59ef4b5e39a8db8a9e1b5fb9f42b58f14257f989e8e615c2a659e91f4',
    'spk_bv_research/native_actor_coverage_frontier_v4ghi.py':
        '262afa18daa46239c526b05a84fbe9745ccdd85f3bdbc55e65df39be34b288a1',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3tuv', type=Path, required=True)
    parser.add_argument('--v4abc', type=Path, required=True)
    parser.add_argument('--v4def', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pins = []
        for relative, digest in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise EnvelopeRejected('v4g-v4i missing/unsafe pinned source: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise EnvelopeRejected('v4g-v4i source SHA drift: '+relative)
            pins.append((path, raw))
        signed = []
        for path_arg in (args.v3tuv, args.v4abc, args.v4def):
            path = path_arg.resolve(strict=True)
            if path_arg.is_symlink() or not path.is_file():
                raise EnvelopeRejected('v4g-v4i unsafe signed source path')
            signed.append((path, path.read_bytes()))
        out = safe_output(args.out, root, tuple(p for p, _ in signed))
        (p3, raw3), (p4, raw4), (pd, rawd) = signed
        report = evaluate(json.loads(raw3), raw3, json.loads(raw4), raw4,
                          json.loads(rawd), rawd)
        if any(path.read_bytes() != raw for path, raw in pins+signed):
            raise EnvelopeRejected('v4g-v4i signed source changed mid-audit')
        with out.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({'status': report['status'],
                          'native_original_replays': report['source_original_native_replays'],
                          'derived_contexts': report['source_derived_contexts'],
                          'windows_4': report['window_frontiers']['4']['complete_zero_grant_windows'],
                          'strict_4_infeasible_contexts': report['window_frontiers']['4'][
                              'strict_spare_only_infeasible_contexts'],
                          'native_scheduler_changed': report['native_v0e_modified'],
                          'output': str(out)}, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, EnvelopeRejected) as exc:
        print('SPK BV v4g-v4i COVERAGE FRONTIER REJECTED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
