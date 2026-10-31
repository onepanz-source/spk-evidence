"""Create-only, source-SHA-pinned two-view task adjudication research report."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_disagreement_audit_v4aeag import evaluate

CODE_SHA = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':
        '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'spk_bv_research/native_ack_causal_replay_v4mno.py':
        'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261',
    'spk_bv_research/native_ack_actor_loop_v4pqr.py':
        'e489ceca0730d2404face2c79c2da36ffbfdeb82e63dd04dd9a07210a3586f85',
    'spk_bv_research/native_ack_paid_consumer_v4stu.py':
        '4ee3c1704aee638b6271277c18735e345783e9e4eeca5c65958613abb37fa046',
    'spk_bv_research/native_actor_candidate_boundary_v4vwx.py':
        'c8a6aa32f615a73a0779a5ee095d2b04652544394e14be0889a08f6a1b3173b0',
    'spk_bv_research/native_actor_objective_v4yzaa.py':
        '7c1b53cb7adf4e3d35fdddc9efa134d365ac2f0a392aeb75a6facf0e2995c5b9',
    'spk_bv_research/task_oracle_custody_v4abad.py':
        '15cc718297d8684f52003d3ee0297f2af5345e2ce9bb20aabf42686bab674c3c',
    'spk_bv_research/task_oracle_fixture_v4abad.py':
        'd2c9d86be72f62980935a341a5a067615aca78538dab24ab677c061332a09127',
    'spk_bv_research/task_oracle_audit_v4abad.py':
        'f665ce8b07716c4b0335646c0cc71fcdfc2707ba088237229e75459bc1b89507',
    'spk_bv_research/task_disagreement_v4aeag.py':
        '937d4b9c1cd00e5a0331ee05581c7fa64a0d8784f92a968742cf2ea53618988c',
    'spk_bv_research/task_disagreement_fixture_v4aeag.py':
        '4a0dc6dc4c339df3f9ee0c5e58ea2632a8ddbb57c377d4df69e8e37ffbc44e2b',
    'spk_bv_research/task_disagreement_audit_v4aeag.py':
        '66e47cd5b7d287d7dd02f47b6aa37d445f0fe612d3c00151c3c501c914cd029b',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v3tuv', required=True, type=Path)
    parser.add_argument('--v4abad', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        code = []
        for name, expected in CODE_SHA.items():
            path = root / name
            if (path.is_symlink() or not path.is_file() or
                    path.resolve(strict=True) != path or
                    sha256(path.read_bytes()).hexdigest() != expected):
                raise ValueError('v4aeag source SHA or safe path drift: ' + name)
            code.append((path, path.read_bytes()))
        signed = []
        for source in (args.v3tuv, args.v4abad):
            path = source.resolve(strict=True)
            if (source.is_symlink() or source != path or not path.is_file() or
                    root == path or root in path.parents):
                raise ValueError('v4aeag unsafe predecessor report')
            signed.append((path, path.read_bytes()))
        destination = safe_output(args.out, root, tuple(p for p, _ in signed))
        report = evaluate(json.loads(signed[0][1]), signed[0][1],
                          json.loads(signed[1][1]), signed[1][1])
        if any(p.read_bytes() != raw for p, raw in code + signed):
            raise ValueError('v4aeag source changed during research execution')
        with destination.open('xb') as stream:
            stream.write(canon(report))
        print(json.dumps({
            'status': report['status'], 'output': str(destination),
            'signed_native_replays': report['totals']['signed_native_replays'],
            'counterfactual_native_probes': report['totals']['counterfactual_native_probe_executions'],
            'adjudications': report['totals']['adjudication_scenarios'],
            'reviewer_conflicts_quarantined': report['reviewer_conflicts_quarantined'],
            'reviewer_abstentions_quarantined': report['reviewer_abstentions_quarantined'],
            'program_adoptions': 0, 'native_learning_implemented': False,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print('SPK BV v4ae-v4ag TWO-VIEW PROBE REJECTED: ' + str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
