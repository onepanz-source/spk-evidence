#!/usr/bin/env python3
"""Create-only source-replayed V5-T2g observational report; research-only."""
from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from spk_v5_research.island_residual_service_v5t2g import run_t2g

def emit(path_arg):
    p=Path(path_arg)
    if not p.is_absolute() or p.is_symlink() or p.exists():
        raise ValueError('new absolute non-symlink destination required')
    dest=p.resolve(strict=False)
    if dest==ROOT or ROOT in dest.parents or not dest.parent.is_dir():
        raise ValueError('report destination may not reside in source repository')
    content=(json.dumps(run_t2g(),sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
    fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as f:f.write(content)
    print('V5-T2g source-grounded shadow report created:',dest)
if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: python search/spk_v5_t2g_residual_service.py /tmp/new-report.json')
    try:emit(sys.argv[1])
    except (ValueError,OSError) as e:
        raise SystemExit('V5-T2g REJECTED: '+str(e))
