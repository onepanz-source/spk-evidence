#!/usr/bin/env python3
"""Create-only, research-only V5-T2e source-executed abstract BV cost report."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spk_v5_research.island_bv_resource_bridge_v5t2e import run_t2e


def create_report(path: str) -> dict:
    if type(path) is not str or not path:
        raise ValueError('explicit output outside source repository required')
    target = Path(path).absolute()
    if target.exists() or target.is_symlink() or not target.parent.is_dir():
        raise ValueError('output exists, is symlink, or parent is missing')
    if target.parent.is_symlink():
        raise ValueError('symlinked output parent rejected')
    real = target.resolve(strict=False)
    if ROOT == real or ROOT in real.parents:
        raise ValueError('observational outputs forbidden inside repository')
    report = run_t2e()
    data = (json.dumps(report,sort_keys=True,separators=(',', ':'),ensure_ascii=True)+'\n').encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    return {'output': str(target), 'cells': report['cells'], 'status': report['status']}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: python search/spk_v5_t2e_bv_resource_bridge.py /tmp/new-report.json')
        print(json.dumps(create_report(sys.argv[1]),sort_keys=True))
    except (ValueError, OSError) as error:
        raise SystemExit('SPK V5-T2e REJECTED: '+str(error))
