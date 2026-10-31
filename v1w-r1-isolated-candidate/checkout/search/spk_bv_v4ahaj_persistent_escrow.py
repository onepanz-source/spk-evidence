"""Create-only SQLite plus JSON reference: task-review durable custody RESEARCH."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_disagreement_fixture_v4aeag import TEST_VIEW_KEYS
from spk_bv_research.task_escrow_store_v4ahaj import DurableEscrow
from spk_bv_research.task_escrow_audit_v4ahaj import evaluate

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
    'spk_bv_research/task_escrow_store_v4ahaj.py':
        '85c81558f058ea2b28bfaf0eca729483c076019d762b3e3206e1229f08b5727a',
    'spk_bv_research/task_escrow_fixture_v4ahaj.py':
        '8e3c2d87031851a1bccabe8070ec148513fe73030b74d4e626b0f6ea43e423c8',
    'spk_bv_research/task_escrow_audit_v4ahaj.py':
        '9fdea72ea4a8072693deb7979eb150d1cc9fe43343f67555f3981df5631ba4e5',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v3tuv', required=True, type=Path)
    parser.add_argument('--v4aeag', required=True, type=Path)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        code = []
        for name, expected in CODE_SHA.items():
            p = root / name
            if (p.is_symlink() or not p.is_file() or
                    p.resolve(strict=True) != p or
                    sha256(p.read_bytes()).hexdigest() != expected):
                raise ValueError('v4ahaj pinned code SHA/path drift: ' + name)
            code.append((p, p.read_bytes()))
        sources = []
        for name in (args.v3tuv, args.v4aeag):
            p = name.resolve(strict=True)
            if (name != p or name.is_symlink() or not p.is_file() or
                    root in p.parents or p == root):
                raise ValueError('v4ahaj unsafe signed predecessor source')
            sources.append((p, p.read_bytes()))
        out = safe_output(args.out, root, tuple(p for p, _ in sources))
        db = safe_output(args.db, root, tuple(p for p, _ in sources))
        if out == db:
            raise ValueError('escrow DB and report must have different destinations')
        report = evaluate(json.loads(sources[0][1]), sources[0][1],
                          json.loads(sources[1][1]), sources[1][1],
                          db_path=db)
        if any(p.read_bytes() != original for p, original in code + sources):
            raise ValueError('v4ahaj source changed during reexecution')
        with DurableEscrow.open(db, report['signed_v4aeag_sha256'],
                                TEST_VIEW_KEYS,
                                external_head=report['sqlite_logical_witness']['head']) as store:
            if store.verify(external_head=report['sqlite_logical_witness']['head']) != report['sqlite_logical_witness']:
                raise ValueError('SQLite custody not identical to output evidence')
        with out.open('xb') as target:
            target.write(canon(report))
        print(json.dumps({
            'status': report['status'], 'output': str(out),
            'database': str(db),
            'signed_native_replays': report['totals']['signed_native_replays'],
            'counterfactual_native_probes': report['totals']['counterfactual_native_probes'],
            'persistent_custody_entries': report['sqlite_logical_witness']['entries'],
            'persisted_unique_nonces': report['sqlite_logical_witness']['persisted_unique_nonces'],
            'review_attempts': report['totals']['custody_attempts'],
            'head_sha256': report['sqlite_logical_witness']['head'],
            'program_adoptions': 0,
            'native_learning_implemented': False,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print('SPK BV v4ah-v4aj DURABLE ESCROW REJECTED: ' + str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
