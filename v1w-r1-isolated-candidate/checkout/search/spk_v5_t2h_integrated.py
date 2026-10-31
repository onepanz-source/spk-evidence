#!/usr/bin/env python3
"""Create-only, pinned, bounded V5-T2h research observation."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from spk_v5_research.island_interleaved_v5t2h import run_t2h


def report_bytes():
    return (json.dumps(run_t2h(),sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()


def main(args):
    if len(args)!=1:
        raise ValueError('usage: python search/spk_v5_t2h_integrated.py /tmp/NEW-report.json')
    root=Path(__file__).resolve().parent.parent
    raw=Path(args[0]).expanduser().absolute()
    if raw.is_symlink() or raw.exists() or root==raw or root in raw.parents:
        raise ValueError('target must be absent, non-symlinked and outside repo')
    # The gate must already have validated manifest before output can be made.
    m=json.loads((root/'docs/spk-v5-t2h-manifest.json').read_text())
    import hashlib
    for rel,digest in m['pins_sha256'].items():
        path=root/rel
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('source pin drift: '+rel)
    payload=report_bytes()
    fd=os.open(str(raw),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(payload)
    print('V5-T2h interleaved fork research report created:',raw)


if __name__=='__main__':
    try:main(sys.argv[1:])
    except (ValueError,OSError) as error:
        print('V5-T2h REJECTED:',error,file=sys.stderr)
        raise SystemExit(2)
