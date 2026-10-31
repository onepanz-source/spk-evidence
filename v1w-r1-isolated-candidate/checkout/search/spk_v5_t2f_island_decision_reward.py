#!/usr/bin/env python3
"""Create-only canonical V5-T2f research report; NEVER native program mutation."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from spk_v5_research.island_decision_reward_v5t2f import run_t2f


def emit(destination):
    path=Path(destination)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError('output must be a new, absolute, non-symlink path')
    resolved=path.resolve(strict=False)
    if resolved == ROOT or ROOT in resolved.parents or not resolved.parent.is_dir():
        raise ValueError('output must be outside repository')
    content=(json.dumps(run_t2f(),sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    # Guard code custody is enforced by the preceding gate; standalone source
    # runner still refuses overwrite and will not rewrite predecessor reports.
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(resolved,flags,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(content)
    print('V5-T2f source-executed report created:',resolved)


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: python search/spk_v5_t2f_island_decision_reward.py /tmp/new-report.json')
    try:emit(sys.argv[1])
    except (ValueError,OSError) as e:
        raise SystemExit('V5-T2f REJECTED: '+str(e))
