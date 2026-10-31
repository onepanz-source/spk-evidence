"""Create-only signed-source v4p-v4r endogenous actor ACK research report."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_ack_actor_audit_v4pqr import evaluate

CODE_SHA = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':
        '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'spk_bv_research/native_ack_causal_replay_v4mno.py':
        'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261',
    'spk_bv_research/native_ack_actor_loop_v4pqr.py':
        'e489ceca0730d2404face2c79c2da36ffbfdeb82e63dd04dd9a07210a3586f85',
    'spk_bv_research/native_ack_actor_audit_v4pqr.py':
        '40b338e00470fee8dd0a1b2ab34042497c1d7b50e408f4ac50e7017944a4c37b',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v3tuv', required=True, type=Path)
    parser.add_argument('--v4mno', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pinned = []
        for name, expected in CODE_SHA.items():
            source = root / name
            if (not source.is_file() or source.is_symlink() or
                    source.resolve(strict=True) != source):
                raise ValueError('v4p unsafe or missing pinned module: ' + name)
            raw = source.read_bytes()
            if sha256(raw).hexdigest() != expected:
                raise ValueError('v4p source SHA drift: ' + name)
            pinned.append((source, raw))
        signed = []
        for source in (args.v3tuv, args.v4mno):
            path = source.resolve(strict=True)
            if source.is_symlink() or not path.is_file():
                raise ValueError('v4p unsafe signed predecessor')
            signed.append((path, path.read_bytes()))
        destination = safe_output(args.out, root, tuple(p for p, _ in signed))
        raw3, raw4 = signed[0][1], signed[1][1]
        report = evaluate(json.loads(raw3), raw3, json.loads(raw4), raw4)
        if any(p.read_bytes() != raw for p, raw in pinned + signed):
            raise ValueError('v4p pinned modules or predecessors changed during run')
        with destination.open('xb') as output:
            output.write(canon(report))
        print(json.dumps({
            'status': report['status'], 'output': str(destination),
            'source_native_replays': report['totals']['original_native_replays'],
            'derived_actor_reexecutions': report['totals']['derived_scenarios'],
            'originated_and_delivered_controls': report['totals']['originated_judgments'],
            'derived_actor_credits_applied': report['totals']['derived_actor_credit_applied'],
            'native_learning_implemented': False,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('SPK BV v4p-v4r ACTOR GATE REJECTED: ' + str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
