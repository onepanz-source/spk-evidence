"""Create-only signed-source v4m-v4o native ACK causal probe (research only)."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_causal_audit_v4mno import evaluate


CODE_SHA = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':
        '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'spk_bv_research/native_ack_shadow_arbiter_v4jkl.py':
        '64d84026fed3bbc0350a001fab66b41212987a10c4ad64ac92f543b86a1c02a1',
    'spk_bv_research/native_ack_causal_replay_v4mno.py':
        'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261',
    'spk_bv_research/native_ack_causal_audit_v4mno.py':
        '94918f92027334527cb52ed100c1a1a831eea4ad34403553bf90cf650cd9b366',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v3tuv', required=True, type=Path)
    parser.add_argument('--v4jkl', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for path, expected in CODE_SHA.items():
            candidate = root / path
            if (not candidate.is_file() or candidate.is_symlink() or
                    candidate.resolve(strict=True) != candidate):
                raise ValueError('v4m-v4o missing or unsafe source: ' + path)
            raw = candidate.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v4m-v4o source SHA drift: ' + path)
            pinned.append((candidate, raw))
        signed = []
        for source in (args.v3tuv, args.v4jkl):
            path = source.resolve(strict=True)
            if source.is_symlink() or not path.is_file():
                raise ValueError('v4m-v4o unsafe signed source')
            signed.append((path, path.read_bytes()))
        destination = safe_output(args.out, root, tuple(p for p, _ in signed))
        raw3, raw4 = signed[0][1], signed[1][1]
        report = evaluate(json.loads(raw3), raw3, json.loads(raw4), raw4)
        if any(path.read_bytes() != raw for path, raw in pinned + signed):
            raise ValueError('v4m-v4o signed predecessor or source changed during replay')
        # An existing report is an explicit stop condition, never overwritten.
        with destination.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status': report['status'], 'output': str(destination),
            'native_source_replays': report['totals']['original_native_replays'],
            'derived_reexecuted_scenarios': report['totals']['derived_scenarios'],
            'exogenous_ACK_transport_deliveries': report['totals']['simulated_ack_deliveries'],
            'real_actor_credit_applied': False,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('SPK BV v4m-v4o CAUSAL PROBE REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
