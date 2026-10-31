"""v4ak-v4am source-pinned, create-only external-head research witness CLI."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.task_anchor_audit_v4akam import evaluate
from spk_bv_research.task_anchor_fixture_v4akam import TEST_ANCHOR_KEY
from spk_bv_research.task_anchor_v4akam import (
    AnchorRejected, check_anchored_database,
)

CODE_SHA = {
    'spk_backvalidation_v0/live_dual_scheduler_v0e.py':
        '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    'spk_bv_research/task_disagreement_v4aeag.py':
        '937d4b9c1cd00e5a0331ee05581c7fa64a0d8784f92a968742cf2ea53618988c',
    'spk_bv_research/task_disagreement_fixture_v4aeag.py':
        '4a0dc6dc4c339df3f9ee0c5e58ea2632a8ddbb57c377d4df69e8e37ffbc44e2b',
    'spk_bv_research/task_escrow_store_v4ahaj.py':
        '85c81558f058ea2b28bfaf0eca729483c076019d762b3e3206e1229f08b5727a',
    'spk_bv_research/task_escrow_fixture_v4ahaj.py':
        '8e3c2d87031851a1bccabe8070ec148513fe73030b74d4e626b0f6ea43e423c8',
    'spk_bv_research/task_escrow_audit_v4ahaj.py':
        '9fdea72ea4a8072693deb7979eb150d1cc9fe43343f67555f3981df5631ba4e5',
    'spk_bv_research/task_anchor_v4akam.py':
        '4ef1434bbda231bb6be9b398faa12bb29884c40d67140e8cb8ae0b4d79a2dc12',
    'spk_bv_research/task_anchor_fixture_v4akam.py':
        '3fde29952eb787d528ce15fe86726012e710029678a030dcb1d7d555c5103278',
    'spk_bv_research/task_anchor_audit_v4akam.py':
        '51d716ce411f6cf3f4964ac2e2093fcabc18fb76d20af080c04a6f724b9fae1f',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v4ahaj', required=True, type=Path)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--anchor-out', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        pins = []
        for name, expected in CODE_SHA.items():
            path = root / name
            if (path.is_symlink() or not path.is_file() or
                    path.resolve(strict=True) != path or
                    sha256(path.read_bytes()).hexdigest() != expected):
                raise AnchorRejected('v4akam pinned code SHA/path drift: ' + name)
            pins.append((path, path.read_bytes()))
        signed = args.v4ahaj
        database = args.db
        if (signed.is_symlink() or signed != signed.resolve(strict=True) or
                not signed.is_file() or root in signed.parents or
                database.is_symlink() or
                database != database.resolve(strict=True) or
                not database.is_file() or root in database.parents):
            raise AnchorRejected('signed predecessor or local SQLite path unsafe')
        raw_signed = signed.read_bytes()
        destination = safe_output(args.out, root, (signed, database))
        anchor_path = safe_output(args.anchor_out, root, (signed, database))
        if destination == anchor_path or destination == database or anchor_path == database:
            raise AnchorRejected('anchor and report require exclusive separate files')
        capsule, report = evaluate(raw_signed, database)
        anchor_raw = canon(capsule)
        if (signed.read_bytes() != raw_signed or
                any(path.read_bytes() != orig for path, orig in pins)):
            raise AnchorRejected('pinned source changed during proof')
        expected_sha = report['separately_custodialized_capsule_sha256']
        check_anchored_database(database, report['sqlite_witness']['parent_sha256'],
                                anchor_raw, TEST_ANCHOR_KEY,
                                expected_anchor_sha256=expected_sha)
        # The anchor and report are NOT a cross-file atomic transaction.
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
        fd = os.open(str(anchor_path), flags, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(anchor_raw)
            target.flush()
            os.fsync(target.fileno())
        with destination.open('xb') as target:
            target.write(canon(report))
        print(json.dumps({
            'status': report['status'], 'anchor': str(anchor_path),
            'anchor_sha256': expected_sha, 'output': str(destination),
            'valid_local_forks_exhibited': report['fork_and_rollback_counterexample']['locally_valid_distinct_forks'],
            'externally_anchored_fork_and_rollback_rejected': True,
            'real_trust_root_provisioned': False,
            'native_learning_implemented': False,
            'program_adoptions': 0,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, IndexError, KeyError) as exc:
        print('SPK BV v4ak-v4am EXTERNAL HEAD PROBE REJECTED: ' + str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
