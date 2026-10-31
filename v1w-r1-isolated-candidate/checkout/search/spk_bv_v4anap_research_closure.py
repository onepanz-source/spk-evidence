"""Final bounded BV research protocol closure; create-only evidence report."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from search.spk_bv_v1b_native_operator_replay import safe_output
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.research_closure_v4anap import (
    ClosureRejected, audit,
)

MAX_INPUT_BYTES = 2_000_000


def _validated_source(path: Path, root: Path, *, limit=MAX_INPUT_BYTES):
    path = path.absolute()
    if (path.is_symlink() or any(p.is_symlink() for p in path.parents) or
            not path.is_file() or root in path.parents or
            path.stat().st_size > limit or path.stat().st_size == 0):
        raise ClosureRejected('unsafe source: ' + str(path))
    if path.resolve(strict=True) != path:
        raise ClosureRejected('noncanonical input path')
    return path.read_bytes()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--v4aeag', required=True, type=Path)
    parser.add_argument('--v4ahaj', required=True, type=Path)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--anchor', required=True, type=Path)
    parser.add_argument('--v4akam', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        sources = [args.v4aeag, args.v4ahaj, args.db,
                   args.anchor, args.v4akam]
        absolute = [p.absolute() for p in sources]
        _validated_source(args.db, root, limit=10_000_000)
        _ids = [(p.stat().st_dev, p.stat().st_ino) for p in absolute]
        if len(set(_ids)) != len(_ids):
            raise ClosureRejected('aliasing research source inputs')
        v4aeag = _validated_source(args.v4aeag, root)
        v4ahaj = _validated_source(args.v4ahaj, root)
        capsule = _validated_source(args.anchor, root)
        observation = _validated_source(args.v4akam, root)
        output = safe_output(args.out, root, tuple(absolute))
        report = audit(root, v4aeag, v4ahaj, args.db, capsule, observation)
        if any(p.read_bytes() != original for p, original in (
                (args.v4aeag, v4aeag), (args.v4ahaj, v4ahaj),
                (args.anchor, capsule), (args.v4akam, observation))):
            raise ClosureRejected('source changed during closure audit')
        # Reopened SQLite is verified within audit. This is deliberately NOT
        # a database transaction nor an authoritative external trust action.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(str(output), flags, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(canon(report))
            target.flush()
            os.fsync(target.fileno())
        print(json.dumps({
            'status': report['status'], 'out': str(output),
            'new_native_learning': False,
            'real_external_authority': False,
            'inherited_tests': report['evidence_counts']['inherited_tests'],
            'research_acceptance_criteria': len(report['research_acceptance']),
            'next': report['handoff'],
            'report_sha256': sha256(canon(report)).hexdigest(),
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        print('SPK BV v4an-v4ap CLOSURE REJECTED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
