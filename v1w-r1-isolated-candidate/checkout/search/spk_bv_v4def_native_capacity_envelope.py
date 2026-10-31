#!/usr/bin/env python3
"""BV v4d-v4f frozen source/native resource occupancy vs ACK opportunity.

python -m search.spk_bv_v4def_native_capacity_envelope \
  --v3tuv /tmp/spk-bv-v3tuv-grant-rank.json \
  --v4abc /tmp/spk-bv-v4abc-native-contract-candidate.json \
  --out /tmp/spk-bv-v4def-native-capacity-envelope.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from search.spk_bv_v4abc_native_actor_contract_candidate import CODE_SHA as INHERITED_SHA
from spk_bv_research.native_actor_capacity_envelope_v4def import (
    EnvelopeRejected, evaluate,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

CODE_SHA = {
    **INHERITED_SHA,
    'search/spk_bv_v4abc_native_actor_contract_candidate.py':
        '7d5a48ca8a2705b938dc97f5d31681a188b8634afa71b7a6361a89cf71642b15',
    'spk_bv_research/native_actor_capacity_envelope_v4def.py':
        '8d3cf89aada738f8da3788bcf6d9594f86f66bb64380510175e4640d769679fd',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--v3tuv', type=Path, required=True)
    parser.add_argument('--v4abc', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pins = []
        for relative, digest in CODE_SHA.items():
            path = root/relative
            if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
                raise EnvelopeRejected('v4d-v4f missing/unsafe pinned native source: '+relative)
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != digest:
                raise EnvelopeRejected('v4d-v4f source SHA drift: '+relative)
            pins.append((path, raw))
        originals = [args.v3tuv, args.v4abc]
        sources = []
        for source in originals:
            path = source.resolve(strict=True)
            if source.is_symlink() or not path.is_file():
                raise EnvelopeRejected('v4d-v4f unsafe signed source path')
            sources.append((path, path.read_bytes()))
        guard_roots = tuple(path for path, _ in sources)
        out = safe_output(args.out, root, guard_roots)
        (v3_path, v3_raw), (v4_path, v4_raw) = sources
        result = evaluate(json.loads(v3_raw), v3_raw,
                          json.loads(v4_raw), v4_raw)
        if any(path.read_bytes() != old for path, old in pins+sources):
            raise EnvelopeRejected('v4d-v4f signed input/source changed during audit')
        with out.open('xb') as stream:
            stream.write(canon(result))
        t = result['source_native_observed_capacity']
        print(json.dumps({
            'status': result['status'],
            'original_native_replays': t['original_native_replays'],
            'source_derived_contexts': t['derived_source_contexts'],
            'pending_no_grant_ticks': t['pending_no_grant_ticks'],
            'global_PE_full_pending_ticks': t['pending_no_grant_global_PE_full'],
            'four_tick_windows_no_native_slot': t[
                'zero_grant_windows_with_no_native_resource_slot']['4'],
            'native_scheduler_changed': result['native_v0e_modified'],
            'output': str(out),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AssertionError, SyntaxError, EnvelopeRejected) as exc:
        print('SPK BV v4d-v4f CAPACITY ENVELOPE REJECTED: '+str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
